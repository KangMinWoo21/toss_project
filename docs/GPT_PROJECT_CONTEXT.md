# GPT Project Context: Toss Securities Paper-Operation Trading System

Last updated: 2026-06-25

## One-Line Verdict

This repository is useful for paper-operation research and monitoring, but it is
not ready for real-money automated trading. `production-check` is still
`BLOCK`, and `health-check` is `WARN` because scalper data is stale.

## Safety Rules

- Do not add or enable real order execution.
- Keep live trading disabled by default.
- Do not call Toss APIs or network services in tests.
- Do not print, summarize, or commit `.env` secrets.
- Treat production/readiness/risk `BLOCK` as a hard stop.
- Use data through `2026-06-18` as fixed baseline; later data is post-cutoff
  paper-only OOS evidence only.

## Current Status

- Latest pushed commit: `0acf392 Block empty followup stress review output`.
- Production readiness: `BLOCK=8`, `PASS=33`, `WARN=8`.
- Health: `PASS=7`, `WARN=1`; WARN is `scalper_data`.
- Production remains not live-ready.
- Push to `origin master` completed through `0acf392`.

## Production BLOCK Names

- `overall`
- `deployment_gate`
- `validation_scenarios`
- `validation_failure_actions`
- `validation_remediation`
- `validation_failure_patterns`
- `risk_report`
- `performance_report`

## Required Validation Failures

- `stress_exclude_500pct_winners`: max drawdown breach.
- `regime_sideways`: negative excess return.
- `walk_forward_001`: negative excess return.
- `walk_forward_003`: train window rejected.
- `walk_forward_005`: negative excess return.

## Current Best Candidate

`proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`

- Baseline failed required scenarios: `5`.
- Candidate failed required scenarios: `0`.
- Failed delta: `-5`.
- Decision: `PAPER_REVIEW`, not adopt/promote.
- Stress review: `0/5` failed, baseline regressions `0`.
- Duration review: `0/5` failed, baseline regressions `0`.
- Promotion remains blocked by pending post-cutoff OOS and explicit production
  readiness requirements.

## Recent Progress

- Pending post-cutoff OOS proof handling was hardened.
- Candidate decision/follow-up readiness now surfaces pending OOS markers.
- Unsafe live/order/trade/fetch wording is blocked across candidate, sweep,
  remediation, failure action, and drilldown reports.
- Failure action and sweep result coverage checks were added.
- Derived validation failure/remediation/sweep reports were refreshed.
- Performance audit was refreshed to match validation failures:
  `required_scenarios:5 failed of 18 required`.
- `min_history244` paper stress/duration review now has tested builder/saver
  support.
- `monthly-compare-validation --stress-review-output` regenerates paper-only
  candidate stress review reports.
- Candidate follow-up commands now include stress review output paths.
- Readiness blocks missing/empty stress review output wiring for new-format
  follow-up rows.

## Do Not Reuse As-Is

- `proxy_chase_guard_55_med35_short30`: introduced `walk_forward_002`.
- `neutral_breadth_proxy_cap_50`: full-period/stress-slippage regressions.
- `proxy_guard_exit_short_minus5_neutral_breadth_cap75`: worsened
  `regime_sideways` path.
- `guarded_loss_position_stop_12`, `position_stop_12`,
  `weak_cash_10_position_stop_12`, `weak_defense_cash_10`: unresolved
  blockers/regressions.
- `neutral_breadth_proxy_cap_75`, `target_persistence_2`: held/unchanged.
- `proxy_reversal_guard_55_extreme60`, `proxy_guard_short5_extreme50_mdd10`:
  paper-review only; still left required failures.
- Buyable-only or unbuyable-cash-reserve proxy variants worsened
  `regime_sideways` path.

## Current Dirty Worktree

There are many pre-existing unrelated modified/untracked files. Do not revert
or stage them unless explicitly requested.

## Core Verification Commands

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

Latest verified counts before this context refresh:

- Tests: `613 PASS`.
- Compileall: PASS.
- Production: `BLOCK=8`, `PASS=33`, `WARN=8`.
- Health: `PASS=7`, `WARN=1`.

## Next Best Work

- Keep production/readiness `BLOCK` as hard stop.
- Continue from `regime_sideways` and paper-only `min_history244` evidence.
- Do not tune on post-cutoff data; use it only for paper-only OOS review.
- Avoid broad cash, broad stop, or broad proxy cap reuse.
- Keep checkpoint updates short in `docs/GOAL_MODE_CHECKPOINT.md`.
