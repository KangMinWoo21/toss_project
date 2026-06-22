# Goal Mode Checkpoint

Last updated: 2026-06-22 20:58 KST

## Objective

Make this repository a safe paper-operation trading research system, not a live-trading bot.

Primary focus:

- Data quality and point-in-time correctness
- Walk-forward validation reliability
- Drawdown, liquidity, and cost realism
- Production readiness and health monitoring
- Clear human-readable reports and next actions

Do not implement real order execution.

## Safety Rules

- Keep `PRODUCTION_TRADING_ENABLED` off by default.
- Tests must not call real Toss API endpoints.
- Never print, log, or commit `.env` secrets.
- Monthly workflows may create plans and reports only.
- Prefer deterministic `unittest` tests with temp files and fixtures.
- Preserve existing CLI compatibility.

## Current Status

- `python -m unittest discover -s tests`: PASS, 424 tests.
- `python -m compileall -q backtester`: PASS.
- `production-check`: BLOCK by design, because 5 required validation scenarios still fail.
- `health-check`: WARN, only because scalper data is stale.
- Candidate follow-up state: all completed full-validation candidates remain rejected; latest target-only `neutral_proxy_deep_guard_35` is `UNCHANGED`.
- Failure-pattern and failure-drilldown reports are generated and integrated into `production-check`.
- `validation_failure_drilldown`: PASS. Evidence gaps are now closed.

## Latest Loop Results

Added a paper-only validation candidate summary/ranking report that combines candidate decision, scenario delta, and path-comparison evidence:

- Added `build_monthly_validation_candidate_summary`.
- Added `save_monthly_validation_candidate_summary`.
- Added CLI:
  - `python -m backtester monthly-candidate-summary`
- Inputs:
  - `--decision`: candidate decision CSV from `monthly-compare-validation`,
  - `--deltas`: scenario delta CSV from `monthly-compare-validation`,
  - `--path-comparison`: optional path-comparison CSV, repeatable.
- Output:
  - `data/reports/monthly_validation_candidate_summary.csv`
- This is diagnostic-only and paper-only. It does not change strategy behavior, deployment gates, execution planning, or any Toss/API behavior.

The summary report ranks candidates by:

- failures resolved,
- new failures introduced,
- drawdown-buffer regressions,
- path equity regression/improvement days,
- path drawdown regression days,
- symbol-rotation days,
- higher-turnover and higher-trade-cost days,
- worst path drawdown delta,
- minimum path equity delta,
- maximum rolling-peak delta.

Generated report:

- `data/reports/monthly_validation_candidate_summary.csv`

Current candidate summary for `neutral_breadth_proxy_cap_50`:

- `candidate_rank=1`.
- `decision=REJECT`.
- `resolved_count=1`.
- `new_failure_count=2`.
- `drawdown_buffer_regression_count=2`.
- `path_days_compared=86`.
- `path_equity_regression_days=0`.
- `path_equity_improved_days=86`.
- `path_drawdown_regression_days=86`.
- `path_higher_turnover_days=4`.
- `path_min_equity_delta=133957.5058`.
- `path_worst_drawdown_delta_pct=-1.1549`.
- `path_max_rolling_peak_delta=387782.9119`.
- `evaluation_score=-490`.
- Summary:
  - `resolved=1; new_failures=2; drawdown_buffer_regressions=2; path_equity_regression_days=0; path_drawdown_regression_days=86; path_higher_turnover_days=4`.

Interpretation:

- `neutral_breadth_proxy_cap_50` still should not be adopted.
- It preserves positive absolute path equity versus baseline across the compared windows, but it worsens drawdown relative to the higher rolling peak on every compared path day.
- The regression is not symbol rotation (`path_symbol_rotation_days=0`) and is not an absolute-equity regression (`path_equity_regression_days=0`).
- The practical next research step is still a narrow drawdown-buffer preserving acceptance/ranking rule or path-aware candidate filter, not a broad exposure cap.

Verification in this loop:

- Baseline before edits:
  - `python -m unittest discover -s tests`: PASS, `421` tests.
  - `python -m compileall -q backtester`: PASS.
- RED check:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_candidate_summary_combines_delta_and_path_evidence tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_candidate_summary_writes_csv tests.test_cli.CliTests.test_monthly_candidate_summary_cli_combines_deltas_and_path_comparison`: failed because `build_monthly_validation_candidate_summary`, `save_monthly_validation_candidate_summary`, and `monthly-candidate-summary` did not exist.
- Targeted GREEN:
  - same command: PASS.
- Related regression scope:
  - `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `186` tests.
- Full verification:
  - `python -m unittest discover -s tests`: PASS, `424` tests.
  - `python -m compileall -q backtester`: PASS.
  - `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
  - `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=308.13` observed).

Next recommended action:

- Keep `neutral_breadth_proxy_cap_50` rejected.
- Use `data/reports/monthly_validation_candidate_summary.csv` as the candidate triage front door.
- Next, add a path-aware candidate acceptance rule/report that explicitly rejects candidates when:
  - absolute path equity improves,
  - but hard-gate drawdown buffer falls below `-25%`,
  - and the improvement comes from a higher rolling peak rather than same-window recovery.
- Continue direct-alpha stability diagnostics for `walk_forward_003`/`walk_forward_004` before loosening train gates.

Previous loop:

Added a paper-only candidate acceptance diagnostic for candidates that improve return/equity evidence but lose hard drawdown-gate buffer:

- Extended `compare_monthly_validation_scenario_deltas` so a new `max_drawdown_breach` failure is classified as:
  - `equity_improved_but_drawdown_buffer_worse` when candidate excess return improves but max drawdown becomes worse enough to fail the gate,
  - `drawdown_buffer_regression` when drawdown worsens without improved return,
  - `candidate_introduced_drawdown_breach` when the new drawdown breach is not explained by a worse drawdown delta.
- Extended `build_monthly_validation_candidate_decision` so these cases add:
  - `drawdown_buffer_regressions=<n>` to `decision_reasons`,
  - a recommendation to not adopt the candidate and inspect path-level drawdown-buffer diagnostics.
- This is diagnostic-only and paper-only. It does not change strategy behavior, deployment gates, execution planning, or any Toss/API behavior.

Regenerated candidate comparison/decision reports:

- `data/reports/monthly_validation_comparison_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_comparison_deltas_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_candidate_decision_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_comparison.csv`
- `data/reports/monthly_validation_comparison_deltas.csv`
- `data/reports/monthly_validation_candidate_decision.csv`
- `data/reports/production_readiness.csv`
- `data/reports/production_readiness_report.md`
- `data/reports/health_status.json`
- `data/reports/health_status.md`

Candidate acceptance finding:

- `neutral_breadth_proxy_cap_50` remains `REJECT`.
- `full_period` is now a `NEW_FAILURE` with diagnostic `equity_improved_but_drawdown_buffer_worse`.
  - `excess_return_delta=+0.0247`.
  - `max_drawdown_delta=-1.0891`.
- `stress_slippage_x3` is now a `NEW_FAILURE` with diagnostic `equity_improved_but_drawdown_buffer_worse`.
  - `excess_return_delta=+0.3978`.
  - `max_drawdown_delta=-1.0388`.
- Candidate decision now reports:
  - `drawdown_buffer_regressions=2`,
  - `new_failure_diagnostics=equity_improved_but_drawdown_buffer_worse=2`.
- `production_readiness_report.md` now surfaces this exact candidate rejection reason in both the readiness table and action list.

Verification in this loop:

- RED check:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_compare_monthly_validation_scenario_deltas_flags_drawdown_buffer_regression tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_candidate_decision_rejects_drawdown_buffer_loss`: failed because drawdown-buffer regression was still reported as `candidate_introduced_failure` and candidate decision did not include `drawdown_buffer_regressions=1`.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_compare_monthly_validation_scenario_deltas_flags_drawdown_buffer_regression tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_candidate_decision_rejects_drawdown_buffer_loss`: PASS.
- Related regression scope:
  - `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `183` tests.
- Full verification:
  - `python -m unittest discover -s tests`: PASS, `421` tests.
  - `python -m compileall -q backtester`: PASS.
  - `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
  - `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=306.49` observed).

Next recommended action:

- Keep `neutral_breadth_proxy_cap_50` rejected.
- Do not broaden exposure caps from this evidence.
- Next, add a narrow candidate ranking/summary report that combines scenario deltas with path-comparison rows so rejected candidates can be ranked by:
  - failures resolved,
  - new failures introduced,
  - drawdown buffer lost,
  - equity improvement preserved,
  - whether path-level symbol rotation or turnover caused the regression.
- Continue focusing on persistent blockers:
  - `regime_sideways`,
  - `walk_forward_005`,
  - `stress_exclude_500pct_winners`,
  - direct-alpha train weakness around `walk_forward_003`.

Previous loop:

Added paper-only daily path attribution diagnostics to explain why `neutral_breadth_proxy_cap_50` worsened March-April 2025 drawdown even though same-month decisions and selected symbols were identical:

- Added `analyze_monthly_path_attribution`.
- Added `compare_monthly_path_attribution_reports`.
- Added `save_monthly_path_attribution`.
- Added `save_monthly_path_attribution_comparison`.
- Extended `python -m backtester monthly-attribution` with:
  - `--path-output`
- Added CLI:
  - `python -m backtester monthly-compare-paths`
- The path report reconstructs daily:
  - equity,
  - rolling peak,
  - cash,
  - position market value,
  - exposure,
  - position count,
  - total position quantity,
  - held symbols and quantities,
  - buy/sell/turnover value,
  - estimated fee/tax trade cost,
  - drawdown,
  - daily return.
- The path comparison report compares baseline vs candidate by `date` and flags diagnostics such as:
  - `equity_regression`,
  - `equity_improved`,
  - `drawdown_regression`,
  - `drawdown_improved`,
  - `exposure_increased`,
  - `exposure_reduced`,
  - `position_quantity_changed`,
  - `symbol_rotation`,
  - `higher_turnover`,
  - `higher_trade_cost`.
- This is diagnostic-only and paper-only. It does not change strategy behavior or execution behavior.

Generated or refreshed path attribution reports:

- `data/reports/full_period_baseline_path_attribution.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_path_attribution.csv`
- `data/reports/stress_slippage_x3_baseline_path_attribution.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_path_attribution.csv`

Generated path comparison reports for `2025-02-28` through `2025-04-30`:

- `data/reports/full_period_path_comparison_neutral_breadth_proxy_cap_50.csv`
- `data/reports/stress_slippage_x3_path_comparison_neutral_breadth_proxy_cap_50.csv`

Path findings:

- `full_period`
  - Compared days: `43`.
  - `equity_regression_days=0`.
  - `drawdown_regression_days=43`.
  - Minimum candidate equity delta was still positive: `+149,049.6019`.
  - Maximum candidate equity delta: `+315,022.2237`.
  - Worst drawdown delta: `-1.1549` percentage points.
  - Maximum rolling-peak delta: `+387,782.9119`.
  - `symbol_rotation_days=0`.
  - `higher_turnover_days=2`.
  - `higher_trade_cost_days=2`.
  - On `2025-04-07`, baseline drawdown was `-24.044%` and candidate drawdown was `-25.1331%`, despite candidate equity being higher by `+154,349.6019`.
- `stress_slippage_x3`
  - Compared days: `43`.
  - `equity_regression_days=0`.
  - `drawdown_regression_days=43`.
  - Minimum candidate equity delta was still positive: `+133,957.5058`.
  - Maximum candidate equity delta: `+290,511.4143`.
  - Worst drawdown delta: `-1.1128` percentage points.
  - Maximum rolling-peak delta: `+359,575.5263`.
  - `symbol_rotation_days=0`.
  - `higher_turnover_days=2`.
  - `higher_trade_cost_days=2`.
  - On `2025-04-07`, baseline drawdown was `-24.0105%` and candidate drawdown was `-25.0493%`, despite candidate equity being higher by `+140,457.5058`.

Interpretation:

- The new `full_period` and `stress_slippage_x3` failures from `neutral_breadth_proxy_cap_50` are not caused by lower absolute equity in March-April 2025.
- They are rolling-peak/drawdown-buffer failures:
  - the candidate's November-December 2024 neutral-breadth de-risking improved equity and raised the later rolling peak,
  - the March-April 2025 decision rows and held symbol sets stayed aligned with baseline,
  - but the candidate carried slightly higher exposure/quantity after the higher-equity path,
  - so drawdown as a percentage of the higher peak crossed the hard `-25%` gate even while candidate equity remained above baseline.
- This means a broad additional exposure cap is likely the wrong next move.
- The next candidate should focus on peak-relative drawdown buffer preservation, for example gating candidate adoption against path-level drawdown-buffer loss or using a narrowly triggered peak/drawdown guard, while preserving the November-December benefit and avoiding same-month decision churn.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `415` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new path diagnostic tests failed because `analyze_monthly_path_attribution`, `compare_monthly_path_attribution_reports`, `save_monthly_path_attribution`, `save_monthly_path_attribution_comparison`, and `monthly-compare-paths` did not exist.
- Additional RED check: rolling peak tests failed because `rolling_peak` and `rolling_peak_delta` were not yet emitted.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_path_attribution_reconstructs_cash_positions_turnover_and_cost tests.test_monthly_rebalance.MonthlyRebalanceTests.test_compare_monthly_path_attribution_reports_flags_equity_and_holding_path_regression tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_path_attribution_reports_write_csv tests.test_cli.CliTests.test_monthly_compare_paths_cli_writes_daily_path_delta_report`: PASS.
- Related regression scope:
  - `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `181` tests.
- Full verification:
  - `python -m unittest discover -s tests`: PASS, `419` tests.
  - `python -m compileall -q backtester`: PASS.
  - `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
  - `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=306.26` observed).

