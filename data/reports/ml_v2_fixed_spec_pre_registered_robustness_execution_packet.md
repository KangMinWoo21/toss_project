# ML v2 Fixed-Spec Pre-Registered Robustness Execution Packet

This packet pre-registers future robustness diagnostics for the ML v2
fixed-spec research path. It does not execute robustness checks, train a model,
rerun validation, rerun OOS, compare candidates, tune hyperparameters, rank
formulas, create candidates, change strategy parameters, write production
artifacts, submit to a broker, execute orders, or authorize trading.

## Packet Status

`packet_complete=True`

`execution_allowed_now=False`

Next safe action:

`review_or_create_execution_approval_gate`

## Pre-Registered Diagnostics

| Group | Registered rule |
| --- | --- |
| Coverage thresholds | Report joined rows, train rows, validation rows, symbol count, and date-group count before interpretation |
| Split manifest | Report all pre-listed split variants; never keep only the best split |
| Feature lock | Use all six fixed Stage 1 formula hashes together |
| Label balance | Warn on low class counts or class share; no threshold or class-weight tuning |
| PIT/embargo | Re-audit visible-at, usable-from, label end, purge, embargo, and post-cutoff exclusion fields |
| Metric reporting | Report all diagnostics, favorable or unfavorable |
| Interpretation | No model winner, no candidate decision, no production readiness change |
| Cost/failure scope | Shadow-only cost, slippage, concentration, turnover, and failure buckets |

## Execution Boundary

This packet is not an execution approval. It only defines what a future
robustness run must report if a later checkpoint approves execution.

Safety state:

- `allowed_future_execution=False`
- `execution_allowed_now=False`
- `training_allowed_now=False`
- `validation_rerun_allowed_now=False`
- `oos_rerun_allowed_now=False`
- `model_selection_allowed=False`
- `formula_selection_allowed=False`
- `hyperparameter_tuning_allowed=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`

