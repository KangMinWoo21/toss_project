from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .csv_safety import neutralize_csv_formula_fields
from .ml_baseline_model_training import (
    _audit_value,
    _eligible_rows,
    _feature_stats,
    _sigmoid,
    _train_logistic,
    _vector,
)
from .ml_baseline_validation import _float, _month_key
from .ml_data_readiness_audit import FEATURE_CANDIDATES, _parse_date, _read_csv


FEATURE_IMPORTANCE_COLUMNS = [
    "feature",
    "rank",
    "coefficient",
    "importance_abs",
    "direction",
    "missing_rate",
    "overfit_risk_note",
    "train_cutoff",
    "leakage_check",
    "pit_universe_check",
    "protected_candidate_status",
    "candidate_modified",
    "trading_allowed",
    "production_effect",
]

FAILURE_ANALYSIS_COLUMNS = [
    "row_type",
    "period",
    "symbol",
    "regime",
    "predicted_label",
    "actual_label",
    "label_return",
    "failure_reason",
    "overfit_risk_note",
    "train_cutoff",
    "leakage_check",
    "pit_universe_check",
    "protected_candidate_status",
    "candidate_modified",
    "trading_allowed",
    "production_effect",
]


def _validation_status(rows: list[dict[str, str]], metric: str, default: str = "") -> str:
    for row in rows:
        if row.get("metric") == metric:
            return row.get("status", default)
    return default


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _regime(row: dict[str, str]) -> str:
    volatility = _float(row.get("volatility_3m"))
    momentum = _float(row.get("return_3m"))
    if volatility is not None and volatility >= 0.08:
        return "high_volatility"
    if momentum is not None and momentum > 0:
        return "positive_momentum"
    if momentum is not None and momentum < 0:
        return "negative_momentum"
    return "neutral_or_sparse"


def _prediction(row: dict[str, str], stats: dict[str, tuple[float, float]], weights: list[float]) -> str:
    probability = _sigmoid(sum(weight * value for weight, value in zip(weights, _vector(row, stats))))
    return "positive" if probability >= 0.5 else "negative"


def _failure_reason(row: dict[str, str], predicted: str) -> str:
    if predicted != row.get("label"):
        return "wrong_direction"
    label_return = _float(row.get("label_return")) or 0.0
    if label_return < 0:
        return "negative_realized_return"
    return "not_failure"


