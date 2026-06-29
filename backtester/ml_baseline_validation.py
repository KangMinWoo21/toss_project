from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date
from pathlib import Path

from .ml_baseline_model_training import (
    _accuracy,
    _audit_value,
    _eligible_rows,
    _feature_stats,
    _format_float,
    _sigmoid,
    _split_train_validation,
    _target,
    _train_logistic,
    _vector,
)
from .ml_data_readiness_audit import FEATURE_CANDIDATES, _parse_date, _read_csv


VALIDATION_REPORT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "trading_allowed",
    "production_effect",
]


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


def _float(value: object) -> float | None:
    try:
        text = str(value).strip()
        return None if text == "" else float(text)
    except ValueError:
        return None


def _month_key(value: str) -> str:
    return value[:7]


def _monthly_validation_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    monthly: list[dict[str, object]] = []
    dates = sorted({_month_key(row["feature_date"]) for row in rows})
    for index in range(1, len(dates)):
        train_months = set(dates[:index])
        validation_month = dates[index]
        train_rows = [row for row in rows if _month_key(row["feature_date"]) in train_months]
        validation_rows = [row for row in rows if _month_key(row["feature_date"]) == validation_month]
        if not train_rows or not validation_rows:
            continue
        stats = _feature_stats(train_rows)
        weights = _train_logistic(train_rows, stats)
        accuracy = _accuracy(validation_rows, stats, weights)
        selected = _selected_validation_rows(validation_rows, stats, weights)
        selected_return = _average_return(selected)
        benchmark_return = _average_return(validation_rows)
        monthly.append(
            {
                "month": validation_month,
                "train_rows": len(train_rows),
                "validation_rows": len(validation_rows),
                "accuracy": accuracy,
                "selected_return": selected_return,
                "benchmark_return": benchmark_return,
                "selected_symbols": tuple(row.get("symbol", "") for row in selected),
            }
        )
    return monthly


