# Goal Mode Checkpoint

Last updated: 2026-06-24 min-history 244 validation

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
- Latest completed local goal commit:
  `Record min-history 244 validation` (current HEAD after this loop).
- Expected dirty worktree: many pre-existing unrelated modified/untracked files
  remain outside recent goal loops. Do not revert them.
- Latest full tests: `python -m unittest discover -s tests` PASS, `522` tests.
- Latest compile: `python -m compileall -q backtester` PASS.
- Latest default production-check: BLOCK, `BLOCK=8`, `PASS=31`, `WARN=8`.
- Latest candidate-overlay production-check using
  `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`
  reports plus explicit candidate decision: BLOCK, `BLOCK=3`, `PASS=38`,
  `WARN=6`.
- Latest health-check: WARN only because scalper data is stale
  (`age_hours=346.36` observed).
- Production remains not live-ready.

## Latest Loop

Ran a paper-only full validation of the current best candidate with the PIT
minimum history gate relaxed from `252` to `244` rows.

Changed behavior:

- No strategy default, validation gate, order, live behavior, Toss API, or
  baseline behavior changed.
- Generated:
  `data/reports/monthly_validation_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv`.

Verification:

- Validation run: `18` scenarios, `failed_required=0`, deployment gate
  `deployable=True`, reason `passed`.
- Comparison versus current `252`-day best candidate:
  `comparison_status=IMPROVED`, baseline required failures `1`, candidate
  required failures `0`, resolved `regime_sideways`, new failures `0`,
  decision `PAPER_REVIEW`.
- Regressions to watch, all still deployable: `duration_1y` excess delta
  `-4.6393`, `duration_6m` `-3.2402`, `duration_3m` `-2.2312`,
  `walk_forward_003` `-1.2941`.
- Final verification: full `unittest` PASS (`511` tests), compile PASS,
  production-check remains BLOCK, health-check remains WARN from stale scalper
  data only.
- Follow-up readiness overlay generated candidate-specific failure-pattern and
  monthly risk reports. This removes readiness BLOCKs only when all
  production-check inputs are pointed at the candidate artifacts; the default
  canonical check remains BLOCK and the candidate remains `PAPER_REVIEW`.
- Candidate decision recommendations now explicitly require paper-only handling,
  full validation rerun, OOS/post-cutoff review, and explicit production
  readiness changes before promotion.
- `PAPER_REVIEW` candidate decisions now block production readiness promotion.
  Current data ends at `2026-06-18`, so no post-cutoff/OOS review artifact
  exists yet.
- Missing or empty candidate-decision reports now also block readiness when a
  candidate overlay is explicitly supplied.
- Accepted candidate decisions require explicit `oos_review_passed` and
  `production_readiness_approved` markers in `decision_reasons`; manual
  `ACCEPT` without those markers blocks readiness.
- `monthly-plan` can now take `--candidate-decision-report`; when supplied,
  paper-review/rejected candidates or accepted candidates without promotion
  proof block the monthly risk report. The `min_history244` candidate monthly
  plan now reports `risk_status BLOCK` from `candidate_decision:PAPER_REVIEW`.
- The same plan writes `execution_allowed=False`, `execution_mode=blocked`,
  `risk_status_BLOCK` for all `5` generated orders.
- Candidate-named deployment/performance reports now require a candidate
  decision report automatically; omitting it keeps monthly-plan
  `risk_status BLOCK` with detail `candidate artifacts detected`.

Residual evidence:

- Prior entry-month comparison showed `start_date_delta_days=12`,
  reference monthly excess higher by `+10.2896`, target exposure higher by
  `+0.7425`, selected-proxy delta higher by `+7.4382`, and shared symbols
  `6/12`.
- Prior path split shows the failed pre-split `2025-01-02..2025-01-13` return was
  `+1.6148`, average exposure `0.303`, and still `-6.1225` versus the
  reference post-split return.
- On shared dates `2025-01-14..2025-01-31`, failed post-split return was only
  `+0.4198` with average exposure `0.3104`, while reference post-split return
  was `+7.7374` with average exposure `0.8791`.
- Failed post-split delta versus reference post-split: return `-7.3175`,
  exposure `-0.5687`, shared symbols `6/12`; diagnostic:
  `reference_post_outperformed;reference_exposure_higher;symbol_rotation`.
- Prior target-contribution overlap: selected-total contribution gap `+7.4578`;
  shared symbols contribute `-0.0520` of the gap, while rotation symbols
  contribute `+7.5098` (`100.6973%` of total gap).
- Shared symbols:
  `000270;000660;005380;042660;068270;373220`.
- Rotation symbols: failed-only
  `005490;010130;051910;055550;086790;105560`; reference-only
  `000100;007660;011790;196170;277810;328130`.
- New selected-symbol rotation detail: `18` selected-union rows, with `6`
  failed-only, `6` reference-only, and `6` shared symbols.
- Reference-only names: failed-side selection diagnostics were
  `missed_inside_proxy_liquidity_cutoff=4` and
  `missed_outside_proxy_liquidity_cutoff=2`; reference-side diagnostics were
  `selected_proxy_winner=4` and `selected_proxy_loser=2`.
- Rotation-role aggregates: failed-only average failed-period return `+0.1271`
  and contribution-gap sum `-0.0161`; reference-only average failed-period
  return `+26.6961` and contribution-gap sum `+7.5569`; shared contribution-gap
  sum `-0.0300`.
- New eligibility join: `18` rows, failed-side universe exclusions `5`,
  reference-side exclusions `0`; all failed exclusions were
  `insufficient_history` with `history_rows=244; required=252`.
- Reference-only eligibility: `000100`, `007660`, `196170`, `277810`, and
  `328130` were failed-side `insufficient_history`; `011790` was included but
  outside the failed proxy liquidity cutoff.
- Interpretation: missed early-January timing and shared-name exposure scale are
  not the main target-contribution cause. The failed January proxy selection
  mostly omitted high-return reference-only names because they did not yet meet
  the fixed `252`-row PIT history gate at signal date `2024-12-30`, then became
  eligible by the reference signal date `2025-01-13`.
- New min-history `244` evidence: `regime_sideways` improved from failing to
  passing with excess `+3.5847` and max drawdown `-21.5169`. The candidate also
  passed `walk_forward_001` (`+3.0038` excess), `walk_forward_003` (`+8.7530`),
  and `walk_forward_005` (`+4.4114`).

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
