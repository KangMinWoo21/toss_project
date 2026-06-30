# ML v2 Formulaic Alpha Merge Readiness

## Purpose

CP-08 decides whether the CP-06 formulaic alpha samples are ready to merge into
an ML v2 training dataset. Based on CP-07, the answer is `BLOCK`.

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
- `candidate_creation=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_sample_generation.csv`
- `data/reports/formulaic_alpha_sample_generation.md`
- `data/reports/formulaic_alpha_feature_audit.csv`
- `data/reports/formulaic_alpha_feature_audit.md`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/post_cutoff_oos_proof_inventory.md`
- `data/reports/paper_operation_safety_status_index.md`

## Readiness Summary

- Formula sample rows: `6`.
- Ledger sample rows: `6`.
- Formula hashes present: `6`.
- Materialized feature values: `0`.
- Materialized `feature_hash` values: `0`.
- PIT aligned samples: `0`.
- Missingness-audited samples: `0`.
- Label-isolated samples: `0`.
- Merge-ready samples: `0`.
- Overall `merge_readiness=BLOCK`.

## Blockers

- Feature values were not generated in CP-06.
- CP-07 records PIT availability blockers for all samples.
- CP-07 records label isolation blockers for all samples.
- CP-07 records missingness policy blockers for all samples.
- `feature_hash` values are reserved but not materialized.
- Effective trial count remains `not_available`.
- Post-cutoff OOS proof does not authorize promotion or production.

## Recommendation

Do not merge formulaic alpha samples into an ML v2 dataset yet. CP-09 training
readiness should treat formulaic alpha merge readiness as `BLOCK` unless a
future paper-only feature materialization checkpoint supplies PIT timestamps,
missingness policy, label isolation, deterministic `feature_hash` values, and
schema/content checks.

## Completion Statement

CP-08 is complete as a readiness report. It documents coverage, missingness,
PIT alignment, trial ledger linkage, and merge blockers without performing a
dataset merge, training run, comparison, candidate creation, or production
change.
