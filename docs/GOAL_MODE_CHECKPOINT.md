# Goal Mode Checkpoint

Last updated: 2026-06-24 token-trim checkpoint loop

This file is intentionally short so goal-mode resumes do not spend large token
budgets rereading old loops. The full pre-trim checkpoint was preserved at:

- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_pre_token_trim.md`

## Objective

Make this repository a safe paper-operation trading research and monitoring
system, not a live-trading bot.

Primary focus:

- Data quality and point-in-time correctness.
- Walk-forward validation reliability.
- Drawdown, liquidity, and cost realism.
- Production readiness and health monitoring.
- Clear reports and next actions.

Do not implement real order execution.

## Safety Rules

- Keep `PRODUCTION_TRADING_ENABLED` off by default.
- Tests must not call real Toss API endpoints.
- Never print, log, or commit `.env` secrets.
- Monthly workflows may create plans, diagnostics, and reports only.
- Prefer deterministic `unittest` tests with temp files and fixtures.
- Preserve existing CLI compatibility.
- Treat production/readiness BLOCK results as hard stops.

## Context Operation Rules

Automatic compaction is not preferred in the middle of an active work loop.

Consider compaction only after an important loop is cleanly closed:

- Changes are organized.
- Required tests and verification were run.
- Generated reports and key numbers were checked.
- `docs/GOAL_MODE_CHECKPOINT.md` was updated.
- Commit and push are complete when needed.

If context becomes too large and reasoning quality is likely to degrade, Codex
may compact earlier.

After compaction, first actions must always be:

1. Read the goal objective file.
2. Read `docs/GOAL_MODE_CHECKPOINT.md`.
3. Run `git status --short`.
4. Check latest `production-check` and `health-check` reports.
5. Reconfirm rejected candidates and remaining blockers before continuing.

Compaction summaries must include:

- Latest commit.
- Changed files.
- Passing tests.
- Production and health status.
- Generated reports.
- Accepted or rejected candidates with reasons.
- Remaining BLOCK causes.
- Exact next task.

## Current Repository State

Latest pushed commit:

- `2c77fad Add proxy guard recovery exit candidate`

Expected dirty worktree:

- Many pre-existing modified/untracked files remain outside the latest
  goal-mode loop, including modules such as `backtester/scalper.py`,
  `backtester/engine.py`, `backtester/strategies.py`, related tests, and
  several docs/scripts.
- Do not revert or clean those files unless the user explicitly asks.
- Recent goal-loop files around `monthly_rebalance`, CLI tests, and this
  checkpoint were clean after the latest commit.

Latest verification:

- `python -m unittest discover -s tests`: PASS, `456` tests.
- `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: BLOCK,
  `BLOCK=8`, `PASS=31`, `WARN=8`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`:
  WARN, only because scalper data is stale.

Latest reports checked:

- `data/reports/production_readiness.csv`: mtime `2026-06-24 01:38:04`,
  `BLOCK=8`, `PASS=31`, `WARN=8`.
- `data/reports/health_status.json`: mtime `2026-06-24 01:38:09`,
  overall `WARN`; all checks PASS except stale `scalper_data`.
- `data/reports/monthly_validation_candidate_decision_proxy_guard_exit_short_minus5.csv`:
  `PAPER_REVIEW`, `IMPROVED`, baseline failed required `5`, candidate failed
  required `2`, failed delta `-3`.

## Latest Token-Trim Loop

Compressed this checkpoint from `3614` lines to `228` lines and preserved the
full pre-trim file in the archive path listed above. This was a documentation
and context-management change only; no strategy behavior changed.

Verification for this loop:

- `python -m unittest discover -s tests`: PASS, `456` tests.
- `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: BLOCK,
  expected current safety gate state.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`:
  WARN, only because scalper data is stale (`age_hours=336.80` observed).

## Latest Loop Summary

Added and validated a default-off, paper-only proxy guard recovery-exit
candidate:

- Config field:
  - `market_beta_proxy_reversal_guard_recovery_exit_short_return_pct`
- CLI option:
  - `--market-beta-proxy-reversal-guard-recovery-exit-short-return-pct`
- Candidate label:
  - `proxy_guard_exit_short_minus5`
- Candidate options:
  - `--market-beta-proxy-reversal-guard-max-exposure 0.55`
  - `--market-beta-proxy-reversal-guard-medium-lookback-days 40`
  - `--market-beta-proxy-reversal-guard-medium-return-pct 35`
  - `--market-beta-proxy-reversal-guard-short-lookback-days 20`
  - `--market-beta-proxy-reversal-guard-short-max-return-pct 5`
  - `--market-beta-proxy-reversal-guard-extreme-return-pct 50`
  - `--market-beta-proxy-reversal-guard-medium-drawdown-pct -10`
  - `--market-beta-proxy-reversal-guard-recovery-exit-short-return-pct -5`

Behavior:

- Default remains off at `0.0`.
- If a non-extreme drawdown-based proxy guard cap would apply and the
  short-window proxy basket return is already at or below `-5%`, the guard
  exits instead of capping.
- Extreme medium overheat still caps, preserving stress loss-cap behavior.
- This is paper/backtest/report-only and does not add real order execution.

Key candidate evidence:

- `walk_forward_005`: total `18.4931%`, buy-hold `14.0817%`, excess
  `4.4114%`, max DD `-15.2709%`; `2026-03` stays capped and `2026-04`
  recovers uncapped.
- `stress_exclude_500pct_winners`: total `29.4016%`, excess `27.9113%`,
  max DD `-21.2614%`; guarded loss caps remain aligned.
- `walk_forward_002`: total `15.8455%`, excess `0.8313%`, max DD `-4.4510%`;
  profitable continuation remains uncapped.
- Full validation improved required failures from `5` to `2`, with no new
  failures.

Decision:

- Keep `proxy_guard_exit_short_minus5` as the best current paper-review
  candidate.
- Do not adopt/promote it because required blockers remain.

## Generated Reports From Latest Strategy Loop

The full list is preserved in the archive. Most important current reports:

- `data/reports/monthly_validation_candidate_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_failures_candidate_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_remediation_candidate_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_sweep_plan_candidate_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_deployment_gate_candidate_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_comparison_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_comparison_deltas_proxy_guard_exit_short_minus5.csv`
- `data/reports/monthly_validation_candidate_decision_proxy_guard_exit_short_minus5.csv`
- `data/reports/walk_forward_005_validation_train_proxy_guard_exit_short_minus5_recovery_exit_diagnostics.csv`
- `data/reports/stress_proxy_guard_exit_short_minus5_drawdown_pressure.csv`

## Rejected Or Held Candidates

Do not adopt these as-is:

- `proxy_chase_guard_55_med35_short30`: rejected; introduced
  `walk_forward_002` failure by capping a profitable continuation.
- `neutral_breadth_proxy_cap_50`: rejected; introduced full-period and
  stress-slippage regressions.
- `position_stop_12`, `weak_cash_10_position_stop_12`,
  `weak_defense_cash_10`: rejected due unresolved core failures and/or
  regressions.
- `neutral_breadth_proxy_cap_75`: held/unchanged.
- `target_persistence_2`: held/unchanged.
- `proxy_reversal_guard_55_extreme60`: paper-review only; improved but still
  failed required scenarios.
- `proxy_guard_short5_extreme50_mdd10`: paper-review only; improved but left
  `regime_sideways`, `walk_forward_003`, and `walk_forward_005`.

## Remaining BLOCK Causes

Production baseline still blocks on five required validation failures:

- `stress_exclude_500pct_winners`: max drawdown breach, about `-28.0835%`.
- `regime_sideways`: negative excess, about `-7.1648%`.
- `walk_forward_001`: negative excess, about `-0.7420%`.
- `walk_forward_003`: train window rejected, train excess about `-1.3447%`.
- `walk_forward_005`: negative excess, about `-5.5812%`.

Latest paper-review candidate reduces candidate failures to two:

- `regime_sideways`: negative excess about `-5.2338%`, max DD about
  `-21.7254%`.
- `walk_forward_003`: train window rejected; train excess about `-0.3002%`,
  test excess about `8.7530%`, max DD about `-7.1592%`.

Production remains BLOCK. Health remains WARN only because scalper data is
stale.

## Next Highest-Value Work

Continue with the two remaining candidate failures:

- `regime_sideways`: focus on unchanged high-exposure loss months
  `2024-10`, `2024-11`, and `2024-12`; avoid broad parameter sweeps.
- `walk_forward_003`: preserve train gates and analyze direct-alpha train
  ineligibility/stability evidence before changing behavior.

The next strategy loop should be one of:

1. Add diagnostics or a narrow candidate for `regime_sideways` early
   neutral-breadth high-exposure proxy losses, while preserving
   `walk_forward_002`, `walk_forward_004`, and resolved `walk_forward_005`.
2. Return to `walk_forward_003` direct-alpha ineligibility and decompose why
   train candidates remain unstable or non-eligible.

For code changes, use test-first changes and rerun at minimum:

- focused tests,
- `python -m unittest discover -s tests`,
- `python -m compileall -q backtester`,
- production-check with blocked exit allowed,
- health-check with blocked exit allowed.
