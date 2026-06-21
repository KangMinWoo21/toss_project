# Retail Edge Strategy Notes

This project now separates three momentum-rotation profiles:

- `balanced`: default profile for lower drawdown and steadier rolling-window behavior.
- `aggressive`: higher-return profile with larger drawdown tolerance.
- `retail`: aggressive signal profile plus liquidity and participation controls for smaller-cap universes.

## Why Retail Can Differ From Institutions

Institutions usually face capacity, mandate, benchmark, compliance, and market-impact constraints. A retail-sized account can sometimes exploit opportunities that are too small or operationally annoying for large capital, but only if order sizing is disciplined.

Practical retail advantages:

- Smaller order size can enter/exit lower-liquidity stocks without dominating daily volume.
- No benchmark mandate means the strategy can sit in cash when breadth is weak.
- Concentrated positions are possible, though drawdown risk rises quickly.
- The universe can be refreshed faster when new leaders emerge.

Practical retail risks:

- Small caps have wider spreads, gaps, halts, and disclosure/event risk.
- Backtests can overstate fills if liquidity is not capped.
- A strategy that works at 10 million KRW may not work at 1 billion KRW.

## Implemented Controls

The `retail` preset currently uses:

- `min_average_trading_value=300_000_000`
- `max_trade_participation_rate=0.005`
- `liquidity_window_days=20`

This means candidate stocks must clear a minimum 20-day average trading value, and each buy order is capped at 0.5% of recent average daily trading value. On the current 15 large-cap KRX universe this cap is not binding, so `retail` currently matches `aggressive`. It becomes meaningful after adding mid/small-cap symbols.

## Recommended Next Data Expansion

To test the real retail edge, expand beyond the current large-cap universe:

- KOSPI 200 plus KOSDAQ 150.
- Filter out stocks with insufficient listing history.
- Keep minimum 20-day average trading value configurable.
- Compare `balanced`, `aggressive`, and `retail` separately.
- Report capacity: max deployable capital per strategy before the participation cap starts reducing position sizes.

## Execution Rules Before Live Use

- Trade only after the daily signal is finalized; do not use same-day close to decide same-day entry.
- Use limit orders around the open or VWAP-style splitting for thin stocks.
- Stop trading automatically if data is missing, API order rejection rises, or realized slippage exceeds the backtest assumption.
- Keep daily logs of intended order, actual fill, slippage, and rejected quantity.

## Monthly Plan Safety Gate

`monthly-plan` now writes a separate risk report before any future live executor should be allowed to place orders:

```powershell
python -m backtester monthly-plan --data-dir "data\krx_expanded" --as-of 2026-06-20 --cash 10000000 --day-start-equity 10000000 --risk-output "data\reports\monthly_risk_report.csv"
```

The gate reports `PASS`, `WARN`, or `BLOCK`.

- `data/KILL_SWITCH` blocks trading immediately when the file exists.
- Signal data older than 7 days is blocked by default.
- Daily loss beyond 3% is blocked when `--day-start-equity` is provided.
- Total target exposure is capped at 80% by default, leaving a 20% cash buffer.
- Single order value, total buy value, total sell value, order count, invalid sell quantity, skipped orders, and malformed orders are checked.
- A blocked or warned plan should not be wired to live order execution.

`monthly-validate` writes `data/reports/monthly_validation_scenarios.csv` and updates `data/reports/monthly_deployment_gate.csv`. `monthly-plan` reads that deployment gate by default and blocks the order plan if the latest validation gate is not deployable.

```powershell
python -m backtester monthly-validate --data-dir "data\krx_expanded" --start 2024-01-01 --end 2026-06-18 --initial-cash 10000000
```

Current deployment criteria:

- Excess return versus equal-weight buy and hold must be positive.
- Max drawdown must be no worse than -25%.
- Universe-bias warning must be false unless explicitly overridden.
- Duration, regime, and stress scenarios must all pass.
- Stress checks include 500% winner exclusion, top-winner exclusion, slippage x2/x3, and liquidity top-50.

Default point-in-time universe filters:

- Use only candles available on or before the signal date.
- Require at least 252 prior daily rows.
- Require the latest signal-date close to be at least 1,000 KRW.
- Exclude stocks already up more than 300% over the prior 252 trading rows.
- Keep only the top 100 symbols by signal-date 20-day average trading value.

Important limitation: the current 2024-2026 expanded KRX universe still shows survivorship/extreme-winner bias. The conservative plan can beat equal-weight buy and hold on the base test, but it fails an extreme-winner exclusion stress test. The default safety gate therefore blocks live deployment for now. Treat this strategy as paper/live-simulation only until more point-in-time universe data and additional holdout periods are validated.