Next recommended action:

- Do not adopt `neutral_breadth_proxy_cap_50`.
- Do not treat March-April 2025 as an absolute-equity regression; candidate equity is higher during the inspected path window.
- Add a candidate acceptance/ranking diagnostic that rejects candidates when they improve equity but reduce hard-gate drawdown buffer below `-25%`.
- If testing a strategy tweak next, use a narrow peak-relative drawdown-buffer guard rather than broad neutral/strong breadth exposure caps.

Previous loop:

Added a paper-only sweep-plan experiment that combines the previously rejected neutral-breadth proxy cap with an explicit deep drawdown guard:

- Added sweep-plan support for:
  - `drawdown_guard_deep_trigger_pct`
  - `drawdown_guard_deep_scale`
- Added planned experiment:
  - `neutral_proxy_deep_guard_35`
  - `--market-beta-proxy-neutral-breadth-max-exposure 0.5`
  - `--drawdown-guard-deep-trigger-pct -20`
  - `--drawdown-guard-deep-scale 0.35`
- This is paper-only planning/validation plumbing.
- Baseline monthly strategy defaults are unchanged.
- No live order execution was added.
- No Toss API calls were added to tests.

Generated or refreshed reports:

- `data/reports/monthly_validation_scenarios_pit_universe.csv`
- `data/reports/monthly_validation_failures_pit_universe.csv`
- `data/reports/monthly_validation_remediation.csv`
- `data/reports/monthly_validation_sweep_plan.csv`
- `data/reports/monthly_validation_sweep_results_neutral_proxy_deep_guard_35.csv`
- `data/reports/monthly_universe_price_coverage.csv`
- `data/reports/monthly_performance_audit.csv`
- `data/reports/monthly_performance_concentration.csv`
- `data/reports/monthly_deployment_gate_pit_universe.csv`
- `data/reports/monthly_validation_failure_patterns.csv`
- `data/reports/monthly_validation_failure_drilldown.csv`
- `data/reports/production_readiness.csv`
- `data/reports/production_readiness_report.md`
- `data/reports/health_status.json`
- `data/reports/health_status.md`

Candidate target-only result:

- `neutral_proxy_deep_guard_35`: `UNCHANGED`.
- Target-only failed required scenarios stayed `3 -> 3`.
- Failed delta: `0`.
- Minimum excess return: `-5.6018%`.
- Worst drawdown: `-23.991%`.
- Interpretation:
  - Adding a deep drawdown guard to the neutral-breadth proxy cap is not enough on target scenarios.
  - Do not promote this candidate to paper-operation defaults.
  - The highest-value next step remains path-level diagnostics around the March-April 2025 drawdown buffer, especially daily equity, holdings/quantity, turnover, and cost differences.

Verification in this loop:

- RED check:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_sweep_plan_creates_weak_window_candidates tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_validation_sweep_results_emits_deep_guard_args`: failed because `neutral_proxy_deep_guard_35` and deep-drawdown sweep argument propagation did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_sweep_plan_creates_weak_window_candidates tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_validation_sweep_results_emits_deep_guard_args`: PASS.
- Related regression scope:
  - `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `177` tests.
- Full verification:
  - `python -m unittest discover -s tests`: PASS, `415` tests.
  - `python -m compileall -q backtester`: PASS.
  - `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
  - `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=306.03` observed).

Commands run in this loop:

```powershell
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_sweep_plan_creates_weak_window_candidates tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_validation_sweep_results_emits_deep_guard_args
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --data-quality-output data/reports/monthly_validation_data_quality_pit_universe.csv --coverage-output data/reports/monthly_universe_price_coverage.csv --performance-output data/reports/monthly_performance_audit.csv --concentration-output data/reports/monthly_performance_concentration.csv --failure-output data/reports/monthly_validation_failures_pit_universe.csv --remediation-output data/reports/monthly_validation_remediation.csv --sweep-plan-output data/reports/monthly_validation_sweep_plan.csv --sweep-result-output data/reports/monthly_validation_sweep_results.csv --universe-filter-report data/reports/universe_filter_report_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --remediation-output data/reports/monthly_validation_remediation.csv --sweep-plan-output data/reports/monthly_validation_sweep_plan.csv --run-sweep-results --sweep-experiment-id neutral_proxy_deep_guard_35 --sweep-result-output data/reports/monthly_validation_sweep_results_neutral_proxy_deep_guard_35.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m unittest tests.test_monthly_rebalance tests.test_cli
python -m compileall -q backtester
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

Next recommended action:

- Do not adopt `neutral_proxy_deep_guard_35`.
- Add path-level daily diagnostics for baseline vs rejected candidates over `2025-02-28..2025-04-30`.
- Focus on why March 2025 worsened despite identical March decision rows under `neutral_breadth_proxy_cap_50`.
- Keep candidate work paper-only and continue avoiding Toss API calls in tests.

Previous loop:

Added a paper-only monthly decision attribution comparison report to explain the rejected `neutral_breadth_proxy_cap_50` March-April 2025 drawdown regression:

- Added `compare_monthly_decision_attribution_reports`.
- Added `save_monthly_decision_attribution_comparison`.
- Added CLI:
  - `python -m backtester monthly-compare-decisions`
- The report compares baseline vs candidate decision attribution rows by `as_of_date`.
- New comparison fields include:
  - baseline/candidate mode and reason,
  - baseline/candidate target exposure and cash weight,
  - exposure/cash/position-count deltas,
  - shared/baseline-only/candidate-only symbol counts,
  - baseline-only and candidate-only symbols,
  - a diagnostic such as `exposure_reduced`, `cash_increased`, `symbol_rotation`, `reason_changed`, `missing_decision`, or `same_decision`.
- This is diagnostic-only and paper-only. It does not change strategy behavior or execution behavior.

Generated decision comparison reports:

- `data/reports/full_period_decision_comparison_neutral_breadth_proxy_cap_50.csv`
- `data/reports/stress_slippage_x3_decision_comparison_neutral_breadth_proxy_cap_50.csv`

Findings:

- Both `full_period` and `stress_slippage_x3` had `30` compared decision rows.
- Both scenarios had only `3` changed decision rows.
- All changed rows were exposure/cash changes; `symbol_rotation_rows=0`.
- Changed rows:
  - `2024-11-01`: candidate capped neutral-breadth proxy exposure from `0.99` to `0.50`.
  - `2024-12-02`: candidate capped neutral-breadth proxy exposure from `0.99` to `0.50`.
  - `2025-06-02`: candidate entered drawdown-guard scaling from `0.99` to `0.7425`.
- `2025-03-04` decision was identical between baseline and candidate:
  - mode `market_beta_proxy`,
  - target exposure `0.99`,
  - cash weight `0.01`,
  - position count `12`,
  - reason `no_train_candidate_strong_breadth_proxy`.
- `2025-04-01` decision was also identical:
  - mode `market_beta_proxy`,
  - target exposure `0.7425`,
  - cash weight `0.2575`,
  - position count `12`,
  - reason `no_train_candidate_strong_breadth_proxy_drawdown_guard`.
- Interpretation:
  - The March-April 2025 new drawdown breach is not explained by same-month decision mode changes or selected-symbol rotation.
  - The candidate's useful November-December neutral-breadth de-risking improved drawdown into February, but the later March return/drawdown regression happened with identical March/April decision rows.
  - The next diagnostic should inspect path/position/quantity/cost or daily equity differences between February-end and April 2025, not add another broad exposure cap immediately.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `412` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new decision comparison tests failed because `compare_monthly_decision_attribution_reports`, `save_monthly_decision_attribution_comparison`, and `monthly-compare-decisions` did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_compare_monthly_decision_attribution_reports_flags_exposure_and_symbol_rotation tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_decision_attribution_comparison_writes_csv tests.test_cli.CliTests.test_monthly_compare_decisions_cli_writes_exposure_and_symbol_delta_report`: PASS.
- Related regression scope:
  - `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `177` tests.
- Full verification:
  - `python -m unittest discover -s tests`: PASS, `415` tests.
  - `python -m compileall -q backtester`: PASS.
  - `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
  - `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=305.91` observed).

Next recommended action:

- Do not adopt `neutral_breadth_proxy_cap_50`.
- Compare baseline vs candidate daily equity, holdings/quantity, turnover, and transaction-cost path from `2025-02-28` through `2025-04-30`.
- The next report should explain why March 2025 return worsened despite identical March decision rows and no selected-symbol rotation.
- Avoid additional strategy changes until that path-level cause is identified.

