# Goal Mode Checkpoint

Last updated: 2026-06-25 follow-up stress review output value guard

Purpose: keep this file small enough to read on every resume. Full historical
context is archived at:

- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_pre_token_trim.md`
- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_readiness_evidence_loops.md`
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
  `1ac11a3 Block empty validation scenario reports`.
- Latest local goal commit series: pending OOS proof/status hardening,
  post-cutoff OOS period guards, lowercase pending marker detail, and failure
  action/sweep result coverage checks;
  push to `origin` is pending explicit approval.
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `608` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest default production-check: BLOCK, `BLOCK=8`, `PASS=33`, `WARN=8`;
  BLOCK_NAMES=`overall`, `deployment_gate`, `validation_scenarios`,
  `validation_failure_actions`, `validation_remediation`,
  `validation_failure_patterns`, `risk_report`, `performance_report`.
  Performance report now matches validation scenarios:
  `required_scenarios:5 failed of 18 required`.
- Latest candidate-overlay production-check using
  `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`
  reports plus explicit candidate decision: BLOCK, `BLOCK=3`, `PASS=38`,
  `WARN=6`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=357.98` observed).
- Production remains not live-ready.

## Recent Loops

- Older safety, freshness, schema-evidence, and value-evidence loops are in
  `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_readiness_evidence_loops.md`.
- Validation scenario readiness now blocks all-pass scenario reports that
  include required columns but omit core scenario, period, performance, risk,
  universe, deployability, reason, or source values.
- Deployment gate readiness now blocks reports that include required columns
  but omit deployability, reason, source, performance, drawdown, trade-count, or
  universe-bias values.
- Risk report readiness now blocks required paper-operation gate rows that have
  detail evidence but omit status values.
- Performance report readiness now blocks required performance gate rows that
  have detail evidence but omit status values.
- Validation scenario readiness now blocks empty scenario reports instead of
  raising an internal error.
- Sweep result readiness no longer blocks unchanged/skipped no-config rows when
  they explicitly record `NO_CONFIG_CHANGE`.
- Failure drilldown readiness no longer blocks non-walk-forward rows for missing
  train-window metadata when they explicitly record non-applicability.
- Paper-review candidate decisions now write explicit `PENDING_POST_CUTOFF_OOS`
  markers until post-cutoff OOS evidence exists.
- Candidate decision risk details now surface pending post-cutoff OOS status
  when those markers are present.
- Candidate decision readiness details now also surface pending post-cutoff OOS
  status when those markers are present.
- Candidate follow-up readiness details now surface pending post-cutoff OOS
  status for blocked paper-review decisions.
- Candidate summary reports now carry `post_cutoff_oos_status=pending` for
  paper-review candidates waiting on OOS evidence.
- Candidate promotion proof now classifies `PENDING_POST_CUTOFF_OOS` as
  `post_cutoff_oos_pending`, not invalid.
- Candidate promotion proof now also treats partial pending OOS markers as
  `post_cutoff_oos_pending`, not missing.
- Candidate promotion proof treats pending OOS markers case-insensitively.
- Candidate promotion proof now blocks supplied OOS start dates that are not
  after the fixed `2026-06-18` baseline cutoff.
- Candidate promotion proof now blocks supplied OOS periods where start is
  after end.
- Candidate promotion proof now requires a post-cutoff OOS start date as well
  as an end date before an `ACCEPT` decision can pass.
- Candidate promotion proof now treats `oos_review_start_date` pending markers
  as pending instead of invalid.
- Candidate promotion proof now also treats pending OOS markers embedded in
  `decision_reasons` as pending instead of missing.
- Candidate promotion proof now classifies malformed OOS dates embedded in
  `decision_reasons` as invalid instead of missing.
- Candidate promotion proof now accepts whitespace around OOS key/value
  markers embedded in `decision_reasons`.
- Candidate promotion proof now accepts comma-separated OOS key/value markers
  embedded in `decision_reasons`.
- Candidate promotion proof no longer prefix-matches extended pending OOS
  reason values as valid pending markers.
- Candidate promotion proof no longer treats prefixed/fake OOS reason keys as
  valid proof dates.
- Validation remediation readiness now blocks unsafe live/order/trade/fetch
  wording in `next_experiment`.
- Validation remediation readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action`.
- Validation remediation readiness now blocks unsafe live/order/trade/fetch
  wording in `parameter_hints`.
- Validation sweep plan readiness now blocks unsafe live/order/trade/fetch
  wording in `risk_note`.
