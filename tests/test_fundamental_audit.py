import csv
import tempfile
import unittest
from pathlib import Path

from backtester.fundamental_audit import (
    FUNDAMENTAL_AUDIT_COLUMNS,
    FUNDAMENTAL_SAMPLE_INPUT_COLUMNS,
    build_regime_sideways_fundamental_audit,
    load_csv_rows,
    load_local_fundamental_sample_rows,
    save_regime_sideways_fundamental_audit,
    save_regime_sideways_fundamental_sample_template,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
REGIME_SIDEWAYS_SAMPLE_FIXTURE = FIXTURE_DIR / "regime_sideways_fundamental_sample_rows.csv"


class FundamentalAuditTests(unittest.TestCase):
    def test_build_regime_sideways_audit_joins_fixture_fundamentals(self):
        missed = [{"symbol": "008970"}, {"symbol": "064350"}]
        min_history = [{"symbol": "007660"}, {"symbol": "008970"}]
        comparison = [
            {
                "candidate_id": "no_min_history_relaxation_neutral_loss_guard",
                "top_loss_symbols": "011790:-122843.725;064350:-87741.65",
            }
        ]
        fundamentals = [
            {
                "symbol": "008970",
                "fiscal_period": "2024Q4",
                "usable_from": "2025-01-31T09:00:00+09:00",
                "revenue_growth_yoy": "22.5",
                "operating_profit_growth_yoy": "31.0",
                "net_income_growth_yoy": "18.0",
                "operating_margin": "0.15",
                "debt_ratio": "0.40",
                "current_ratio": "1.80",
                "roe": "0.12",
                "operating_cashflow": "1200",
                "capital_impairment_flag": "False",
                "capital_increase_or_cb_flag": "False",
                "earnings_event_risk_status": "normal",
                "fundamental_quality_status": "pass",
            }
        ]

        rows = build_regime_sideways_fundamental_audit(
            missed_recovery_rows=missed,
            min_history_rows=min_history,
            candidate_comparison_rows=comparison,
            fundamental_rows=fundamentals,
        )

        row_by_key = {(row["symbol"], row["group"]): row for row in rows}
        self.assertEqual(row_by_key[("008970", "missed_252safe_recovery")]["revenue_growth_yoy"], "22.5")
        self.assertEqual(row_by_key[("008970", "min_history244_contribution")]["usable_from"], "2025-01-31T09:00:00+09:00")
        self.assertEqual(row_by_key[("011790", "selected_loser")]["fiscal_period"], "not_available")
        self.assertEqual(row_by_key[("011790", "selected_loser")]["explains_ranking_gap"], "insufficient_fundamental_data")
        self.assertEqual(len(rows), 5)

    def test_save_regime_sideways_audit_writes_schema_complete_csv(self):
        rows = build_regime_sideways_fundamental_audit(
            missed_recovery_rows=[{"symbol": "008970"}],
            min_history_rows=[],
            candidate_comparison_rows=[],
            fundamental_rows=[],
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.csv"
            saved = save_regime_sideways_fundamental_audit(rows, path)
            with path.open(newline="", encoding="utf-8") as f:
                written = list(csv.DictReader(f))

        self.assertEqual(saved, 1)
        self.assertEqual(list(written[0].keys()), FUNDAMENTAL_AUDIT_COLUMNS)
        self.assertEqual(written[0]["symbol"], "008970")
        self.assertEqual(written[0]["fundamental_quality_status"], "not_available")
        self.assertEqual(written[0]["reason"], "no_local_pit_fundamental_or_earnings_rows")

    def test_load_csv_rows_strips_utf8_bom_from_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bom.csv"
            path.write_text("\ufeffsymbol\n008970\n", encoding="utf-8")
            rows = load_csv_rows(path)

        self.assertEqual(rows, [{"symbol": "008970"}])

    def test_local_sample_valid_pit_row_populates_audit_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = Path(tmp) / "sample.csv"
            with sample_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FUNDAMENTAL_SAMPLE_INPUT_COLUMNS)
                writer.writeheader()
                writer.writerow(
                    {
                        "symbol": "008970",
                        "group": "missed_252safe_recovery",
                        "fiscal_period": "2024Q4",
                        "report_type": "quarterly",
                        "receipt_date": "2025-02-12",
                        "receipt_time": "15:35:00",
                        "available_date": "2025-02-13",
                        "usable_from": "2025-02-13",
                        "revenue_growth_yoy": "12.3",
                        "operating_profit_growth_yoy": "7.4",
                        "net_income_growth_yoy": "5.2",
                        "operating_margin": "0.11",
                        "debt_ratio": "0.42",
                        "current_ratio": "1.6",
                        "roe": "0.09",
                        "operating_cashflow": "1000",
                        "capital_impairment_flag": "False",
                        "capital_increase_or_cb_flag": "False",
                        "earnings_event_risk_status": "normal",
                        "source": "local_fixture",
                        "source_report_id": "fixture-008970-q4",
                    }
                )

            result = load_local_fundamental_sample_rows(sample_path, as_of="2025-04-30")
            rows = build_regime_sideways_fundamental_audit(
                missed_recovery_rows=[{"symbol": "008970"}],
                min_history_rows=[],
                candidate_comparison_rows=[],
                fundamental_rows=result.valid_rows,
            )

        self.assertEqual(result.issues, [])
        self.assertEqual(rows[0]["fiscal_period"], "2024Q4")
        self.assertEqual(rows[0]["revenue_growth_yoy"], "12.3")
        self.assertEqual(rows[0]["earnings_event_risk_status"], "normal")
        self.assertEqual(rows[0]["explains_ranking_gap"], "fundamental_data_available_review_only")

    def test_local_sample_future_usable_from_row_is_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = Path(tmp) / "sample.csv"
            with sample_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FUNDAMENTAL_SAMPLE_INPUT_COLUMNS)
                writer.writeheader()
                writer.writerow(
                    {
                        "symbol": "008970",
                        "group": "missed_252safe_recovery",
                        "fiscal_period": "2024Q4",
                        "receipt_date": "2025-02-12",
                        "usable_from": "2025-05-01",
                        "revenue_growth_yoy": "12.3",
                    }
                )

            result = load_local_fundamental_sample_rows(sample_path, as_of="2025-04-30")

        self.assertEqual(result.valid_rows, [])
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].field, "usable_from")
        self.assertEqual(result.issues[0].reason, "row_not_usable_as_of")

    def test_local_sample_missing_usable_from_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = Path(tmp) / "sample.csv"
            with sample_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FUNDAMENTAL_SAMPLE_INPUT_COLUMNS)
                writer.writeheader()
                writer.writerow(
                    {
                        "symbol": "008970",
                        "group": "missed_252safe_recovery",
                        "fiscal_period": "2024Q4",
                        "receipt_date": "2025-02-12",
                    }
                )

            result = load_local_fundamental_sample_rows(sample_path, as_of="2025-04-30")

        self.assertEqual(result.valid_rows, [])
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].field, "usable_from")
        self.assertEqual(result.issues[0].reason, "missing_required_field")

    def test_save_sample_template_writes_one_row_per_audit_symbol_group(self):
        audit_rows = [
            {"symbol": "008970", "group": "missed_252safe_recovery"},
            {"symbol": "008970", "group": "min_history244_contribution"},
            {"symbol": "007660", "group": "min_history244_contribution"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "template.csv"
            saved = save_regime_sideways_fundamental_sample_template(audit_rows, path)
            with path.open(newline="", encoding="utf-8") as f:
                written = list(csv.DictReader(f))

        self.assertEqual(saved, 3)
        self.assertEqual(list(written[0].keys()), FUNDAMENTAL_SAMPLE_INPUT_COLUMNS)
        self.assertEqual(written[0]["symbol"], "008970")
        self.assertEqual(written[0]["group"], "missed_252safe_recovery")
        self.assertEqual(written[0]["usable_from"], "not_available")

    def test_fixture_sample_filters_by_pit_usable_from_and_reports_invalid_rows(self):
        result = load_local_fundamental_sample_rows(REGIME_SIDEWAYS_SAMPLE_FIXTURE, as_of="2025-04-30")

        symbols = {row["symbol"] for row in result.valid_rows}
        issue_keys = {(issue.symbol, issue.field, issue.reason) for issue in result.issues}

        self.assertIn("008970", symbols)
        self.assertIn("006260", symbols)
        self.assertIn("047810", symbols)
        self.assertNotIn("064350", symbols)
        self.assertNotIn("003230", symbols)
        self.assertNotIn("079550", symbols)
        self.assertIn(("064350", "usable_from", "row_not_usable_as_of"), issue_keys)
        self.assertIn(("003230", "usable_from", "missing_required_field"), issue_keys)
        self.assertIn(("079550", "usable_from", "row_not_usable_as_of"), issue_keys)

    def test_fixture_sample_does_not_treat_fiscal_period_as_availability_date(self):
        result = load_local_fundamental_sample_rows(REGIME_SIDEWAYS_SAMPLE_FIXTURE, as_of="2025-04-30")

        self.assertFalse(any(row["symbol"] == "079550" for row in result.valid_rows))
        self.assertTrue(
            any(
                issue.symbol == "079550" and issue.reason == "row_not_usable_as_of"
                for issue in result.issues
            )
        )

    def test_fixture_sample_accepts_available_date_when_receipt_date_is_missing(self):
        result = load_local_fundamental_sample_rows(REGIME_SIDEWAYS_SAMPLE_FIXTURE, as_of="2025-04-30")
        rows_by_symbol = {row["symbol"]: row for row in result.valid_rows}

        self.assertIn("047810", rows_by_symbol)
        self.assertEqual(rows_by_symbol["047810"]["receipt_date"], "")
        self.assertEqual(rows_by_symbol["047810"]["available_date"], "2025-02-17")

    def test_fixture_sample_uses_append_only_corrected_latest_usable_row(self):
        result = load_local_fundamental_sample_rows(REGIME_SIDEWAYS_SAMPLE_FIXTURE, as_of="2025-04-30")
        rows = build_regime_sideways_fundamental_audit(
            missed_recovery_rows=[{"symbol": "008970"}],
            min_history_rows=[],
            candidate_comparison_rows=[],
            fundamental_rows=result.valid_rows,
        )

        self.assertEqual(rows[0]["fiscal_period"], "2024Q4")
        self.assertEqual(rows[0]["usable_from"], "2025-02-13")
        self.assertEqual(rows[0]["revenue_growth_yoy"], "14.0")

    def test_fixture_sample_not_available_values_are_not_treated_as_zero(self):
        result = load_local_fundamental_sample_rows(REGIME_SIDEWAYS_SAMPLE_FIXTURE, as_of="2025-04-30")
        rows = build_regime_sideways_fundamental_audit(
            missed_recovery_rows=[{"symbol": "006260"}],
            min_history_rows=[],
            candidate_comparison_rows=[],
            fundamental_rows=result.valid_rows,
        )

        self.assertEqual(rows[0]["revenue_growth_yoy"], "not_available")
        self.assertEqual(rows[0]["operating_profit_growth_yoy"], "not_available")
        self.assertNotEqual(rows[0]["revenue_growth_yoy"], "0")

    def test_fixture_sample_audit_remains_schema_complete_when_data_is_missing_or_future(self):
        rows = build_regime_sideways_fundamental_audit(
            missed_recovery_rows=[{"symbol": "064350"}, {"symbol": "003230"}, {"symbol": "999999"}],
            min_history_rows=[],
            candidate_comparison_rows=[],
            local_sample_path=REGIME_SIDEWAYS_SAMPLE_FIXTURE,
            as_of="2025-04-30",
        )

        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(list(row.keys()), FUNDAMENTAL_AUDIT_COLUMNS)
            self.assertEqual(row["fundamental_quality_status"], "not_available")
            self.assertEqual(row["explains_ranking_gap"], "insufficient_fundamental_data")


if __name__ == "__main__":
    unittest.main()
