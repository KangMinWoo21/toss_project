import subprocess
import sys
import unittest
from pathlib import Path

from backtester.data import load_candles
from backtester.engine import BacktestConfig, BacktestResult
from backtester.swing_sweep import build_swing_strategy_grid, score_swing_train_result, run_swing_parameter_sweep


class SwingSweepTests(unittest.TestCase):
    def test_build_swing_strategy_grid_creates_named_parameter_variants(self):
        strategies = build_swing_strategy_grid(preset="compact")
        names = [strategy.name for strategy in strategies]

        self.assertGreater(len(strategies), 10)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(any(name.startswith("tsm_l20") for name in names))
        self.assertTrue(any(name.startswith("composite_m20") for name in names))

    def test_run_swing_parameter_sweep_selects_train_winner_for_next_window(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))

        report = run_swing_parameter_sweep(
            candles=candles,
            train_size=7,
            test_size=4,
            step_size=4,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
            preset="compact",
        )

        self.assertTrue(report.periods)
        self.assertTrue(report.summary)
        self.assertIn(report.periods[0].best_strategy, {row.strategy_name for row in report.summary})

    def test_cli_swing_sweep_prints_periods_and_summary(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "swing-sweep",
                "--data",
                "data/sample_kr_stock.csv",
                "--train-size",
                "7",
                "--test-size",
                "4",
                "--step-size",
                "4",
                "--preset",
                "compact",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Swing sweep periods", completed.stdout)
        self.assertIn("Strategy summary", completed.stdout)

    def test_score_swing_train_result_prefers_active_strategy_over_no_trade(self):
        no_trade = BacktestResult(
            strategy_name="no_trade",
            initial_cash=1_000_000,
            final_equity=1_000_000,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            trade_count=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            calmar_ratio=0.0,
            trades=[],
            equity_curve=[1_000_000],
        )
        active = BacktestResult(
            strategy_name="active",
            initial_cash=1_000_000,
            final_equity=1_010_000,
            total_return_pct=1.0,
            max_drawdown_pct=-2.0,
            trade_count=1,
            win_rate_pct=100.0,
            profit_factor=1.0,
            sharpe_ratio=0.5,
            calmar_ratio=0.5,
            trades=[],
            equity_curve=[1_000_000, 1_010_000],
        )

        self.assertGreater(score_swing_train_result(active), score_swing_train_result(no_trade))


if __name__ == "__main__":
    unittest.main()
