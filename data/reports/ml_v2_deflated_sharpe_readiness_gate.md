# ML v2 Deflated Sharpe Readiness Gate

This gate checks whether Deflated Sharpe can be calculated from existing local
approved evidence. It does not calculate Deflated Sharpe, Sharpe, PnL, rankings,
model-selection metrics, train ML v2, validate ML v2, rerun OOS, or rerun
candidate comparison.

## Gate Result

- gate_result: `BLOCK`
- deflated_sharpe_ready: `False`
- deflated_sharpe_calculated: `False`
- model_selection_allowed: `False`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Missing Or Blocked Inputs

- raw Sharpe: `not_available`
- skew: `not_available`
- kurtosis: `not_available`
- sample length: `not_available`
- raw trial count: `lower_bound_only_41_not_complete`
- effective trial count: `not_available`

## Recommendation

Keep model selection and ML v2 training blocked. The next training-readiness
reopen gate should return `BLOCK` unless a separate future loop resolves the
missing trial-count and validation-return inputs.
