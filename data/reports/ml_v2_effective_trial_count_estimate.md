# ML v2 Effective Trial Count Estimate

This report decides whether an effective trial count can be estimated from the
current raw-count inventory and lineage audit. It does not calculate effective
trial count, Deflated Sharpe, Sharpe, PnL, rankings, or model-selection metrics.

## Result

- effective_trial_count_status: `BLOCK_NO_ESTIMATE`
- effective_trial_count: `not_available`
- raw_trial_count_used: `not_available`
- exact raw-count lower bound: `41`
- lineage resolved groups: `0`
- lineage manual_review_required groups: `0`
- lineage unresolved groups: `23`
- calculation_allowed_now: `False`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- deflated_sharpe_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Reason

The raw-count inventory provides only a lower bound, and every dependency group
remains unresolved. Because independence cannot be established, the effective
trial count remains unavailable.

## Next Safe Action

Run the Deflated Sharpe readiness gate as `BLOCK`, then refresh ML v2 training
readiness. Do not train or validate ML v2 unless a later gate explicitly allows
paper-only training.
