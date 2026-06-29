# ML External Feature Readiness Re-Audit

## Do Not Trade / Re-Audit Only

This report re-audits external feature readiness for paper-only ML research. It does not fetch data, call APIs, score sentiment, train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- Overall readiness: `BLOCK`.
- `training_allowed=False` for every row.
- `feature_added_to_training=False` for every row.
- `post_cutoff_data_used_for_train=False` for every row.
- `trading_allowed=False` for every row.
- `production_effect=none` for every row.

## Re-Audit Rows

| Feature Group | Readiness | Leakage Check | Missing Rate | Evidence | Next Safe Action |
| --- | --- | --- | --- | --- | --- |
| financial | not_ready | PASS | 1.0000 | merge_audit=financial_feature_merge_audit_complete; join_coverage=0/5; training_allowed_now=True | Do not train; financial sample remains not ready until coverage and missingness pass under explicit approval. |
| news | not_ready | PASS | not_measured_schema_only | schema_plan_only=True; fetch_allowed_now=True; training_allowed_now=True; feature_added_to_training=True | Keep news plan-only; no fetch or training until a future explicitly approved limited news-fetch goal. |
| sentiment | not_ready | PASS | not_measured_plan_only | schema_plan_only=True; rule_lexicon_v1=True; model_training_allowed=True; feature_added_to_training=True | Keep sentiment plan-only; do not score, train, or merge until external feature readiness is explicitly approved. |
| overall | BLOCK | PASS | mixed | financial=not_ready; news=not_ready; sentiment=not_ready | External features are not approved for training; proceed only to a future paper-only experiment if separately approved. |
