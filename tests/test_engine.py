import csv
import tempfile
import unittest
from pathlib import Path

from backtester.data import load_candles
from backtester.engine import BacktestConfig, Backtester, Trade
from backtester.models import Candle
from backtester.strategies import BuyAndHoldStrategy, MarketRegimeEnsembleStrategy, MovingAverageCrossStrategy


class BacktesterEngineTests(unittest.TestCase):
    def test_load_candles_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candles.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "open", "high", "low", "close", "volume"])
                writer.writerow(["2026-01-02", "100", "110", "90", "105", "1000"])

            candles = load_candles(path)

        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].date, "2026-01-02")
        self.assertEqual(candles[0].close, 105.0)
        self.assertEqual(candles[0].volume, 1000)

    def test_buy_and_hold_creates_trade_and_profit(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        result = Backtester(
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0)
        ).run(candles, BuyAndHoldStrategy())

        self.assertEqual(len(result.trades), 1)
        self.assertGreater(result.final_equity, result.initial_cash)
        self.assertGreater(result.total_return_pct, 0)
        self.assertEqual(result.trades[0].side, "SELL")
        self.assertGreater(result.trades[0].pnl, 0)
        self.assertEqual(result.win_rate_pct, 100.0)

    def test_backtester_executes_signal_on_next_open(self):
        class FirstDaySignalStrategy:
            name = "first_day_signal"

            def on_candle(self, index, candles, position):
                if index == 0 and position is None:
                    return "BUY"
                return "HOLD"

        candles = [
            Candle("2026-01-02", 100, 100, 100, 100, 1000),
            Candle("2026-01-05", 150, 150, 150, 150, 1000),
        ]

        result = Backtester(
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0)
        ).run(candles, FirstDaySignalStrategy())

        self.assertAlmostEqual(result.final_equity, 1_000_000)
        self.assertEqual(result.trades[0].entry_price, 150)

    def test_moving_average_strategy_does_not_look_ahead(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        strategy = MovingAverageCrossStrategy(short_window=3, long_window=5)

        signals = [strategy.on_candle(i, candles, None) for i in range(len(candles))]

        self.assertTrue(all(signal == "HOLD" for signal in signals[:4]))
        self.assertIn("BUY", signals)

    def test_mdd_is_negative_when_equity_falls_after_peak(self):
        trades = [
            Trade(
                date="2026-01-03",
                side="SELL",
                price=90.0,
                quantity=10,
                cash_after=900.0,
                equity_after=900.0,
                reason="test",
            )
        ]
        result = Backtester.build_result(
            initial_cash=1_000.0,
            final_cash=900.0,
            final_position=0,
            final_price=90.0,
            equity_curve=[1_000.0, 1_100.0, 900.0],
            trades=trades,
        )

        self.assertAlmostEqual(result.max_drawdown_pct, -18.1818, places=3)
        self.assertLess(result.calmar_ratio, 0)

    def test_result_includes_risk_adjusted_metrics(self):
        result = Backtester.build_result(
            initial_cash=1_000.0,
            final_cash=1_300.0,
            final_position=0,
            final_price=130.0,
            equity_curve=[1_000.0, 1_050.0, 1_020.0, 1_300.0],
            trades=[],
        )

        self.assertNotEqual(result.sharpe_ratio, 0.0)
        self.assertGreater(result.calmar_ratio, 0.0)

    def test_market_regime_ensemble_can_generate_buy_signal_after_warmup(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        strategy = MarketRegimeEnsembleStrategy(trend_window=5, breakout_k=0.3, rsi_window=3)

        signals = [strategy.on_candle(i, candles, None) for i in range(len(candles))]

        self.assertIn("BUY", signals)


if __name__ == "__main__":
    unittest.main()
