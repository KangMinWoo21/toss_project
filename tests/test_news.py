import csv
import tempfile
import unittest
from pathlib import Path

from backtester.news import (
    articles_to_event_rows,
    load_social_posts_csv,
    rss_to_event_rows,
    score_title_sentiment,
    social_posts_to_event_rows,
)


class NewsFetchTests(unittest.TestCase):
    def test_score_title_sentiment_uses_simple_positive_negative_terms(self):
        self.assertGreater(score_title_sentiment("Samsung shares surge on strong profit outlook"), 0)
        self.assertLess(score_title_sentiment("Samsung falls after weak demand warning"), 0)
        self.assertGreater(score_title_sentiment("삼성전자 호실적 전망에 상승"), 0)
        self.assertLess(score_title_sentiment("삼성전자 수요 부진 우려에 하락"), 0)

    def test_articles_to_event_rows_converts_gdelt_articles_to_event_csv_rows(self):
        payload = {
            "articles": [
                {
                    "seendate": "20260609123000",
                    "title": "Samsung shares surge on AI chip demand",
                    "domain": "example.com",
                    "url": "https://example.com/article",
                }
            ]
        }

        rows = articles_to_event_rows(payload, symbol="005930")

        self.assertEqual(rows[0][0], "2026-06-09")
        self.assertEqual(rows[0][1], "005930")
        self.assertEqual(rows[0][2], "gdelt:example.com")
        self.assertGreater(rows[0][4], 0)

    def test_rss_to_event_rows_converts_google_news_items(self):
        rss = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>Samsung shares surge on AI chip demand - Example</title>
            <pubDate>Tue, 09 Jun 2026 12:30:00 GMT</pubDate>
            <source url="https://example.com">Example</source>
          </item>
        </channel></rss>
        """

        rows = rss_to_event_rows(rss, symbol="005930")

        self.assertEqual(rows[0][0], "2026-06-09")
        self.assertEqual(rows[0][1], "005930")
        self.assertEqual(rows[0][2], "google-news:Example")
        self.assertGreater(rows[0][4], 0)

    def test_social_posts_to_event_rows_uses_engagement_as_importance(self):
        rows = social_posts_to_event_rows(
            [
                {
                    "timestamp": "2026-06-09T12:30:00+09:00",
                    "symbol": "005930",
                    "platform": "x",
                    "text": "Samsung shares surge on AI chip demand",
                    "likes": "100",
                    "reposts": "25",
                    "comments": "5",
                }
            ]
        )

        self.assertEqual(rows[0][0], "2026-06-09")
        self.assertEqual(rows[0][1], "005930")
        self.assertEqual(rows[0][2], "sns:x")
        self.assertGreater(rows[0][4], 0)
        self.assertGreater(rows[0][5], 1.0)

    def test_load_social_posts_csv_can_use_default_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sns.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "platform", "text", "likes"])
                writer.writerow(["2026-06-09", "blog", "Samsung profit growth outlook", "10"])

            rows = load_social_posts_csv(path, symbol="005930")

        self.assertEqual(rows[0][1], "005930")
        self.assertEqual(rows[0][2], "sns:blog")


if __name__ == "__main__":
    unittest.main()
