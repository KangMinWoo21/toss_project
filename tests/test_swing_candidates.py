import csv
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.data import load_candles
from backtester.engine import BacktestConfig
from backtester.swing_sweep import (
    build_candidate_strategy_grid,
    run_candidate_validation,
    summarize_candidate_validation,
)


class SwingCandidateTests(unittest.TestCase):
    def test_build_candidate_strategy_grid_keeps_only_two_survivors(self):
        strategies = build_candidate_strategy_grid()

        self.assertEqual([strategy.name for strategy in strategies], ["tsm_l20_r5", "composite_m20_t20_b10_v2"])

    def test_candidate_validation_marks_no_trade_or_no_excess_as_rejected(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))

        rows = run_candidate_validation(
            candles=candles,
            train_size=7,
            test_size=4,
            step_size=4,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
        )

        self.assertTrue(rows)
        self.assertTrue(all(row.accepted == (row.test_trade_count > 0 and row.excess_return_pct > 0) for row in rows))

    def test_candidate_summary_counts_accepted_windows(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        rows = run_candidate_validation(
            candles=candles,
            train_size=7,
            test_size=4,
            step_size=4,
            config=BacktestConfig(initial_cash=1_000_000, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0),
        )

        summary = summarize_candidate_validation(rows)

        self.assertIn("accepted", summary)
        self.assertIn("avg_excess_pct", summary)

    def test_cli_swing_candidates_prints_validation_and_summary(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "backtester",
                "swing-candidates",
                "--data",
                "data/sample_kr_stock.csv",
                "--train-size",
                "7",
                "--test-size",
                "4",
                "--step-size",
                "4",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Candidate validation", completed.stdout)
        self.assertIn("Candidate summary", completed.stdout)


if __name__ == "__main__":
    unittest.main()
