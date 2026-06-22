# GPT Project Context: Toss Securities Paper-Operation Trading System

Generated at: 2026-06-22 18:34:13 KST
Repository root: `C:\Users\KangMinWoo\Documents\토스증권`

This file is the compact handoff. For a source-inclusive snapshot, use `docs/GPT_PROJECT_SNAPSHOT_FULL.md`. Both files intentionally exclude real `.env` values, `.git`, ZIP archives, caches, raw downloaded market data, and large generated CSV datasets.

## One-Line Verdict

This repository is useful for paper-operation research and monitoring, but it is **not ready for real-money automated trading**. `production-check` is still `BLOCK`, and `health-check` is `WARN` because scalper data is stale.

## Non-Negotiable Safety Rules

- Do not add real order execution.
- Do not enable live trading by default.
- Keep `PRODUCTION_TRADING_ENABLED` disabled by default.
- Do not call Toss API from tests.
- Do not expose, print, summarize, or commit `.env` secrets.
- Monthly workflows may create plans, diagnostics, and reports only.
- Treat production/risk/validation/readiness `BLOCK` states as hard stops.
- Preserve deterministic `unittest` coverage and CLI compatibility.
- Do not blindly revert existing uncommitted changes.

## Current Practical Status

- Paper operation / dry run: acceptable and useful.
- Live market data with no order transmission: acceptable only if secrets are protected.
- Fully automated live trading: not acceptable.
- Very small live experiment: still premature.

## Latest Local Verification
- `python -m unittest discover -s tests`: PASS, 411 tests.
- `python -m compileall -q backtester`: PASS.
- `python -m backtester production-check --allow-blocked-exit-zero`: BLOCK.
- `python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero`: WARN; scalper data is stale.

## Required Validation Failures

| scenario | category | reason | excess_return_pct | max_drawdown_pct | train_excess_pct |
| --- | --- | --- | --- | --- | --- |
| stress_exclude_500pct_winners | stress | max_drawdown_breach | 12.9565 | -28.0835 |  |
| regime_sideways | regime | negative_excess_return | -7.1648 | -23.9059 |  |
| walk_forward_001 | walk_forward | negative_excess_return | -0.742 | -25.1309 | 19.228 |
| walk_forward_003 | walk_forward | train_window_rejected | 8.753 | -7.1592 | -1.3447 |
| walk_forward_005 | walk_forward | negative_excess_return | -5.5812 | -20.5503 | 38.8708 |

## Failure Drilldown Highlights

| scenario | category | root_cause | reason | excess_pct | max_dd_pct | next_action |
| --- | --- | --- | --- | --- | --- | --- |
| regime_sideways | regime | insufficient_recovery | negative_excess_return | -7.1648 | -23.9059 | Use attribution evidence to isolate the partial fix before changing risk parameters. |
| walk_forward_005 | walk_forward | insufficient_recovery | negative_excess_return | -5.5812 | -20.5503 | Use attribution evidence to isolate the partial fix before changing risk parameters. |
| full_period | duration | selection_or_exposure_regression | passed | 60.7053 | -24.044 | Avoid regression configs; compare selected symbols, exposure, and cash weight against baseline. |
| stress_slippage_x3 | stress | selection_or_exposure_regression | passed | 54.883 | -24.0105 | Avoid regression configs; compare selected symbols, exposure, and cash weight against baseline. |
| stress_exclude_500pct_winners | stress | drawdown_pressure | max_drawdown_breach | 12.9565 | -28.0835 | Run drawdown attribution and reduce exposure only after identifying loss months and symbols. |
| walk_forward_001 | walk_forward | scenario_review | negative_excess_return | -0.742 | -25.1309 | Review scenario metrics before adding another parameter experiment. |
| walk_forward_003 | walk_forward | direct_alpha_ineligible | train_window_rejected | 8.753 | -7.1592 | Diagnose why direct alpha train candidates have non-positive excess returns before loosening gates. |

## Latest Candidate Decision

| candidate | decision | baseline_failed | candidate_failed | resolved | new_failures | recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| neutral_breadth_proxy_cap_50 | REJECT | 5 | 6 | walk_forward_003 | full_period; stress_slippage_x3 | Do not adopt this candidate; inspect new failure diagnostics and run narrower paper-only experiments. |

## Neutral Breadth Proxy Cap Attribution Comparison

### full_period

