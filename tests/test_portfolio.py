import unittest

from backtester.portfolio import (
    PortfolioPosition,
    calculate_current_weights,
    cap_target_allocations,
    generate_rebalance_orders,
)


class PortfolioTests(unittest.TestCase):
    def test_calculate_current_weights_includes_cash(self):
        weights = calculate_current_weights(
            positions=[PortfolioPosition("005930", 2)],
            prices={"005930": 50_000},
            cash=100_000,
        )

        self.assertAlmostEqual(weights["005930"], 0.5)
        self.assertAlmostEqual(weights["CASH"], 0.5)

    def test_cap_target_allocations_limits_single_position_and_reserves_cash(self):
        capped = cap_target_allocations(
            {"005930": 0.6, "000660": 0.3},
            max_position_weight=0.4,
            cash_buffer_weight=0.1,
        )

        self.assertAlmostEqual(capped["005930"], 0.4)
        self.assertAlmostEqual(capped["000660"], 0.3)
        self.assertLessEqual(sum(capped.values()), 0.9)

    def test_generate_rebalance_orders_filters_small_orders(self):
        orders = generate_rebalance_orders(
            positions=[PortfolioPosition("005930", 1)],
            prices={"005930": 50_000, "000660": 100_000},
            cash=150_000,
            target_weights={"005930": 0.25, "000660": 0.5},
            min_order_amount=60_000,
        )

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].symbol, "000660")
        self.assertEqual(orders[0].side, "BUY")
        self.assertEqual(orders[0].estimated_quantity, 1)


if __name__ == "__main__":
    unittest.main()
