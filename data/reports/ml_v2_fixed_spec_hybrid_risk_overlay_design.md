# ML v2 Fixed-Spec Hybrid Risk Overlay Design

This report designs the fixed-spec ML v2 hybrid risk overlay after POST-31. It
uses existing local reports only. It does not fetch data, call APIs, scrape
news or SNS, score text with LLMs or sentiment models, merge external features,
train a model, rerun validation, rerun OOS, create candidates, generate orders,
submit to a broker, execute orders, or authorize trading.

## Design Result

`overlay_design_status=disabled_by_default_risk_overlay_design`

All overlay components are default-off, risk-control-only, and manual-review
gated. They may only feed a future paper-only research packet unless a separate
future checkpoint explicitly approves a bounded report-only action.

## Overlay Roles

| Overlay | Role |
| --- | --- |
| Macro and market regime | Future risk-context or exposure-cap proposal only; no direct buy alpha. |
| Disclosure events | Future manual-review event risk flag only after PIT/correction lineage is proven. |
| News events | Future risk watchlist only; no scraping, scoring, or headline alpha now. |
| Official SNS | Whitelist/manual-review-only; no personal-data scoring or automated overlay action. |
| Community SNS | Rejected for automated overlay due to spam, manipulation, and personal-data risk. |
| Sentiment models | Later-stage research only; no FinBERT, LLM, or lexicon scoring now. |
| Internal risk blockers | Carry cost, concentration, and failure blockers into the final packet. |
| Governance | Any future overlay execution requires a separate paper-only gate. |

## Safety State

- `default_enabled=False`
- `risk_control_only=True`
- `fetch_allowed_now=False`
- `api_call_allowed_now=False`
- `news_or_sns_scrape_allowed_now=False`
- `llm_scoring_allowed_now=False`
- `training_allowed_now=False`
- `feature_merge_allowed_now=False`
- `strategy_parameter_change_allowed=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`

Next safe checkpoint: assemble the final ML v2 paper-only research packet.