Previous loop:

Created and refreshed GPT handoff documentation for the current working tree:

- Updated `docs/GPT_PROJECT_CONTEXT.md`.
  - Compact GPT-ready handoff with safety rules, current verification status, failed required scenarios, readiness/health summaries, latest candidate decision, current git state, repository map, core commands, and next recommended task.
- Created `docs/GPT_PROJECT_SNAPSHOT_FULL.md`.
  - Source-inclusive GPT snapshot for handoff use.
  - Includes non-secret source/docs/test/script/sample files and current report summaries.
  - Intentionally excludes real `.env` values, `.git`, caches, ZIP archives, raw downloaded market data, and large/generated CSV datasets.
- This loop is documentation-only.
  - No trading behavior changed.
  - No real order execution was added.
  - No Toss API calls were added to tests.
  - No `.env` secret values were printed or included.

Verification in this loop:

- `python -m unittest discover -s tests`: PASS, `411` tests.
- `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=305.64` observed).

Next recommended action:

- Use `docs/GPT_PROJECT_CONTEXT.md` for compact GPT context and `docs/GPT_PROJECT_SNAPSHOT_FULL.md` when a source-inclusive snapshot is needed.
- Continue strategy diagnostics without adopting `neutral_breadth_proxy_cap_50`.
- Compare baseline vs candidate decision/exposure/symbol differences around the March-April 2025 drawdown regression before testing any narrower paper-only guard.

Previous loop:

Added a paper-only monthly attribution comparison report to explain the rejected `neutral_breadth_proxy_cap_50` drawdown regressions:

- Added `compare_monthly_attribution_reports`.
- Added `save_monthly_attribution_comparison`.
- Added CLI:
  - `python -m backtester monthly-compare-attribution`
- The report compares baseline vs candidate monthly attribution rows by `month`.
- New comparison fields include:
  - baseline/candidate monthly returns,
  - baseline/candidate equity change,
  - baseline/candidate worst monthly drawdown,
  - return/equity/drawdown deltas,
  - whether the candidate newly crossed the drawdown threshold,
  - a diagnostic such as `new_drawdown_breach`, `drawdown_regression`, `drawdown_improved`, or `return_drag`.
- This is report-only and does not change strategy behavior or execution behavior.

Generated baseline and candidate attribution reports for the two new failures introduced by `neutral_breadth_proxy_cap_50`:

- `data/reports/full_period_baseline_monthly_attribution.csv`
- `data/reports/full_period_baseline_symbol_attribution.csv`
- `data/reports/full_period_baseline_decision_attribution.csv`
- `data/reports/full_period_baseline_recovery_attribution.csv`
- `data/reports/full_period_baseline_proxy_decision_diagnostics.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_monthly_attribution.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_symbol_attribution.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_decision_attribution.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_recovery_attribution.csv`
- `data/reports/full_period_neutral_breadth_proxy_cap_50_proxy_decision_diagnostics.csv`
- `data/reports/stress_slippage_x3_baseline_monthly_attribution.csv`
- `data/reports/stress_slippage_x3_baseline_symbol_attribution.csv`
- `data/reports/stress_slippage_x3_baseline_decision_attribution.csv`
- `data/reports/stress_slippage_x3_baseline_recovery_attribution.csv`
- `data/reports/stress_slippage_x3_baseline_proxy_decision_diagnostics.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_monthly_attribution.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_symbol_attribution.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_decision_attribution.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_recovery_attribution.csv`
- `data/reports/stress_slippage_x3_neutral_breadth_proxy_cap_50_proxy_decision_diagnostics.csv`

Generated monthly attribution comparison reports:

- `data/reports/full_period_attribution_comparison_neutral_breadth_proxy_cap_50.csv`
- `data/reports/stress_slippage_x3_attribution_comparison_neutral_breadth_proxy_cap_50.csv`

Findings:

- Both new failures crossed the max-drawdown hard gate in `2025-04`.
- `full_period`
  - `2025-03`: candidate return worsened from `-9.2322%` to `-9.935%`; drawdown worsened from `-19.8137%` to `-20.8382%`.
  - `2025-04`: candidate return was slightly better (`1.8109%` vs baseline `1.6378%`), but candidate worst drawdown crossed the hard gate (`-25.1331%` vs baseline `-24.044%`).
- `stress_slippage_x3`
  - `2025-03`: candidate return worsened from `-9.0285%` to `-9.8857%`; drawdown worsened from `-19.6864%` to `-20.7729%`.
  - `2025-04`: candidate return was slightly better (`1.6683%` vs baseline `1.5526%`), but candidate worst drawdown crossed the hard gate (`-25.0493%` vs baseline `-24.0105%`).
- Interpretation:
  - The rejected candidate's new failures are not simple April monthly-return losses.
  - The regression is path/drawdown-buffer related: March 2025 worsened the drawdown base, then April 2025 still crossed the `-25%` hard stop despite a positive monthly return.
  - Any next candidate must restore the March-April 2025 drawdown buffer while preserving the `walk_forward_003` train-stability benefit.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `408` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new attribution comparison tests failed because `compare_monthly_attribution_reports`, `save_monthly_attribution_comparison`, and `monthly-compare-attribution` did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_compare_monthly_attribution_reports_flags_new_drawdown_breach tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_attribution_comparison_writes_csv tests.test_cli.CliTests.test_monthly_compare_attribution_cli_writes_monthly_delta_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `173` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `411` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=305.51` observed).

Next recommended action:

- Do not adopt `neutral_breadth_proxy_cap_50`.
- Use the March-April 2025 attribution comparison to test a narrower paper-only guard that avoids worsening March 2025 drawdown buffer.
- Candidate direction should be diagnostic-first: preserve `walk_forward_003` train stability, but reject or scale configurations that push full-period/stress drawdown below `-25%` in March-April 2025.

Previous loop:

Added and rejected a narrower paper-only conditional proxy candidate:

- Added `market_beta_proxy_neutral_breadth_max_exposure` to `MonthlyRebalanceConfig`, defaulting to `1.0` so baseline behavior is unchanged.
- Added CLI support for `--market-beta-proxy-neutral-breadth-max-exposure` in:
  - `monthly-plan`
  - `monthly-backtest`
  - `monthly-attribution`
  - `monthly-validate`
  - `monthly-train-decision-diagnostics`
- Added the sweep-plan experiment `neutral_breadth_proxy_cap_50`.
- The candidate caps fallback `market_beta_proxy` only when breadth is neutral:
  - `prior_breadth >= market_beta_breadth_threshold`
  - `prior_breadth < fallback_breadth_threshold`
- Strong-breadth proxy participation is preserved.
- Direct `market_beta` allocation is not capped by this setting.
- This is optional, paper-only, and disabled by default.

Regenerated baseline validation reports:

- `data/reports/monthly_validation_scenarios_pit_universe.csv`
- `data/reports/monthly_validation_failures_pit_universe.csv`
- `data/reports/monthly_validation_remediation.csv`
- `data/reports/monthly_validation_sweep_plan.csv`
- `data/reports/monthly_universe_price_coverage.csv`
- `data/reports/monthly_performance_audit.csv`
- `data/reports/monthly_performance_concentration.csv`
- `data/reports/monthly_deployment_gate_pit_universe.csv`

Generated full candidate validation and decision reports:

- `data/reports/monthly_validation_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_failures_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_remediation_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_sweep_plan_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_universe_price_coverage_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_performance_audit_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_performance_concentration_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_deployment_gate_candidate_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_comparison_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_comparison_deltas_neutral_breadth_proxy_cap_50.csv`
- `data/reports/monthly_validation_candidate_decision_neutral_breadth_proxy_cap_50.csv`
- default comparison files were also updated to this candidate:
  - `data/reports/monthly_validation_comparison.csv`
  - `data/reports/monthly_validation_comparison_deltas.csv`
  - `data/reports/monthly_validation_candidate_decision.csv`

Candidate result:

- Baseline failed required scenarios: `5`.
- Candidate failed required scenarios: `6`.
- Candidate decision: `REJECT`.
- Resolved failures:
  - `walk_forward_003`
- New failures:
  - `full_period`
  - `stress_slippage_x3`
- Unchanged failures:
  - `regime_sideways`
  - `stress_exclude_500pct_winners`
  - `walk_forward_001`
  - `walk_forward_005`
- Useful signal:
  - `walk_forward_003` passed under this candidate, so neutral-breadth proxy exposure affects recursive train stability enough to remove the train-window rejection.
  - `regime_sideways` excess improved from `-7.1648%` to `-5.6018%`, but it still failed.
  - `full_period` and `stress_slippage_x3` crossed the max-drawdown hard block, with candidate max drawdowns around `-25.13%` and `-25.05%`.
- Interpretation:
  - Neutral-breadth-only proxy capping is narrower than the blanket cap and avoids the known `walk_forward_002`/`walk_forward_004` regression pattern.
  - It still creates unacceptable full-period/stress drawdown regressions.
  - Do not adopt this candidate.

Closed new evidence gaps introduced by the candidate's new failures:

- Generated candidate attribution/proxy diagnostics for:
  - `data/reports/full_period_monthly_attribution.csv`
  - `data/reports/full_period_symbol_attribution.csv`
  - `data/reports/full_period_decision_attribution.csv`
  - `data/reports/full_period_recovery_attribution.csv`
  - `data/reports/full_period_proxy_decision_diagnostics.csv`
  - `data/reports/stress_slippage_x3_monthly_attribution.csv`
  - `data/reports/stress_slippage_x3_symbol_attribution.csv`
  - `data/reports/stress_slippage_x3_decision_attribution.csv`
  - `data/reports/stress_slippage_x3_recovery_attribution.csv`
  - `data/reports/stress_slippage_x3_proxy_decision_diagnostics.csv`
- Regenerated:
  - `data/reports/monthly_validation_failure_patterns.csv`
  - `data/reports/monthly_validation_failure_drilldown.csv`
- `validation_failure_drilldown`: PASS, evidence gaps `0`.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `406` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new neutral-breadth proxy cap tests failed because the config field, conditional cap behavior, sweep-plan row, and CLI help option did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_monthly_config_defaults_to_five_candidate_slots tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_sweep_plan_creates_weak_window_candidates tests.test_monthly_rebalance.MonthlyRebalanceTests.test_decide_monthly_allocation_caps_neutral_breadth_proxy_only tests.test_monthly_rebalance.MonthlyRebalanceTests.test_decide_monthly_allocation_keeps_strong_breadth_proxy_full_size_when_neutral_cap_set tests.test_cli.CliTests.test_monthly_backtest_help_includes_deep_drawdown_guard_options tests.test_cli.CliTests.test_monthly_attribution_help_includes_stress_and_output_options`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `170` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `408` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=305.30` observed).

Next recommended action:

- Do not adopt `neutral_breadth_proxy_cap_50`.
- Compare baseline vs candidate month-level attribution for `full_period` and `stress_slippage_x3` to identify exactly which months pushed drawdown below `-25%`.
- The next candidate should preserve the `walk_forward_003` train-stability benefit without lowering full-period/stress drawdown buffer below the hard gate.
- Avoid additional broad exposure caps until the month-level regression source is isolated.

Earlier loop:

Added paper-only proxy decision diagnostics to explain why fallback `market_beta_proxy` months help in some windows and hurt in others:

- Added `analyze_monthly_proxy_decision_diagnostics` and `save_monthly_proxy_decision_diagnostics`.
- Extended `python -m backtester monthly-attribution` with `--proxy-output`.
- The new report joins monthly return attribution, decision attribution, and train-decision evidence into one row per monthly decision.
- New report fields include:
  - train breadth and thresholds,
  - trend, volatility, liquidity, and exposure scales,
  - direct candidate counts and best direct candidate quality,
  - direct rejection reasons,
  - proxy/recovery diagnostics,
  - `recommended_next_action`.
- This is diagnostic-only and paper-only. It does not add live order execution.

Generated or refreshed proxy diagnostics:

- `data/reports/regime_sideways_proxy_decision_diagnostics.csv`
- `data/reports/walk_forward_005_proxy_decision_diagnostics.csv`
- `data/reports/walk_forward_002_proxy_decision_diagnostics.csv`
- `data/reports/walk_forward_004_proxy_decision_diagnostics.csv`

Proxy diagnostic findings:

- `regime_sideways`
  - Proxy decision rows: `7`.
  - Diagnostics include `market_beta_proxy=7`, `high_exposure_proxy=5`, `high_exposure_proxy_loss=4`, `no_eligible_direct_candidate=6`, `proxy_gain_participation=3`, and `already_scaled_by_drawdown_guard=1`.
  - Loss rows include 2024-10, 2024-11, 2024-12, and 2025-03 high-exposure proxy months.
  - 2025-04 was already scaled by the drawdown guard and still participated in recovery, so broad de-risking would be harmful there.
- `walk_forward_005`
  - Proxy decision rows: `4`.
  - Diagnostics include `market_beta_proxy=3`, `high_exposure_proxy=3`, `high_exposure_proxy_loss=2`, `proxy_gain_participation=1`, and `scaled_alpha_recovery=1`.
  - 2026-03 is the key high-exposure proxy loss month.
  - 2026-04 is a drawdown-guard-scaled alpha recovery month and should not be weakened by a broad cap.
- `walk_forward_002`
  - Proxy decision rows: `4`.
  - Diagnostics include `high_exposure_proxy_loss=2` and `proxy_gain_participation=2`.
  - This baseline window passes, but the rejected blanket cap weakens it enough to create a new failure.
- `walk_forward_004`
  - Proxy decision rows: `4`.
  - Every proxy row is `proxy_gain_participation`.
  - This explains why `market_beta_proxy_cap_75` created a train-gate/new-failure regression here.

Interpretation:

- The rejected `market_beta_proxy_cap_75` candidate failed because fallback proxy months are not uniformly bad.
- A blanket proxy cap reduces some drawdowns but also removes necessary beta participation in passing or recovering windows.
- The next candidate should be conditional, not broad:
  - target high-exposure proxy loss contexts,
  - preserve drawdown-guard-scaled recovery months,
  - avoid weakening `walk_forward_002` and `walk_forward_004`.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `404` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new proxy decision diagnostics tests failed because the analyzer, CSV saver, and `--proxy-output` CLI option did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_proxy_decision_diagnostics_flags_loss_and_recovery_context tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_proxy_decision_diagnostics_writes_csv tests.test_cli.CliTests.test_monthly_attribution_help_includes_stress_and_output_options tests.test_cli.CliTests.test_monthly_attribution_cli_writes_recovery_summary_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `168` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `406` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=304.93` observed).

