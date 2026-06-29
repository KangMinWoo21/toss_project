import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_news_event_schema_plan import (
    NEWS_SCHEMA_COLUMNS,
    build_ml_news_event_schema_plan,
    save_ml_news_event_schema_plan,
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlNewsEventSchemaPlanTest(unittest.TestCase):
    def test_news_schema_rows_are_deterministic_fetch_free_and_pit_safe(self):
        first = build_ml_news_event_schema_plan()
        second = build_ml_news_event_schema_plan()

        self.assertEqual(first, second)
        self.assertEqual(4, len(first))
        self.assertEqual(NEWS_SCHEMA_COLUMNS, list(first[0]))

        by_group = {row["event_group"]: row for row in first}
        self.assertIn("naver_news_search_api", by_group["naver_news_events"]["source_name"])
        self.assertIn("gdelt", by_group["gdelt_news_events"]["source_name"])
        self.assertIn("manual_news_calendar", by_group["manual_calendar_events"]["source_name"])
        self.assertEqual("schema_plan_only", by_group["pit_controls"]["current_status"])

        for row in first:
            self.assertEqual("False", row["fetch_allowed_now"])
            self.assertEqual("False", row["training_allowed_now"])
            self.assertEqual("False", row["trading_allowed"])
            self.assertEqual("none", row["production_effect"])
            self.assertEqual("True", row["pit_required"])
            self.assertEqual("True", row["usable_from_required"])
            self.assertIn("published_at", row["timestamp_fields"])
            self.assertIn("collected_at", row["timestamp_fields"])
            self.assertIn("visible_at", row["timestamp_fields"])
            self.assertIn("usable_from", row["timestamp_fields"])
            self.assertIn("text_hash", row["dedupe_rule"])
            self.assertTrue(row["source_coverage_risk"])

    def test_schema_defines_required_news_fields_and_no_training_merge(self):
        rows = build_ml_news_event_schema_plan()
        by_group = {row["event_group"]: row for row in rows}

        naver = by_group["naver_news_events"]
        self.assertIn("headline", naver["schema_fields"])
        self.assertIn("url", naver["schema_fields"])
        self.assertIn("text_hash", naver["schema_fields"])
        self.assertEqual("mixed", naver["api_key_required"])

        gdelt = by_group["gdelt_news_events"]
        self.assertIn("source_id", gdelt["schema_fields"])
        self.assertIn("language", gdelt["schema_fields"])
        self.assertIn("source_coverage_bias", gdelt["source_coverage_risk"])

        manual = by_group["manual_calendar_events"]
        self.assertIn("event_type", manual["candidate_features"])
        self.assertIn("manual_review_required", manual["schema_fields"])

        controls = by_group["pit_controls"]
        self.assertIn("feature_date", controls["schema_fields"])
        self.assertIn("usable_from <= feature_date", controls["lineage_rule"])
        self.assertEqual("False", controls["feature_added_to_training"])

    def test_save_writes_phase_8_reports(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_output = root / "data" / "reports" / "ml_news_event_schema_plan.csv"
            md_output = root / "data" / "reports" / "ml_news_event_schema_plan.md"

            save_ml_news_event_schema_plan(
                build_ml_news_event_schema_plan(),
                csv_output,
                md_output,
            )

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(4, len(saved))
            self.assertEqual(NEWS_SCHEMA_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / News Schema Plan Only", markdown)
            self.assertIn("fetch_allowed_now=False", markdown)
            self.assertIn("published_at", markdown)
            self.assertIn("text_hash", markdown)


if __name__ == "__main__":
    unittest.main()
