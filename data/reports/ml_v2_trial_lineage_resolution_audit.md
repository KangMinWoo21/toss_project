# ML v2 Trial Lineage Resolution Audit

This audit classifies trial dependency groups from the manifest as resolved,
unresolved, or manual-review-required using existing local reports only. It does
not calculate effective trial count, Deflated Sharpe, Sharpe, PnL, rankings, or
model-selection metrics.

## Summary

- dependency groups reviewed: `23`
- resolved groups: `0`
- manual_review_required groups: `0`
- unresolved groups: `23`
- raw-trial lower-bound sum retained: `41`
- effective_trial_count_allowed_now: `False`
- deflated_sharpe_allowed_now: `False`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Interpretation

Lineage remains insufficient for an effective trial count. Groups with missing
candidate, formula, or model lineage cannot be treated as independent trials for
model selection.

## Next Safe Action

Create an effective-trial-count estimate report that remains `BLOCK`, or perform
a manual source-lineage review. Do not train or validate ML v2 until a future
gate explicitly allows paper-only training.
