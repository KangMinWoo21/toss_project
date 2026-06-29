import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.ml_financial_feature_merge_audit import (
    FINANCIAL_FEATURE_MERGE_AUDIT_COLUMNS,
    build_ml_financial_feature_merge_audit,
    save_ml_financial_feature_merge_audit,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MlFinancialFeatureMergeAuditTest(unittest.TestCase):
    def _write_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        dataset = reports / "ml_baseline_feature_label_sample.csv"
        observations = reports / "ml_financial_observations_sample.csv"
        pit_audit = reports / "ml_financial_pit_audit.csv"

        _write(
            dataset,
            "symbol,feature_date,label_end_date,return_1m,label_return,label,train_cutoff,post_cutoff_data_used_for_train,training_ran,trading_allowed,production_effect\n"
            "005930,2026-03-31,2026-04-30,0.0100000000,0.0200000000,positive,2026-06-18,False,False,False,none\n"
            "000660,2026-03-31,2026-04-30,0.0200000000,-0.0100000000,negative,2026-06-18,False,False,False,none\n"
            "035420,2026-03-31,2026-04-30,0.0300000000,0.0000000000,flat,2026-06-18,False,False,False,none\n",
        )
        _write(
            observations,
            "symbol,corp_code,business_year,report_code,fs_div,statement_name,account_name,current_amount,previous_amount,currency,ord,receipt_no,receipt_date,receipt_time,collected_at,usable_from,report_period_end,correction_filing_flag,original_receipt_no,source_revision,quality_status,excluded_reason,training_allowed_now,trading_allowed,production_effect\n"
            "005930,00126380,2025,11011,CFS,income_statement,Revenue,1000,900,KRW,1,20260315000001,2026-03-15,00:00:00,2026-06-30T09:00:00,2026-06-30,2025-12-31,False,20260315000001,dart:005930:2025:11011,PASS,,False,False,none\n"
            "000660,00164779,2025,11011,CFS,balance_sheet,Assets,2000,1800,KRW,1,20260320000001,2026-03-20,00:00:00,2026-06-30T09:00:00,2026-06-30,2025-12-31,False,20260320000001,dart:000660:2025:11011,PASS,,False,False,none\n",
        )
        _write(
            pit_audit,
            "check_name,check_status,evidence,train_cutoff,post_cutoff_data_used_for_train,training_allowed_now,trading_allowed,production_effect,protected_candidate_unchanged\n"
            "usable_from_presence,PASS,2/2 observations include usable_from,2026-06-18,False,False,False,none,True\n"
            "post_cutoff_train_leakage,PASS,2 observations are post-cutoff and not used for train,2026-06-18,False,False,False,none,True\n"
            "readiness_status,BLOCK,limited sample only,2026-06-18,False,False,False,none,True\n",
        )
        return {
            "dataset_csv": dataset,
            "financial_observations_csv": observations,
            "financial_pit_audit_csv": pit_audit,
        }

    def test_merge_audit_records_coverage_missingness_and_safety(self):
        with TemporaryDirectory() as tmp:
            result = build_ml_financial_feature_merge_audit(**self._write_sources(Path(tmp)))
            by_metric = {row["metric"]: row for row in result.audit_rows}

            self.assertEqual(FINANCIAL_FEATURE_MERGE_AUDIT_COLUMNS, list(result.audit_rows[0]))
            self.assertEqual("financial_feature_merge_audit_complete", by_metric["summary"]["status"])
            self.assertEqual("2/3", by_metric["join_coverage"]["value"])
            self.assertEqual("0.3333", by_metric["missing_rate"]["value"])
            self.assertEqual("PASS", by_metric["leakage_check"]["status"])
            self.assertEqual("False", by_metric["post_cutoff_data_used_for_train"]["value"])
            self.assertEqual("False", by_metric["feature_added_to_training"]["value"])
            self.assertEqual("False", by_metric["training_allowed_now"]["value"])
            self.assertEqual("False", by_metric["trading_allowed"]["value"])
            self.assertEqual("none", by_metric["production_effect"]["value"])
            self.assertEqual("True", by_metric["protected_candidate_unchanged"]["value"])

    def test_save_writes_phase_7_csv_and_markdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_ml_financial_feature_merge_audit(**self._write_sources(root))
            csv_output = root / "data" / "reports" / "ml_financial_feature_merge_audit.csv"
            md_output = root / "data" / "reports" / "ml_financial_feature_merge_audit.md"

            save_ml_financial_feature_merge_audit(result, csv_output, md_output)

            rows = _read_rows(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(FINANCIAL_FEATURE_MERGE_AUDIT_COLUMNS, list(rows[0]))
            self.assertIn("Do Not Trade / Merge Audit Only", markdown)
            self.assertIn("Feature added to training: `False`", markdown)


if __name__ == "__main__":
    unittest.main()
