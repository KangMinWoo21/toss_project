# ML v2 Training Readiness After Trial Manifest

This refresh uses POST-06 and POST-08 trial-count evidence to decide whether ML
v2 training or validation can proceed. It does not train a model, validate a
model, evaluate formulas, compute performance metrics, rerun OOS, rerun
candidate comparison, create a candidate, or change production readiness.

## Gate Result

- gate_result: `BLOCK`
- training_allowed_now: `False`
- paper_only_training_allowed_next: `False`
- validation_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Reason

POST-06 and POST-08 improved the visibility of trial-count blockers, but they
did not remove them:

- raw-trial evidence is still a lower bound only: `41`
- effective trial count remains `not_available`
- all dependency groups retain incomplete-lineage warnings
- Deflated Sharpe inputs remain missing
- tiny experiment execution remains `BLOCK`
- ML v2 validation still has no available model

## Recommendation

Do not train or validate ML v2 yet. The next safe action is either an exact
raw-count inventory for unresolved ledger rows or a lineage-resolution audit.
All outputs remain paper-only.