| month | diagnostic | base_ret | cand_ret | ret_delta | base_worst_dd | cand_worst_dd | dd_delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-11 | drawdown_improved | -2.0103 | -1.3867 | 0.6236 | -10.7636 | -10.1636 | 0.6 |
| 2024-12 | drawdown_improved | -2.9667 | -1.7587 | 1.208 | -15.2482 | -11.7815 | 3.4667 |
| 2025-01 | drawdown_improved | 1.6886 | 1.7736 | 0.085 | -12.2507 | -10.4813 | 1.7694 |
| 2025-02 | drawdown_improved | 3.3149 | 3.9316 | 0.6167 | -12.2313 | -12.106 | 0.1253 |
| 2025-03 | drawdown_regression | -9.2322 | -9.935 | -0.7028 | -19.8137 | -20.8382 | -1.0245 |
| 2025-04 | new_drawdown_breach | 1.6378 | 1.8109 | 0.1731 | -24.044 | -25.1331 | -1.0891 |
| 2025-05 | drawdown_regression | 4.5077 | 4.6524 | 0.1447 | -18.8648 | -19.8288 | -0.964 |
| 2025-06 | drawdown_regression | 11.0273 | 8.973 | -2.0543 | -13.9647 | -15.0697 | -1.105 |
| 2025-07 | drawdown_regression | -0.0003 | -0.2421 | -0.2418 | -8.5832 | -11.3502 | -2.767 |
| 2025-08 | drawdown_regression | -4.1112 | -4.0937 | 0.0175 | -9.3224 | -12.0628 | -2.7404 |
| 2025-09 | drawdown_regression | 3.5835 | 3.5865 | 0.003 | -9.6584 | -12.3895 | -2.7311 |
| 2025-10 | drawdown_regression | 14.5023 | 14.5041 | 0.0018 | -7.2251 | -10.0258 | -2.8007 |
| 2025-11 | drawdown_regression | -0.0023 | -0.0023 | 0 | -8.8303 | -8.8308 | -0.0005 |
| 2025-12 | drawdown_regression | 2.6571 | 2.6572 | 0.0001 | -7.4808 | -7.4812 | -0.0004 |
| 2026-01 | drawdown_regression | 32.2628 | 32.2645 | 0.0017 | -2.3714 | -2.3715 | -0.0001 |
| 2026-02 | drawdown_regression | 16.0329 | 16.0335 | 0.0006 | -7.6163 | -7.6166 | -0.0003 |
| 2026-03 | drawdown_regression | -20.9029 | -20.9036 | -0.0007 | -21.7887 | -21.7895 | -0.0008 |
| 2026-04 | drawdown_regression | 19.8262 | 19.8271 | 0.0009 | -19.6689 | -19.6696 | -0.0007 |
| 2026-05 | drawdown_improved | -2.7779 | -2.7737 | 0.0042 | -14.0699 | -14.0403 | 0.0296 |
| 2026-06 | drawdown_improved | -8.8466 | -8.8346 | 0.012 | -21.1177 | -21.1033 | 0.0144 |

### stress_slippage_x3

| month | diagnostic | base_ret | cand_ret | ret_delta | base_worst_dd | cand_worst_dd | dd_delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-11 | drawdown_improved | -2.0343 | -1.4269 | 0.6074 | -10.8144 | -10.2295 | 0.5849 |
| 2024-12 | drawdown_improved | -3.0187 | -1.7915 | 1.2272 | -15.3507 | -11.8763 | 3.4744 |
| 2025-01 | drawdown_improved | 1.6315 | 1.7514 | 0.1199 | -12.4001 | -10.5986 | 1.8015 |
| 2025-02 | drawdown_improved | 3.2385 | 3.6987 | 0.4602 | -12.4634 | -12.0815 | 0.3819 |
| 2025-03 | drawdown_regression | -9.0285 | -9.8857 | -0.8572 | -19.6864 | -20.7729 | -1.0865 |
| 2025-04 | new_drawdown_breach | 1.5526 | 1.6683 | 0.1157 | -24.0105 | -25.0493 | -1.0388 |
| 2025-05 | drawdown_regression | 4.4639 | 4.5325 | 0.0686 | -18.8548 | -19.928 | -1.0732 |
| 2025-06 | drawdown_regression | 11.0143 | 8.9504 | -2.0639 | -13.9871 | -15.2107 | -1.2236 |
| 2025-07 | drawdown_regression | -0.055 | -0.2882 | -0.2332 | -8.6363 | -11.5963 | -2.96 |
| 2025-08 | drawdown_regression | -4.2022 | -4.1748 | 0.0274 | -9.4389 | -12.3472 | -2.9083 |
| 2025-09 | drawdown_regression | 3.5225 | 3.544 | 0.0215 | -9.8522 | -12.7458 | -2.8936 |
| 2025-10 | drawdown_regression | 14.4979 | 14.5709 | 0.073 | -7.5041 | -10.4577 | -2.9536 |
| 2025-11 | drawdown_regression | 0.0843 | 0.0853 | 0.001 | -8.2699 | -8.2958 | -0.0259 |
| 2025-12 | drawdown_improved | 1.7178 | 1.7369 | 0.0191 | -7.4296 | -7.429 | 0.0006 |
| 2026-01 | drawdown_regression | 32.0085 | 32.1002 | 0.0917 | -2.3792 | -2.3853 | -0.0061 |
| 2026-02 | drawdown_regression | 15.1964 | 15.2325 | 0.0361 | -7.6751 | -7.6929 | -0.0178 |
| 2026-03 | drawdown_improved | -21.1238 | -21.0999 | 0.0239 | -22.0576 | -22.0441 | 0.0135 |
| 2026-04 | drawdown_improved | 19.7485 | 19.7719 | 0.0234 | -19.946 | -19.9285 | 0.0175 |
| 2026-05 | drawdown_improved | -4.1497 | -3.7969 | 0.3528 | -15.0726 | -14.657 | 0.4156 |
| 2026-06 | drawdown_improved | -8.1768 | -8.1585 | 0.0183 | -21.3252 | -20.9722 | 0.353 |


