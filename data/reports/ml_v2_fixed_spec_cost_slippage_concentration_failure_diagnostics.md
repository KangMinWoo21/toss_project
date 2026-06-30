# ML v2 Fixed-Spec Cost, Slippage, Concentration, And Failure Diagnostics

This report adds fixed-spec ML v2 cost, slippage, concentration, and failure
diagnostics using existing local reports only. It does not fetch data, call
APIs, rerun OOS, rerun candidate comparison, train a model, rerun validation,
generate orders, create candidates, change strategy parameters, submit to a
broker, execute orders, or authorize trading.

## Diagnostic Result

`final_status=WARN_BLOCKED_NOT_LIVE_READY`

ML v2 fixed-spec remains paper-only research. The current evidence supports
risk documentation, not live readiness or candidate selection.

## Key Findings

| Area | Finding |
| --- | --- |
| Cost realism | Blocked: ML v2 fixed-spec has no trades, weights, fills, turnover, or order rows. |
| Slippage | Context only: existing slippage fields are not ML v2 fixed-spec estimates. |
| Turnover | Blocked: no ML v2 rebalance path or target weights exist. |
| Concentration | Warning: bounded diagnostic covers 98 joined rows, 5 symbols, and 23 date groups. |
| Return contribution | Blocked: no ML v2 month/symbol return-contribution artifact exists. |
| Label/failure risk | Warning: rolling-origin split and primary validation have small positive-class counts. |
| Overfit context | Warning remains unresolved from the fixed-spec overfit analysis. |
| Failure taxonomy | Existing ML failure rows are context only, not direct ML v2 fixed-spec failure attribution. |

## Safety State

- `model_winner_declared=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`
- `model_training_performed_now=False`
- `validation_rerun_performed_now=False`
- `oos_rerun_performed_now=False`
- `candidate_comparison_rerun_performed_now=False`

Next safe checkpoint: design the ML v2 hybrid risk overlay with all overlays
disabled by default and risk-control-only.
