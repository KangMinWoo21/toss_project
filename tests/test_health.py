import csv
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.health import evaluate_health, save_health_json, save_health_markdown


AS_OF = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)


class HealthCheckTests(unittest.TestCase):
    def test_latest_reports_pass_health_check(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            report = evaluate_health(root=root, as_of=AS_OF, max_report_age_hours=48, max_scalper_age_hours=24)

        self.assertEqual(report.status, "PASS")
        self.assertFalse([check for check in report.checks if check.status != "PASS"])

    def test_stale_report_blocks_when_beyond_block_age(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            old = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp()
            os.utime(root / "data" / "reports" / "monthly_order_plan.csv", (old, old))

            report = evaluate_health(
                root=root,
                as_of=AS_OF,
                max_report_age_hours=48,
                block_report_age_hours=168,
                max_scalper_age_hours=24,
            )

        self.assertEqual(report.status, "BLOCK")
        stale = [check for check in report.checks if check.name == "monthly_order_plan"][0]
        self.assertEqual(stale.status, "BLOCK")
        self.assertIn("stale", stale.detail)
        self.assertIn("Regenerate", stale.suggested_action)

    def test_missing_required_report_blocks_health_check(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            (root / "data" / "reports" / "production_readiness.csv").unlink()

            report = evaluate_health(root=root, as_of=AS_OF)

        self.assertEqual(report.status, "BLOCK")
        missing = [check for check in report.checks if check.name == "production_readiness"][0]
        self.assertEqual(missing.status, "BLOCK")
        self.assertIn("missing", missing.detail)

    def test_csv_schema_drift_blocks_when_required_column_is_missing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            _write_csv(root / "data" / "reports" / "monthly_order_plan.csv", ["as_of_date", "symbol"], [])

            report = evaluate_health(root=root, as_of=AS_OF)

        drift = [check for check in report.checks if check.name == "monthly_order_plan"][0]
        self.assertEqual(drift.status, "BLOCK")
        self.assertIn("schema_drift", drift.detail)
        self.assertIn("Regenerate", drift.suggested_action)

    def test_stale_scalper_data_can_warn_in_monthly_only_mode(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            old = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp()
            os.utime(root / "data" / "scalper" / "AAPL_2026-06-21_paper_scalp.csv", (old, old))

            report = evaluate_health(
                root=root,
                as_of=AS_OF,
                scalper_mode="warn",
                max_scalper_age_hours=24,
                block_scalper_age_hours=72,
            )

        scalper = [check for check in report.checks if check.name == "scalper_data"][0]
        self.assertEqual(report.status, "WARN")
        self.assertEqual(scalper.status, "WARN")
        self.assertIn("mode=warn", scalper.detail)

    def test_missing_scalper_data_blocks_in_required_mode(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            for item in (root / "data" / "scalper").glob("*"):
                item.unlink()
            (root / "data" / "scalper").rmdir()

            report = evaluate_health(root=root, as_of=AS_OF, scalper_mode="required")

        scalper = [check for check in report.checks if check.name == "scalper_data"][0]
        self.assertEqual(report.status, "BLOCK")
        self.assertEqual(scalper.status, "BLOCK")

    def test_scalper_monitoring_can_be_disabled_explicitly(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            old = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp()
            os.utime(root / "data" / "scalper" / "AAPL_2026-06-21_paper_scalp.csv", (old, old))

            report = evaluate_health(root=root, as_of=AS_OF, scalper_mode="off")

        scalper = [check for check in report.checks if check.name == "scalper_data"][0]
        self.assertEqual(report.status, "PASS")
        self.assertEqual(scalper.status, "PASS")
        self.assertIn("disabled", scalper.detail)

    def test_missing_ohlcv_fetch_summary_schema_drift_blocks_health_check(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            _write_csv(root / "data" / "reports" / "krx_missing_ohlcv_fetch_summary.csv", ["status"], [])

            report = evaluate_health(root=root, as_of=AS_OF)

        drift = [check for check in report.checks if check.name == "krx_missing_ohlcv_fetch_summary"][0]
        self.assertEqual(drift.status, "BLOCK")
        self.assertIn("schema_drift", drift.detail)

    def test_derived_coverage_report_warns_when_price_data_is_newer(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            coverage = root / "data" / "reports" / "monthly_universe_price_coverage.csv"
            _write_csv(
                coverage,
                [
                    "date",
                    "universe_symbols",
                    "price_symbols",
                    "covered_symbols",
                    "missing_symbols",
                    "coverage_pct",
                    "status",
                    "missing_preview",
                ],
                [],
            )
            price_file = root / "data" / "krx_expanded" / "005930.csv"
            _write_csv(price_file, ["date", "open", "high", "low", "close", "volume"], [])
            universe_file = root / "data" / "krx_metadata" / "krx_universe_monthly.csv"
            _write_csv(universe_file, ["date", "symbol", "name", "market"], [])
            report_timestamp = datetime(2026, 6, 21, 9, 0, tzinfo=timezone.utc).timestamp()
            input_timestamp = datetime(2026, 6, 21, 11, 0, tzinfo=timezone.utc).timestamp()
            os.utime(coverage, (report_timestamp, report_timestamp))
            os.utime(price_file, (input_timestamp, input_timestamp))
            os.utime(universe_file, (report_timestamp, report_timestamp))

            report = evaluate_health(root=root, as_of=AS_OF, max_report_age_hours=48)

        stale = [check for check in report.checks if check.name == "monthly_universe_price_coverage_inputs"][0]
        self.assertEqual(report.status, "WARN")
        self.assertEqual(stale.status, "WARN")
        self.assertIn("input_newer_than_report", stale.detail)
        self.assertIn("Regenerate monthly_universe_price_coverage.csv", stale.suggested_action)

    def test_health_outputs_write_json_and_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_required_health_files(root)
            report = evaluate_health(root=root, as_of=AS_OF)
            json_path = root / "data" / "reports" / "health_status.json"
            md_path = root / "data" / "reports" / "health_status.md"

            save_health_json(report, json_path)
            save_health_markdown(report, md_path)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")

        self.assertEqual(payload["status"], "PASS")
        self.assertIn("suggested_action", payload["checks"][0])
        self.assertIn("Health Status", markdown)
        self.assertIn("Suggested Action", markdown)


def _write_required_health_files(root: Path) -> None:
    reports = root / "data" / "reports"
    reports.mkdir(parents=True)
    _write_csv(
        reports / "monthly_order_plan.csv",
        [
            "as_of_date",
            "symbol",
            "action",
            "quantity",
            "reference_price",
            "estimated_value",
            "target_weight",
            "current_quantity",
            "reason",
            "adv_20d",
            "adv_participation_rate",
            "liquidity_status",
            "liquidity_reason",
            "estimated_slippage_rate",
            "estimated_total_cost",
            "execution_allowed",
            "execution_mode",
            "execution_block_reason",
            "risk_status",
            "risk_reasons",
        ],
        [],
    )
    _write_csv(reports / "production_readiness.csv", ["name", "status", "detail"], [])
    _write_csv(reports / "data_quality_excluded_symbols.csv", ["symbol", "status", "reason"], [])
    _write_csv(
        reports / "krx_missing_ohlcv_fetch_summary.csv",
        [
            "status",
            "attempted_batches",
            "completed_batches",
            "timed_out_batches",
            "failed_batches",
            "saved",
            "remaining_targets",
            "command_count",
            "last_stdout_tail",
            "last_stderr_tail",
        ],
        [],
    )
    scalper = root / "data" / "scalper"
    scalper.mkdir(parents=True)
    _write_csv(scalper / "AAPL_2026-06-21_paper_scalp.csv", ["timestamp", "symbol", "last_price"], [])


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
