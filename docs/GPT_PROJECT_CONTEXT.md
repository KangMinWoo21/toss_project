# GPT Project Context: Toss Securities Paper-Operation Trading System

Generated at: 2026-06-22 16:43 KST

This document is a compact project handoff for GPT. It summarizes the current repository state, safety rules, architecture, reports, validation results, and next work. It intentionally excludes secrets, `.env` values, private credentials, and raw downloaded market data.

## One-Line Summary

This repository is a Python trading research and automation toolkit being hardened into a safe paper-operation system. It must not become a live-trading bot until readiness, validation, drawdown, health, and operational safety gates pass.

## Absolute Safety Rules

- Do not add real order execution.
- Do not enable live trading by default.
- Keep `PRODUCTION_TRADING_ENABLED` off by default.
- Do not call Toss API from tests.
- Do not print, copy, summarize, or commit `.env` secrets.
- Monthly workflows may create plans and reports only.
- Treat blocked readiness or risk reports as hard stops.
- Prefer deterministic `unittest` tests with temp files and fixtures.
- Preserve existing CLI compatibility.

## Current Verdict

The system is not ready for real-money automated trading.

Current practical status:

- Paper operation / dry run: acceptable and useful.
- Live market data with no order transmission: acceptable if secrets are protected.
- Fully automated live trading: not acceptable.
- Very small live experiment: still premature.

Why:

- `production-check`: `BLOCK`
- `health-check`: `WARN`
- Required validation failures remain: 5 of 18
- Readiness status counts: `BLOCK=8`, `PASS=31`, `WARN=8`
- Worst max drawdown: `-28.0835%`
- Walk-forward train alpha is weak or ineligible.
- Some rejected remediation candidates fixed two failures but introduced or preserved regressions elsewhere.

## Latest Commit Context

Recent commits:

```text
fc51fb3 Add train decision path diagnostics
bb7d015 Add direct alpha holding path diagnostics
958249b Add direct alpha selection diagnostics
8cd4dcc Add direct alpha train diagnostics
bd9b613 Classify direct alpha train failures
```

Latest committed checkpoint before this loop:

- `fc51fb3 Add train decision path diagnostics`
- Added `monthly-train-decision-diagnostics`.
- Added `data/reports/monthly_train_decision_path_diagnostics.csv`.
- The report reconstructs recursive monthly train decisions inside walk-forward train windows and explains `alpha_ratio=0` with row-level decision mode, reason, `alpha_block_reason`, direct candidate scores/rejection reasons, prior breadth, target exposure, cash weight, and universe counts.
- `python -m unittest discover -s tests`: PASS, 397 tests.
- `python -m compileall -q backtester`: PASS.

Latest current loop work:

- Extended `monthly-train-decision-diagnostics` with `--stability-output`.
- Added `data/reports/monthly_train_stability_window_diagnostics.csv`.
- The report decomposes candidate `train_positive_ratio` into stability subwindows with subwindow total/buy-hold/excess return, drawdown, trade count, positive flag, and rejection reasons.
- `walk_forward_003`: 52 counted stability rows; 16 positive and 36 nonpositive/no-trade subwindows; candidate positive ratios are mainly `0.25` or `0.5`; worst subwindow is `train_stability_2024_2025` ending `2025-04-30`, excess `-55.0564`.
- `walk_forward_004`: 52 counted stability rows; 17 positive and 35 nonpositive/no-trade subwindows; candidate positive ratios range `0.0` to `0.75`; worst subwindow is also `train_stability_2024_2025` ending `2025-04-30`, excess `-55.0564`.
- Current full verification after this work: `python -m unittest discover -s tests` PASS with `399` tests; `python -m compileall -q backtester` PASS.
- `production-check` remains `BLOCK` with `BLOCK=8`, `PASS=31`, `WARN=8`; `health-check` remains `WARN` because scalper data is stale (`age_hours=303.89` observed).

## Current Git Worktree Warning

The repository has many existing uncommitted changes outside the latest direct-alpha diagnostics commit. Do not revert them blindly. Treat them as user or prior-session work.

Known modified/untracked areas include:

