# Strategy Comparison Review

As of the latest local reports, no strategy should be promoted to normal-size
live trading. The current monthly rebalance strategy remains the best operating
candidate because it has the broadest validation harness and explicit live
blocking gates.

## Compared Approaches

### Monthly Rebalance

Source: `data/reports/monthly_validation_scenarios_pit_universe.csv`

Strengths:

- Passes 18 required validation scenarios.
- Uses point-in-time universe snapshots.
- Includes duration, stress, regime, and walk-forward checks.
- Has production readiness and risk-report gates.
- Current paper plan is blocked/scaled when performance is `WARN`.

Weaknesses:

- Minimum walk-forward excess return is only `+3.2425%`.
- Worst scenario max drawdown is `-22.0847%`.
- Full-period excess return is much larger than median walk-forward excess,
  which suggests return concentration.

Current role:

- Primary paper/live-simulation strategy.
- Not normal-size live ready while production readiness is `WARN`.

### Momentum Rotation

Source:

- `data/reports/momentum_rotation_preset_summary.csv`
- `data/reports/momentum_rotation_walk_forward_validation.csv`
- `data/reports/momentum_rotation_holdout_validation.csv`

Strengths:

- High raw and excess returns in long full-period tests.
- Captures strong trend regimes well.

Weaknesses:

- Max drawdown in stored summaries reaches roughly `-24%` to `-27%`.
- Walk-forward rows include a failed accepted state in prior reports.
- More exposed to winner concentration and regime reversal.

Current role:

- Research benchmark, not live candidate.

### Leader Swing / Regime Leader

Source:

- `data/reports/leader_window_study_summary.csv`
- `data/reports/leader_regime_window_summary.csv`

Strengths:

- Defensive windows show strong relative protection versus buy and hold.
- DART-positive overlays improved some sideways/down windows.

Weaknesses:

- Up-regime windows underperform buy and hold by a wide margin.
- Best use appears to be risk overlay or defensive sleeve, not standalone core.

Current role:

- Secondary research strategy and defensive comparison tool.

### News, SNS, and Disclosure Event Overlay

Source:

- `data/events/krx15_dart_2018_2026.csv`
- `data/events/005930_google_news.csv`
- `docs/event-data-integration.md`

Strengths:

- Can veto negative recent events.
- Can apply small position weight adjustments.
- Supports source-specific weighting such as `news=1,sns=0.25,dart=0.5`.

Weaknesses:

- Current broad historical event file covers only 15 large symbols.
- DART-only event overlay did not reduce drawdown or fix the weakest
  walk-forward window in the latest local test.
- Wider news/SNS coverage is required before treating this as a material alpha
  input.

Current role:

- Risk/context overlay only.

## Recommended Decision

Keep the monthly rebalance strategy as the main paper candidate, keep live
execution blocked by `production-check --strict`, and use event data only as a
small overlay until broader source coverage is available.

Near-term improvements:

1. Expand point-in-time OHLCV coverage for missing KRX symbols.
2. Build broader event data coverage beyond the current 15 large DART symbols.
3. Keep testing event overlays on walk-forward windows, not just full period.
4. Avoid reducing exposure mechanically when it lowers the weakest
   walk-forward margin more than it reduces drawdown.
5. Keep paper monthly plan generation on the cloud VM, but leave live orders
   disabled.
