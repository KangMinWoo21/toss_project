import csv
import json
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.monitoring import (
    SchedulerMonitoringInputs,
    build_scheduler_monitoring_rows,
    save_scheduler_monitoring_reports,
)


class AutoTradingMonitoringTests(unittest.TestCase):
    def test_scheduler_monitoring_passes_when_all_local_artifacts_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = _write_passing_artifacts(root)

            rows = build_scheduler_monitoring_rows(inputs)

            self.assertTrue(all(row["status"] == "PASS" for row in rows))
            self.assertEqual({row["check"] for row in rows}, {
                "audit_log",
                "external_data_readiness",
                "portfolio_risk_gate",
                "factor_risk",
                "tca_report",
                "operation_health",
            })
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["dry_run"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in rows))

    def test_scheduler_monitoring_blocks_missing_or_failed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = _write_passing_artifacts(root)
            inputs.external_data_readiness.unlink()

            rows = build_scheduler_monitoring_rows(inputs)
            by_check = {row["check"]: row for row in rows}

            self.assertEqual(by_check["external_data_readiness"]["status"], "BLOCK")
            self.assertIn("missing_file", by_check["external_data_readiness"]["reasons"])

            inputs.audit_log.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "NOT_COMPLETE",
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            rows = build_scheduler_monitoring_rows(inputs)
            by_check = {row["check"]: row for row in rows}
            self.assertEqual(by_check["audit_log"]["status"], "BLOCK")
            self.assertIn("objective_status=NOT_COMPLETE", by_check["audit_log"]["observed_status"])

    def test_scheduler_monitoring_writes_csv_and_markdown_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = build_scheduler_monitoring_rows(_write_passing_artifacts(root))
            csv_path = root / "monitoring.csv"
            md_path = root / "monitoring.md"
            save_scheduler_monitoring_reports(rows, csv_path, md_path)

            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["execution_allowed"], "False")
            self.assertIn("Scheduler Monitoring", md_path.read_text(encoding="utf-8"))


def _write_passing_artifacts(root: Path) -> SchedulerMonitoringInputs:
    audit = root / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "engine_status": "SUCCESS",
                "objective_status": "COMPLETE",
                "paper_only": True,
                "dry_run": True,
                "execution_allowed": False,
                "production_effect": "none",
            }
        ),
        encoding="utf-8",
    )
    external = root / "external.csv"
    external.write_text(
        "adapter,status,paper_only,dry_run,execution_allowed,production_effect\n"
        "factors,PASS,True,True,False,none\n",
        encoding="utf-8",
    )
    risk = root / "risk.csv"
    risk.write_text(
        "check,status,paper_only,dry_run,execution_allowed,production_effect\n"
        "single_name_weight,PASS,True,True,False,none\n",
        encoding="utf-8",
    )
    factor = root / "factor.csv"
    factor.write_text(
        "check,status,paper_only,dry_run,execution_allowed,production_effect\n"
        "weighted_beta,PASS,True,True,False,none\n",
        encoding="utf-8",
    )
    tca = root / "tca.csv"
    tca.write_text(
        "symbol,tca_status,paper_only,dry_run,execution_allowed,production_effect\n"
        "AAPL,PASS,True,True,False,none\n",
        encoding="utf-8",
    )
    health = root / "health.csv"
    health.write_text(
        "check,status,detail,paper_only,dry_run,execution_allowed,production_effect\n"
        "objective_complete,PASS,ok,True,True,False,none\n",
        encoding="utf-8",
    )
    return SchedulerMonitoringInputs(
        audit_log=audit,
        external_data_readiness=external,
        portfolio_risk_gate=risk,
        factor_risk=factor,
        tca_report=tca,
        operation_health=health,
    )


if __name__ == "__main__":
    unittest.main()