- Modified: `README.md`
- Modified modules: `backtester/auto_scalper.py`, `config.py`, `engine.py`, `events.py`, `flow.py`, `leader_swing.py`, `news.py`, `pykrx_fetcher.py`, `scalper.py`, `strategies.py`
- Modified tests: `tests/test_auto_scalper.py`, `test_config.py`, `test_engine.py`, `test_events.py`, `test_flow.py`, `test_leader_swing.py`, `test_news.py`, `test_pykrx_fetcher.py`, `test_scalper.py`
- Untracked modules: `backtester/data_quality.py`, `execution_plan.py`, `health.py`, `portfolio.py`, `risk.py`
- Untracked docs/scripts/tests for cloud operation, health, portfolio, risk, and execution planning

## Project Goal

Make this repository a safe paper-operation trading research system, not a live-trading bot.

Primary focus:

- Data quality and point-in-time correctness
- Walk-forward validation reliability
- Drawdown, liquidity, and transaction-cost realism
- Production readiness and health monitoring
- Clear human-readable reports and next actions
- Paper-only operational workflows

## Repository Structure

Core package:

- `backtester/__main__.py`: CLI entry point.
- `backtester/monthly_rebalance.py`: monthly validation, monthly paper plan, deployment gate, attribution, failure diagnostics, sweep planning.
- `backtester/readiness.py`: production readiness checks and recommendations.
- `backtester/health.py`: health-check report generation.
- `backtester/execution_plan.py`: paper execution planning.
- `backtester/risk.py`: risk guard checks.
- `backtester/portfolio.py`: portfolio state helpers.
- `backtester/pykrx_fetcher.py`: KRX / pykrx data fetching utilities.
- `backtester/toss.py`: Toss API adapter. Do not call from tests.
- `backtester/scalper.py` and `backtester/auto_scalper.py`: paper scalper logic and collector.
- `backtester/strategies.py`: basic strategy implementations.
- `backtester/momentum_rotation.py`: direct momentum rotation strategy.
- `backtester/momentum_validation.py`: walk-forward and train candidate selection helpers.
- `backtester/leader_swing.py`, `leader_regime_switch.py`, `leader_window_study.py`: leader/swing strategy research.
- `backtester/events.py`, `news.py`, `flow.py`, `dart.py`: event, news, flow, and DART-related scoring inputs.
- `backtester/data_quality.py`: data-quality screening.
- `backtester/models.py`: shared data models such as candles.
- `backtester/analysis.py`, `reporting.py`, `regime.py`, `study.py`, `swing_sweep.py`, `scalp_replay.py`: analysis/reporting/replay support.

Tests:

- Standard library `unittest`.
- Tests live under `tests/`.
- Current full suite: 399 tests passing as of the latest checkpoint.
- Important files:
  - `tests/test_monthly_rebalance.py`
  - `tests/test_readiness.py`
  - `tests/test_cli.py`
  - `tests/test_momentum_rotation.py`
  - `tests/test_momentum_validation.py`
  - `tests/test_health.py`
  - `tests/test_risk.py`
  - `tests/test_execution_plan.py`

Docs:

- `docs/GOAL_MODE_CHECKPOINT.md`: current running checkpoint. Read first when resuming work.
- `docs/GPT_PROJECT_CONTEXT.md`: this handoff file.
- `docs/safe-research-operation.md`: safe operation notes.
- `docs/project-overview.md`: broader overview.
- `docs/cloud-always-on-operation-plan.md`: cloud operation plan.
- `docs/event-data-integration.md`: event-data notes.
- `docs/strategy-comparison-review.md`: strategy comparison notes.
- `docs/tossinvest-openapi-guide.md` and `docs/tossinvest-openapi.json`: Toss API reference materials.

Data and reports:

- `data/krx_expanded/`: expanded KRX OHLCV data.
- `data/krx_metadata/krx_universe_monthly.csv`: point-in-time universe snapshots.
- `data/reports/`: generated reports.
- Report files are operational outputs and may not all be git-tracked.

Scripts:

- `scripts/cloud/run_monthly_plan.sh`
- `scripts/cloud/run_health_check.sh`
- `scripts/cloud/run_scalper.sh`
- `scripts/cloud/toss-monthly-plan.service`
- `scripts/cloud/toss-monthly-plan.timer`
- Other PowerShell helpers for downloading or registering report/scalper tasks.

## Core Commands

Run full tests:

