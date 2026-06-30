# ML v2 Manual Lineage Review

This review manually classifies dependency groups using local report names,
trial ids, method families, formula hashes, and scenario labels. It does not
fetch data, train a model, validate a model, evaluate formulas, compute
performance metrics, calculate effective trial count, or calculate Deflated
Sharpe.

## Summary

- dependency groups reviewed: `23`
- manual_review_required: `19`
- resolved_non_selection_overlay: `1`
- unresolved: `3`
- selection_trial_allowed: `False`
- effective_trial_count_allowed_now: `False`
- deflated_sharpe_allowed_now: `False`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Interpretation

Manual pattern review improves classification, but it does not provide enough
source lineage to calculate effective trial count or reopen ML v2 training.
Most groups remain manual-review-required, and no group is allowed as an
independent model-selection trial.

## Next Safe Action

Create a training-readiness refresh after manual lineage review. It should stay
`BLOCK` unless a future human source-lineage decision explicitly resolves the
manual-review-required groups.
