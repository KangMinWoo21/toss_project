import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_financial_feature_schema_plan import (
    FINANCIAL_SCHEMA_COLUMNS,
    build_ml_financial_feature_schema_plan,
    save_ml_financial_feature_schema_plan,
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlFinancialFeatureSchemaPlanTest(unittest.TestCase):
    def test_schema_rows_are_fetch_free_and_pit_safe(self):
        rows = build_ml_financial_feature_schema_plan()

        self.assertEqual(rows, build_ml_financial_feature_schema_plan())
        self.assertEqual(FINANCIAL_SCHEMA_COLUMNS, list(rows[0]))
        self.assertGreaterEqual(len(rows), 4)
        by_name = {row["feature_group"]: row for row in rows}
        self.assertIn("financial_statement_metrics", by_name)
        self.assertIn("market_valuation_metrics", by_name)
        self.assertIn("disclosure_lineage", by_name)
        self.assertIn("pit_controls", by_name)

        for row in rows:
            self.assertEqual("False", row["fetch_allowed_now"])
            self.assertEqual("False", row["training_allowed_now"])
            self.assertEqual("False", row["trading_allowed"])
            self.assertEqual("none", row["production_effect"])
            self.assertEqual("True", row["pit_required"])
            self.assertEqual("True", row["usable_from_required"])
            self.assertEqual("True", row["api_key_required"])
            self.assertIn("usable_from", row["timestamp_fields"])

        combined_features = ";".join(row["candidate_features"] for row in rows)
        for feature in ("sales", "operating_income", "net_income", "debt_ratio", "roe", "per", "pbr"):
            self.assertIn(feature, combined_features)

        lineage = by_name["disclosure_lineage"]
        self.assertIn("receipt_date", lineage["timestamp_fields"])
        self.assertIn("receipt_time", lineage["timestamp_fields"])
        self.assertIn("report_period_end", lineage["timestamp_fields"])
        self.assertIn("correction", lineage["lineage_rule"])

    def test_save_writes_csv_and_markdown_with_plan_only_notice(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_output = root / "data" / "reports" / "ml_financial_feature_schema_plan.csv"
            md_output = root / "data" / "reports" / "ml_financial_feature_schema_plan.md"

            save_ml_financial_feature_schema_plan(
                build_ml_financial_feature_schema_plan(),
                csv_output,
                md_output,
            )

            saved = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(FINANCIAL_SCHEMA_COLUMNS, list(saved[0]))
            self.assertIn("Do Not Trade / Schema Plan Only", markdown)
            self.assertIn("fetch_allowed_now=False", markdown)
            self.assertIn("training_allowed_now=False", markdown)
            self.assertIn("receipt_date", markdown)
            self.assertIn("usable_from", markdown)


if __name__ == "__main__":
    unittest.main()