```powershell
python -m unittest discover -s tests
```

Check syntax:

```powershell
python -m compileall -q backtester
```

Run production readiness:

```powershell
python -m backtester production-check --allow-blocked-exit-zero
```

Run health check:

```powershell
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

Regenerate baseline monthly validation:

```powershell
python -m backtester monthly-validate --data-dir data/krx_expanded --start 2024-01-01 --end 2026-06-18 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --scenario-output data/reports/monthly_validation_scenarios_pit_universe.csv --deployment-gate-output data/reports/monthly_deployment_gate_pit_universe.csv
```

Regenerate failure patterns:

```powershell
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
```

Regenerate failure drilldown:

```powershell
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
```

Regenerate recursive train decision and stability diagnostics:

```powershell
python -m backtester monthly-train-decision-diagnostics --data-dir data/krx_expanded --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --scenario walk_forward_003 --scenario walk_forward_004 --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv --output data/reports/monthly_train_decision_path_diagnostics.csv --stability-output data/reports/monthly_train_stability_window_diagnostics.csv
```

## Current Readiness State

Production readiness:

```text
Overall: BLOCK
Status counts: BLOCK=8, PASS=31, WARN=8
```

Main blockers:

- `deployment_gate`: BLOCK
- `validation_scenarios`: BLOCK
- `validation_failure_actions`: BLOCK
- `validation_remediation`: BLOCK
- `validation_failure_patterns`: BLOCK
- `risk_report`: BLOCK
- `performance_report`: BLOCK

Current warnings:

- `walk_forward_train_candidate_coverage`
- `validation_sweep_plan`
- `validation_sweep_results`
- `validation_comparison`
- `validation_comparison_deltas`
- `validation_candidate_decision`
- `validation_candidate_followup`
- `krx_missing_ohlcv_fetch_summary`

Health:

```text
Overall: WARN
Only non-PASS check: scalper_data
Reason: latest paper scalper file is stale, age about 301 hours.
```

## Current Required Validation Failures

Five required scenarios still fail:

| Scenario | Category | Reason | Excess Return | Max Drawdown | Train Excess |
| --- | --- | --- | ---: | ---: | ---: |
| `stress_exclude_500pct_winners` | stress | `max_drawdown_breach` | `12.9565%` | `-28.0835%` | |
| `regime_sideways` | regime | `negative_excess_return` | `-7.1648%` | `-23.9059%` | |
| `walk_forward_001` | walk_forward | `negative_excess_return` | `-0.7420%` | `-25.1309%` | `19.2280%` |
| `walk_forward_003` | walk_forward | `train_window_rejected` | `8.7530%` | `-7.1592%` | `-1.3447%` |
| `walk_forward_005` | walk_forward | `negative_excess_return` | `-5.5812%` | `-20.5503%` | `38.8708%` |

## Failure Drilldown Root Causes

Current root cause counts:

| Root Cause | Count |
| --- | ---: |
| `insufficient_recovery` | 2 |
| `direct_alpha_ineligible` | 2 |
| `selection_or_exposure_regression` | 1 |
| `over_defense_or_filter_drag` | 1 |
| `drawdown_pressure` | 1 |
| `candidate_fixed_failure` | 1 |

Scenario mapping:

- `regime_sideways`: `insufficient_recovery`
- `walk_forward_003`: `direct_alpha_ineligible`
- `walk_forward_005`: `insufficient_recovery`
- `regime_bear`: `selection_or_exposure_regression`
- `walk_forward_002`: `over_defense_or_filter_drag`
- `walk_forward_004`: `direct_alpha_ineligible`
- `stress_exclude_500pct_winners`: `drawdown_pressure`
- `walk_forward_001`: `candidate_fixed_failure`

## Direct Alpha Train Diagnostics

The latest commit added `train_direct_diagnostics` to monthly validation and failure drilldown reports.

Purpose:

- Explain why direct train alpha candidates are ineligible.
- Decompose by period, universe, liquidity, market regime, and direct-vs-buy-hold performance.
- Avoid blindly loosening train gates when the train alpha itself is weak.

Key findings:

### `walk_forward_003`

- Train window: `2024-07-08..2025-07-22`
- `period_days=380`
- `raw_symbols=2184`
- `universe_symbols=2081`
- `pit_symbols=2029`
- `liquid_symbols=100`
- `train_symbols=100`
- `universe_removed=103`
- `pit_filter_removed=52`
- `liquidity_removed=1929`
- `train_coverage_removed=0`
- `train_avg_symbol_return_pct=53.6167`
- `train_median_symbol_return_pct=36.7157`
- `market_regime=risk_on`
- `direct_candidate_count=1`
- `best_direct_total_return_pct=16.2733`
- `best_direct_buy_hold_return_pct=35.9941`
- `best_direct_excess_pct=-19.7208`
- `all_direct_excess_nonpositive=true`

Interpretation: train coverage is not missing and the broad backdrop is not weak. Direct alpha underperformed a strong buy-hold benchmark after PIT and top-100 liquidity filtering.

### `walk_forward_004`

- Train window: `2024-10-14..2025-10-27`
- `period_days=379`
- `raw_symbols=2184`
- `universe_symbols=2081`
- `pit_symbols=2022`
- `liquid_symbols=100`
- `train_symbols=100`
- `universe_removed=103`
- `pit_filter_removed=59`
- `liquidity_removed=1922`
- `train_coverage_removed=0`
- `train_avg_symbol_return_pct=87.4997`
- `train_median_symbol_return_pct=68.4406`
- `market_regime=risk_on`
- `direct_candidate_count=1`
- `best_direct_total_return_pct=0.4340`
- `best_direct_buy_hold_return_pct=60.5903`
- `best_direct_excess_pct=-60.1564`
- `all_direct_excess_nonpositive=true`

Interpretation: the direct alpha candidate badly lagged a very strong buy-hold backdrop. Do not solve this by loosening train gates.

## Recursive Train Decision And Stability Diagnostics

Reports:

```text
data/reports/monthly_train_decision_path_diagnostics.csv
data/reports/monthly_train_stability_window_diagnostics.csv
```

Generated for:

- `walk_forward_003`
- `walk_forward_004`

Decision-path findings:

- Both scenarios have `13` recursive train decisions.
- Both scenarios are fallback-only in the train path: `13 market_beta_proxy`, `0 alpha`, `0 cash`.
- `alpha_ratio=0`.
- Main alpha block reasons:
  - `no_eligible_direct_candidate=12`
  - `weak_breadth_and_weak_train_average=1`
- The system is not missing candidates entirely; the single direct candidate usually fails stability/positive-ratio gates, and later often fails nonpositive-excess as well.

Stability-window findings:

- `walk_forward_003`
  - `52` counted stability rows.
  - `16` positive subwindows, `36` nonpositive/no-trade subwindows.
  - Candidate positive ratios are mainly `0.25` or `0.5`.
  - Worst subwindow: `train_stability_2024_2025`, `2024-01-01..2025-04-30`, excess `-55.0564`, trades `34`.
- `walk_forward_004`
  - `52` counted stability rows.
  - `17` positive subwindows, `35` nonpositive/no-trade subwindows.
  - Candidate positive ratios range from `0.0` to `0.75`.
  - Worst subwindow: `train_stability_2024_2025`, `2024-01-01..2025-04-30`, excess `-55.0564`, trades `34`.

Interpretation:

- `low_positive_ratio` is now decomposed into concrete windows, not just a compact score.
- Older windows such as `2021_2022`, `2022_2023`, and `2023_2024` repeatedly have negative excess even when headline candidate excess is positive in late 2024.
- In 2025, the direct candidate often becomes both unstable and outright negative-excess.
- Do not loosen the positive-ratio gate yet.

## Direct Alpha Symbol-Selection Diagnostics

New report:

```text
data/reports/monthly_direct_alpha_selection_diagnostics.csv
```

Generated for:

- `walk_forward_003`
- `walk_forward_004`

Current report size:

- `200` rows
- `2` scenarios x `100` train symbols

`walk_forward_003` summary:

- `5 selected`, `95 rejected`
- Rejection reasons: `below_selected_rank=87`, `trend_filter_failed=8`
- Candidate turnover: `trade_count=10`, `buy_count=5`, `sell_count=5`, `unique_traded_symbols=5`
- Candidate performance: `total_return_pct=16.2733`, `buy_hold_return_pct=35.9941`, `excess_return_pct=-19.7208`
- Train-end selected symbols had high momentum and strong train-period returns, so the next question is whether the benchmark is too strong, the train-end snapshot differs from in-period holdings, or the alpha/turnover path lagged the equal-weight benchmark.

`walk_forward_004` summary:

- `5 selected`, `95 rejected`
- Rejection reasons: `below_selected_rank=91`, `trend_filter_failed=4`
- Candidate turnover: `trade_count=16`, `buy_count=8`, `sell_count=8`, `unique_traded_symbols=8`
- Candidate performance: `total_return_pct=0.4340`, `buy_hold_return_pct=60.5903`, `excess_return_pct=-60.1564`
- Train-end selected symbols were also strong, but the candidate path badly lagged the top-100 liquid benchmark.

Next diagnostic:

- Shift from direct-alpha eligibility to scenario failure attribution, especially `regime_sideways` and `walk_forward_005` (`insufficient_recovery`).

## Important Strategic Interpretation

The immediate issue is not simply that there is only one preset candidate.

Evidence:

- Multi-preset diagnostic validation with `balanced,aggressive,retail` did not improve required failure count.
- The three preset names produced identical train score signatures in walk-forward windows.
- Walk-forward monthly train decisions show `alpha_ratio=0`; they are fallback-only, usually `market_beta_proxy`, sometimes `cash`.
- Direct alpha candidates are also negative excess in walk-forward train windows.

Implication:

- Expanding preset names without changing actual decision diversity will not fix the system.
- Selection, turnover, benchmark construction, top-100 liquid universe behavior, and train-window stability have now been inspected for `walk_forward_003` and `walk_forward_004`; the next high-value work is attribution for the remaining required scenario failures.

## Candidate Experiment History

Generated candidate family:

- `position_stop_12`
- `weak_cash_10_position_stop_12`
- `weak_defense_cash_10`

Result:

- All 3 full-validation candidates completed.
- All were rejected.
- Some fixed `stress_exclude_500pct_winners` and `walk_forward_001`.
- They did not fix `regime_sideways`, `walk_forward_003`, or `walk_forward_005`.
- They introduced or preserved regression risk in:
  - `walk_forward_002`
  - `regime_bear`
  - `walk_forward_004`

Do not continue the same candidate family as-is.

## What Must Be True Before Live Trading

Minimum gate:

- `production-check`: PASS
- Required validation failures: 0
- `health-check`: PASS or only explicitly accepted non-critical WARNs
- Worst drawdown below hard block threshold, preferably much better than `-20%`
- Walk-forward train alpha no longer fallback-only / direct-ineligible
- Candidate fixes do not introduce new failures
- Risk report is PASS
- Paper operation has fresh reports

Operational safety required before any real order path:

- Kill switch
- Daily loss limit
- Total order value limit
- Single order value limit
- Max order count
- ADV participation limit
- Liquidity checks
- Duplicate order prevention
- Position/cash reconciliation
- Explicit dry-run vs real-run mode separation
- Manual approval phase before any automated execution
- Failure mode should stop, not force liquidation automatically

## Suggested Next Highest-Value Work

1. Build a narrow attribution drilldown for `regime_sideways` and `walk_forward_005`, the remaining `insufficient_recovery` failures.
2. Compare exposure, cash ratio, worst holding periods, and symbol-level contribution against the now-explained `walk_forward_003` direct-alpha-ineligible case.
3. Preserve the candidate behavior that fixed `stress_exclude_500pct_winners` and `walk_forward_001`, but isolate it so it does not create `regime_bear`, `walk_forward_002`, or `walk_forward_004` regressions.
4. Continue working from failed scenario evidence, not from broad parameter sweeps.
5. Keep all changes paper-only.

## Resume Procedure For GPT

When another GPT or agent resumes:

1. Read `docs/GOAL_MODE_CHECKPOINT.md`.
2. Read this file.
3. Run `git status --short`.
4. Inspect current generated reports under `data/reports/`.
5. Start from the highest BLOCK cause.
6. Use tests before code changes.
7. Do not call Toss API in tests.
8. Do not print or commit secrets.
9. Regenerate affected reports after behavior/report changes.
10. Run:

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
```

