# ML v2 Fixed-Spec Overfit Analysis

This is a paper-only overfit diagnostic based only on existing local reports. It
does not train a model, rerun validation, rerun OOS, compare candidates, tune
hyperparameters, rank formulas, create candidates, change strategy parameters,
write production artifacts, submit to a broker, execute orders, or authorize
trading.

## Key Findings

| Model family | Train rows | Validation rows | Train accuracy | Validation accuracy | Gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| ML baseline internal split | 111 | 88 | 0.5946 | 0.5909 | 0.0037 |
| ML baseline validation report | 111 | 88 | 0.5946 | 0.5335 | 0.0611 |
| ML model v1 internal split | 111 | 88 | 0.5946 | 0.5909 | 0.0037 |
| ML v2 fixed-spec | 74 | 20 | 0.6486 | 0.5500 | 0.0986 |

## Interpretation

ML v2 fixed-spec shows a materially larger train-validation gap than the
baseline/v1 internal split diagnostics. That is an overfit warning, not proof of
overfit. The validation sample has only 20 rows, with 8 positive and 12 negative
labels, so sampling noise can easily dominate the measured gap.

The POST-21 fixed-spec protocol reduced model-selection overfit risk because it
uses one model, one feature set, one split policy, no formula ranking, and no
hyperparameter sweep. However, repeated research loops still create process
overfit risk. The right next step is not promotion or tuning; it is a
pre-registered robustness execution gate.

## Decision Boundary

- No model winner is declared.
- ML v2 is not production-ready.
- ML v2 should not be tuned from this result.
- No candidate should be created or promoted.
- No strategy parameter should change.
- No OOS rerun or candidate comparison rerun is authorized.

Safety state:

- `training_performed_now=False`
- `validation_rerun_performed_now=False`
- `oos_rerun_performed_now=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `trading_allowed=False`
- `production_effect=none`

