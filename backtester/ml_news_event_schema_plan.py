from __future__ import annotations

import csv
from pathlib import Path


NEWS_SCHEMA_COLUMNS = [
    "event_group",
    "source_name",
    "candidate_features",
    "schema_fields",
    "timestamp_fields",
    "dedupe_rule",
    "lineage_rule",
    "api_key_required",
    "fetch_allowed_now",
    "training_allowed_now",
    "feature_added_to_training",
    "trading_allowed",
    "production_effect",
    "pit_required",
    "usable_from_required",
    "source_coverage_risk",
    "leakage_risk",
    "data_quality_risk",
    "current_status",
    "next_safe_action",
]


def _row(
    *,
    event_group: str,
    source_name: str,
    candidate_features: list[str],
    schema_fields: list[str],
    timestamp_fields: list[str],
    dedupe_rule: str,
    lineage_rule: str,
    api_key_required: str,
    source_coverage_risk: str,
    leakage_risk: str,
    data_quality_risk: str,
    next_safe_action: str,
) -> dict[str, str]:
    return {
        "event_group": event_group,
        "source_name": source_name,
        "candidate_features": ";".join(candidate_features),
        "schema_fields": ";".join(schema_fields),
        "timestamp_fields": ";".join(timestamp_fields),
        "dedupe_rule": dedupe_rule,
        "lineage_rule": lineage_rule,
        "api_key_required": api_key_required,
        "fetch_allowed_now": "False",
        "training_allowed_now": "False",
        "feature_added_to_training": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "pit_required": "True",
        "usable_from_required": "True",
        "source_coverage_risk": source_coverage_risk,
        "leakage_risk": leakage_risk,
        "data_quality_risk": data_quality_risk,
        "current_status": "schema_plan_only",
        "next_safe_action": next_safe_action,
    }


def build_ml_news_event_schema_plan() -> list[dict[str, str]]:
    common_timestamps = ["published_at", "collected_at", "visible_at", "usable_from"]
    common_dedupe = "normalize_source_url_and_title; compute text_hash over normalized title/source/url/date; keep earliest visible_at per text_hash"
    return [
        _row(
            event_group="naver_news_events",
            source_name="naver_news_search_api",
            candidate_features=[
                "event_count_1m",
                "negative_keyword_count_1m",
                "source_coverage_count",
                "symbol_event_flag",
                "headline_keyword_flags",
            ],
            schema_fields=[
                "source_id",
                "provider",
                "symbol",
                "headline",
                "summary",
                "url",
                "publisher",
                "language",
                "text_hash",
                "event_type",
            ],
            timestamp_fields=common_timestamps + ["indexed_at"],
            dedupe_rule=common_dedupe,
            lineage_rule="append_only_by_source_id_and_text_hash; never replace a visible row with later edited text before its own visible_at",
            api_key_required="mixed",
            source_coverage_risk="search-ranking drift, delayed indexing, missing paywalled sources, source-specific Korean market coverage bias",
            leakage_risk="high_if_collected_at_or_visible_at_is_after_feature_date",
            data_quality_risk="duplicate syndicated headlines, symbol ambiguity, headline edits, title/body mismatch",
            next_safe_action="Schema review only; do not call Naver News or any news API until a future goal explicitly approves limited fetch.",
        ),
        _row(
            event_group="gdelt_news_events",
            source_name="gdelt",
            candidate_features=[
                "global_event_count_1m",
                "foreign_source_count_1m",
                "event_tone_proxy",
                "source_coverage_count",
            ],
            schema_fields=[
                "source_id",
                "provider",
                "symbol",
                "headline",
                "url",
                "publisher",
                "language",
                "country",
                "text_hash",
                "event_type",
            ],
            timestamp_fields=common_timestamps + ["crawl_seen_at"],
            dedupe_rule=common_dedupe,
            lineage_rule="join only rows whose usable_from is on or before feature_date; preserve provider source_id lineage",
            api_key_required="False",
            source_coverage_risk="source_coverage_bias from global media mix, Korean-language undercoverage, translation and entity-linking gaps",
            leakage_risk="medium_high_if_article_visibility_is_inferred_from_event_date_only",
            data_quality_risk="entity ambiguity, non-Korean coverage imbalance, duplicate wire articles, language detection drift",
            next_safe_action="Keep GDELT as schema-only; no network fetch until explicitly approved for a limited news-fetch goal.",
        ),
        _row(
            event_group="manual_calendar_events",
            source_name="manual_news_calendar",
            candidate_features=[
                "event_type",
                "event_count_1m",
                "earnings_or_disclosure_event_flag",
                "manual_risk_flag",
            ],
            schema_fields=[
                "source_id",
                "provider",
                "symbol",
                "event_type",
                "event_title",
                "event_note",
                "manual_review_required",
                "text_hash",
            ],
            timestamp_fields=common_timestamps + ["entered_at"],
            dedupe_rule="compute text_hash over symbol/event_type/event_title/published_at/provider; keep manual corrections as new visible versions",
            lineage_rule="manual rows are append-only with reviewer-visible timestamps; corrections must not overwrite prior usable_from",
            api_key_required="False",
            source_coverage_risk="manual curation may miss events and overrepresent known symbols or recent failures",
            leakage_risk="high_if_manual_entry_uses_hindsight_or_post_feature_date_information",
            data_quality_risk="inconsistent event taxonomy, sparse coverage, reviewer bias, correction timing ambiguity",
            next_safe_action="Define manual-entry review checklist only; do not merge into training in this phase.",
        ),
        _row(
            event_group="pit_controls",
            source_name="derived_news_feature_controls",
            candidate_features=[
                "usable_from",
                "source_revision",
                "news_event_id",
                "feature_valid_asof",
            ],
            schema_fields=[
                "news_event_id",
                "source_revision",
                "feature_date",
                "feature_valid_asof",
                "excluded_reason",
                "quality_status",
                "text_hash",
            ],
            timestamp_fields=common_timestamps + ["feature_generated_at"],
            dedupe_rule="block duplicates by text_hash within source and symbol before aggregation; retain excluded duplicate lineage",
            lineage_rule="feature rows become research-eligible only when usable_from <= feature_date and quality_status=PASS",
            api_key_required="False",
            source_coverage_risk="coverage must be measured by provider, language, symbol, and month before any experiment",
            leakage_risk="block_if_usable_from_missing_or_after_feature_date",
            data_quality_risk="timezone ambiguity, delayed collection, duplicate clusters, symbol-link quality drift",
            next_safe_action="Use this schema as input to the Phase 9 sentiment plan; keep fetch_allowed_now=False and training_allowed_now=False.",
        ),
    ]


