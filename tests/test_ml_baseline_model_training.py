import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_baseline_model_training import (
    TRAINING_REPORT_COLUMNS,
    build_ml_baseline_model_training_report,
    save_ml_baseline_model_training_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlBaselineModelTrainingTest(unittest.TestCase):
    def _write_dataset(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        audit = reports / "ml_baseline_feature_label_dataset_audit.csv"
        rows = [
            "symbol,feature_date,label_end_date,return_1m,return_3m,return_6m,volatility_3m,volume_change_1m,price_vs_3m_sma,drawdown_3m,label_return,label,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect",
            "111111,2024-01-31,2024-02-29,0.01,0.02,0.03,0.01,0.10,0.02,0.00,0.020,positive,2024-08-30,False,False,False,none",
            "111111,2024-02-29,2024-03-29,0.02,0.03,0.04,0.01,0.10,0.02,0.00,0.015,positive,2024-08-30,False,False,False,none",
            "222222,2024-01-31,2024-02-29,-0.01,-0.02,-0.03,0.02,-0.10,-0.02,-0.03,-0.020,negative,2024-08-30,False,False,False,none",
            "222222,2024-02-29,2024-03-29,-0.02,-0.03,-0.04,0.02,-0.10,-0.02,-0.04,-0.015,negative,2024-08-30,False,False,False,none",
            "111111,2024-03-29,2024-04-30,0.03,0.04,0.05,0.01,0.10,0.03,0.00,0.018,positive,2024-08-30,False,False,False,none",
            "222222,2024-03-29,2024-04-30,-0.03,-0.04,-0.05,0.02,-0.10,-0.03,-0.05,-0.018,negative,2024-08-30,False,False,False,none",
        ]
        _write(dataset, "\n".join(rows) + "\n")
        _write(
            audit,
            "metric,status,value,reason,source,trading_allowed,production_effect\n"
            "summary,ready_for_training_scaffold,ready_for_training_scaffold,ok,derived,False,none\n"
            "train_cutoff,PASS,2024-08-30,ok,ledger,False,none\n"
            "post_cutoff_data_used_for_train,PASS,False,ok,derived,False,none\n"
            "protected_candidate_status,PASS,PAPER_REVIEW,ok,ledger,False,none\n",
        )
        return {"dataset_csv": dataset, "dataset_audit_csv": audit}

    def test_training_report_records_paper_only_cutoff_safe_scaffold(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_dataset(Path(tmp))

            rows = build_ml_baseline_model_training_report(**paths)
            by_metric = {row["metric"]: row for row in rows}

            self.assertEqual(TRAINING_REPORT_COLUMNS, list(rows[0]))
            self.assertEqual("paper_only_baseline_trained", rows[0]["status"])
            self.assertEqual("logistic_regression_sgd", by_metric["model_type"]["value"])
            self.assertEqual("2024-08-30", by_metric["train_cutoff"]["value"])
            self.assertEqual("False", by_metric["post_cutoff_data_used_for_train"]["value"])
            self.assertEqual("False", by_metric["oos_data_used"]["value"])
            self.assertEqual("False", by_metric["production_artifact_linked"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])
            self.assertEqual("PAPER_REVIEW", by_metric["protected_candidate_status"]["value"])
            self.assertEqual("PASS", by_metric["train_validation_split_cutoff_safe"]["status"])
            self.assertGreaterEqual(float(by_metric["validation_accuracy"]["value"]), 0.0)

    def test_save_writes_csv_and_markdown_with_do_not_trade_notice(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_dataset(root)
            rows = build_ml_baseline_model_training_report(**paths)
            csv_output = root / "data" / "reports" / "ml_baseline_model_training_report.csv"
            md_output = root / "data" / "reports" / "ml_baseline_model_training_report.md"

            save_ml_baseline_model_training_report(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual("summary", saved[0]["metric"])
            self.assertIn("Do Not Trade / Paper-Only Baseline Training", markdown)
            self.assertIn("production artifact", markdown)


if __name__ == "__main__":
    unittest.main()
