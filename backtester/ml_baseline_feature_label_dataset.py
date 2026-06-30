from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .csv_safety import neutralize_csv_formula_fields
from .ml_data_readiness_audit import (
    FEATURE_CANDIDATES,
    _baseline_cutoff,
    _feature_values,
    _format_distribution,
    _format_rates,
    _load_monthly_closes,
    _parse_date,
    _read_csv,
)


AUDIT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "trading_allowed",
    "production_effect",
]

FEATURE_LABEL_COLUMNS = [
    "symbol",
    "feature_date",
    "label_end_date",
    *FEATURE_CANDIDATES,
    "label_return",
    "label",
    "train_cutoff",
    "post_cutoff_data_used_for_train",
    "training_ran",
    "trading_allowed",
    "production_effect",
]


@dataclass(frozen=True)
class BaselineFeatureLabelDatasetResult:
    audit_rows: list[dict[str, str]]
    sample_rows: list[dict[str, str]]


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


def _return(current: object, previous: object) -> float | None:
    if not isinstance(current, float) or not isinstance(previous, float) or previous == 0:
        return None
    return current / previous - 1.0


def _label(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def _format_float(value: float | None) -> str:
    return "" if value is None else f"{value:.10f}"


def _available_symbols(quality_rows: list[dict[str, str]], symbol_months: dict[str, list[dict[str, object]]]) -> set[str]:
    return {
        row.get("symbol", "")
        for row in quality_rows
        if row.get("status") == "PASS" and row.get("symbol")
    } or set(symbol_months)


def _build_feature_label_rows(
    symbol_months: dict[str, list[dict[str, object]]],
    available_symbols: set[str],
    cutoff: date,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for symbol in sorted(available_symbols):
        months = symbol_months.get(symbol, [])
        for index in range(len(months) - 1):
            feature_date = months[index]["date"]
            label_end_date = months[index + 1]["date"]
            if not isinstance(feature_date, date) or not isinstance(label_end_date, date):
                continue
            if feature_date > cutoff or label_end_date > cutoff:
                continue
            label_return = _return(months[index + 1].get("close"), months[index].get("close"))
            if label_return is None:
                continue
            values = _feature_values(months, index)
            row = {
                "symbol": symbol,
                "feature_date": feature_date.isoformat(),
                "label_end_date": label_end_date.isoformat(),
                **{feature: _format_float(values.get(feature)) for feature in FEATURE_CANDIDATES},
                "label_return": _format_float(label_return),
                "label": _label(label_return),
                "train_cutoff": cutoff.isoformat(),
                "post_cutoff_data_used_for_train": "False",
                "training_ran": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
            rows.append({column: row[column] for column in FEATURE_LABEL_COLUMNS})
    return rows


def _feature_missing_rates(rows: list[dict[str, str]]) -> dict[str, float]:
    if not rows:
        return {feature: 1.0 for feature in FEATURE_CANDIDATES}
    return {
        feature: sum(1 for row in rows if row.get(feature, "") == "") / len(rows)
        for feature in FEATURE_CANDIDATES
    }


def _label_distribution(rows: list[dict[str, str]]) -> Counter[str]:
    return Counter(row.get("label", "") for row in rows if row.get("label"))


def build_ml_baseline_feature_label_dataset(
    *,
    price_dir: Path | str = "data/krx_expanded",
    candidate_ledger_csv: Path | str = "data/reports/monthly_candidate_research_ledger.csv",
    data_quality_csv: Path | str = "data/reports/monthly_validation_data_quality.csv",
    data_quality_exclusions_csv: Path | str = "data/reports/data_quality_excluded_symbols.csv",
    universe_coverage_csv: Path | str = "data/reports/monthly_universe_price_coverage.csv",
    pit_universe_csv: Path | str = "data/krx_metadata/krx_universe_monthly.csv",
    train_cutoff: str | None = None,
    sample_limit: int = 200,
) -> BaselineFeatureLabelDatasetResult:
    ledger_rows, ledger_error = _read_csv(candidate_ledger_csv)
    quality_rows, quality_error = _read_csv(data_quality_csv)
    exclusion_rows, exclusion_error = _read_csv(data_quality_exclusions_csv)
    universe_rows, universe_error = _read_csv(universe_coverage_csv)

    cutoff_text = train_cutoff or _baseline_cutoff(ledger_rows, "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    symbol_months, price_errors = _load_monthly_closes(price_dir, cutoff)
    symbols = _available_symbols(quality_rows, symbol_months)
    dataset_rows = _build_feature_label_rows(symbol_months, symbols, cutoff)

    protected = next((row for row in ledger_rows if row.get("status") == "PAPER_REVIEW"), {})
    protected_ok = protected.get("status") == "PAPER_REVIEW" and str(protected.get("protected_from_tuning")).lower() == "true"
    pit_available = (
        Path(pit_universe_csv).exists()
        and not universe_error
        and bool(universe_rows)
        and any(row.get("status") == "PASS" for row in universe_rows)
    )
    source_errors = [error for error in [ledger_error, quality_error, exclusion_error] if error] + price_errors
    max_feature_date = max((_parse_date(row["feature_date"]) for row in dataset_rows), default=None)
    max_label_end = max((_parse_date(row["label_end_date"]) for row in dataset_rows), default=None)
    post_cutoff_used = any(value is not None and value > cutoff for value in (max_feature_date, max_label_end))
    missing_rates = _feature_missing_rates(dataset_rows)
    label_counts = _label_distribution(dataset_rows)
    dataset_ready = (
        not source_errors
        and bool(dataset_rows)
        and not post_cutoff_used
        and protected_ok
        and pit_available
    )
    status = "ready_for_training_scaffold" if dataset_ready else "partial_dataset_only"

    audit_rows = [
        _row(
            "summary",
            status,
            status,
            "Phase 1 baseline feature/label dataset audit only; no model training, OOS rerun, fetch, candidate compare, candidate generation, or strategy parameter change was performed.",
            "derived",
        ),
        _row(
            "source_files_present",
            "PASS" if not source_errors else "BLOCK",
            "all required local sources readable" if not source_errors else "; ".join(source_errors),
            "Required for deterministic local-only feature/label dataset construction.",
            "multiple",
        ),
        _row("train_cutoff", "PASS", cutoff.isoformat(), "Cutoff read from protected candidate ledger unless explicitly overridden.", candidate_ledger_csv),
        _row("available_symbol_count", "PASS" if symbols else "BLOCK", len(symbols), "PASS data-quality symbols, falling back to local price files.", data_quality_csv),
        _row("feature_row_count", "PASS" if dataset_rows else "BLOCK", len(dataset_rows), "Rows with a feature date and next-month label ending on or before cutoff.", price_dir),
        _row("label_row_count", "PASS" if dataset_rows else "BLOCK", len(dataset_rows), "Label rows available for a future training scaffold; no training ran here.", price_dir),
        _row("feature_candidates", "PASS", ";".join(FEATURE_CANDIDATES), "Baseline tabular technical feature candidates from local OHLCV only.", "derived"),
        _row("feature_missing_rates", "PASS" if dataset_rows else "BLOCK", _format_rates(missing_rates), "Missing-rate denominator is feature/label dataset rows.", "derived"),
        _row("label_distribution", "PASS" if dataset_rows else "BLOCK", _format_distribution(label_counts), "Next-month return labels: positive/negative/flat.", "derived"),
        _row("post_cutoff_data_used_for_train", "PASS" if not post_cutoff_used else "BLOCK", post_cutoff_used, f"max_feature_date={max_feature_date}; max_label_end={max_label_end}", "derived"),
        _row("training_ran", "PASS", "False", "Phase 1 creates/audits feature-label data only.", "derived"),
        _row("pit_universe_available", "PASS" if pit_available else "WARN", pit_available, "Requires local PIT universe metadata and PASS universe coverage report.", f"{pit_universe_csv};{universe_coverage_csv}"),
        _row("data_quality_exclusion_applied", "WARN" if any(row.get("status") == "BLOCK" for row in exclusion_rows) else "PASS", any(row.get("status") == "BLOCK" for row in exclusion_rows), f"excluded_symbols={sum(1 for row in exclusion_rows if row.get('status') == 'BLOCK')}", data_quality_exclusions_csv),
        _row("protected_candidate_status", "PASS" if protected_ok else "BLOCK", protected.get("status", "missing"), "Protected PAPER_REVIEW candidate is read-only and remains locked from tuning.", candidate_ledger_csv),
        _row("trading_allowed", "PASS", "False", "Dataset audit only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]
    if universe_error:
        audit_rows.append(_row("universe_coverage_source", "WARN", universe_error, "PIT availability fails closed when coverage report is missing.", universe_coverage_csv))
    if quality_error:
        audit_rows.append(_row("data_quality_source", "BLOCK", quality_error, "Data quality source is required for usable-symbol accounting.", data_quality_csv))

    limit = max(0, sample_limit)
    return BaselineFeatureLabelDatasetResult(audit_rows=audit_rows, sample_rows=dataset_rows[:limit])


def save_ml_baseline_feature_label_dataset_audit(
    result: BaselineFeatureLabelDatasetResult,
    csv_output: Path | str,
    markdown_output: Path | str,
    sample_output: Path | str | None = "data/reports/ml_baseline_feature_label_sample.csv",
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(result.audit_rows)

    if sample_output is not None:
        sample_path = Path(sample_output)
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        with sample_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FEATURE_LABEL_COLUMNS)
            writer.writeheader()
            writer.writerows(neutralize_csv_formula_fields(result.sample_rows, {"symbol"}))

    summary = result.audit_rows[0] if result.audit_rows else {}
    lines = [
        "# ML Baseline Feature/Label Dataset Audit",
        "",
        "## Do Not Trade / Feature-Label Dataset Only",
        "",
        "This report is paper-only and does not train models, rerun OOS, fetch data, compare candidates, generate candidates, tune strategy parameters, promote candidates, call broker APIs, or authorize trading.",
        "",
        f"- Dataset status: `{summary.get('status', 'partial_dataset_only')}`.",
        "- Training ran: `False`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "",
        "## Checks",
        "",
        "| Metric | Status | Value | Reason | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in result.audit_rows:
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
