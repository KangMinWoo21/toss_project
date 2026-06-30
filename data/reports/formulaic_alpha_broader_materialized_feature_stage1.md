# Formulaic Alpha Broader Materialized Feature Stage 1

## Purpose

This paper-only artifact implements the Stage 1 broader materialization plan for the existing six CP-06 formula strings. It uses existing local OHLCV files only and remains below the 10000-row cap.

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
- `dataset_merge_performed=False`.

## Scope

- Chunk id: `stage1_50x24x6`.
- Symbols: `50`.
- Monthly feature dates: `24`.
- Formula samples: `6`.
- Feature rows created: `7200`.
- Row cap: `10000`.
- First feature date: `2024-07-31`.
- Last feature date: `2026-06-18`.
- Feature hashes materialized: `6`.
- Feature row hashes created: `7200`.
- Missing rows: `24`.
- Label joins performed: `0`.
- Evaluation metrics calculated: `0`.

## PIT And Label Controls

Every row includes `feature_visible_at`, `feature_usable_from`, `source_cutoff_time`, `label_horizon`, `label_start_date`, `label_end_date`, `purge_window_days`, and `embargo_window_days`. Labels, future returns, validation results, and candidate outcomes were not used to compute feature values.

## Interpretation

This is a broader materialized feature sample, not a training dataset. It does not evaluate formulas, select candidates, merge a dataset for training, or change production readiness.

## Companion Files

- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1_manifest.csv`
