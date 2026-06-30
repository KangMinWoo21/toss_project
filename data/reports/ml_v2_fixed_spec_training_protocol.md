# ML v2 Fixed-Spec Training Protocol

This report converts the next ML v2 experiment from a model-selection problem
into one fixed-spec, no-selection, paper-only experiment.

## Fixed Specification

| Field | Fixed value |
|---|---|
| Model type | `logistic_regression_sgd_fixed_v2` |
| Feature set | `stage1_formulaic_ohlcv_fixed_6_features_only` |
| Label policy | `next_month_return_binary_from_existing_local_ml_label_source` |
| Split policy | `date_group_chronological_train_then_validation_with_purge_embargo_v1` |
| Hyperparameter policy | library defaults or one documented constant set only |
| Output boundary | paper-only reports only |

## Controls

- No hyperparameter sweep.
- No formula ranking.
- No model family comparison.
- No candidate creation.
- No production artifact.
- No strategy parameter change.
- No OOS rerun or candidate comparison rerun.

## Training Status

`training_allowed_now=False` for this checkpoint. The only possible next step is
paper-only training if the fixed-spec readiness gate returns
`ALLOW_PAPER_ONLY_TRAINING`.

Safety state remains:

- production `BLOCK`
- protected candidate `PAPER_REVIEW`
- `trading_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `production_effect=none`

