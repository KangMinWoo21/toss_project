# ML v2 Trial Count And Deflated Sharpe Blocker Audit

This paper-only audit checks whether existing local reports are sufficient to
unblock ML v2 training with trial-count and Deflated Sharpe controls. It does
not train a model, evaluate formulas, compute performance metrics, rerun OOS,
rerun candidate comparison, create a candidate, or change production readiness.

## Result

- blocker_status: `BLOCK`
- training_gate_effect: `BLOCK`
- training_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

ML v2 training remains blocked. Existing reports provide useful trial-ledger
coverage, but not enough evidence to calculate an effective trial count or a
Deflated Sharpe adjustment.

## Evidence

- `data/reports/candidate_trial_ledger.csv`
- `data/reports/deflated_sharpe_placeholder_report.csv`
- `data/reports/ml_v2_training_readiness_gate_stage1_refresh.csv`
- `data/reports/ml_v2_stage1_tiny_experiment_execution_gate.csv`

## Ledger Findings

- candidate trial ledger rows: `29`
- numeric `raw_trial_count` rows: `7`
- `raw_trial_count` unavailable rows: `22`
- numeric raw-trial lower-bound sum: `41`
- numeric `effective_trial_count` rows: `0`
- effective trial count: `not_available`

The raw-trial sum of `41` is only a lower bound because most ledger rows still
use `not_available`. It is not a complete project-wide trial count.

## Deflated Sharpe Findings

The Deflated Sharpe placeholder reserves the required fields but does not fill
them:

- raw Sharpe: `not_available`
- skew: `not_available`
- kurtosis: `not_available`
- sample length: `not_available`
- raw trial count: lower-bound only, not complete
- effective trial count: `not_available`
- adjusted score: `not_calculated`

Therefore Deflated Sharpe is not calculable from current approved local
evidence.

## Training Implication

ML v2 training and validation should not proceed. The safe next action is to
design a dependency-adjusted effective-trial-count method or produce a blocked
training-readiness refresh. No model selection, formula ranking, Sharpe claim,
candidate promotion, broker submission, order execution, or production
readiness change is allowed.