Next recommended action:

- Build a paper-only conditional proxy-entry experiment using the new diagnostics.
- Do not lower fallback proxy exposure globally.
- First candidate direction: reduce or block full-exposure fallback proxy only in high-exposure loss-prone contexts, while explicitly preserving rows tagged `proxy_gain_participation`, `scaled_proxy_recovery`, or `scaled_alpha_recovery`.

Earlier loop:

Added a narrow fallback proxy exposure-cap experiment and rejected it with full validation evidence:

- Added `market_beta_proxy_max_exposure` to `MonthlyRebalanceConfig`, defaulting to `1.0` so existing behavior is unchanged.
- Added CLI support for `--market-beta-proxy-max-exposure` in:
  - `monthly-plan`
  - `monthly-backtest`
  - `monthly-attribution`
  - `monthly-validate`
  - `monthly-train-decision-diagnostics`
- The cap applies only when the configured `market_beta_symbol` is unavailable and the system falls back to `market_beta_proxy`.
- Direct `market_beta` allocation is not capped by this setting.
- Added the paper-only sweep experiment `market_beta_proxy_cap_75` to the validation sweep plan.
- Regenerated baseline validation reports; the baseline still has 5 failed required scenarios.
- Ran full candidate validation for `market_beta_proxy_cap_75` with `--market-beta-proxy-max-exposure 0.75`.
- Generated current candidate comparison and decision reports:
  - `data/reports/monthly_validation_candidate_market_beta_proxy_cap_75.csv`
  - `data/reports/monthly_validation_comparison_market_beta_proxy_cap_75.csv`
  - `data/reports/monthly_validation_comparison_deltas_market_beta_proxy_cap_75.csv`
  - `data/reports/monthly_validation_candidate_decision_market_beta_proxy_cap_75.csv`
  - default comparison files were also updated to this candidate:
    - `data/reports/monthly_validation_comparison.csv`
    - `data/reports/monthly_validation_comparison_deltas.csv`
    - `data/reports/monthly_validation_candidate_decision.csv`

Candidate result:

- Baseline failed required scenarios: `5`.
- Candidate failed required scenarios: `7`.
- Candidate decision: `REJECT`.
- Resolved failures: none.
- New failures:
  - `walk_forward_002`
  - `walk_forward_004`
- Unchanged failures:
  - `stress_exclude_500pct_winners`
  - `regime_sideways`
  - `walk_forward_001`
  - `walk_forward_003`
  - `walk_forward_005`
- Useful signal:
  - The cap reduced drawdown in several failures, for example `regime_sideways` max drawdown improved from `-23.9059%` to `-19.3294%`, and `walk_forward_005` max drawdown improved from `-20.5503%` to `-15.4592%`.
  - It did not clear negative excess return gates.
  - It reduced train/test excess enough to create new `walk_forward_002` and `walk_forward_004` failures.
- Interpretation:
  - A blunt fallback proxy exposure cap is too broad.
  - It can reduce drawdown, but it creates over-defense/filter drag and train-gate regression.
  - Do not adopt this candidate.

Added attribution evidence to keep drilldown evidence gaps closed after the new mixed candidate response:

- `data/reports/stress_exclude_500pct_winners_monthly_attribution.csv`
- `data/reports/stress_exclude_500pct_winners_symbol_attribution.csv`
- `data/reports/stress_exclude_500pct_winners_decision_attribution.csv`
- `data/reports/stress_exclude_500pct_winners_recovery_attribution.csv`
- `data/reports/walk_forward_001_monthly_attribution.csv`
- `data/reports/walk_forward_001_symbol_attribution.csv`
- `data/reports/walk_forward_001_decision_attribution.csv`
- `data/reports/walk_forward_001_recovery_attribution.csv`

Updated failure-pattern and drilldown reports using the existing rejected candidates plus `market_beta_proxy_cap_75`:

- `data/reports/monthly_validation_failure_patterns.csv`
- `data/reports/monthly_validation_failure_drilldown.csv`
- `validation_failure_drilldown`: PASS, evidence gaps `0`.

Verification in this loop:

- Baseline before edits: `python -m unittest discover -s tests`: PASS, `402` tests.
- Baseline before edits: `python -m compileall -q backtester`: PASS.
- RED check: new proxy-cap tests failed because `market_beta_proxy_max_exposure`, CLI flags, and sweep plan row did not exist.
- Targeted GREEN:
  - `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_monthly_config_defaults_to_five_candidate_slots tests.test_monthly_rebalance.MonthlyRebalanceTests.test_build_monthly_validation_sweep_plan_creates_weak_window_candidates tests.test_monthly_rebalance.MonthlyRebalanceTests.test_decide_monthly_allocation_caps_proxy_exposure_only tests.test_monthly_rebalance.MonthlyRebalanceTests.test_decide_monthly_allocation_does_not_cap_direct_market_beta_symbol`: PASS.
  - `python -m unittest tests.test_cli.CliTests.test_monthly_backtest_help_includes_deep_drawdown_guard_options tests.test_cli.CliTests.test_monthly_attribution_help_includes_stress_and_output_options tests.test_cli.CliTests.test_monthly_validate_help_includes_failure_diagnostics_output tests.test_cli.CliTests.test_monthly_plan_help_includes_human_summary_output`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `166` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `404` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=304.69` observed).

Next recommended action:

- Do not try a lower blanket proxy cap.
- Design a narrower paper-only candidate that distinguishes:
  - high-risk proxy entry months like `2025-03` and `2026-03`,
  - already de-risked recovery months such as `2026-04`,
  - walk-forward windows where proxy cap causes train-gate regression.
- Candidate direction: add diagnostics or an experiment around conditional proxy gating, for example requiring stronger breadth/trend confirmation before full `market_beta_proxy`, while preserving participation after drawdown guards have already lowered exposure.

Earlier loop:

Added recovery attribution summaries for `insufficient_recovery` failures:

- Extended `python -m backtester monthly-attribution` with:
  - `--scenario-name`
  - `--summary-output`
- New paper-only summary reports:
  - `data/reports/regime_sideways_recovery_attribution.csv`
  - `data/reports/walk_forward_005_recovery_attribution.csv`
  - `data/reports/walk_forward_003_recovery_attribution.csv` for contrast with the already explained direct-alpha-ineligible case.
- Purpose: connect monthly drawdown attribution, decision exposure/cash attribution, symbol realized PnL attribution, and total-vs-benchmark performance in one row per scenario.
- Added CSV fields for:
  - scenario, period, total/buy-hold/excess return, max drawdown,
  - loss/gain month counts and positive month ratio,
  - average target exposure and cash weight,
  - worst/best month return, exposure, cash weight, mode, and decision reason,
  - post-worst recovery return,
  - top loss symbols and loss/gain symbol counts,
  - `failure_mode` and semicolon-delimited diagnostics.
- Added deterministic tests for:
  - exposure/cash/loss-symbol recovery summary generation,
  - recovery summary CSV saving,
  - `monthly-attribution --summary-output` CLI generation.

Recovery attribution findings:

- `regime_sideways`
  - Total return `-9.2276%`, buy-hold `-2.0628%`, excess `-7.1648%`.
  - Loss months `4`, gain months `3`, positive month ratio `0.4286`.
  - Average target exposure `0.8486`, average cash weight `0.1514`.
  - Worst month `2025-03`: return `-8.8337%`, target exposure `0.99`, cash `0.01`, mode `market_beta_proxy`, reason `no_train_candidate_strong_breadth_proxy`.
  - Best month `2025-02`: return `3.4379%`, target exposure `0.99`, cash `0.01`.
  - Post-worst recovery after the March loss was only `1.3031%`.
  - Top loss symbols: `005490:-218620`, `051910:-216092.25`, `450080:-175280.4`.
  - Failure mode: `absolute_loss_and_benchmark_drag`.
  - Diagnostic: `negative_excess;high_exposure_worst_month;insufficient_post_worst_recovery;loss_month_pressure;symbol_loss_concentration`.
- `walk_forward_005`
  - Attribution CLI result: total return `8.6057%`, buy-hold `14.0817%`, excess `-5.476%`.
  - Loss months `2`, gain months `2`, positive month ratio `0.5`.
  - Average target exposure `0.9281`, average cash weight `0.0719`.
  - Worst month `2026-03`: return `-19.2651%`, target exposure `0.99`, cash `0.01`, mode `market_beta_proxy`, reason `no_train_candidate_strong_breadth_proxy`.
  - Best month `2026-04`: return `20.2536%`, target exposure `0.7425`, cash `0.2575`.
  - Post-worst recovery was `20.2536%`, but the benchmark recovered more, so excess stayed negative.
  - Top loss symbols: `009830:-218934.801`, `080220:-214073.55`, `066570:-177152.4`.
  - Failure mode: `benchmark_outpaced_recovery`.
  - Diagnostic: `benchmark_recovered_more;high_exposure_worst_month;cash_drag_best_month;loss_month_pressure;symbol_loss_concentration`.
- Contrast case, `walk_forward_003`
  - Total return `10.5419%`, buy-hold `1.7889%`, excess `8.753%`, max drawdown `-7.1592%`.
  - Average target exposure `0.99`, average cash `0.01`.
  - Worst month `2025-08`: return `-4.2304%`.
  - Post-worst recovery `17.2902%`.
  - This case is not an insufficient-recovery failure; it remains blocked because train window/direct alpha eligibility is rejected.
- Interpretation:
  - The two `insufficient_recovery` failures are not identical.
  - `regime_sideways` is an absolute loss and post-worst recovery failure after high-exposure market-beta-proxy allocation in March 2025.
  - `walk_forward_005` recovered strongly in April 2026 but still lagged an even stronger buy-hold benchmark; reducing March 2026 high-exposure loss or improving April participation would be more relevant than simply adding broad cash.
  - Do not adopt broad weak-cash candidates blindly; previous candidates that helped some cases created regressions elsewhere.

Verification in this loop:

- Baseline before edits: `python -m compileall -q backtester`: PASS.
- Baseline before edits: `python -m unittest discover -s tests`: PASS, `399` tests.
- RED check: new recovery attribution tests failed because the functions and `--summary-output` CLI option did not exist.
- Targeted GREEN: `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_recovery_attribution_summarizes_exposure_and_loss_symbols tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_recovery_attribution_writes_csv tests.test_cli.CliTests.test_monthly_attribution_help_includes_stress_and_output_options tests.test_cli.CliTests.test_monthly_attribution_cli_writes_recovery_summary_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `164` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `402` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`, status remains blocked.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=304.15` observed).

