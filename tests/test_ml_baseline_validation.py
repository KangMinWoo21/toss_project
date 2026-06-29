import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_baseline_validation import (
    VALIDATION_REPORT_COLUMNS,
    build_ml_baseline_validation_report,
    save_ml_baseline_validation_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlBaselineValidationTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        training = reports / "ml_baseline_model_training_report.csv"
        rows = [
            "symbol,feature_date,label_end_date,return_1m,return_3m,return_6m,volatility_3m,volume_change_1m,price_vs_3m_sma,drawdown_3m,label_return,label,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect",
            "111111,2024-01-31,2024-02-29,0.01,0.02,0.03,0.01,0.10,0.02,0.00,0.020,positive,2024-08-30,False,False,False,none",
            "222222,2024-01-31,2024-02-29,-0.01,-0.02,-0.03,0.02,-0.10,-0.02,-0.03,-0.020,negative,2024-08-30,False,False,False,none",
            "111111,2024-02-29,2024-03-29,0.02,0.03,0.04,0.01,0.10,0.02,0.00,0.015,positive,2024-08-30,False,False,False,none",
            "222222,2024-02-29,2024-03-29,-0.02,-0.03,-0.04,0.02,-0.10,-0.02,-0.04,-0.015,negative,2024-08-30,False,False,False,none",
            "111111,2024-03-29,2024-04-30,0.03,0.04,0.05,0.01,0.10,0.03,0.00,0.018,positive,2024-08-30,False,False,False,none",
            "222222,2024-03-29,2024-04-30,-0.03,-0.04,-0.05,0.02,-0.10,-0.03,-0.05,-0.018,negative,2024-08-30,False,False,False,none",
        ]
        _write(dataset, "\n".join(rows) + "\n")
        _write(
            training,
            "metric,status,value,reason,source,trading_allowed,production_effect\n"
            "summary,paper_only_baseline_trained,paper_only_baseline_trained,ok,derived,False,none\n"
            "model_type,PASS,logistic_regression_sgd,ok,derived,False,none\n"
            "train_cutoff,PASS,2024-08-30,ok,dataset,False,none\n"
            "post_cutoff_data_used_for_train,PASS,False,ok,derived,False,none\n"
            "oos_data_used,PASS,False,ok,derived,False,none\n"
            "production_artifact_linked,PASS,False,ok,derived,False,none\n"
            "protected_candidate_status,PASS,PAPER_REVIEW,ok,dataset,False,none\n",
        )
        return {"dataset_csv": dataset, "training_report_csv": training}

    def test_validation_report_records_walk_forward_safety_and_metrics(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_sources(Path(tmp))

            rows = build_ml_baseline_validation_report(**paths)
            by_metric = {row["metric"]: row for row in rows}

            self.assertEqual(VALIDATION_REPORT_COLUMNS, list(rows[0]))
            self.assertEqual("paper_only_validation_complete", rows[0]["status"])
            self.assertEqual("PASS", by_metric["leakage_check"]["status"])
            self.assertEqual("PASS", by_metric["pit_universe_check"]["status"])
            self.assertEqual("PASS", by_metric["feature_availability_check"]["status"])
            self.assertEqual("False", by_metric["post_cutoff_data_used_for_validation"]["value"])
            self.assertEqual("False", by_metric["oos_rerun"]["value"])
            self.assertEqual("False", by_metric["candidate_modified"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])
            self.assertEqual("PAPER_REVIEW", by_metric["protected_candidate_status"]["value"])
            self.assertIn("months=", by_metric["walk_forward_months"]["value"])
            self.assertGreaterEqual(float(by_metric["hit_rate"]["value"]), 0.0)
            self.assertIn("benchmark_return=", by_metric["benchmark_relative_performance"]["value"])
            self.assertIn("turnover=", by_metric["turnover"]["value"])

    def test_save_writes_csv_and_markdown_with_do_not_trade_notice(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_sources(root)
            rows = build_ml_baseline_validation_report(**paths)
            csv_output = root / "data" / "reports" / "ml_baseline_validation_report.csv"
            md_output = root / "data" / "reports" / "ml_baseline_validation_report.md"

            save_ml_baseline_validation_report(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual("summary", saved[0]["metric"])
            self.assertIn("Do Not Trade / Paper-Only ML Validation", markdown)
            self.assertIn("candidate modification", markdown)


if __name__ == "__main__":
    unittest.main()
