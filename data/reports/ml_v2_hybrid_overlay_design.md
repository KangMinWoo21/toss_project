# ML v2 Hybrid Overlay Design

## Purpose

CP-14 designs the ML v2 hybrid overlay as a disabled-by-default risk overlay
layer. It does not fetch external data, scrape news or SNS, score text, train a
model, change strategy parameters, or produce trading signals.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `external_fetch_performed=False`.
- `llm_scoring_performed=False`.
- `strategy_parameter_change=False`.
- All overlays default to disabled.

## Local Evidence Used

- `data/reports/ml_v2_external_research_source_inventory.csv`
- `data/reports/ml_v2_external_research_source_inventory.md`
- `data/reports/ml_news_event_schema_plan.md`
- `data/reports/ml_sentiment_scoring_plan.md`

## Overlay Roles

- Macro/regime: release-safe risk context only, default off.
- Disclosure/event: PIT event risk flags only, default off.
- News/event: deduplicated source-visible risk flags only, default off.
- CEO/official SNS: whitelist-only manual review watchlist, default off.
- Sentiment model: later-stage research reference only, not an approved scorer.

## Controls

- `direct_buy_alpha_allowed=False` for all overlays.
- `training_allowed_now=False` for all overlays.
- Manual review is required before any future source activation.
- Privacy, platform terms, source visibility, and PIT lineage must be reviewed.
- No overlay may create orders, broker submissions, monthly plan changes,
  candidate promotion, or production readiness changes.

## Recommendation

Keep all external overlays disabled by default. Future work should treat them as
risk context only after source-specific PIT, licensing, privacy, and manual
review controls exist.

## Completion Statement

CP-14 is complete as a hybrid overlay design. It documents macro/news/SNS
overlay roles, default-off gates, manual review controls, and privacy/terms
risks without external fetch, scraping, LLM scoring, or strategy changes.
