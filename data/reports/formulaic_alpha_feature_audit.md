# Formulaic Alpha Feature Audit

## Purpose

CP-07 audits the CP-06 formulaic alpha samples for PIT readiness, lookback
metadata, label isolation, missingness policy, `formula_hash`, and
`feature_hash`. Because CP-06 generated formula strings only and no feature
values, this audit records a `BLOCK` status for merge or training readiness.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `feature_values_generated=False`.
- `evaluation_performed=False`.
- `training_allowed_now=False`.
- `merge_ready=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_sample_generation.csv`
- `data/reports/formulaic_alpha_sample_generation.md`
- `data/reports/formulaic_alpha_schema_plan.md`
- `data/reports/purged_embargo_validation_schema_plan.md`

## Audit Summary

- Sample rows audited: `6`.
- Formula hashes present: `6`.
- Feature hashes materialized: `0`.
- Feature values generated: `0`.
- Samples with PIT availability blocker: `6`.
- Samples with label isolation blocker: `6`.
- Samples with missingness policy blocker: `6`.
- Samples merge-ready: `0`.

## Findings

The CP-06 samples have deterministic formula hashes and bounded lookback
metadata. However, they do not yet have materialized feature values,
`feature_visible_at`, `feature_usable_from`, assigned label horizons, concrete
missingness policies, or final `feature_hash` values. Therefore, they cannot be
merged into an ML v2 dataset and cannot be used for model training or
selection.

## Recommendation

Keep CP-07 as a blocking audit. Before CP-08 can allow any merge readiness,
future work must materialize features in a paper-only process with PIT
timestamps, label isolation, missingness policy, and deterministic
`feature_hash` generation. Do not evaluate formula returns, select formulas,
train a model, or modify strategy parameters from this audit.

## Completion Statement

CP-07 is complete as a feature audit. It checks PIT availability, lookback
metadata, label isolation, missingness policy, `feature_hash`, and
`formula_hash`, and records `audit_status=BLOCK` because no feature values were
generated.
