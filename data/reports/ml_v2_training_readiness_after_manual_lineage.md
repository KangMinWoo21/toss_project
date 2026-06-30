# ML v2 Training Readiness After Manual Lineage Review

This report refreshes ML v2 training readiness after the manual lineage review.
It does not train or validate ML v2.

## Gate Result

- gate_result: `BLOCK`
- manual_review_required groups: `19`
- unresolved groups: `3`
- resolved_non_selection_overlay groups: `1`
- selection_trial_allowed: `False`
- training_allowed_now: `False`
- paper_only_training_allowed_next: `False`
- validation_allowed_now: `False`
- model_training_performed: `False`
- validation_run_performed: `False`
- production_effect: `none`
- trading_allowed: `False`

## Reason

Manual lineage review improved classification, but it did not authorize any
independent model-selection trial. Effective trial count remains unavailable and
Deflated Sharpe readiness remains blocked.

## Next Decision

A human source-lineage decision is required to resolve manual-review-required
trial groups. Until then, do not train or validate ML v2.
