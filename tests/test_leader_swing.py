import csv
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.events import EventScoreStore
from backtester.leader_swing import LeaderSwingConfig, load_symbol_candles, run_leader_swing_backtest


def _write_symbol(path: Path, closes: list[float], volume: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for index, close in enumerate(closes):
            row_date = date(2024, 1, 1) + timedelta(days=index)
            writer.writerow(
                [
                    row_date.isoformat(),
                    close,
                    close + 1,
                    close - 1,
                    close,
                    volume,
                ]
            )


def _write_symbol_rows(path: Path, rows: list[tuple[float, float, float, float, int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for index, row in enumerate(rows):
            row_date = date(2024, 1, 1) + timedelta(days=index)
            writer.writerow([row_date.isoformat(), *row])


class LeaderSwingTests(unittest.TestCase):
    def test_load_symbol_candles_reads_symbol_from_filename(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "005930_2018_2026.csv", [100, 101, 102], 1000)

            candles = load_symbol_candles(root)

        self.assertIn("005930", candles)
        self.assertEqual(candles["005930"][0].close, 100)

    def test_load_symbol_candles_strips_plain_csv_extension(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "005930.csv", [100, 101, 102], 1000)

            candles = load_symbol_candles(root)

        self.assertEqual(list(candles), ["005930"])

    def test_leader_swing_prefers_liquid_momentum_leader(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            leader = [100 + index * 2 for index in range(35)]
            illiquid = [100 + index * 3 for index in range(35)]
            laggard = [120 - index for index in range(35)]
            _write_symbol(root / "111111_2018_2026.csv", leader, 10000)
            _write_symbol(root / "222222_2018_2026.csv", illiquid, 10)
            _write_symbol(root / "333333_2018_2026.csv", laggard, 20000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=2,
                    max_positions=1,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertTrue(result.trades)
        self.assertTrue(all(trade.symbol == "111111" for trade in result.trades))
        self.assertGreater(result.total_return_pct, 0)

    def test_leader_swing_enters_on_next_open_after_signal(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                (100, 101, 99, 100, 10000),
                (101, 102, 100, 101, 10000),
                (102, 103, 101, 102, 10000),
                (103, 104, 102, 103, 10000),
                (104, 105, 103, 104, 10000),
                (105, 106, 104, 105, 10000),
                (106, 107, 105, 106, 10000),
                (107, 108, 106, 107, 10000),
                (108, 109, 107, 108, 10000),
                (109, 110, 108, 109, 10000),
                (110, 132, 109, 130, 10000),
                (200, 202, 198, 200, 10000),
            ]
            _write_symbol_rows(root / "111111_2018_2026.csv", rows)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=3,
                    momentum_short=3,
                    momentum_long=5,
                    breakout_window=5,
                    trend_window=5,
                    liquidity_top_n=1,
                    max_positions=1,
                    max_holding_days=20,
                    min_short_return_pct=10.0,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertTrue(result.trades)
        self.assertEqual(result.trades[0].entry_date, "2024-01-12")
        self.assertEqual(result.trades[0].entry_price, 200)

    def test_buy_hold_benchmark_uses_first_open_not_first_close(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                (100, 200, 100, 200, 10000),
                (200, 200, 200, 200, 10000),
            ]
            _write_symbol_rows(root / "111111_2018_2026.csv", rows)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    initial_cash=1_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertEqual(result.buy_hold_return_pct, 100.0)

    def test_buy_hold_benchmark_keeps_cash_when_first_open_is_invalid(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol_rows(
                root / "111111_2018_2026.csv",
                [
                    (0, 0, 0, 100, 10000),
                    (100, 100, 100, 100, 10000),
                ],
            )
            _write_symbol_rows(
                root / "222222_2018_2026.csv",
                [
                    (100, 100, 100, 100, 10000),
                    (200, 200, 200, 200, 10000),
                ],
            )

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    initial_cash=1_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertEqual(result.buy_hold_return_pct, 50.0)

    def test_entry_size_is_capped_by_average_trading_value_participation(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                (100, 101, 99, 100, 100),
                (101, 102, 100, 101, 100),
                (102, 103, 101, 102, 100),
                (103, 104, 102, 103, 100),
                (104, 105, 103, 104, 100),
                (105, 106, 104, 105, 100),
                (106, 107, 105, 106, 100),
                (107, 108, 106, 107, 100),
                (108, 109, 107, 108, 100),
                (109, 110, 108, 109, 100),
                (110, 132, 109, 130, 100),
                (200, 202, 198, 200, 100),
            ]
            _write_symbol_rows(root / "111111_2018_2026.csv", rows)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=3,
                    momentum_short=3,
                    momentum_long=5,
                    breakout_window=5,
                    trend_window=5,
                    liquidity_top_n=1,
                    max_positions=1,
                    max_holding_days=20,
                    min_short_return_pct=10.0,
                    max_position_adv_pct=0.05,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertTrue(result.trades)
        self.assertLessEqual(result.trades[0].quantity, 2)

    def test_entry_size_is_capped_by_per_position_loss_budget(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                (100, 101, 99, 100, 100000),
                (101, 102, 100, 101, 100000),
                (102, 103, 101, 102, 100000),
                (103, 104, 102, 103, 100000),
                (104, 105, 103, 104, 100000),
                (105, 106, 104, 105, 100000),
                (106, 107, 105, 106, 100000),
                (107, 108, 106, 107, 100000),
                (108, 109, 107, 108, 100000),
                (109, 110, 108, 109, 100000),
                (110, 132, 109, 130, 100000),
                (200, 202, 198, 200, 100000),
            ]
            _write_symbol_rows(root / "111111_2018_2026.csv", rows)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=3,
                    momentum_short=3,
                    momentum_long=5,
                    breakout_window=5,
                    trend_window=5,
                    liquidity_top_n=1,
                    max_positions=1,
                    max_holding_days=20,
                    min_short_return_pct=10.0,
                    stop_loss_pct=-10.0,
                    max_loss_per_position_pct=0.5,
                    max_position_adv_pct=1.0,
                    max_position_weight=1.0,
                    cash_buffer_weight=0.0,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertTrue(result.trades)
        self.assertLessEqual(result.trades[0].quantity, 250)

    def test_cli_leader_swing_prints_summary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 2 for index in range(35)], 10000)
            _write_symbol(root / "333333_2018_2026.csv", [120 - index for index in range(35)], 20000)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "leader-swing",
                    "--data-dir",
                    temp_dir,
                    "--liquidity-window",
                    "5",
                    "--momentum-short",
                    "5",
                    "--momentum-long",
                    "10",
                    "--breakout-window",
                    "10",
                    "--trend-window",
                    "10",
                    "--liquidity-top-n",
                    "2",
                    "--max-positions",
                    "1",
                    "--max-holding-days",
                    "5",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Leader swing summary", completed.stdout)
        self.assertIn("total_return_%", completed.stdout)

    def test_cli_leader_regime_prints_summary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 2 for index in range(50)], 10000)
            _write_symbol(root / "333333_2018_2026.csv", [100 + index for index in range(50)], 20000)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "leader-regime",
                    "--data-dir",
                    temp_dir,
                    "--regime-window",
                    "10",
                    "--bull-return-threshold-pct",
                    "5",
                    "--bull-breadth-threshold",
                    "0.5",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Leader regime summary", completed.stdout)
        self.assertIn("bull_days", completed.stdout)

    def test_market_breadth_filter_can_block_new_entries(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 2 for index in range(35)], 10000)
            _write_symbol(root / "333333_2018_2026.csv", [200 - index * 3 for index in range(35)], 20000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    market_filter_window=5,
                    market_breadth_threshold=0.75,
                    liquidity_top_n=2,
                    max_positions=1,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertEqual(result.trade_count, 0)

    def test_symbol_weight_multiplier_allocates_more_to_preferred_symbol(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 2 for index in range(35)], 10000)
            _write_symbol(root / "222222_2018_2026.csv", [100 + index * 2 for index in range(35)], 10000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=2,
                    max_positions=2,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                    symbol_weight_multipliers={"111111": 1.5},
                    max_position_weight=1.0,
                    max_position_adv_pct=1.0,
                    max_loss_per_position_pct=100.0,
                    cash_buffer_weight=0.0,
                ),
            )

        first_entry_date = min(trade.entry_date for trade in result.trades)
        first_trades = {trade.symbol: trade.quantity for trade in result.trades if trade.entry_date == first_entry_date}
        self.assertGreater(first_trades["111111"], first_trades["222222"])

    def test_relative_strength_filter_blocks_market_laggard(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 3 for index in range(35)], 10000)
            _write_symbol(root / "222222_2018_2026.csv", [100 + index for index in range(35)], 10000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=2,
                    max_positions=2,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                    min_relative_long_return_pct=0.0,
                ),
            )

        self.assertTrue(result.trades)
        self.assertTrue(all(trade.symbol == "111111" for trade in result.trades))

    def test_trailing_stop_closes_position_after_peak_drawdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            closes = [100 + index * 3 for index in range(20)] + [160, 150, 142, 140, 138]
            _write_symbol(root / "111111_2018_2026.csv", closes, 10000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=1,
                    max_positions=1,
                    max_holding_days=100,
                    exit_ma_window=100,
                    stop_loss_pct=-50,
                    trailing_stop_pct=5.0,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        self.assertTrue(any(trade.reason == "trailing_stop" for trade in result.trades))

    def test_loss_cooldown_delays_reentry_after_losing_trade(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            closes = [100 + index * 2 for index in range(12)] + [115, 117, 119, 121, 123, 125, 127, 129, 131, 133, 135, 137]
            _write_symbol(root / "111111_2018_2026.csv", closes, 10000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=1,
                    max_positions=1,
                    max_holding_days=100,
                    exit_ma_window=100,
                    stop_loss_pct=-3,
                    loss_cooldown_days=8,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                ),
            )

        losing_trade = next(trade for trade in result.trades if trade.pnl < 0)
        later_entries = [
            trade.entry_date
            for trade in result.trades
            if trade.symbol == losing_trade.symbol and trade.entry_date > losing_trade.exit_date
        ]
        if later_entries:
            gap = (date.fromisoformat(min(later_entries)) - date.fromisoformat(losing_trade.exit_date)).days
            self.assertGreaterEqual(gap, 8)

    def test_dart_event_filter_blocks_negative_disclosure_leader(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_symbol(root / "111111_2018_2026.csv", [100 + index * 2 for index in range(35)], 10000)
            _write_symbol(root / "333333_2018_2026.csv", [120 - index for index in range(35)], 20000)

            result = run_leader_swing_backtest(
                load_symbol_candles(root),
                LeaderSwingConfig(
                    liquidity_window=5,
                    momentum_short=5,
                    momentum_long=10,
                    breakout_window=10,
                    trend_window=10,
                    liquidity_top_n=2,
                    max_positions=1,
                    max_holding_days=5,
                    initial_cash=1_000_000,
                    fee_rate=0.0,
                    tax_rate=0.0,
                    slippage_rate=0.0,
                    event_scores=EventScoreStore({("111111", "2024-01-11"): -0.9}),
                    event_lookback_days=100,
                    min_entry_event_score=-0.2,
                ),
            )

        self.assertEqual(result.trade_count, 0)


if __name__ == "__main__":
    unittest.main()
