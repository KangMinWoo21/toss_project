import csv
import json
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.operation_health import (
    build_operation_health_rows,
    save_operation_health_reports,
)


class AutoTradingOperationHealthTests(unittest.TestCase):
    def test_operation_health_passes_complete_safe_paper_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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
            auto_order = root / "auto_order.csv"
            auto_order.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            kis_targets = root / "kis_targets.csv"
            kis_targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            kis_plan = root / "kis_plan.csv"
            kis_plan.write_text(
                "symbol,side,risk_status,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,BUY,PASS,True,True,False,none\n",
                encoding="utf-8",
            )

            rows = build_operation_health_rows(
                audit_log_path=audit,
                auto_order_plan_path=auto_order,
                kis_targets_path=kis_targets,
                kis_order_plan_path=kis_plan,
            )

            self.assertTrue(rows)
            self.assertTrue(all(row["status"] == "PASS" for row in rows))
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["dry_run"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in rows))
            self.assertIn("objective_complete", {row["check"] for row in rows})
            self.assertIn("kis_order_plan_safe", {row["check"] for row in rows})

    def test_operation_health_blocks_unsafe_execution_or_not_complete_objective(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "REVIEW",
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            auto_order = root / "auto_order.csv"
            auto_order.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,True,none\n",
                encoding="utf-8",
            )
            kis_targets = root / "kis_targets.csv"
            kis_targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            kis_plan = root / "kis_plan.csv"
            kis_plan.write_text(
                "symbol,side,risk_status,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,BUY,PASS,True,False,False,none\n",
                encoding="utf-8",
            )

            rows = build_operation_health_rows(
                audit_log_path=audit,
                auto_order_plan_path=auto_order,
                kis_targets_path=kis_targets,
                kis_order_plan_path=kis_plan,
            )

            blocked = {row["check"] for row in rows if row["status"] == "BLOCK"}
            self.assertIn("objective_complete", blocked)
            self.assertIn("auto_order_plan_safe", blocked)
            self.assertIn("kis_order_plan_safe", blocked)

    def test_save_operation_health_reports_writes_csv_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {
                    "check": "objective_complete",
                    "status": "PASS",
                    "detail": "ok",
                    "paper_only": "True",
                    "dry_run": "True",
                    "execution_allowed": "False",
                    "production_effect": "none",
                }
            ]
            csv_path = root / "health.csv"
            md_path = root / "health.md"

            save_operation_health_reports(rows, csv_path, md_path)

            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["check"], "objective_complete")
            self.assertEqual(written[0]["execution_allowed"], "False")
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("paper-only", text)
            self.assertIn("objective_complete", text)


if __name__ == "__main__":
    unittest.main()
