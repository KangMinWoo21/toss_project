# ML Model v1 Risk Report

## Do Not Trade / Paper-Only ML Model v1

This report covers a paper-only technical-feature model experiment. It does not use external financial/news/sentiment features, rerun OOS, compare candidates for promotion, change strategy parameters, generate order output, call broker APIs, or authorize trading.

- `external_features_used=False`.
- `post_cutoff_data_used_for_train=False`.
- `trading_allowed=False`.
- `production_effect=none`.
- Protected candidate unchanged.
- External feature policy: `external_readiness=BLOCK;external_features_used=False`.

## Risk Rows

| Metric | Status | Value | Reason |
| --- | --- | --- | --- |
| summary | paper_only_model_v1_risk_review | paper_only_model_v1_risk_review | Risk notes for a technical-only research model; no production readiness change. |
| external_feature_policy | PASS | external_readiness=BLOCK;external_features_used=False | Phase 10 does not approve financial/news/sentiment features for training. |
| overfit_and_data_snooping_risk | WARN | model_v1_reuses_baseline_technical_features;future_iterations_require_locked_protocol | Repeated research loops can overfit process decisions even without candidate promotion. |
| candidate_promotion | PASS | False | Promotion is forbidden in Phase 11. |
| order_output | PASS | False | No order output is generated. |
| protected_candidate_unchanged | PASS | True | Protected PAPER_REVIEW candidate remains unchanged. |
| trading_allowed | PASS | False | Risk report only; no trading authorization. |
| production_effect | PASS | none | Report has no production effect. |