Next recommended action:

- Use the recovery summaries to design a narrow candidate experiment that specifically caps high-exposure market-beta-proxy losses in the worst months (`2025-03` and `2026-03`) while preserving `walk_forward_003` recovery behavior and avoiding known regressions in `regime_bear`, `walk_forward_002`, and `walk_forward_004`.

Previous loop:

Added recursive train stability-window diagnostics:

- Extended `python -m backtester monthly-train-decision-diagnostics` with `--stability-output`.
- New report: `data/reports/monthly_train_stability_window_diagnostics.csv`.
- Purpose: decompose the direct candidate `train_positive_ratio` behind `low_positive_ratio` rejections into the actual stability subwindows, with each subwindow's excess return, drawdown, trade count, positive flag, and rejection reason.
- Added CSV fields for:
  - scenario, walk-forward preset, as-of date, signal date, and actual train decision mode/reason,
  - `alpha_block_reason`,
  - inner train start/end,
  - stability window name/start/end,
  - subwindow symbol count, total/buy-hold/excess return, max drawdown, trade count, positive flag, and subwindow rejection reasons,
  - candidate full-train total/buy-hold/excess return, max drawdown, trade count, subwindow counts, positive ratio, average/worst subwindow excess, and candidate rejection reasons,
  - raw/PIT/liquidity/train universe counts and filter removals.
- Added deterministic tests for:
  - stability-window decomposition of candidate positive ratio,
  - stability-window CSV saving,
  - `monthly-train-decision-diagnostics --stability-output` CLI report generation.
- Regenerated train decision and train stability-window diagnostics for `walk_forward_003` and `walk_forward_004`.
- Current train decision path report rows: `26` (`2` scenarios x `13` train decisions).
- Current train stability-window report rows: `104`.

Train stability-window findings:

- `walk_forward_003`
  - Counted stability rows: `52`.
  - Positive subwindows: `16`; nonpositive/no-trade subwindows: `36`.
  - Candidate positive ratios seen by decision date: `0.25` and `0.5`.
  - Candidate rejection reasons across subwindow rows:
    - `low_positive_ratio=24`
    - `eligible=4`
    - `nonpositive_excess;low_positive_ratio=16`
    - `nonpositive_excess=8`
  - Subwindow rejection summary:
    - `nonpositive_excess=36`
    - `positive=16`
  - Worst subwindow: `2025-05-02`, `train_stability_2024_2025`, `2024-01-01..2025-04-30`, excess `-55.0564`, trades `34`, candidate excess `-63.6368`.
- `walk_forward_004`
  - Counted stability rows: `52`.
  - Positive subwindows: `17`; nonpositive/no-trade subwindows: `35`.
  - Candidate positive ratios seen by decision date: `0.0`, `0.25`, `0.5`, and `0.75`.
  - Candidate rejection reasons across subwindow rows:
    - `low_positive_ratio=12`
    - `eligible=4`
    - `nonpositive_excess;low_positive_ratio=24`
    - `nonpositive_excess=12`
  - Subwindow rejection summary:
    - `nonpositive_excess=34`
    - `no_trades=2`
    - `positive=17`
  - Worst subwindow: `2025-05-02`, `train_stability_2024_2025`, `2024-01-01..2025-04-30`, excess `-55.0564`, trades `34`, candidate excess `-63.6368`.
- Interpretation:
  - `low_positive_ratio` is not a bookkeeping artifact. The candidate repeatedly fails across older two-year windows (`2021_2022`, `2022_2023`, `2023_2024`) even when headline candidate excess is positive in late 2024.
  - In 2025, the candidate often adds `nonpositive_excess`, with the `2024_2025` stability window becoming the largest negative contributor.
  - This supports keeping the alpha gate strict for now. Loosening the positive-ratio gate would admit candidates with unstable historical subwindow behavior and large recent subwindow losses.

Verification in this loop:

- Baseline before edits: `python -m compileall -q backtester`: PASS.
- Baseline before edits: `python -m unittest discover -s tests`: PASS, `397` tests.
- RED check: new stability-window tests failed because the functions and `--stability-output` CLI option did not exist.
- Targeted GREEN: `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_train_stability_windows_breaks_positive_ratio_into_subwindows tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_train_stability_windows_writes_csv tests.test_cli.CliTests.test_monthly_train_decision_diagnostics_cli_writes_path_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `161` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `399` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `monthly_performance_concentration.csv` remained sourced from `monthly-validate:2024-01-01..2026-06-18` after full unittest.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`, status counts `BLOCK=8`, `PASS=31`, `WARN=8`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=303.89` observed).

Next recommended action:

- Move from direct-alpha train eligibility to scenario failure attribution for the remaining required blockers. Start with `regime_sideways` and `walk_forward_005` (`insufficient_recovery`) and compare decision exposure/cash ratio, worst holding periods, and symbol-level contribution against the now-explained `direct_alpha_ineligible` cases.

Previous loop:

Added recursive monthly train decision path diagnostics:

- New CLI: `python -m backtester monthly-train-decision-diagnostics`.
- New report: `data/reports/monthly_train_decision_path_diagnostics.csv`.
- Purpose: explain the recursive monthly train decisions inside walk-forward train windows, especially why `alpha_ratio=0` and why train decisions fall back to `market_beta_proxy` or `cash`.
- Added CSV fields for:
  - scenario, walk-forward preset, as-of date, and signal date,
  - actual train decision mode, selected preset, reason, and decision family,
  - `alpha_block_reason`,
  - target symbols, target exposure, and cash weight,
  - inner train window used at that decision,
  - prior breadth and risk overlay scales,
  - direct candidate count, eligible candidate count, candidate scores, rejection reasons, and best direct candidate metrics,
  - outer recursive train total/buy-hold/excess return, drawdown, trade count, decision count, and alpha ratio,
  - raw/PIT/liquidity/train universe counts and filter removals.
- Added deterministic tests for:
  - fallback choice explanation with direct candidate rejection reasons,
  - train decision path CSV saving,
  - `monthly-train-decision-diagnostics` CLI report generation.
- Regenerated train decision path diagnostics for `walk_forward_003` and `walk_forward_004`.
- Current train decision path report rows: `26` (`2` scenarios x `13` train decisions).

Recursive train decision findings:

- `walk_forward_003`
  - Train decision rows: `13`.
  - Decision modes: `13 market_beta_proxy`, `0 alpha`, `0 cash`.
  - Outer recursive train alpha ratio: `0`.
  - Decision reasons:
    - `no_train_candidate_strong_breadth_proxy=8`
    - `no_train_candidate_neutral_breadth_proxy=2`
    - `no_train_candidate_strong_breadth_proxy_drawdown_guard=2`
    - `weak_train_neutral_breadth_proxy_trend_scaled=1`
  - Alpha block reasons:
    - `no_eligible_direct_candidate=12`
    - `weak_breadth_and_weak_train_average=1`
  - Direct candidate count was `1` at each decision, but eligible candidate count was usually `0`.
  - Direct candidate rejection was mainly `low_positive_ratio`; some later rows also had `nonpositive_excess`.
- `walk_forward_004`
  - Train decision rows: `13`.
  - Decision modes: `13 market_beta_proxy`, `0 alpha`, `0 cash`.
  - Outer recursive train alpha ratio: `0`.
  - Decision reasons:
    - `no_train_candidate_strong_breadth_proxy=7`
    - `no_train_candidate_neutral_breadth_proxy=3`
    - `no_train_candidate_strong_breadth_proxy_drawdown_guard=2`
    - `weak_train_neutral_breadth_proxy_trend_scaled=1`
  - Alpha block reasons:
    - `no_eligible_direct_candidate=12`
    - `weak_breadth_and_weak_train_average=1`
  - Direct candidate best excess ranged from about `-94.7878` to `55.7425`, but stability/positive-ratio gates kept recursive alpha decisions at zero.
- Interpretation:
  - The recursive train behavior is now explicitly fallback-only in the report, not just summarized in a compact profile string.
  - In these windows, alpha is blocked less by missing candidates and more by unstable direct candidate subwindow performance (`low_positive_ratio`) plus weak-breadth fallback rules.
  - Do not loosen gates yet; the next useful diagnostic is to decompose the low positive-ratio subwindows and identify which stability windows flip the direct candidate from strong headline excess to ineligible.

Verification in this loop:

- Baseline before edits: `python -m compileall -q backtester`: PASS.
- Baseline before edits: `python -m unittest discover -s tests`: PASS, `394` tests.
- RED check: new train decision path tests initially failed because the new functions/CLI did not exist.
- RED refinement: `alpha_block_reason` was initially missing from the path rows.
- Targeted GREEN: `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_train_decision_path_explains_fallback_choices tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_train_decision_path_writes_csv tests.test_cli.CliTests.test_monthly_train_decision_diagnostics_cli_writes_path_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `159` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `397` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- `monthly_performance_concentration.csv` remained sourced from `monthly-validate:2024-01-01..2026-06-18` after full unittest.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`, status counts `BLOCK=8`, `PASS=31`, `WARN=8`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=303.64` observed).