11. Update `docs/GOAL_MODE_CHECKPOINT.md`.
12. Commit verified stable checkpoints when practical.

## GPT Handoff Prompt

Use this prompt when pasting this project into GPT:

```text
You are helping with a Python trading research repository. The goal is a safe paper-operation trading research and monitoring system, not a live-trading bot.

Absolute rules:
- Do not add real order execution.
- Do not enable live trading by default.
- Do not call Toss API from tests.
- Do not expose .env secrets.
- Treat production-check BLOCK as a hard stop.
- Use deterministic unittest tests before behavior changes.

Current state:
- production-check is BLOCK.
- health-check is WARN only because scalper data is stale.
- Full unittest recently passed: 399 tests.
- compileall passed.
- Required validation failures remain: stress_exclude_500pct_winners, regime_sideways, walk_forward_001, walk_forward_003, walk_forward_005.
- Main current research issue: direct alpha train candidates are ineligible, especially walk_forward_003 and walk_forward_004. The latest diagnostics show the broad train regime is risk_on and coverage is not missing, direct alpha badly underperforms buy-hold after PIT/top-100 liquidity filtering, and `low_positive_ratio` is caused by concrete negative stability subwindows rather than missing data.

Your next task should start from the current BLOCK causes, not from a new strategy idea.
```

