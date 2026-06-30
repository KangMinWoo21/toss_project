# ML v2 Fixed-Spec Robustness Approval Gate

This report is a paper-only execution approval gate for the pre-registered ML
v2 fixed-spec robustness packet. It does not execute robustness diagnostics,
train a model, rerun validation, rerun OOS, compare candidates, tune
hyperparameters, rank formulas, create candidates, change strategy parameters,
write production artifacts, submit to a broker, execute orders, or authorize
trading.

## Gate Decision

`gate_decision=ALLOW_ONE_BOUNDED_PAPER_ROBUSTNESS_RUN`

Allowed next action:

`run_one_bounded_paper_only_robustness_diagnostic_next`

This approval is limited to one future bounded diagnostic checkpoint using the
fixed ML v2 specification and the POST-27 pre-registered packet. It is not a
model-selection, candidate-decision, promotion, production-readiness, broker,
or order-execution approval.

## Required Boundaries

| Boundary | Requirement |
| --- | --- |
| Fixed specification | Reuse `logistic_regression_sgd_fixed_v2` and the fixed Stage 1 six-formula feature lock |
| Split reporting | Report all pre-registered split diagnostics; do not keep only the best split |
| PIT/embargo | Re-audit visible-at, usable-from, label end, purge, embargo, and post-cutoff exclusion fields |
| Sample warnings | Treat small validation sample and label-balance warnings as interpretation blockers |
| Interpretation | No model winner, no candidate decision, no tuning, no promotion |
| Output | CSV and Markdown diagnostics only under `data/reports` |
| Safety | Keep production `BLOCK`, protected candidate `PAPER_REVIEW`, `trading_allowed=False`, and `production_effect=none` |

## Safety State

- `bounded_robustness_diagnostic_allowed_next=True`
- `execution_performed_now=False`
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

Next safe checkpoint: run exactly one bounded paper-only robustness diagnostic,
then analyze all results without selecting a winner.
