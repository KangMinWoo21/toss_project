# Goal Mode Checkpoint

Last updated: 2026-06-24 regime sideways combo diagnostics loop

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
- Latest strategy commit: `2c77fad Add proxy guard recovery exit candidate`.
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `459` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest production-check: BLOCK, `BLOCK=8`, `PASS=31`, `WARN=8`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=337.22` observed).
- Production remains not live-ready.

## Latest Loop

Focused on `regime_sideways` because `walk_forward_003` remains a train-gate
issue that should not be overridden without stronger stability evidence.

Focused attribution for `proxy_guard_exit_short_minus5`:

- Reproduced `regime_sideways`: total `-7.2966%`, excess `-5.2338%`,
  max DD `-21.7254%`.
- Guard outcomes: `missed_high_exposure_loss=3` (`2024-10`, `2024-11`,
  `2024-12`), `loss_cap_aligned=1` (`2025-03`), `gain_preserved=3`.
- Versus baseline: `2025-03` return delta `+2.6350%`; `2025-04` return drag
  `-0.7512%`; early high-exposure neutral-breadth losses were unchanged.

Tested paper-only combo:
`proxy_guard_exit_short_minus5_neutral_breadth_cap75`.

- Main validation rows completed, but the CLI timed out before writing the
  deployment-gate CSV. Treat as diagnostic only.
- Required failures improved from `2` to `1`; `walk_forward_003` resolved.
- Remaining failure: `regime_sideways`, worsened to excess `-5.8965%`,
  max DD `-21.8429%`.
- Decision report: `PAPER_REVIEW`, not adopt/promote.
- Regime path comparison versus `proxy_guard_exit_short_minus5` showed
  `107` equity-regression days, `47` drawdown-regression days, `35`
  symbol-rotation days, worst equity delta `-657162.0359` on `2024-10-29`.
- Root cause evidence: lower neutral-breadth target weights dropped `010130`
  from actual held positions in early months; broad cap is not a clean
  exposure-only fix.

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
  `2024-11`, `2024-12`, especially why lower target weights drop expensive
  symbols such as `010130`; avoid broad neutral-breadth caps as-is.
- `walk_forward_003`: continue from the new stability summary; inspect the
  negative subwindow symbol/path-drift rows before changing gates.

For code changes, use test-first work and finish with focused tests, full
`unittest`, `compileall`, production-check, health-check, checkpoint update,
commit, and push.
