# ML Financial Feature Readiness Report

## Do Not Trade / PIT Audit Only

This report records a limited OpenDART sample for paper-only ML feature readiness. It does not train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- `training_allowed_now=False`.
- `trading_allowed=False`.
- `production_effect=none`.
- `post_cutoff_data_used_for_train=False`.
- Protected candidate unchanged.

## PIT Summary

- observation_rows=459
- usable_from_check=PASS
- correction_lineage=PASS
- readiness_status=BLOCK

## Next Safe Action

Use this sample only for Phase 7 financial feature merge audit. Keep `training_allowed_now=False` until merge coverage, missingness, and leakage checks pass under a separately approved paper-only experiment.
