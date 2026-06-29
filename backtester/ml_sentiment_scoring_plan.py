from __future__ import annotations

import csv
from pathlib import Path


SENTIMENT_PLAN_COLUMNS = [
    "component",
    "source_name",
    "model_version",
    "candidate_features",
    "schema_fields",
    "timestamp_fields",
    "sentiment_score_range",
    "lineage_rule",
    "fetch_allowed_now",
    "training_allowed_now",
    "model_training_allowed",
    "feature_added_to_training",
    "trading_allowed",
    "production_effect",
    "pit_required",
    "usable_from_required",
    "llm_risk_note",
    "leakage_risk",
    "data_quality_risk",
    "current_status",
    "next_safe_action",
]


def _row(
    *,
    component: str,
    source_name: str,
    model_version: str,
    candidate_features: list[str],
    schema_fields: list[str],
    timestamp_fields: list[str],
    sentiment_score_range: str,
    lineage_rule: str,
    llm_risk_note: str,
    leakage_risk: str,
    data_quality_risk: str,
    next_safe_action: str,
) -> dict[str, str]:
    return {
        "component": component,
        "source_name": source_name,
        "model_version": model_version,
        "candidate_features": ";".join(candidate_features),
        "schema_fields": ";".join(schema_fields),
        "timestamp_fields": ";".join(timestamp_fields),
        "sentiment_score_range": sentiment_score_range,
        "lineage_rule": lineage_rule,
        "fetch_allowed_now": "False",
        "training_allowed_now": "False",
        "model_training_allowed": "False",
        "feature_added_to_training": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "pit_required": "True",
        "usable_from_required": "True",
        "llm_risk_note": llm_risk_note,
        "leakage_risk": leakage_risk,
        "data_quality_risk": data_quality_risk,
        "current_status": "schema_plan_only",
        "next_safe_action": next_safe_action,
    }


def build_ml_sentiment_scoring_plan() -> list[dict[str, str]]:
    common_timestamps = ["published_at", "collected_at", "visible_at", "scored_at", "usable_from"]
    return [
        _row(
            component="lexicon_scoring",
            source_name="news_events_schema_rows",
            model_version="rule_lexicon_v1",
            candidate_features=[
                "sentiment_score",
                "sentiment_label",
                "positive_keyword_count",
                "negative_keyword_count",
                "importance_score",
            ],
            schema_fields=[
                "news_event_id",
                "text_hash",
                "model_version",
                "positive_terms",
                "negative_terms",
                "sentiment_score",
                "sentiment_label",
                "importance_score",
            ],
            timestamp_fields=common_timestamps,
            sentiment_score_range="-1.0_to_1.0",
            lineage_rule="score only timestamped news rows from Phase 8 schema; retain model_version and text_hash lineage",
            llm_risk_note="No FinBERT or LLM scoring in Phase 9; rule_lexicon_v1 only.",
            leakage_risk="medium_if_scored_with_revised_text_or_future_event_labels",
            data_quality_risk="Korean finance vocabulary gaps, negation handling, title/body mismatch, keyword overfitting",
            next_safe_action="Review lexicon categories only; do not score live news or add sentiment to training.",
        ),
        _row(
            component="monthly_aggregation",
            source_name="derived_sentiment_monthly_features",
            model_version="rule_lexicon_v1",
            candidate_features=[
                "sentiment_count_1m",
                "negative_sentiment_share_1m",
                "mean_sentiment_score_1m",
                "max_negative_importance_1m",
            ],
            schema_fields=[
                "symbol",
                "feature_date",
                "model_version",
                "sentiment_count_1m",
                "negative_sentiment_share_1m",
                "mean_sentiment_score_1m",
                "usable_from",
            ],
            timestamp_fields=common_timestamps + ["feature_generated_at"],
            sentiment_score_range="-1.0_to_1.0_aggregated",
            lineage_rule="aggregate only scored rows where usable_from <= feature_date; keep provider and text_hash audit trail",
            llm_risk_note="No LLM-generated labels or summaries may enter aggregation in Phase 9.",
            leakage_risk="high_if_any_scored_at_or_usable_from_is_after_feature_date",
            data_quality_risk="sparse article counts, source coverage skew, duplicate clusters, symbol ambiguity",
            next_safe_action="Use aggregation contract only for readiness review; keep feature_added_to_training=False.",
        ),
        _row(
            component="pit_controls",
            source_name="derived_sentiment_pit_controls",
            model_version="rule_lexicon_v1",
            candidate_features=[
                "sentiment_observation_id",
                "source_revision",
                "quality_status",
                "excluded_reason",
            ],
            schema_fields=[
                "sentiment_observation_id",
                "news_event_id",
                "text_hash",
                "source_revision",
                "feature_date",
                "scored_at",
                "usable_from",
                "quality_status",
                "excluded_reason",
            ],
            timestamp_fields=common_timestamps + ["feature_generated_at"],
            sentiment_score_range="not_applicable_controls",
            lineage_rule="sentiment rows become research-eligible only when scored_at and usable_from are on or before feature_date",
            llm_risk_note="Block uncontrolled LLM outputs, prompt revisions, or regenerated scores without versioned lineage.",
            leakage_risk="block_if_scored_at_or_usable_from_after_feature_date",
            data_quality_risk="timezone ambiguity, duplicate text_hash lineage gaps, scorer version drift",
            next_safe_action="Use these controls in Phase 10 external feature readiness re-audit.",
        ),
        _row(
            component="later_stage_models",
            source_name="FinBERT/LLM later-stage only",
            model_version="later_stage_not_ready",
            candidate_features=[
                "finbert_sentiment_score",
                "llm_sentiment_label",
                "llm_importance_reason",
            ],
            schema_fields=[
                "model_version",
                "prompt_version",
                "scored_at",
                "usable_from",
                "input_text_hash",
                "output_hash",
                "human_review_status",
            ],
            timestamp_fields=common_timestamps + ["model_released_at", "prompt_approved_at"],
            sentiment_score_range="not_defined_for_phase_9",
            lineage_rule="later-stage models require separate approval, versioned prompts/models, and human review before any research use",
            llm_risk_note="FinBERT and LLM sentiment are later-stage only due to hallucination, prompt drift, vendor changes, and non-deterministic outputs.",
            leakage_risk="high_without_model_version_prompt_version_and_visible_at_controls",
            data_quality_risk="hallucination, Korean finance context errors, prompt drift, non-determinism, vendor model changes",
            next_safe_action="Keep FinBERT/LLM as later-stage; do not train, score, or merge in this phase.",
        ),
    ]


