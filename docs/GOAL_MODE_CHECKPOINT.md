# Goal Mode Checkpoint

Last updated: 2026-06-22 02:22 KST

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

- `python -m unittest discover -s tests`: PASS, 368 tests.
- `python -m compileall -q backtester`: PASS.
- `production-check`: BLOCK by design, because validation still fails required scenarios.
- `health-check`: WARN, only because scalper data is stale.
- Candidate follow-up state: all 3 full-validation candidates completed, all rejected.
- Failure-pattern and failure-drilldown reports are generated and integrated into `production-check`.

## Latest Loop Results

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
- `train_window_selection=2`
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
- Evidence gaps remain for six scenarios:
  - selected symbols
  - exposure
  - cash weight
  - symbol PnL attribution
  - train-window candidate scores where applicable

## Current BLOCK/WARN Summary

Production readiness:

- Status counts: `BLOCK=8`, `PASS=29`, `WARN=9`
- Main BLOCK: required monthly validation failures remain.
- `validation_failure_patterns`: BLOCK
  - `CANDIDATE_FIXED=2`
  - `PERSISTENT_BLOCK=3`
  - `REGRESSION_RISK=3`
- `validation_failure_drilldown`: WARN
  - root causes: `insufficient_recovery=2`, `train_window_selection=2`, `selection_or_exposure_regression=1`, `over_defense_or_filter_drag=1`, `drawdown_pressure=1`, `candidate_fixed_failure=1`
  - evidence gaps: 6 scenarios
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
- Reason: latest scalper file is stale, age about 289 hours.
- Action: inspect or restart cloud scalper collector if tick/paper scalper data is still needed.

## Latest Code/Report Changes

Touched in latest loop:

- `backtester/monthly_rebalance.py`
- `backtester/readiness.py`
- `backtester/__main__.py`
- `tests/test_monthly_rebalance.py`
- `tests/test_readiness.py`
- `tests/test_cli.py`
- `data/reports/monthly_validation_failure_drilldown.csv`
- `data/reports/monthly_validation_failure_patterns.csv`
- `data/reports/production_readiness.csv`
- `data/reports/production_readiness_report.md`
- `data/reports/health_status.json`
- `data/reports/health_status.md`
- `docs/GOAL_MODE_CHECKPOINT.md`

## Commands Run In Latest Loop

```powershell
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_patterns_flags_persistent_and_regression tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_patterns_writes_csv tests.test_readiness.ProductionReadinessTests.test_validation_failure_patterns_block_persistent_failures tests.test_cli.CliTests.test_monthly_failure_patterns_cli_writes_report
python -m backtester monthly-failure-patterns --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --output data/reports/monthly_validation_failure_patterns.csv
python -m unittest tests.test_monthly_rebalance.MonthlyRebalanceTests.test_analyze_monthly_validation_failure_drilldown_summarizes_root_cause_and_gaps tests.test_monthly_rebalance.MonthlyRebalanceTests.test_save_monthly_validation_failure_drilldown_writes_csv tests.test_cli.CliTests.test_monthly_failure_drilldown_cli_writes_report tests.test_readiness.ProductionReadinessTests.test_validation_failure_drilldown_warns_on_missing_attribution_evidence
python -m backtester monthly-failure-drilldown --baseline data/reports/monthly_validation_scenarios_pit_universe.csv --patterns data/reports/monthly_validation_failure_patterns.csv --output data/reports/monthly_validation_failure_drilldown.csv
python -m backtester production-check --allow-blocked-exit-zero
python -m unittest discover -s tests
python -m compileall -q backtester
python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero
```

## Next Highest-Value Work

1. Fill the drilldown evidence gaps before another parameter sweep:
   - selected symbols per failed scenario
   - realized symbol PnL attribution per failed scenario
   - average exposure/cash weight per failed scenario
   - train-window candidate scores for train-window failures
2. Build a narrower diagnostic experiment around `PERSISTENT_BLOCK` scenarios only:
   - `regime_sideways`
   - `walk_forward_003`
   - `walk_forward_005`
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
