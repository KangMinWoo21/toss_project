from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .ml_baseline_model_training import (
    _audit_value,
    _eligible_rows,
    _feature_stats,
    _sigmoid,
    _split_train_validation,
    _train_logistic,
    _vector,
)
from .ml_data_readiness_audit import _parse_date, _read_csv


ML_SHADOW_SCORING_COLUMNS = [
    "rank",
    "symbol",
    "feature_date",
    "score_type",
    "shadow_score",
    "score_bucket",
    "model_version",
    "source_model_report",
    "order_output",
    "broker_submission",
    "monthly_plan_regenerated",
    "candidate_promotion",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]


def build_ml_shadow_scoring_report(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    dataset_audit_csv: Path | str = "data/reports/ml_baseline_feature_label_dataset_audit.csv",
    model_v1_training_csv: Path | str = "data/reports/ml_model_v1_training_report.csv",
    max_rows: int = 50,
) -> list[dict[str, str]]:
    dataset_rows, dataset_error = _read_csv(dataset_csv)
    audit_rows, audit_error = _read_csv(dataset_audit_csv)
    model_rows, model_error = _read_csv(model_v1_training_csv)
    source_errors = [error for error in (dataset_error, audit_error, model_error) if error]
    if source_errors:
        return [_blocked_row("; ".join(source_errors), model_v1_training_csv)]

    cutoff_text = _audit_value(audit_rows, "train_cutoff", "2026-06-18")
    cutoff = _parse_date(cutoff_text) or date(2026, 6, 18)
    model_status = _audit_value(model_rows, "summary", "missing")
    external_used = _audit_value(model_rows, "external_features_used", "True")
    protected_status = _audit_value(audit_rows, "protected_candidate_status", "missing")
    eligible = _eligible_rows(dataset_rows, cutoff)
    train_rows, _ = _split_train_validation(eligible)
    if model_status != "paper_only_model_v1_trained" or external_used != "False" or protected_status != "PAPER_REVIEW" or not train_rows:
        return [_blocked_row(f"model_status={model_status}; external_features_used={external_used}; protected={protected_status}", model_v1_training_csv)]

    latest_feature_date = max((row["feature_date"] for row in eligible), default="")
    score_candidates = [row for row in eligible if row.get("feature_date") == latest_feature_date]
    stats = _feature_stats(train_rows)
    weights = _train_logistic(train_rows, stats)
    scored = []
    for row in score_candidates:
        score = _sigmoid(sum(weight * value for weight, value in zip(weights, _vector(row, stats))))
        scored.append((score, row))
    scored.sort(key=lambda item: (item[0], item[1].get("symbol", "")), reverse=True)
    limit = max(1, max_rows)
    rows: list[dict[str, str]] = []
    for rank, (score, row) in enumerate(scored[:limit], start=1):
        rows.append(
            {
                "rank": str(rank),
                "symbol": row.get("symbol", ""),
                "feature_date": row.get("feature_date", ""),
                "score_type": "technical_only_shadow_score",
                "shadow_score": f"{score:.6f}",
                "score_bucket": _bucket(score),
                "model_version": "ml_model_v1_technical_only",
                "source_model_report": str(model_v1_training_csv),
                "order_output": "False",
                "broker_submission": "False",
                "monthly_plan_regenerated": "False",
                "candidate_promotion": "False",
                "trading_allowed": "False",
                "production_effect": "none",
                "protected_candidate_unchanged": "True",
            }
        )
    return rows or [_blocked_row("no eligible shadow scoring rows", model_v1_training_csv)]


def save_ml_shadow_scoring_report(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ML_SHADOW_SCORING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_markdown(rows), encoding="utf-8")


def _bucket(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def _blocked_row(reason: str, source: Path | str) -> dict[str, str]:
    return {
        "rank": "1",
        "symbol": "BLOCKED",
        "feature_date": "",
        "score_type": "technical_only_shadow_score_blocked",
        "shadow_score": "0.000000",
        "score_bucket": reason,
        "model_version": "ml_model_v1_technical_only",
        "source_model_report": str(source),
        "order_output": "False",
        "broker_submission": "False",
        "monthly_plan_regenerated": "False",
        "candidate_promotion": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("shadow scoring report is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in ML_SHADOW_SCORING_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"shadow scoring row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("order_output", "False"),
            ("broker_submission", "False"),
            ("monthly_plan_regenerated", "False"),
            ("candidate_promotion", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("protected_candidate_unchanged", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"shadow scoring row {index} {column}={row[column]} expected {expected}")


def _build_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# ML Shadow Scoring Report",
        "",
        "## Do Not Trade / Shadow Scoring Only",
        "",
        "This report applies paper-only ML model v1 scores as human-readable shadow scores. It does not generate order output, submit to a broker, regenerate the monthly plan, promote candidates, change strategy parameters, call broker APIs, or authorize trading.",
        "",
        "- No order output.",
        "- No broker submission.",
        "- Monthly plan regenerated: `False`.",
        "- Candidate promotion: `False`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "- Protected candidate unchanged.",
        "",
        "## Score Rows",
        "",
        "| Rank | Symbol | Feature Date | Score | Bucket |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['symbol']} | {row['feature_date']} | {row['shadow_score']} | {row['score_bucket']} |"
        )
    return "\n".join(lines) + "\n"
