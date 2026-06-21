import unittest

from backtester.models import Candle
from backtester.regime import classify_regime
from backtester.strategies import RegimeSwitchingStrategy


def candles_from_closes(closes: list[float]) -> list[Candle]:
    return [
        Candle(f"2026-01-{index + 1:02d}", close, close * 1.01, close * 0.99, close, 1000 + index)
        for index, close in enumerate(closes)
    ]


class RegimeRouterTests(unittest.TestCase):
    def test_classify_regime_detects_uptrend(self):
        candles = candles_from_closes([100 + i for i in range(80)])

        self.assertEqual(classify_regime(candles, len(candles) - 1), "uptrend")

    def test_classify_regime_detects_crash(self):
        candles = candles_from_closes([100] * 60 + [98, 95, 92, 88, 84, 80])

        self.assertEqual(classify_regime(candles, len(candles) - 1), "crash")

    def test_regime_switching_strategy_returns_valid_signal(self):
        candles = candles_from_closes([100 + i for i in range(80)])
        strategy = RegimeSwitchingStrategy()

        signal = strategy.on_candle(len(candles) - 1, candles, None)

        self.assertIn(signal, {"BUY", "SELL", "HOLD"})


if __name__ == "__main__":
    unittest.main()
