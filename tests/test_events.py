import tempfile
import unittest
from pathlib import Path

from backtester.data import load_candles
from backtester.events import EventScoreStore, load_event_scores
from backtester.strategies import NewsFilteredStrategy, VolatilityBreakoutStrategy


class EventScoreTests(unittest.TestCase):
    def test_load_event_scores_aggregates_by_symbol_and_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,news,good news,0.8,1.0\n"
                "2026-01-05,005930,sns,ceo post,0.4,0.5\n",
                encoding="utf-8",
            )

            store = load_event_scores(path)

        self.assertAlmostEqual(store.score("005930", "2026-01-05"), 0.6666, places=3)

    def test_event_score_store_can_score_recent_event_window(self):
        event_store = EventScoreStore(
            {
                ("005930", "2026-01-05"): 0.6,
                ("005930", "2026-01-07"): -0.2,
                ("000660", "2026-01-07"): -1.0,
            }
        )

        self.assertAlmostEqual(event_store.score_window("005930", "2026-01-08", 3), 0.2, places=3)
        self.assertEqual(event_store.score_window("005930", "2026-01-08", 1), -0.2)

    def test_news_filtered_strategy_blocks_negative_event_day_buy(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        event_store = EventScoreStore({("005930", "2026-01-08"): -0.9})
        base = VolatilityBreakoutStrategy(k=0.3)
        strategy = NewsFilteredStrategy(
            base_strategy=base,
            event_scores=event_store,
            symbol="005930",
            min_buy_score=-0.2,
            force_sell_score=-0.8,
        )

        signal = strategy.on_candle(6, candles, None)

        self.assertEqual(signal, "HOLD")

    def test_news_filtered_strategy_blocks_recent_negative_event_buy(self):
        candles = load_candles(Path("data/sample_kr_stock.csv"))
        event_store = EventScoreStore({("005930", "2026-01-07"): -0.9})
        base = VolatilityBreakoutStrategy(k=0.3)
        strategy = NewsFilteredStrategy(
            base_strategy=base,
            event_scores=event_store,
            symbol="005930",
            min_buy_score=-0.2,
            force_sell_score=-0.8,
            event_lookback_days=2,
        )

        signal = strategy.on_candle(6, candles, None)

        self.assertEqual(signal, "HOLD")


if __name__ == "__main__":
    unittest.main()
