# Formulaic Alpha Materialized Feature Sample

## Purpose

This paper-only artifact materializes a narrow feature sample for the six CP-06 formulaic alpha strings using existing local OHLCV files only. It creates feature values for 5 symbols on `2026-06-18` for audit purposes only.

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
- No model training, OOS rerun, candidate comparison rerun, candidate creation, monthly plan regeneration, strategy parameter change, broker work, or production readiness change was performed.

## Scope

- Symbols: `000020;005930;035420;051910;068270`.
- Feature date: `2026-06-18`.
- Formula samples: `6`.
- Feature rows created: `30`.
- Feature hashes materialized: `6`.
- Feature row hashes created: `30`.
- Missing rows: `0`.
- Label joins performed: `0`.
- Evaluation metrics calculated: `0`.

## PIT And Label Controls

- `feature_visible_at=2026-06-18T15:30:00+09:00`.
- `feature_usable_from=2026-06-19T00:00:00+09:00`.
- `source_cutoff_time=2026-06-18T15:30:00+09:00`.
- `label_horizon=next_month_placeholder_no_label_join`.
- `label_start_date=not_joined`.
- `label_end_date=not_joined`.
- Labels, future returns, validation results, and candidate outcomes were not used to compute `feature_value`.

## Interpretation

This sample resolves materialization mechanics for a tiny audit slice only. It does not make CP-08 merge-ready and does not authorize training. A refreshed audit is required before any future readiness gate changes.

## Companion CSV

`data/reports/formulaic_alpha_materialized_feature_sample.csv`
