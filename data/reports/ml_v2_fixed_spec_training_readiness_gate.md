# ML v2 Fixed-Spec Training Readiness Gate

## Decision

`ALLOW_PAPER_ONLY_TRAINING`

This does not authorize model selection. It only allows the next checkpoint to
run one bounded, fixed-spec, paper-only ML v2 training/validation experiment.

## Why This Resolves The Current Block

The current block came from treating ML v2 as a model-selection or alpha-selection
problem while trial counts, effective trial counts, and Deflated Sharpe inputs
were incomplete. This gate removes selection from the next step:

- one model type
- one feature set
- one split policy
- no hyperparameter sweep
- no formula ranking
- no candidate creation
- no production artifact

The Stage 1 feature evidence is local and PIT-audited, but not full coverage.
Therefore the allowed next step is bounded paper-only training only.

## Next Action

Run the next checkpoint as a single fixed-spec paper-only training and
validation report. Keep all outputs research-only and disabled by default.

Safety state remains:

- `training_allowed_now=False` for this checkpoint
- `paper_only_training_allowed_next=True`
- `validation_allowed_now=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `production_effect=none`
- `trading_allowed=False`
