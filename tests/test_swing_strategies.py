import unittest

from backtester.models import Candle
from backtester.strategies import (
    BollingerMeanReversionStrategy,
    CompositeSwingStrategy,
    DonchianAtrBreakoutStrategy,
    MacdRsiTrendStrategy,
    TimeSeriesMomentumStrategy,
    available_strategies,
    get_strategy,
)


def _candles(closes: list[float]) -> list[Candle]:
    return [
        Candle(
            date=f"2026-01-{index + 1:02d}",
            open=close - 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1000 + index * 10,
        )
        for index, close in enumerate(closes)
    ]


class SwingStrategyTests(unittest.TestCase):
    def test_time_series_momentum_buys_when_lookback_return_is_positive(self):
        candles = _candles([100, 101, 102, 103, 105, 108])
        strategy = TimeSeriesMomentumStrategy(lookback=3, min_return_pct=2.0)

        self.assertEqual(strategy.on_candle(5, candles, position=None), "BUY")

    def test_bollinger_mean_reversion_buys_deep_pullback(self):
        candles = _candles([100, 101, 102, 103, 104, 105, 106, 92])
        strategy = BollingerMeanReversionStrategy(window=5, stdev_multiplier=1.0, rsi_window=3, rsi_buy_below=35)

        self.assertEqual(strategy.on_candle(7, candles, position=None), "BUY")

    def test_donchian_atr_breakout_buys_new_high(self):
        candles = _candles([100, 101, 102, 103, 104, 108])
        strategy = DonchianAtrBreakoutStrategy(entry_window=3, atr_window=3)

        self.assertEqual(strategy.on_candle(5, candles, position=None), "BUY")

    def test_macd_rsi_trend_can_buy_after_uptrend_warmup(self):
        candles = _candles([100 + index for index in range(40)])
        strategy = MacdRsiTrendStrategy(fast_window=3, slow_window=6, signal_window=3, rsi_window=5)

        signals = [strategy.on_candle(index, candles, position=None) for index in range(len(candles))]

        self.assertIn("BUY", signals)

    def test_composite_swing_votes_across_multiple_rules(self):
        candles = _candles([100, 101, 102, 103, 104, 106, 108, 111, 115, 119])
        strategy = CompositeSwingStrategy(momentum_lookback=3, trend_window=5, breakout_window=3, rsi_window=3, min_votes=2)

        self.assertEqual(strategy.on_candle(9, candles, position=None), "BUY")

    def test_new_swing_strategies_are_available_by_name(self):
        names = available_strategies()

        self.assertIn("time_series_momentum", names)
        self.assertIn("macd_rsi_trend", names)
        self.assertIsInstance(get_strategy("composite_swing"), CompositeSwingStrategy)


if __name__ == "__main__":
    unittest.main()
