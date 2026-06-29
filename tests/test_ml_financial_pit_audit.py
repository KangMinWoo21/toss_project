import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.dart import DartDisclosureRow
from backtester.ml_financial_pit_audit import (
    FINANCIAL_OBSERVATION_COLUMNS,
    FINANCIAL_PIT_AUDIT_COLUMNS,
    build_ml_financial_pit_audit_reports,
    save_ml_financial_pit_audit_reports,
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlFinancialPitAuditTest(unittest.TestCase):
    def test_build_reports_are_deterministic_pit_safe_and_paper_only(self):
        financial_rows = [
            {
                "symbol": "005930",
                "corp_code": "00126380",
                "business_year": "2025",
                "report_code": "11011",
                "fs_div": "CFS",
                "statement_name": "income_statement",
                "account_name": "Revenue",
                "current_amount": 1000.0,
                "previous_amount": 900.0,
                "currency": "KRW",
                "ord": "1",
            }
        ]
        disclosures = [
            DartDisclosureRow(
                date="2026-03-15",
                symbol="005930",
                corp_name="Samsung Electronics",
                report_name="Annual Report",
                receipt_no="20260315000001",
            ),
            DartDisclosureRow(
                date="2026-04-01",
                symbol="005930",
                corp_name="Samsung Electronics",
                report_name="Correction Annual Report",
                receipt_no="20260401000001",
            ),
        ]

        observations, audit_rows, readiness_markdown = build_ml_financial_pit_audit_reports(
            financial_rows,
            disclosures,
            collected_at="2026-06-30T09:00:00",
            train_cutoff="2026-06-18",
        )

        observations_again, audit_rows_again, readiness_markdown_again = build_ml_financial_pit_audit_reports(
            financial_rows,
            disclosures,
            collected_at="2026-06-30T09:00:00",
            train_cutoff="2026-06-18",
        )
        self.assertEqual(observations, observations_again)
        self.assertEqual(audit_rows, audit_rows_again)
        self.assertEqual(readiness_markdown, readiness_markdown_again)

        self.assertEqual(FINANCIAL_OBSERVATION_COLUMNS, list(observations[0]))
        self.assertEqual(FINANCIAL_PIT_AUDIT_COLUMNS, list(audit_rows[0]))
        self.assertTrue(all(row["usable_from"] for row in observations))
        self.assertTrue(any(row["correction_filing_flag"] == "True" for row in observations))
        self.assertTrue(any(row["check_name"] == "correction_lineage" for row in audit_rows))

        for row in audit_rows:
            self.assertEqual("False", row["training_allowed_now"])
            self.assertEqual("False", row["trading_allowed"])
            self.assertEqual("none", row["production_effect"])
            self.assertIn(row["check_status"], {"PASS", "WARN", "BLOCK"})

        self.assertIn("Do Not Trade / PIT Audit Only", readiness_markdown)
        self.assertIn("training_allowed_now=False", readiness_markdown)
        self.assertIn("trading_allowed=False", readiness_markdown)
        self.assertIn("production_effect=none", readiness_markdown)

    def test_save_writes_all_phase_6_reports(self):
        observations, audit_rows, readiness_markdown = build_ml_financial_pit_audit_reports(
            [
                {
                    "symbol": "000660",
                    "corp_code": "00164779",
                    "business_year": "2025",
                    "report_code": "11011",
                    "fs_div": "CFS",
                    "statement_name": "balance_sheet",
                    "account_name": "Assets",
                    "current_amount": 2000.0,
                    "previous_amount": 1800.0,
                    "currency": "KRW",
                    "ord": "1",
                }
            ],
            [
                DartDisclosureRow(
                    date="2026-03-20",
                    symbol="000660",
                    corp_name="SK hynix",
                    report_name="Annual Report",
                    receipt_no="20260320000001",
                )
            ],
            collected_at="2026-06-30T09:00:00",
            train_cutoff="2026-06-18",
        )

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample_output = root / "data" / "reports" / "ml_financial_observations_sample.csv"
            audit_output = root / "data" / "reports" / "ml_financial_pit_audit.csv"
            md_output = root / "data" / "reports" / "ml_financial_feature_readiness_report.md"

            save_ml_financial_pit_audit_reports(
                observations,
                audit_rows,
                readiness_markdown,
                sample_output,
                audit_output,
                md_output,
            )

            self.assertEqual(FINANCIAL_OBSERVATION_COLUMNS, list(_read_rows(sample_output)[0]))
            self.assertEqual(FINANCIAL_PIT_AUDIT_COLUMNS, list(_read_rows(audit_output)[0]))
            markdown = md_output.read_text(encoding="utf-8")
            self.assertIn("Do Not Trade / PIT Audit Only", markdown)
            self.assertIn("limited OpenDART sample", markdown)


if __name__ == "__main__":
    unittest.main()
