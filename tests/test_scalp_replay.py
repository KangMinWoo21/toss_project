import csv
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.scalp_replay import aggregate_scalp_results, discover_scalp_files, replay_scalp_file


def _write_scalp_csv(path: Path) -> None:
    rows = [
        ("2026-06-15T09:00:00+09:00", 100.0, 100, 99.98, 100.02, 900, 900),
        ("2026-06-15T09:00:01+09:00", 100.1, 120, 100.08, 100.12, 1300, 500),
        ("2026-06-15T09:00:02+09:00", 100.3, 500, 100.28, 100.32, 1800, 400),
        ("2026-06-15T09:00:03+09:00", 100.5, 700, 100.48, 100.52, 2200, 400),
        ("2026-06-15T09:00:04+09:00", 100.7, 650, 100.68, 100.72, 2400, 500),
        ("2026-06-15T09:00:05+09:00", 100.8, 620, 100.78, 100.82, 2100, 600),
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "tick",
                "timestamp",
                "last_price",
                "recent_trade_volume",
                "best_bid",
                "best_ask",
                "spread",
                "bid_volume_5",
                "ask_volume_5",
                "bid_ask_imbalance",
                "signal",
                "reason",
                "position",
                "realized_pnl_pct",
            ]
        )
        for index, row in enumerate(rows):
            timestamp, price, volume, bid, ask, bid_volume, ask_volume = row
            writer.writerow(
                [
                    index,
                    timestamp,
                    price,
                    volume,
                    bid,
                    ask,
                    ask - bid,
                    bid_volume,
                    ask_volume,
                    bid_volume / ask_volume,
                    "HOLD",
                    "",
                    "FLAT",
                    0.0,
                ]
            )


class ScalpReplayTests(unittest.TestCase):
    def test_discover_scalp_files_keeps_kr_symbols_only_by_default(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            kr_path = root / "005930_2026-06-15_paper_scalp.csv"
            us_path = root / "AAPL_2026-06-15_paper_scalp.csv"
            _write_scalp_csv(kr_path)
            _write_scalp_csv(us_path)

            files = discover_scalp_files(root)

        self.assertEqual([path.name for path in files], ["005930_2026-06-15_paper_scalp.csv"])

    def test_replay_scalp_file_scores_open_source_inspired_rules(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "000660_2026-06-15_paper_scalp.csv"
            _write_scalp_csv(path)

            rows = replay_scalp_file(path, horizons=[2], min_trades=1)

        names = {row.strategy_name for row in rows}
        self.assertIn("imbalance_momentum_2.0", names)
        self.assertIn("volume_price_breakout_2.0", names)
        best = max(rows, key=lambda row: row.average_return_pct)
        self.assertGreater(best.trade_count, 0)
        self.assertGreater(best.profit_factor, 0)

    def test_cli_scalp_replay_prints_ranked_table(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "000660_2026-06-15_paper_scalp.csv"
            _write_scalp_csv(path)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backtester",
                    "scalp-replay",
                    "--data-dir",
                    temp_dir,
                    "--horizons",
                    "2",
                    "--min-trades",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("strategy", completed.stdout)
        self.assertIn("avg_%", completed.stdout)
        self.assertIn("imbalance_momentum", completed.stdout)

    def test_aggregate_scalp_results_keeps_profit_factor(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "000660_2026-06-15_paper_scalp.csv"
            _write_scalp_csv(path)
            rows = replay_scalp_file(path, horizons=[2], min_trades=1)

            aggregated = aggregate_scalp_results(rows, min_trades=1)

        self.assertTrue(aggregated)
        self.assertTrue(any(row.profit_factor > 0 for row in aggregated))


if __name__ == "__main__":
    unittest.main()
