import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.execution_plan import OrderPlanRow, load_order_plan, save_order_plan_rows


class ExecutionPlanTests(unittest.TestCase):
    def test_save_and_load_order_plan_rows_with_risk_fields(self):
        row = OrderPlanRow(
            plan_id="plan-20260620",
            rebalance_date="2026-06-20",
            symbol="005930",
            side="BUY",
            current_weight=0.0,
            target_weight=0.1,
            target_amount=100_000,
            estimated_quantity=2,
            reference_price=50_000,
            reason="monthly_rebalance",
            risk_status="BLOCKED",
            risk_reasons="production_trading_disabled",
            created_at="2026-06-20T09:00:00+09:00",
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.csv"
            saved = save_order_plan_rows([row], path)
            loaded = load_order_plan(path)

        self.assertEqual(saved, 1)
        self.assertEqual(loaded, [row])

    def test_order_plan_writer_includes_required_schema(self):
        row = OrderPlanRow(
            plan_id="p1",
            rebalance_date="2026-06-20",
            symbol="000660",
            side="SELL",
            current_weight=0.2,
            target_weight=0.1,
            target_amount=50_000,
            estimated_quantity=1,
            reference_price=50_000,
            reason="trim",
            risk_status="PASS",
            risk_reasons="",
            created_at="2026-06-20T09:00:00+09:00",
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.csv"
            save_order_plan_rows([row], path)
            with path.open(newline="", encoding="utf-8-sig") as f:
                fieldnames = next(csv.DictReader(f)).keys()

        self.assertIn("plan_id", fieldnames)
        self.assertIn("risk_status", fieldnames)
        self.assertIn("risk_reasons", fieldnames)


if __name__ == "__main__":
    unittest.main()