## Current Git State

### Recent Commits

```text
af015ea Add monthly attribution comparison
e445aeb Test neutral breadth proxy cap
60ea514 Add proxy decision diagnostics
0478887 Test proxy exposure cap candidate
1da5f1b Add recovery attribution summaries
dcdda11 Add train stability window diagnostics
fc51fb3 Add train decision path diagnostics
bb7d015 Add direct alpha holding path diagnostics
958249b Add direct alpha selection diagnostics
8cd4dcc Add direct alpha train diagnostics
```

### Working Tree Status

```text
M README.md
 M backtester/auto_scalper.py
 M backtester/config.py
 M backtester/engine.py
 M backtester/events.py
 M backtester/flow.py
 M backtester/leader_swing.py
 M backtester/news.py
 M backtester/pykrx_fetcher.py
 M backtester/scalper.py
 M backtester/strategies.py
 M tests/test_auto_scalper.py
 M tests/test_config.py
 M tests/test_engine.py
 M tests/test_events.py
 M tests/test_flow.py
 M tests/test_leader_swing.py
 M tests/test_news.py
 M tests/test_pykrx_fetcher.py
 M tests/test_scalper.py
?? AGENTS.md
?? backtester/data_quality.py
?? backtester/execution_plan.py
?? backtester/health.py
?? backtester/portfolio.py
?? backtester/risk.py
?? docs/GPT_PROJECT_SNAPSHOT_FULL.md
?? docs/cloud-always-on-operation-plan.md
?? docs/event-data-integration.md
?? docs/project-overview.md
?? docs/safe-research-operation.md
?? docs/strategy-comparison-review.md
?? scripts/cloud/run_health_check.sh
?? scripts/cloud/run_monthly_plan.sh
?? scripts/cloud/toss-monthly-plan.service
?? scripts/cloud/toss-monthly-plan.timer
?? scripts/download_cloud_reports.ps1
?? scripts/register_cloud_reports_download_task.ps1
?? tests/test_cloud_scripts.py
?? tests/test_data_quality.py
?? tests/test_execution_plan.py
?? tests/test_health.py
?? tests/test_portfolio.py
?? tests/test_risk.py
```

### Diff Stat For Modified Tracked Files

```text
README.md                   |   7 ++
 backtester/auto_scalper.py  |  21 +++-
 backtester/config.py        |   8 ++
 backtester/engine.py        |  34 +++++-
 backtester/events.py        | 132 +++++++++++++++++++--
 backtester/flow.py          |  12 ++
 backtester/leader_swing.py  | 187 ++++++++++++++++++++----------
 backtester/news.py          |  82 +++++++++++++
 backtester/pykrx_fetcher.py | 276 +++++++++++++++++++++++++++++++++++++++++++-
 backtester/scalper.py       |  16 ++-
 backtester/strategies.py    |   9 +-
 tests/test_auto_scalper.py  |  11 ++
 tests/test_config.py        |  14 ++-
 tests/test_engine.py        |  22 ++++
 tests/test_events.py        | 101 +++++++++++++++-
 tests/test_flow.py          |  19 ++-
 tests/test_leader_swing.py  | 197 ++++++++++++++++++++++++++++++-
 tests/test_news.py          |  47 +++++++-
 tests/test_pykrx_fetcher.py | 149 ++++++++++++++++++++++++
 tests/test_scalper.py       |  75 +++++++++++-
 20 files changed, 1327 insertions(+), 92 deletions(-)
```

