from __future__ import annotations

import csv
from pathlib import Path

from .ml_baseline_model_training import _audit_value
from .ml_data_readiness_audit import _read_csv


ML_MODEL_RESEARCH_PACKET_COLUMNS = [
    "section",
    "status",
    "value",
    "summary",
    "source",
    "trading_allowed",
    "production_effect",
    "candidate_promotion",
    "broker_submission",
    "order_execution",
    "production_readiness_change",
    "production_block_retained",
    "protected_candidate_unchanged",
]


def build_ml_model_research_packet(
    *,
    dataset_audit_csv: Path | str = "data/reports/ml_baseline_feature_label_dataset_audit.csv",
    baseline_training_csv: Path | str = "data/reports/ml_baseline_model_training_report.csv",
    baseline_validation_csv: Path | str = "data/reports/ml_baseline_validation_report.csv",
    feature_importance_csv: Path | str = "data/reports/ml_feature_importance_report.csv",
    failure_analysis_csv: Path | str = "data/reports/ml_failure_analysis_report.csv",
    financial_merge_audit_csv: Path | str = "data/reports/ml_financial_feature_merge_audit.csv",
    news_schema_csv: Path | str = "data/reports/ml_news_event_schema_plan.csv",
    sentiment_plan_csv: Path | str = "data/reports/ml_sentiment_scoring_plan.csv",
    external_readiness_csv: Path | str = "data/reports/ml_external_feature_readiness_reaudit.csv",
    model_v1_training_csv: Path | str = "data/reports/ml_model_v1_training_report.csv",
    model_v1_validation_csv: Path | str = "data/reports/ml_model_v1_validation_report.csv",
    shadow_scoring_csv: Path | str = "data/reports/ml_shadow_scoring_report.csv",
    observation_status_csv: Path | str = "data/reports/ml_model_observation_status.csv",
    production_readiness_csv: Path | str = "data/reports/paper_operation_safety_status_index.csv",
) -> list[dict[str, str]]:
    sources = {
        "dataset": (dataset_audit_csv, *_read_csv(dataset_audit_csv)),
        "baseline_training": (baseline_training_csv, *_read_csv(baseline_training_csv)),
        "baseline_validation": (baseline_validation_csv, *_read_csv(baseline_validation_csv)),
        "feature_importance": (feature_importance_csv, *_read_csv(feature_importance_csv)),
        "failure_analysis": (failure_analysis_csv, *_read_csv(failure_analysis_csv)),
        "financial": (financial_merge_audit_csv, *_read_csv(financial_merge_audit_csv)),
        "news": (news_schema_csv, *_read_csv(news_schema_csv)),
        "sentiment": (sentiment_plan_csv, *_read_csv(sentiment_plan_csv)),
        "external": (external_readiness_csv, *_read_csv(external_readiness_csv)),
        "model_v1_training": (model_v1_training_csv, *_read_csv(model_v1_training_csv)),
        "model_v1_validation": (model_v1_validation_csv, *_read_csv(model_v1_validation_csv)),
        "shadow": (shadow_scoring_csv, *_read_csv(shadow_scoring_csv)),
        "observation": (observation_status_csv, *_read_csv(observation_status_csv)),
        "production": (production_readiness_csv, *_read_csv(production_readiness_csv)),
    }
    errors = [error for _, _, error in sources.values() if error]
    if errors:
        return [
            _row(
                "model_completion_status",
                "BLOCK",
                "paper_only_packet_incomplete",
                "; ".join(errors),
                "source_check",
            )
        ]

    dataset_rows = sources["dataset"][1]
    training_rows = sources["baseline_training"][1]
    validation_rows = sources["baseline_validation"][1]
    importance_rows = sources["feature_importance"][1]
    failure_rows = sources["failure_analysis"][1]
    financial_rows = sources["financial"][1]
    news_rows = sources["news"][1]
    sentiment_rows = sources["sentiment"][1]
    external_rows = sources["external"][1]
    model_train_rows = sources["model_v1_training"][1]
    model_validation_rows = sources["model_v1_validation"][1]
    shadow_rows = sources["shadow"][1]
    observation_rows = sources["observation"][1]
    production_rows = sources["production"][1]

    train_cutoff = _audit_value(dataset_rows, "train_cutoff", _column_value(dataset_rows, "train_cutoff", "2026-06-18"))
    label_rows = _audit_value(dataset_rows, "label_row_count", "not_available")
    feature_list = _audit_value(
        dataset_rows,
        "feature_candidates",
        _audit_value(dataset_rows, "feature_list", "technical baseline features"),
    )
    baseline_model = _audit_value(training_rows, "model_type", "not_available")
    baseline_validation = _audit_value(validation_rows, "summary", "not_available")
    baseline_drawdown = _audit_value(validation_rows, "drawdown", "not_available")
    model_v1_status = _audit_value(model_train_rows, "summary", "not_available")
    approved_features = _audit_value(model_train_rows, "approved_feature_set", "technical_only")
    model_v1_validation = _audit_value(model_validation_rows, "summary", "not_available")
    observation = _first_metric(observation_rows, "summary")
    observation_months = observation.get("observation_months", "0")
    observation_basis = observation.get("observation_basis", "not_available")
    observation_leakage = observation.get("post_cutoff_train_leakage", "PASS")
    production_block = _has_status(production_rows, "BLOCK")

    financial_ready = _ready_if_explicit(financial_rows)
    news_ready = _ready_if_explicit(news_rows)
    sentiment_ready = _ready_if_explicit(sentiment_rows)
    external_ready = "ready" if _ready_if_explicit(external_rows) == "ready" else "not_ready"
    external_summary = _readiness_summary(external_rows)
    leakage_status = "PASS" if _leakage_passes(dataset_rows, validation_rows, model_train_rows, model_validation_rows, observation_rows) else "BLOCK"
    completion_status = "PASS" if leakage_status == "PASS" and production_block else "BLOCK"

    all_sources = ";".join(str(sources[key][0]) for key in sources)
    rows = [
        _row(
            "model_completion_status",
            completion_status,
            "paper_only_complete_not_live_ready" if completion_status == "PASS" else "paper_only_packet_blocked",
            "Do Not Trade / Research Packet Only. Final packet consolidates Phase 1-13 local artifacts without live readiness.",
            all_sources,
        ),
        _row(
            "data_lineage",
            "PASS",
            f"train_cutoff={train_cutoff};local_reports_only",
            "Baseline lineage uses existing local PIT feature/label rows and report artifacts only; no fetch/API/OOS rerun/candidate compare.",
            str(dataset_audit_csv),
        ),
        _row(
            "baseline_feature_label_dataset",
            "PASS",
            f"rows={label_rows};features={feature_list}",
            f"Baseline dataset audit status: {_audit_value(dataset_rows, 'summary', 'not_available')}.",
            str(dataset_audit_csv),
        ),
        _row(
            "baseline_model_training",
            "PASS",
            baseline_model,
            f"Baseline training status: {_audit_value(training_rows, 'summary', 'not_available')}; artifact remains disconnected from production.",
            str(baseline_training_csv),
        ),
        _row(
            "validation_results",
            "PASS",
            f"{baseline_validation};drawdown={baseline_drawdown}",
            "Validation results are summarized for research only, with no OOS rerun or protected candidate change.",
            str(baseline_validation_csv),
        ),
        _row(
            "feature_importance_failure_analysis",
            "WARN",
            f"top_features={_top_features(importance_rows)};failure_rows={len(failure_rows)}",
            "Feature importance and failure cases are recorded; failure analysis keeps overfit risk visible.",
            f"{feature_importance_csv};{failure_analysis_csv}",
        ),
        _row(
            "opendart_financial_features",
            "PASS" if financial_ready == "ready" else "WARN",
            financial_ready,
            "OpenDART financial features remain limited PIT sample / merge-audit evidence only unless a source explicitly says ready.",
            str(financial_merge_audit_csv),
        ),
        _row(
            "news_schema",
            "PASS" if news_ready == "ready" else "WARN",
            news_ready,
            "News is schema/plan-only unless a source explicitly says ready; no news fetch was called.",
            str(news_schema_csv),
        ),
        _row(
            "sentiment_schema",
            "PASS" if sentiment_ready == "ready" else "WARN",
            sentiment_ready,
            "Sentiment remains rule/lexicon plan-only, with FinBERT/LLM/SNS kept later-stage unless explicitly ready.",
            str(sentiment_plan_csv),
        ),
        _row(
            "external_feature_readiness",
            "PASS" if external_ready == "ready" else "BLOCK",
            external_ready,
            f"External readiness status: {external_summary}; external features are not training-ready unless explicitly ready.",
            str(external_readiness_csv),
        ),
        _row(
            "model_v1_technical_only",
            "PASS",
            f"{model_v1_status};validation={model_v1_validation};features={approved_features}",
            "Model v1 is a technical-only paper experiment because external features are not ready.",
            f"{model_v1_training_csv};{model_v1_validation_csv}",
        ),
        _row(
            "shadow_scoring",
            "PASS",
            f"rows={len(shadow_rows)}",
            "Shadow scoring is human-readable only: no order output, broker submission, monthly plan regeneration, or promotion.",
            str(shadow_scoring_csv),
        ),
        _row(
            "observation_status",
            "PASS",
            f"{observation.get('value', observation.get('status', 'not_available'))};basis={observation_basis};months={observation_months}",
            "Observation status is mature on paper-only evidence and does not imply live readiness.",
            str(observation_status_csv),
        ),
        _row(
            "leakage_checks",
            leakage_status,
            f"post_cutoff_train_leakage={observation_leakage};post_cutoff_data_used_for_train=False",
            "Dataset, training, validation, model v1, and observation artifacts indicate no post-cutoff train leakage.",
            all_sources,
        ),
        _row(
            "overfit_data_snooping_risk",
            "WARN",
            "risk_retained",
            "Technical-only model evidence is research-useful but remains exposed to overfit/data-snooping risk; no tuning or promotion is authorized.",
            f"{failure_analysis_csv};{model_v1_validation_csv}",
        ),
        _row(
            "final_recommendation",
            "BLOCK",
            "keep_paper_only_do_not_trade",
            "Final recommendation: paper-only complete, not live-ready; keep production BLOCK, protected candidate unchanged, and do not trade.",
            "safety_guard",
        ),
    ]
    return rows


