import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.data_quality import (
    DataQualityResult,
    diagnose_candle_csv,
    save_data_quality_exclusions,
    save_data_quality_diagnostics,
    validate_candle_csv,
    validate_candle_dataframe,
    validate_dataset_freshness,
    validate_universe_metadata,
)


class DataQualityTests(unittest.TestCase):
    def test_validate_candle_dataframe_passes_clean_rows(self):
        result = validate_candle_dataframe(
            [
                {"date": "2026-06-19", "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
                {"date": "2026-06-20", "open": 105, "high": 106, "low": 100, "close": 101, "volume": 900},
            ],
            as_of_date="2026-06-21",
            max_stale_days=7,
        )

        self.assertIsInstance(result, DataQualityResult)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.latest_date, "2026-06-20")
        self.assertEqual(result.stale_days, 1)
        self.assertEqual(result.rows_checked, 2)

    def test_validate_candle_csv_blocks_bad_ohlcv_and_duplicates(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,100,90,95,105,1000\n"
                "2026-06-20,101,106,100,104,-1\n",
                encoding="utf-8",
            )

            result = validate_candle_csv(path)

        self.assertEqual(result.status, "BLOCK")
        self.assertIn("duplicate date", "; ".join(result.issues))
        self.assertIn("high below open/close", "; ".join(result.issues))
        self.assertIn("negative volume", "; ".join(result.issues))

    def test_validate_dataset_freshness_blocks_stale_symbol_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            (root / "000660.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,200,202,198,201,1000\n",
                encoding="utf-8",
            )

            result = validate_dataset_freshness(root, as_of_date="2026-06-21", max_stale_days=7)

        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.latest_date, "2026-06-20")
        self.assertEqual(result.stale_days, 20)
        self.assertEqual(result.blocked_symbols, ("005930",))
        self.assertIn("005930.csv stale", "; ".join(result.issues))

    def test_save_data_quality_exclusions_writes_blocked_symbols_only(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            (root / "000660.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,200,202,198,201,1000\n",
                encoding="utf-8",
            )
            result = validate_dataset_freshness(root, as_of_date="2026-06-21", max_stale_days=7)
            output = root / "excluded.csv"

            saved = save_data_quality_exclusions(result, output)
            text = output.read_text(encoding="utf-8-sig")

        self.assertEqual(saved, 1)
        self.assertIn("symbol,status,reason", text)
        self.assertIn("005930,BLOCK", text)
        self.assertNotIn("000660", text)

    def test_diagnose_candle_csv_classifies_reason_codes_and_action(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "005930.csv"
            path.write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,101,99,,1000\n"
                "2026-06-01,100,90,95,105,-1\n"
                "2026-06-02,0,101,99,100,1000\n",
                encoding="utf-8",
            )

            diagnosis = diagnose_candle_csv(path, as_of_date="2026-06-21", max_stale_days=7)

        self.assertEqual(diagnosis.symbol, "005930")
        self.assertEqual(diagnosis.status, "BLOCK")
        self.assertEqual(diagnosis.reason_code, "missing_close")
        self.assertGreaterEqual(diagnosis.issue_count, 5)
        self.assertEqual(diagnosis.latest_date, "2026-06-02")
        self.assertEqual(diagnosis.stale_days, 19)
        self.assertEqual(diagnosis.suggested_action, "FIXABLE")
        self.assertIn("missing close", diagnosis.first_issue)

    def test_diagnose_candle_csv_detects_split_or_adjustment_issue(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "000660.csv"
            path.write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-19,10000,10100,9900,10000,1000\n"
                "2026-06-20,1000,1010,990,1000,1000\n",
                encoding="utf-8",
            )

            diagnosis = diagnose_candle_csv(path, as_of_date="2026-06-21", max_stale_days=7)

        self.assertEqual(diagnosis.status, "WARN")
        self.assertEqual(diagnosis.reason_code, "suspected_split_or_adjustment_issue")
        self.assertEqual(diagnosis.suggested_action, "REVIEW")

    def test_save_data_quality_diagnostics_writes_requested_columns(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad = root / "005930.csv"
            good = root / "000660.csv"
            output = root / "diagnostics.csv"
            bad.write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-01,100,90,95,105,1000\n",
                encoding="utf-8",
            )
            good.write_text(
                "date,open,high,low,close,volume\n"
                "2026-06-20,100,101,99,100,1000\n",
                encoding="utf-8",
            )
            diagnoses = [
                diagnose_candle_csv(bad, as_of_date="2026-06-21", max_stale_days=7),
                diagnose_candle_csv(good, as_of_date="2026-06-21", max_stale_days=7),
            ]

            saved = save_data_quality_diagnostics(diagnoses, output)
            text = output.read_text(encoding="utf-8-sig")

        self.assertEqual(saved, 2)
        self.assertIn("symbol,file_path,status,reason_code,issue_count,warning_count,latest_date,stale_days,first_issue,suggested_action", text)
        self.assertIn("005930", text)
        self.assertIn("invalid_ohlc", text)

    def test_validate_universe_metadata_requires_date_and_symbol(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text("date,name\n2026-06-01,Samsung\n", encoding="utf-8")

            result = validate_universe_metadata(path)

        self.assertEqual(result.status, "BLOCK")
        self.assertIn("missing columns: symbol", "; ".join(result.issues))


if __name__ == "__main__":
    unittest.main()
