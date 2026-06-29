# ML News Event Schema Plan

## Do Not Trade / News Schema Plan Only

This report is a fetch-free paper-only news event schema plan. It does not call APIs, fetch news, train models, rerun OOS, compare candidates, create candidates, regenerate monthly plans, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- `fetch_allowed_now=False` for every row.
- `training_allowed_now=False` for every row.
- `feature_added_to_training=False` for every row.
- `trading_allowed=False` for every row.
- `production_effect=none` for every row.
- Required PIT timestamps include `published_at`, `collected_at`, `visible_at`, and `usable_from`.
- Duplicate removal requires deterministic `text_hash` lineage.

## Schema Rows

| Event Group | Source | Candidate Features | Timestamp Fields | Dedupe Rule | Source Coverage Risk | Next Safe Action |
| --- | --- | --- | --- | --- | --- | --- |
| naver_news_events | naver_news_search_api | event_count_1m;negative_keyword_count_1m;source_coverage_count;symbol_event_flag;headline_keyword_flags | published_at;collected_at;visible_at;usable_from;indexed_at | normalize_source_url_and_title; compute text_hash over normalized title/source/url/date; keep earliest visible_at per text_hash | search-ranking drift, delayed indexing, missing paywalled sources, source-specific Korean market coverage bias | Schema review only; do not call Naver News or any news API until a future goal explicitly approves limited fetch. |
| gdelt_news_events | gdelt | global_event_count_1m;foreign_source_count_1m;event_tone_proxy;source_coverage_count | published_at;collected_at;visible_at;usable_from;crawl_seen_at | normalize_source_url_and_title; compute text_hash over normalized title/source/url/date; keep earliest visible_at per text_hash | source_coverage_bias from global media mix, Korean-language undercoverage, translation and entity-linking gaps | Keep GDELT as schema-only; no network fetch until explicitly approved for a limited news-fetch goal. |
| manual_calendar_events | manual_news_calendar | event_type;event_count_1m;earnings_or_disclosure_event_flag;manual_risk_flag | published_at;collected_at;visible_at;usable_from;entered_at | compute text_hash over symbol/event_type/event_title/published_at/provider; keep manual corrections as new visible versions | manual curation may miss events and overrepresent known symbols or recent failures | Define manual-entry review checklist only; do not merge into training in this phase. |
| pit_controls | derived_news_feature_controls | usable_from;source_revision;news_event_id;feature_valid_asof | published_at;collected_at;visible_at;usable_from;feature_generated_at | block duplicates by text_hash within source and symbol before aggregation; retain excluded duplicate lineage | coverage must be measured by provider, language, symbol, and month before any experiment | Use this schema as input to the Phase 9 sentiment plan; keep fetch_allowed_now=False and training_allowed_now=False. |