def _selected_validation_rows(
    rows: list[dict[str, str]],
    stats: dict[str, tuple[float, float]],
    weights: list[float],
) -> list[dict[str, str]]:
    scored: list[tuple[float, dict[str, str]]] = []
    for row in rows:
        probability = _sigmoid(sum(weight * value for weight, value in zip(weights, _vector(row, stats))))
        scored.append((probability, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    count = max(1, min(5, len(scored) // 2 or 1))
    return [row for _, row in scored[:count]]


def _average_return(rows: list[dict[str, str]]) -> float:
    values = [_float(row.get("label_return")) for row in rows]
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else 0.0


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    return drawdown


def _turnover(monthly_rows: list[dict[str, object]]) -> float:
    if len(monthly_rows) < 2:
        return 0.0
    changes: list[float] = []
    previous: set[str] | None = None
    for row in monthly_rows:
        current = set(row.get("selected_symbols", ()))
        if previous is not None:
            denominator = max(len(previous | current), 1)
            changes.append(len(previous ^ current) / denominator)
        previous = current
    return sum(changes) / len(changes) if changes else 0.0


def _missing_feature_rate(rows: list[dict[str, str]]) -> float:
    total = len(rows) * len(FEATURE_CANDIDATES)
    if total == 0:
        return 1.0
    missing = sum(1 for row in rows for feature in FEATURE_CANDIDATES if row.get(feature, "") == "")
    return missing / total


def _distribution(rows: list[dict[str, str]]) -> str:
    counts = Counter(row.get("label", "") for row in rows)
    return ";".join(f"{key}={counts.get(key, 0)}" for key in ["positive", "negative"])


def build_ml_baseline_validation_report(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    training_report_csv: Path | str = "data/reports/ml_baseline_model_training_report.csv",
) -> list[dict[str, str]]:
    dataset_rows, dataset_error = _read_csv(dataset_csv)
    training_rows, training_error = _read_csv(training_report_csv)
    cutoff_text = _audit_value(training_rows, "train_cutoff", "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    protected_status = _audit_value(training_rows, "protected_candidate_status", "missing")
    training_ready = _audit_value(training_rows, "summary") == "paper_only_baseline_trained"
    eligible = _eligible_rows(dataset_rows, cutoff)
    train_rows, validation_rows = _split_train_validation(eligible)
    monthly_rows = _monthly_validation_rows(eligible)
    max_label_end = max((_parse_date(row.get("label_end_date")) for row in eligible), default=None)
    post_cutoff_used = any(value is not None and value > cutoff for value in (max_label_end,))
    leakage_ok = bool(eligible) and not post_cutoff_used
    pit_ok = all(row.get("post_cutoff_data_used_for_train") == "False" for row in eligible)
    feature_missing_rate = _missing_feature_rate(eligible)
    feature_ok = bool(eligible) and feature_missing_rate < 1.0
    accuracies = [row["accuracy"] for row in monthly_rows if isinstance(row.get("accuracy"), float)]
    selected_returns = [float(row["selected_return"]) for row in monthly_rows]
    benchmark_returns = [float(row["benchmark_return"]) for row in monthly_rows]
    hit_rate = sum(1 for value in selected_returns if value > 0) / len(selected_returns) if selected_returns else 0.0
    average_selected = sum(selected_returns) / len(selected_returns) if selected_returns else 0.0
    average_benchmark = sum(benchmark_returns) / len(benchmark_returns) if benchmark_returns else 0.0
    average_accuracy = sum(accuracies) / len(accuracies) if accuracies else None
    drawdown = _max_drawdown(selected_returns)
    turnover = _turnover(monthly_rows)
    source_errors = [error for error in [dataset_error, training_error] if error]
    status = (
        "paper_only_validation_complete"
        if training_ready and leakage_ok and pit_ok and feature_ok and monthly_rows and not source_errors
        else "validation_blocked"
    )

    return [
        _row(
            "summary",
            status,
            status,
            "Phase 3 paper-only monthly walk-forward validation; no OOS rerun, fetch, candidate compare, candidate modification, promotion, broker call, or production change was performed.",
            "derived",
        ),
        _row(
            "source_files_present",
            "PASS" if not source_errors else "BLOCK",
            "all required local sources readable" if not source_errors else "; ".join(source_errors),
            "Phase 3 consumes only Phase 1 dataset sample and Phase 2 training report.",
            f"{dataset_csv};{training_report_csv}",
        ),
        _row("training_report_ready", "PASS" if training_ready else "BLOCK", training_ready, "Requires Phase 2 paper_only_baseline_trained.", training_report_csv),
        _row("train_cutoff", "PASS", cutoff.isoformat(), "Cutoff inherited from Phase 2 training report.", training_report_csv),
        _row("walk_forward_months", "PASS" if monthly_rows else "BLOCK", f"months={len(monthly_rows)}", "Monthly expanding-window validation over pre-cutoff rows.", "derived"),
        _row("leakage_check", "PASS" if leakage_ok else "BLOCK", leakage_ok, f"max_label_end={max_label_end}; cutoff={cutoff}", "derived"),
        _row("pit_universe_check", "PASS" if pit_ok else "BLOCK", pit_ok, "Dataset rows must carry post_cutoff_data_used_for_train=False.", dataset_csv),
        _row("feature_availability_check", "PASS" if feature_ok else "BLOCK", f"missing_rate={feature_missing_rate:.4f}", "At least some baseline features must be available for validation.", dataset_csv),
        _row("post_cutoff_data_used_for_validation", "PASS" if not post_cutoff_used else "BLOCK", post_cutoff_used, "Post-cutoff rows are excluded before validation.", "derived"),
        _row("oos_rerun", "PASS", "False", "No OOS rerun is performed in Phase 3.", "derived"),
        _row("validation_accuracy", "PASS" if average_accuracy is not None else "WARN", _format_float(average_accuracy), "Average monthly validation accuracy; pre-cutoff diagnostic only.", "derived"),
        _row("benchmark_relative_performance", "PASS" if monthly_rows else "BLOCK", f"model_return={average_selected:.4f};benchmark_return={average_benchmark:.4f};excess={average_selected - average_benchmark:.4f}", "Read-only benchmark comparison from validation rows; no candidate compare or promotion.", "derived"),
        _row("drawdown", "PASS" if monthly_rows else "BLOCK", f"{drawdown:.4f}", "Drawdown of monthly selected-return path.", "derived"),
        _row("hit_rate", "PASS" if monthly_rows else "BLOCK", f"{hit_rate:.4f}", "Share of validation months with positive selected return.", "derived"),
        _row("turnover", "PASS" if monthly_rows else "BLOCK", f"turnover={turnover:.4f}", "Average symbol-set turnover across validation months.", "derived"),
        _row("label_distribution_validation", "PASS" if validation_rows else "BLOCK", _distribution(validation_rows), "Holdout validation labels remain pre-cutoff.", "derived"),
        _row("protected_candidate_status", "PASS" if protected_status == "PAPER_REVIEW" else "BLOCK", protected_status, "Protected PAPER_REVIEW candidate remains unchanged.", training_report_csv),
        _row("candidate_modified", "PASS", "False", "Phase 3 may reference existing status only; no candidate is modified, tuned, or promoted.", "derived"),
        _row("candidate_promotion", "PASS", "False", "No promotion occurs in Phase 3.", "derived"),
        _row("trading_allowed", "PASS", "False", "Validation report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]


def save_ml_baseline_validation_report(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    lines = [
        "# ML Baseline Validation Report",
        "",
        "## Do Not Trade / Paper-Only ML Validation",
        "",
        "This report is paper-only. It performs pre-cutoff monthly validation diagnostics only, does not rerun OOS, does not fetch data, does not perform candidate comparison for promotion, does not allow candidate modification, does not call broker APIs, and does not authorize trading.",
        "",
        f"- Validation status: `{summary.get('status', 'validation_blocked')}`.",
        "- Leakage check: `PASS` when recorded in the checks table.",
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
