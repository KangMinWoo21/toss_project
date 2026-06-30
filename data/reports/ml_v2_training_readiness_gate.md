# ML v2 Training Readiness Gate

## Purpose

CP-09 gates whether ML v2 paper-only training is allowed. The explicit gate
result is `BLOCK`.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `paper_only_training_allowed_next=False`.
- `model_training_performed=False`.
- `candidate_creation=False`.

## Local Evidence Used

- `data/reports/ml_baseline_feature_label_dataset_audit.md`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/ml_v2_formulaic_alpha_merge_readiness.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/min_history244_pit_universe_safety_review.md`
- `data/reports/post_cutoff_oos_proof_inventory.md`
- `data/reports/ml_v2_external_research_source_inventory.md`
- `data/reports/fee_tax_slippage_adjusted_expectancy_report.md`
- `data/reports/month_symbol_concentration_report.md`

## Gate Result

`gate_result=BLOCK`

The gate is blocked because:

- CP-08 records `merge_readiness=BLOCK`.
- Formulaic alpha feature values are not materialized.
- PIT availability fields and final `feature_hash` values are missing.
- Label isolation and missingness policies are not materialized.
- Effective trial count remains `not_available`.
- Deflated Sharpe remains placeholder-only and not calculated.
- `min_history244` PIT universe evidence remains incomplete.
- Post-cutoff OOS proof does not authorize review, promotion, or production.
- External macro/news/SNS inputs remain disabled-by-default risk overlays and
  are not training-ready.

## Recommendation

Do not train ML v2 in CP-09. CP-10 should create a blocked paper-only training
report explaining that training was not run because CP-09 blocked it. Later
checkpoints may continue only as blocked, design, or report-only artifacts when
they do not require unavailable model outputs.

## Completion Statement

CP-09 is complete as a training readiness gate. It evaluates local data
readiness, validation readiness, cost controls, trial counts, leakage controls,
and external overlay status, and records explicit `BLOCK`.
