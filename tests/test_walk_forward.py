import unittest
from pathlib import Path

from backtester.analysis import filter_candles, summarize_walk_forward, walk_forward
from backtester.data import load_candles
from backtester.engine import BacktestConfig
from backtester.strategies import BuyAndHoldStrategy, VolatilityBreakoutStrategy


class WalkForwardTests(unittest.TestCase):
    def test_filter_candles_by_date_range(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))

        filtered = filter_candles(candles, start="2026-01-04", end="2026-01-06")

        self.assertEqual([c.date for c in filtered], ["2026-01-04", "2026-01-05", "2026-01-06"])

    def test_walk_forward_selects_train_winner_and_tests_next_period(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        windows = [
            ("2026-01-02", "2026-01-08", "2026-01-09", "2026-01-12"),
            ("2026-01-06", "2026-01-12", "2026-01-13", "2026-01-16"),
        ]

        results = walk_forward(
            candles=candles,
            strategies=[BuyAndHoldStrategy(), VolatilityBreakoutStrategy()],
            windows=windows,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
        )

        self.assertEqual(len(results), 2)
        self.assertIn(results[0].best_strategy, {"buy_and_hold", "volatility_breakout"})
        self.assertEqual(results[0].test_start, "2026-01-09")
        self.assertGreater(results[0].train_return_pct, 0)

    def test_summarize_walk_forward_ranks_by_test_return(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        windows = [
            ("2026-01-02", "2026-01-08", "2026-01-09", "2026-01-12"),
            ("2026-01-06", "2026-01-12", "2026-01-13", "2026-01-16"),
        ]
        results = walk_forward(
            candles=candles,
            strategies=[BuyAndHoldStrategy(), VolatilityBreakoutStrategy()],
            windows=windows,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
        )

        summary = summarize_walk_forward(results)

        self.assertGreaterEqual(summary[0].average_test_return_pct, summary[-1].average_test_return_pct)
        self.assertGreater(summary[0].window_count, 0)


if __name__ == "__main__":
    unittest.main()
