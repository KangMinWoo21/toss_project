import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_model_observation_status import (
    ML_MODEL_OBSERVATION_STATUS_COLUMNS,
    build_ml_model_observation_status_report,
    save_ml_model_observation_status_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlModelObservationStatusTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        shadow = reports / "ml_shadow_scoring_report.csv"
        validation = reports / "ml_model_v1_validation_report.csv"
        _write(
            shadow,
            "rank,symbol,feature_date,score_type,shadow_score,score_bucket,model_version,source_model_report,order_output,broker_submission,monthly_plan_regenerated,candidate_promotion,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "1,111111,2024-05-31,technical_only_shadow_score,0.600000,medium,ml_model_v1_technical_only,training.csv,False,False,False,False,False,none,True\n"
            "2,222222,2024-05-31,technical_only_shadow_score,0.400000,low,ml_model_v1_technical_only,training.csv,False,False,False,False,False,none,True\n",
        )
        _write(
            validation,
            "metric,status,value,reason,source,post_cutoff_data_used_for_train,external_features_used,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "drawdown,PASS,-0.1200,ok,derived,False,False,False,none,True\n"
            "turnover,PASS,turnover=0.2500,ok,derived,False,False,False,none,True\n",
        )
        return {
            "shadow_scoring_csv": shadow,
            "model_v1_validation_csv": validation,
        }

    def test_observation_status_records_metrics_without_promotion(self):
        with TemporaryDirectory() as tmp:
            rows = build_ml_model_observation_status_report(**self._write_sources(Path(tmp)))

            self.assertEqual(ML_MODEL_OBSERVATION_STATUS_COLUMNS, list(rows[0]))
            by_metric = {row["metric"]: row for row in rows}
            self.assertEqual("paper_only_observation_started", by_metric["summary"]["status"])
            self.assertEqual("1", by_metric["observation_months"]["value"])
            self.assertEqual("False", by_metric["sufficient_observation_months"]["value"])
            self.assertEqual("not_mature_shadow_only", by_metric["performance_stability"]["value"])
            self.assertEqual("-0.1200", by_metric["drawdown"]["value"])
            self.assertEqual("turnover=0.2500", by_metric["turnover"]["value"])
            self.assertEqual("symbols=2;months=1", by_metric["coverage"]["value"])
            for row in rows:
                self.assertEqual("False", row["candidate_promotion"])
                self.assertEqual("False", row["trading_allowed"])
                self.assertEqual("none", row["production_effect"])
                self.assertEqual("True", row["protected_candidate_unchanged"])

    def test_save_writes_observation_csv_and_markdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = build_ml_model_observation_status_report(**self._write_sources(root))
            csv_output = root / "data" / "reports" / "ml_model_observation_status.csv"
            md_output = root / "data" / "reports" / "ml_model_observation_status.md"

            save_ml_model_observation_status_report(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(ML_MODEL_OBSERVATION_STATUS_COLUMNS, list(saved[0]))
            self.assertIn("Paper-Only Observation Status", markdown)
            self.assertIn("Observation maturity: `False`", markdown)
            self.assertIn("Production effect: `none`", markdown)


if __name__ == "__main__":
    unittest.main()
