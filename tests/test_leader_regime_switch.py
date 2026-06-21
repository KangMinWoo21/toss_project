import unittest
from datetime import date, timedelta

from backtester.leader_regime_switch import (
    LeaderRegimeSwitchConfig,
    classify_leader_market_regime,
    run_regime_switching_leader_backtest,
)
from backtester.leader_swing import LeaderSwingConfig
from backtester.models import Candle


def _candles(closes: list[float], volume: int = 10000) -> list[Candle]:
    start = date(2024, 1, 1)
    rows: list[Candle] = []
    for index, close in enumerate(closes):
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=volume,
            )
        )
    return rows


class LeaderRegimeSwitchTests(unittest.TestCase):
    def test_classifies_bull_market_from_past_return_and_breadth(self):
        symbol_candles = {
            "111111": _candles([100 + index for index in range(40)]),
            "222222": _candles([100 + index * 0.8 for index in range(40)]),
        }
        index_by_symbol_date = {
            symbol: {candle.date: index for index, candle in enumerate(candles)}
            for symbol, candles in symbol_candles.items()
        }
        current_date = symbol_candles["111111"][-1].date

        regime = classify_leader_market_regime(
            current_date,
            symbol_candles,
            index_by_symbol_date,
            LeaderRegimeSwitchConfig(regime_window=20, bull_return_threshold_pct=10, bull_breadth_threshold=0.5),
        )

        self.assertEqual(regime, "bull")

    def test_classifies_defensive_market_when_breadth_is_weak(self):
        symbol_candles = {
            "111111": _candles([100 + index for index in range(40)]),
            "222222": _candles([140 - index for index in range(40)]),
        }
        index_by_symbol_date = {
            symbol: {candle.date: index for index, candle in enumerate(candles)}
            for symbol, candles in symbol_candles.items()
        }
        current_date = symbol_candles["111111"][-1].date

        regime = classify_leader_market_regime(
            current_date,
            symbol_candles,
            index_by_symbol_date,
            LeaderRegimeSwitchConfig(regime_window=20, bull_return_threshold_pct=5, bull_breadth_threshold=0.75),
        )

        self.assertEqual(regime, "defensive")

    def test_regime_switching_backtest_returns_mode_counts(self):
        symbol_candles = {
            "111111": _candles([100 + index * 2 for index in range(50)], volume=20000),
            "222222": _candles([100 + index for index in range(50)], volume=15000),
        }

        result = run_regime_switching_leader_backtest(
            symbol_candles,
            LeaderRegimeSwitchConfig(
                regime_window=10,
                bull_return_threshold_pct=5,
                bull_breadth_threshold=0.5,
                defensive=LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    max_positions=1,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0,
                    tax_rate=0,
                    slippage_rate=0,
                ),
                bullish=LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    max_positions=2,
                    max_holding_days=20,
                    initial_cash=1_000_000,
                    fee_rate=0,
                    tax_rate=0,
                    slippage_rate=0,
                ),
            ),
        )

        self.assertGreater(result.mode_counts["bull"], 0)
        self.assertGreater(result.result.total_return_pct, 0)


if __name__ == "__main__":
    unittest.main()
