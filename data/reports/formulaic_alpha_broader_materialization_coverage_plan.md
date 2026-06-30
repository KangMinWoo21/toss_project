# Formulaic Alpha Broader Materialization Coverage Plan

## Purpose

This paper-only plan defines the next broader materialization step after the
30-row formulaic feature sample. It does not generate feature values. Its job
is to prevent an uncontrolled jump from a tiny audit slice to a full universe
feature table.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `feature_values_generated_now=False`.
- `dataset_merge_performed=False`.
- `training_allowed_now=False`.

## Local Evidence Used

- `data/reports/ml_v2_formulaic_alpha_merge_readiness_refresh.md`
- `data/reports/ml_v2_training_readiness_gate_refresh.md`
- `data/reports/formulaic_alpha_materialized_feature_sample.md`
- `data/reports/formulaic_alpha_feature_audit_refresh.md`
- `data/reports/formulaic_alpha_feature_materialization_plan.md`
- `data/reports/formulaic_alpha_sample_generation.csv`
- `data/reports/purged_embargo_validation_schema_plan.md`

## Recommended Stage 1 Coverage

- Symbols: `50` local OHLCV symbols after existing data-quality/PIT screening.
- Dates: `24` monthly feature dates.
- Formulas: existing CP-06 six formula strings only.
- Estimated rows: `50 * 24 * 6 = 7200`.
- Hard cap: `10000` feature rows for the first broader materialization loop.

## Required Future Controls

- No new formulas and no formula sweep.
- No label joins during feature construction.
- Every row must include `feature_visible_at`, `feature_usable_from`, and
  `source_cutoff_time`.
- Every missing value must carry explicit `missing_reason`.
- Every row must carry deterministic `feature_hash` and `feature_row_hash`.
- A chunk manifest must record `chunk_id`, row count, input scope, and output
  hash summary.
- A broader audit refresh must pass before any merge-readiness report changes.

## Stop Rules

Stop the future materialization loop and report `BLOCK` if:

- planned rows exceed `10000`;
- PIT timestamp checks fail;
- duplicate row hashes appear;
- feature hashes remain reserved;
- missingness exceeds a future threshold;
- any step would require API calls, data fetches, OOS rerun, candidate
  comparison rerun, model training, strategy changes, or broker work.

## Current Result

`readiness_status=DESIGN_ONLY_NOT_MATERIALIZED`

This plan does not unblock merge readiness or training readiness. It only
defines the next bounded paper-only implementation loop.

## Completion Statement

The broader materialization coverage plan is complete as a design artifact. No
feature values, formula evaluations, model training, dataset merge, candidate
creation, or production changes occurred.
