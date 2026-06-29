from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date
from pathlib import Path

from .ml_baseline_feature_label_dataset import FEATURE_LABEL_COLUMNS
from .ml_data_readiness_audit import FEATURE_CANDIDATES, _parse_date, _read_csv


TRAINING_REPORT_COLUMNS = [
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


def _audit_value(rows: list[dict[str, str]], metric: str, default: str = "") -> str:
    for row in rows:
        if row.get("metric") == metric:
            return row.get("value", default)
    return default


def _eligible_rows(rows: list[dict[str, str]], cutoff: date) -> list[dict[str, str]]:
    eligible: list[dict[str, str]] = []
    for row in rows:
        feature_date = _parse_date(row.get("feature_date"))
        label_end_date = _parse_date(row.get("label_end_date"))
        if feature_date is None or label_end_date is None:
            continue
        if feature_date > cutoff or label_end_date > cutoff:
            continue
        if row.get("post_cutoff_data_used_for_train") != "False":
            continue
        if row.get("training_ran") != "False":
            continue
        if row.get("trading_allowed") != "False":
            continue
        if row.get("production_effect") != "none":
            continue
        if row.get("label") not in {"positive", "negative"}:
            continue
        eligible.append(row)
    return eligible


def _split_train_validation(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    dates = sorted({row["feature_date"] for row in rows})
    if len(dates) < 2:
        return rows, []
    split_index = max(1, int(len(dates) * 0.8))
    if split_index >= len(dates):
        split_index = len(dates) - 1
    validation_dates = set(dates[split_index:])
    train = [row for row in rows if row["feature_date"] not in validation_dates]
    validation = [row for row in rows if row["feature_date"] in validation_dates]
    return train, validation


def _feature_stats(rows: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    stats: dict[str, tuple[float, float]] = {}
    for feature in FEATURE_CANDIDATES:
        values = [_float(row.get(feature)) for row in rows]
        clean = [value for value in values if value is not None]
        mean = sum(clean) / len(clean) if clean else 0.0
        variance = sum((value - mean) ** 2 for value in clean) / len(clean) if clean else 0.0
        std = math.sqrt(variance) or 1.0
        stats[feature] = (mean, std)
    return stats


def _vector(row: dict[str, str], stats: dict[str, tuple[float, float]]) -> list[float]:
    values = [1.0]
    for feature in FEATURE_CANDIDATES:
        raw = _float(row.get(feature))
        mean, std = stats[feature]
        value = mean if raw is None else raw
        values.append((value - mean) / std)
    return values


def _target(row: dict[str, str]) -> int:
    return 1 if row.get("label") == "positive" else 0


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _train_logistic(train_rows: list[dict[str, str]], stats: dict[str, tuple[float, float]]) -> list[float]:
    weights = [0.0] * (len(FEATURE_CANDIDATES) + 1)
    learning_rate = 0.05
    epochs = 30
    for _ in range(epochs):
        for row in train_rows:
            x = _vector(row, stats)
            prediction = _sigmoid(sum(weight * value for weight, value in zip(weights, x)))
            error = prediction - _target(row)
            for index, value in enumerate(x):
                weights[index] -= learning_rate * error * value
    return weights


def _accuracy(rows: list[dict[str, str]], stats: dict[str, tuple[float, float]], weights: list[float]) -> float | None:
    if not rows:
        return None
    correct = 0
    for row in rows:
        x = _vector(row, stats)
        prediction = 1 if _sigmoid(sum(weight * value for weight, value in zip(weights, x))) >= 0.5 else 0
        if prediction == _target(row):
            correct += 1
    return correct / len(rows)


def _distribution(rows: list[dict[str, str]]) -> str:
    counts = Counter(row.get("label", "") for row in rows)
    return ";".join(f"{key}={counts.get(key, 0)}" for key in ["positive", "negative"])


def _format_float(value: float | None) -> str:
    return "not_available" if value is None else f"{value:.4f}"


def build_ml_baseline_model_training_report(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    dataset_audit_csv: Path | str = "data/reports/ml_baseline_feature_label_dataset_audit.csv",
) -> list[dict[str, str]]:
    dataset_rows, dataset_error = _read_csv(dataset_csv)
    audit_rows, audit_error = _read_csv(dataset_audit_csv)
    cutoff_text = _audit_value(audit_rows, "train_cutoff", "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    protected_status = _audit_value(audit_rows, "protected_candidate_status", "missing")
    dataset_ready = _audit_value(audit_rows, "summary") == "ready_for_training_scaffold"
    eligible = _eligible_rows(dataset_rows, cutoff)
    train_rows, validation_rows = _split_train_validation(eligible)
    stats = _feature_stats(train_rows)
    weights = _train_logistic(train_rows, stats) if train_rows else [0.0] * (len(FEATURE_CANDIDATES) + 1)
    train_accuracy = _accuracy(train_rows, stats, weights)
    validation_accuracy = _accuracy(validation_rows, stats, weights)
    max_train_label_end = max((_parse_date(row.get("label_end_date")) for row in train_rows), default=None)
    max_validation_label_end = max((_parse_date(row.get("label_end_date")) for row in validation_rows), default=None)
    post_cutoff_used = any(value is not None and value > cutoff for value in (max_train_label_end, max_validation_label_end))
    split_safe = bool(train_rows) and bool(validation_rows) and not post_cutoff_used
    source_errors = [error for error in [dataset_error, audit_error] if error]
    status = "paper_only_baseline_trained" if dataset_ready and split_safe and not source_errors else "training_scaffold_blocked"

    return [
        _row(
            "summary",
            status,
            status,
            "Phase 2 paper-only baseline model training scaffold; no OOS rerun, fetch, candidate compare, candidate promotion, broker call, or production linkage was performed.",
            "derived",
        ),
        _row(
            "source_files_present",
            "PASS" if not source_errors else "BLOCK",
            "all required local sources readable" if not source_errors else "; ".join(source_errors),
            "Phase 2 consumes the Phase 1 feature/label dataset and audit only.",
            f"{dataset_csv};{dataset_audit_csv}",
        ),
        _row("model_type", "PASS", "logistic_regression_sgd", "Simplest paper-only baseline implemented with standard-library deterministic SGD.", "derived"),
        _row("dataset_ready", "PASS" if dataset_ready else "BLOCK", dataset_ready, "Requires Phase 1 ready_for_training_scaffold.", dataset_audit_csv),
        _row("train_cutoff", "PASS", cutoff.isoformat(), "Cutoff inherited from Phase 1 audit.", dataset_audit_csv),
        _row("train_row_count", "PASS" if train_rows else "BLOCK", len(train_rows), "Training split uses only pre-cutoff rows.", dataset_csv),
        _row("validation_row_count", "PASS" if validation_rows else "BLOCK", len(validation_rows), "Validation split uses only pre-cutoff rows.", dataset_csv),
        _row("train_validation_split_cutoff_safe", "PASS" if split_safe else "BLOCK", split_safe, f"max_train_label_end={max_train_label_end}; max_validation_label_end={max_validation_label_end}", "derived"),
        _row("post_cutoff_data_used_for_train", "PASS" if not post_cutoff_used else "BLOCK", post_cutoff_used, "Rows after cutoff are excluded before train/validation split.", "derived"),
        _row("oos_data_used", "PASS", "False", "Post-cutoff OOS data is not used in Phase 2.", "derived"),
        _row("label_distribution_train", "PASS" if train_rows else "BLOCK", _distribution(train_rows), "Binary positive/negative labels used for baseline scaffold.", "derived"),
        _row("label_distribution_validation", "PASS" if validation_rows else "BLOCK", _distribution(validation_rows), "Validation labels are pre-cutoff only.", "derived"),
        _row("train_accuracy", "PASS" if train_accuracy is not None else "WARN", _format_float(train_accuracy), "In-sample diagnostic only; not a production claim.", "derived"),
        _row("validation_accuracy", "PASS" if validation_accuracy is not None else "WARN", _format_float(validation_accuracy), "Pre-cutoff validation diagnostic only; no OOS review performed.", "derived"),
        _row("model_artifact_written", "PASS", "False", "No model artifact is written in this scaffold loop.", "derived"),
        _row("production_artifact_linked", "PASS", "False", "No model artifact is connected to production.", "derived"),
        _row("protected_candidate_status", "PASS" if protected_status == "PAPER_REVIEW" else "BLOCK", protected_status, "Protected PAPER_REVIEW candidate remains unchanged.", dataset_audit_csv),
        _row("candidate_promotion", "PASS", "False", "Phase 2 cannot promote or tune candidates.", "derived"),
        _row("trading_allowed", "PASS", "False", "Training report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]


def save_ml_baseline_model_training_report(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRAINING_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    lines = [
        "# ML Baseline Model Training Report",
        "",
        "## Do Not Trade / Paper-Only Baseline Training",
        "",
        "This report is paper-only. It uses only the Phase 1 local feature/label dataset, does not rerun OOS, does not fetch data, does not compare or promote candidates, does not write a production artifact, does not call broker APIs, and does not authorize trading.",
        "",
        f"- Training status: `{summary.get('status', 'training_scaffold_blocked')}`.",
        "- Model type: `logistic_regression_sgd`.",
        "- OOS data used: `False`.",
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
