# ML v2 No-Selection DSR Exception Gate

## Decision

`ALLOW_NO_SELECTION_TRAINING`

The prior ML v2 block remains correct for model selection: exact trial counts
and effective trial counts are still incomplete, and Deflated Sharpe is not
calculation-ready. This gate does not weaken that rule.

The exception is narrow: a single fixed model, fixed feature set, fixed split,
and no hyperparameter sweep is not a selection contest. Therefore Deflated
Sharpe is deferred for later model-selection work and is not calculated here.

## Boundaries

- This gate cannot create, promote, demote, or replace a candidate.
- This gate cannot authorize production output.
- This gate cannot authorize broker submission or order execution.
- This gate only allows the next readiness gate to decide whether a paper-only
  fixed-spec training run may proceed.

Safety state remains `production_effect=none` and `trading_allowed=False`.
