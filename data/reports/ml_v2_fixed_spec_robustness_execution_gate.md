# ML v2 Fixed-Spec Robustness Execution Gate

This is a paper-only gate for future robustness work. It does not execute
robustness checks, train a model, rerun validation, rerun OOS, compare
candidates, tune hyperparameters, rank formulas, create candidates, change
strategy parameters, write production artifacts, submit to a broker, execute
orders, or authorize trading.

## Gate Decision

`BLOCK`

The next safe action is:

`create_pre_registered_robustness_execution_packet`

## Why Execution Is Blocked Now

ML v2 fixed-spec is runnable, but the current evidence is not enough for a
robustness execution loop:

- validation sample is only `20` rows
- train-validation gap is `0.0986`
- overfit status is `WARN_OVERFIT_RISK_NOT_PROVEN`
- split variants are not yet pre-registered
- label-balance warning thresholds are not yet fixed
- a full joined-row PIT/embargo re-audit is not yet defined
- no-winner interpretation needs to stay explicit

## Required Before Any Robustness Run

- Minimum joined row, symbol, date-group, and validation row thresholds.
- A split manifest listing every variant before execution.
- A fixed six-formula hash lock.
- Label-balance warning thresholds.
- Joined-row PIT, visible-at, usable-from, label-end, purge, and embargo checks.
- A no-winner interpretation gate.

## Boundary

The future robustness packet may be descriptive only. It cannot select the best
split, tune the model, rank formulas, promote a candidate, alter the protected
candidate, or create production readiness.

Safety state:

- `execution_allowed_now=False`
- `training_allowed_now=False`
- `validation_rerun_allowed_now=False`
- `oos_rerun_allowed_now=False`
- `model_selection_allowed=False`
- `formula_selection_allowed=False`
- `hyperparameter_tuning_allowed=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `trading_allowed=False`
- `production_effect=none`

