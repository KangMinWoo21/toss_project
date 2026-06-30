# ML v2 Blocked Training Report After Reopen

This report records the result of the ML v2 training-readiness reopen gate. The
gate returned `BLOCK`, so ML v2 training was not run.

## Result

- gate_result: `BLOCK`
- training_status: `blocked_not_run`
- model_artifact_created: `False`
- model_training_performed: `False`
- dataset_merge_performed: `False`
- validation_allowed_next: `False`
- candidate_creation: `False`
- candidate_promotion: `False`
- broker_submission: `False`
- order_execution: `False`
- trading_allowed: `False`
- production_effect: `none`

## Reason

The reopen gate remains blocked because raw trial count is lower-bound only,
lineage is unresolved, effective trial count is unavailable, Deflated Sharpe is
blocked, and Stage 1 feature merge readiness is not full readiness evidence.

## Validation Status

Validation is not allowed because no ML v2 model was trained and no model
artifact exists. Do not create comparison claims for ML v2 performance.
