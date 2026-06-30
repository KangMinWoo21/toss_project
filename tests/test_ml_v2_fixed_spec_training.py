import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_v2_fixed_spec_training import (
    ML_V2_FIXED_SPEC_REPORT_COLUMNS,
    build_ml_v2_fixed_spec_training_reports,
    save_ml_v2_fixed_spec_training_reports,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlV2FixedSpecTrainingTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        feature_csv = reports / "formulaic_alpha_broader_materialized_feature_stage1.csv"
        label_csv = reports / "ml_baseline_feature_label_sample.csv"
        readiness_csv = reports / "ml_v2_fixed_spec_training_readiness_gate.csv"
        feature_lines = [
            "chunk_id,sample_id,alpha_family,formula_string,formula_hash,feature_hash,feature_row_hash,symbol,feature_date,date_group,feature_value,missing_reason,operator_version,parameter_summary,feature_visible_at,feature_usable_from,source_cutoff_time,label_horizon,label_start_date,label_end_date,purge_window_days,embargo_window_days,pit_check,label_isolation_check,missingness_policy,evaluation_performed,training_allowed_now,candidate_promotion,production_effect,trading_allowed,notes",
        ]
        for feature_date in ["2024-01-31", "2024-02-29", "2024-03-29", "2024-04-30", "2024-05-31"]:
            for symbol, base in [("111111", 1.0), ("222222", -1.0)]:
                for index, formula_hash in enumerate(["f1", "f2"]):
                    value = base + index * 0.1
                    feature_lines.append(
                        f"stage1,sample,alpha,formula,{formula_hash},hash,rowhash,{symbol},{feature_date},{feature_date[:7]},{value},available,op,params,,,,,,,,,PASS,PASS,policy,False,False,False,none,False,note"
                    )
        _write(feature_csv, "\n".join(feature_lines) + "\n")
        label_lines = [
            "symbol,feature_date,label_end_date,return_1m,label_return,label,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect",
        ]
        for feature_date in ["2024-01-31", "2024-02-29", "2024-03-29", "2024-04-30", "2024-05-31"]:
            label_lines.append(f"111111,{feature_date},2024-06-28,0.01,0.01,positive,2024-12-31,False,False,False,none")
            label_lines.append(f"222222,{feature_date},2024-06-28,-0.01,-0.01,negative,2024-12-31,False,False,False,none")
        _write(label_csv, "\n".join(label_lines) + "\n")
        _write(
            readiness_csv,
            "gate_id,readiness_group,requirement,evidence,status,gate_result,training_allowed_now,paper_only_training_allowed_next,validation_allowed_now,model_training_performed,validation_run_performed,candidate_creation,candidate_promotion,broker_submission,order_execution,production_effect,trading_allowed,recommended_next_action,notes\n"
            "g,final,ok,source,PASS,ALLOW_PAPER_ONLY_TRAINING,False,True,False,False,False,False,False,False,False,none,False,run,next\n",
        )
        return {"feature_csv": feature_csv, "label_csv": label_csv, "readiness_csv": readiness_csv}

    def test_fixed_spec_training_runs_without_selection_or_production_effect(self):
        with TemporaryDirectory() as tmp:
            reports = build_ml_v2_fixed_spec_training_reports(**self._write_sources(Path(tmp)))

            training_by_metric = {row["metric"]: row for row in reports.training_rows}
            validation_by_metric = {row["metric"]: row for row in reports.validation_rows}

            self.assertEqual(ML_V2_FIXED_SPEC_REPORT_COLUMNS, list(reports.training_rows[0]))
            self.assertEqual("paper_only_ml_v2_fixed_spec_trained", training_by_metric["summary"]["status"])
            self.assertEqual("paper_only_ml_v2_fixed_spec_validated", validation_by_metric["summary"]["status"])
            self.assertEqual("False", training_by_metric["model_artifact_written"]["value"])
            self.assertEqual("False", validation_by_metric["formula_selection_used"]["value"])
            self.assertEqual("False", validation_by_metric["model_selection_used"]["value"])
            self.assertEqual("False", validation_by_metric["hyperparameter_sweep_used"]["value"])
            self.assertEqual("False", validation_by_metric["trading_allowed"]["value"])
            self.assertEqual("none", validation_by_metric["production_effect"]["value"])

    def test_save_writes_training_validation_and_markdown_reports(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = build_ml_v2_fixed_spec_training_reports(**self._write_sources(root))
            training_csv = root / "data" / "reports" / "ml_v2_fixed_spec_paper_training_report.csv"
            validation_csv = root / "data" / "reports" / "ml_v2_fixed_spec_paper_validation_report.csv"
            markdown = root / "data" / "reports" / "ml_v2_fixed_spec_paper_training_report.md"

            save_ml_v2_fixed_spec_training_reports(reports, training_csv, validation_csv, markdown)

            self.assertEqual(ML_V2_FIXED_SPEC_REPORT_COLUMNS, list(_read_rows(training_csv)[0]))
            self.assertEqual(ML_V2_FIXED_SPEC_REPORT_COLUMNS, list(_read_rows(validation_csv)[0]))
            text = markdown.read_text(encoding="utf-8")
            self.assertIn("Do Not Trade / Paper-Only ML v2", text)
            self.assertIn("Formula selection used: `False`", text)


if __name__ == "__main__":
    unittest.main()
