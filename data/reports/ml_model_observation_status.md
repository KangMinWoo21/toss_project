# ML Model Paper-Only Observation Status

## Paper-Only Observation Status

This report records the current shadow-score observation window. It does not promote candidates, generate order output, submit to a broker, regenerate a monthly plan, change strategy parameters, enable production, or authorize trading.

- Observation months: `101`.
- Observation basis: `historical_backfill`.
- Observation maturity: `True`.
- Post-cutoff train leakage: `PASS`.
- Performance stability: `historical_backfill_stable`.
- Drawdown: `-0.6520`.
- Turnover: `turnover=0.1700`.
- Coverage: `symbols=5;months=101`.
- Candidate promotion: `False`.
- Trading allowed: `False`.
- Production effect: `none`.
- Protected candidate unchanged.

Historical backfill is used only when explicitly requested and only from existing local rows.

## Status Rows

| Metric | Status | Value |
| --- | --- | --- |
| summary | paper_only_observation_mature | paper_only_observation_mature |
| observation_basis | PASS | historical_backfill |
| post_cutoff_train_leakage | PASS | False |
| observation_months | PASS | 101 |
| sufficient_observation_months | PASS | True |
| performance_stability | PASS | historical_backfill_stable |
| drawdown | PASS | -0.6520 |
| turnover | PASS | turnover=0.1700 |
| coverage | PASS | symbols=5;months=101 |
| candidate_promotion | PASS | False |
