import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_sentiment_scoring_plan import (
    SENTIMENT_PLAN_COLUMNS,
    build_ml_sentiment_scoring_plan,
    save_ml_sentiment_scoring_plan,
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlSentimentScoringPlanTest(unittest.TestCase):
    def test_sentiment_plan_is_rule_lexicon_first_and_paper_only(self):
        first = build_ml_sentiment_scoring_plan()
        second = build_ml_sentiment_scoring_plan()

        self.assertEqual(first, second)
        self.assertEqual(4, len(first))
        self.assertEqual(SENTIMENT_PLAN_COLUMNS, list(first[0]))

        by_component = {row["component"]: row for row in first}
        self.assertEqual("rule_lexicon_v1", by_component["lexicon_scoring"]["model_version"])
        self.assertEqual("-1.0_to_1.0", by_component["lexicon_scoring"]["sentiment_score_range"])
        self.assertIn("positive_terms", by_component["lexicon_scoring"]["schema_fields"])
        self.assertIn("negative_terms", by_component["lexicon_scoring"]["schema_fields"])
        self.assertIn("published_at", by_component["pit_controls"]["timestamp_fields"])
        self.assertIn("scored_at", by_component["pit_controls"]["timestamp_fields"])
        self.assertIn("usable_from", by_component["pit_controls"]["timestamp_fields"])
        self.assertIn("FinBERT", by_component["later_stage_models"]["llm_risk_note"])
        self.assertIn("LLM", by_component["later_stage_models"]["llm_risk_note"])

        for row in first:
            self.assertEqual("False", row["fetch_allowed_now"])
            self.assertEqual("False", row["training_allowed_now"])
            self.assertEqual("False", row["feature_added_to_training"])
            self.assertEqual("False", row["trading_allowed"])
            self.assertEqual("none", row["production_effect"])
            self.assertEqual("True", row["pit_required"])
            self.assertEqual("True", row["usable_from_required"])
            self.assertEqual("schema_plan_only", row["current_status"])

    def test_plan_defines_scoring_contract_without_llm_or_training_use(self):
        rows = build_ml_sentiment_scoring_plan()
        by_component = {row["component"]: row for row in rows}

        scoring = by_component["lexicon_scoring"]
        self.assertIn("sentiment_score", scoring["candidate_features"])
        self.assertIn("sentiment_label", scoring["candidate_features"])
        self.assertIn("model_version", scoring["schema_fields"])
        self.assertIn("scored_at", scoring["timestamp_fields"])

        aggregation = by_component["monthly_aggregation"]
        self.assertIn("sentiment_count_1m", aggregation["candidate_features"])
        self.assertIn("negative_sentiment_share_1m", aggregation["candidate_features"])
        self.assertIn("usable_from <= feature_date", aggregation["lineage_rule"])

        controls = by_component["pit_controls"]
        self.assertIn("text_hash", controls["schema_fields"])
        self.assertIn("block_if_scored_at_or_usable_from_after_feature_date", controls["leakage_risk"])

        later = by_component["later_stage_models"]
        self.assertEqual("False", later["model_training_allowed"])
        self.assertIn("later-stage", later["next_safe_action"])

    def test_save_writes_phase_9_reports(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_output = root / "data" / "reports" / "ml_sentiment_scoring_plan.csv"
            md_output = root / "data" / "reports" / "ml_sentiment_scoring_plan.md"

            save_ml_sentiment_scoring_plan(
                build_ml_sentiment_scoring_plan(),
                csv_output,
                md_output,
            )

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(4, len(saved))
            self.assertEqual(SENTIMENT_PLAN_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / Sentiment Plan Only", markdown)
            self.assertIn("rule_lexicon_v1", markdown)
            self.assertIn("sentiment_score", markdown)
            self.assertIn("training_allowed_now=False", markdown)


if __name__ == "__main__":
    unittest.main()
