import unittest
from pathlib import Path

from backtester.engine import BacktestConfig
from backtester.strategies import BuyAndHoldStrategy, MovingAverageCrossStrategy
from backtester.study import run_market_regime_study


class MarketRegimeStudyTests(unittest.TestCase):
    def test_run_market_regime_study_groups_up_and_down_windows(self):
        rows = run_market_regime_study(
            data_files=[
                Path("data/sample_kr_stock.csv"),
                Path("data/sample_kr_stock_downtrend.csv"),
            ],
            strategies=[BuyAndHoldStrategy(), MovingAverageCrossStrategy()],
            train_size=7,
            test_size=4,
            step_size=4,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
        )

        regimes = {row.regime for row in rows}
        self.assertIn("up", regimes)
        self.assertIn("down", regimes)
        self.assertTrue(any(row.strategy_name == "buy_and_hold" for row in rows))


if __name__ == "__main__":
    unittest.main()
