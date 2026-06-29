from __future__ import annotations

import csv
from pathlib import Path


PLAN_COLUMNS = [
    "source_group",
    "source_name",
    "candidate_features",
    "expected_use",
    "priority",
    "api_key_required",
    "fetch_allowed_now",
    "training_allowed_now",
    "production_effect",
    "trading_allowed",
    "pit_required",
    "usable_from_required",
    "timestamp_fields",
    "leakage_risk",
    "data_quality_risk",
    "current_status",
    "next_safe_action",
]

OVERALL_CONCLUSION = "PLAN_ONLY_NOT_READY_FOR_TRAINING"


def _plan_row(
    *,
    source_group: str,
    source_name: str,
    candidate_features: list[str],
    expected_use: str,
    priority: str,
    api_key_required: str,
    timestamp_fields: list[str],
    leakage_risk: str,
    data_quality_risk: str,
    current_status: str,
    next_safe_action: str,
) -> dict[str, str]:
    return {
        "source_group": source_group,
        "source_name": source_name,
        "candidate_features": ";".join(candidate_features),
        "expected_use": expected_use,
        "priority": priority,
        "api_key_required": api_key_required,
        "fetch_allowed_now": "False",
        "training_allowed_now": "False",
        "production_effect": "none",
        "trading_allowed": "False",
        "pit_required": "True",
        "usable_from_required": "True",
        "timestamp_fields": ";".join(timestamp_fields),
        "leakage_risk": leakage_risk,
        "data_quality_risk": data_quality_risk,
        "current_status": current_status,
        "next_safe_action": next_safe_action,
    }


def build_ml_external_feature_readiness_plan() -> list[dict[str, str]]:
    return [
        _plan_row(
            source_group="OpenDART financial_disclosure",
            source_name="opendart_financial_statements;opendart_disclosures",
            candidate_features=[
                "sales",
                "operating_income",
                "net_income",
                "debt_ratio",
                "roe",
                "per",
                "pbr",
                "filing_event_type",
                "correction_filing_flag",
            ],
            expected_use="PIT-safe monthly ranking features and disclosure risk flags after schema validation only.",
            priority="high",
            api_key_required="True",
            timestamp_fields=[
                "fiscal_period",
                "report_period_end",
                "receipt_date",
                "receipt_time",
                "correction_filing",
                "collected_at",
                "usable_from",
            ],
            leakage_risk="high_without_usable_from_and_correction_handling",
            data_quality_risk="restatements, missing filings, consolidated/separate statement mismatch, fiscal-period alignment, PER/PBR market-date alignment",
            current_status="planned_high_priority",
            next_safe_action="Define append-only OpenDART schema with usable_from, correction filing lineage, and PIT validation; do not fetch in this loop.",
        ),
        _plan_row(
            source_group="news_events",
            source_name="naver_news_search_api;gdelt;manual_news_calendar",
            candidate_features=[
                "event_count_1m",
                "negative_event_count_1m",
                "source_coverage_count",
                "text_hash",
                "event_type",
                "symbol_event_flag",
            ],
            expected_use="Secondary event-risk features or manual review flags after financial schema is stable.",
            priority="medium",
            api_key_required="mixed",
            timestamp_fields=[
                "published_at",
                "collected_at",
                "visible_at",
                "usable_from",
                "source_id",
                "text_hash",
            ],
            leakage_risk="medium_high_if_published_or_visible_times_are_missing",
            data_quality_risk="duplicate articles, syndicated copies, symbol ambiguity, delayed indexing, headline edits, source coverage bias",
            current_status="planned_after_financials",
            next_safe_action="Draft PIT-safe news_events schema and deterministic text_hash de-dup rules after OpenDART plan is accepted; no API calls now.",
        ),
        _plan_row(
            source_group="sentiment",
            source_name="rule_lexicon_v1;FinBERT/LLM later-stage",
            candidate_features=[
                "model_version",
                "sentiment_score",
                "importance_score",
                "sentiment_count_1m",
                "negative_sentiment_share_1m",
            ],
            expected_use="Start with simple rule/lexicon scores on timestamped news rows; defer FinBERT/LLM sentiment.",
            priority="medium-low",
            api_key_required="False",
            timestamp_fields=[
                "published_at",
                "collected_at",
                "visible_at",
                "usable_from",
                "model_version",
                "scored_at",
            ],
            leakage_risk="medium_if_scored_with_future_text_or_revised_labels",
            data_quality_risk="Korean finance vocabulary coverage, negation handling, title/body mismatch, model drift, low article counts",
            current_status="planned_after_news_schema",
            next_safe_action="Plan lexicon_v1 scoring contract only after news schema has text_hash and usable_from; keep FinBERT/LLM later-stage.",
        ),
        _plan_row(
            source_group="sns_community",
            source_name="sns_community_later_stage",
            candidate_features=[
                "community_mention_count",
                "community_sentiment_score",
                "spam_score",
                "duplicate_cluster_id",
                "manipulation_risk_flag",
            ],
            expected_use="Later-stage monitoring research only, not baseline ML ranking input.",
            priority="later-stage",
            api_key_required="unknown",
            timestamp_fields=[
                "posted_at",
                "collected_at",
                "visible_at",
                "usable_from",
                "account_id_hash",
                "text_hash",
            ],
            leakage_risk="high_due_to_timestamp_visibility_and_deleted_or_edited_posts",
            data_quality_risk="spam, duplicates, coordinated manipulation, timestamp uncertainty, survivorship from deleted posts, platform policy drift",
            current_status="later_stage_not_ready",
            next_safe_action="Keep out of baseline ML until spam, duplication, manipulation, and timestamp controls are designed and reviewed.",
        ),
    ]


def _validate_rows(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [column for column in PLAN_COLUMNS if column not in row or str(row[column]).strip() == ""]
        if missing:
            raise ValueError(f"plan row {index} missing required columns: {','.join(missing)}")
        for column, expected in (
            ("fetch_allowed_now", "False"),
            ("training_allowed_now", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("pit_required", "True"),
            ("usable_from_required", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"plan row {index} has {column}={row[column]} expected {expected}")


def save_ml_external_feature_readiness_plan(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# ML External Feature Readiness Plan",
        "",
        "## Do Not Trade / Plan Only",
        "",
        "This report is a plan-only artifact. It does not fetch data, call APIs, train models, rerun OOS, compare candidates, create candidates, regenerate monthly plans, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        f"- Overall conclusion: `{OVERALL_CONCLUSION}`.",
        "- `fetch_allowed_now=False` for every row.",
        "- `training_allowed_now=False` for every row.",
        "- `trading_allowed=False` for every row.",
        "- `production_effect=none` for every row.",
        "- PIT-safe `usable_from` and source timestamps are required before any future training dataset can be built.",
        "",
        "## Plan Rows",
        "",
        "| Source Group | Source Name | Priority | Status | Candidate Features | Timestamp Fields | Next Safe Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {source_group} | {source_name} | {priority} | {current_status} | {candidate_features} | {timestamp_fields} | {next_safe_action} |".format(
                source_group=row["source_group"],
                source_name=row["source_name"],
                priority=row["priority"],
                current_status=row["current_status"],
                candidate_features=row["candidate_features"].replace("|", "/"),
                timestamp_fields=row["timestamp_fields"].replace("|", "/"),
                next_safe_action=row["next_safe_action"].replace("|", "/"),
            )
        )

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
