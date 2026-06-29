# ML External Feature Readiness Plan

## Do Not Trade / Plan Only

This report is a plan-only artifact. It does not fetch data, call APIs, train models, rerun OOS, compare candidates, create candidates, regenerate monthly plans, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- Overall conclusion: `PLAN_ONLY_NOT_READY_FOR_TRAINING`.
- `fetch_allowed_now=False` for every row.
- `training_allowed_now=False` for every row.
- `trading_allowed=False` for every row.
- `production_effect=none` for every row.
- PIT-safe `usable_from` and source timestamps are required before any future training dataset can be built.

## Plan Rows

| Source Group | Source Name | Priority | Status | Candidate Features | Timestamp Fields | Next Safe Action |
| --- | --- | --- | --- | --- | --- | --- |
| OpenDART financial_disclosure | opendart_financial_statements;opendart_disclosures | high | planned_high_priority | sales;operating_income;net_income;debt_ratio;roe;per;pbr;filing_event_type;correction_filing_flag | fiscal_period;report_period_end;receipt_date;receipt_time;correction_filing;collected_at;usable_from | Define append-only OpenDART schema with usable_from, correction filing lineage, and PIT validation; do not fetch in this loop. |
| news_events | naver_news_search_api;gdelt;manual_news_calendar | medium | planned_after_financials | event_count_1m;negative_event_count_1m;source_coverage_count;text_hash;event_type;symbol_event_flag | published_at;collected_at;visible_at;usable_from;source_id;text_hash | Draft PIT-safe news_events schema and deterministic text_hash de-dup rules after OpenDART plan is accepted; no API calls now. |
| sentiment | rule_lexicon_v1;FinBERT/LLM later-stage | medium-low | planned_after_news_schema | model_version;sentiment_score;importance_score;sentiment_count_1m;negative_sentiment_share_1m | published_at;collected_at;visible_at;usable_from;model_version;scored_at | Plan lexicon_v1 scoring contract only after news schema has text_hash and usable_from; keep FinBERT/LLM later-stage. |
| sns_community | sns_community_later_stage | later-stage | later_stage_not_ready | community_mention_count;community_sentiment_score;spam_score;duplicate_cluster_id;manipulation_risk_flag | posted_at;collected_at;visible_at;usable_from;account_id_hash;text_hash | Keep out of baseline ML until spam, duplication, manipulation, and timestamp controls are designed and reviewed. |
