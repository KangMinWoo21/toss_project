import subprocess
import sys
import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory


class CliTests(unittest.TestCase):
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

    def test_plan_pykrx_missing_ohlcv_writes_prioritized_targets(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            data_dir.mkdir()
            (data_dir / "005930.csv").write_text("date,open,high,low,close,volume\n", encoding="utf-8")
            universe = root / "universe.csv"
            universe.write_text(
                "date,symbol,name,market\n"
                "2024-01-31,005930,Samsung,KOSPI\n"
                "2024-01-31,000660,Hynix,KOSPI\n"
                "2024-02-29,000660,Hynix,KOSPI\n",
                encoding="utf-8",
            )
            output = root / "targets.csv"

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
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            text = output.read_text(encoding="utf-8") if output.exists() else ""

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("saved 1 missing OHLCV targets", completed.stdout)
        self.assertIn("000660", text)
        self.assertIn("missing_snapshots", text)

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


if __name__ == "__main__":
    unittest.main()
