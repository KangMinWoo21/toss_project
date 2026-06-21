import unittest

from backtester.toss import candle_page_to_rows, market_payloads_to_snapshot


class TossApiTests(unittest.TestCase):
    def test_candle_page_to_rows_converts_toss_fields_to_csv_rows(self):
        page = {
            "result": {
                "candles": [
                    {
                        "timestamp": "2026-03-25T09:00:00+09:00",
                        "openPrice": "71600",
                        "highPrice": "72300",
                        "lowPrice": "71500",
                        "closePrice": "72000",
                        "volume": "3521000",
                    }
                ],
                "nextBefore": None,
            }
        }

        rows = candle_page_to_rows(page)

        self.assertEqual(rows, [["2026-03-25", 71600.0, 72300.0, 71500.0, 72000.0, 3521000]])

    def test_candle_page_to_rows_can_keep_intraday_timestamp(self):
        page = {
            "result": {
                "candles": [
                    {
                        "timestamp": "2026-03-25T09:32:00+09:00",
                        "openPrice": "72000",
                        "highPrice": "72100",
                        "lowPrice": "71950",
                        "closePrice": "72050",
                        "volume": "15200",
                    }
                ],
                "nextBefore": None,
            }
        }

        rows = candle_page_to_rows(page, keep_timestamp=True)

        self.assertEqual(rows[0][0], "2026-03-25T09:32:00+09:00")

    def test_market_payloads_to_snapshot_combines_price_orderbook_and_trades(self):
        snapshot = market_payloads_to_snapshot(
            price_payload={"result": [{"lastPrice": "72000", "timestamp": "2026-03-25T09:30:00+09:00"}]},
            orderbook_payload={
                "result": {
                    "bids": [{"price": "71900", "volume": "100"}],
                    "asks": [{"price": "72100", "volume": "50"}],
                }
            },
            trades_payload={"result": [{"price": "72000", "volume": "10"}]},
        )

        self.assertEqual(snapshot.last_price, 72000.0)
        self.assertEqual(snapshot.recent_trade_volume, 10.0)
        self.assertEqual(snapshot.bids[0].volume, 100.0)


if __name__ == "__main__":
    unittest.main()