def _feature_rows(
    dataset_rows: list[dict[str, str]],
    stats: dict[str, tuple[float, float]],
    weights: list[float],
    *,
    cutoff: date,
    protected_status: str,
    leakage_check: str,
    pit_check: str,
) -> list[dict[str, str]]:
    feature_weights = list(zip(FEATURE_CANDIDATES, weights[1:]))
    feature_weights.sort(key=lambda item: abs(item[1]), reverse=True)
    total_rows = max(len(dataset_rows), 1)
    rows: list[dict[str, str]] = []
    for rank, (feature, coefficient) in enumerate(feature_weights, start=1):
        missing = sum(1 for row in dataset_rows if row.get(feature, "") == "") / total_rows
        direction = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "flat"
        rows.append(
            {
                "feature": feature,
                "rank": str(rank),
                "coefficient": f"{coefficient:.6f}",
                "importance_abs": f"{abs(coefficient):.6f}",
                "direction": direction,
                "missing_rate": f"{missing:.4f}",
                "overfit_risk_note": "overfit risk: feature importance is from a paper-only baseline and requires future validation before any use.",
                "train_cutoff": cutoff.isoformat(),
                "leakage_check": leakage_check,
                "pit_universe_check": pit_check,
                "protected_candidate_status": protected_status,
                "candidate_modified": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
        )
    return rows


def _failure_rows(
    dataset_rows: list[dict[str, str]],
    stats: dict[str, tuple[float, float]],
    weights: list[float],
    *,
    cutoff: date,
    protected_status: str,
    leakage_check: str,
    pit_check: str,
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    regime_returns: dict[str, list[float]] = defaultdict(list)
    month_returns: dict[str, list[float]] = defaultdict(list)
    for row in dataset_rows:
        label_return = _float(row.get("label_return")) or 0.0
        regime = _regime(row)
        month = _month_key(row.get("feature_date", ""))
        predicted = _prediction(row, stats, weights)
        reason = _failure_reason(row, predicted)
        regime_returns[regime].append(label_return)
        month_returns[month].append(label_return)
        if reason != "not_failure":
            failures.append(
                {
                    "row_type": "failure_symbol",
                    "period": month,
                    "symbol": row.get("symbol", ""),
                    "regime": regime,
                    "predicted_label": predicted,
                    "actual_label": row.get("label", ""),
                    "label_return": f"{label_return:.6f}",
                    "failure_reason": reason,
                    "overfit_risk_note": "overfit risk: failures are diagnostic and do not justify tuning or promotion.",
                    "train_cutoff": cutoff.isoformat(),
                    "leakage_check": leakage_check,
                    "pit_universe_check": pit_check,
                    "protected_candidate_status": protected_status,
                    "candidate_modified": "False",
                    "trading_allowed": "False",
                    "production_effect": "none",
                }
            )
    wrote_failure_month = False
    for month, values in sorted(month_returns.items()):
        avg_return = _average(values)
        if avg_return < 0:
            wrote_failure_month = True
            failures.append(
                {
                    "row_type": "failure_month",
                    "period": month,
                    "symbol": "ALL",
                    "regime": "monthly_average",
                    "predicted_label": "mixed",
                    "actual_label": "mixed",
                    "label_return": f"{avg_return:.6f}",
                    "failure_reason": "negative_month_average",
                    "overfit_risk_note": "overfit risk: month-level failures require observation, not tuning.",
                    "train_cutoff": cutoff.isoformat(),
                    "leakage_check": leakage_check,
                    "pit_universe_check": pit_check,
                    "protected_candidate_status": protected_status,
                    "candidate_modified": "False",
                    "trading_allowed": "False",
                    "production_effect": "none",
                }
            )
    if month_returns and not wrote_failure_month:
        month, values = min(month_returns.items(), key=lambda item: _average(item[1]))
        failures.append(
            {
                "row_type": "failure_month",
                "period": month,
                "symbol": "ALL",
                "regime": "monthly_average",
                "predicted_label": "mixed",
                "actual_label": "mixed",
                "label_return": f"{_average(values):.6f}",
                "failure_reason": "worst_month_diagnostic",
                "overfit_risk_note": "overfit risk: worst-month diagnostic requires observation, not tuning.",
                "train_cutoff": cutoff.isoformat(),
                "leakage_check": leakage_check,
                "pit_universe_check": pit_check,
                "protected_candidate_status": protected_status,
                "candidate_modified": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
        )
    for regime, values in sorted(regime_returns.items()):
        failures.append(
            {
                "row_type": "regime_summary",
                "period": "ALL",
                "symbol": "ALL",
                "regime": regime,
                "predicted_label": "mixed",
                "actual_label": "mixed",
                "label_return": f"{_average(values):.6f}",
                "failure_reason": f"rows={len(values)}",
                "overfit_risk_note": "overfit risk: regime summary is descriptive only.",
                "train_cutoff": cutoff.isoformat(),
                "leakage_check": leakage_check,
                "pit_universe_check": pit_check,
                "protected_candidate_status": protected_status,
                "candidate_modified": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
        )
    if not failures:
        failures.append(
            {
                "row_type": "failure_symbol",
                "period": "NONE",
                "symbol": "NONE",
                "regime": "none",
                "predicted_label": "none",
                "actual_label": "none",
                "label_return": "0.000000",
                "failure_reason": "no_failure_rows_detected",
                "overfit_risk_note": "overfit risk still applies even when no failure row is detected.",
                "train_cutoff": cutoff.isoformat(),
                "leakage_check": leakage_check,
                "pit_universe_check": pit_check,
                "protected_candidate_status": protected_status,
                "candidate_modified": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
        )
    return failures


def build_ml_explainability_failure_analysis_reports(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    validation_report_csv: Path | str = "data/reports/ml_baseline_validation_report.csv",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    dataset_rows, _ = _read_csv(dataset_csv)
    validation_rows, _ = _read_csv(validation_report_csv)
    cutoff_text = _audit_value(validation_rows, "train_cutoff", "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    protected_status = _audit_value(validation_rows, "protected_candidate_status", "PAPER_REVIEW")
    leakage_check = _validation_status(validation_rows, "leakage_check", "BLOCK")
    pit_check = _validation_status(validation_rows, "pit_universe_check", "BLOCK")
    eligible = _eligible_rows(dataset_rows, cutoff)
    stats = _feature_stats(eligible)
    weights = _train_logistic(eligible, stats) if eligible else [0.0] * (len(FEATURE_CANDIDATES) + 1)
    return (
        _feature_rows(
            eligible,
            stats,
            weights,
            cutoff=cutoff,
            protected_status=protected_status,
            leakage_check=leakage_check,
            pit_check=pit_check,
        ),
        _failure_rows(
            eligible,
            stats,
            weights,
            cutoff=cutoff,
            protected_status=protected_status,
            leakage_check=leakage_check,
            pit_check=pit_check,
        ),
    )


def save_ml_explainability_failure_analysis_reports(
    feature_rows: list[dict[str, str]],
    failure_rows: list[dict[str, str]],
    feature_importance_output: Path | str,
    failure_analysis_output: Path | str,
) -> None:
    feature_path = Path(feature_importance_output)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    with feature_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_IMPORTANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(feature_rows)

    failure_path = Path(failure_analysis_output)
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    with failure_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FAILURE_ANALYSIS_COLUMNS)
        writer.writeheader()
        writer.writerows(neutralize_csv_formula_fields(failure_rows, {"symbol"}))
