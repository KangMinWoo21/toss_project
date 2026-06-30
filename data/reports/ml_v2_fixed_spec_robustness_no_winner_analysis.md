# ML v2 Fixed-Spec Robustness No-Winner Analysis

This report analyzes the POST-29 bounded robustness diagnostic without
selecting a model winner. It uses existing local reports only and does not run
another robustness diagnostic, train a model, rerun validation, rerun OOS,
compare candidates, tune hyperparameters, rank formulas, create candidates,
change strategy parameters, submit to a broker, execute orders, or authorize
trading.

## Analysis Result

`winner_declared=False`

`candidate_decision_allowed=False`

`production_effect=none`

POST-29 is useful paper-only research evidence, but it is not live-readiness
evidence. The bounded diagnostic reported 9 `PASS` rows and 2 `WARN` rows. The
warnings are material interpretation limits, not tuning instructions.

## Key Findings

| Area | Interpretation |
| --- | --- |
| Coverage | Joined sample is 98 rows across 5 symbols and 23 date groups; this remains narrow. |
| Feature lock | Six formula hashes remained locked together with no missing feature values. |
| Chronological split | Primary split used 74 train rows, 20 validation rows, and one embargo date group. |
| Rolling-origin split | Warning: 12 rows with only 4 positive labels. |
| Primary label balance | Warning: validation positives are 8, below the pre-registered count threshold. |
| PIT/cutoff | Joined-row PIT/cutoff re-audit found no local violations. |
| Overfit context | Existing ML v2 overfit warning remains unresolved. |
| Comparison context | Existing ML baseline/v1/v2 reports remain non-comparable and no head-to-head winner is allowed. |

## Safety State

- `winner_declared=False`
- `model_selection_allowed=False`
- `formula_selection_allowed=False`
- `hyperparameter_tuning_allowed=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`
- `model_training_performed_now=False`
- `validation_rerun_performed_now=False`
- `oos_rerun_performed_now=False`
- `candidate_comparison_rerun_performed_now=False`

Next safe checkpoint: add cost, slippage, concentration, and failure diagnostics
for the ML v2 fixed-spec paper-only research packet.
