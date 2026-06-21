import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.scalper import OrderbookLevel, ScalperConfig, TickSnapshot, decide_scalp_signal, run_paper_scalper, snapshot_metrics


class ScalperTests(unittest.TestCase):
    def test_decide_scalp_signal_buys_on_volume_spike_price_rise_and_bid_imbalance(self):
        previous = [
            TickSnapshot(
                timestamp="2026-06-10T09:00:00+09:00",
                last_price=100.0,
                recent_trade_volume=1000,
                bids=[OrderbookLevel(99, 2000)],
                asks=[OrderbookLevel(101, 2000)],
            )
        ]
        current = TickSnapshot(
            timestamp="2026-06-10T09:00:01+09:00",
            last_price=103.0,
            recent_trade_volume=7000,
            bids=[OrderbookLevel(102.95, 7000), OrderbookLevel(102.9, 5000)],
            asks=[OrderbookLevel(103.05, 2000), OrderbookLevel(103.1, 2000)],
        )

        signal = decide_scalp_signal(previous, current, position=None, config=ScalperConfig())

        self.assertEqual(signal.action, "BUY")

    def test_decide_scalp_signal_blocks_wide_spread_entries(self):
        previous = [
            TickSnapshot(
                timestamp="2026-06-10T09:00:00+09:00",
                last_price=100.0,
                recent_trade_volume=1000,
                bids=[OrderbookLevel(99, 2000)],
                asks=[OrderbookLevel(101, 2000)],
            )
        ]
        current = TickSnapshot(
            timestamp="2026-06-10T09:00:01+09:00",
            last_price=103.0,
            recent_trade_volume=7000,
            bids=[OrderbookLevel(100, 7000)],
            asks=[OrderbookLevel(104, 1000)],
        )

        signal = decide_scalp_signal(previous, current, position=None, config=ScalperConfig(max_spread_pct=0.5))

        self.assertEqual(signal.action, "HOLD")
        self.assertIn("spread_too_wide", signal.reason)

    def test_decide_scalp_signal_sells_on_stop_loss(self):
        current = TickSnapshot(
            timestamp="2026-06-10T09:00:02+09:00",
            last_price=98.0,
            recent_trade_volume=1000,
            bids=[OrderbookLevel(97, 1000)],
            asks=[OrderbookLevel(99, 1000)],
        )

        signal = decide_scalp_signal(
            [],
            current,
            position={"entry_price": 100.0, "entry_time": "2026-06-10T09:00:00+09:00"},
            config=ScalperConfig(stop_loss_pct=-1.0),
        )

        self.assertEqual(signal.action, "SELL")

    def test_snapshot_metrics_extracts_orderbook_features(self):
        snapshot = TickSnapshot(
            timestamp="2026-06-10T09:00:01+09:00",
            last_price=103.0,
            recent_trade_volume=7000,
            bids=[OrderbookLevel(102, 7000), OrderbookLevel(101, 5000)],
            asks=[OrderbookLevel(104, 2000), OrderbookLevel(105, 2000)],
        )

        metrics = snapshot_metrics(snapshot)

        self.assertEqual(metrics["best_bid"], 102)
        self.assertEqual(metrics["best_ask"], 104)
        self.assertEqual(metrics["bid_volume_5"], 12000)
        self.assertEqual(metrics["ask_volume_5"], 4000)
        self.assertEqual(metrics["bid_ask_imbalance"], 3)

    def test_run_paper_scalper_skips_ticks_outside_required_date(self):
        snapshot = TickSnapshot(
            timestamp="2026-06-09T15:30:00+09:00",
            last_price=100.0,
            recent_trade_volume=1000,
            bids=[OrderbookLevel(99, 1000)],
            asks=[OrderbookLevel(101, 1000)],
        )

        with TemporaryDirectory() as temp_dir:
            rows = run_paper_scalper(
                snapshot_fetcher=lambda: snapshot,
                iterations=1,
                interval_seconds=0,
                output_path=Path(temp_dir) / "paper.csv",
                required_date="2026-06-10",
            )

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
