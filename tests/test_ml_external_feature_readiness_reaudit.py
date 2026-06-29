import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_external_feature_readiness_reaudit import (
    EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS,
    build_ml_external_feature_readiness_reaudit,
    save_ml_external_feature_readiness_reaudit,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlExternalFeatureReadinessReauditTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        financial = reports / "ml_financial_feature_merge_audit.csv"
        news = reports / "ml_news_event_schema_plan.csv"
        sentiment = reports / "ml_sentiment_scoring_plan.csv"
        _write(
            financial,
            "metric,status,value,reason,source,post_cutoff_data_used_for_train,feature_added_to_training,training_allowed_now,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "join_coverage,WARN,0/5,coverage missing,derived,False,False,False,False,none,True\n"
            "missing_rate,WARN,1.0000,missing all,derived,False,False,False,False,none,True\n"
            "leakage_check,PASS,safe,derived,False,False,False,False,none,True\n",
        )
        _write(
            news,
            "event_group,source_name,candidate_features,schema_fields,timestamp_fields,dedupe_rule,lineage_rule,api_key_required,fetch_allowed_now,training_allowed_now,feature_added_to_training,trading_allowed,production_effect,pit_required,usable_from_required,source_coverage_risk,leakage_risk,data_quality_risk,current_status,next_safe_action\n"
            "naver_news_events,naver_news_search_api,event_count_1m,source_id;symbol;headline;text_hash,published_at;collected_at;visible_at;usable_from,compute text_hash,append only,mixed,False,False,False,False,none,True,True,coverage risk,leakage risk,data risk,schema_plan_only,no fetch\n",
        )
        _write(
            sentiment,
            "component,source_name,model_version,candidate_features,schema_fields,timestamp_fields,sentiment_score_range,lineage_rule,fetch_allowed_now,training_allowed_now,model_training_allowed,feature_added_to_training,trading_allowed,production_effect,pit_required,usable_from_required,llm_risk_note,leakage_risk,data_quality_risk,current_status,next_safe_action\n"
            "lexicon_scoring,news_events_schema_rows,rule_lexicon_v1,sentiment_score,model_version;sentiment_score,published_at;collected_at;visible_at;scored_at;usable_from,-1.0_to_1.0,score only safe rows,False,False,False,False,False,none,True,True,No FinBERT or LLM scoring,leakage risk,data risk,schema_plan_only,no training\n",
        )
        return {
            "financial_merge_audit_csv": financial,
            "news_schema_plan_csv": news,
            "sentiment_scoring_plan_csv": sentiment,
        }

    def test_reaudit_classifies_external_features_not_ready_and_paper_only(self):
        with TemporaryDirectory() as tmp:
            result = build_ml_external_feature_readiness_reaudit(**self._write_sources(Path(tmp)))
            by_group = {row["feature_group"]: row for row in result.rows}

            self.assertEqual(EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS, list(result.rows[0]))
            self.assertEqual("not_ready", by_group["financial"]["readiness"])
            self.assertEqual("not_ready", by_group["news"]["readiness"])
            self.assertEqual("not_ready", by_group["sentiment"]["readiness"])
            self.assertEqual("BLOCK", by_group["overall"]["readiness"])
            self.assertEqual("PASS", by_group["financial"]["leakage_check"])
            self.assertEqual("1.0000", by_group["financial"]["missing_rate"])
            self.assertIn("schema_plan_only", by_group["news"]["evidence"])
            self.assertIn("rule_lexicon_v1", by_group["sentiment"]["evidence"])

            for row in result.rows:
                self.assertEqual("False", row["training_allowed"])
                self.assertEqual("False", row["feature_added_to_training"])
                self.assertEqual("False", row["post_cutoff_data_used_for_train"])
                self.assertEqual("False", row["trading_allowed"])
                self.assertEqual("none", row["production_effect"])
                self.assertEqual("True", row["protected_candidate_unchanged"])

    def test_save_writes_phase_10_reports(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_ml_external_feature_readiness_reaudit(**self._write_sources(root))
            csv_output = root / "data" / "reports" / "ml_external_feature_readiness_reaudit.csv"
            md_output = root / "data" / "reports" / "ml_external_feature_readiness_reaudit.md"

            save_ml_external_feature_readiness_reaudit(result, csv_output, md_output)

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / Re-Audit Only", markdown)
            self.assertIn("training_allowed=False", markdown)
            self.assertIn("financial", markdown)
            self.assertIn("sentiment", markdown)


if __name__ == "__main__":
    unittest.main()