Next recommended action:

- Add direct candidate stability-window diagnostics: for each walk-forward train decision, show the subwindows behind `train_positive_ratio`, their excess returns, drawdowns, and trade counts so `low_positive_ratio` can be attributed to specific market periods.

Previous loop:

Added direct-alpha holding-path diagnostics:

- Extended `python -m backtester monthly-direct-alpha-diagnostics` with `--path-output`.
- New report: `data/reports/monthly_direct_alpha_path_diagnostics.csv`.
- Purpose: compare actual in-period direct-alpha holdings by rebalance date against the train-end selected snapshot and the PIT/top-100 benchmark universe.
- Added CSV fields for:
  - rebalance date and event type,
  - held, entered, and exited symbols,
  - equal holding weights,
  - train-end selected symbols,
  - overlap count and overlap symbols,
  - holdings not in the train-end snapshot,
  - train-end selections missing from current holdings,
  - benchmark symbol count/composition,
  - benchmark average/median return,
  - candidate total/buy-hold/excess return and turnover counts,
  - raw/PIT/liquidity/train universe counts and filter removals.
- Added deterministic tests for:
  - holding-path analysis comparing rebalance holdings with the train-end snapshot,
  - no-trade scheduled rebalance snapshots,
  - holding-path CSV saving,
  - `monthly-direct-alpha-diagnostics --path-output` CLI generation.
- Regenerated direct-alpha diagnostics for `walk_forward_003` and `walk_forward_004`.
- Current holding-path report rows: `6`.

Direct-alpha holding-path findings:

- `walk_forward_003`
  - Path rows: `3` (`2025-04-08` no-trade rebalance, `2025-06-10` rebalance, `2025-07-22` liquidation).
  - The `2025-04-08` scheduled rebalance had no holdings and no trades.
  - Actual in-period holdings: `000880;037270;108490;214450;298380`.
  - Train-end selected snapshot: `108490;002020;000880;294570;064260`.
  - Rebalance overlap with train-end snapshot: `2 of 5` (`000880;108490`).
  - Candidate performance remains `total_return_pct=16.2733`, `buy_hold_return_pct=35.9941`, `excess_return_pct=-19.7208`.
  - Interpretation: the train-end snapshot looked strong, but actual in-period holdings only partly matched it; the candidate held three names that were not in the final train-end selected set.
- `walk_forward_004`
  - Path rows: `3` (`2025-07-11` rebalance, `2025-09-08` rebalance, `2025-10-27` liquidation).
  - Initial holdings: `003230;064260;064350;124500;214450`.
  - Second rebalance replaced `003230;124500;214450` with `087010;226950;298380`.
  - Train-end selected snapshot: `226950;222800;124500;064350;006800`.
  - Rebalance overlap with train-end snapshot stayed `2 of 5` before liquidation.
  - Candidate performance remains `total_return_pct=0.4340`, `buy_hold_return_pct=60.5903`, `excess_return_pct=-60.1564`.
  - Interpretation: the direct-alpha failure is now better explained as path dependence and turnover/selection drift against a very strong top-100 buy-hold benchmark, not simply absence of strong train-end symbols.

Verification in this loop:

- Baseline before edits: `python -m compileall -q backtester`: PASS.
- Baseline before edits: `python -m unittest discover -s tests`: PASS, `392` tests.
- RED check: new holding-path tests initially failed because the new functions/CLI option did not exist.
- RED refinement: no-trade scheduled rebalance snapshots were initially missing from the path report.
- Test isolation fix: `tests/test_cli.py::test_monthly_backtest_can_exclude_symbols_from_data_quality_file` now runs `monthly-backtest` in a temp cwd so full unittest no longer overwrites workspace `data/reports/monthly_performance_concentration.csv`.
- Targeted GREEN: `python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_direct_alpha_holding_path_compares_rebalance_holdings_to_train_end_snapshot tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_direct_alpha_holding_path_writes_csv tests.test_cli.CliTests.test_monthly_direct_alpha_diagnostics_cli_writes_selection_report`: PASS.
- Related regression scope: `python -m unittest tests.test_monthly_rebalance tests.test_cli`: PASS, `156` tests.
- Full verification: `python -m unittest discover -s tests`: PASS, `394` tests.
- Full syntax check: `python -m compileall -q backtester`: PASS.
- Regenerated baseline monthly validation after detecting `monthly_performance_concentration.csv` had been overwritten by `monthly-backtest`; the first 300s run timed out, then the 600s rerun passed and the report source is back to `monthly-validate:2024-01-01..2026-06-18`.
- `python -m backtester production-check --allow-blocked-exit-zero`: `BLOCK`, status counts `BLOCK=8`, `PASS=31`, `WARN=8`.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: `WARN`, only because scalper data is stale (`age_hours=303.30` observed).

Next recommended action:

- Add recursive monthly train decision path diagnostics: explain when each train window chooses `market_beta_proxy` or `cash`, what direct-alpha candidates existed at each train decision point, and why `alpha_ratio` remains `0`.

Added direct-alpha symbol-selection diagnostics:

- New CLI: `python -m backtester monthly-direct-alpha-diagnostics`
- New report: `data/reports/monthly_direct_alpha_selection_diagnostics.csv`
- Purpose: explain direct alpha train failures by symbol-level selection evidence inside the PIT/top-liquid train universe.
- Added CSV fields for:
  - selected/rejected symbols,
  - selected weights,
  - momentum score,
  - average trading value,
  - symbol train return,
  - benchmark average/median return,
  - candidate total/buy-hold/excess return,
  - candidate trade/buy/sell/unique-traded-symbol counts,
  - raw/PIT/liquidity/train universe counts and filter removals.
- Added deterministic tests for:
  - direct-alpha selected and rejected symbol rows,
  - direct-alpha diagnostics CSV saving,
  - `monthly-direct-alpha-diagnostics` CLI report generation.
- Generated the report for `walk_forward_003` and `walk_forward_004`.
- Current report rows: `200` (`2` scenarios x `100` train symbols).

Direct-alpha symbol-selection findings:

- `walk_forward_003`
  - Selected/rejected: `5 selected`, `95 rejected`.
  - Rejection reasons: `below_selected_rank=87`, `trend_filter_failed=8`.
  - Candidate turnover: `trade_count=10`, `buy_count=5`, `sell_count=5`, `unique_traded_symbols=5`.
  - Candidate performance: `total_return_pct=16.2733`, `buy_hold_return_pct=35.9941`, `excess_return_pct=-19.7208`.
  - Train-end selected symbols had high momentum and strong train-period returns, so the remaining concern is less "no strong symbols existed" and more whether the direct train benchmark is too strong, the snapshot differs from in-period holdings, or the alpha/turnover path lagged the equal-weight benchmark.
- `walk_forward_004`
  - Selected/rejected: `5 selected`, `95 rejected`.
  - Rejection reasons: `below_selected_rank=91`, `trend_filter_failed=4`.
  - Candidate turnover: `trade_count=16`, `buy_count=8`, `sell_count=8`, `unique_traded_symbols=8`.
  - Candidate performance: `total_return_pct=0.4340`, `buy_hold_return_pct=60.5903`, `excess_return_pct=-60.1564`.
  - The selected train-end symbols were also strong, but the candidate path badly lagged the top-100 liquid benchmark. Next diagnostics should compare actual in-period holdings by rebalance date against the train-end snapshot and benchmark constituents.

Added direct-alpha train-window diagnostics:

- Added `train_direct_diagnostics` to monthly validation and failure drilldown rows.
- The field decomposes direct train alpha candidates by:
  - period length,
  - raw/PIT/liquidity/train universe counts,
  - universe, PIT filter, liquidity, and train-coverage removals,
  - train-window average and median symbol returns,
  - simple market-regime label,
  - direct candidate total return, buy-hold return, excess return, and non-positive excess flag.
- Added regression tests for:
  - walk-forward validation writing the new train-direct diagnostics,
  - failure drilldown preserving the diagnostics,
  - failure drilldown CSV header including the new field.
- Regenerated monthly validation, failure patterns, failure drilldown, production readiness, and health reports.

Direct-alpha ineligible decomposition:

- `walk_forward_003`
  - Train window: `2024-07-08..2025-07-22`, `period_days=380`.
  - Universe path: `raw_symbols=2184`, `universe_symbols=2081`, `pit_symbols=2029`, `liquid_symbols=100`, `train_symbols=100`.
  - Filter removals: `universe_removed=103`, `pit_filter_removed=52`, `liquidity_removed=1929`, `train_coverage_removed=0`.
  - Train-window broad return backdrop: `train_avg_symbol_return_pct=53.6167`, `train_median_symbol_return_pct=36.7157`, `market_regime=risk_on`.
  - Direct alpha candidate: `total_return_pct=16.2733`, `buy_hold_return_pct=35.9941`, `excess_return_pct=-19.7208`.
- `walk_forward_004`
  - Train window: `2024-10-14..2025-10-27`, `period_days=379`.
  - Universe path: `raw_symbols=2184`, `universe_symbols=2081`, `pit_symbols=2022`, `liquid_symbols=100`, `train_symbols=100`.
  - Filter removals: `universe_removed=103`, `pit_filter_removed=59`, `liquidity_removed=1922`, `train_coverage_removed=0`.
  - Train-window broad return backdrop: `train_avg_symbol_return_pct=87.4997`, `train_median_symbol_return_pct=68.4406`, `market_regime=risk_on`.
  - Direct alpha candidate: `total_return_pct=0.4340`, `buy_hold_return_pct=60.5903`, `excess_return_pct=-60.1564`.
- Interpretation:
  - These failures are not explained by a weak broad train-window regime or missing train coverage.
  - The immediate evidence points to the direct alpha candidate underperforming a strong buy-hold backdrop after PIT and top-100 liquidity filtering.
  - Do not loosen train gates based on this; next diagnostics should compare selected direct-alpha symbols, weights, turnover, and benchmark construction inside the top-100 liquid train universe.
- Current readiness status counts remain `BLOCK=8`, `PASS=31`, `WARN=8`.
- Health remains `WARN` for stale scalper data only; latest observed age was about `302.5` hours.

Improved direct-alpha failure drilldown and report-source safety:

- Failure drilldown now classifies train-window failures with negative direct alpha candidate scores as `direct_alpha_ineligible`.
- Current root-cause counts:
  - `insufficient_recovery=2`
  - `direct_alpha_ineligible=2`
  - `selection_or_exposure_regression=1`
  - `over_defense_or_filter_drag=1`
  - `drawdown_pressure=1`
  - `candidate_fixed_failure=1`
- Affected walk-forward rows:
  - `walk_forward_003`: `direct_alpha_ineligible`
  - `walk_forward_004`: `direct_alpha_ineligible`
  - `walk_forward_005`: `insufficient_recovery`
  - `walk_forward_002`: `over_defense_or_filter_drag`
  - `walk_forward_001`: `candidate_fixed_failure`
- Added production readiness protection for `monthly_performance_concentration.csv` source mismatch.
- If the concentration report is accidentally overwritten by `monthly-backtest`, production-check now warns with `unexpected_source`.
- Regenerated monthly validation after detecting this overwrite risk; current concentration source is back to `monthly-validate:2024-01-01..2026-06-18`.
- Production readiness status counts are `BLOCK=8`, `PASS=31`, `WARN=8`.
- Health remains `WARN` only for stale scalper data.

Clarified walk-forward train alpha weakness:

- Added `train_candidate_direct_scores` to monthly validation and failure drilldown reports.
- This records direct momentum train candidate scores separately from recursive monthly train backtest scores.
- `production-check` now reports `direct_alpha_ineligible=5` in `walk_forward_train_candidate_coverage`.
- Current evidence shows all 5 walk-forward train windows have fallback-only monthly train decisions and direct alpha train candidates with negative excess returns.
- This changes the interpretation:
  - The immediate issue is not only that the default monthly config has one preset.
  - Even direct alpha train candidates are currently ineligible in the walk-forward train windows.
  - Next experiments should diagnose train-window alpha weakness and data/regime fit before loosening gates.
- Readiness recommendations now say `Diagnose walk-forward train alpha weakness` when direct alpha candidates are ineligible, instead of only saying to expand candidate count.
- Regenerated baseline monthly validation, failure patterns, failure drilldown, production readiness, and health reports.
- Production readiness status counts are now `BLOCK=8`, `PASS=31`, `WARN=8`.

Hardened validation delta discovery:

- `monthly-failure-patterns` and `monthly-failure-drilldown` now avoid mixing diagnostic delta files into operational failure reports.
- If `--delta-report` is supplied, those commands no longer silently supplement it with the default delta glob.
- If no explicit delta report is supplied, the default glob still discovers candidate delta reports, but skips diagnostic patterns:
  - `data/reports/monthly_validation_comparison_deltas_multi_*.csv`
  - `data/reports/monthly_validation_comparison_deltas_diagnostic_*.csv`
- Added `--exclude-delta-glob` to both commands for extra automatic-discovery exclusions.
- Regenerated `monthly_validation_failure_patterns.csv` and `monthly_validation_failure_drilldown.csv` using the safer default discovery.
- Both regenerated reports read `delta_reports=3`, excluding the diagnostic `multi_preset` report.
- That loop preserved strategy performance state; later readiness counts are now `BLOCK=8`, `PASS=31`, `WARN=8`.

Added walk-forward train candidate coverage diagnostics:

- New production readiness check: `walk_forward_train_candidate_coverage`.
- The check warns when walk-forward rows have fewer than 2 train candidates.
- It also warns when multiple named candidates have identical score signatures.
- It now records train candidate decision profiles and warns when train candidates are fallback-only.
- Added readiness recommendations: `Expand walk-forward train candidates`.
- Ran a separate candidate validation with `--presets balanced,aggressive,retail`.
- Result: failed required scenarios stayed at 5; comparison status `UNCHANGED`.
- Important finding: all three preset names produced identical train scores in every walk-forward window.
- Stronger finding: all walk-forward train windows have `alpha_ratio=0`; the monthly validation train candidates are proxy/cash fallback-only.
- Interpretation: simply widening `--presets` does not currently add real model diversity. The next fix should inspect why monthly train windows never reach alpha decisions before changing strategy behavior.
- Operational note: diagnostic `multi_preset` deltas should not be mixed into the main failure-pattern report. The main `monthly_validation_failure_patterns.csv` and drilldown were regenerated with the three remediation candidate delta reports explicitly.

Closed validation drilldown evidence gaps:

- Added decision-level attribution support for monthly validation drilldown.
- Added `monthly-failure-drilldown --attribution-dir`.
- The command reads `<scenario>_decision_attribution.csv` and `<scenario>_symbol_attribution.csv`.
- Added `train_candidate_scores` to monthly walk-forward validation rows.
- Drilldown now treats scenario attribution and train candidate scores as evidence.
- Regenerated attribution reports for:
  - `regime_sideways`
  - `walk_forward_003`
  - `walk_forward_005`
  - `regime_bear`
  - `walk_forward_002`
  - `walk_forward_004`
- Regenerated baseline monthly validation, failure patterns, failure drilldown, production readiness, and health reports.
- `validation_failure_drilldown` now reports `evidence_gaps=0` and PASS in production readiness.

Latest validation state:

- Required failures remain: 5 of 18.
- Failed required scenarios:
  - `stress_exclude_500pct_winners`
  - `regime_sideways`
  - `walk_forward_001`
  - `walk_forward_003`
  - `walk_forward_005`
- Remaining production BLOCK is now clearer: actual scenario failures and performance/risk gates, not missing diagnostic evidence.

Added validation failure-pattern diagnostics:

- New CLI: `python -m backtester monthly-failure-patterns`
- New report: `data/reports/monthly_validation_failure_patterns.csv`
- New production-check input: `--validation-failure-patterns`
- New readiness check: `validation_failure_patterns`

Added validation failure drilldown diagnostics:

- New CLI: `python -m backtester monthly-failure-drilldown`
- New report: `data/reports/monthly_validation_failure_drilldown.csv`
- New production-check input: `--validation-failure-drilldown`
- New readiness check: `validation_failure_drilldown`
- Purpose: combine baseline scenario metrics, persistent/regression pattern status, and candidate deltas into a scenario-level root-cause/action report.

Generated from baseline validation plus 3 candidate delta reports:

- Rows: 8
- Delta reports read: 3
- Top pattern: `regime_sideways PERSISTENT_BLOCK`

Pattern summary:

- `PERSISTENT_BLOCK=3`
  - `regime_sideways`
  - `walk_forward_003`
  - `walk_forward_005`
- `REGRESSION_RISK=3`
  - `walk_forward_002`
  - `regime_bear`
  - `walk_forward_004`
- `CANDIDATE_FIXED=2`
  - `stress_exclude_500pct_winners`
  - `walk_forward_001`

Interpretation:

- The previous rejected candidates did fix `stress_exclude_500pct_winners` and `walk_forward_001`.
- They did not fix `regime_sideways`, `walk_forward_003`, or `walk_forward_005`.
- They introduced or preserved regression risk in `walk_forward_002`, `regime_bear`, and `walk_forward_004`.
- Do not continue the same candidate family as-is. Isolate what fixed the two resolved scenarios without carrying the regression behavior.

Latest drilldown summary:

- `insufficient_recovery=2`
  - `regime_sideways`
  - `walk_forward_005`
- `direct_alpha_ineligible=2`
  - `walk_forward_003`
  - `walk_forward_004`
- `selection_or_exposure_regression=1`
  - `regime_bear`
- `over_defense_or_filter_drag=1`
  - `walk_forward_002`
- `drawdown_pressure=1`
  - `stress_exclude_500pct_winners`
- `candidate_fixed_failure=1`
  - `walk_forward_001`

Important interpretation update:

- `regime_sideways` and `walk_forward_005` did improve under candidates, but not enough to pass.
- They are now classified as `insufficient_recovery`, not just weak-window drag.
- Evidence gaps are now closed.

## Current BLOCK/WARN Summary

Production readiness:

- Status counts: `BLOCK=8`, `PASS=31`, `WARN=8`
- Main BLOCK: required monthly validation failures remain.
- `validation_failure_patterns`: BLOCK
  - `CANDIDATE_FIXED=2`
  - `PERSISTENT_BLOCK=3`
  - `REGRESSION_RISK=3`
- `validation_failure_drilldown`: PASS
  - root causes: `insufficient_recovery=2`, `direct_alpha_ineligible=2`, `selection_or_exposure_regression=1`, `over_defense_or_filter_drag=1`, `drawdown_pressure=1`, `candidate_fixed_failure=1`
  - evidence gaps: 0 scenarios
- `walk_forward_train_candidate_coverage`: WARN
  - `under_covered=5`
  - `min_candidates=1`
  - `min_unique_scores=1`
  - `fallback_only=5`
  - `direct_alpha_ineligible=5`
- `validation_scenarios`: BLOCK
  - `stress_exclude_500pct_winners`
  - `regime_sideways`
  - `walk_forward_001`
  - `walk_forward_003`
  - `walk_forward_005`
- `performance_report`: BLOCK
  - required scenarios failed: 5 of 18
  - min required excess return: `-7.1648%`
  - min walk-forward excess return: `-5.5812%`
  - worst max drawdown: `-28.0835%`

Health:

- Overall: `WARN`
- Only non-PASS check: `scalper_data`
- Reason: latest scalper file is stale, age about 300 hours.
- Action: inspect or restart cloud scalper collector if tick/paper scalper data is still needed.

## Latest Code/Report Changes

Touched in latest loop:

- `backtester/monthly_rebalance.py`
- `backtester/readiness.py`
- `backtester/__main__.py`
- `tests/test_monthly_rebalance.py`
- `tests/test_readiness.py`
- `tests/test_cli.py`
- `data/reports/monthly_validation_scenarios_pit_universe.csv`
- `data/reports/monthly_validation_failure_drilldown.csv`
- `data/reports/monthly_validation_failure_patterns.csv`
- `data/reports/regime_sideways_decision_attribution.csv`
- `data/reports/regime_sideways_symbol_attribution.csv`
- `data/reports/walk_forward_003_decision_attribution.csv`
- `data/reports/walk_forward_003_symbol_attribution.csv`
- `data/reports/walk_forward_005_decision_attribution.csv`
- `data/reports/walk_forward_005_symbol_attribution.csv`
- `data/reports/regime_bear_decision_attribution.csv`
- `data/reports/regime_bear_symbol_attribution.csv`
- `data/reports/walk_forward_002_decision_attribution.csv`
- `data/reports/walk_forward_002_symbol_attribution.csv`
- `data/reports/walk_forward_004_decision_attribution.csv`
- `data/reports/walk_forward_004_symbol_attribution.csv`
- `data/reports/monthly_validation_candidate_multi_preset.csv`
- `data/reports/monthly_validation_comparison_multi_preset.csv`
- `data/reports/monthly_validation_comparison_deltas_multi_preset.csv`
- `data/reports/monthly_validation_candidate_decision_multi_preset.csv`
- `data/reports/production_readiness.csv`
- `data/reports/production_readiness_report.md`
- `data/reports/health_status.json`
- `data/reports/health_status.md`
- `docs/GOAL_MODE_CHECKPOINT.md`