## Source File Map

Non-data project files currently visible:

```text
AGENTS.md
README.md
backtester/__init__.py
backtester/__main__.py
backtester/analysis.py
backtester/auto_scalper.py
backtester/config.py
backtester/dart.py
backtester/data.py
backtester/data_quality.py
backtester/engine.py
backtester/events.py
backtester/execution_plan.py
backtester/flow.py
backtester/health.py
backtester/leader_regime_switch.py
backtester/leader_swing.py
backtester/leader_window_study.py
backtester/models.py
backtester/momentum_rotation.py
backtester/momentum_validation.py
backtester/monthly_rebalance.py
backtester/news.py
backtester/portfolio.py
backtester/pykrx_fetcher.py
backtester/readiness.py
backtester/regime.py
backtester/reporting.py
backtester/risk.py
backtester/scalp_replay.py
backtester/scalper.py
backtester/strategies.py
backtester/study.py
backtester/swing_sweep.py
backtester/toss.py
docs/GOAL_MODE_CHECKPOINT.md
docs/GPT_PROJECT_CONTEXT.md
docs/academic-backtesting-notes.md
docs/cloud-always-on-operation-plan.md
docs/event-data-integration.md
docs/oracle-cloud-free-vm-guide.md
docs/project-overview.md
docs/retail_edge_strategy_notes.md
docs/safe-research-operation.md
docs/strategy-comparison-review.md
docs/tossinvest-openapi-guide.md
docs/tossinvest-openapi.json
scripts/cloud/backup_scalper.sh
scripts/cloud/run_auto_scalper.sh
scripts/cloud/run_health_check.sh
scripts/cloud/run_monthly_plan.sh
scripts/cloud/run_scalper.sh
scripts/cloud/toss-monthly-plan.service
scripts/cloud/toss-monthly-plan.timer
scripts/cloud/toss-scalper.service
scripts/collect_scalp_data.ps1
scripts/download_cloud_reports.ps1
scripts/download_scalper_data.ps1
scripts/register_cloud_reports_download_task.ps1
scripts/register_scalper_download_task.ps1
tests/test_auto_scalper.py
tests/test_cli.py
tests/test_cloud_scripts.py
tests/test_config.py
tests/test_dart.py
tests/test_data_quality.py
tests/test_engine.py
tests/test_events.py
tests/test_execution_plan.py
tests/test_flow.py
tests/test_health.py
tests/test_intraday.py
tests/test_leader_regime_switch.py
tests/test_leader_swing.py
tests/test_leader_window_study.py
tests/test_momentum_rotation.py
tests/test_momentum_validation.py
tests/test_monthly_rebalance.py
tests/test_news.py
tests/test_portfolio.py
tests/test_pykrx_fetcher.py
tests/test_readiness.py
tests/test_regime_router.py
tests/test_risk.py
tests/test_scalp_replay.py
tests/test_scalper.py
tests/test_study.py
tests/test_swing_candidates.py
tests/test_swing_strategies.py
tests/test_swing_sweep.py
tests/test_toss.py
tests/test_walk_forward.py
```