- Validation sweep plan readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action`.
- Validation sweep plan readiness now blocks unsafe live/order/trade/fetch
  wording in `experiment_id`.
- Validation sweep plan readiness now blocks unsafe live/order/trade/fetch
  wording in `expected_effect`, while allowing explicit `no-trade` gate text.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `risk_note`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `experiment_id`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `candidate_validation_args`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `config_changes`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `validation_scope`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `adoption_status`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `adoption_requirements`.
- Validation sweep results readiness now blocks unsafe live/order/trade/fetch
  wording in `result_summary`.
- Validation candidate follow-up readiness now blocks unsafe live/order/trade
  or fetch wording in pending validation/comparison commands.
- Validation candidate follow-up readiness now blocks unsafe live/order/trade
  or fetch wording in pending `experiment_id` values.
- Validation candidate follow-up readiness now blocks unsafe live/order/trade
  or fetch wording in pending `risk_note` values.
- Validation candidate decision readiness now blocks unsafe live/order/trade or
  fetch wording in `recommendation` values.
- Post-cutoff OOS pending marker detection is centralized; readiness and risk
  details now surface lowercase pending markers as `post_cutoff_oos_status=pending`.
- Validation failure action coverage now blocks when a failed required scenario
  is missing from the failure action report.
- Derived failure/remediation/sweep-plan reports were refreshed from
  `monthly_validation_scenarios_pit_universe.csv`; coverage now passes with
  `5` covered failed scenarios, including `stress_exclude_500pct_winners`.
- Validation sweep result coverage now blocks planned paper experiments missing
  from sweep results. Missing results were refreshed for
  `guarded_loss_position_stop_12`, `market_beta_proxy_cap_75`,
  `neutral_breadth_proxy_cap_50`, and `neutral_proxy_deep_guard_35`; coverage
  now passes with `12` covered sweep results.
- Candidate follow-up was regenerated after sweep result refresh and remains
  `3` rejected follow-up sets; no new improved sweep candidates were introduced.
- Post-cutoff OOS cannot run from local data yet: `data/krx_expanded` max date
  is `2026-06-18` and post-cutoff rows are `0`; no fetch was run.
- Stale performance audit report was refreshed from
  `monthly_validation_scenarios_pit_universe.csv`; `required_scenarios` now
  reports `5 failed of 18 required`, matching validation scenarios.
- `min_history244` paper-only stress/duration review was recorded in ignored
  report `monthly_validation_candidate_stress_review_neutral_loss_guard55_min_history244.csv`:
  stress failed `0/5`, duration failed `0/5`, baseline regressions `0`; still
  blocked from promotion by pending post-cutoff OOS.
- Candidate stress/duration review now has a tested builder/saver and the
  ignored `min_history244` review report was regenerated from validation and
  comparison rows.
- `monthly-compare-validation --stress-review-output` now regenerates that
  paper-only review report; `min_history244` comparison remains IMPROVED with
  baseline failed `5`, candidate failed `0`, review rows `2`.
- Candidate follow-up rows now include `candidate_stress_review_output` and
  comparison commands include `--stress-review-output`; ignored follow-up
  report regenerated with `3` rows.
- Readiness now blocks pending follow-up rows that declare
  `candidate_stress_review_output` but omit `--stress-review-output` from the
  comparison command.
- Readiness follow-up detail now surfaces `next_stress_review_output` for
  pending rows that include the stress review output path.
- Candidate follow-up readiness keeps legacy report compatibility, while
  blocking new-format pending rows that declare stress-review support but leave
  `candidate_stress_review_output` empty.
- Validation failure action readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action` values.
- Validation failure action readiness now blocks unsafe live/order/trade/fetch
  wording in `parameter_hints` values.
- Validation failure pattern readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action` values.
- Validation failure drilldown readiness now blocks unsafe live/order/trade/fetch
  wording in `next_action` values.
- Validation failure drilldown readiness now blocks unsafe live/order/trade/fetch
  wording in `suggested_action` values.
- Full historical detail is in `docs/archive/` and git history.

## Current Best Candidate

`proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244` is the
best paper-review candidate.

Result:

- Current canonical baseline required failures: `5`.
- Candidate required failures: `0`.
- Failed delta: `-5`.
- Decision: `PAPER_REVIEW`, not adopt/promote.

Why useful:

- Resolved all current required failures in the full validation run.
- Fixed current `walk_forward_001`, `walk_forward_003`, and
  `walk_forward_005` blockers without new failures.
- Preserved useful strong-breadth recovery participation while reducing the
  neutral-breadth high-exposure loss cluster in `regime_sideways`.

Why still blocked:

- It relaxes the fixed point-in-time history safety gate to `244`.
- Post-cutoff OOS evidence is still pending.
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

- `stress_exclude_500pct_winners`: max drawdown breach.
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