def _validate_rows(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [column for column in SENTIMENT_PLAN_COLUMNS if not row.get(column)]
        if missing:
            raise ValueError(f"sentiment plan row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("fetch_allowed_now", "False"),
            ("training_allowed_now", "False"),
            ("model_training_allowed", "False"),
            ("feature_added_to_training", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("pit_required", "True"),
            ("usable_from_required", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"sentiment plan row {index} {column}={row[column]} expected {expected}")
        for field in ("published_at", "collected_at", "visible_at", "scored_at", "usable_from"):
            if field not in row["timestamp_fields"]:
                raise ValueError(f"sentiment plan row {index} missing timestamp field {field}")
        if "LLM" not in row["llm_risk_note"] and "FinBERT" not in row["llm_risk_note"]:
            raise ValueError(f"sentiment plan row {index} missing LLM/FinBERT risk note")


def save_ml_sentiment_scoring_plan(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SENTIMENT_PLAN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# ML Sentiment Scoring Plan",
        "",
        "## Do Not Trade / Sentiment Plan Only",
        "",
        "This report is a paper-only rule/lexicon sentiment scoring plan. It does not fetch news, call APIs, run FinBERT or LLM scoring, train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        "- `model_version=rule_lexicon_v1` for the initial scoring contract.",
        "- `sentiment_score` range is `-1.0_to_1.0` for row-level lexicon scoring.",
        "- `fetch_allowed_now=False` for every row.",
        "- `training_allowed_now=False` for every row.",
        "- `feature_added_to_training=False` for every row.",
        "- `trading_allowed=False` for every row.",
        "- `production_effect=none` for every row.",
        "- Required PIT timestamps include `published_at`, `collected_at`, `visible_at`, `scored_at`, and `usable_from`.",
        "- FinBERT and LLM sentiment remain later-stage only because of hallucination, prompt drift, and non-determinism risk.",
        "",
        "## Plan Rows",
        "",
        "| Component | Model Version | Candidate Features | Timestamp Fields | Score Range | LLM Risk Note | Next Safe Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {component} | {model_version} | {candidate_features} | {timestamp_fields} | {sentiment_score_range} | {llm_risk_note} | {next_safe_action} |".format(
                component=row["component"],
                model_version=row["model_version"],
                candidate_features=row["candidate_features"].replace("|", "/"),
                timestamp_fields=row["timestamp_fields"].replace("|", "/"),
                sentiment_score_range=row["sentiment_score_range"],
                llm_risk_note=row["llm_risk_note"].replace("|", "/"),
                next_safe_action=row["next_safe_action"].replace("|", "/"),
            )
        )
    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