## Repository Map

Core package:

- `backtester/__main__.py`: CLI entry point.
- `backtester/monthly_rebalance.py`: monthly paper plan, validation, deployment gate, attribution, failure diagnostics, sweep planning.
- `backtester/readiness.py`: production readiness checks.
- `backtester/health.py`: health-check report generation.
- `backtester/risk.py`: risk guards.
- `backtester/execution_plan.py`: paper execution plans.
- `backtester/portfolio.py`: portfolio state helpers.
- `backtester/pykrx_fetcher.py`: KRX/pykrx data utilities.
- `backtester/toss.py`: Toss API adapter; do not call from tests.
- `backtester/scalper.py`, `backtester/auto_scalper.py`: paper scalper and collector logic.
- `backtester/strategies.py`, `momentum_rotation.py`, `momentum_validation.py`: strategy and validation helpers.
- `backtester/leader_swing.py`, `leader_regime_switch.py`, `leader_window_study.py`: swing/leader research.
- `backtester/events.py`, `news.py`, `flow.py`, `dart.py`: event/news/flow/DART scoring inputs.
- `backtester/data_quality.py`: data-quality screening.

Tests use standard-library `unittest` and live under `tests/`. Current full suite passes with 411 tests.

Docs and operations:

- `docs/GOAL_MODE_CHECKPOINT.md`: read this first when resuming goal-mode work.
- `docs/GPT_PROJECT_CONTEXT.md`: compact handoff.
- `docs/GPT_PROJECT_SNAPSHOT_FULL.md`: full source-inclusive GPT snapshot.
- `scripts/cloud/*`: cloud paper-operation helpers and systemd units.

Source-like files included in the full snapshot: 99.

## Core Commands

