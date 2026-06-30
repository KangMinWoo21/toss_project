import unittest

from backtester.models import Candle
from backtester.monthly.paper_orders import (
    annotate_order_liquidity,
    average_daily_trading_value,
    mark_order_plan_execution,
    normalize_liquidity_status,
)
from backtester.monthly_rebalance import PlannedOrder


class MonthlyPaperOrderHelperTests(unittest.TestCase):
    def test_average_daily_trading_value_uses_recent_valid_history(self) -> None:
        candles = [
            Candle("2026-06-25", 10.0, 11.0, 9.0, 10.0, 100),
            Candle("2026-06-26", 20.0, 21.0, 19.0, 20.0, 200),
            Candle("2026-06-29", 30.0, 31.0, 29.0, 30.0, 300),
            Candle("2026-07-01", 40.0, 41.0, 39.0, 40.0, 400),
        ]

        self.assertEqual(
            average_daily_trading_value(candles, as_of_date="2026-06-30", window_days=2),
            6500.0,
        )
        self.assertEqual(
            average_daily_trading_value(candles, as_of_date="2026-06-30", window_days=5),
            0.0,
        )

    def test_annotate_order_liquidity_marks_warn_when_participation_exceeds_warn_threshold(self) -> None:
        order = PlannedOrder(
            as_of_date="2026-06-30",
            symbol="005930",
            action="BUY",
            quantity=10,
            reference_price=100.0,
            estimated_value=1000.0,
            target_weight=0.1,
            current_quantity=0,
            reason="selected_monthly_alpha",
        )
        candles = [
            Candle("2026-06-26", 100.0, 100.0, 100.0, 100.0, 100),
            Candle("2026-06-29", 100.0, 100.0, 100.0, 100.0, 100),
        ]

        marked = annotate_order_liquidity(
            order,
            candles,
            as_of_date="2026-06-30",
            adv_window_days=2,
            base_slippage_rate=0.001,
            impact_slippage_multiplier=0.1,
            warn_adv_participation_rate=0.05,
            max_adv_participation_rate=0.2,
            liquidity_missing_adv_status="WARN",
        )

        self.assertEqual(marked.adv_20d, 10000.0)
        self.assertEqual(marked.adv_participation_rate, 0.1)
        self.assertEqual(marked.liquidity_status, "WARN")
        self.assertAlmostEqual(marked.estimated_slippage_rate, 0.011)
        self.assertAlmostEqual(marked.estimated_total_cost, 11.0)

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
