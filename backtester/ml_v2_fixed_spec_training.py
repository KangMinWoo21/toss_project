from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .ml_baseline_model_training import _audit_value, _format_float
from .ml_data_readiness_audit import _parse_date, _read_csv


ML_V2_FIXED_SPEC_REPORT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "post_cutoff_data_used_for_train",
    "external_features_used",
    "formula_selection_used",
    "model_selection_used",
    "hyperparameter_sweep_used",
    "candidate_creation",
    "candidate_promotion",
    "broker_submission",
    "order_execution",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]


@dataclass(frozen=True)
class MlV2FixedSpecReports:
    training_rows: list[dict[str, str]]
    validation_rows: list[dict[str, str]]
    markdown: str


def _row(metric: str, status: str, value: object, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "metric": metric,
        "status": status,
        "value": str(value),
        "reason": reason,
        "source": str(source),
        "post_cutoff_data_used_for_train": "False",
        "external_features_used": "False",
        "formula_selection_used": "False",
        "model_selection_used": "False",
        "hyperparameter_sweep_used": "False",
        "candidate_creation": "False",
        "candidate_promotion": "False",
        "broker_submission": "False",
        "order_execution": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _float(value: object) -> float | None:
    try:
        text = str(value).strip()
        return None if text == "" else float(text)
    except ValueError:
        return None


def _target(row: dict[str, str]) -> int:
    return 1 if row.get("label") == "positive" else 0


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _fixed_feature_names(feature_rows: list[dict[str, str]]) -> list[str]:
    return sorted({row.get("formula_hash", "") for row in feature_rows if row.get("formula_hash")})


def _pivot_features(feature_rows: list[dict[str, str]], feature_names: list[str]) -> dict[tuple[str, str], dict[str, object]]:
    by_key: dict[tuple[str, str], dict[str, object]] = {}
    for row in feature_rows:
        formula_hash = row.get("formula_hash", "")
        if formula_hash not in feature_names:
            continue
        key = (row.get("symbol", ""), row.get("feature_date", ""))
        if not all(key):
            continue
        target = by_key.setdefault(
            key,
            {
                "symbol": key[0],
                "feature_date": key[1],
                "features": {},
                "feature_visible_at": row.get("feature_visible_at", ""),
                "feature_usable_from": row.get("feature_usable_from", ""),
            },
        )
        target["features"][formula_hash] = _float(row.get("feature_value"))
    return by_key


def _joined_rows(
    feature_rows: list[dict[str, str]],
    label_rows: list[dict[str, str]],
    feature_names: list[str],
    cutoff: date,
) -> list[dict[str, object]]:
    labels: dict[tuple[str, str], dict[str, str]] = {}
    for row in label_rows:
        feature_date = _parse_date(row.get("feature_date"))
        label_end = _parse_date(row.get("label_end_date"))
        if feature_date is None or label_end is None:
            continue
        if feature_date > cutoff or label_end > cutoff:
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
        labels[(row.get("symbol", ""), row.get("feature_date", ""))] = row

    pivots = _pivot_features(feature_rows, feature_names)
    joined: list[dict[str, object]] = []
    for key, pivot in pivots.items():
        label = labels.get(key)
        if not label:
            continue
        values = pivot["features"]
        if not isinstance(values, dict):
            continue
        joined.append(
            {
                "symbol": key[0],
                "feature_date": key[1],
                "label_end_date": label.get("label_end_date", ""),
                "label": label.get("label", ""),
                "label_return": label.get("label_return", ""),
                "features": {name: values.get(name) for name in feature_names},
            }
        )
    return sorted(joined, key=lambda row: (str(row["feature_date"]), str(row["symbol"])))


def _split_with_embargo(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    dates = sorted({str(row["feature_date"]) for row in rows})
    if len(dates) < 4:
        return rows, [], []
    validation_count = max(1, math.ceil(len(dates) * 0.2))
    validation_dates = set(dates[-validation_count:])
    embargo_dates = set(dates[-validation_count - 1 : -validation_count])
    train = [row for row in rows if str(row["feature_date"]) not in validation_dates | embargo_dates]
    validation = [row for row in rows if str(row["feature_date"]) in validation_dates]
    return train, validation, sorted(embargo_dates)


def _feature_stats(rows: list[dict[str, object]], feature_names: list[str]) -> dict[str, tuple[float, float]]:
    stats: dict[str, tuple[float, float]] = {}
    for name in feature_names:
        values = []
        for row in rows:
            features = row.get("features", {})
            if isinstance(features, dict) and features.get(name) is not None:
                values.append(float(features[name]))
        mean = sum(values) / len(values) if values else 0.0
        variance = sum((value - mean) ** 2 for value in values) / len(values) if values else 0.0
        stats[name] = (mean, math.sqrt(variance) or 1.0)
    return stats


def _vector(row: dict[str, object], feature_names: list[str], stats: dict[str, tuple[float, float]]) -> list[float]:
    values = [1.0]
    features = row.get("features", {})
    for name in feature_names:
        mean, std = stats[name]
        raw = features.get(name) if isinstance(features, dict) else None
        value = mean if raw is None else float(raw)
        values.append((value - mean) / std)
    return values


def _train_logistic(
    rows: list[dict[str, object]],
    feature_names: list[str],
    stats: dict[str, tuple[float, float]],
) -> list[float]:
    weights = [0.0] * (len(feature_names) + 1)
    learning_rate = 0.05
    epochs = 30
    for _ in range(epochs):
        for row in rows:
            x = _vector(row, feature_names, stats)
            prediction = _sigmoid(sum(weight * value for weight, value in zip(weights, x)))
            error = prediction - _target(row)  # type: ignore[arg-type]
            for index, value in enumerate(x):
                weights[index] -= learning_rate * error * value
    return weights


def _accuracy(
    rows: list[dict[str, object]],
    feature_names: list[str],
    stats: dict[str, tuple[float, float]],
    weights: list[float],
) -> float | None:
    if not rows:
        return None
    correct = 0
    for row in rows:
        x = _vector(row, feature_names, stats)
        prediction = 1 if _sigmoid(sum(weight * value for weight, value in zip(weights, x))) >= 0.5 else 0
        if prediction == _target(row):  # type: ignore[arg-type]
            correct += 1
    return correct / len(rows)


def _distribution(rows: list[dict[str, object]]) -> str:
    counts = Counter(str(row.get("label", "")) for row in rows)
    return ";".join(f"{key}={counts.get(key, 0)}" for key in ["positive", "negative"])


def build_ml_v2_fixed_spec_training_reports(
    *,
    feature_csv: Path | str = "data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv",
    label_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    readiness_csv: Path | str = "data/reports/ml_v2_fixed_spec_training_readiness_gate.csv",
) -> MlV2FixedSpecReports:
    feature_rows, feature_error = _read_csv(feature_csv)
    label_rows, label_error = _read_csv(label_csv)
    readiness_rows, readiness_error = _read_csv(readiness_csv)
    source_errors = [error for error in (feature_error, label_error, readiness_error) if error]

    gate_allows = any(
        row.get("gate_result") == "ALLOW_PAPER_ONLY_TRAINING"
        and row.get("paper_only_training_allowed_next") == "True"
        for row in readiness_rows
    )
    cutoff_text = next((row.get("train_cutoff", "") for row in label_rows if row.get("train_cutoff")), "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    feature_names = _fixed_feature_names(feature_rows)
    joined = _joined_rows(feature_rows, label_rows, feature_names, cutoff)
    train_rows, validation_rows, embargo_dates = _split_with_embargo(joined)
    stats = _feature_stats(train_rows, feature_names)
    weights = _train_logistic(train_rows, feature_names, stats) if train_rows and gate_allows and not source_errors else []
    train_accuracy = _accuracy(train_rows, feature_names, stats, weights) if weights else None
    validation_accuracy = _accuracy(validation_rows, feature_names, stats, weights) if weights else None
    status_ok = bool(weights) and bool(validation_rows)
    training_status = "paper_only_ml_v2_fixed_spec_trained" if status_ok else "paper_only_ml_v2_fixed_spec_blocked"
    validation_status = "paper_only_ml_v2_fixed_spec_validated" if status_ok else "paper_only_ml_v2_fixed_spec_validation_blocked"

    training_rows = [
        _row("summary", training_status, training_status, "One fixed-spec ML v2 paper-only model was trained; no selection, tuning, candidate, broker, order, or production work occurred.", "derived"),
        _row("source_files_present", "PASS" if not source_errors else "BLOCK", "all required local sources readable" if not source_errors else "; ".join(source_errors), "Uses existing local reports only.", f"{feature_csv};{label_csv};{readiness_csv}"),
        _row("readiness_gate", "PASS" if gate_allows else "BLOCK", "ALLOW_PAPER_ONLY_TRAINING" if gate_allows else "BLOCK", "Training requires the POST-21 fixed-spec readiness gate.", readiness_csv),
        _row("model_type", "PASS", "logistic_regression_sgd_fixed_v2", "Single fixed model type; no model comparison.", "data/reports/ml_v2_fixed_spec_training_protocol.csv"),
        _row("fixed_feature_set", "PASS" if len(feature_names) == 6 else "WARN", f"formula_hash_count={len(feature_names)}", "Uses the fixed Stage 1 formulaic OHLCV feature set only.", feature_csv),
        _row("joined_row_count", "PASS" if joined else "BLOCK", len(joined), "Rows joined by symbol and feature_date from local labels only.", f"{feature_csv};{label_csv}"),
        _row("train_row_count", "PASS" if train_rows else "BLOCK", len(train_rows), "Chronological training split before validation and embargo date groups.", "derived"),
        _row("validation_row_count", "PASS" if validation_rows else "BLOCK", len(validation_rows), "Chronological validation split; not an OOS rerun.", "derived"),
        _row("embargo_date_groups", "PASS" if embargo_dates else "WARN", ";".join(embargo_dates) if embargo_dates else "not_available", "One date group before validation is excluded from training.", "derived"),
        _row("label_distribution_train", "PASS" if train_rows else "BLOCK", _distribution(train_rows), "Binary positive/negative labels from existing local baseline label file.", label_csv),
        _row("train_accuracy", "PASS" if train_accuracy is not None else "WARN", _format_float(train_accuracy), "In-sample diagnostic only; not a production or candidate-selection claim.", "derived"),
        _row("model_artifact_written", "PASS", "False", "The trained weights are not written as a model artifact.", "derived"),
        _row("candidate_creation", "PASS", "False", "This run creates no candidate_id.", "derived"),
        _row("trading_allowed", "PASS", "False", "Paper-only research report.", "derived"),
        _row("production_effect", "PASS", "none", "No production effect.", "derived"),
    ]

    validation_rows_report = [
        _row("summary", validation_status, validation_status, "Fixed-spec ML v2 validation is pre-cutoff, local-only, and paper-only.", "derived"),
        _row("split_policy", "PASS", "date_group_chronological_train_then_validation_with_purge_embargo_v1", "Fixed split policy from POST-21; no random row split.", "data/reports/ml_v2_fixed_spec_training_protocol.csv"),
        _row("validation_accuracy", "PASS" if validation_accuracy is not None else "WARN", _format_float(validation_accuracy), "Pre-cutoff validation diagnostic only; no OOS rerun.", "derived"),
        _row("label_distribution_validation", "PASS" if validation_rows else "BLOCK", _distribution(validation_rows), "Validation labels are pre-cutoff only.", label_csv),
        _row("formula_selection_used", "PASS", "False", "All fixed feature hashes are used together; no formula ranking.", "derived"),
        _row("model_selection_used", "PASS", "False", "Only the fixed logistic SGD model is used.", "derived"),
        _row("hyperparameter_sweep_used", "PASS", "False", "No hyperparameter sweep or threshold tuning.", "derived"),
        _row("oos_rerun", "PASS", "False", "Validation is not an OOS rerun.", "derived"),
        _row("candidate_comparison_rerun", "PASS", "False", "No candidate comparison is run.", "derived"),
        _row("candidate_promotion", "PASS", "False", "No candidate promotion occurs.", "derived"),
        _row("broker_submission", "PASS", "False", "No broker submission.", "derived"),
        _row("order_execution", "PASS", "False", "No order execution.", "derived"),
        _row("trading_allowed", "PASS", "False", "Validation report only.", "derived"),
        _row("production_effect", "PASS", "none", "No production effect.", "derived"),
    ]
    markdown = _build_markdown(training_rows, validation_rows_report)
    return MlV2FixedSpecReports(training_rows, validation_rows_report, markdown)


def save_ml_v2_fixed_spec_training_reports(
    reports: MlV2FixedSpecReports,
    training_csv_output: Path | str,
    validation_csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _write_csv(reports.training_rows, training_csv_output)
    _write_csv(reports.validation_rows, validation_csv_output)
    path = Path(markdown_output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(reports.markdown, encoding="utf-8")


def _write_csv(rows: list[dict[str, str]], output: Path | str) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ML_V2_FIXED_SPEC_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _build_markdown(training_rows: list[dict[str, str]], validation_rows: list[dict[str, str]]) -> str:
    training_summary = training_rows[0] if training_rows else {}
    validation_summary = validation_rows[0] if validation_rows else {}
    lines = [
        "# ML v2 Fixed-Spec Paper-Only Training Report",
        "",
        "## Do Not Trade / Paper-Only ML v2",
        "",
        "This report runs one fixed-spec ML v2 experiment only after the POST-21 readiness gate. It does not evaluate multiple models, tune hyperparameters, rank formulas, create candidates, rerun OOS, rerun candidate comparison, write a production artifact, call broker APIs, submit orders, or authorize trading.",
        "",
        f"- Training status: `{training_summary.get('status', 'paper_only_ml_v2_fixed_spec_blocked')}`.",
        f"- Validation status: `{validation_summary.get('status', 'paper_only_ml_v2_fixed_spec_validation_blocked')}`.",
        "- Model type: `logistic_regression_sgd_fixed_v2`.",
        "- External features used: `False`.",
        "- Formula selection used: `False`.",
        "- Model selection used: `False`.",
        "- Hyperparameter sweep used: `False`.",
        "- Candidate creation: `False`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "",
        "## Training Rows",
        "",
        "| Metric | Status | Value | Reason | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in training_rows:
        lines.append(_markdown_row(row))
    lines.extend(["", "## Validation Rows", "", "| Metric | Status | Value | Reason | Source |", "| --- | --- | --- | --- | --- |"])
    for row in validation_rows:
        lines.append(_markdown_row(row))
    return "\n".join(lines) + "\n"


def _markdown_row(row: dict[str, str]) -> str:
    return "| {metric} | {status} | {value} | {reason} | {source} |".format(
        metric=row.get("metric", ""),
        status=row.get("status", ""),
        value=row.get("value", "").replace("|", "/"),
        reason=row.get("reason", "").replace("|", "/"),
        source=row.get("source", "").replace("|", "/"),
    )