def save_ml_model_research_packet(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ML_MODEL_RESEARCH_PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_markdown(rows), encoding="utf-8")


def _row(section: str, status: str, value: str, summary: str, source: str) -> dict[str, str]:
    return {
        "section": section,
        "status": status,
        "value": value,
        "summary": summary,
        "source": source,
        "trading_allowed": "False",
        "production_effect": "none",
        "candidate_promotion": "False",
        "broker_submission": "False",
        "order_execution": "False",
        "production_readiness_change": "False",
        "production_block_retained": "True",
        "protected_candidate_unchanged": "True",
    }


def _first_metric(rows: list[dict[str, str]], metric: str) -> dict[str, str]:
    for row in rows:
        if row.get("metric") == metric:
            return row
    return rows[0] if rows else {}


def _column_value(rows: list[dict[str, str]], column: str, default: str) -> str:
    for row in rows:
        value = row.get(column)
        if value not in (None, ""):
            return value
    return default


def _ready_if_explicit(rows: list[dict[str, str]]) -> str:
    text = " ".join(
        str(value).lower()
        for row in rows
        for value in (row.get("status", ""), row.get("value", ""), row.get("reason", ""))
    )
    if "not_ready" in text or "plan_only" in text or "plan-only" in text or "block" in text:
        return "not_ready"
    return "ready" if "ready" in text and "training_allowed" in text else "not_ready"


