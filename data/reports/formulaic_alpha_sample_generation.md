# Small OHLCV Formulaic Alpha Sample Generation

## Purpose

CP-06 creates a small, bounded, paper-only sample of OHLCV formula strings after
CP-01 through CP-05 are complete. It does not compute feature values, evaluate
formulas, train a model, create a trading candidate, rerun OOS, or produce
orders.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `sample_count=6`.
- `evaluation_metric_status=not_calculated`.
- `model_training_status=not_run`.
- `candidate_creation_status=not_created`.
- `order_output=False`.

## Preconditions Used

- CP-01 Deflated Sharpe placeholder report exists.
- CP-02 purged / embargo validation schema plan exists.
- CP-03 post-cutoff OOS proof inventory exists.
- CP-04 `min_history244` PIT universe safety review exists.
- CP-05 formulaic alpha candidate inventory exists.

## Sample Summary

- Formula sample rows: `6`.
- Formula hashes created: `6`.
- Ledger rows added: `6`.
- Feature values generated: `0`.
- Evaluation metrics calculated: `0`.
- Model training runs: `0`.
- Trading candidates created: `0`.

## Generated Samples

The companion CSV records the formula strings and deterministic short SHA-256
hashes. The formulas use only existing OHLCV fields and allowed operators from
the formulaic alpha schema plan:

- `zscore(delta(close, 21))`
- `rank(delta(close, 63))`
- `zscore(delta(close, 126))`
- `rank(zscore(delta(close, 5)))`
- `rank(rolling_std(returns, 20))`
- `rank(correlation(returns, volume, 20))`

## Ledger Update

Six `formulaic_alpha_sample` rows were added to
`data/reports/candidate_trial_ledger.csv`. They are marked
`sample_only_no_eval`, with `entered_comparison=False`,
`production_effect=none`, and `trading_allowed=False`.

## Recommendation

Do not evaluate or select these samples until CP-07 audits PIT controls,
missingness, label isolation, `feature_hash`, and `formula_hash`. The samples
are not direct buy alpha and are not trading candidates.

## Completion Statement

CP-06 is complete as a bounded paper-only sample generation checkpoint. No
formula evaluation, model training, OOS rerun, candidate creation, production
output, broker submission, or order output occurred.
