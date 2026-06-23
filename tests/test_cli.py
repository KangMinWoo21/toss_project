import subprocess
import sys
import unittest
import os
import csv
from datetime import datetime, timedelta
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

    def _write_trend_price_file(self, data_dir: Path, symbol: str, *, close: float, step: float, volume: int) -> str:
        data_dir.mkdir(parents=True, exist_ok=True)
        start = datetime.fromisoformat("2024-01-01")
        lines = ["date,open,high,low,close,volume"]
        for index in range(220):
            day = (start + timedelta(days=index)).date().isoformat()
            price = close + step * index
            lines.append(f"{day},{price},{price + 1},{max(1, price - 1)},{price},{volume}")
        (data_dir / f"{symbol}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return (start + timedelta(days=219)).date().isoformat()

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
            cwd = Path(temp_dir)
            data_dir = cwd / "prices"
            data_dir.mkdir()
            (data_dir / "111111.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2024-01-02,100,101,99,100,1000\n"
                "2024-02-01,100,101,99,100,1000\n"
                "2024-03-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            (data_dir / "222222.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2024-01-02,100,101,99,100,1000\n"
                "2024-02-01,100,101,99,100,1000\n"
                "2024-03-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            excluded = cwd / "excluded.csv"
            excluded.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")

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
                    str(excluded),
                ],
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
        self.assertIn("--market-beta-proxy-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-neutral-breadth-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-medium-lookback-days", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-medium-drawdown-pct", completed.stdout)

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
        self.assertIn("--summary-output", completed.stdout)
        self.assertIn("--market-beta-proxy-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-neutral-breadth-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-medium-lookback-days", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-medium-drawdown-pct", completed.stdout)
        self.assertIn("--drawdown-guard-deep-trigger-pct", completed.stdout)
        self.assertIn("--drawdown-guard-deep-scale", completed.stdout)
        self.assertIn("--train-start", completed.stdout)
        self.assertIn("--proxy-output", completed.stdout)
        self.assertIn("--stress-drawdown-output", completed.stdout)

    def test_monthly_attribution_cli_writes_recovery_summary_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            for symbol, step, volume in [
                ("AAA", 1.0, 10_000),
                ("BBB", 0.8, 9_000),
                ("CCC", 0.6, 8_000),
                ("DDD", 0.4, 7_000),
                ("EEE", 0.2, 6_000),
                ("FFF", -0.1, 5_000),
            ]:
                self._write_trend_price_file(data_dir, symbol, close=100, step=step, volume=volume)
            summary_output = root / "recovery_summary.csv"
            proxy_output = root / "proxy_diagnostics.csv"
            stress_drawdown_output = root / "stress_drawdown.csv"

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-attribution",
                    "--data-dir",
                    str(data_dir),
                    "--start",
                    "2024-05-01",
                    "--end",
                    "2024-08-07",
                    "--point-in-time-min-history-days",
                    "20",
                    "--train-start",
                    "2024-01-01",
                    "--scenario-name",
                    "walk_forward_unit",
                    "--drawdown-guard-deep-trigger-pct",
                    "-20",
                    "--drawdown-guard-deep-scale",
                    "0.35",
                    "--market-beta-proxy-reversal-guard-medium-drawdown-pct",
                    "-10",
                    "--summary-output",
                    str(summary_output),
                    "--proxy-output",
                    str(proxy_output),
                    "--stress-drawdown-output",
                    str(stress_drawdown_output),
                ],
            )
            if summary_output.exists():
                with summary_output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []
            if proxy_output.exists():
                with proxy_output.open(encoding="utf-8") as f:
                    proxy_rows = list(csv.DictReader(f))
            else:
                proxy_rows = []
            if stress_drawdown_output.exists():
                with stress_drawdown_output.open(encoding="utf-8") as f:
                    stress_drawdown_rows = list(csv.DictReader(f))
            else:
                stress_drawdown_rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("recovery_attribution_report", completed.stdout)
        self.assertIn("proxy_decision_diagnostics_report", completed.stdout)
        self.assertIn("stress_drawdown_pressure_report", completed.stdout)
        self.assertTrue(rows)
        self.assertTrue(proxy_rows)
        self.assertTrue(stress_drawdown_rows)
        self.assertEqual(rows[0]["scenario"], "walk_forward_unit")
        self.assertEqual(proxy_rows[0]["scenario"], "walk_forward_unit")
        self.assertEqual(stress_drawdown_rows[0]["scenario"], "walk_forward_unit")
        self.assertIn("recommended_next_action", proxy_rows[0])
        self.assertIn("recommended_candidate_focus", stress_drawdown_rows[0])
        self.assertIn("diagnostic", rows[0])

    def test_monthly_proxy_guard_diagnostics_cli_writes_outcome_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proxy_input = root / "proxy_diagnostics.csv"
            output = root / "proxy_guard_outcomes.csv"
            proxy_input.write_text(
                "scenario,as_of_date,signal_date,month,month_return_pct,month_status,mode,reason,"
                "target_exposure,cash_weight,proxy_reversal_guard_triggered,proxy_reversal_guard_cap,"
                "proxy_reversal_guard_medium_return_pct,proxy_reversal_guard_short_return_pct,"
                "proxy_reversal_guard_reason,diagnostic,recommended_next_action\n"
                "candidate_guard,2025-06-02,2025-05-30,2025-06,7.4531,GAIN,market_beta_proxy,"
                "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped,0.55,0.45,true,"
                "0.55,38.5407,8.6214,proxy_reversal_guard_capped,"
                "market_beta_proxy;proxy_gain_participation;strong_breadth,"
                "preserve_train_gate_and_improve_alpha_candidates\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-proxy-guard-diagnostics",
                    "--proxy-input",
                    str(proxy_input),
                    "--output",
                    str(output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("proxy_guard_outcomes_report", completed.stdout)
        self.assertEqual(rows[0]["guard_outcome"], "profitable_continuation_capped")
        self.assertEqual(rows[0]["paper_only"], "true")

    def test_monthly_proxy_guard_recovery_exits_cli_writes_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proxy_input = root / "proxy_diagnostics.csv"
            comparison_input = root / "attribution_comparison.csv"
            output = root / "proxy_guard_recovery_exits.csv"
            proxy_input.write_text(
                "scenario,month,month_return_pct,month_status,mode,reason,target_exposure,cash_weight,"
                "proxy_reversal_guard_triggered,proxy_reversal_guard_medium_return_pct,"
                "proxy_reversal_guard_short_return_pct,proxy_reversal_guard_medium_drawdown_pct,"
                "proxy_reversal_guard_reason,diagnostic\n"
                "walk_forward_005,2026-03,-13.954,LOSS,market_beta_proxy,"
                "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped,0.55,0.45,"
                "true,63.4465,32.5244,-4.9111,proxy_reversal_guard_capped,"
                "market_beta_proxy;strong_breadth\n"
                "walk_forward_005,2026-04,16.3361,GAIN,market_beta_proxy,"
                "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped,0.55,0.45,"
                "true,36.6735,-6.6038,-12.4731,proxy_reversal_guard_capped,"
                "market_beta_proxy;proxy_gain_participation;strong_breadth\n",
                encoding="utf-8",
            )
            comparison_input.write_text(
                "scenario,month,baseline_return_pct,candidate_return_pct,return_delta_pct,"
                "baseline_worst_drawdown_pct,candidate_worst_drawdown_pct,drawdown_delta_pct,diagnostic\n"
                "walk_forward_005,2026-03,-19.2651,-13.954,5.3111,-20.5503,-15.2709,5.2794,drawdown_improved\n"
                "walk_forward_005,2026-04,20.1371,16.3361,-3.801,-14.7816,-10.6855,4.0961,return_drag\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-proxy-guard-recovery-exits",
                    "--proxy-input",
                    str(proxy_input),
                    "--comparison-input",
                    str(comparison_input),
                    "--scenario",
                    "walk_forward_005",
                    "--candidate-label",
                    "proxy_guard_short5_extreme50_mdd10",
                    "--output",
                    str(output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("proxy_guard_recovery_exit_report", completed.stdout)
        self.assertEqual(rows[0]["recovery_exit_outcome"], "recovery_drag_after_loss_cap")
        self.assertEqual(rows[0]["paper_only"], "true")

    def test_monthly_compare_attribution_cli_writes_monthly_delta_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline.csv"
            candidate = root / "candidate.csv"
            output = root / "compare.csv"
            baseline.write_text(
                "month,return_pct,equity_change,worst_drawdown_pct,status\n"
                "2026-02,8,800,-10,GAIN\n"
                "2026-03,-18,-1800,-24,LOSS\n",
                encoding="utf-8",
            )
            candidate.write_text(
                "month,return_pct,equity_change,worst_drawdown_pct,status\n"
                "2026-02,7,700,-11,GAIN\n"
                "2026-03,-20,-2100,-25.2,LOSS\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-compare-attribution",
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--scenario",
                    "full_period",
                    "--candidate-label",
                    "neutral_cap",
                    "--drawdown-threshold-pct",
                    "-25",
                    "--output",
                    str(output),
                ],
            )
            with output.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("attribution_comparison_report", completed.stdout)
        self.assertIn("new_drawdown_breach_months  1", completed.stdout)
        self.assertEqual(rows[1]["diagnostic"], "new_drawdown_breach")
        self.assertEqual(rows[1]["candidate_label"], "neutral_cap")

    def test_monthly_compare_decisions_cli_writes_exposure_and_symbol_delta_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline_decisions.csv"
            candidate = root / "candidate_decisions.csv"
            output = root / "decision_compare.csv"
            baseline.write_text(
                "as_of_date,signal_date,mode,selected_preset,position_count,selected_symbols,"
                "target_exposure,cash_weight,max_position_weight,min_position_weight,target_weights,reason\n"
                "2025-03-31,2025-03-28,market_beta_proxy,balanced,3,AAA;BBB;CCC,"
                "0.99,0.01,0.33,0.33,AAA:0.33;BBB:0.33;CCC:0.33,baseline_high_exposure\n",
                encoding="utf-8",
            )
            candidate.write_text(
                "as_of_date,signal_date,mode,selected_preset,position_count,selected_symbols,"
                "target_exposure,cash_weight,max_position_weight,min_position_weight,target_weights,reason\n"
                "2025-03-31,2025-03-28,market_beta_proxy,balanced,2,AAA;DDD,"
                "0.5,0.5,0.25,0.25,AAA:0.25;DDD:0.25,neutral_breadth_proxy_cap\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-compare-decisions",
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--scenario",
                    "full_period",
                    "--candidate-label",
                    "neutral_cap",
                    "--output",
                    str(output),
                ],
            )
            with output.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("decision_comparison_report", completed.stdout)
        self.assertIn("changed_decision_rows  1", completed.stdout)
        self.assertEqual(rows[0]["target_exposure_delta"], "-0.49")
        self.assertEqual(rows[0]["baseline_only_symbols"], "BBB;CCC")
        self.assertEqual(rows[0]["candidate_only_symbols"], "DDD")
        self.assertIn("symbol_rotation", rows[0]["diagnostic"])

    def test_monthly_compare_paths_cli_writes_daily_path_delta_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = root / "baseline_path.csv"
            candidate = root / "candidate_path.csv"
            output = root / "path_compare.csv"
            baseline.write_text(
                "date,equity,drawdown_pct,cash,exposure,position_count,total_position_quantity,"
                "position_symbols,turnover_value,estimated_trade_cost\n"
                "2025-03-03,1000,-5,200,0.8,2,12,AAA;BBB,100,0.1\n",
                encoding="utf-8",
            )
            candidate.write_text(
                "date,equity,drawdown_pct,cash,exposure,position_count,total_position_quantity,"
                "position_symbols,turnover_value,estimated_trade_cost\n"
                "2025-03-03,980,-7,392,0.6,2,10,AAA;CCC,200,0.2\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-compare-paths",
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--scenario",
                    "full_period",
                    "--candidate-label",
                    "neutral_cap",
                    "--output",
                    str(output),
                ],
            )
            with output.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("path_comparison_report", completed.stdout)
        self.assertIn("equity_regression_days  1", completed.stdout)
        self.assertEqual(rows[0]["equity_delta"], "-20")
        self.assertEqual(rows[0]["candidate_only_symbols"], "CCC")
        self.assertIn("higher_trade_cost", rows[0]["diagnostic"])

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
        self.assertIn("--market-beta-proxy-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-max-exposure", completed.stdout)
        self.assertIn("--market-beta-proxy-reversal-guard-medium-lookback-days", completed.stdout)
        self.assertIn("--direct-alpha-target-persistence-signals", completed.stdout)

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

    def test_monthly_failure_patterns_explicit_delta_report_does_not_read_default_glob(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "data" / "reports"
            reports.mkdir(parents=True)
            baseline = root / "baseline.csv"
            explicit_delta = root / "explicit_delta.csv"
            diagnostic_delta = reports / "monthly_validation_comparison_deltas_multi_preset.csv"
            output = root / "patterns.csv"
            baseline.write_text(
                "name,required,deployable,reason\n"
                "walk_001,True,False,negative_excess_return\n",
                encoding="utf-8",
            )
            explicit_delta.write_text(
                "name,classification,candidate_label,diagnostic\n"
                "walk_001,UNCHANGED_FAILURE,approved_candidate,same_failure_persists\n",
                encoding="utf-8",
            )
            diagnostic_delta.write_text(
                "name,classification,candidate_label,diagnostic\n"
                "walk_001,RESOLVED,multi_preset,diagnostic_only\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-failure-patterns",
                    "--baseline",
                    str(baseline),
                    "--delta-report",
                    str(explicit_delta),
                    "--output",
                    str(output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("delta_reports  1", completed.stdout)
        self.assertEqual(rows[0]["candidate_labels_unchanged"], "approved_candidate")
        self.assertEqual(rows[0]["candidate_labels_resolved"], "")

    def test_monthly_failure_patterns_default_glob_skips_multi_preset_diagnostics(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "data" / "reports"
            reports.mkdir(parents=True)
            baseline = root / "baseline.csv"
            candidate_delta = reports / "monthly_validation_comparison_deltas_position_stop_12.csv"
            diagnostic_delta = reports / "monthly_validation_comparison_deltas_multi_preset.csv"
            output = root / "patterns.csv"
            baseline.write_text(
                "name,required,deployable,reason\n"
                "walk_001,True,False,negative_excess_return\n",
                encoding="utf-8",
            )
            candidate_delta.write_text(
                "name,classification,candidate_label,diagnostic\n"
                "walk_001,UNCHANGED_FAILURE,position_stop_12,same_failure_persists\n",
                encoding="utf-8",
            )
            diagnostic_delta.write_text(
                "name,classification,candidate_label,diagnostic\n"
                "walk_001,RESOLVED,multi_preset,diagnostic_only\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-failure-patterns",
                    "--baseline",
                    str(baseline),
                    "--output",
                    str(output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("delta_reports  1", completed.stdout)
        self.assertEqual(rows[0]["candidate_labels_unchanged"], "position_stop_12")
        self.assertEqual(rows[0]["candidate_labels_resolved"], "")

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

    def test_monthly_failure_drilldown_explicit_delta_report_does_not_read_default_glob(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "data" / "reports"
            reports.mkdir(parents=True)
            baseline = root / "baseline.csv"
            patterns = root / "patterns.csv"
            explicit_delta = root / "explicit_delta.csv"
            diagnostic_delta = reports / "monthly_validation_comparison_deltas_multi_preset.csv"
            output = root / "drilldown.csv"
            baseline.write_text(
                "name,category,required,deployable,reason,start,end,excess_return_pct,max_drawdown_pct,trade_count\n"
                "regime_sideways,regime,True,False,negative_excess_return,2025-01-01,2025-06-30,-7.1,-18.2,42\n",
                encoding="utf-8",
            )
            patterns.write_text(
                "scenario,pattern_status,dominant_diagnostic,failed_candidate_count,suggested_action\n"
                "regime_sideways,PERSISTENT_BLOCK,same_failure_persists=1,1,REVIEW_PERSISTENT_FAILURE\n",
                encoding="utf-8",
            )
            explicit_delta.write_text(
                "name,classification,candidate_label,excess_return_delta,max_drawdown_delta,trade_count_delta,diagnostic\n"
                "regime_sideways,UNCHANGED_FAILURE,approved_candidate,1,1,-4,same_failure_persists\n",
                encoding="utf-8",
            )
            diagnostic_delta.write_text(
                "name,classification,candidate_label,excess_return_delta,max_drawdown_delta,trade_count_delta,diagnostic\n"
                "regime_sideways,RESOLVED,multi_preset,9,1,4,diagnostic_only\n",
                encoding="utf-8",
            )

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-failure-drilldown",
                    "--baseline",
                    str(baseline),
                    "--patterns",
                    str(patterns),
                    "--delta-report",
                    str(explicit_delta),
                    "--output",
                    str(output),
                ],
            )
            with output.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("delta_reports  1", completed.stdout)
        self.assertIn("approved_candidate", rows[0]["candidate_labels"])
        self.assertNotIn("multi_preset", rows[0]["candidate_labels"])

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

    def test_monthly_direct_alpha_diagnostics_cli_writes_selection_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            train_end = self._write_trend_price_file(data_dir, "AAA", close=100, step=1.2, volume=10_000)
            for symbol, step, volume in [
                ("BBB", 1.0, 9_000),
                ("CCC", 0.8, 8_000),
                ("DDD", 0.6, 7_000),
                ("EEE", 0.4, 6_000),
                ("FFF", 0.2, 5_000),
                ("PENNY", 0.01, 20_000),
                ("OUT", 2.0, 30_000),
            ]:
                self._write_trend_price_file(
                    data_dir,
                    symbol,
                    close=10 if symbol == "PENNY" else 100,
                    step=step,
                    volume=volume,
                )
            baseline = root / "baseline.csv"
            baseline.write_text(
                "name,category,required,train_start,train_end,start,end,deployable,reason\n"
                f"walk_forward_unit,walk_forward,True,2024-01-01,{train_end},2024-08-08,2024-09-30,False,train_window_rejected\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "date,symbol\n"
                + "".join(f"{train_end},{symbol}\n" for symbol in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "PENNY"]),
                encoding="utf-8",
            )
            output = root / "direct_alpha_selection.csv"
            path_output = root / "direct_alpha_path.csv"
            path_drift_output = root / "direct_alpha_path_drift.csv"
            timing_output = root / "direct_alpha_timing.csv"
            rank_drift_output = root / "direct_alpha_rank_drift.csv"

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-direct-alpha-diagnostics",
                    "--data-dir",
                    str(data_dir),
                    "--baseline",
                    str(baseline),
                    "--scenario",
                    "walk_forward_unit",
                    "--point-in-time-universe",
                    str(universe),
                    "--point-in-time-min-history-days",
                    "20",
                    "--point-in-time-min-reference-price",
                    "50",
                    "--point-in-time-liquidity-top-n",
                    "6",
                    "--point-in-time-liquidity-window-days",
                    "20",
                    "--min-rows-per-window",
                    "20",
                    "--start-grace-days",
                    "0",
                    "--output",
                    str(output),
                    "--path-output",
                    str(path_output),
                    "--path-drift-output",
                    str(path_drift_output),
                    "--timing-output",
                    str(timing_output),
                    "--rank-drift-output",
                    str(rank_drift_output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []
            if path_output.exists():
                with path_output.open(encoding="utf-8") as f:
                    path_rows = list(csv.DictReader(f))
            else:
                path_rows = []
            if path_drift_output.exists():
                with path_drift_output.open(encoding="utf-8") as f:
                    path_drift_rows = list(csv.DictReader(f))
            else:
                path_drift_rows = []
            if timing_output.exists():
                with timing_output.open(encoding="utf-8") as f:
                    timing_rows = list(csv.DictReader(f))
            else:
                timing_rows = []
            if rank_drift_output.exists():
                with rank_drift_output.open(encoding="utf-8") as f:
                    rank_drift_rows = list(csv.DictReader(f))
            else:
                rank_drift_rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("direct_alpha_selection_report", completed.stdout)
        self.assertIn("direct_alpha_path_report", completed.stdout)
        self.assertIn("direct_alpha_path_drift_report", completed.stdout)
        self.assertIn("direct_alpha_timing_report", completed.stdout)
        self.assertIn("direct_alpha_rank_drift_report", completed.stdout)
        self.assertTrue(any(row["symbol"] == "AAA" and row["selection_status"] == "selected" for row in rows))
        self.assertTrue(any(row["symbol"] == "FFF" and row["rejection_reason"] == "below_selected_rank" for row in rows))
        self.assertTrue(any("AAA" in row["held_symbols"].split(";") for row in path_rows))
        self.assertTrue(any(row["symbol"] == "AAA" and "contribution_delta_pct" in row for row in path_drift_rows))
        self.assertTrue(any("timing_diagnostic" in row for row in timing_rows))
        self.assertTrue(any("momentum_delta_pct" in row and "drop_reason" in row for row in rank_drift_rows))

    def test_monthly_train_decision_diagnostics_cli_writes_path_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            train_end = self._write_trend_price_file(data_dir, "AAA", close=100, step=1.2, volume=10_000)
            for symbol, step, volume in [
                ("BBB", 1.0, 9_000),
                ("CCC", 0.8, 8_000),
                ("DDD", 0.6, 7_000),
                ("EEE", 0.4, 6_000),
                ("FFF", 0.2, 5_000),
            ]:
                self._write_trend_price_file(data_dir, symbol, close=100, step=step, volume=volume)
            baseline = root / "baseline.csv"
            baseline.write_text(
                "name,category,required,train_start,train_end,start,end,deployable,reason\n"
                f"walk_forward_unit,walk_forward,True,2024-01-01,{train_end},2024-08-08,2024-09-30,False,train_window_rejected\n",
                encoding="utf-8",
            )
            output = root / "train_decisions.csv"
            stability_output = root / "train_stability.csv"
            stability_symbol_output = root / "train_stability_symbols.csv"
            path_drift_experiment_output = root / "path_drift_experiments.csv"

            completed = self._run_backtester_in_cwd(
                root,
                [
                    "monthly-train-decision-diagnostics",
                    "--data-dir",
                    str(data_dir),
                    "--baseline",
                    str(baseline),
                    "--scenario",
                    "walk_forward_unit",
                    "--point-in-time-universe",
                    "",
                    "--point-in-time-min-history-days",
                    "20",
                    "--point-in-time-min-reference-price",
                    "50",
                    "--point-in-time-liquidity-top-n",
                    "6",
                    "--point-in-time-liquidity-window-days",
                    "20",
                    "--min-rows-per-window",
                    "20",
                    "--start-grace-days",
                    "0",
                    "--train-stability-years",
                    "1",
                    "--min-train-trades",
                    "999",
                    "--output",
                    str(output),
                    "--stability-output",
                    str(stability_output),
                    "--stability-symbol-output",
                    str(stability_symbol_output),
                    "--path-drift-experiment-output",
                    str(path_drift_experiment_output),
                ],
            )
            if output.exists():
                with output.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = []
            if stability_output.exists():
                with stability_output.open(encoding="utf-8") as f:
                    stability_rows = list(csv.DictReader(f))
            else:
                stability_rows = []
            if stability_symbol_output.exists():
                with stability_symbol_output.open(encoding="utf-8") as f:
                    stability_symbol_rows = list(csv.DictReader(f))
            else:
                stability_symbol_rows = []
            if path_drift_experiment_output.exists():
                with path_drift_experiment_output.open(encoding="utf-8") as f:
                    path_drift_experiment_rows = list(csv.DictReader(f))
            else:
                path_drift_experiment_rows = []

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("train_decision_path_report", completed.stdout)
        self.assertIn("train_stability_report", completed.stdout)
        self.assertIn("train_stability_symbol_report", completed.stdout)
        self.assertIn("train_path_drift_experiment_report", completed.stdout)
        self.assertTrue(rows)
        self.assertTrue(any(row["direct_candidate_rejection_reasons"] or row["filter_error"] for row in rows))
        self.assertTrue(stability_rows)
        self.assertTrue(any("subwindow_positive_flag" in row for row in stability_rows))
        self.assertTrue(any("candidate_eligible" in row for row in stability_rows))
        self.assertTrue(any("stability_failed_reason" in row for row in stability_rows))
        self.assertTrue(any("stability_underperformance_driver" in row for row in stability_rows))
        self.assertTrue(any(row["candidate_rejection_reasons"] for row in stability_rows))
        self.assertTrue(stability_symbol_rows)
        self.assertTrue(any("stability_symbol_role" in row for row in stability_symbol_rows))
        self.assertTrue(any("symbol_return_pct" in row for row in stability_symbol_rows))
        self.assertTrue(path_drift_experiment_rows)
        self.assertTrue(any("experiment_recommendation" in row for row in path_drift_experiment_rows))
        self.assertTrue(any(row["paper_only"] == "true" for row in path_drift_experiment_rows))

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

    def test_monthly_candidate_summary_cli_combines_deltas_and_path_comparison(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision = root / "candidate_decision.csv"
            deltas = root / "candidate_deltas.csv"
            path = root / "path_comparison.csv"
            output = root / "candidate_summary.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,"
                "candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,"
                "resolved_failure_names,new_failure_names,new_failure_diagnostics,recommendation\n"
                "neutral_breadth_proxy_cap_50,REJECT,REJECT,"
                "comparison_rejected; new_failures=2; drawdown_buffer_regressions=2,5,6,1,1,2,4,"
                "walk_forward_003,full_period; stress_slippage_x3,"
                "equity_improved_but_drawdown_buffer_worse=2,Do not adopt.\n",
                encoding="utf-8",
            )
            deltas.write_text(
                "candidate_label,name,classification,diagnostic,excess_return_delta,max_drawdown_delta\n"
                "neutral_breadth_proxy_cap_50,walk_forward_003,RESOLVED,candidate_fixed_required_failure,1,2\n"
                "neutral_breadth_proxy_cap_50,full_period,NEW_FAILURE,"
                "equity_improved_but_drawdown_buffer_worse,0.0247,-1.0891\n",
                encoding="utf-8",
            )
            path.write_text(
                "candidate_label,scenario,date,equity_delta,candidate_drawdown_pct,rolling_peak_delta,"
                "drawdown_delta_pct,diagnostic\n"
                "neutral_breadth_proxy_cap_50,full_period,2025-04-07,154349.6019,-25.1331,387782.9119,-1.1549,"
                "equity_improved;drawdown_regression;higher_turnover\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "monthly-candidate-summary",
                    "--decision",
                    str(decision),
                    "--deltas",
                    str(deltas),
                    "--path-comparison",
                    str(path),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            with output.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("candidate_summary_report", completed.stdout)
        self.assertIn("candidate_rows  1", completed.stdout)
        self.assertIn("top_candidate  neutral_breadth_proxy_cap_50 decision=REJECT", completed.stdout)
        self.assertEqual(rows[0]["drawdown_buffer_regression_count"], "2")
        self.assertEqual(rows[0]["path_equity_improved_days"], "1")
        self.assertEqual(rows[0]["path_higher_turnover_days"], "1")
        self.assertEqual(rows[0]["path_acceptance_decision"], "REJECT")
        self.assertEqual(rows[0]["path_equity_improved_drawdown_breach_days"], "1")
        self.assertIn("higher_rolling_peak_drawdown_buffer_loss", rows[0]["path_rejection_reasons"])

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
        self.assertIn("--market-beta-proxy-max-exposure", completed.stdout)

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
