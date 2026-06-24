# Goal Mode Checkpoint

Last updated: 2026-06-24 validation comparison evidence hardening

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

- Previous pushed goal commit before this loop:
  `6ad00f0 Require validation sweep evidence`.
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `541` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest default production-check: BLOCK, `BLOCK=8`, `PASS=31`, `WARN=8`.
- Latest candidate-overlay production-check using
  `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`
  reports plus explicit candidate decision: BLOCK, `BLOCK=3`, `PASS=38`,
  `WARN=6`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=349.05` observed).
- Production remains not live-ready.

## Recent Loops

- `925f9e1`: candidate `ACCEPT/APPROVE` requires marker proof plus post-cutoff
  OOS end date after `2026-06-18`; marker-only proof blocks readiness/monthly
  risk.
- Candidate decision CSV now has explicit `post_cutoff_oos_start_date` and
  `post_cutoff_oos_end_date` fields for that proof.
- `84f0999`: `monthly-plan --max-data-stale-days` blocks stale included OHLCV
  before strategy selection or paper order planning.
- Monthly-plan now also blocks stale point-in-time universe snapshots with
  `universe_freshness` before strategy selection.
- Monthly-plan now blocks low point-in-time universe price coverage with
  `universe_price_coverage` before strategy selection.
- Monthly-plan now requires a point-in-time universe before paper-operation
  planning, so universe freshness/coverage gates cannot be bypassed by omission.
- Production readiness now blocks monthly risk reports that omit required
  paper-operation gate evidence rows: PIT universe, market data freshness,
  universe freshness, and universe price coverage.
- Candidate follow-up readiness now blocks completed follow-up decisions that
  are still promotion-blocked, including proofless `ACCEPT` and `PAPER_REVIEW`.
- `ACCEPT`/`APPROVE` candidate decisions now also require consistency with
  validation results: accepted candidates cannot carry rejected comparisons,
  remaining required failures, or new failures.
- Production readiness now blocks performance audit reports that omit required
  evidence rows for scenarios, excess, walk-forward margin, drawdown,
  concentration, and trade activity.
- Production readiness now blocks performance concentration reports that omit
  required concentration evidence columns before accepting PASS/WARN/BLOCK
  status.
- Production readiness now blocks drawdown attribution reports that omit
  required monthly or symbol attribution evidence columns.
- Production readiness now blocks validation failure and remediation reports
  that omit required action/remediation evidence columns.
- Production readiness now blocks validation sweep plan/result reports that omit
  required experiment, command, adoption, or risk-note evidence columns.
- Production readiness now blocks validation comparison and scenario delta
  reports that omit required comparison, metric-delta, or diagnostic evidence
  columns.
- Earlier candidate-safety loop: candidate decisions gate monthly plans and
  production readiness; `PAPER_REVIEW` and missing candidate decisions block.
- Full historical detail is in
  `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_pre_token_trim.md` and git
  history.

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

Best paper-review candidate:

- `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244` has
  `0` required failures in the full validation run.
- Decision: `PAPER_REVIEW`, not adopt/promote.
- Why not promote yet: it relaxes a data-history safety gate and reduces several
  short-duration excess results even though they remain deployable; needs a
  clean full rerun, paper-only OOS/post-cutoff review, and explicit production
  readiness changes before any adoption.

Diagnostic combo remaining failure:

- `proxy_guard_exit_short_minus5_neutral_breadth_cap75` leaves only
  `regime_sideways`, but it worsens that blocker and needs a clean full rerun
  before it can be compared operationally.

## Next Work

Pick one narrow loop:

- `regime_sideways`: the neutral loss guard reduced but did not solve the
  remaining excess gap. New benchmark-excess evidence points to missed
  `2025-04` recovery participation after the `2025-03` drawdown. Contribution
  and selection-rank evidence points to recovery-breadth/selection rather than
  only March loss control. Scenario comparison now shows low-liquidity
  missed-winner drag is shared with passing scenarios, and selected-proxy drag
  is not unique to the failed scenario. Window comparison now shows the blocker
  is in `2025-01-02..2025-04-17`, while the `2024-10..2024-12` pre-window has
  positive excess. January path subperiod comparison shows missed early-January
  timing is not the main cause, contribution-overlap comparison shows the
  selected-target gap is dominated by six-symbol rotation rather than shared
  symbols, and eligibility join shows five reference-only names were excluded by
  the fixed PIT history gate at the failed signal date. Full paper validation
  with `point_in_time_min_history_days=244` resolved all required failures, but
  remains paper-review only. Next paper-only work should stress/OOS-review
  `min_history244` before considering any default change. Avoid broad cash,
  broad stop, or broad proxy cap reuse.
- `walk_forward_003`: now passes under the best candidate. Preserve train-gate
  discipline; do not loosen rejected train windows.

For code changes, use test-first work and finish with focused tests, full
`unittest`, `compileall`, production-check, health-check, checkpoint update,
commit, and push only with explicit approval.
