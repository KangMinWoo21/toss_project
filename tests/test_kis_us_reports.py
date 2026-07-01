import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.kis_us.models import KisUsPlannedOrder
from backtester.kis_us.reports import KIS_US_ORDER_COLUMNS, save_kis_us_order_plan, save_kis_us_order_summary


class KisUsReportsTests(unittest.TestCase):
    def test_saves_csv_schema_and_markdown_safety_language(self):
        order = KisUsPlannedOrder(
            plan_id="kis-us-20260701",
            as_of="2026-07-01",
            symbol="AAPL",
            exchange="NAS",
            side="BUY",
            quantity=1,
            current_quantity=0,
            target_weight=0.1,
            current_weight=0.0,
            reference_price=100.0,
            estimated_value=100.0,
            risk_status="PASS",
            risk_reasons="dry_run_only",
            execution_allowed=False,
            created_at="2026-07-01T09:00:00+09:00",
        )
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "plan.csv"
            md_path = Path(temp_dir) / "plan.md"
            save_kis_us_order_plan([order], csv_path)
            save_kis_us_order_summary([order], md_path, as_of="2026-07-01", cash_usd=1000.0)

            with csv_path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            markdown = md_path.read_text(encoding="utf-8")

        self.assertEqual(list(rows[0].keys()), KIS_US_ORDER_COLUMNS)
        self.assertEqual(rows[0]["paper_only"], "True")
        self.assertEqual(rows[0]["dry_run"], "True")
        self.assertEqual(rows[0]["execution_allowed"], "False")
        self.assertEqual(rows[0]["production_effect"], "none")
        self.assertIn("paper-only", markdown)
        self.assertIn("dry-run", markdown)
        self.assertIn("no order submitted", markdown)


if __name__ == "__main__":
    unittest.main()