```powershell
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester production-check --allow-blocked-exit-zero
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

## Current Production Readiness Report

# Production Readiness Report

Overall status: BLOCK

| Check | Status | Detail |
| --- | --- | --- |
| artifact:krx_universe_monthly.csv | PASS | present: data\krx_metadata\krx_universe_monthly.csv |
| artifact:monthly_validation_scenarios_pit_universe.csv | PASS | present: data\reports\monthly_validation_scenarios_pit_universe.csv |
| artifact:monthly_deployment_gate_pit_universe.csv | PASS | present: data\reports\monthly_deployment_gate_pit_universe.csv |
| artifact:monthly_risk_report.csv | PASS | present: data\reports\monthly_risk_report.csv |
| artifact:monthly_universe_price_coverage.csv | PASS | present: data\reports\monthly_universe_price_coverage.csv |
| artifact:monthly_performance_audit.csv | PASS | present: data\reports\monthly_performance_audit.csv |
| deployment_gate | BLOCK | monthly-validate:2024-01-01..2026-06-18;data_quality_exclusions=auto:data\reports\data_quality_excluded_symbols.csv;excluded_symbols=355:failed_required_scenarios:stress_exclude_500pct_winners,regime_sideways,walk_forward_001,walk_forward_003,walk_forward_005 |
| validation_scenarios | BLOCK | 5 failed: stress_exclude_500pct_winners,regime_sideways,walk_forward_001,walk_forward_003,walk_forward_005; reasons: max_drawdown_breach=1, negative_excess_return=3, train_window_rejected=1 |
| walk_forward_train_candidate_coverage | WARN | under_covered=5; low_diversity=0; fallback_only=5; direct_alpha_ineligible=5; min_candidates=1; min_unique_scores=1; walk_forward_001:1/1, walk_forward_002:1/1, walk_forward_003:1/1, walk_forward_004:1/1, walk_forward_005:1/1 |
| validation_failure_actions | BLOCK | 5 failures; actions: IMPROVE_WEAK_WINDOW_DEFENSE=3, KEEP_TRAIN_WINDOW_REJECTED=1, REDUCE_DRAWDOWN=1; samples: IMPROVE_WEAK_WINDOW_DEFENSE->regime_sideways:negative_excess_return excess_return_pct=-7.1648; hints=increase cash_buffer_weight in weak regimes; tighten min_train_positive_ratio; test lower candidate_pool_size and stronger market_beta/cash fallback \| KEEP_TRAIN_WINDOW_REJECTED->walk_forward_003:train_window_rejected train_excess_return_pct=-1.3447; hints=Do not override rejected train windows; inspect preset stability and require robust train windows. \| REDUCE_DRAWDOWN->stress_exclude_500pct_winners:max_drawdown_breach max_drawdown_pct=-28.0835; hints=lower max_position_weight; increase cash_buffer_weight; strengthen drawdown_guard_scale; test higher market_volatility_min_scale and stricter risk-off fallback |
| validation_remediation | BLOCK | 3 experiment groups; priorities: P1=3; top_action=IMPROVE_WEAK_WINDOW_DEFENSE; affected=regime_sideways; walk_forward_001; walk_forward_005; next=Run a parameter sweep with higher cash_buffer_weight, stricter min_train_positive_ratio, and lower candidate_pool_size on only failed weak windows. |
| validation_sweep_plan | WARN | 11 planned experiments; actions: COMBINE_WEAK_DEFENSE_AND_DRAWDOWN=1, IMPROVE_WEAK_WINDOW_DEFENSE=5, KEEP_TRAIN_WINDOW_REJECTED=1, REDUCE_DRAWDOWN=4; first=weak_defense_cash_05; targets=regime_sideways; walk_forward_001; walk_forward_005; risk_note=Plan only; run monthly validation before adopting any parameter change. |
| validation_sweep_results | WARN | 9 sweep results; statuses: IMPROVED=3, UNCHANGED=6; adoption_statuses: FULL_VALIDATION_REQUIRED=3, PAPER_DIAGNOSTIC_ONLY=6; best=weak_cash_10_position_stop_12; delta=-2; summary=failed_required 4 -> 2; experiment=weak_cash_10_position_stop_12; risk_note=Plan only; run monthly validation before adopting any parameter change.; candidate_validation_args=--cash-buffer-weight 0.1 --min-train-positive-ratio 0.6 --candidate-pool-size 5 --position-trailing-stop-pct -12; improved=weak_defense_cash_10, position_stop_12, weak_cash_10_position_stop_12; target_only_improvements_require_full_validation |
| validation_comparison | WARN | neutral_breadth_proxy_cap_50:REJECT; failed_delta=1; new_failures=full_period; stress_slippage_x3; resolved_failures=walk_forward_003; summary=failed_required 5 -> 6; resolved=1; new failures=2; unchanged=4 |
| validation_comparison_deltas | WARN | 18 scenario deltas; classes: NEW_FAILURE=2, RESOLVED=1, UNCHANGED_FAILURE=4, UNCHANGED_PASS=11; diagnostics: candidate_fixed_required_failure=1, candidate_introduced_failure=2, same_failure_persists=4; new_failures=full_period; stress_slippage_x3 |
| validation_candidate_decision | WARN | neutral_breadth_proxy_cap_50:REJECT; comparison_status=REJECT; failed_delta=1; new_failures=2; resolved=1; new_failure_names=full_period; stress_slippage_x3; resolved_failure_names=walk_forward_003; unchanged_failure_names=regime_sideways; stress_exclude_500pct_winners; walk_forward_001; walk_forward_005; diagnostics=candidate_introduced_failure=2; reasons=comparison_rejected; new_failures=2; failed_delta=1; unchanged_failures=4; recommendation=Do not adopt this candidate; inspect new failure diagnostics and run narrower paper-only experiments. |
| validation_candidate_followup | WARN | 3 candidate follow-up command sets; top=weak_cash_10_position_stop_12; failed_delta=-2; decisions: REJECT=3; top_decision=REJECT; candidate_failed_required=6; new_failures=regime_bear; walk_forward_002; walk_forward_004; completed=3; pending=0; all_candidate_followups_completed |
| validation_failure_patterns | BLOCK | 10 scenarios; statuses: MIXED_RESPONSE=3, PERSISTENT_BLOCK=2, REGRESSION_RISK=5; top=regime_sideways:PERSISTENT_BLOCK:REVIEW_PERSISTENT_FAILURE; walk_forward_005:PERSISTENT_BLOCK:REVIEW_PERSISTENT_FAILURE; walk_forward_002:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS; walk_forward_004:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS; regime_bear:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS |
| validation_failure_drilldown | PASS | 10 scenarios; root_causes: direct_alpha_ineligible=2, drawdown_pressure=1, insufficient_recovery=2, over_defense_or_filter_drag=1, scenario_review=1, selection_or_exposure_regression=3; evidence_gaps=0; top=regime_sideways:insufficient_recovery:; walk_forward_005:insufficient_recovery:; full_period:selection_or_exposure_regression:; regime_bear:selection_or_exposure_regression:; stress_slippage_x3:selection_or_exposure_regression: |
| risk_report | BLOCK | deployment_gate:monthly-validate:2024-01-01..2026-06-18;data_quality_exclusions=auto:data\reports\data_quality_excluded_symbols.csv;excluded_symbols=355:failed_required_scenarios:stress_exclude_500pct_winners,regime_sideways,walk_forward_001,walk_forward_003,walk_forward_005; performance_guard:required_scenarios:5 failed of 18 required; required_excess:min_required_excess_pct=-7.1648; walk_forward_margin:min_walk_forward_excess_pct=-5.5812; warn_below=5.0000; drawdown_buffer:worst_max_drawdown_pct=-28.0835; warn_at_or_below=-20.0000; block_below=-25.0000; target_scale=0.0000 |
| universe_price_coverage | PASS | 30 snapshots covered; min_coverage_pct=91.8 |
| krx_missing_ohlcv_targets | PASS | targets=263; top=008110:26; 036180:26; 126730:26; 140430:26; 145170:26; first_missing_date=2024-01-31; last_missing_date=2026-06-18; next=python -m backtester fetch-pykrx-missing-ohlcv-loop --universe-file data/krx_metadata/krx_universe_monthly.csv --start 2024-01-01 --end YYYY-MM-DD --targets-output data\reports\krx_missing_ohlcv_targets.csv |
| krx_missing_ohlcv_fetch_plan | PASS | status=READY; target_count=263; planned_batches=1; planned_symbols=50; remaining_after_plan=213; batch_timeout_seconds=300.0; batch_pause_seconds=10.0; top=008110:26; 036180:26; 126730:26; 140430:26; 145170:26; command=python -m backtester fetch-pykrx-missing-ohlcv-loop --universe-file "data/krx_metadata/krx_universe_monthly.csv" --start 2024-01-01 --end 2026-06-18 --data-dir "data/krx_expanded" --targets-output "data/reports/krx_missing_ohlcv_targets.csv" --report-dir "data/reports" --batch-size 50 --max-batches 1 --batch-timeout-seconds 300 --batch-pause-seconds 10 |
| krx_missing_ohlcv_fetch_summary | WARN | status=not_started; attempted_batches=0; completed_batches=0; timed_out_batches=0; failed_batches=0; saved=0; remaining_targets=397; stderr_tail=fetch loop has not been executed |
| performance_report | BLOCK | required_scenarios:5 failed of 18 required; required_excess:min_required_excess_pct=-7.1648; walk_forward_margin:min_walk_forward_excess_pct=-5.5812; warn_below=5.0000; drawdown_buffer:worst_max_drawdown_pct=-28.0835; warn_at_or_below=-20.0000; block_below=-25.0000 |
| performance_concentration | PASS | monthly-validate:2024-01-01..2026-06-18;data_quality_exclusions=auto:data\reports\data_quality_excluded_symbols.csv;excluded_symbols=355:no reasons; top_1_month=0.254747; top_5_symbol=0.435459 |
| drawdown_attribution | PASS | monthly_rows=30; symbol_rows=73; worst_month=2026-03 equity_change=-3655376.7348; worst_drawdown_month=2026-06 worst_drawdown_pct=-28.0835; worst_symbol=051910 realized_pnl=-538464.75 |
| data_quality_exclusions | PASS | applied in deployment_gate,validation_scenarios,risk_report; exclusions=data\reports\data_quality_excluded_symbols.csv |
| deployment_gate_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_scenarios_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_failures_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_remediation_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_sweep_plan_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_sweep_results_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_comparison_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_comparison_deltas_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| validation_candidate_decision_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| risk_report_freshness | PASS | age 1d within 45d; modified=2026-06-21 |
| universe_price_coverage_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| krx_missing_ohlcv_targets_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| krx_missing_ohlcv_fetch_plan_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| krx_missing_ohlcv_fetch_summary_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| performance_report_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| performance_concentration_freshness | PASS | age 0d within 45d; modified=2026-06-22 |
| drawdown_attribution_freshness | PASS | age 1d within 45d; modified=2026-06-21 |
| symbol_attribution_freshness | PASS | age 1d within 45d; modified=2026-06-21 |

## Required Next Actions

| Priority | Action | Detail |
| --- | --- | --- |
| P0 | Keep live executor disabled | The monthly deployment gate is not deployable; paper review and data collection only. |
| P1 | Inspect KRX missing OHLCV fetch result | Review failed or timed-out collection batches before rerunning validation. |
| P1 | Reduce stress drawdown | Tune exposure caps, stop rules, or risk-off overlays until required stress scenarios pass. |
| P0 | Keep risk report as an order hard stop | A blocked risk report should prevent order generation even if signals look attractive. |
| P1 | Improve walk-forward margin | Raise the weakest required-window excess return before increasing size; test stricter entry filters, slower rebalance cadence, or lower exposure in marginal regimes. |
| P1 | Reduce drawdown pressure | Worst drawdown is too close to the hard block threshold; test stronger risk-off overlays, lower max position weight, and faster de-risking after equity-curve drawdowns. |
| P1 | Treat performance fragility as a live-size limiter | Thin walk-forward margins, high drawdown pressure, or full-period concentration should keep trading in paper/live dry-run or very small sizing until they improve. |
| P1 | Diagnose walk-forward train alpha weakness | under_covered=5; low_diversity=0; fallback_only=5; direct_alpha_ineligible=5; min_candidates=1; min_unique_scores=1; walk_forward_001:1/1, walk_forward_002:1/1, walk_forward_003:1/1, walk_forward_004:1/1, walk_forward_005:1/1 |
| P1 | Apply validation failure playbook | 5 failures; actions: IMPROVE_WEAK_WINDOW_DEFENSE=3, KEEP_TRAIN_WINDOW_REJECTED=1, REDUCE_DRAWDOWN=1; samples: IMPROVE_WEAK_WINDOW_DEFENSE->regime_sideways:negative_excess_return excess_return_pct=-7.1648; hints=increase cash_buffer_weight in weak regimes; tighten min_train_positive_ratio; test lower candidate_pool_size and stronger market_beta/cash fallback \| KEEP_TRAIN_WINDOW_REJECTED->walk_forward_003:train_window_rejected train_excess_return_pct=-1.3447; hints=Do not override rejected train windows; inspect preset stability and require robust train windows. \| REDUCE_DRAWDOWN->stress_exclude_500pct_winners:max_drawdown_breach max_drawdown_pct=-28.0835; hints=lower max_position_weight; increase cash_buffer_weight; strengthen drawdown_guard_scale; test higher market_volatility_min_scale and stricter risk-off fallback |
| P1 | Run validation remediation experiments | 3 experiment groups; priorities: P1=3; top_action=IMPROVE_WEAK_WINDOW_DEFENSE; affected=regime_sideways; walk_forward_001; walk_forward_005; next=Run a parameter sweep with higher cash_buffer_weight, stricter min_train_positive_ratio, and lower candidate_pool_size on only failed weak windows. |
| P2 | Review validation sweep plan | 11 planned experiments; actions: COMBINE_WEAK_DEFENSE_AND_DRAWDOWN=1, IMPROVE_WEAK_WINDOW_DEFENSE=5, KEEP_TRAIN_WINDOW_REJECTED=1, REDUCE_DRAWDOWN=4; first=weak_defense_cash_05; targets=regime_sideways; walk_forward_001; walk_forward_005; risk_note=Plan only; run monthly validation before adopting any parameter change. |
| P1 | Review validation sweep results | 9 sweep results; statuses: IMPROVED=3, UNCHANGED=6; adoption_statuses: FULL_VALIDATION_REQUIRED=3, PAPER_DIAGNOSTIC_ONLY=6; best=weak_cash_10_position_stop_12; delta=-2; summary=failed_required 4 -> 2; experiment=weak_cash_10_position_stop_12; risk_note=Plan only; run monthly validation before adopting any parameter change.; candidate_validation_args=--cash-buffer-weight 0.1 --min-train-positive-ratio 0.6 --candidate-pool-size 5 --position-trailing-stop-pct -12; improved=weak_defense_cash_10, position_stop_12, weak_cash_10_position_stop_12; target_only_improvements_require_full_validation |
| P1 | Do not adopt rejected validation candidate | neutral_breadth_proxy_cap_50:REJECT; failed_delta=1; new_failures=full_period; stress_slippage_x3; resolved_failures=walk_forward_003; summary=failed_required 5 -> 6; resolved=1; new failures=2; unchanged=4 |
| P1 | Review validation scenario deltas | 18 scenario deltas; classes: NEW_FAILURE=2, RESOLVED=1, UNCHANGED_FAILURE=4, UNCHANGED_PASS=11; diagnostics: candidate_fixed_required_failure=1, candidate_introduced_failure=2, same_failure_persists=4; new_failures=full_period; stress_slippage_x3 |
| P1 | Do not adopt rejected validation candidate | neutral_breadth_proxy_cap_50:REJECT; comparison_status=REJECT; failed_delta=1; new_failures=2; resolved=1; new_failure_names=full_period; stress_slippage_x3; resolved_failure_names=walk_forward_003; unchanged_failure_names=regime_sideways; stress_exclude_500pct_winners; walk_forward_001; walk_forward_005; diagnostics=candidate_introduced_failure=2; reasons=comparison_rejected; new_failures=2; failed_delta=1; unchanged_failures=4; recommendation=Do not adopt this candidate; inspect new failure diagnostics and run narrower paper-only experiments. |
| P1 | Run candidate follow-up validation | 3 candidate follow-up command sets; top=weak_cash_10_position_stop_12; failed_delta=-2; decisions: REJECT=3; top_decision=REJECT; candidate_failed_required=6; new_failures=regime_bear; walk_forward_002; walk_forward_004; completed=3; pending=0; all_candidate_followups_completed |
| P1 | Analyze persistent validation failures | 10 scenarios; statuses: MIXED_RESPONSE=3, PERSISTENT_BLOCK=2, REGRESSION_RISK=5; top=regime_sideways:PERSISTENT_BLOCK:REVIEW_PERSISTENT_FAILURE; walk_forward_005:PERSISTENT_BLOCK:REVIEW_PERSISTENT_FAILURE; walk_forward_002:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS; walk_forward_004:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS; regime_bear:REGRESSION_RISK:AVOID_REGRESSION_CONFIGS |


## Current Health Report

# Health Status

Overall status: WARN
Generated at: 2026-06-22T09:28:37.897938+00:00

| Check | Status | Detail | Modified At | Age Hours | Suggested Action |
| --- | --- | --- | --- | --- | --- |
| monthly_order_plan | PASS | fresh report; schema_ok columns=20 | 2026-06-21T12:25:04.526844+00:00 | 21.06 | No action required. |
| production_readiness | PASS | fresh report; schema_ok columns=3 | 2026-06-22T09:28:32.119679+00:00 | 0.00 | No action required. |
| data_quality_excluded_symbols | PASS | fresh report; schema_ok columns=3 | 2026-06-21T10:11:03.138032+00:00 | 23.29 | No action required. |
| monthly_universe_price_coverage | PASS | fresh report; schema_ok columns=10 | 2026-06-22T08:55:09.826289+00:00 | 0.56 | No action required. |
| krx_missing_ohlcv_fetch_summary | PASS | fresh report; schema_ok columns=10 | 2026-06-21T15:10:07.860080+00:00 | 18.31 | No action required. |
| monthly_universe_price_coverage_inputs | PASS | derived report inputs are not newer than report | 2026-06-22T08:55:09.826289+00:00 |  | No action required. |
| scalper_data | WARN | old scalper data: latest=005930_paper_scalp.csv; age_hours=305.64; mode=warn | 2026-06-09T15:50:00.159130+00:00 | 305.64 | Restart or inspect the cloud scalper collector; latest file is stale. |
| logs | PASS | no logs directory: logs |  |  | No action required. |


## Current Goal Checkpoint

# Goal Mode Checkpoint

Last updated: 2026-06-22 18:35 KST

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

- `python -m unittest discover -s tests`: PASS, 411 tests.
- `python -m compileall -q backtester`: PASS.
- `production-check`: BLOCK by design, because 5 required validation scenarios still fail.
- `health-check`: WARN, only because scalper data is stale.
- Candidate follow-up state: all completed full-validation candidates remain rejected; latest `neutral_breadth_proxy_cap_50` is also rejected.
- Failure-pattern and failure-drilldown reports are generated and integrated into `production-check`.
- `validation_failure_drilldown`: PASS. Evidence gaps are now closed.

## Latest Loop Results

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


## Recommended Next Task

Do not adopt `neutral_breadth_proxy_cap_50`. The next diagnostic should compare baseline vs candidate decision/exposure/symbol differences around the March-April 2025 drawdown regression, then test a narrower paper-only guard only if evidence supports it. The live-order path must remain disabled.
