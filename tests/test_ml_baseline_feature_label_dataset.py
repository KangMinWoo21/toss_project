import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_baseline_feature_label_dataset import (
    FEATURE_LABEL_COLUMNS,
    build_ml_baseline_feature_label_dataset,
    save_ml_baseline_feature_label_dataset_audit,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlBaselineFeatureLabelDatasetTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        data_dir = root / "data" / "krx_expanded"
        reports = root / "data" / "reports"
        metadata = root / "data" / "krx_metadata"

        dates = [
            "2024-01-31",
            "2024-02-29",
            "2024-03-29",
            "2024-04-30",
            "2024-05-31",
            "2024-06-28",
            "2024-07-31",
            "2024-08-30",
            "2024-09-30",
        ]
        for symbol, base, step in (("111111", 100.0, 2.0), ("222222", 200.0, -3.0)):
            rows = ["date,open,high,low,close,volume"]
            for index, day in enumerate(dates):
                close = base + step * index
                rows.append(f"{day},{close - 1},{close + 1},{close - 2},{close},{1000 + index}")
            _write(data_dir / f"{symbol}.csv", "\n".join(rows) + "\n")

        ledger = reports / "monthly_candidate_research_ledger.csv"
        quality = reports / "monthly_validation_data_quality.csv"
        exclusions = reports / "data_quality_excluded_symbols.csv"
        universe = reports / "monthly_universe_price_coverage.csv"
        pit = metadata / "krx_universe_monthly.csv"
        _write(
            ledger,
            "candidate_id,status,protected_from_tuning,baseline_cutoff\n"
            "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244,PAPER_REVIEW,True,2024-08-30\n",
        )
        _write(
            quality,
            "symbol,status,first_date,last_date,rows,duplicate_dates,nonpositive_price_rows,reason\n"
            "111111,PASS,2024-01-31,2024-09-30,9,0,0,passed\n"
            "222222,PASS,2024-01-31,2024-09-30,9,0,0,passed\n"
            "333333,BLOCK,2024-01-31,2024-09-30,9,0,1,bad price\n",
        )
        _write(exclusions, "symbol,status,reason\n333333,BLOCK,bad price\n")
        _write(
            universe,
            "date,universe_symbols,price_symbols,covered_symbols,excluded_symbols,missing_symbols,coverage_pct,status,missing_preview,excluded_preview\n"
            "2024-01-31,2,2,2,0,0,100,PASS,,\n",
        )
        _write(pit, "date,symbol\n2024-01-31,111111\n2024-01-31,222222\n")
        return {
            "price_dir": data_dir,
            "candidate_ledger_csv": ledger,
            "data_quality_csv": quality,
            "data_quality_exclusions_csv": exclusions,
            "universe_coverage_csv": universe,
            "pit_universe_csv": pit,
        }

    def test_dataset_audit_records_phase_one_safety_conditions(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_sources(Path(tmp))

            result = build_ml_baseline_feature_label_dataset(**paths)
            by_metric = {row["metric"]: row for row in result.audit_rows}

            self.assertEqual("ready_for_training_scaffold", result.audit_rows[0]["status"])
            self.assertEqual("2024-08-30", by_metric["train_cutoff"]["value"])
            self.assertEqual("False", by_metric["post_cutoff_data_used_for_train"]["value"])
            self.assertEqual("False", by_metric["training_ran"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])
            self.assertEqual("PAPER_REVIEW", by_metric["protected_candidate_status"]["value"])
            self.assertEqual("True", by_metric["pit_universe_available"]["value"])
            self.assertEqual("14", by_metric["label_row_count"]["value"])
            self.assertIn("return_1m=", by_metric["feature_missing_rates"]["value"])
            self.assertIn("positive=7", by_metric["label_distribution"]["value"])
            self.assertIn("negative=7", by_metric["label_distribution"]["value"])
            self.assertEqual("14", str(len(result.sample_rows)))
            self.assertEqual(FEATURE_LABEL_COLUMNS, list(result.sample_rows[0]))
            self.assertTrue(all(row["trading_allowed"] == "False" for row in result.sample_rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in result.sample_rows))
            self.assertTrue(all(row["training_ran"] == "False" for row in result.sample_rows))

    def test_save_writes_csv_markdown_and_sample_without_training(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_sources(root)
            result = build_ml_baseline_feature_label_dataset(**paths)
            audit_csv = root / "data" / "reports" / "ml_baseline_feature_label_dataset_audit.csv"
            audit_md = root / "data" / "reports" / "ml_baseline_feature_label_dataset_audit.md"
            sample_csv = root / "data" / "reports" / "ml_baseline_feature_label_sample.csv"

            save_ml_baseline_feature_label_dataset_audit(result, audit_csv, audit_md, sample_csv)

            audit_rows = _read_rows(audit_csv)
            sample_rows = _read_rows(sample_csv)
            markdown = audit_md.read_text(encoding="utf-8")
            self.assertEqual("summary", audit_rows[0]["metric"])
            self.assertEqual("False", {row["metric"]: row for row in audit_rows}["training_ran"]["value"])
            self.assertEqual("14", str(len(sample_rows)))
            self.assertIn("Do Not Trade / Feature-Label Dataset Only", markdown)
            self.assertIn("does not train models", markdown)


if __name__ == "__main__":
    unittest.main()
