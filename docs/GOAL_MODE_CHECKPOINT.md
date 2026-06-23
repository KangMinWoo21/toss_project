# Goal Mode Checkpoint

Last updated: 2026-06-24 train stability summary diagnostics loop

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

Added paper-only train stability summary diagnostics to
`monthly-train-decision-diagnostics`.

Changed behavior:

- New pure report builder: `analyze_monthly_train_stability_summary`.
- New CSV writer: `save_monthly_train_stability_summary`.
- New CLI option: `--stability-summary-output`.
- No trading behavior changed; this is report-only.

TDD:

- RED: new summary tests failed on missing functions; CLI test failed on
  unknown `--stability-summary-output`.
- GREEN: targeted tests PASS, `3` tests.
- Extra RED/GREEN: split semicolon-composed underperformance drivers into
  separate `token=count` values.

Generated reports:

- `data/reports/walk_forward_003_train_decision_proxy_guard_exit_short_minus5.csv`
- `data/reports/walk_forward_003_train_stability_proxy_guard_exit_short_minus5.csv`
- `data/reports/walk_forward_003_train_stability_summary_proxy_guard_exit_short_minus5.csv`
- `data/reports/walk_forward_003_train_stability_symbol_proxy_guard_exit_short_minus5.csv`
- `data/reports/walk_forward_003_train_path_drift_experiment_proxy_guard_exit_short_minus5.csv`

Key `walk_forward_003` finding:

- Summary rows: `2`.
- Direct candidate row: `balanced`.
- Direct candidate train decisions summarized: `6`.
- Direct candidate low-positive-ratio decisions: `6`.
- Counted stability subwindows: `6`; positive `0`, negative `6`.
- Negative subwindow ratio: `1.0`.
- Average stability excess: `-31.7252%`; worst: `-53.3186%`.
- Dominant failed reason: `nonpositive_excess`.
- Driver counts:
  `benchmark_positive_selection_nonpositive=3`,
  `holding_path_differs_from_selection_snapshot=3`, `no_trades=3`.
- Diagnostic:
  `low_positive_ratio_due_to_negative_stability_windows`.
- No-direct-candidate row: `7` decisions, all `no_train_symbols`.
- Path-drift experiment rows suggest only paper-review candidates:
  `test_stricter_target_persistence`, not adopted.

## Current Best Candidate

`proxy_guard_exit_short_minus5` is the best current paper-review candidate.

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

## Next Work

Pick one narrow loop:

- `regime_sideways`: inspect high-exposure loss months `2024-10`,
  `2024-11`, `2024-12`; avoid broad sweeps.
- `walk_forward_003`: continue from the new stability summary; inspect the
  negative subwindow symbol/path-drift rows before changing gates.

For code changes, use test-first work and finish with focused tests, full
`unittest`, `compileall`, production-check, health-check, checkpoint update,
commit, and push.
