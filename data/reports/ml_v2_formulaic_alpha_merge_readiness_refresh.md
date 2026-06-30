# ML v2 Formulaic Alpha Merge Readiness Refresh

## Purpose

This paper-only refresh re-evaluates CP-08 formulaic alpha merge readiness after
the narrow materialized feature sample and audit refresh.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `dataset_merge_performed=False`.
- `model_training_performed=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_materialized_feature_sample.csv`
- `data/reports/formulaic_alpha_materialized_feature_sample.md`
- `data/reports/formulaic_alpha_feature_audit_refresh.csv`
- `data/reports/formulaic_alpha_feature_audit_refresh.md`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`

## Result

`merge_readiness=BLOCK_PARTIAL_SAMPLE_ONLY`

The materialized sample improves evidence compared with CP-08 because it
contains 30 feature rows, 6 final feature hashes, PIT timestamps, label
non-join fields, and missing rows `0`. However, it is only a 5-symbol,
one-date audit slice. It is not a full ML v2 feature dataset.

## Remaining Blockers

- No full universe/date coverage.
- No validation-ready feature matrix.
- No formula evaluation.
- No effective trial count.
- No Deflated Sharpe calculation.
- No explicit future readiness gate allowing merge.

## Recommendation

Keep merge readiness blocked. The next paper-only loop should design or create
a broader feature materialization coverage plan before any training gate can
change.

## Completion Statement

This refresh is complete as a paper-only readiness update. No dataset merge,
model training, formula evaluation, candidate creation, or production change
occurred.
