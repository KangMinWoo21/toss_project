import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_external_feature_readiness_plan import (
    PLAN_COLUMNS,
    build_ml_external_feature_readiness_plan,
    save_ml_external_feature_readiness_plan,
)


REQUIRED_COLUMNS = [
    "source_group",
    "source_name",
    "candidate_features",
    "expected_use",
    "priority",
    "api_key_required",
    "fetch_allowed_now",
    "training_allowed_now",
    "production_effect",
    "trading_allowed",
    "pit_required",
    "usable_from_required",
    "timestamp_fields",
    "leakage_risk",
    "data_quality_risk",
    "current_status",
    "next_safe_action",
]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlExternalFeatureReadinessPlanTest(unittest.TestCase):
    def test_plan_rows_are_deterministic_and_plan_only(self):
        first = build_ml_external_feature_readiness_plan()
        second = build_ml_external_feature_readiness_plan()

        self.assertEqual(first, second)
        self.assertEqual(REQUIRED_COLUMNS, PLAN_COLUMNS)
        self.assertEqual(4, len(first))

        by_group = {row["source_group"]: row for row in first}
        self.assertEqual("planned_high_priority", by_group["OpenDART financial_disclosure"]["current_status"])
        self.assertEqual("planned_after_financials", by_group["news_events"]["current_status"])
        self.assertEqual("planned_after_news_schema", by_group["sentiment"]["current_status"])
        self.assertEqual("later_stage_not_ready", by_group["sns_community"]["current_status"])

        for row in first:
            self.assertEqual("False", row["fetch_allowed_now"])
            self.assertEqual("False", row["training_allowed_now"])
            self.assertEqual("False", row["trading_allowed"])
            self.assertEqual("none", row["production_effect"])
            self.assertEqual("True", row["pit_required"])
            self.assertEqual("True", row["usable_from_required"])
            self.assertTrue(row["timestamp_fields"])

    def test_required_feature_and_timestamp_details_are_present(self):
        rows = build_ml_external_feature_readiness_plan()
        by_group = {row["source_group"]: row for row in rows}

        financial = by_group["OpenDART financial_disclosure"]
        self.assertIn("sales", financial["candidate_features"])
        self.assertIn("operating_income", financial["candidate_features"])
        self.assertIn("net_income", financial["candidate_features"])
        self.assertIn("debt_ratio", financial["candidate_features"])
        self.assertIn("roe", financial["candidate_features"])
        self.assertIn("per", financial["candidate_features"])
        self.assertIn("pbr", financial["candidate_features"])
        self.assertIn("receipt_date", financial["timestamp_fields"])
        self.assertIn("correction_filing", financial["timestamp_fields"])
        self.assertIn("report_period_end", financial["timestamp_fields"])
        self.assertEqual("high", financial["priority"])

        news = by_group["news_events"]
        self.assertIn("naver_news_search_api", news["source_name"])
        self.assertIn("gdelt", news["source_name"])
        self.assertIn("manual_news_calendar", news["source_name"])
        self.assertIn("published_at", news["timestamp_fields"])
        self.assertIn("collected_at", news["timestamp_fields"])
        self.assertIn("visible_at", news["timestamp_fields"])
        self.assertIn("usable_from", news["timestamp_fields"])
        self.assertIn("text_hash", news["candidate_features"])

        sentiment = by_group["sentiment"]
        self.assertIn("lexicon", sentiment["source_name"])
        self.assertIn("model_version", sentiment["candidate_features"])
        self.assertIn("sentiment_score", sentiment["candidate_features"])
        self.assertIn("importance_score", sentiment["candidate_features"])
        self.assertIn("FinBERT/LLM later-stage", sentiment["next_safe_action"])

        sns = by_group["sns_community"]
        self.assertIn("spam", sns["data_quality_risk"])
        self.assertIn("timestamp", sns["data_quality_risk"])

    def test_save_writes_csv_and_markdown_plan_only_notice(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_output = root / "data" / "reports" / "ml_external_feature_readiness_plan.csv"
            md_output = root / "data" / "reports" / "ml_external_feature_readiness_plan.md"

            save_ml_external_feature_readiness_plan(
                build_ml_external_feature_readiness_plan(),
                csv_output,
                md_output,
            )

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(4, len(saved))
            self.assertEqual(REQUIRED_COLUMNS, list(saved[0].keys()))
            self.assertIn("Do Not Trade / Plan Only", markdown)
            self.assertIn("PLAN_ONLY_NOT_READY_FOR_TRAINING", markdown)
            self.assertIn("fetch_allowed_now=False", markdown)
            self.assertIn("training_allowed_now=False", markdown)


if __name__ == "__main__":
    unittest.main()
