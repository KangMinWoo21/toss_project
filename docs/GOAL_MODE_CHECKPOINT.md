# Goal Mode Checkpoint

Last updated: 2026-06-22 16:59 KST

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

- `python -m unittest discover -s tests`: PASS, 402 tests.
- `python -m compileall -q backtester`: PASS.
- `production-check`: BLOCK by design, because 5 required validation scenarios still fail.
- `health-check`: WARN, only because scalper data is stale.
- Candidate follow-up state: all 3 full-validation candidates completed, all rejected.
- Failure-pattern and failure-drilldown reports are generated and integrated into `production-check`.
- `validation_failure_drilldown`: PASS. Evidence gaps are now closed.

## Latest Loop Results

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
