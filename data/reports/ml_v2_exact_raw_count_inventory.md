# ML v2 Exact Raw Count Inventory

This inventory uses existing local reports only. It does not fetch data, call
APIs, rerun OOS, rerun candidate comparison, train a model, validate a model,
compute performance metrics, or calculate Deflated Sharpe.

## Summary

- source ledger rows: `29`
- inventory rows including summary: `30`
- exact numeric raw-count rows: `7`
- rows still `not_available`: `22`
- exact numeric lower-bound sum: `41`
- exact project-wide raw trial count: `not_available`
- effective trial count: `not_available`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- candidate_promotion: `False`
- broker_submission: `False`
- order_execution: `False`
- trading_allowed: `False`
- production_effect: `none`

## Interpretation

The existing ledger contains some explicit numeric raw counts, but the full
project-wide exact raw trial count is not available. Source report row counts
are included only as audit evidence and are not treated as trial counts.

## Next Safe Action

Run the lineage-resolution audit against this inventory and the existing trial
dependency manifest. ML v2 training and validation remain blocked until a later
gate explicitly allows paper-only training.
