import tempfile
import unittest
from pathlib import Path

from backtester.data import load_candles
from backtester.flow import FlowScoreStore, load_flow_scores, score_flow_row
from backtester.strategies import FlowFilteredStrategy, VolatilityBreakoutStrategy


class FlowScoreTests(unittest.TestCase):
    def test_score_flow_row_rewards_foreign_and_institution_buying(self):
        score = score_flow_row(
            foreign_net_value=100_000_000,
            institution_net_value=50_000_000,
            individual_net_value=-120_000_000,
            insider_buy_value=0,
            insider_sell_value=0,
            scale_value=100_000_000,
        )

        self.assertGreater(score, 0)

    def test_load_flow_scores_reads_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flows.csv"
            path.write_text(
                "date,symbol,foreign_net_value,institution_net_value,individual_net_value,insider_buy_value,insider_sell_value\n"
                "2026-01-08,005930,100000000,50000000,-120000000,0,0\n",
                encoding="utf-8",
            )

            store = load_flow_scores(path)

        self.assertGreater(store.score("005930", "2026-01-08"), 0)

    def test_flow_filtered_strategy_blocks_buy_on_negative_flow(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        flow_store = FlowScoreStore({("005930", "2026-01-08"): -0.9})
        strategy = FlowFilteredStrategy(
            base_strategy=VolatilityBreakoutStrategy(k=0.3),
            flow_scores=flow_store,
            symbol="005930",
            min_buy_score=-0.2,
            force_sell_score=-0.8,
        )

        signal = strategy.on_candle(6, candles, None)

        self.assertEqual(signal, "HOLD")


if __name__ == "__main__":
    unittest.main()
