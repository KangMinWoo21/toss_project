import unittest
import subprocess

from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.data import load_candles
from backtester.pykrx_fetcher import (
    build_missing_ohlcv_targets,
    fetch_missing_ohlcv_batches,
    fetch_pykrx_ohlcv_universe_csv,
    available_ohlcv_symbols,
    monthly_snapshot_dates,
    normalize_pykrx_market_snapshot_frames,
    normalize_pykrx_universe_snapshot,
    load_symbol_universe,
    normalize_pykrx_ohlcv_frame,
    normalize_pykrx_trading_value_frame,
    run_missing_ohlcv_batch_subprocess_loop,
    save_market_snapshot_rows,
    save_missing_ohlcv_targets,
    save_universe_snapshot_rows,
    save_ohlcv_rows,
)


class PykrxFetcherTests(unittest.TestCase):
    def test_normalize_pykrx_trading_value_frame_accepts_dict_rows(self):
        rows = normalize_pykrx_trading_value_frame(
            symbol="005930",
            rows=[
                {
                    "date": "2026-01-08",
                    "외국인": 100_000_000,
                    "기관합계": 50_000_000,
                    "개인": -120_000_000,
                }
            ],
        )

        self.assertEqual(rows[0]["symbol"], "005930")
        self.assertEqual(rows[0]["foreign_net_value"], 100_000_000)
        self.assertEqual(rows[0]["institution_net_value"], 50_000_000)
        self.assertEqual(rows[0]["individual_net_value"], -120_000_000)

    def test_normalize_pykrx_ohlcv_frame_writes_candle_csv(self):
        rows = normalize_pykrx_ohlcv_frame(
            [
                {
                    "date": "2024-01-02",
                    "시가": 100,
                    "고가": 110,
                    "저가": 90,
                    "종가": 105,
                    "거래량": 1000,
                }
            ]
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "005930.csv"
            saved = save_ohlcv_rows(rows, path)
            candles = load_candles(path)

        self.assertEqual(saved, 1)
        self.assertEqual(candles[0].date, "2024-01-02")
        self.assertEqual(candles[0].close, 105)

    def test_load_symbol_universe_pads_symbols_and_dedupes(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "symbol,name,market\n"
                "5930,Samsung Electronics,KOSPI\n"
                "000660,SK hynix,KOSPI\n"
                "005930,Duplicate Samsung,KOSPI\n",
                encoding="utf-8",
            )

            rows = load_symbol_universe(path)

        self.assertEqual([row["symbol"] for row in rows], ["005930", "000660"])
        self.assertEqual(rows[0]["name"], "Samsung Electronics")

    def test_fetch_pykrx_ohlcv_universe_records_success_and_failure(self):
        def fake_fetcher(start, end, symbol, output_path):
            if symbol == "000660":
                raise RuntimeError("temporary KRX error")
            return save_ohlcv_rows(
                [
                    {
                        "date": "2024-01-02",
                        "open": 100,
                        "high": 110,
                        "low": 90,
                        "close": 105,
                        "volume": 1000,
                    }
                ],
                output_path,
            )

        with TemporaryDirectory() as temp_dir:
            report = fetch_pykrx_ohlcv_universe_csv(
                start="2024-01-01",
                end="2024-01-31",
                symbols=[
                    {"symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI"},
                    {"symbol": "000660", "name": "SK hynix", "market": "KOSPI"},
                ],
                output_dir=temp_dir,
                fetcher=fake_fetcher,
            )

            self.assertTrue((Path(temp_dir) / "005930.csv").exists())

        self.assertEqual(report[0]["status"], "saved")
        self.assertEqual(report[0]["rows"], 1)
        self.assertEqual(report[1]["status"], "failed")
        self.assertIn("temporary KRX error", report[1]["error"])

    def test_fetch_pykrx_ohlcv_universe_checkpoints_report_after_each_symbol(self):
        def fake_fetcher(start, end, symbol, output_path):
            if symbol == "000660":
                raise RuntimeError("temporary KRX error")
            return save_ohlcv_rows(
                [
                    {
                        "date": "2024-01-02",
                        "open": 100,
                        "high": 110,
                        "low": 90,
                        "close": 105,
                        "volume": 1000,
                    }
                ],
                output_path,
            )

        with TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.csv"
            fetch_pykrx_ohlcv_universe_csv(
                start="2024-01-01",
                end="2024-01-31",
                symbols=[
                    {"symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI"},
                    {"symbol": "000660", "name": "SK hynix", "market": "KOSPI"},
                ],
                output_dir=Path(temp_dir) / "prices",
                fetcher=fake_fetcher,
                checkpoint_report_path=report_path,
            )
            text = report_path.read_text(encoding="utf-8")

        self.assertIn("005930", text)
        self.assertIn("000660", text)
        self.assertIn("failed", text)

    def test_available_ohlcv_symbols_reads_symbol_prefixes_from_data_dir(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "005930.csv").write_text("date,open,high,low,close,volume\n", encoding="utf-8")
            (root / "000660_extra.csv").write_text("date,open,high,low,close,volume\n", encoding="utf-8")

            symbols = available_ohlcv_symbols(root)

        self.assertEqual(symbols, {"005930", "000660"})

    def test_build_missing_ohlcv_targets_prioritizes_repeated_missing_symbols(self):
        targets = build_missing_ohlcv_targets(
            [
                {"date": "2024-01-31", "symbol": "005930", "name": "Samsung", "market": "KOSPI"},
                {"date": "2024-01-31", "symbol": "000660", "name": "Hynix", "market": "KOSPI"},
                {"date": "2024-02-29", "symbol": "000660", "name": "Hynix", "market": "KOSPI"},
                {"date": "2024-02-29", "symbol": "035420", "name": "Naver", "market": "KOSPI"},
            ],
            available_symbols={"005930"},
        )

        self.assertEqual([row["symbol"] for row in targets], ["000660", "035420"])
        self.assertEqual(targets[0]["missing_snapshots"], 2)
        self.assertEqual(targets[0]["first_missing_date"], "2024-01-31")
        self.assertEqual(targets[0]["last_missing_date"], "2024-02-29")

    def test_save_missing_ohlcv_targets_writes_loadable_symbols_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "targets.csv"
            saved = save_missing_ohlcv_targets(
                [
                    {
                        "symbol": "000660",
                        "name": "Hynix",
                        "market": "KOSPI",
                        "missing_snapshots": 2,
                        "first_missing_date": "2024-01-31",
                        "last_missing_date": "2024-02-29",
                    }
                ],
                path,
            )
            rows = load_symbol_universe(path)

        self.assertEqual(saved, 1)
        self.assertEqual(rows[0]["symbol"], "000660")

    def test_fetch_missing_ohlcv_batches_replans_between_small_batches(self):
        def fake_fetcher(start, end, symbol, output_path):
            return save_ohlcv_rows(
                [
                    {
                        "date": "2024-01-02",
                        "open": 100,
                        "high": 110,
                        "low": 90,
                        "close": 105,
                        "volume": 1000,
                    }
                ],
                output_path,
            )

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "prices"
            data_dir.mkdir()
            universe = root / "universe.csv"
            universe.write_text(
                "date,symbol,name,market\n"
                "2024-01-31,005930,Samsung,KOSPI\n"
                "2024-01-31,000660,Hynix,KOSPI\n"
                "2024-01-31,035420,Naver,KOSPI\n",
                encoding="utf-8",
            )
            targets_output = root / "targets.csv"
            report_dir = root / "reports"
            pauses = []

            summary = fetch_missing_ohlcv_batches(
                start="2024-01-01",
                end="2024-01-31",
                universe_file=universe,
                data_dir=data_dir,
                targets_output=targets_output,
                report_dir=report_dir,
                batch_size=1,
                batches=2,
                batch_pause_seconds=1.5,
                fetcher=fake_fetcher,
                sleeper=pauses.append,
            )
            remaining = load_symbol_universe(targets_output)
            first_report_exists = (report_dir / "krx_missing_ohlcv_fetch_batch001.csv").exists()
            second_report_exists = (report_dir / "krx_missing_ohlcv_fetch_batch002.csv").exists()

        self.assertEqual(summary["batches_run"], 2)
        self.assertEqual(summary["saved"], 2)
        self.assertEqual(summary["remaining_targets"], 1)
        self.assertEqual(pauses, [1.5])
        self.assertEqual([row["symbol"] for row in remaining], ["035420"])
        self.assertTrue(first_report_exists)
        self.assertTrue(second_report_exists)

    def test_run_missing_ohlcv_batch_subprocess_loop_uses_one_batch_children_and_stops_on_timeout(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            targets_output = root / "targets.csv"
            calls = []
            pauses = []

            def fake_runner(command, *, capture_output, text, encoding, errors, timeout):
                calls.append((command, timeout, encoding, errors))
                if len(calls) == 1:
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=(
                            "Missing OHLCV batch fetch summary\n"
                            "saved  50\n"
                            "remaining_targets  1\n"
                        ),
                        stderr="",
                    )
                raise subprocess.TimeoutExpired(command, timeout)

            summary = run_missing_ohlcv_batch_subprocess_loop(
                start="2024-01-01",
                end="2024-01-31",
                universe_file=root / "universe.csv",
                data_dir=root / "prices",
                targets_output=targets_output,
                report_dir=root / "reports",
                report_prefix="fetch",
                batch_size=50,
                max_batches=2,
                batch_timeout_seconds=7,
                batch_pause_seconds=3,
                python_executable="python-test",
                command_runner=fake_runner,
                sleeper=pauses.append,
            )

        self.assertEqual(len(calls), 2)
        self.assertIn("--batches", calls[0][0])
        self.assertEqual(calls[0][0][calls[0][0].index("--batches") + 1], "1")
        self.assertIn("fetch_loop001", calls[0][0])
        self.assertIn("fetch_loop002", calls[1][0])
        self.assertEqual(calls[0][1], 7)
        self.assertEqual(calls[0][2], "utf-8")
        self.assertEqual(calls[0][3], "replace")
        self.assertEqual(pauses, [3])
        self.assertEqual(summary["completed_batches"], 1)
        self.assertEqual(summary["timed_out_batches"], 1)
        self.assertEqual(summary["remaining_targets"], 1)
        self.assertEqual(summary["status"], "timed_out")

    def test_normalize_pykrx_universe_snapshot_records_symbols_names_and_market(self):
        rows = normalize_pykrx_universe_snapshot(
            date="2026-06-18",
            market="KOSPI",
            tickers=["5930", "000660"],
            name_lookup=lambda ticker: {"005930": "Samsung Electronics", "000660": "SK hynix"}[ticker],
        )

        self.assertEqual(rows, [
            {"date": "2026-06-18", "symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI"},
            {"date": "2026-06-18", "symbol": "000660", "name": "SK hynix", "market": "KOSPI"},
        ])

    def test_monthly_snapshot_dates_include_month_ends_and_final_date(self):
        self.assertEqual(
            monthly_snapshot_dates("2024-01-10", "2024-03-15"),
            ["2024-01-31", "2024-02-29", "2024-03-15"],
        )

    def test_save_universe_snapshot_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            saved = save_universe_snapshot_rows(
                [{"date": "2026-06-18", "symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI"}],
                path,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("date,symbol,name,market", text)
        self.assertIn("005930", text)

    def test_normalize_pykrx_market_snapshot_frames_merges_ohlcv_and_market_cap(self):
        rows = normalize_pykrx_market_snapshot_frames(
            date="2026-06-18",
            market="KOSPI",
            ohlcv_rows=[
                {
                    "티커": "005930",
                    "시가": 100,
                    "고가": 110,
                    "저가": 90,
                    "종가": 105,
                    "거래량": 1_000,
                    "거래대금": 105_000,
                }
            ],
            market_cap_rows=[
                {
                    "티커": "005930",
                    "시가총액": 600_000_000,
                    "상장주식수": 5_000_000,
                }
            ],
            name_lookup=lambda ticker: "Samsung Electronics",
        )

        self.assertEqual(rows[0]["symbol"], "005930")
        self.assertEqual(rows[0]["trading_value"], 105_000)
        self.assertEqual(rows[0]["market_cap"], 600_000_000)
        self.assertEqual(rows[0]["shares"], 5_000_000)

    def test_save_market_snapshot_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "market_snapshot.csv"
            saved = save_market_snapshot_rows(
                [
                    {
                        "date": "2026-06-18",
                        "symbol": "005930",
                        "name": "Samsung Electronics",
                        "market": "KOSPI",
                        "open": 100,
                        "high": 110,
                        "low": 90,
                        "close": 105,
                        "volume": 1_000,
                        "trading_value": 105_000,
                        "market_cap": 600_000_000,
                        "shares": 5_000_000,
                    }
                ],
                path,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("market_cap", text)
        self.assertIn("600000000", text)


if __name__ == "__main__":
    unittest.main()
