import unittest

from backtester.models import Candle
from backtester.strategies import MinuteScalpingStrategy, OpeningRangeBreakoutStrategy, VwapTrendStrategy


class IntradayStrategyTests(unittest.TestCase):
    def test_opening_range_breakout_buys_after_range_break(self):
        candles = [
            Candle("2026-06-09T09:00:00+09:00", 100, 101, 99, 100, 1000),
            Candle("2026-06-09T09:01:00+09:00", 100, 102, 99, 101, 1000),
            Candle("2026-06-09T09:02:00+09:00", 101, 103, 100, 102, 1000),
            Candle("2026-06-09T09:03:00+09:00", 102, 106, 102, 105, 2000),
        ]
        strategy = OpeningRangeBreakoutStrategy(range_bars=3)

        self.assertEqual(strategy.on_candle(3, candles, None), "BUY")

    def test_vwap_trend_buys_when_price_reclaims_vwap_with_volume(self):
        candles = [
            Candle("2026-06-09T09:00:00+09:00", 100, 101, 99, 100, 1000),
            Candle("2026-06-09T09:01:00+09:00", 100, 101, 98, 99, 1000),
            Candle("2026-06-09T09:02:00+09:00", 99, 103, 99, 102, 4000),
        ]
        strategy = VwapTrendStrategy(volume_multiplier=1.5)

        self.assertEqual(strategy.on_candle(2, candles, None), "BUY")

    def test_minute_scalping_buys_on_volume_spike_and_breakout(self):
        candles = [
            Candle("2026-06-09T09:00:00+09:00", 100, 101, 99, 100, 1000),
            Candle("2026-06-09T09:01:00+09:00", 100, 101, 99, 100, 1000),
            Candle("2026-06-09T09:02:00+09:00", 100, 101, 99, 100, 1000),
            Candle("2026-06-09T09:03:00+09:00", 101, 105, 101, 104, 6000),
        ]
        strategy = MinuteScalpingStrategy(volume_window=3, volume_spike_multiplier=3.0)

        self.assertEqual(strategy.on_candle(3, candles, None), "BUY")


if __name__ == "__main__":
    unittest.main()
