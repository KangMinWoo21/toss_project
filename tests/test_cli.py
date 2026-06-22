import subprocess
import sys
import unittest
import os
import csv
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def _run_backtester_in_cwd(self, cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else str(ROOT) + os.pathsep + existing_pythonpath
        return subprocess.run(
            [sys.executable, "-m", "backtester", *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(cwd),
            env=env,
        )

    def _write_monthly_price_files(self, data_dir: Path, symbols: list[str]) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        for index, symbol in enumerate(symbols, start=1):
            base = 100 + index
            (data_dir / f"{symbol}.csv").write_text(
                "date,open,high,low,close,volume\n"
                f"2024-01-02,{base},{base + 1},{base - 1},{base},1000\n"
                f"2024-02-01,{base},{base + 1},{base - 1},{base},1000\n"
                f"2024-03-01,{base},{base + 1},{base - 1},{base},1000\n",
                encoding="utf-8",
            )

    def test_compare_command_prints_strategy_table(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "compare",
                "--data",
                "data/sample_kr_stock.csv",
                "--initial-cash",
                "1000000",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("strategy", completed.stdout)
        self.assertIn("buy_and_hold", completed.stdout)
        self.assertIn("volatility_breakout", completed.stdout)

    def test_walk_forward_command_prints_period_and_summary_tables(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "walk-forward",
                "--data",
                "data/sample_kr_stock.csv",
                "--initial-cash",
                "1000000",
                "--window",
                "2026-01-02:2026-01-08:2026-01-09:2026-01-12",
                "--window",
                "2026-01-06:2026-01-12:2026-01-13:2026-01-16",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("best_strategy", completed.stdout)
        self.assertIn("avg_test_%", completed.stdout)

    def test_compare_command_can_use_news_filter(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "compare",
                "--data",
                "data/sample_kr_stock.csv",
                "--news-filter",
                "--events",
                "data/sample_events.csv",
                "--symbol",
                "005930",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("news_filtered", completed.stdout)

    def test_compare_command_can_use_flow_filter(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "compare",
                "--data",
                "data/sample_kr_stock.csv",
                "--flow-filter",
                "--flows",
                "data/sample_flows.csv",
                "--symbol",
                "005930",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("flow_filtered", completed.stdout)

    def test_fetch_dart_events_requires_api_key(self):
        env = os.environ.copy()
        env["DART_API_KEY"] = ""
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "fetch-dart-events",
                "--symbol",
                "005930",
                "--start",
                "2026-01-01",
                "--end",
                "2026-01-31",
                "--output",
                "data/dart_events.csv",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("DART_API_KEY", completed.stderr)

    def test_import_social_events_command_writes_event_csv(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            social = root / "social.csv"
            output = root / "events.csv"
            social.write_text(
                "date,platform,text,likes\n"
                "2026-06-09,x,Samsung shares surge on AI demand,100\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "import-social-events",
                    "--input",
                    str(social),
                    "--output",
                    str(output),
                    "--symbol",
                    "005930",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("saved 1 social events", completed.stdout)
            self.assertIn("sns:x", output.read_text(encoding="utf-8"))

    def test_merge_events_command_combines_weightable_sources(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            news = root / "news.csv"
            sns = root / "sns.csv"
            output = root / "combined.csv"
            news.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-06-09,005930,google-news:Example,strong outlook,0.8,1.0\n",
                encoding="utf-8",
            )
            sns.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-06-09,005930,sns:x,noisy post,-0.5,1.0\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "merge-events",
                    "--input",
                    str(news),
                    "--input",
                    str(sns),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("merged 2 events", completed.stdout)
            self.assertIn("google-news:Example", output.read_text(encoding="utf-8"))
            self.assertIn("sns:x", output.read_text(encoding="utf-8"))

    def test_data_check_command_reports_block_for_stale_dataset(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "data-check",
                    "--path",
                    str(root),
                    "--as-of",
                    "2026-06-21",
                    "--max-stale-days",
                    "7",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("data_quality_status  BLOCK", completed.stdout)
        self.assertIn("stale_days", completed.stdout)

    def test_data_check_command_writes_exclude_output(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "excluded.csv"
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            (root / "000660.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,200,202,198,201,1000\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "data-check",
                    "--path",
                    str(root),
                    "--as-of",
                    "2026-06-21",
                    "--max-stale-days",
                    "7",
                    "--exclude-output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8-sig") if output.exists() else ""

        self.assertEqual(completed.returncode, 2)
        self.assertIn("exclude_output", completed.stdout)
        self.assertIn("005930,BLOCK", text)
        self.assertNotIn("000660", text)

    def test_data_check_command_writes_diagnose_output_without_breaking_exclude_output(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diagnose_output = root / "diagnostics.csv"
            exclude_output = root / "excluded.csv"
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,90,95,105,1000\n",
                encoding="utf-8",
            )
            (root / "000660.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,200,202,198,201,1000\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "data-check",
                    "--path",
                    str(root),
                    "--as-of",
                    "2026-06-21",
                    "--max-stale-days",
                    "7",
                    "--diagnose-output",
                    str(diagnose_output),
                    "--exclude-output",
                    str(exclude_output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            diagnose_text = diagnose_output.read_text(encoding="utf-8-sig") if diagnose_output.exists() else ""
            exclude_text = exclude_output.read_text(encoding="utf-8-sig") if exclude_output.exists() else ""

        self.assertEqual(completed.returncode, 2)
        self.assertIn("diagnose_output", completed.stdout)
        self.assertIn("symbol,file_path,status,reason_code", diagnose_text)
        self.assertIn("005930", diagnose_text)
        self.assertIn("invalid_ohlc", diagnose_text)
        self.assertIn("005930,BLOCK", exclude_text)

    def test_health_check_prints_suggested_action_for_blocked_checks(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "data" / "reports"
            reports.mkdir(parents=True)
            (reports / "monthly_order_plan.csv").write_text(
                "as_of_date,symbol,action\n",
                encoding="utf-8",
            )
            (reports / "production_readiness.csv").write_text(
                "name,status,detail\n",
                encoding="utf-8",
            )
            (reports / "data_quality_excluded_symbols.csv").write_text(
                "symbol,status,reason\n",
                encoding="utf-8",
            )
            scalper = root / "data" / "scalper"
            scalper.mkdir(parents=True)
            (scalper / "AAPL_2026-06-21_paper_scalp.csv").write_text(
                "timestamp,symbol,last_price\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                ["health-check", "--allow-blocked-exit-zero"],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("health_status  BLOCK", completed.stdout)
        self.assertIn("schema_drift", completed.stdout)
        self.assertIn("action=Regenerate", completed.stdout)

    def test_monthly_backtest_can_exclude_symbols_from_data_quality_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "111111.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2024-01-02,100,101,99,100,1000\n"
                "2024-02-01,100,101,99,100,1000\n"
                "2024-03-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            (root / "222222.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2024-01-02,100,101,99,100,1000\n"
                "2024-02-01,100,101,99,100,1000\n"
                "2024-03-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            excluded = root / "excluded.csv"
            excluded.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-backtest",
                    "--data-dir",
                    str(root),
                    "--start",
                    "2024-01-02",
                    "--end",
                    "2024-03-01",
                    "--train-years",
                    "1",
                    "--min-rows-per-window",
                    "1",
                    "--exclude-symbols",
                    str(excluded),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("universe_symbols  1", completed.stdout)

    def test_monthly_backtest_auto_applies_default_data_quality_exclusions(self):
        with TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            data_dir = cwd / "prices"
            self._write_monthly_price_files(data_dir, ["111111", "222222"])
            default_exclusions = cwd / "data" / "reports" / "data_quality_excluded_symbols.csv"
            default_exclusions.parent.mkdir(parents=True, exist_ok=True)
            default_exclusions.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")

            completed = self._run_backtester_in_cwd(
                cwd,
                [
                    "monthly-backtest",
                    "--data-dir",
                    str(data_dir),
                    "--start",
                    "2024-01-02",
                    "--end",
                    "2024-03-01",
                    "--train-years",
                    "1",
                    "--min-rows-per-window",
                    "1",
                ],
            )
            gate = (cwd / "data" / "reports" / "monthly_deployment_gate.csv").read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("data_quality_exclusions  auto:", completed.stdout)
        self.assertIn("symbols=1", completed.stdout)
        self.assertIn("universe_symbols  1", completed.stdout)
        self.assertIn("data_quality_exclusions=auto:", gate)

    def test_monthly_backtest_explicit_exclude_symbols_wins_over_default(self):
        with TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            data_dir = cwd / "prices"
            self._write_monthly_price_files(data_dir, ["111111", "222222", "333333"])
            default_exclusions = cwd / "data" / "reports" / "data_quality_excluded_symbols.csv"
            default_exclusions.parent.mkdir(parents=True, exist_ok=True)
            default_exclusions.write_text("symbol,status,reason\n222222,BLOCK,default bad\n", encoding="utf-8")
            explicit_exclusions = cwd / "explicit.csv"
            explicit_exclusions.write_text("symbol,status,reason\n111111,BLOCK,explicit bad\n", encoding="utf-8")

            completed = self._run_backtester_in_cwd(
                cwd,
                [
                    "monthly-backtest",
                    "--data-dir",
                    str(data_dir),
                    "--start",
                    "2024-01-02",
                    "--end",
                    "2024-03-01",
                    "--train-years",
                    "1",
                    "--min-rows-per-window",
                    "1",
                    "--exclude-symbols",
                    str(explicit_exclusions),
                ],
            )
            gate = (cwd / "data" / "reports" / "monthly_deployment_gate.csv").read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("data_quality_exclusions  explicit:", completed.stdout)
        self.assertNotIn("data_quality_exclusions  auto:", completed.stdout)
        self.assertIn("universe_symbols  2", completed.stdout)
        self.assertIn("data_quality_exclusions=explicit:", gate)

    def test_monthly_backtest_ignore_data_quality_exclusions_preserves_universe(self):
        with TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            data_dir = cwd / "prices"
            self._write_monthly_price_files(data_dir, ["111111", "222222"])
            default_exclusions = cwd / "data" / "reports" / "data_quality_excluded_symbols.csv"
            default_exclusions.parent.mkdir(parents=True, exist_ok=True)
            default_exclusions.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")

            completed = self._run_backtester_in_cwd(
                cwd,
                [
                    "monthly-backtest",
                    "--data-dir",
                    str(data_dir),
                    "--start",
                    "2024-01-02",
                    "--end",
                    "2024-03-01",
                    "--train-years",
                    "1",
                    "--min-rows-per-window",
                    "1",
                    "--ignore-data-quality-exclusions",
                ],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("data_quality_exclusions  ignored", completed.stdout)
        self.assertIn("universe_symbols  2", completed.stdout)

    def test_monthly_backtest_missing_default_exclusions_warns_and_preserves_universe(self):
        with TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            data_dir = cwd / "prices"
            self._write_monthly_price_files(data_dir, ["111111", "222222"])

            completed = self._run_backtester_in_cwd(
                cwd,
                [
                    "monthly-backtest",
                    "--data-dir",
                    str(data_dir),
                    "--start",
                    "2024-01-02",
                    "--end",
                    "2024-03-01",
                    "--train-years",
                    "1",
                    "--min-rows-per-window",
                    "1",
                ],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("data_quality_exclusions  WARN default_missing:", completed.stdout)
        self.assertIn("universe_symbols  2", completed.stdout)

    def test_monthly_backtest_help_includes_deep_drawdown_guard_options(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "monthly-backtest",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--drawdown-guard-deep-trigger-pct", completed.stdout)
        self.assertIn("--drawdown-guard-deep-scale", completed.stdout)
        self.assertIn("--position-trailing-stop-pct", completed.stdout)

    def test_monthly_attribution_help_includes_stress_and_output_options(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "monthly-attribution",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--stress-exclude-return-above", completed.stdout)
        self.assertIn("--monthly-output", completed.stdout)
        self.assertIn("--symbol-output", completed.stdout)
        self.assertIn("--decision-output", completed.stdout)

    def test_monthly_validate_help_includes_failure_diagnostics_output(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "monthly-validate",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--failure-output", completed.stdout)
        self.assertIn("--remediation-output", completed.stdout)
        self.assertIn("--sweep-plan-output", completed.stdout)
        self.assertIn("--run-sweep-results", completed.stdout)
        self.assertIn("--sweep-result-output", completed.stdout)
        self.assertIn("--sweep-experiment-id", completed.stdout)
        self.assertIn("--sweep-limit", completed.stdout)

    def test_monthly_compare_validation_help_includes_delta_output(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "monthly-compare-validation",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--delta-output", completed.stdout)
        self.assertIn("--decision-output", completed.stdout)

    def test_monthly_candidate_followup_cli_writes_next_commands(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sweep = root / "sweep.csv"
            output = root / "followup.csv"
            sweep.write_text(
                "experiment_id,status,adoption_status,failed_delta,candidate_validation_args,risk_note\n"
                "weak_cash_10_position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-2,--cash-buffer-weight 0.1 --position-trailing-stop-pct -12,Plan only\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-candidate-followup",
                    "--sweep-results",
                    str(sweep),
                    "--data-dir",
                    "data/krx_expanded",
                    "--start",
                    "2024-01-01",
                    "--end",
                    "2026-06-18",
                    "--baseline-scenarios",
                    "data/reports/monthly_validation_scenarios_pit_universe.csv",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("candidate_followup_report", completed.stdout)
        self.assertIn("monthly-validate", text)
        self.assertIn("monthly-compare-validation", text)
        self.assertIn("--cash-buffer-weight 0.1", text)

    def test_monthly_failure_patterns_cli_writes_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.csv"
            delta = root / "delta.csv"
            output = root / "patterns.csv"
            baseline.write_text(
                "name,required,deployable,reason\n"
                "walk_001,True,False,negative_excess_return\n"
                "walk_002,True,True,passed\n",
                encoding="utf-8",
            )
            delta.write_text(
                "name,classification,candidate_label,diagnostic\n"
                "walk_001,UNCHANGED_FAILURE,cash_10,same_failure_persists\n"
                "walk_002,NEW_FAILURE,cash_10,selection_or_exposure_drag\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-failure-patterns",
                    "--baseline",
                    str(baseline),
                    "--delta-report",
                    str(delta),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("failure_pattern_report", completed.stdout)
        self.assertIn("walk_001", text)
        self.assertIn("walk_002", text)
        self.assertIn("pattern_status", text.splitlines()[0])

    def test_monthly_failure_drilldown_cli_writes_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.csv"
            patterns = root / "patterns.csv"
            delta = root / "delta.csv"
            output = root / "drilldown.csv"
            baseline.write_text(
                "name,category,required,deployable,reason,train_start,train_end,selected_preset,train_excess_return_pct,start,end,excess_return_pct,max_drawdown_pct,trade_count\n"
                "regime_sideways,regime,True,False,negative_excess_return,2024-01-01,2024-12-31,balanced,3.5,2025-01-01,2025-06-30,-7.1,-18.2,42\n",
                encoding="utf-8",
            )
            patterns.write_text(
                "scenario,pattern_status,dominant_diagnostic,failed_candidate_count,suggested_action\n"
                "regime_sideways,PERSISTENT_BLOCK,same_failure_persists=3,3,REVIEW_PERSISTENT_FAILURE\n",
                encoding="utf-8",
            )
            delta.write_text(
                "name,classification,candidate_label,excess_return_delta,max_drawdown_delta,trade_count_delta,diagnostic\n"
                "regime_sideways,UNCHANGED_FAILURE,cash_10,-2,1,-4,same_failure_persists\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-failure-drilldown",
                    "--baseline",
                    str(baseline),
                    "--patterns",
                    str(patterns),
                    "--delta-report",
                    str(delta),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("failure_drilldown_report", completed.stdout)
        self.assertIn("regime_sideways", text)
        self.assertIn("likely_root_cause", text.splitlines()[0])
        self.assertIn("weak_window_return_drag", text)

    def test_monthly_failure_drilldown_cli_uses_attribution_dir(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.csv"
            patterns = root / "patterns.csv"
            delta = root / "delta.csv"
            output = root / "drilldown.csv"
            baseline.write_text(
                "name,category,required,deployable,reason,start,end,excess_return_pct,max_drawdown_pct,trade_count\n"
                "regime_sideways,regime,True,False,negative_excess_return,2025-01-01,2025-06-30,-7.1,-18.2,42\n",
                encoding="utf-8",
            )
            patterns.write_text(
                "scenario,pattern_status,dominant_diagnostic,failed_candidate_count,suggested_action\n"
                "regime_sideways,PERSISTENT_BLOCK,same_failure_persists=3,3,REVIEW_PERSISTENT_FAILURE\n",
                encoding="utf-8",
            )
            delta.write_text(
                "name,classification,candidate_label,excess_return_delta,max_drawdown_delta,trade_count_delta,diagnostic\n"
                "regime_sideways,UNCHANGED_FAILURE,cash_10,1,1,-4,same_failure_persists\n",
                encoding="utf-8",
            )
            (root / "regime_sideways_decision_attribution.csv").write_text(
                "as_of_date,selected_symbols,target_exposure,cash_weight\n"
                "2025-01-01,005490;051910,0.99,0.01\n",
                encoding="utf-8",
            )
            (root / "regime_sideways_symbol_attribution.csv").write_text(
                "symbol,realized_pnl\n"
                "005490,-218620\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-failure-drilldown",
                    "--baseline",
                    str(baseline),
                    "--patterns",
                    str(patterns),
                    "--delta-report",
                    str(delta),
                    "--attribution-dir",
                    str(root),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(rows[0]["evidence_gaps"], "")
        self.assertIn("attribution_reports  2", completed.stdout)

    def test_monthly_compare_validation_cli_writes_comparison(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.csv"
            candidate = root / "candidate.csv"
            output = root / "comparison.csv"
            delta_output = root / "comparison_deltas.csv"
            decision_output = root / "candidate_decision.csv"
            baseline.write_text(
                "name,required,deployable,reason,excess_return_pct,max_drawdown_pct\n"
                "stress,True,False,max_drawdown_breach,5,-28\n"
                "walk_001,True,False,negative_excess_return,-1,-25\n"
                "walk_002,True,True,passed,1,-5\n",
                encoding="utf-8",
            )
            candidate.write_text(
                "name,required,deployable,reason,excess_return_pct,max_drawdown_pct\n"
                "stress,True,True,passed,6,-24\n"
                "walk_001,True,False,negative_excess_return,-2,-23\n"
                "walk_002,True,False,negative_excess_return,-0.2,-4\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-compare-validation",
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--candidate-label",
                    "weak_defense_cash_10",
                    "--output",
                    str(output),
                    "--delta-output",
                    str(delta_output),
                    "--decision-output",
                    str(decision_output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            text = output.read_text(encoding="utf-8")
            delta_text = delta_output.read_text(encoding="utf-8")
            decision_text = decision_output.read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("comparison_status  REJECT", completed.stdout)
        self.assertIn("candidate_decision_report", completed.stdout)
        self.assertIn("weak_defense_cash_10", text)
        self.assertIn("walk_002", text)
        self.assertIn("NEW_FAILURE", delta_text)
        self.assertIn("REJECT", decision_text)

    def test_production_check_includes_validation_candidate_decision_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact.csv"
            artifact.write_text("ok\n", encoding="utf-8")
            gate = root / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "True,,monthly-validate,1,0,1,-5,10,False\n",
                encoding="utf-8",
            )
            scenarios = root / "scenarios.csv"
            scenarios.write_text("name,required,deployable,reason\nfull_period,True,True,\n", encoding="utf-8")
            risk = root / "risk.csv"
            risk.write_text("name,status,detail\norders,PASS,valid\n", encoding="utf-8")
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,10,10,10,0,100.0,PASS,\n",
                encoding="utf-8",
            )
            decision = root / "monthly_validation_candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,new_failure_diagnostics,recommendation\n"
                "weak_cash10_stop12,REJECT,REJECT,new_failures=3,5,6,1,2,3,3,selection_or_exposure_drag=2; train_gate_regression=1,Do not adopt rejected candidate.\n",
                encoding="utf-8",
            )
            output = root / "readiness.csv"
            markdown = root / "readiness.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "production-check",
                    "--required-artifact",
                    str(artifact),
                    "--deployment-gate-file",
                    str(gate),
                    "--validation-scenarios",
                    str(scenarios),
                    "--risk-report",
                    str(risk),
                    "--coverage-report",
                    str(coverage),
                    "--validation-candidate-decision",
                    str(decision),
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--allow-blocked-exit-zero",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            readiness = output.read_text(encoding="utf-8") if output.exists() else ""
            markdown_text = markdown.read_text(encoding="utf-8") if markdown.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("validation_candidate_decision", readiness)
        self.assertIn("weak_cash10_stop12:REJECT", readiness)
        self.assertIn("new_failures=3", readiness)
        self.assertIn("Do not adopt rejected validation candidate", markdown_text)

    def test_production_check_writes_reports_and_prints_block(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact.csv"
            artifact.write_text("ok\n", encoding="utf-8")
            gate = root / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "False,failed_required_scenarios,monthly-validate,0,0,0,0,0,False\n",
                encoding="utf-8",
            )
            scenarios = root / "scenarios.csv"
            scenarios.write_text("name,required,deployable,reason\nfull_period,True,False,bias\n", encoding="utf-8")
            risk = root / "risk.csv"
            risk.write_text("name,status,detail\norders,PASS,valid\n", encoding="utf-8")
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,10,10,10,0,100.0,PASS,\n",
                encoding="utf-8",
            )
            output = root / "readiness.csv"
            markdown = root / "readiness.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "production-check",
                    "--required-artifact",
                    str(artifact),
                    "--deployment-gate-file",
                    str(gate),
                    "--validation-scenarios",
                    str(scenarios),
                    "--risk-report",
                    str(risk),
                    "--coverage-report",
                    str(coverage),
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--allow-blocked-exit-zero",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            output_exists = output.exists()
            markdown_exists = markdown.exists()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("readiness_status  BLOCK", completed.stdout)
        self.assertTrue(output_exists)
        self.assertTrue(markdown_exists)

    def test_production_check_blocks_stale_reports(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact.csv"
            artifact.write_text("ok\n", encoding="utf-8")
            performance = root / "performance.csv"
            performance.write_text("name,status,detail\nall,PASS,ok\n", encoding="utf-8")
            old_timestamp = datetime(2026, 1, 1, 9, 0, 0).timestamp()
            os.utime(performance, (old_timestamp, old_timestamp))
            output = root / "readiness.csv"
            markdown = root / "readiness.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "production-check",
                    "--required-artifact",
                    str(artifact),
                    "--performance-report",
                    str(performance),
                    "--max-report-age-days",
                    "30",
                    "--as-of",
                    "2026-06-21",
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--allow-blocked-exit-zero",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            readiness = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("readiness_status  BLOCK", completed.stdout)
        self.assertIn("performance_report_freshness", readiness)
        self.assertIn("exceeds 30d", readiness)

    def test_production_check_includes_validation_comparison_delta_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact.csv"
            artifact.write_text("ok\n", encoding="utf-8")
            gate = root / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "True,,monthly-validate,1,0,1,-5,10,False\n",
                encoding="utf-8",
            )
            scenarios = root / "scenarios.csv"
            scenarios.write_text("name,required,deployable,reason\nfull_period,True,True,\n", encoding="utf-8")
            risk = root / "risk.csv"
            risk.write_text("name,status,detail\norders,PASS,valid\n", encoding="utf-8")
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,10,10,10,0,100.0,PASS,\n",
                encoding="utf-8",
            )
            deltas = root / "monthly_validation_comparison_deltas.csv"
            deltas.write_text(
                "name,classification,diagnostic,excess_return_delta,max_drawdown_delta,trade_count_delta\n"
                "regime_bear,NEW_FAILURE,over_defense_or_filter_drag,-7.1,-2.0,54\n",
                encoding="utf-8",
            )
            output = root / "readiness.csv"
            markdown = root / "readiness.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "production-check",
                    "--required-artifact",
                    str(artifact),
                    "--deployment-gate-file",
                    str(gate),
                    "--validation-scenarios",
                    str(scenarios),
                    "--risk-report",
                    str(risk),
                    "--coverage-report",
                    str(coverage),
                    "--validation-comparison-deltas",
                    str(deltas),
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--allow-blocked-exit-zero",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            readiness = output.read_text(encoding="utf-8") if output.exists() else ""
            markdown_text = markdown.read_text(encoding="utf-8") if markdown.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("validation_comparison_deltas", readiness)
        self.assertIn("NEW_FAILURE=1", readiness)
        self.assertIn("over_defense_or_filter_drag=1", readiness)
        self.assertIn("Review validation scenario deltas", markdown_text)

    def test_production_check_includes_missing_ohlcv_target_plan(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact.csv"
            artifact.write_text("ok\n", encoding="utf-8")
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,83,83,17,83.0,PASS,AAA;BBB\n",
                encoding="utf-8",
            )
            targets = root / "targets.csv"
            targets.write_text(
                "symbol,name,market,missing_snapshots,first_missing_date,last_missing_date\n"
                "000660,Hynix,KOSPI,5,2024-01-31,2024-05-31\n",
                encoding="utf-8",
            )
            fetch_plan = root / "fetch_plan.csv"
            fetch_plan.write_text(
                "plan_id,status,target_count,batch_size,max_batches,planned_batches,planned_symbols,remaining_after_plan,batch_timeout_seconds,batch_pause_seconds,top_symbols,start,end,universe_file,data_dir,targets_output,report_dir,recommended_command,risk_note\n"
                "missing_ohlcv_fetch,READY,1,50,1,1,1,0,300,10,000660:5,2024-01-01,2026-06-18,universe.csv,prices,targets.csv,reports,python -m backtester fetch-pykrx-missing-ohlcv-loop --batch-size 50,Plan only\n",
                encoding="utf-8",
            )
            output = root / "readiness.csv"
            markdown = root / "readiness.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "production-check",
                    "--required-artifact",
                    str(artifact),
                    "--coverage-report",
                    str(coverage),
                    "--missing-ohlcv-targets",
                    str(targets),
                    "--missing-ohlcv-fetch-plan",
                    str(fetch_plan),
                    "--output",
                    str(output),
                    "--markdown-output",
                    str(markdown),
                    "--allow-blocked-exit-zero",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            readiness = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("krx_missing_ohlcv_targets", readiness)
        self.assertIn("top=000660:5", readiness)
        self.assertIn("krx_missing_ohlcv_fetch_plan", readiness)
        self.assertIn("planned_symbols=1", readiness)

    def test_monthly_plan_help_includes_human_summary_output(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "monthly-plan",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--summary-output", completed.stdout)

    def test_plan_pykrx_missing_ohlcv_writes_prioritized_targets(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            data_dir.mkdir()
            (data_dir / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2024-01-15,1,1,1,1,1\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "date,symbol,name,market\n"
                "2024-01-31,005930,Samsung,KOSPI\n"
                "2024-01-31,000660,Hynix,KOSPI\n"
                "2024-02-29,000660,Hynix,KOSPI\n",
                encoding="utf-8",
            )
            output = root / "targets.csv"
            fetch_plan = root / "fetch_plan.csv"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "plan-pykrx-missing-ohlcv",
                    "--universe-file",
                    str(universe),
                    "--data-dir",
                    str(data_dir),
                    "--output",
                    str(output),
                    "--fetch-plan-output",
                    str(fetch_plan),
                    "--batch-size",
                    "50",
                    "--max-batches",
                    "1",
                    "--batch-timeout-seconds",
                    "120",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8") if output.exists() else ""
            plan_text = fetch_plan.read_text(encoding="utf-8") if fetch_plan.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("saved 1 missing OHLCV targets", completed.stdout)
        self.assertIn("fetch_plan", completed.stdout)
        self.assertIn("000660", text)
        self.assertIn("missing_snapshots", text)
        self.assertIn("recommended_command", plan_text)
        self.assertIn("fetch-pykrx-missing-ohlcv-loop", plan_text)

    def test_fetch_pykrx_missing_ohlcv_loop_help_is_available(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "fetch-pykrx-missing-ohlcv-loop",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--batch-timeout-seconds", completed.stdout)
        self.assertIn("--max-batches", completed.stdout)
        self.assertIn("--summary-output", completed.stdout)

    def test_health_check_help_includes_scalper_mode(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "health-check",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--scalper-mode", completed.stdout)


if __name__ == "__main__":
    unittest.main()
