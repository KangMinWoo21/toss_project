import csv
import math
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.leader_swing import load_symbol_candles
from backtester.models import Candle
from backtester.momentum_rotation import (
    MomentumRotationConfig,
    momentum_rotation_config_for_preset,
    rank_momentum_targets,
    run_momentum_rotation_backtest,
)


def _candles(
    closes: list[float],
    opens: list[float] | None = None,
    volume: int = 10000,
    start_offset_days: int = 0,
) -> list[Candle]:
    start = date(2024, 1, 1) + timedelta(days=start_offset_days)
    open_values = opens or closes
    rows: list[Candle] = []
    for index, close in enumerate(closes):
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=open_values[index],
                high=max(open_values[index], close) + 1,
                low=min(open_values[index], close) - 1,
                close=close,
                volume=volume,
            )
        )
    return rows


def _write_symbol(path: Path, closes: list[float], volume: int = 10000) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for index, close in enumerate(closes):
            row_date = date(2024, 1, 1) + timedelta(days=index)
            writer.writerow([row_date.isoformat(), close, close + 1, close - 1, close, volume])


class MomentumRotationTests(unittest.TestCase):
    def test_default_config_uses_validated_diversified_breadth_profile(self):
        config = MomentumRotationConfig()

        self.assertEqual(config.lookback_days, 180)
        self.assertEqual(config.rebalance_days, 40)
        self.assertEqual(config.top_n, 5)
        self.assertEqual(config.trend_filter_days, 120)
        self.assertEqual(config.market_trend_filter_days, 180)
        self.assertEqual(config.market_breadth_threshold, 0.4)
        self.assertEqual(config.bull_breadth_threshold, 0.5)
        self.assertEqual(config.bull_top_n, 5)
        self.assertEqual(config.bull_trend_filter_days, 60)

    def test_aggressive_preset_uses_faster_trend_profile(self):
        config = momentum_rotation_config_for_preset("aggressive")

        self.assertEqual(config.top_n, 3)
        self.assertEqual(config.trend_filter_days, 60)
        self.assertEqual(config.market_trend_filter_days, 180)
        self.assertEqual(config.market_breadth_threshold, 0.4)
        self.assertEqual(config.bull_breadth_threshold, 0.8)
        self.assertEqual(config.bull_top_n, 5)
        self.assertEqual(config.bull_trend_filter_days, 60)

    def test_retail_preset_adds_capacity_controls_for_smaller_universes(self):
        config = momentum_rotation_config_for_preset("retail")

        self.assertEqual(config.top_n, 3)
        self.assertEqual(config.trend_filter_days, 60)
        self.assertEqual(config.min_average_trading_value, 300_000_000)
        self.assertEqual(config.max_trade_participation_rate, 0.005)

    def test_buys_strongest_previous_close_momentum_symbol(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 100, 100, 130, 131]),
                "222222": _candles([100, 101, 102, 103, 104]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "111111")

    def test_does_not_use_current_day_close_for_entry_signal(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 100, 100, 110, 111]),
                "222222": _candles([100, 100, 100, 100, 300], opens=[100, 100, 100, 100, 100]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "111111")

    def test_trend_filter_excludes_momentum_symbol_below_moving_average(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 220, 200, 150, 151]),
                "222222": _candles([100, 110, 115, 120, 121]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=3,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "222222")

    def test_market_breadth_filter_blocks_entries_when_too_few_symbols_are_in_uptrends(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 90, 80, 70, 71]),
                "222222": _candles([100, 110, 120, 130, 131]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=3,
                market_breadth_threshold=1.0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertEqual(result.trade_count, 0)

    def test_liquidity_filter_excludes_thinly_traded_momentum_symbol(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 100, 100, 130, 131], volume=10),
                "222222": _candles([100, 101, 102, 103, 104], volume=10000),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                liquidity_window_days=2,
                min_average_trading_value=500_000,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "222222")

    def test_trade_participation_cap_limits_buy_size_for_retail_capacity_checks(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 100, 100, 130, 131], volume=1000),
                "222222": _candles([100, 101, 102, 103, 104], volume=1000),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                liquidity_window_days=2,
                max_trade_participation_rate=0.1,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertLessEqual(first_buy.quantity, 100)

    def test_bull_profile_uses_relaxed_trend_filter_when_market_breadth_is_strong(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 220, 200, 150, 151]),
                "222222": _candles([100, 110, 120, 130, 131]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=3,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=3,
                market_trend_filter_days=2,
                market_breadth_threshold=0.5,
                bull_breadth_threshold=0.5,
                bull_top_n=1,
                bull_trend_filter_days=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "111111")

    def test_reports_buy_hold_and_excess_return(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 105, 110, 120, 130]),
                "222222": _candles([100, 98, 96, 94, 92]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=2,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertAlmostEqual(result.excess_return_pct, result.total_return_pct - result.buy_hold_return_pct)
        self.assertGreater(result.trade_count, 0)

    def test_trades_existing_symbols_before_later_listed_symbols_have_history(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 105, 110, 120, 130]),
                "222222": _candles([50, 51], start_offset_days=3),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=2,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        first_buy = next(trade for trade in result.trades if trade.action == "BUY")
        self.assertEqual(first_buy.symbol, "111111")

    def test_buy_hold_ignores_untradeable_zero_open_first_candle(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 110, 120], opens=[0, 100, 110]),
                "222222": _candles([100, 101, 102]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=1,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertTrue(math.isfinite(result.buy_hold_return_pct))

    def test_skips_entry_when_trade_open_is_zero(self):
        result = run_momentum_rotation_backtest(
            {
                "111111": _candles([100, 100, 130, 131], opens=[100, 100, 100, 0]),
                "222222": _candles([100, 100, 101, 102]),
            },
            MomentumRotationConfig(
                initial_cash=1_000_000,
                lookback_days=2,
                rebalance_days=1,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertNotIn("111111", [trade.symbol for trade in result.trades if trade.action == "BUY"])

    def test_rank_momentum_targets_uses_signal_date_not_later_future(self):
        targets = rank_momentum_targets(
            {
                "111111": _candles([100, 100, 130, 131, 132]),
                "222222": _candles([100, 100, 100, 100, 300]),
            },
            signal_date="2024-01-04",
            config=MomentumRotationConfig(
                lookback_days=2,
                top_n=1,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertEqual(targets, ["111111"])

    def test_rank_momentum_targets_excludes_overextended_lookback_return(self):
        targets = rank_momentum_targets(
            {
                "OVER": _candles([100, 100, 500, 500]),
                "STEADY": _candles([100, 100, 170, 170]),
            },
            signal_date="2024-01-04",
            config=MomentumRotationConfig(
                lookback_days=2,
                top_n=2,
                trend_filter_days=0,
                market_trend_filter_days=0,
                market_breadth_threshold=0,
                max_lookback_return_pct=200,
                fee_rate=0,
                tax_rate=0,
                slippage_rate=0,
            ),
        )

        self.assertEqual(targets, ["STEADY"])

    def test_cli_momentum_rotation_prints_summary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100, 105, 110, 120, 130])
            _write_symbol(root / "222222_2018_2026.csv", [100, 98, 96, 94, 92])
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "momentum-rotation",
                    "--data-dir",
                    temp_dir,
                    "--lookback-days",
                    "2",
                    "--rebalance-days",
                    "1",
                    "--top-n",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Momentum rotation summary", completed.stdout)
        self.assertIn("excess_%", completed.stdout)


if __name__ == "__main__":
    unittest.main()
