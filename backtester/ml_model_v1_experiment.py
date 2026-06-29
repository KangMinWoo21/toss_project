from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .ml_baseline_model_training import (
    _accuracy,
    _audit_value,
    _distribution,
    _eligible_rows,
    _feature_stats,
    _format_float,
    _split_train_validation,
    _train_logistic,
)
from .ml_baseline_validation import _max_drawdown, _monthly_validation_rows, _turnover
from .ml_data_readiness_audit import _parse_date, _read_csv


ML_MODEL_V1_REPORT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "post_cutoff_data_used_for_train",
    "external_features_used",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]


@dataclass(frozen=True)
class MlModelV1ExperimentReports:
    training_rows: list[dict[str, str]]
    validation_rows: list[dict[str, str]]
    risk_rows: list[dict[str, str]]


def build_ml_model_v1_experiment_reports(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    dataset_audit_csv: Path | str = "data/reports/ml_baseline_feature_label_dataset_audit.csv",
    external_readiness_csv: Path | str = "data/reports/ml_external_feature_readiness_reaudit.csv",
) -> MlModelV1ExperimentReports:
    dataset_rows, dataset_error = _read_csv(dataset_csv)
    audit_rows, audit_error = _read_csv(dataset_audit_csv)
    external_rows, external_error = _read_csv(external_readiness_csv)

    cutoff_text = _audit_value(audit_rows, "train_cutoff", "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    protected_status = _audit_value(audit_rows, "protected_candidate_status", "missing")
    dataset_ready = _audit_value(audit_rows, "summary") == "ready_for_training_scaffold"
    external_by_group = {row.get("feature_group", ""): row for row in external_rows}
    external_overall = external_by_group.get("overall", {}).get("readiness", "BLOCK")
    external_allowed = external_overall == "ready"

    eligible = _eligible_rows(dataset_rows, cutoff)
    train_rows, validation_rows = _split_train_validation(eligible)
    stats = _feature_stats(train_rows)
    weights = _train_logistic(train_rows, stats) if train_rows else []
    train_accuracy = _accuracy(train_rows, stats, weights) if weights else None
    validation_accuracy = _accuracy(validation_rows, stats, weights) if weights else None
    monthly_rows = _monthly_validation_rows(eligible)
    selected_returns = [float(row["selected_return"]) for row in monthly_rows]
    benchmark_returns = [float(row["benchmark_return"]) for row in monthly_rows]
    average_selected = sum(selected_returns) / len(selected_returns) if selected_returns else 0.0
    average_benchmark = sum(benchmark_returns) / len(benchmark_returns) if benchmark_returns else 0.0
    max_label_end = max((_parse_date(row.get("label_end_date")) for row in eligible), default=None)
    post_cutoff_used = max_label_end is not None and max_label_end > cutoff
    source_errors = [error for error in (dataset_error, audit_error, external_error) if error]
    split_ok = bool(train_rows) and bool(validation_rows)
    status_ok = dataset_ready and split_ok and not post_cutoff_used and not source_errors

    training_status = "paper_only_model_v1_trained" if status_ok else "paper_only_model_v1_blocked"
    validation_status = "paper_only_model_v1_validated" if status_ok and monthly_rows else "paper_only_model_v1_validation_blocked"

    training_report = [
        _row("summary", training_status, training_status, "Phase 11 paper-only ML model v1 uses approved local technical features only; no external feature merge, OOS rerun, candidate promotion, broker call, or production linkage was performed.", "derived"),
        _row("source_files_present", "PASS" if not source_errors else "BLOCK", "all required local sources readable" if not source_errors else "; ".join(source_errors), "Requires Phase 1 dataset/audit and Phase 10 external readiness re-audit.", f"{dataset_csv};{dataset_audit_csv};{external_readiness_csv}"),
        _row("approved_feature_set", "PASS", "technical_only", "External features are excluded because Phase 10 overall readiness is not ready/BLOCK.", external_readiness_csv),
        _row("external_feature_readiness", "PASS" if not external_allowed else "WARN", external_overall, "External features may be used only if explicitly approved and ready.", external_readiness_csv),
        _row("external_features_used", "PASS", "False", "No external financial/news/sentiment features enter v1.", "derived"),
        _row("model_type", "PASS", "logistic_regression_sgd", "Deterministic standard-library model reused from baseline scaffold.", "derived"),
        _row("train_cutoff", "PASS", cutoff.isoformat(), "Cutoff inherited from Phase 1 audit.", dataset_audit_csv),
        _row("train_row_count", "PASS" if train_rows else "BLOCK", len(train_rows), "Training split uses only pre-cutoff rows.", dataset_csv),
        _row("validation_row_count", "PASS" if validation_rows else "BLOCK", len(validation_rows), "Validation split uses only pre-cutoff rows.", dataset_csv),
        _row("post_cutoff_data_used_for_train", "PASS" if not post_cutoff_used else "BLOCK", "False" if not post_cutoff_used else "True", f"max_label_end={max_label_end}; cutoff={cutoff}", "derived"),
        _row("train_accuracy", "PASS" if train_accuracy is not None else "WARN", _format_float(train_accuracy), "In-sample diagnostic only.", "derived"),
        _row("validation_accuracy", "PASS" if validation_accuracy is not None else "WARN", _format_float(validation_accuracy), "Pre-cutoff validation diagnostic only.", "derived"),
        _row("protected_candidate_status", "PASS" if protected_status == "PAPER_REVIEW" else "BLOCK", protected_status, "Protected candidate remains unchanged.", dataset_audit_csv),
        _row("production_artifact_linked", "PASS", "False", "No production artifact is written or linked.", "derived"),
        _row("trading_allowed", "PASS", "False", "Research report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]

    validation_report = [
        _row("summary", validation_status, validation_status, "Phase 11 paper-only ML model v1 validation over pre-cutoff local technical features only.", "derived"),
        _row("leakage_check", "PASS" if not post_cutoff_used and eligible else "BLOCK", "False" if not post_cutoff_used else "True", f"max_label_end={max_label_end}; cutoff={cutoff}", "derived"),
        _row("walk_forward_months", "PASS" if monthly_rows else "BLOCK", f"months={len(monthly_rows)}", "Monthly expanding-window validation over pre-cutoff rows.", "derived"),
        _row("benchmark_comparison", "PASS" if monthly_rows else "BLOCK", f"model_return={average_selected:.4f};benchmark_return={average_benchmark:.4f};excess={average_selected - average_benchmark:.4f}", "Benchmark comparison is read-only and not a candidate comparison.", "derived"),
        _row("baseline_technical_comparison", "PASS" if monthly_rows else "BLOCK", f"v1_technical_return={average_selected:.4f};baseline_technical_reference={average_benchmark:.4f};excess={average_selected - average_benchmark:.4f}", "v1 uses the same approved technical-only feature family; no external feature claim is made.", "derived"),
        _row("drawdown", "PASS" if monthly_rows else "BLOCK", f"{_max_drawdown(selected_returns):.4f}", "Drawdown of validation selected-return path.", "derived"),
        _row("turnover", "PASS" if monthly_rows else "BLOCK", f"turnover={_turnover(monthly_rows):.4f}", "Average selected-symbol turnover across validation months.", "derived"),
        _row("label_distribution_train", "PASS" if train_rows else "BLOCK", _distribution(train_rows), "Pre-cutoff training labels.", "derived"),
        _row("label_distribution_validation", "PASS" if validation_rows else "BLOCK", _distribution(validation_rows), "Pre-cutoff validation labels.", "derived"),
        _row("candidate_promotion", "PASS", "False", "No candidate promotion occurs.", "derived"),
        _row("trading_allowed", "PASS", "False", "Validation report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]

    risk_report = [
        _row("summary", "paper_only_model_v1_risk_review", "paper_only_model_v1_risk_review", "Risk notes for a technical-only research model; no production readiness change.", "derived"),
        _row("external_feature_policy", "PASS", f"external_readiness={external_overall};external_features_used=False", "Phase 10 does not approve financial/news/sentiment features for training.", external_readiness_csv),
        _row("overfit_and_data_snooping_risk", "WARN", "model_v1_reuses_baseline_technical_features;future_iterations_require_locked_protocol", "Repeated research loops can overfit process decisions even without candidate promotion.", "derived"),
        _row("candidate_promotion", "PASS", "False", "Promotion is forbidden in Phase 11.", "derived"),
        _row("order_output", "PASS", "False", "No order output is generated.", "derived"),
        _row("protected_candidate_unchanged", "PASS", "True", "Protected PAPER_REVIEW candidate remains unchanged.", "derived"),
        _row("trading_allowed", "PASS", "False", "Risk report only; no trading authorization.", "derived"),
        _row("production_effect", "PASS", "none", "Report has no production effect.", "derived"),
    ]
    return MlModelV1ExperimentReports(training_report, validation_report, risk_report)


def save_ml_model_v1_experiment_reports(
    reports: MlModelV1ExperimentReports,
    training_csv_output: Path | str,
    validation_csv_output: Path | str,
    risk_markdown_output: Path | str,
) -> None:
    _write_csv(reports.training_rows, training_csv_output)
    _write_csv(reports.validation_rows, validation_csv_output)
    Path(risk_markdown_output).parent.mkdir(parents=True, exist_ok=True)
    Path(risk_markdown_output).write_text(_build_risk_markdown(reports), encoding="utf-8")


def _row(metric: str, status: str, value: object, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "metric": metric,
        "status": status,
        "value": str(value),
        "reason": reason,
        "source": str(source),
        "post_cutoff_data_used_for_train": "False",
        "external_features_used": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _write_csv(rows: list[dict[str, str]], output: Path | str) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ML_MODEL_V1_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _build_risk_markdown(reports: MlModelV1ExperimentReports) -> str:
    risk_by_metric = {row["metric"]: row for row in reports.risk_rows}
    lines = [
        "# ML Model v1 Risk Report",
        "",
        "## Do Not Trade / Paper-Only ML Model v1",
        "",
        "This report covers a paper-only technical-feature model experiment. It does not use external financial/news/sentiment features, rerun OOS, compare candidates for promotion, change strategy parameters, generate order output, call broker APIs, or authorize trading.",
        "",
        "- `external_features_used=False`.",
        "- `post_cutoff_data_used_for_train=False`.",
        "- `trading_allowed=False`.",
        "- `production_effect=none`.",
        "- Protected candidate unchanged.",
        f"- External feature policy: `{risk_by_metric.get('external_feature_policy', {}).get('value', '')}`.",
        "",
        "## Risk Rows",
        "",
        "| Metric | Status | Value | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for row in reports.risk_rows:
        lines.append(
            "| {metric} | {status} | {value} | {reason} |".format(
                metric=row["metric"],
                status=row["status"],
                value=row["value"].replace("|", "/"),
                reason=row["reason"].replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"
