import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_model_research_packet import (
    ML_MODEL_RESEARCH_PACKET_COLUMNS,
    build_ml_model_research_packet,
    save_ml_model_research_packet,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlModelResearchPacketTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        paths = {
            "dataset_audit_csv": reports / "ml_baseline_feature_label_dataset_audit.csv",
            "baseline_training_csv": reports / "ml_baseline_model_training_report.csv",
            "baseline_validation_csv": reports / "ml_baseline_validation_report.csv",
            "feature_importance_csv": reports / "ml_feature_importance_report.csv",
            "failure_analysis_csv": reports / "ml_failure_analysis_report.csv",
            "financial_merge_audit_csv": reports / "ml_financial_feature_merge_audit.csv",
            "news_schema_csv": reports / "ml_news_event_schema_plan.csv",
            "sentiment_plan_csv": reports / "ml_sentiment_scoring_plan.csv",
            "external_readiness_csv": reports / "ml_external_feature_readiness_reaudit.csv",
            "model_v1_training_csv": reports / "ml_model_v1_training_report.csv",
            "model_v1_validation_csv": reports / "ml_model_v1_validation_report.csv",
            "shadow_scoring_csv": reports / "ml_shadow_scoring_report.csv",
            "observation_status_csv": reports / "ml_model_observation_status.csv",
            "production_readiness_csv": reports / "production_readiness.csv",
        }
        _write(
            paths["dataset_audit_csv"],
            "metric,status,value,reason,source,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "summary,PASS,ready_for_training_scaffold,ok,local,2026-06-18,False,False,False,none,True\n"
            "label_row_count,PASS,69915,ok,local,2026-06-18,False,False,False,none,True\n"
            "feature_list,PASS,return_1m;return_3m;return_6m;volatility_3m,ok,local,2026-06-18,False,False,False,none,True\n",
        )
        _write(
            paths["baseline_training_csv"],
            "metric,status,value,reason,source,post_cutoff_data_used_for_train,oos_data_used,production_artifact_linked,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "summary,PASS,paper_only_baseline_trained,ok,local,False,False,False,False,none,True\n"
            "model_type,PASS,logistic_regression_sgd,ok,local,False,False,False,False,none,True\n",
        )
        _write(
            paths["baseline_validation_csv"],
            "metric,status,value,reason,source,post_cutoff_data_used_for_validation,oos_rerun,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "summary,PASS,paper_only_validation_complete,ok,local,False,False,False,none,True\n"
            "leakage_check,PASS,PASS,ok,local,False,False,False,none,True\n"
            "drawdown,PASS,-0.1000,ok,local,False,False,False,none,True\n",
        )
        _write(paths["feature_importance_csv"], "metric,status,value,reason,source,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,PASS,feature_importance_recorded,ok,local,False,none,True\n")
        _write(paths["failure_analysis_csv"], "metric,status,value,reason,source,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,WARN,failure_cases_recorded,overfit risk noted,local,False,none,True\n")
        _write(paths["financial_merge_audit_csv"], "metric,status,value,reason,source,training_allowed_now,feature_added_to_training,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,WARN,not_ready,missing_rate=1.0000,local,False,False,False,none,True\n")
        _write(paths["news_schema_csv"], "metric,status,value,reason,source,fetch_allowed_now,training_allowed_now,feature_added_to_training,trading_allowed,production_effect\nsummary,PASS,schema_plan_only,plan-only,local,False,False,False,False,none\n")
        _write(paths["sentiment_plan_csv"], "metric,status,value,reason,source,training_allowed_now,model_training_allowed,feature_added_to_training,trading_allowed,production_effect\nsummary,PASS,rule_lexicon_plan_only,FinBERT/LLM later-stage,local,False,False,False,False,none\n")
        _write(paths["external_readiness_csv"], "metric,status,value,reason,source,training_allowed,feature_added_to_training,post_cutoff_data_used_for_train,trading_allowed,production_effect\nsummary,BLOCK,BLOCK,financial/news/sentiment not_ready,local,False,False,False,False,none\n")
        _write(paths["model_v1_training_csv"], "metric,status,value,reason,source,post_cutoff_data_used_for_train,external_features_used,candidate_promotion,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,PASS,paper_only_model_v1_trained,ok,local,False,False,False,False,none,True\napproved_feature_set,PASS,technical_only,ok,local,False,False,False,False,none,True\n")
        _write(paths["model_v1_validation_csv"], "metric,status,value,reason,source,post_cutoff_data_used_for_train,external_features_used,candidate_promotion,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,PASS,paper_only_model_v1_validated,ok,local,False,False,False,False,none,True\nleakage_check,PASS,PASS,ok,local,False,False,False,False,none,True\n")
        _write(paths["shadow_scoring_csv"], "rank,symbol,feature_date,score_type,shadow_score,score_bucket,model_version,source_model_report,order_output,broker_submission,monthly_plan_regenerated,candidate_promotion,trading_allowed,production_effect,protected_candidate_unchanged\n1,111111,2026-06-18,technical_only_shadow_score,0.600000,medium,model.csv,local,False,False,False,False,False,none,True\n")
        _write(paths["observation_status_csv"], "metric,status,value,reason,source,observation_basis,post_cutoff_train_leakage,observation_months,sufficient_observation_months,performance_stability,drawdown,turnover,coverage,candidate_promotion,trading_allowed,production_effect,protected_candidate_unchanged\nsummary,paper_only_observation_mature,paper_only_observation_mature,ok,local,historical_backfill,PASS,101,True,historical_backfill_stable,-0.6520,turnover=0.1700,symbols=5;months=101,False,False,none,True\n")
        _write(paths["production_readiness_csv"], "check,status,details\nsummary,BLOCK,not live-ready\n")
        return paths

    def test_packet_consolidates_required_sections_and_safety_gates(self):
        with TemporaryDirectory() as tmp:
            rows = build_ml_model_research_packet(**self._write_sources(Path(tmp)))

            self.assertEqual(ML_MODEL_RESEARCH_PACKET_COLUMNS, list(rows[0]))
            sections = {row["section"]: row for row in rows}
            for section in (
                "model_completion_status",
                "data_lineage",
                "baseline_feature_label_dataset",
                "baseline_model_training",
                "validation_results",
                "feature_importance_failure_analysis",
                "opendart_financial_features",
                "news_schema",
                "sentiment_schema",
                "external_feature_readiness",
                "model_v1_technical_only",
                "shadow_scoring",
                "observation_status",
                "leakage_checks",
                "overfit_data_snooping_risk",
                "final_recommendation",
            ):
                self.assertIn(section, sections)
            self.assertEqual("paper_only_complete_not_live_ready", sections["model_completion_status"]["value"])
            self.assertEqual("not_ready", sections["opendart_financial_features"]["value"])
            self.assertEqual("not_ready", sections["news_schema"]["value"])
            self.assertEqual("not_ready", sections["sentiment_schema"]["value"])
            for row in rows:
                self.assertEqual("False", row["trading_allowed"])
                self.assertEqual("none", row["production_effect"])
                self.assertEqual("False", row["candidate_promotion"])
                self.assertEqual("False", row["broker_submission"])
                self.assertEqual("False", row["order_execution"])
                self.assertEqual("False", row["production_readiness_change"])
                self.assertEqual("True", row["production_block_retained"])
                self.assertEqual("True", row["protected_candidate_unchanged"])

    def test_save_writes_packet_csv_and_markdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = build_ml_model_research_packet(**self._write_sources(root))
            csv_output = root / "data" / "reports" / "ml_model_research_packet.csv"
            md_output = root / "data" / "reports" / "ml_model_research_packet.md"

            save_ml_model_research_packet(rows, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(ML_MODEL_RESEARCH_PACKET_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / Research Packet Only", markdown)
            self.assertIn("paper_only_complete_not_live_ready", markdown)
            self.assertIn("trading_allowed=False", markdown)


if __name__ == "__main__":
    unittest.main()
