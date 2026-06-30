# Formulaic Alpha Feature Materialization Plan

## Purpose

This paper-only plan defines the contract for a future formulaic alpha feature
materialization loop. It addresses the first ML v2 final-packet blocker at the
design level: feature values, PIT timestamps, label isolation, missingness
policy, and final `feature_hash` values are not yet materialized.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `feature_values_generated_now=False`.
- `evaluation_performed_now=False`.
- `training_allowed_now=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_sample_generation.csv`
- `data/reports/formulaic_alpha_schema_plan.md`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/formulaic_alpha_feature_audit.md`
- `data/reports/ml_v2_final_research_packet.md`

## Required Future Feature Table

A future feature table contract is required before any feature materialization
can unblock merge readiness.

A future materialization loop should create a table with, at minimum:

- `sample_id`
- `formula_hash`
- `feature_hash`
- `symbol`
- `feature_date`
- `date_group`
- `feature_value`
- `missing_reason`
- `operator_version`
- `parameter_summary`
- `feature_visible_at`
- `feature_usable_from`
- `source_cutoff_time`
- `label_horizon`
- `label_start_date`
- `label_end_date`
- `purge_window_days`
- `embargo_window_days`

## Required Controls

- PIT: `feature_visible_at <= feature_usable_from`, and
  `feature_usable_from` must be no later than the decision timestamp.
- Label isolation: labels, future returns, validation results, and candidate
  outcomes must not influence `feature_value`.
- Missingness: insufficient lookback, missing input, PIT-universe exclusion,
  and undefined operator states must produce explicit `missing_reason` values.
- Hashing: final `feature_hash` must include formula hash, operator version,
  input fields, lookback metadata, PIT fields, and missingness policy version.
- Audit: a refreshed feature audit must pass before merge readiness can change.

## Current Result

`readiness_status=DESIGN_ONLY_NOT_MATERIALIZED`

This plan resolves only the design gap. It does not generate feature values and
does not unblock CP-08/CP-09. The materialized-feature blocker remains until a
future paper-only loop creates the table and passes audit.

## Non-Goals Preserved

No feature values were generated, no formula was evaluated, no model was
trained, no data was fetched, no API was called, no news/SNS was scraped, no
OOS was rerun, no candidate comparison was rerun, no candidate was created, no
monthly plan was regenerated, no strategy parameter was changed, no protected
candidate was modified, no broker work occurred, and no production readiness
changed.

## Completion Statement

This loop is complete as a paper-only feature materialization plan. The next
required action is a separate paper-only materialization implementation that
creates feature rows and then reruns the formulaic alpha feature audit.
