# ML v2 Trial Dependency Group Manifest

This report applies the POST-07 grouping method to the existing candidate trial
ledger as a manifest only. It does not calculate effective trial count,
Deflated Sharpe, Sharpe, PnL, rankings, model-selection metrics, or formula
performance.

## Summary

- source ledger rows: `29`
- dependency groups: `23`
- groups with incomplete lineage: `23`
- raw-trial lower-bound sum across numeric groups: `41`
- effective_trial_count_calculated: `False`
- deflated_sharpe_calculated: `False`
- training_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Interpretation

The manifest provides a conservative grouping surface for future trial-count
work. It is not an effective trial count. Groups with `not_available` lineage
must remain unresolved until source reports provide enough detail to classify
independence.

## Next Safe Action

Either create an exact raw-count inventory for unresolved rows or produce a
blocked ML v2 training-readiness refresh. Do not train or validate ML v2 until a
future gate explicitly allows it.
