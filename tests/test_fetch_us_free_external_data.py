import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.fetch_us_free_external_data import main


class _FakeResponse:
    def __init__(self, text: str):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._text.encode("utf-8")


class FetchUsFreeExternalDataTests(unittest.TestCase):
    def test_fetch_script_writes_normalized_free_external_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cik_map = root / "cik_map.csv"
            cik_map.write_text("symbol,cik\nAAPL,0000320193\n", encoding="utf-8")
            responses = [
                _FakeResponse("Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n20260630|AAPL|200|0|1000|Q\n"),
                _FakeResponse(
                    "symbol,name,exchange,assetType,ipoDate,delistingDate,status\n"
                    "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,null,Active\n"
                ),
                _FakeResponse(
                    json.dumps(
                        {
                            "feed": [
                                {
                                    "ticker_sentiment": [
                                        {"ticker": "AAPL", "ticker_sentiment_score": "0.30"},
                                        {"ticker": "MSFT", "ticker_sentiment_score": "-0.10"},
                                    ]
                                },
                                {
                                    "ticker_sentiment": [
                                        {"ticker": "AAPL", "ticker_sentiment_score": "0.10"},
                                    ]
                                },
                            ]
                        }
                    )
                ),
                _FakeResponse(
                    json.dumps(
                        {
                            "facts": {
                                "us-gaap": {
                                    "Assets": {"units": {"USD": [{"fy": 2025, "val": 1000}]}},
                                    "Liabilities": {"units": {"USD": [{"fy": 2025, "val": 400}]}},
                                    "NetIncomeLoss": {"units": {"USD": [{"fy": 2025, "val": 120}]}},
                                    "Revenues": {"units": {"USD": [{"fy": 2025, "val": 900}]}},
                                }
                            }
                        }
                    )
                ),
            ]

            with patch("urllib.request.urlopen", side_effect=responses):
                exit_code = main(
                    [
                        "--symbols",
                        "AAPL",
                        "--output-dir",
                        str(root / "out"),
                        "--alpha-vantage-key",
                        "demo",
                        "--cik-map",
                        str(cik_map),
                        "--finra-date",
                        "20260630",
                        "--sleep-seconds",
                        "0",
                    ]
                )

            self.assertEqual(exit_code, 0)
            listing = _read_csv(root / "out" / "listing_status.csv")
            short = _read_csv(root / "out" / "short_sale_volume.csv")
            news = _read_csv(root / "out" / "news_sentiment.csv")
            factors = _read_csv(root / "out" / "factors.csv")

            self.assertEqual(listing[0]["symbol"], "AAPL")
            self.assertEqual(listing[0]["source"], "alpha_vantage_listing_status")
            self.assertEqual(short[0]["short_volume"], "200")
            self.assertEqual(short[0]["source"], "finra_daily_short_sale_volume")
            self.assertEqual(news[0]["article_count"], "2")
            self.assertEqual(news[0]["source"], "alpha_vantage_news_sentiment")
            self.assertEqual(factors[0]["symbol"], "AAPL")
            self.assertEqual(factors[0]["source"], "sec_edgar_companyfacts_proxy")
            self.assertGreater(float(factors[0]["quality_score"]), 0.0)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


if __name__ == "__main__":
    unittest.main()
