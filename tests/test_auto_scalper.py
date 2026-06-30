import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.auto_scalper import (
    KST,
    auto_scalper_sleep_seconds,
    choose_symbols_for_now,
    is_market_open,
    parse_symbol_list,
    run_auto_scalper_once,
)


class AutoScalperTests(unittest.TestCase):
    def test_parse_symbol_list_ignores_empty_values(self):
        self.assertEqual(parse_symbol_list("005930, 000660,,AAPL"), ["005930", "000660", "AAPL"])

    def test_parse_symbol_list_rejects_path_components(self):
        with self.assertRaises(ValueError):
            parse_symbol_list("005930,..\\escape")

    def test_kst_timezone_is_used_for_collection_dates(self):
        self.assertEqual(KST.key, "Asia/Seoul")

    def test_is_market_open_uses_calendar_sessions(self):
        calendar = {
            "result": {
                "today": {
                    "date": "2026-06-10",
                    "regularMarket": {
                        "startTime": "2026-06-10T09:00:00+09:00",
                        "endTime": "2026-06-10T15:30:00+09:00",
                    },
                }
            }
        }
        now = datetime.fromisoformat("2026-06-10T10:00:00+09:00")

        self.assertTrue(is_market_open(calendar, now, ["regularMarket"]))

    def test_choose_symbols_prefers_kr_when_both_markets_are_open(self):
        kr_calendar = {
            "result": {
                "today": {
                    "date": "2026-06-10",
                    "integrated": {
                        "regularMarket": {
                            "startTime": "2026-06-10T09:00:00+09:00",
                            "endTime": "2026-06-10T15:30:00+09:00",
                        }
                    },
                }
            }
        }
        us_calendar = {
            "result": {
                "today": {
                    "date": "2026-06-10",
                    "regularMarket": {
                        "startTime": "2026-06-10T08:00:00+09:00",
                        "endTime": "2026-06-10T12:00:00+09:00",
                    },
                }
            }
        }
        now = datetime.fromisoformat("2026-06-10T10:00:00+09:00")

        market, symbols = choose_symbols_for_now(
            kr_calendar=kr_calendar,
            us_calendar=us_calendar,
            now=now,
            kr_symbols=["005930"],
            us_symbols=["AAPL"],
        )

        self.assertEqual(market, "KR")
        self.assertEqual(symbols, ["005930"])

    def test_run_auto_scalper_once_writes_each_open_symbol(self):
        kr_calendar = {"result": []}
        us_calendar = {
            "result": {
                "today": {
                    "date": "2026-06-10",
                    "regularMarket": {
                        "startTime": "2026-06-10T00:00:00+09:00",
                        "endTime": "2026-06-10T23:59:59+09:00",
                    },
                }
            }
        }
        calls = []

        def fake_runner(symbol, output_path, required_date):
            calls.append((symbol, Path(output_path).name, required_date))
            return 2

        with TemporaryDirectory() as temp_dir:
            rows = run_auto_scalper_once(
                now=datetime.fromisoformat("2026-06-10T10:00:00+09:00"),
                kr_calendar=kr_calendar,
                us_calendar=us_calendar,
                kr_symbols=[],
                us_symbols=["AAPL", "NVDA"],
                output_dir=Path(temp_dir),
                runner=fake_runner,
            )

        self.assertEqual(rows, [("US", "AAPL", 2), ("US", "NVDA", 2)])
        self.assertEqual(calls[0], ("AAPL", "AAPL_2026-06-10_paper_scalp.csv", "2026-06-10"))

    def test_run_auto_scalper_once_rejects_symbol_path_traversal(self):
        kr_calendar = {
            "result": {
                "today": {
                    "regularMarket": {
                        "startTime": "2026-06-10T00:00:00+09:00",
                        "endTime": "2026-06-10T23:59:59+09:00",
                    }
                }
            }
        }

        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                run_auto_scalper_once(
                    now=datetime.fromisoformat("2026-06-10T10:00:00+09:00"),
                    kr_calendar=kr_calendar,
                    us_calendar={"result": []},
                    kr_symbols=["..\\escape"],
                    us_symbols=[],
                    output_dir=Path(temp_dir),
                    runner=lambda symbol, output_path, required_date: 1,
                )

    def test_auto_scalper_sleeps_between_open_market_cycles(self):
        self.assertEqual(
            auto_scalper_sleep_seconds([("US", "AAPL", 1)], interval_seconds=1.5, idle_seconds=60.0),
            1.5,
        )
        self.assertEqual(
            auto_scalper_sleep_seconds([], interval_seconds=1.5, idle_seconds=60.0),
            60.0,
        )


if __name__ == "__main__":
    unittest.main()
