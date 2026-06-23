# Goal Mode Checkpoint

Last updated: 2026-06-24 monthly benchmark-excess diagnostic

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
  `30fbb87 Refresh best candidate comparison evidence`.
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `484` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest production-check: BLOCK, `BLOCK=8`, `PASS=31`, `WARN=8`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=343.27` observed).
- Production remains not live-ready.

## Latest Loop

Added a report-only monthly benchmark-excess diagnostic for the remaining
`regime_sideways` negative-excess blocker.

Changed behavior:

- New `monthly-attribution --benchmark-output` writes per-month strategy return,
  equal-weight buy-hold return, and monthly excess.
- No strategy default, validation gate, order, live behavior, Toss API, or
  baseline behavior changed.
- Generated the best-candidate `regime_sideways` benchmark-excess report under
  separate `_current` output paths.

Verification:

- RED: analyzer/saver imports failed; CLI help lacked `--benchmark-output`.
- GREEN: targeted benchmark-excess tests PASS, monthly module PASS (`194`
  tests), CLI module PASS (`51` tests).
- Final verification: full `unittest` PASS (`484` tests), compile PASS,
  production-check remains BLOCK, health-check remains WARN from stale scalper
  data only.

Residual evidence:

- Best-candidate `regime_sideways` benchmark-excess rows: `7`.
- Negative-excess months: `4`; positive-excess months: `3`.
- Largest monthly excess drag is `2025-04`: strategy `+0.5697%` versus
  benchmark `+5.5069%`, monthly excess `-4.9372%`, worst drawdown `-21.7902%`.
- Other negative-excess months: `2025-01` (`-1.6436%`), `2024-12`
  (`-1.2740%`), `2025-03` (`-0.9108%`).
- Interpretation: March remains the largest absolute strategy loss, but April
  is the main residual benchmark gap. Next work should investigate missed
  recovery participation after the March drawdown, not broaden the March loss
  cap or reuse stopped-out candidates.

Prior `regime_sideways` path-summary evidence versus
`proxy_guard_exit_short_minus5`:

- `neutral_breadth_cap75`: `107/126` equity-regression days, `47`
  drawdown-regression days, `35` symbol-rotation days; worst equity delta
  `-657162.0359` on `2024-10-29`.
- `buyable_proxy`: `108/126` equity-regression days, `101`
  drawdown-regression days, `39` symbol-rotation days; worst equity delta
  `-172507.1649` on `2024-12-09`.
- `cash_reserve_proxy`: `104/126` equity-regression days, `68`
  drawdown-regression days, `39` symbol-rotation days; worst equity delta
  `-271623.8209` on `2025-01-08`.
- Decision: do not promote these variants. The blocker is not explained by
  below-one-share execution gaps alone; broad proxy reweighting/buyability/cash
  reserve changes degrade path behavior across many days.

Prior `walk_forward_003` no-trade context to preserve:

Focused `walk_forward_003` evidence for `proxy_guard_exit_short_minus5`:

- Baseline persistence `1`: avg stability excess `-31.7252%`, worst
  `-53.3186%`, negative windows `6/6`; no-trade `3`, positive-benchmark
  no-trade `3`, total no-trade benchmark return `43.4006%`.
- Persistence `2`: avg `-25.1776%`, worst `-38.1485%`, negative windows
  still `6/6`; no-trade `6`, positive-benchmark no-trade `6`, total
  no-trade benchmark return `151.0656%`.
- Persistence `3`: avg `-25.1776%`, worst `-38.1485%`, negative windows
  still `6/6`; no-trade `6`, positive-benchmark no-trade `6`, total
  no-trade benchmark return `151.0656%`.
- Decision: do not promote stricter target persistence as-is. It suppresses
  path drift by suppressing direct-alpha trades, increasing opportunity cost.

Prior `walk_forward_003` diagnostic context to preserve:

- Train decision rows: `13`; `no_train_symbols=7`,
  `no_eligible_direct_candidate=6`.
- The train rejection is evidence-backed; do not loosen gates.

Prior buyability context to preserve:

- `proxy_guard_exit_short_minus5 + market_beta_proxy_buyable_only`: removed
  below-one-share gaps but worsened most `regime_sideways` path days
  (`108/126` equity regression days).
- `proxy_guard_exit_short_minus5_execution_gap.csv`: rows `55`;
  `target_underfilled_after_rebalance=51`, `target_value_below_one_share=4`.
- `proxy_guard_exit_short_minus5_neutral_breadth_cap75_execution_gap.csv`:
  rows `57`; `target_underfilled_after_rebalance=51`,
  `target_value_below_one_share=6`.
- `proxy_guard_exit_short_minus5 + market_beta_proxy_unbuyable_cash_reserve`:
  total `-9.21%`, excess `-7.15%`, max DD `-21.78%`; rejected as-is.

## Current Best Candidate

`proxy_guard_exit_short_minus5_neutral_loss_guard55` is the best fully
validated paper-review candidate.

Result:

- Current canonical baseline required failures: `4`.
- Candidate required failures: `1`.
- Failed delta: `-3`.
- Decision: `PAPER_REVIEW`, not adopt/promote.

Why useful:

- Fixed current `walk_forward_001`, `walk_forward_003`, and
  `walk_forward_005` blockers without new failures.
- Preserved useful strong-breadth recovery participation while reducing the
  neutral-breadth high-exposure loss cluster in `regime_sideways`.

Why still blocked:

- `regime_sideways` still has negative excess.
- Production/readiness remains BLOCK and target scale stays `0`.

## Do Not Reuse As-Is

- `proxy_chase_guard_55_med35_short30`: introduced `walk_forward_002` failure.
- `neutral_breadth_proxy_cap_50`: full-period/stress-slippage regressions.
- `proxy_guard_exit_short_minus5_neutral_breadth_cap75`: diagnostic-only;
  reduced failures to `1` but worsened `regime_sideways`; path summary shows
  `107/126` equity-regression days versus `proxy_guard_exit_short_minus5`.
- `guarded_loss_position_stop_12`, `position_stop_12`,
  `weak_cash_10_position_stop_12`,
  `weak_defense_cash_10`: unresolved blockers/regressions.
- `neutral_breadth_proxy_cap_75`, `target_persistence_2`: held/unchanged.
- `proxy_reversal_guard_55_extreme60`, `proxy_guard_short5_extreme50_mdd10`:
  paper-review only; improved but still left required failures.
- `proxy_guard_exit_short_minus5 + market_beta_proxy_buyable_only`: removes
  below-one-share gaps but worsens most `regime_sideways` path days
  (`108/126` equity-regression days).
- `proxy_guard_exit_short_minus5 + market_beta_proxy_unbuyable_cash_reserve`:
  makes cash reserve explicit but worsens `regime_sideways` excess and path
  (`104/126` equity-regression days).

## Remaining Blockers

Production baseline required failures:

- `regime_sideways`: excess about `-7.1648%`, max DD about `-23.9059%`.
- `walk_forward_001`: excess about `-0.7420%`, max DD about `-25.1309%`.
- `walk_forward_003`: train rejected; train excess about `-1.3447%`.
- `walk_forward_005`: excess about `-5.2167%`, max DD about `-20.2645%`.

Best candidate remaining failure:

- `regime_sideways`: excess `-4.0548%`, max DD `-21.7902%`.

Diagnostic combo remaining failure:

- `proxy_guard_exit_short_minus5_neutral_breadth_cap75` leaves only
  `regime_sideways`, but it worsens that blocker and needs a clean full rerun
  before it can be compared operationally.

## Next Work

Pick one narrow loop:

- `regime_sideways`: the neutral loss guard reduced but did not solve the
  remaining excess gap. New benchmark-excess evidence points to missed
  `2025-04` recovery participation after the `2025-03` drawdown. Next paper-only
  work should inspect April holdings/benchmark contribution before broadening
  any March loss cap.
- `walk_forward_003`: now passes under the best candidate. Preserve train-gate
  discipline; do not loosen rejected train windows.

For code changes, use test-first work and finish with focused tests, full
`unittest`, `compileall`, production-check, health-check, checkpoint update,
commit, and push only with explicit approval.
