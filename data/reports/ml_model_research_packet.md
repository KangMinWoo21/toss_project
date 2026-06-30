# ML Model Research Packet

## Do Not Trade / Research Packet Only

- model_completion_status: `paper_only_complete_not_live_ready`.
- trading_allowed=False.
- production_effect=none.
- candidate_promotion=False.
- broker_submission=False.
- order_execution=False.
- production_readiness_change=False.
- production `BLOCK` retained.
- Protected candidate unchanged.
- Final state: paper-only complete / not live-ready.

## Research Summary

| Section | Status | Value | Summary |
| --- | --- | --- | --- |
| model_completion_status | PASS | paper_only_complete_not_live_ready | Do Not Trade / Research Packet Only. Final packet consolidates Phase 1-13 local artifacts without live readiness. |
| data_lineage | PASS | train_cutoff=2026-06-18;local_reports_only | Baseline lineage uses existing local PIT feature/label rows and report artifacts only; no fetch/API/OOS rerun/candidate compare. |
| baseline_feature_label_dataset | PASS | rows=69915;features=return_1m;return_3m;return_6m;volatility_3m;volume_change_1m;price_vs_3m_sma;drawdown_3m | Baseline dataset audit status: ready_for_training_scaffold. |
| baseline_model_training | PASS | logistic_regression_sgd | Baseline training status: paper_only_baseline_trained; artifact remains disconnected from production. |
| validation_results | PASS | paper_only_validation_complete;drawdown=-0.5687 | Validation results are summarized for research only, with no OOS rerun or protected candidate change. |
| feature_importance_failure_analysis | WARN | top_features=price_vs_3m_sma;return_3m;drawdown_3m;failure_rows=232 | Feature importance and failure cases are recorded; failure analysis keeps overfit risk visible. |
| opendart_financial_features | WARN | not_ready | OpenDART financial features remain limited PIT sample / merge-audit evidence only unless a source explicitly says ready. |
| news_schema | WARN | not_ready | News is schema/plan-only unless a source explicitly says ready; no news fetch was called. |
| sentiment_schema | WARN | not_ready | Sentiment remains rule/lexicon plan-only, with FinBERT/LLM/SNS kept later-stage unless explicitly ready. |
| external_feature_readiness | BLOCK | not_ready | External readiness status: BLOCK; external features are not training-ready unless explicitly ready. |
| model_v1_technical_only | PASS | paper_only_model_v1_trained;validation=paper_only_model_v1_validated;features=technical_only | Model v1 is a technical-only paper experiment because external features are not ready. |
| shadow_scoring | PASS | rows=4 | Shadow scoring is human-readable only: no order output, broker submission, monthly plan regeneration, or promotion. |
| observation_status | PASS | paper_only_observation_mature;basis=historical_backfill;months=101 | Observation status is mature on paper-only evidence and does not imply live readiness. |
| leakage_checks | PASS | post_cutoff_train_leakage=PASS;post_cutoff_data_used_for_train=False | Dataset, training, validation, model v1, and observation artifacts indicate no post-cutoff train leakage. |
| overfit_data_snooping_risk | WARN | risk_retained | Technical-only model evidence is research-useful but remains exposed to overfit/data-snooping risk; no tuning or promotion is authorized. |
| final_recommendation | BLOCK | keep_paper_only_do_not_trade | Final recommendation: paper-only complete, not live-ready; keep production BLOCK, protected candidate unchanged, and do not trade. |

## Final Recommendation

Final recommendation: paper-only complete, not live-ready; keep production BLOCK, protected candidate unchanged, and do not trade.

External features remain excluded from training unless an existing local readiness report explicitly marks them ready.