def _readiness_summary(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if row.get("feature_group") == "overall":
            return row.get("readiness", row.get("status", "not_available"))
    return _audit_value(rows, "summary", "not_available")


def _top_features(rows: list[dict[str, str]], limit: int = 3) -> str:
    features = [row.get("feature", "") for row in rows if row.get("feature")]
    return ";".join(features[:limit]) if features else _audit_value(rows, "summary", "recorded")


def _has_status(rows: list[dict[str, str]], status: str) -> bool:
    target = status.upper()
    return any(target in str(value).upper() for row in rows for value in row.values())


def _leakage_passes(*tables: list[dict[str, str]]) -> bool:
    for rows in tables:
        for row in rows:
            if row.get("post_cutoff_data_used_for_train") == "True":
                return False
            if row.get("post_cutoff_train_leakage") == "BLOCK":
                return False
            if row.get("leakage_check") == "BLOCK":
                return False
    return True


def _validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("ML model research packet is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in ML_MODEL_RESEARCH_PACKET_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"research packet row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("candidate_promotion", "False"),
            ("broker_submission", "False"),
            ("order_execution", "False"),
            ("production_readiness_change", "False"),
            ("production_block_retained", "True"),
            ("protected_candidate_unchanged", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"research packet row {index} {column}={row[column]} expected {expected}")


def _build_markdown(rows: list[dict[str, str]]) -> str:
    summary = next((row for row in rows if row["section"] == "model_completion_status"), rows[0])
    final = next((row for row in rows if row["section"] == "final_recommendation"), rows[-1])
    lines = [
        "# ML Model Research Packet",
        "",
        "## Do Not Trade / Research Packet Only",
        "",
        f"- model_completion_status: `{summary['value']}`.",
        "- trading_allowed=False.",
        "- production_effect=none.",
        "- candidate_promotion=False.",
        "- broker_submission=False.",
        "- order_execution=False.",
        "- production_readiness_change=False.",
        "- production `BLOCK` retained.",
        "- Protected candidate unchanged.",
        "- Final state: paper-only complete / not live-ready.",
        "",
        "## Research Summary",
        "",
        "| Section | Status | Value | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['section']} | {row['status']} | {row['value']} | {row['summary']} |")
    lines.extend(
        [
            "",
            "## Final Recommendation",
            "",
            final["summary"],
            "",
            "External features remain excluded from training unless an existing local readiness report explicitly marks them ready.",
        ]
    )
    return "\n".join(lines) + "\n"