## Commands Run In Latest Loop

Current loop additions:

```powershell
python -m compileall -q backtester
python -m unittest discover -s tests
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_recovery_attribution_summarizes_exposure_and_loss_symbols tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_recovery_attribution_writes_csv tests.test_cli.CliTests.test_monthly_attribution_help_includes_stress_and_output_options tests.test_cli.CliTests.test_monthly_attribution_cli_writes_recovery_summary_report
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2024-10-14 --end 2025-04-17 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-name regime_sideways --monthly-output data/reports/regime_sideways_monthly_attribution.csv --symbol-output data/reports/regime_sideways_symbol_attribution.csv --decision-output data/reports/regime_sideways_decision_attribution.csv --summary-output data/reports/regime_sideways_recovery_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2026-01-28 --end 2026-04-30 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-name walk_forward_005 --monthly-output data/reports/walk_forward_005_monthly_attribution.csv --symbol-output data/reports/walk_forward_005_symbol_attribution.csv --decision-output data/reports/walk_forward_005_decision_attribution.csv --summary-output data/reports/walk_forward_005_recovery_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2025-07-23 --end 2025-10-27 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-name walk_forward_003 --monthly-output data/reports/walk_forward_003_monthly_attribution.csv --symbol-output data/reports/walk_forward_003_symbol_attribution.csv --decision-output data/reports/walk_forward_003_decision_attribution.csv --summary-output data/reports/walk_forward_003_recovery_attribution.csv
python -m unittest tests.test_monthly_rebalance tests.test_cli
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

Previous recorded additions:

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_direct_alpha_selection_explains_selected_and_rejected_symbols tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_direct_alpha_selection_writes_csv
python -m unittest tests.test_cli.CliTests.test_monthly_direct_alpha_diagnostics_cli_writes_selection_report
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_direct_alpha_selection_explains_selected_and_rejected_symbols tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_direct_alpha_selection_writes_csv tests.test_cli.CliTests.test_monthly_direct_alpha_diagnostics_cli_writes_selection_report
python -m backtester monthly-direct-alpha-diagnostics --data-dir data/krx_expanded --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --scenario walk_forward_003 --scenario walk_forward_004 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --output data/reports/monthly_direct_alpha_selection_diagnostics.csv
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_flags_direct_alpha_ineligible tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_drilldown_writes_csv tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_walk_forward_validation_records_direct_train_diagnostics
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_walk_forward_validation_records_direct_train_diagnostics
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_flags_direct_alpha_ineligible tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_drilldown_writes_csv tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_walk_forward_validation_records_direct_train_candidate_scores tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_walk_forward_validation_records_direct_train_diagnostics tests.test_cli.CliTests.test_monthly_failure_drilldown_cli_writes_report
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
python -m unittest discover -s tests
python -m compileall -q backtester
```

```powershell
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_patterns_flags_persistent_and_regression tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_patterns_writes_csv tests.test_readiness.ProductionReadinessTests.test_validation_failure_patterns_block_persistent_failures tests.test_cli.CliTests.test_monthly_failure_patterns_cli_writes_report
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_summarizes_root_cause_and_gaps tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_drilldown_writes_csv tests.test_cli.CliTests.test_monthly_failure_drilldown_cli_writes_report tests.test_readiness.ProductionReadinessTests.test_validation_failure_drilldown_warns_on_missing_attribution_evidence
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2024-10-14 --end 2025-04-17 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/regime_sideways_monthly_attribution.csv --symbol-output data/reports/regime_sideways_symbol_attribution.csv --decision-output data/reports/regime_sideways_decision_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2025-07-23 --end 2025-10-27 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/walk_forward_003_monthly_attribution.csv --symbol-output data/reports/walk_forward_003_symbol_attribution.csv --decision-output data/reports/walk_forward_003_decision_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2026-01-28 --end 2026-04-30 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/walk_forward_005_monthly_attribution.csv --symbol-output data/reports/walk_forward_005_symbol_attribution.csv --decision-output data/reports/walk_forward_005_decision_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2024-07-08 --end 2025-01-13 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/regime_bear_monthly_attribution.csv --symbol-output data/reports/regime_bear_symbol_attribution.csv --decision-output data/reports/regime_bear_decision_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2025-04-18 --end 2025-07-22 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/walk_forward_002_monthly_attribution.csv --symbol-output data/reports/walk_forward_002_symbol_attribution.csv --decision-output data/reports/walk_forward_002_decision_attribution.csv
python -m backtester monthly-attribution --data-dir data/krx_expanded --start 2025-10-28 --end 2026-01-27 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --monthly-output data/reports/walk_forward_004_monthly_attribution.csv --symbol-output data/reports/walk_forward_004_symbol_attribution.csv --decision-output data/reports/walk_forward_004_decision_attribution.csv
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m unittest tests.test_readiness.ProductionReadinessTests.test_walk_forward_single_train_candidate_warns_readiness tests.test_readiness.ProductionReadinessTests.test_walk_forward_multiple_train_candidates_passes_readiness tests.test_readiness.ProductionReadinessTests.test_walk_forward_duplicate_train_candidate_scores_warn_readiness tests.test_readiness.ProductionReadinessTests.test_walk_forward_train_candidate_warning_recommends_candidate_expansion
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --presets balanced,aggressive,retail --scenario-output data/reports/monthly_validation_candidate_multi_preset.csv --data-quality-output data/reports/monthly_validation_data_quality_candidate_multi_preset.csv --coverage-output data/reports/monthly_universe_price_coverage_candidate_multi_preset.csv --performance-output data/reports/monthly_performance_audit_candidate_multi_preset.csv --concentration-output data/reports/monthly_performance_concentration_candidate_multi_preset.csv --failure-output data/reports/monthly_validation_failures_candidate_multi_preset.csv --remediation-output data/reports/monthly_validation_remediation_candidate_multi_preset.csv --sweep-plan-output data/reports/monthly_validation_sweep_plan_candidate_multi_preset.csv --sweep-result-output data/reports/monthly_validation_sweep_results_candidate_multi_preset.csv --universe-filter-report data/reports/universe_filter_report_candidate_multi_preset.csv --deployment-gate-output data/reports/monthly_deployment_gate_candidate_multi_preset.csv
python -m backtester monthly-compare-validation --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --candidate data/reports/monthly_validation_candidate_multi_preset.csv --candidate-label multi_preset --output data/reports/monthly_validation_comparison_multi_preset.csv --delta-output data/reports/monthly_validation_comparison_deltas_multi_preset.csv --decision-output data/reports/monthly_validation_candidate_decision_multi_preset.csv
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --delta-glob __no_auto_delta_reports__ --delta-report data/reports/monthly_validation_comparison_deltas_position_stop_12.csv --delta-report data/reports/monthly_validation_comparison_deltas_weak_cash_10_position_stop_12.csv --delta-report data/reports/monthly_validation_comparison_deltas_weak_defense_cash_10.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --delta-glob __no_auto_delta_reports__ --delta-report data/reports/monthly_validation_comparison_deltas_position_stop_12.csv --delta-report data/reports/monthly_validation_comparison_deltas_weak_cash_10_position_stop_12.csv --delta-report data/reports/monthly_validation_comparison_deltas_weak_defense_cash_10.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m unittest tests.test_cli.CliTests.test_monthly_failure_patterns_explicit_delta_report_does_not_read_default_glob tests.test_cli.CliTests.test_monthly_failure_patterns_default_glob_skips_multi_preset_diagnostics tests.test_cli.CliTests.test_monthly_failure_drilldown_explicit_delta_report_does_not_read_default_glob
python -m unittest tests.test_cli.CliTests.test_monthly_failure_patterns_cli_writes_report tests.test_cli.CliTests.test_monthly_failure_patterns_explicit_delta_report_does_not_read_default_glob tests.test_cli.CliTests.test_monthly_failure_patterns_default_glob_skips_multi_preset_diagnostics tests.test_cli.CliTests.test_monthly_failure_drilldown_cli_writes_report tests.test_cli.CliTests.test_monthly_failure_drilldown_explicit_delta_report_does_not_read_default_glob tests.test_cli.CliTests.test_monthly_failure_drilldown_cli_uses_attribution_dir
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_run_monthly_walk_forward_validation_records_direct_train_candidate_scores tests.test_readiness.ProductionReadinessTests.test_walk_forward_fallback_only_with_negative_direct_scores_reports_ineligible_alpha
python -m unittest tests.test_readiness.ProductionReadinessTests.test_walk_forward_direct_alpha_ineligible_recommends_train_alpha_diagnosis
python -m unittest tests.test_readiness.ProductionReadinessTests.test_walk_forward_fallback_only_with_negative_direct_scores_reports_ineligible_alpha tests.test_readiness.ProductionReadinessTests.test_walk_forward_direct_alpha_ineligible_recommends_train_alpha_diagnosis tests.test_readiness.ProductionReadinessTests.test_walk_forward_train_candidate_warning_recommends_candidate_expansion
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_flags_direct_alpha_ineligible
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_summarizes_root_cause_and_gaps tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_uses_train_candidate_scores tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_flags_direct_alpha_ineligible tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_drilldown_writes_csv
python -m unittest tests.test_readiness.ProductionReadinessTests.test_performance_concentration_wrong_source_warns_readiness
python -m unittest tests.test_readiness.ProductionReadinessTests.test_missing_performance_concentration_report_warns_readiness tests.test_readiness.ProductionReadinessTests.test_performance_concentration_block_blocks_readiness tests.test_readiness.ProductionReadinessTests.test_performance_concentration_wrong_source_warns_readiness
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
python -m backtester production-check --allow-blocked-exit-zero
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

## Next Highest-Value Work

1. Design one narrow candidate experiment from the recovery summaries:
   - cap high-exposure `market_beta_proxy` losses in `2025-03` and `2026-03`,
   - avoid broad cash drag that would weaken `walk_forward_003` and other recovery windows,
   - preserve the existing train gate for direct-alpha-ineligible windows.
2. Compare the candidate against baseline with full validation and delta reports before considering adoption.
3. Separately preserve the behavior that fixed:
   - `stress_exclude_500pct_winners`
   - `walk_forward_001`
4. Avoid candidate settings that introduce:
   - `walk_forward_002`
   - `regime_bear`
   - `walk_forward_004`
5. Keep all changes paper-only.

## Resume Procedure

When goal mode resumes:

1. Read this file first.
2. Run `git status --short`.
3. Inspect current reports under `data/reports/`.
4. Start from the highest BLOCK cause, not from a new strategy idea.
5. Use TDD for code changes.
6. Regenerate affected reports.
7. Run:

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
```

8. Update this checkpoint at the end of the loop.
9. Commit stable verified checkpoints when practical.

## Scheduled Resume

- A thread heartbeat is scheduled for 04:20 KST.
- A detached workspace cron automation is scheduled for 09:30 KST.
- The 09:30 cron automation id is `goal-mode-cron-09-30`.
- The cron should read this checkpoint first, continue the goal-mode loop, run tests, and update this file.
