import unittest

from backtester.monthly.paper_orders import mark_order_plan_execution, normalize_liquidity_status
from backtester.monthly_rebalance import PlannedOrder


class MonthlyPaperOrderHelperTests(unittest.TestCase):
    def test_normalize_liquidity_status_allows_only_known_non_block_states(self) -> None:
        self.assertEqual(normalize_liquidity_status("pass"), "PASS")
        self.assertEqual(normalize_liquidity_status(" warn "), "WARN")
        self.assertEqual(normalize_liquidity_status("NOT_CHECKED"), "NOT_CHECKED")
        self.assertEqual(normalize_liquidity_status("unknown"), "BLOCK")

    def test_mark_order_plan_execution_blocks_when_production_trading_disabled(self) -> None:
        order = PlannedOrder(
            as_of_date="2026-06-30",
            symbol="005930",
            action="BUY",
            quantity=10,
            reference_price=70000.0,
            estimated_value=700000.0,
            target_weight=0.1,
            current_quantity=0,
            reason="selected_monthly_alpha",
        )

        [marked] = mark_order_plan_execution(
            [order],
            risk_status_value="PASS",
            production_trading_enabled=False,
        )

        self.assertFalse(marked.execution_allowed)
        self.assertEqual(marked.execution_mode, "blocked")
        self.assertEqual(marked.execution_block_reason, "production_trading_disabled")
        self.assertEqual(marked.risk_status, "BLOCKED")

    def test_mark_order_plan_execution_allows_live_ready_only_when_enabled_and_passed(self) -> None:
        order = PlannedOrder(
            as_of_date="2026-06-30",
            symbol="005930",
            action="SELL",
            quantity=5,
            reference_price=70000.0,
            estimated_value=350000.0,
            target_weight=0.0,
            current_quantity=5,
            reason="selected_monthly_alpha",
        )

        [marked] = mark_order_plan_execution(
            [order],
            risk_status_value="PASS",
            production_trading_enabled=True,
        )

        self.assertTrue(marked.execution_allowed)
        self.assertEqual(marked.execution_mode, "live_ready")
        self.assertEqual(marked.execution_block_reason, "")
        self.assertEqual(marked.risk_status, "PASS")


if __name__ == "__main__":
    unittest.main()
