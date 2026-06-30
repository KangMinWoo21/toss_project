# ML v2 Fixed-Spec Robustness Plan

This is a paper-only design report for future ML v2 robustness checks. It does
not train a model, rerun validation, rerun OOS, compare candidates, rank
formulas, tune hyperparameters, change strategy parameters, create a candidate,
write production artifacts, submit to a broker, execute orders, or authorize
trading.

## Current Evidence

- ML v2 fixed-spec training status:
  `paper_only_ml_v2_fixed_spec_trained`.
- ML v2 fixed-spec validation status:
  `paper_only_ml_v2_fixed_spec_validated`.
- Joined rows: `98`.
- Train rows: `74`.
- Validation rows: `20`.
- Train accuracy: `0.6486`.
- Validation accuracy: `0.5500`.
- POST-23 comparison status: diagnostic-only, no model winner declared.

## Planned Robustness Checks

| Check | Purpose | Current action |
| --- | --- | --- |
| Joined sample coverage | Decide minimum row/date/symbol requirements before any broader claim | design only |
| Split stability | Pre-register alternate chronological split diagnostics | design only |
| Label balance | Flag unstable class balance without threshold tuning | design only |
| Formula hash lock | Keep all six fixed formula hashes together | design only |
| PIT/embargo re-audit | Recheck visible/usable dates, label isolation, and embargo fields | design only |
| Cost/concentration/failure diagnostics | Plan shadow-only risk diagnostics with no order output | design only |
| No-winner interpretation gate | Prevent robustness diagnostics from becoming model selection | design only |

## Boundary

The next step should be a gate/design checkpoint, not an immediate rerun. Any
future robustness execution must be pre-registered and must report all planned
diagnostics without selecting the best result.

Safety state:

- `selection_allowed=False`
- `candidate_decision_allowed=False`
- `training_allowed_now=False`
- `validation_rerun_allowed_now=False`
- `oos_rerun_allowed_now=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`