def _validate_rows(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [column for column in NEWS_SCHEMA_COLUMNS if not row.get(column)]
        if missing:
            raise ValueError(f"news schema row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("fetch_allowed_now", "False"),
            ("training_allowed_now", "False"),
            ("feature_added_to_training", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("pit_required", "True"),
            ("usable_from_required", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"news schema row {index} {column}={row[column]} expected {expected}")
        for field in ("published_at", "collected_at", "visible_at", "usable_from"):
            if field not in row["timestamp_fields"]:
                raise ValueError(f"news schema row {index} missing timestamp field {field}")
        if "text_hash" not in row["dedupe_rule"]:
            raise ValueError(f"news schema row {index} missing text_hash dedupe rule")


def save_ml_news_event_schema_plan(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NEWS_SCHEMA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# ML News Event Schema Plan",
        "",
        "## Do Not Trade / News Schema Plan Only",
        "",
        "This report is a fetch-free paper-only news event schema plan. It does not call APIs, fetch news, train models, rerun OOS, compare candidates, create candidates, regenerate monthly plans, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        "- `fetch_allowed_now=False` for every row.",
        "- `training_allowed_now=False` for every row.",
        "- `feature_added_to_training=False` for every row.",
        "- `trading_allowed=False` for every row.",
        "- `production_effect=none` for every row.",
        "- Required PIT timestamps include `published_at`, `collected_at`, `visible_at`, and `usable_from`.",
        "- Duplicate removal requires deterministic `text_hash` lineage.",
        "",
        "## Schema Rows",
        "",
        "| Event Group | Source | Candidate Features | Timestamp Fields | Dedupe Rule | Source Coverage Risk | Next Safe Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {event_group} | {source_name} | {candidate_features} | {timestamp_fields} | {dedupe_rule} | {source_coverage_risk} | {next_safe_action} |".format(
                event_group=row["event_group"],
                source_name=row["source_name"],
                candidate_features=row["candidate_features"].replace("|", "/"),
                timestamp_fields=row["timestamp_fields"].replace("|", "/"),
                dedupe_rule=row["dedupe_rule"].replace("|", "/"),
                source_coverage_risk=row["source_coverage_risk"].replace("|", "/"),
                next_safe_action=row["next_safe_action"].replace("|", "/"),
            )
        )
    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
