# ML v2 Stage 1 Paper-Only Experiment Gate Design

## Purpose

POST-01 defines the gate for deciding whether the Stage 1 broader formulaic
feature table can support a future bounded paper-only experiment. This is a
gate design only. It does not execute the gate, train a model, evaluate
formulas, merge a training dataset, or create a candidate.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `dataset_merge_allowed_now=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_broader_feature_audit_stage1.md`
- `data/reports/ml_v2_formulaic_alpha_merge_readiness_stage1_refresh.md`
- `data/reports/ml_v2_training_readiness_gate_stage1_refresh.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/paper_operation_safety_status_index.md`
- `data/reports/post_cutoff_oos_proof_inventory.md`

## Gate Outcome Vocabulary

A future gate execution report must return exactly one of:

- `ALLOW_PAPER_ONLY_EXPERIMENT`
- `BLOCK`
- `deferred_later_stage`

`ALLOW_PAPER_ONLY_EXPERIMENT` may only allow a bounded, paper-only pipeline
experiment. It must not allow production readiness, candidate promotion, broker
submission, order output, monthly plan regeneration, or protected candidate
changes.

## Allow Conditions For A Future Gate Execution

- Stage 1 feature table and audit exist.
- PIT status is `PASS`.
- Label isolation is `PASS`.
- Missingness remains below a documented threshold.
- Feature hashes and row hashes are materialized and non-reserved.
- The experiment is explicitly bounded and non-promotional.
- Deflated Sharpe and effective trial count remain recognized as not available
  for selection claims.

## Block Conditions

- Missing source reports.
- PIT failure.
- Label leakage.
- Missing or reserved feature hashes.
- Duplicate row hashes.
- Excessive missingness.
- Any need for OOS rerun, candidate comparison rerun, model selection,
  strategy change, protected candidate change, broker work, production
  readiness change, or live trading path.

## Completion Statement

POST-01 is complete as a design-only checkpoint. It defines the future Stage 1
paper-only experiment gate and preserves all safety fields with
`production_effect=none`.
