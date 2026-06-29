import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_shadow_scoring import (
    ML_SHADOW_SCORING_COLUMNS,
    build_ml_shadow_scoring_report,
    save_ml_shadow_scoring_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlShadowScoringTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        audit = reports / "ml_baseline_feature_label_dataset_audit.csv"
        v1_training = reports / "ml_model_v1_training_report.csv"
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
            v1_training,
            "metric,status,value,reason,source,post_cutoff_data_used_for_train,external_features_used,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "summary,paper_only_model_v1_trained,paper_only_model_v1_trained,ok,derived,False,False,False,none,True\n"
            "approved_feature_set,PASS,technical_only,ok,derived,False,False,False,none,True\n"
            "external_features_used,PASS,False,ok,derived,False,False,False,none,True\n"
            "post_cutoff_data_used_for_train,PASS,False,ok,derived,False,False,False,none,True\n",
        )
        return {
            "dataset_csv": dataset,
            "dataset_audit_csv": audit,
            "model_v1_training_csv": v1_training,
        }

    def test_shadow_scoring_is_human_readable_and_never_order_output(self):
        with TemporaryDirectory() as tmp:
            rows = build_ml_shadow_scoring_report(**self._write_sources(Path(tmp)))

            self.assertEqual(ML_SHADOW_SCORING_COLUMNS, list(rows[0]))
            self.assertGreaterEqual(len(rows), 2)
            scores = [float(row["shadow_score"]) for row in rows]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertTrue(all(row["score_type"] == "technical_only_shadow_score" for row in rows))
            for row in rows:
                self.assertEqual("False", row["order_output"])
                self.assertEqual("False", row["broker_submission"])
                self.assertEqual("False", row["monthly_plan_regenerated"])
                self.assertEqual("False", row["candidate_promotion"])
                self.assertEqual("False", row["trading_allowed"])
                self.assertEqual("none", row["production_effect"])
                self.assertEqual("True", row["protected_candidate_unchanged"])

    def test_save_writes_shadow_csv_and_markdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = build_ml_shadow_scoring_report(**self._write_sources(root))
            csv_output = root / "data" / "reports" / "ml_shadow_scoring_report.csv"
            md_output = root / "data" / "reports" / "ml_shadow_scoring_report.md"

            save_ml_shadow_scoring_report(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(ML_SHADOW_SCORING_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / Shadow Scoring Only", markdown)
            self.assertIn("No order output", markdown)


if __name__ == "__main__":
    unittest.main()
