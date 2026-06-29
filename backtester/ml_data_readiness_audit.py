from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean, pstdev


AUDIT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "trading_allowed",
    "production_effect",
]

FEATURE_CANDIDATES = [
    "return_1m",
    "return_3m",
    "return_6m",
    "volatility_3m",
    "volume_change_1m",
    "price_vs_3m_sma",
    "drawdown_3m",
]


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    source = Path(path)
    if not source.exists():
        return [], f"missing source file: {source}"
    try:
        with source.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f)), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return [], f"failed to parse {source}: {exc}"


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def _float_value(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _bool_text(value: object) -> str:
    return str(value).strip().lower()


def _row(metric: str, status: str, value: object, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "metric": metric,
        "status": status,
        "value": str(value),
        "reason": reason,
        "source": str(source),
        "trading_allowed": "False",
        "production_effect": "none",
    }


def _baseline_cutoff(ledger_rows: list[dict[str, str]], fallback: str) -> str:
    protected = next((row for row in ledger_rows if row.get("status") == "PAPER_REVIEW"), {})
    value = protected.get("baseline_cutoff") or protected.get("train_end") or fallback
    return value if _parse_date(value) else fallback


def _symbol_from_path(path: Path) -> str:
    return path.stem


def _load_monthly_closes(price_dir: Path | str, cutoff: date) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    directory = Path(price_dir)
    if not directory.exists():
        return {}, [f"missing price directory: {directory}"]

    symbol_months: dict[str, list[dict[str, object]]] = {}
    errors: list[str] = []
    for path in sorted(directory.glob("*.csv")):
        rows, error = _read_csv(path)
        if error:
            errors.append(error)
            continue
        by_month: dict[str, dict[str, object]] = {}
        for row in rows:
            row_date = _parse_date(row.get("date"))
            close = _float_value(row.get("close"))
            volume = _float_value(row.get("volume"))
            if row_date is None or close is None or row_date > cutoff:
                continue
            key = row_date.strftime("%Y-%m")
            current = by_month.get(key)
            if current is None or row_date > current["date"]:
                by_month[key] = {"date": row_date, "close": close, "volume": volume}
        months = [by_month[key] for key in sorted(by_month)]
        if months:
            symbol_months[_symbol_from_path(path)] = months
    return symbol_months, errors


def _return(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return current / previous - 1.0


def _feature_values(months: list[dict[str, object]], index: int) -> dict[str, float | None]:
    close = months[index]["close"]
    volume = months[index].get("volume")
    close_f = close if isinstance(close, float) else None
    volume_f = volume if isinstance(volume, float) else None
    closes = [m["close"] for m in months[max(0, index - 2) : index + 1] if isinstance(m["close"], float)]
    returns = [
        _return(months[i]["close"], months[i - 1]["close"])
        for i in range(max(1, index - 2), index + 1)
    ]
    clean_returns = [value for value in returns if value is not None]
    high_3m = max(closes) if closes else None
    avg_3m = mean(closes) if len(closes) == 3 else None
    prev_volume = months[index - 1].get("volume") if index >= 1 else None

    return {
        "return_1m": _return(close_f, months[index - 1]["close"] if index >= 1 else None),
        "return_3m": _return(close_f, months[index - 3]["close"] if index >= 3 else None),
        "return_6m": _return(close_f, months[index - 6]["close"] if index >= 6 else None),
        "volatility_3m": pstdev(clean_returns) if len(clean_returns) >= 2 else None,
        "volume_change_1m": _return(volume_f, prev_volume if isinstance(prev_volume, float) else None),
        "price_vs_3m_sma": (close_f / avg_3m - 1.0) if close_f is not None and avg_3m not in (None, 0) else None,
        "drawdown_3m": (close_f / high_3m - 1.0) if close_f is not None and high_3m not in (None, 0) else None,
    }


def _feature_missing_rates(symbol_months: dict[str, list[dict[str, object]]]) -> tuple[dict[str, float], int]:
    totals = Counter({feature: 0 for feature in FEATURE_CANDIDATES})
    missing = Counter({feature: 0 for feature in FEATURE_CANDIDATES})
    row_count = 0
    for months in symbol_months.values():
        for index in range(len(months)):
            row_count += 1
            values = _feature_values(months, index)
            for feature in FEATURE_CANDIDATES:
                totals[feature] += 1
                if values.get(feature) is None:
                    missing[feature] += 1
    rates = {
        feature: (missing[feature] / totals[feature] if totals[feature] else 1.0)
        for feature in FEATURE_CANDIDATES
    }
    return rates, row_count


def _labels(symbol_months: dict[str, list[dict[str, object]]]) -> tuple[int, Counter[str], date | None]:
    distribution: Counter[str] = Counter()
    max_label_end: date | None = None
    count = 0
    for months in symbol_months.values():
        for index in range(len(months) - 1):
            current = months[index]["close"]
            future = months[index + 1]["close"]
            future_date = months[index + 1]["date"]
            label_return = _return(future if isinstance(future, float) else None, current if isinstance(current, float) else None)
            if label_return is None:
                continue
            count += 1
            if label_return > 0:
                distribution["positive"] += 1
            elif label_return < 0:
                distribution["negative"] += 1
            else:
                distribution["flat"] += 1
            if isinstance(future_date, date) and (max_label_end is None or future_date > max_label_end):
                max_label_end = future_date
    return count, distribution, max_label_end


def _format_rates(rates: dict[str, float]) -> str:
    return ";".join(f"{feature}={rates[feature]:.4f}" for feature in FEATURE_CANDIDATES)


def _format_distribution(distribution: Counter[str]) -> str:
    keys = ["positive", "negative", "flat"]
    return ";".join(f"{key}={distribution.get(key, 0)}" for key in keys)


def _source_ready(path: Path | str, rows: list[dict[str, str]], ready_column: str | None = None) -> bool:
    if not Path(path).exists() or not rows:
        return False
    if ready_column is None:
        return True
    return any(_bool_text(row.get(ready_column)) == "true" for row in rows)


def build_ml_data_readiness_audit(
    *,
    price_dir: Path | str = "data/krx_expanded",
    candidate_ledger_csv: Path | str = "data/reports/monthly_candidate_research_ledger.csv",
    data_quality_csv: Path | str = "data/reports/monthly_validation_data_quality.csv",
    data_quality_exclusions_csv: Path | str = "data/reports/data_quality_excluded_symbols.csv",
    universe_coverage_csv: Path | str = "data/reports/monthly_universe_price_coverage.csv",
    pit_universe_csv: Path | str = "data/krx_metadata/krx_universe_monthly.csv",
    fundamental_pit_audit_csv: Path | str = "data/reports/regime_sideways_fundamental_pit_availability_audit.csv",
    train_cutoff: str | None = None,
) -> list[dict[str, str]]:
    ledger_rows, ledger_error = _read_csv(candidate_ledger_csv)
    quality_rows, quality_error = _read_csv(data_quality_csv)
    exclusion_rows, exclusion_error = _read_csv(data_quality_exclusions_csv)
    universe_rows, universe_error = _read_csv(universe_coverage_csv)
    fundamental_rows, fundamental_error = _read_csv(fundamental_pit_audit_csv)
    cutoff_text = train_cutoff or _baseline_cutoff(ledger_rows, "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)

    symbol_months, price_errors = _load_monthly_closes(price_dir, cutoff)
    min_date = min((month["date"] for months in symbol_months.values() for month in months), default=None)
    max_date = max((month["date"] for months in symbol_months.values() for month in months), default=None)
    available_symbols = {
        row.get("symbol", "")
        for row in quality_rows
        if row.get("status") == "PASS" and row.get("symbol")
    } or set(symbol_months)
    feature_rates, feature_row_count = _feature_missing_rates(
        {symbol: months for symbol, months in symbol_months.items() if symbol in available_symbols}
    )
    label_count, label_distribution, max_label_end = _labels(
        {symbol: months for symbol, months in symbol_months.items() if symbol in available_symbols}
    )
    max_feature_date = max_date
    post_cutoff_train_used = any(
        value is not None and value > cutoff
        for value in (max_feature_date, max_label_end)
    )
    protected = next((row for row in ledger_rows if row.get("status") == "PAPER_REVIEW"), {})
    protected_ok = (
        protected.get("status") == "PAPER_REVIEW"
        and _bool_text(protected.get("protected_from_tuning")) == "true"
    )
    pit_available = (
        Path(pit_universe_csv).exists()
        and not universe_error
        and bool(universe_rows)
        and any(row.get("status") == "PASS" for row in universe_rows)
    )
    exclusion_needed = any(row.get("status") == "BLOCK" for row in exclusion_rows)
    source_errors = [error for error in [ledger_error, quality_error, exclusion_error] if error] + price_errors
    baseline_ready = (
        not source_errors
        and bool(available_symbols)
        and label_count > 0
        and not post_cutoff_train_used
        and protected_ok
        and pit_available
    )
    audit_status = "ready_for_baseline_tabular_ml" if baseline_ready else "partial_data_only"

    rows = [
        _row(
            "summary",
            audit_status,
            audit_status,
            "Paper-only ML data readiness audit; no model training, OOS rerun, fetch, candidate generation, or strategy parameter change was performed.",
            "derived",
        ),
        _row(
            "source_files_present",
            "PASS" if not source_errors else "BLOCK",
            "all required local sources readable" if not source_errors else "; ".join(source_errors),
            "Required for deterministic local-only readiness.",
            "multiple",
        ),
        _row("available_period", "PASS" if min_date and max_date else "BLOCK", f"{min_date}..{max_date}", "Local price rows are clipped at the train cutoff.", price_dir),
        _row("available_symbol_count", "PASS" if available_symbols else "BLOCK", len(available_symbols), "Symbols with PASS data-quality rows, falling back to local price files.", data_quality_csv),
        _row("monthly_feature_row_count", "PASS" if feature_row_count else "BLOCK", feature_row_count, "Monthly symbol rows used only for readiness aggregation.", price_dir),
        _row("monthly_label_count", "PASS" if label_count else "BLOCK", label_count, "Next-month labels available fully on or before the train cutoff.", price_dir),
        _row("feature_candidates", "PASS", ";".join(FEATURE_CANDIDATES), "Baseline tabular technical feature candidates from local OHLCV only.", "derived"),
        _row("feature_missing_rates", "PASS" if feature_row_count else "BLOCK", _format_rates(feature_rates), "Missing-rate denominator is monthly feature rows.", "derived"),
        _row("label_distribution", "PASS" if label_count else "BLOCK", _format_distribution(label_distribution), "Next-month return labels: positive/negative/flat.", "derived"),
        _row("train_cutoff", "PASS", cutoff.isoformat(), "Cutoff read from protected candidate ledger unless explicitly overridden.", candidate_ledger_csv),
        _row("post_cutoff_data_used_for_train", "PASS" if not post_cutoff_train_used else "BLOCK", post_cutoff_train_used, f"max_feature_date={max_feature_date}; max_label_end={max_label_end}", "derived"),
        _row("pit_universe_available", "PASS" if pit_available else "WARN", pit_available, "Requires local PIT universe metadata and PASS universe coverage report.", f"{pit_universe_csv};{universe_coverage_csv}"),
        _row("data_quality_exclusion_needed", "WARN" if exclusion_needed else "PASS", exclusion_needed, f"excluded_symbols={sum(1 for row in exclusion_rows if row.get('status') == 'BLOCK')}", data_quality_exclusions_csv),
        _row("fundamentals_status", "not_ready", "not_ready", "Current PIT fundamentals are insufficient for baseline ML features." if not _source_ready(fundamental_pit_audit_csv, fundamental_rows, "locally_usable_by_audit_as_of") else "Some rows exist, but this audit keeps fundamentals out of baseline start.", fundamental_pit_audit_csv if not fundamental_error else fundamental_error),
        _row("news_status", "not_ready", "not_ready", "No current PIT-safe news feature table is available for ML readiness.", "local reports"),
        _row("sentiment_status", "not_ready", "not_ready", "No current PIT-safe sentiment feature table is available for ML readiness.", "local reports"),
        _row("protected_candidate_status", "PASS" if protected_ok else "BLOCK", protected.get("status", "missing"), "Protected PAPER_REVIEW candidate is read-only and remains locked from tuning.", candidate_ledger_csv),
        _row("recommended_model_start", "PASS", "baseline_tabular_ml", "Start with baseline tabular ML only after review; do not train in this audit.", "derived"),
        _row("deep_learning_status", "not_ready", "not_ready", "Local history and feature breadth are insufficient for deep learning.", "derived"),
        _row("trading_allowed", "PASS", "False", "Readiness report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]
    if universe_error:
        rows.append(_row("universe_coverage_source", "WARN", universe_error, "PIT availability fails closed when coverage report is missing.", universe_coverage_csv))
    if quality_error:
        rows.append(_row("data_quality_source", "BLOCK", quality_error, "Data quality source is required for usable-symbol accounting.", data_quality_csv))
    return rows


def save_ml_data_readiness_audit(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    lines = [
        "# ML Data Readiness Audit",
        "",
        "## Do Not Trade / Data Readiness Audit Only",
        "",
        "This report is paper-only and does not train models, rerun OOS, fetch data, generate candidates, tune strategy parameters, promote candidates, call broker APIs, or authorize trading.",
        "",
        f"- Audit status: `{summary.get('status', 'partial_data_only')}`.",
        "- Recommended model start: `baseline_tabular_ml`.",
        "- Deep learning status: `not_ready`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "",
        "## Checks",
        "",
        "| Metric | Status | Value | Reason | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {metric} | {status} | {value} | {reason} | {source} |".format(
                metric=row.get("metric", ""),
                status=row.get("status", ""),
                value=str(row.get("value", "")).replace("|", "/"),
                reason=str(row.get("reason", "")).replace("|", "/"),
                source=str(row.get("source", "")).replace("|", "/"),
            )
        )

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
