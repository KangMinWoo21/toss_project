# ML v2 Training Readiness Gate Reopen

This gate reopens the ML v2 training-readiness question using the latest exact
raw-count inventory, lineage audit, effective-trial-count status, Deflated
Sharpe readiness, feature coverage, and safety evidence. It does not train or
validate ML v2.

## Gate Result

- gate_result: `BLOCK`
- training_allowed_now: `False`
- paper_only_training_allowed_next: `False`
- validation_allowed_now: `False`
- model_training_performed: `False`
- validation_run_performed: `False`
- production_effect: `none`
- trading_allowed: `False`

## Blocking Evidence

- exact raw trial count: lower-bound only, full count `not_available`
- lineage resolution: `0` resolved, `23` unresolved
- effective trial count: `not_available`
- Deflated Sharpe readiness: `BLOCK`
- feature merge readiness: `WARN_STAGE1_NOT_FULL_COVERAGE`

## Decision

Do not train or validate ML v2. Create a blocked training report rather than a
model artifact. No production, broker, order, candidate, or strategy effect is
allowed.
