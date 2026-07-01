import csv
import json
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.kis_bridge import export_kis_targets_from_auto_paper


class AutoTradingKisBridgeTests(unittest.TestCase):
    def test_exports_complete_auto_paper_plan_to_kis_target_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            order_plan = root / "auto_paper_order_plan.csv"
            order_plan.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,False,none\n"
                "TSLA,0.00,True,True,False,none\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,exchange\n"
                "AAPL,Apple Inc,EQUITY,2015-01-01,,fixture,true,current universe,NAS\n"
                "TSLA,Tesla Inc,EQUITY,2015-01-01,,fixture,true,current universe,NAS\n",
                encoding="utf-8",
            )
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "objective_status": "COMPLETE",
                        "best_model": "model_x",
                        "benchmark_report_sha256": "a" * 64,
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            output = root / "kis_targets.csv"

            rows = export_kis_targets_from_auto_paper(
                auto_order_plan_path=order_plan,
                universe_path=universe,
                audit_log_path=audit,
                output_path=output,
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "AAPL")
            self.assertEqual(rows[0]["exchange"], "NAS")
            self.assertEqual(rows[0]["target_weight"], "0.100000")
            self.assertEqual(rows[0]["source_model"], "model_x")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            with output.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written, rows)

    def test_fails_closed_when_objective_not_complete_or_auto_row_not_paper_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            order_plan = root / "auto_paper_order_plan.csv"
            order_plan.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,exchange\n"
                "AAPL,Apple Inc,EQUITY,2015-01-01,,fixture,true,current universe,NAS\n",
                encoding="utf-8",
            )
            audit = root / "audit.json"
            audit.write_text(json.dumps({"objective_status": "REVIEW"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                export_kis_targets_from_auto_paper(
                    auto_order_plan_path=order_plan,
                    universe_path=universe,
                    audit_log_path=audit,
                    output_path=root / "out.csv",
                )

            audit.write_text(json.dumps({"objective_status": "COMPLETE"}), encoding="utf-8")
            order_plan.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,True,none\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                export_kis_targets_from_auto_paper(
                    auto_order_plan_path=order_plan,
                    universe_path=universe,
                    audit_log_path=audit,
                    output_path=root / "out.csv",
                )


if __name__ == "__main__":
    unittest.main()
