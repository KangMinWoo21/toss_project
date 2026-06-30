from __future__ import annotations

import csv
from pathlib import Path

from .ml_data_readiness_audit import _read_csv


ML_MODEL_OBSERVATION_STATUS_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "observation_basis",
    "post_cutoff_train_leakage",
    "observation_months",
    "sufficient_observation_months",
    "performance_stability",
    "drawdown",
    "turnover",
    "coverage",
    "candidate_promotion",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]

MIN_OBSERVATION_MONTHS = 3


def build_ml_model_observation_status_report(
    *,
    shadow_scoring_csv: Path | str = "data/reports/ml_shadow_scoring_report.csv",
    model_v1_validation_csv: Path | str = "data/reports/ml_model_v1_validation_report.csv",
    historical_dataset_csv: Path | str | None = None,
    use_historical_backfill: bool = False,
    min_observation_months: int = MIN_OBSERVATION_MONTHS,
) -> list[dict[str, str]]:
    shadow_rows, shadow_error = _read_csv(shadow_scoring_csv)
    validation_rows, validation_error = _read_csv(model_v1_validation_csv)
    historical_rows: list[dict[str, str]] = []
    historical_error = ""
    if use_historical_backfill:
        historical_rows, historical_error = _read_csv(historical_dataset_csv or "")
    source_errors = [error for error in (shadow_error, validation_error, historical_error) if error]
    if source_errors:
        return [_row("summary", "BLOCK", "missing_source", "; ".join(source_errors), "source_check")]

    safe_shadow_rows = [
        row
        for row in shadow_rows
        if row.get("symbol") != "BLOCKED"
        and row.get("order_output") == "False"
        and row.get("broker_submission") == "False"
        and row.get("monthly_plan_regenerated") == "False"
        and row.get("candidate_promotion") == "False"
        and row.get("trading_allowed") == "False"
        and row.get("production_effect") == "none"
        and row.get("protected_candidate_unchanged") == "True"
    ]
    months = sorted({_month(row.get("feature_date", "")) for row in safe_shadow_rows if _month(row.get("feature_date", ""))})
    symbols = sorted({row.get("symbol", "") for row in safe_shadow_rows if row.get("symbol")})
    observation_basis = "forward_shadow"
    post_cutoff_train_leakage = "PASS"
    month_count = len(months)
    sufficient = month_count >= max(1, min_observation_months)
    drawdown = _validation_value(validation_rows, "drawdown", "not_available")
    turnover = _validation_value(validation_rows, "turnover", "not_available")
    coverage = f"symbols={len(symbols)};months={month_count}"
    stability = "recorded_shadow_window" if sufficient else "not_mature_shadow_only"
    status = "paper_only_observation_mature" if sufficient else "paper_only_observation_started"
    common_source = f"{shadow_scoring_csv};{model_v1_validation_csv}"
    observation_source = str(shadow_scoring_csv)
    risk_source = str(model_v1_validation_csv)
    risk_reason = "Read-only model v1 validation reference."
    if use_historical_backfill:
        backfill = _historical_backfill(historical_rows)
        months = backfill["months"]
        month_count = len(months)
        symbols = backfill["symbols"]
        sufficient = month_count >= max(1, min_observation_months)
        drawdown = backfill["drawdown"]
        turnover = backfill["turnover"]
        coverage = f"symbols={len(symbols)};months={month_count}"
        stability = "historical_backfill_stable" if sufficient else "historical_backfill_not_mature"
        status = "paper_only_observation_mature" if sufficient else "paper_only_observation_started"
        observation_basis = "historical_backfill"
        post_cutoff_train_leakage = backfill["post_cutoff_train_leakage"]
        common_source = f"{shadow_scoring_csv};{model_v1_validation_csv};{historical_dataset_csv}"
        observation_source = str(historical_dataset_csv)
        risk_source = str(historical_dataset_csv)
        risk_reason = "Historical backfill selected-return path from existing local feature/label rows."

    rows = [
        _row(
            "summary",
            status,
            status,
            "Paper-only observation status only; no promotion, order output, broker submission, monthly plan regeneration, or production change.",
            common_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "observation_basis",
            "PASS",
            observation_basis,
            "Historical backfill uses existing local feature/label rows only when explicitly requested.",
            str(historical_dataset_csv) if use_historical_backfill else str(shadow_scoring_csv),
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "post_cutoff_train_leakage",
            post_cutoff_train_leakage,
            "False" if post_cutoff_train_leakage == "PASS" else "True",
            "Backfill excludes rows marked as post-cutoff train leakage and does not train production artifacts.",
            str(historical_dataset_csv) if use_historical_backfill else str(shadow_scoring_csv),
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "observation_months",
            "PASS" if month_count > 0 else "BLOCK",
            str(month_count),
            f"Observed paper-only months: {','.join(months) if months else 'none'}. Minimum for maturity: {max(1, min_observation_months)}.",
            observation_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "sufficient_observation_months",
            "PASS" if sufficient else "BLOCK",
            str(sufficient),
            "Observation evidence is not mature until enough paper-only months are recorded.",
            observation_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "performance_stability",
            "PASS" if sufficient else "WARN",
            stability,
            "Performance stability is recorded from the available paper-only observation window without enabling promotion.",
            observation_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "drawdown",
            "PASS" if drawdown != "not_available" else "WARN",
            drawdown,
            risk_reason,
            risk_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "turnover",
            "PASS" if turnover != "not_available" else "WARN",
            turnover,
            risk_reason,
            risk_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "coverage",
            "PASS" if month_count > 0 else "BLOCK",
            coverage,
            "Coverage counts safe paper-only symbols and observed months only.",
            observation_source,
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
        _row(
            "candidate_promotion",
            "PASS",
            "False",
            "No promotion occurs in the observation loop.",
            "safety_guard",
            month_count,
            sufficient,
            stability,
            drawdown,
            turnover,
            coverage,
            observation_basis,
            post_cutoff_train_leakage,
        ),
    ]
    return rows


def save_ml_model_observation_status_report(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ML_MODEL_OBSERVATION_STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_markdown(rows), encoding="utf-8")


def _month(date_text: str) -> str:
    return date_text[:7] if len(date_text) >= 7 else ""


def _validation_value(rows: list[dict[str, str]], metric: str, default: str) -> str:
    for row in rows:
        if row.get("metric") == metric:
            return row.get("value", default)
    return default


def _historical_backfill(rows: list[dict[str, str]]) -> dict[str, object]:
    safe_rows = [
        row
        for row in rows
        if row.get("post_cutoff_data_used_for_train") == "False"
        and row.get("trading_allowed") == "False"
        and row.get("production_effect") == "none"
        and row.get("feature_date")
        and row.get("label_return") not in ("", None)
    ]
    by_feature_date: dict[str, list[dict[str, str]]] = {}
    symbols: set[str] = set()
    for row in safe_rows:
        by_feature_date.setdefault(row["feature_date"], []).append(row)
        if row.get("symbol"):
            symbols.add(row["symbol"])

    selected_returns: list[float] = []
    selected_symbols: list[str] = []
    for feature_date in sorted(by_feature_date):
        candidates = by_feature_date[feature_date]
        selected = max(candidates, key=lambda row: (_historical_score(row), row.get("symbol", "")))
        selected_returns.append(_float(selected.get("label_return"), 0.0))
        selected_symbols.append(selected.get("symbol", ""))

    return {
        "months": sorted({_month(date_text) for date_text in by_feature_date if _month(date_text)}),
        "symbols": sorted(symbols),
        "drawdown": f"{_max_drawdown(selected_returns):.4f}",
        "turnover": f"turnover={_turnover(selected_symbols):.4f}",
        "post_cutoff_train_leakage": "PASS"
        if len(safe_rows) == len(rows) or all(row.get("post_cutoff_data_used_for_train") != "True" for row in rows)
        else "BLOCK",
    }


def _historical_score(row: dict[str, str]) -> float:
    return (
        _float(row.get("return_1m"), 0.0)
        + _float(row.get("return_3m"), 0.0)
        + _float(row.get("return_6m"), 0.0)
        + _float(row.get("volume_change_1m"), 0.0) * 0.1
        + _float(row.get("price_vs_3m_sma"), 0.0)
        - abs(_float(row.get("drawdown_3m"), 0.0))
        - _float(row.get("volatility_3m"), 0.0)
    )


def _float(value: str | None, default: float) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    worst = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        if peak:
            worst = min(worst, equity / peak - 1.0)
    return worst


def _turnover(symbols: list[str]) -> float:
    if len(symbols) <= 1:
        return 0.0
    changes = sum(1 for previous, current in zip(symbols, symbols[1:]) if previous != current)
    return changes / (len(symbols) - 1)


def _row(
    metric: str,
    status: str,
    value: str,
    reason: str,
    source: str,
    observation_months: int | str = 0,
    sufficient_observation_months: bool | str = False,
    performance_stability: str = "not_mature_shadow_only",
    drawdown: str = "not_available",
    turnover: str = "not_available",
    coverage: str = "symbols=0;months=0",
    observation_basis: str = "forward_shadow",
    post_cutoff_train_leakage: str = "PASS",
) -> dict[str, str]:
    return {
        "metric": metric,
        "status": status,
        "value": value,
        "reason": reason,
        "source": source,
        "observation_basis": observation_basis,
        "post_cutoff_train_leakage": post_cutoff_train_leakage,
        "observation_months": str(observation_months),
        "sufficient_observation_months": str(sufficient_observation_months),
        "performance_stability": performance_stability,
        "drawdown": drawdown,
        "turnover": turnover,
        "coverage": coverage,
        "candidate_promotion": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("ML model observation status report is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in ML_MODEL_OBSERVATION_STATUS_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"observation status row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("candidate_promotion", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("protected_candidate_unchanged", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"observation status row {index} {column}={row[column]} expected {expected}")


def _build_markdown(rows: list[dict[str, str]]) -> str:
    summary = next((row for row in rows if row["metric"] == "summary"), rows[0])
    lines = [
        "# ML Model Paper-Only Observation Status",
        "",
        "## Paper-Only Observation Status",
        "",
        "This report records the current shadow-score observation window. It does not promote candidates, generate order output, submit to a broker, regenerate a monthly plan, change strategy parameters, enable production, or authorize trading.",
        "",
        f"- Observation months: `{summary['observation_months']}`.",
        f"- Observation basis: `{summary['observation_basis']}`.",
        f"- Observation maturity: `{summary['sufficient_observation_months']}`.",
        f"- Post-cutoff train leakage: `{summary['post_cutoff_train_leakage']}`.",
        f"- Performance stability: `{summary['performance_stability']}`.",
        f"- Drawdown: `{summary['drawdown']}`.",
        f"- Turnover: `{summary['turnover']}`.",
        f"- Coverage: `{summary['coverage']}`.",
        "- Candidate promotion: `False`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "- Protected candidate unchanged.",
        "",
        "Historical backfill is used only when explicitly requested and only from existing local rows.",
        "",
        "## Status Rows",
        "",
        "| Metric | Status | Value |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['metric']} | {row['status']} | {row['value']} |")
    return "\n".join(lines) + "\n"
