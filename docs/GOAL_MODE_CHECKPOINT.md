# Goal Mode Checkpoint

Last updated: 2026-06-24 buyable proxy candidate loop

Purpose: keep this file small enough to read on every resume. Full historical
context is archived at:

- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_pre_token_trim.md`
- Future short goal prompt: `docs/goal-mode-minimal-prompt.md`

## Objective

Build a safe paper-operation trading research and monitoring system. Do not
build or enable live order execution.

## Hard Safety Rules

- No real orders, no live-trading default, no Toss API calls in tests.
- Keep `PRODUCTION_TRADING_ENABLED` disabled by default.
- Never print, summarize, commit, or copy `.env` secrets.
- Monthly workflows are report/diagnostic/plan-only.
- Treat production/readiness BLOCK as a hard stop.
- Preserve deterministic `unittest` coverage and CLI compatibility.

## Resume Protocol

After compaction or a fresh resume:

1. Read the goal objective file.
2. Read this checkpoint.
3. Run `git status --short`.
4. Check latest `production-check` and `health-check` reports.
5. Reconfirm rejected candidates and current blockers before editing.

Keep future checkpoint updates short. Archive old loop detail instead of
appending long command logs or full report lists here.

## Current State

- Previous pushed checkpoint/context commit before this loop:
  `9a96e5c Compact goal mode prompt context`.
- Latest completed local goal commit before this loop:
  `c097d81 Add monthly execution gap diagnostics`.
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `462` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest production-check: BLOCK, `BLOCK=8`, `PASS=31`, `WARN=8`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=338.14` observed).
- Production remains not live-ready.

## Latest Loop

Added a default-off paper-only market beta proxy buyability candidate switch.

Changed behavior:

- New config flag: `market_beta_proxy_buyable_only=False`.
- New CLI flag on monthly plan/backtest/attribution/validate/train-diagnostics:
  `--market-beta-proxy-buyable-only`.
- When enabled, market beta proxy fallback reuses
  `compress_decision_to_buyable_targets`; direct `market_beta` ETF fallback is
  unchanged.
- Defaults and live/order behavior are unchanged.

TDD:

- RED: config/CLI tests failed on the missing flag; the first fixture also
  exposed an invalid empty train slice before the intended fallback path.
- GREEN: targeted tests PASS, `5` tests; monthly+CLI modules PASS, `223`
  tests.

Focused `regime_sideways` evidence with current
`proxy_guard_exit_short_minus5` guard settings plus buyable proxy:

- Output prefix:
  `data/reports/regime_sideways_proxy_guard_exit_short_minus5_buyable_proxy_*`.
- Headline: total return `-7.87%`, excess `-5.80%`, max DD `-21.84%`.
- Execution gaps: rows `45`; buyable compression reasons include
  `buyable_targets_11of12` (`15` rows) and `buyable_targets_9of12` (`9`
  rows). Prior below-one-share misses are removed.
- Comparison versus `proxy_guard_exit_short_minus5`: changed decision rows `4`,
  symbol rotation rows `4`, new drawdown breach months `0`.
- Path comparison is worse: equity regression days `108/126`,
  drawdown regression days `101/126`, worst equity delta
  `2024-12-09 = -172507.1649`.
- Decision: reject as-is; do not run full validation or promote.

Prior execution-gap context to preserve:

- `proxy_guard_exit_short_minus5_execution_gap.csv`: rows `55`;
  `target_underfilled_after_rebalance=51`, `target_value_below_one_share=4`.
- `proxy_guard_exit_short_minus5_neutral_breadth_cap75_execution_gap.csv`:
  rows `57`; `target_underfilled_after_rebalance=51`,
  `target_value_below_one_share=6`.

## Current Best Candidate

`proxy_guard_exit_short_minus5` remains the best fully validated reference
candidate.

Result:

- Baseline required failures: `5`.
- Candidate required failures: `2`.
- Failed delta: `-3`.
- Decision: `PAPER_REVIEW`, not adopt/promote.

Why useful:

- Fixed `stress_exclude_500pct_winners`, `walk_forward_001`, and
  `walk_forward_005` without new failures.
- Preserved useful guarded loss caps while allowing `walk_forward_005`
  recovery to re-enter.

Why still blocked:

- `regime_sideways` still has negative excess.
- `walk_forward_003` still has train-window rejection.

## Do Not Reuse As-Is

- `proxy_chase_guard_55_med35_short30`: introduced `walk_forward_002` failure.
- `neutral_breadth_proxy_cap_50`: full-period/stress-slippage regressions.
- `proxy_guard_exit_short_minus5_neutral_breadth_cap75`: diagnostic-only;
  reduced failures to `1` but timed out before deployment-gate output and
  worsened `regime_sideways`.
- `position_stop_12`, `weak_cash_10_position_stop_12`,
  `weak_defense_cash_10`: unresolved blockers/regressions.
- `neutral_breadth_proxy_cap_75`, `target_persistence_2`: held/unchanged.
- `proxy_reversal_guard_55_extreme60`, `proxy_guard_short5_extreme50_mdd10`:
  paper-review only; improved but still left required failures.
- `proxy_guard_exit_short_minus5 + market_beta_proxy_buyable_only`: removes
  below-one-share gaps but worsens most `regime_sideways` path days.

## Remaining Blockers

Production baseline required failures:

- `stress_exclude_500pct_winners`: max DD about `-28.0835%`.
- `regime_sideways`: excess about `-7.1648%`.
- `walk_forward_001`: excess about `-0.7420%`.
- `walk_forward_003`: train rejected; train excess about `-1.3447%`.
- `walk_forward_005`: excess about `-5.5812%`.

Best candidate remaining failures:

- `regime_sideways`: excess about `-5.2338%`, max DD about `-21.7254%`.
- `walk_forward_003`: train rejected; train excess about `-0.3002%`, test
  excess about `8.7530%`, max DD about `-7.1592%`.

Diagnostic combo remaining failure:

- `proxy_guard_exit_short_minus5_neutral_breadth_cap75` leaves only
  `regime_sideways`, but it worsens that blocker and needs a clean full rerun
  before it can be compared operationally.

## Next Work

Pick one narrow loop:

- `regime_sideways`: inspect actual path/position drift in `2024-10`,
  `2024-11`, `2024-12`. The buyable proxy test worsened December via symbol
  rotation; inspect removed/added proxy names around `2024-12-09` before
  changing weighting again. Avoid broad neutral-breadth caps as-is.
- `walk_forward_003`: continue from the new stability summary; inspect the
  negative subwindow symbol/path-drift rows before changing gates.

For code changes, use test-first work and finish with focused tests, full
`unittest`, `compileall`, production-check, health-check, checkpoint update,
commit, and push.
