import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_explainability_failure_analysis import (
    FAILURE_ANALYSIS_COLUMNS,
    FEATURE_IMPORTANCE_COLUMNS,
    build_ml_explainability_failure_analysis_reports,
    save_ml_explainability_failure_analysis_reports,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlExplainabilityFailureAnalysisTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        validation = reports / "ml_baseline_validation_report.csv"
        rows = [
            "symbol,feature_date,label_end_date,return_1m,return_3m,return_6m,volatility_3m,volume_change_1m,price_vs_3m_sma,drawdown_3m,label_return,label,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect",
            "111111,2024-01-31,2024-02-29,0.01,0.02,0.03,0.01,0.10,0.02,0.00,0.020,positive,2024-08-30,False,False,False,none",
            "222222,2024-01-31,2024-02-29,-0.01,-0.02,-0.03,0.02,-0.10,-0.02,-0.03,-0.020,negative,2024-08-30,False,False,False,none",
            "111111,2024-02-29,2024-03-29,0.02,0.03,0.04,0.01,0.10,0.02,0.00,-0.015,negative,2024-08-30,False,False,False,none",
            "222222,2024-02-29,2024-03-29,-0.02,-0.03,-0.04,0.02,-0.10,-0.02,-0.04,0.015,positive,2024-08-30,False,False,False,none",
            "111111,2024-03-29,2024-04-30,0.03,0.04,0.05,0.01,0.10,0.03,0.00,0.018,positive,2024-08-30,False,False,False,none",
            "222222,2024-03-29,2024-04-30,-0.03,-0.04,-0.05,0.02,-0.10,-0.03,-0.05,-0.018,negative,2024-08-30,False,False,False,none",
        ]
        _write(dataset, "\n".join(rows) + "\n")
        _write(
            validation,
            "metric,status,value,reason,source,trading_allowed,production_effect\n"
            "summary,paper_only_validation_complete,paper_only_validation_complete,ok,derived,False,none\n"
            "leakage_check,PASS,True,ok,derived,False,none\n"
            "pit_universe_check,PASS,True,ok,derived,False,none\n"
            "feature_availability_check,PASS,missing_rate=0.0,ok,dataset,False,none\n"
            "train_cutoff,PASS,2024-08-30,ok,training,False,none\n"
            "protected_candidate_status,PASS,PAPER_REVIEW,ok,training,False,none\n",
        )
        return {"dataset_csv": dataset, "validation_report_csv": validation}

    def test_reports_record_feature_importance_failures_and_safety(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_sources(Path(tmp))

            feature_rows, failure_rows = build_ml_explainability_failure_analysis_reports(**paths)

            self.assertEqual(FEATURE_IMPORTANCE_COLUMNS, list(feature_rows[0]))
            self.assertEqual(FAILURE_ANALYSIS_COLUMNS, list(failure_rows[0]))
            self.assertEqual("1", feature_rows[0]["rank"])
            self.assertIn(feature_rows[0]["feature"], {row["feature"] for row in feature_rows})
            self.assertEqual("False", feature_rows[0]["trading_allowed"])
            self.assertEqual("none", feature_rows[0]["production_effect"])
            self.assertEqual("PAPER_REVIEW", feature_rows[0]["protected_candidate_status"])
            self.assertIn("overfit", feature_rows[0]["overfit_risk_note"])
            self.assertTrue(any(row["row_type"] == "failure_symbol" for row in failure_rows))
            self.assertTrue(any(row["row_type"] == "failure_month" for row in failure_rows))
            self.assertTrue(any(row["row_type"] == "regime_summary" for row in failure_rows))
            self.assertTrue(all(row["candidate_modified"] == "False" for row in failure_rows))
            self.assertTrue(all(row["trading_allowed"] == "False" for row in failure_rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in failure_rows))

    def test_save_writes_feature_importance_and_failure_csvs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_sources(root)
            feature_rows, failure_rows = build_ml_explainability_failure_analysis_reports(**paths)
            feature_csv = root / "data" / "reports" / "ml_feature_importance_report.csv"
            failure_csv = root / "data" / "reports" / "ml_failure_analysis_report.csv"

            save_ml_explainability_failure_analysis_reports(feature_rows, failure_rows, feature_csv, failure_csv)

            self.assertEqual("1", _read_rows(feature_csv)[0]["rank"])
            self.assertTrue(any(row["row_type"] == "failure_symbol" for row in _read_rows(failure_csv)))


if __name__ == "__main__":
    unittest.main()
