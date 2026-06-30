# Formulaic Alpha Feature Audit Refresh

## Purpose

This audit refresh checks the newly materialized formulaic alpha feature sample for PIT availability, label isolation, missingness policy, `formula_hash`, and final `feature_hash` values.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `evaluation_performed=False`.
- `training_allowed_now=False`.
- `merge_ready=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_materialized_feature_sample.csv`
- `data/reports/formulaic_alpha_materialized_feature_sample.md`
- `data/reports/formulaic_alpha_feature_materialization_plan.csv`
- `data/reports/formulaic_alpha_feature_materialization_plan.md`

## Audit Summary

- Feature rows audited: `30`.
- Samples audited: `6`.
- Materialized feature hashes: `6`.
- Feature row hashes: `30`.
- Missing rows: `0`.
- PIT status: `PASS` for the narrow sample.
- Label isolation status: `PASS` for the narrow sample.
- Audit status: `PASS_SAMPLE_ONLY_NOT_TRAINING_READY`.

## Interpretation

The narrow sample now has materialized feature values, PIT timestamps, explicit label non-join fields, missingness policy, formula hashes, final feature hashes, and feature row hashes. This is not a full feature dataset and does not make ML v2 merge-ready or training-ready.

## Remaining Blockers

- Only 5 symbols and one feature date were materialized.
- No full universe/date coverage exists.
- No formula evaluation was performed.
- CP-08 merge readiness remains blocked until a future explicit readiness report changes it.
- CP-09 training readiness remains blocked until a future gate returns `ALLOW_PAPER_ONLY`.

## Completion Statement

The materialized sample audit refresh is complete as paper-only evidence. It does not train a model, score a candidate, create orders, or change production readiness.
