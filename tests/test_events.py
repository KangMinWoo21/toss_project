import tempfile
import unittest
from pathlib import Path

from backtester.data import load_candles
from backtester.events import EventScoreStore, load_event_scores, merge_event_files
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

    def test_load_event_scores_applies_source_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,news,good article,0.8,1.0\n"
                "2026-01-05,005930,sns,noisy post,-0.8,1.0\n",
                encoding="utf-8",
            )

            store = load_event_scores(path, source_weights={"news": 1.0, "sns": 0.25})

        self.assertAlmostEqual(store.score("005930", "2026-01-05"), 0.48, places=3)

    def test_load_event_scores_applies_source_prefix_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,google-news:publisher,good article,0.8,1.0\n"
                "2026-01-05,005930,dart:company,routine filing,-0.2,1.0\n",
                encoding="utf-8",
            )

            store = load_event_scores(path, source_weights={"google-news": 1.0, "dart": 0.5})

        self.assertAlmostEqual(store.score("005930", "2026-01-05"), 0.4666, places=3)

    def test_merge_event_files_combines_news_sns_and_disclosure_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            news = root / "news.csv"
            sns = root / "sns.csv"
            output = root / "combined.csv"
            news.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,google-news:Example,strong profit outlook,0.8,1.0\n",
                encoding="utf-8",
            )
            sns.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,sns:x,noisy negative post,-0.8,1.0\n"
                "2026-01-06,000660,dart:company,self share purchase,0.4,1.0\n",
                encoding="utf-8",
            )

            saved = merge_event_files([news, sns], output)
            store = load_event_scores(output, source_weights={"google-news": 1.0, "sns": 0.25, "dart": 0.5})

        self.assertEqual(saved, 3)
        self.assertAlmostEqual(store.score("005930", "2026-01-05"), 0.48, places=3)
        self.assertEqual(store.score("000660", "2026-01-06"), 0.4)

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

    def test_load_event_scores_uses_available_date_to_prevent_lookahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "event_date,available_date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,2026-01-09,005930,news,late article,-0.9,1.0\n",
                encoding="utf-8",
            )

            store = load_event_scores(path)

        self.assertEqual(store.score_window("005930", "2026-01-08", 5), 0.0)
        self.assertEqual(store.score_window("005930", "2026-01-10", 5), -0.9)

    def test_load_event_scores_warns_when_legacy_date_is_used_as_available_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy_events.csv"
            path.write_text(
                "date,symbol,source,title,sentiment_score,importance_score\n"
                "2026-01-05,005930,news,legacy row,0.5,1.0\n",
                encoding="utf-8",
            )

            store = load_event_scores(path)

        self.assertEqual(store.score("005930", "2026-01-05"), 0.5)
        self.assertTrue(any("available_date" in warning for warning in store.warnings))

    def test_load_event_scores_excludes_rows_without_any_usable_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "symbol,source,title,sentiment_score,importance_score\n"
                "005930,news,undated row,0.9,1.0\n",
                encoding="utf-8",
            )

            store = load_event_scores(path)

        self.assertEqual(store.score("005930", "2026-01-05"), 0.0)
        self.assertTrue(any("missing available_date/event_date/date" in warning for warning in store.warnings))

    def test_news_filtered_strategy_ignores_same_day_event_for_buy(self):
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

        self.assertEqual(signal, "BUY")

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
