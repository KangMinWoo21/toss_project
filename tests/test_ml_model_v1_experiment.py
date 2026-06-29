import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_model_v1_experiment import (
    ML_MODEL_V1_REPORT_COLUMNS,
    build_ml_model_v1_experiment_reports,
    save_ml_model_v1_experiment_reports,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlModelV1ExperimentTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        audit = reports / "ml_baseline_feature_label_dataset_audit.csv"
        external = reports / "ml_external_feature_readiness_reaudit.csv"
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
            audit,
            "metric,status,value,reason,source,trading_allowed,production_effect\n"
            "summary,ready_for_training_scaffold,ready_for_training_scaffold,ok,derived,False,none\n"
            "train_cutoff,PASS,2024-08-30,ok,ledger,False,none\n"
            "protected_candidate_status,PASS,PAPER_REVIEW,ok,ledger,False,none\n",
        )
        _write(
            external,
            "feature_group,readiness,leakage_check,missing_rate,evidence,source,training_allowed,feature_added_to_training,post_cutoff_data_used_for_train,trading_allowed,production_effect,protected_candidate_unchanged,next_safe_action\n"
            "overall,BLOCK,PASS,mixed,financial=not_ready;news=not_ready;sentiment=not_ready,derived,False,False,False,False,none,True,do not train external features\n",
        )
        return {
            "dataset_csv": dataset,
            "dataset_audit_csv": audit,
            "external_readiness_csv": external,
        }

    def test_v1_reports_are_technical_only_paper_safe_and_no_external_features(self):
        with TemporaryDirectory() as tmp:
            reports = build_ml_model_v1_experiment_reports(**self._write_sources(Path(tmp)))

            training_by_metric = {row["metric"]: row for row in reports.training_rows}
            validation_by_metric = {row["metric"]: row for row in reports.validation_rows}
            risk_by_metric = {row["metric"]: row for row in reports.risk_rows}

            self.assertEqual(ML_MODEL_V1_REPORT_COLUMNS, list(reports.training_rows[0]))
            self.assertEqual("paper_only_model_v1_trained", training_by_metric["summary"]["status"])
            self.assertEqual("technical_only", training_by_metric["approved_feature_set"]["value"])
            self.assertEqual("False", training_by_metric["external_features_used"]["value"])
            self.assertEqual("False", training_by_metric["post_cutoff_data_used_for_train"]["value"])
            self.assertEqual("paper_only_model_v1_validated", validation_by_metric["summary"]["status"])
            self.assertIn("excess=", validation_by_metric["baseline_technical_comparison"]["value"])
            self.assertEqual("False", risk_by_metric["candidate_promotion"]["value"])
            self.assertEqual("False", risk_by_metric["trading_allowed"]["value"])
            self.assertEqual("none", risk_by_metric["production_effect"]["value"])
            self.assertIn("external_readiness=BLOCK", risk_by_metric["external_feature_policy"]["value"])
            self.assertIn("data_snooping", risk_by_metric["overfit_and_data_snooping_risk"]["metric"])

    def test_save_writes_training_validation_and_risk_reports(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = build_ml_model_v1_experiment_reports(**self._write_sources(root))
            training_csv = root / "data" / "reports" / "ml_model_v1_training_report.csv"
            validation_csv = root / "data" / "reports" / "ml_model_v1_validation_report.csv"
            risk_md = root / "data" / "reports" / "ml_model_v1_risk_report.md"

            save_ml_model_v1_experiment_reports(reports, training_csv, validation_csv, risk_md)

            self.assertEqual(ML_MODEL_V1_REPORT_COLUMNS, list(_read_rows(training_csv)[0]))
            self.assertEqual(ML_MODEL_V1_REPORT_COLUMNS, list(_read_rows(validation_csv)[0]))
            markdown = risk_md.read_text(encoding="utf-8")
            self.assertIn("Do Not Trade / Paper-Only ML Model v1", markdown)
            self.assertIn("external_features_used=False", markdown)


if __name__ == "__main__":
    unittest.main()
