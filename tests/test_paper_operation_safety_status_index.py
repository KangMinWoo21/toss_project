import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.paper_operation_safety_status_index import (
    build_paper_operation_safety_status_index,
    save_paper_operation_safety_status_index,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class PaperOperationSafetyStatusIndexTest(unittest.TestCase):
    def _write_valid_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        production_blocks = reports / "production_block_classification.csv"
        oos_guard = reports / "protected_candidate_oos_review_eligibility_guard.csv"
        consistency = reports / "monthly_paper_operation_consistency_audit.csv"
        order_plan = reports / "monthly_order_plan_neutral_loss_guard55_min_history244.csv"
        review_packet = reports / "monthly_paper_operation_review_packet.csv"
        trial_summary = reports / "monthly_candidate_research_trial_summary.csv"
        health_warn = reports / "health_warn_classification.csv"

        _write(
            production_blocks,
            "check_scope,block_name,block_status,reason\n"
            "default,overall,BLOCK,baseline hard stop\n"
            "protected_overlay,risk_report,BLOCK,paper review hard stop\n",
        )
        _write(
            oos_guard,
            "check,status,expected,observed,reason,source,guard_status,review_eligibility,trading_allowed,production_effect\n"
            "summary,PASS,guard_status=PASS,guard_status=PASS,ok,derived,PASS,REVIEW_NOT_ALLOWED,False,none\n"
            "protected_candidate_paper_review,PASS,PAPER_REVIEW,ledger=PAPER_REVIEW,ok,ledger.csv,PASS,REVIEW_NOT_ALLOWED,False,none\n"
            "oos_review_not_allowed,PASS,review_allowed=False,review_allowed=False,ok,obs.csv,PASS,REVIEW_NOT_ALLOWED,False,none\n"
            "observed_days_below_required,PASS,observed < required,observed=0; required=15,ok,obs.csv,PASS,REVIEW_NOT_ALLOWED,False,none\n"
            "remaining_days_positive,PASS,remaining > 0,remaining=15,ok,obs.csv,PASS,REVIEW_NOT_ALLOWED,False,none\n",
        )
        _write(
            consistency,
            "check,status,expected,observed,reason,source\n"
            "monthly_consistency_pass_not_authorization,PASS,PASS not auth,rows=20; non_pass=0,review only,audit.csv\n"
            "trading_allowed_false,PASS,trading_allowed=False,rows=11; true_present=False,no trading,packet.csv\n"
            "production_effect_none,PASS,production_effect=none,production_effect=none,no effect,packet.csv\n"
            "actionable_rows_zero,PASS,actionable_rows=0,actionable_rows=0,zero,packet.csv\n"
            "all_order_rows_blocked,PASS,all blocked,rows=5; blocked=5,blocked,order.csv\n",
        )
        _write(
            order_plan,
            "symbol,execution_allowed,execution_mode,risk_status,risk_reasons\n"
            "000270,False,blocked,BLOCKED,risk_status_BLOCK\n"
            "016360,False,blocked,BLOCKED,risk_status_BLOCK\n",
        )
        _write(
            review_packet,
            "section,status,key_value,manual_action_required,trading_allowed,reason,source_report\n"
            "production_readiness,BLOCK,default_gaps=8,True,False,blocked,prod.csv\n"
            "protected_candidate,PAPER_REVIEW,candidate=guard;protected_from_tuning=True,True,False,paper review,ledger.csv\n"
            "oos_observation,OBSERVE,review_allowed=False;observed_days=0;required_days=15;remaining_days=15,True,False,observe,obs.csv\n"
            "monthly_order_plan,BLOCKED_REVIEW_ONLY,rows=2;blocked_rows=2;actionable_rows=0,True,False,blocked,order.csv\n"
            "candidate_trials,REVIEW_ONLY,promoted=0,True,False,no promotion,trials.csv\n"
            "do_not_trade,HARD_STOP,trading_allowed=False;production_effect=none,True,False,no trade,checklist.md\n",
        )
        _write(
            trial_summary,
            "row_type,candidate_id,status,promotion_allowed,promoted_count,recommendation\n"
            "candidate,guard,PAPER_REVIEW,False,,continue_observation\n"
            "trial_count_summary,ALL,,,,0\n",
        )
        _write(
            health_warn,
            "warn_name,current_status,affects_monthly_rebalance,affects_protected_candidate_oos,affects_scalper_only,criticality,reason\n"
            "scalper_data,WARN,False,False,True,non_critical_for_monthly_paper_review_but_blocks_future_scalper_work,old scalper data\n",
        )
        return {
            "production_block_csv": production_blocks,
            "oos_review_guard_csv": oos_guard,
            "monthly_consistency_audit_csv": consistency,
            "order_plan_csv": order_plan,
            "review_packet_csv": review_packet,
            "trial_summary_csv": trial_summary,
            "health_warn_csv": health_warn,
        }

    def test_valid_inputs_observe(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))

            rows = build_paper_operation_safety_status_index(**paths)

            summary = rows[0]
            self.assertEqual("summary", summary["check"])
            self.assertEqual("OBSERVE", summary["overall_status"])
            self.assertEqual("False", summary["trading_allowed"])
            self.assertEqual("False", summary["review_allowed"])
            self.assertEqual("none", summary["production_effect"])
            self.assertEqual("keep_observing_no_tuning_no_promotion", summary["recommended_action"])
            self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_missing_production_block_fails_closed(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            paths["production_block_csv"].write_text(
                "check_scope,block_name,block_status,reason\n"
                "default,overall,PASS,not blocked\n",
                encoding="utf-8",
            )

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", rows[0]["overall_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "production_block_retained")["status"])

    def test_trading_allowed_true_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["oos_review_guard_csv"].read_text(encoding="utf-8")
            paths["oos_review_guard_csv"].write_text(text.replace(",False,none", ",True,none", 1), encoding="utf-8")

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "trading_allowed_false")["status"])

    def test_review_allowed_true_blocks_even_when_production_blocked(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["review_packet_csv"].read_text(encoding="utf-8")
            paths["review_packet_csv"].write_text(text.replace("review_allowed=False", "review_allowed=True"), encoding="utf-8")

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "oos_review_allowed_false")["status"])

    def test_promoted_count_above_zero_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["review_packet_csv"].read_text(encoding="utf-8")
            paths["review_packet_csv"].write_text(text.replace("promoted=0", "promoted=1"), encoding="utf-8")

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "promoted_candidates_zero")["status"])

    def test_missing_source_or_required_field_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            paths["order_plan_csv"].unlink()

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", rows[0]["overall_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "source_files_present")["status"])

        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["oos_review_guard_csv"].read_text(encoding="utf-8")
            paths["oos_review_guard_csv"].write_text(text.replace("review_eligibility,", ""), encoding="utf-8")

            rows = build_paper_operation_safety_status_index(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "oos_guard_required_fields")["status"])

    def test_markdown_contains_do_not_trade(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            rows = build_paper_operation_safety_status_index(**paths)
            csv_output = root / "index.csv"
            markdown_output = root / "index.md"

            save_paper_operation_safety_status_index(rows, csv_output, markdown_output)

            saved = _read_rows(csv_output)
            markdown = markdown_output.read_text(encoding="utf-8")
            self.assertEqual("OBSERVE", saved[0]["overall_status"])
            self.assertIn("Do Not Trade / Status Index Only", markdown)
            self.assertIn("does not authorize trading", markdown)


if __name__ == "__main__":
    unittest.main()
