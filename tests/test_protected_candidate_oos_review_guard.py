import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.protected_candidate_oos_review_guard import (
    build_protected_candidate_oos_review_eligibility_guard,
    save_protected_candidate_oos_review_eligibility_guard,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class ProtectedCandidateOosReviewEligibilityGuardTest(unittest.TestCase):
    def _write_valid_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        observation = reports / "post_cutoff_oos_observation_status_neutral_loss_guard55_min_history244.csv"
        ledger = reports / "monthly_candidate_research_ledger.csv"
        trials = reports / "monthly_candidate_research_trial_summary.csv"
        production_blocks = reports / "production_block_classification.csv"
        consistency = reports / "monthly_paper_operation_consistency_audit.csv"

        _write(
            observation,
            "candidate_id,observed_trading_days_after_plan,required_additional_trading_days,remaining_trading_days,review_allowed,status,reason\n"
            "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244,0,15,15,False,OBSERVE,candidate_remains_PAPER_REVIEW\n",
        )
        _write(
            ledger,
            "candidate_id,status,protected_from_tuning,oos_observation_active,post_cutoff_oos_used,auto_promote,review_assessment\n"
            "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244,PAPER_REVIEW,True,True,existing_observation_only,False,remains PAPER_REVIEW unchanged and not promoted\n"
            "paper_diag,PAPER_DIAGNOSTIC,False,False,False,False,diagnostic only\n",
        )
        _write(
            trials,
            "row_type,candidate_id,status,protected_from_tuning,promotion_allowed,recommendation,promoted_count\n"
            "candidate,proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244,PAPER_REVIEW,True,False,continue_observation,\n"
            "candidate,paper_diag,PAPER_DIAGNOSTIC,False,False,keep_diagnostic,\n"
            "trial_count_summary,ALL,,,,,0\n",
        )
        _write(
            production_blocks,
            "check_scope,block_name,block_status,expected_block,safety_block,can_be_safely_reduced_now,block_classification,reason\n"
            "default,overall,BLOCK,True,True,False,keep_hard_stop,Overall readiness summarizes active BLOCK checks.\n"
            "protected_overlay,validation_candidate_decision,BLOCK,True,True,False,candidate_oos_pending,Wait for required paper OOS observation days.\n",
        )
        _write(
            consistency,
            "check,status,expected,observed,reason,source\n"
            "trading_allowed_false,PASS,trading_allowed=False for every packet row,rows=11; true_present=False,Any trading_allowed=True signal is a hard stop.,packet.csv\n"
            "production_effect_none,PASS,production_effect=none,production_effect=none,Report-only audit must have no production effect.,packet.csv\n"
            "protected_candidate_paper_review,PASS,protected candidate status PAPER_REVIEW,status=PAPER_REVIEW,Protected candidate must remain paper review only.,packet.csv\n",
        )
        return {
            "observation_status_csv": observation,
            "candidate_ledger_csv": ledger,
            "trial_summary_csv": trials,
            "production_block_csv": production_blocks,
            "monthly_consistency_audit_csv": consistency,
        }

    def test_valid_inputs_pass_and_review_not_allowed(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            summary = rows[0]
            self.assertEqual("summary", summary["check"])
            self.assertEqual("PASS", summary["guard_status"])
            self.assertEqual("REVIEW_NOT_ALLOWED", summary["review_eligibility"])
            self.assertEqual("False", summary["trading_allowed"])
            self.assertEqual("none", summary["production_effect"])
            self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_review_allowed_true_blocks_even_when_production_blocked(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["observation_status_csv"].read_text(encoding="utf-8")
            paths["observation_status_csv"].write_text(text.replace(",False,OBSERVE,", ",True,OBSERVE,"), encoding="utf-8")

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            self.assertEqual("BLOCK", rows[0]["guard_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "oos_review_not_allowed")["status"])

    def test_non_paper_review_candidate_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["candidate_ledger_csv"].read_text(encoding="utf-8")
            paths["candidate_ledger_csv"].write_text(text.replace(",PAPER_REVIEW,True", ",ACCEPT,True"), encoding="utf-8")

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "protected_candidate_paper_review")["status"])

    def test_promoted_adopted_or_approved_marker_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["trial_summary_csv"].read_text(encoding="utf-8")
            paths["trial_summary_csv"].write_text(text.replace("continue_observation,", "approved_for_adoption,"), encoding="utf-8")

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "no_promotion_markers")["status"])

    def test_missing_source_or_required_field_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            paths["observation_status_csv"].unlink()

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            self.assertEqual("BLOCK", rows[0]["guard_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "source_files_present")["status"])

        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["candidate_ledger_csv"].read_text(encoding="utf-8")
            paths["candidate_ledger_csv"].write_text(text.replace("protected_from_tuning,", ""), encoding="utf-8")

            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "ledger_required_fields")["status"])

    def test_markdown_contains_do_not_trade_and_outputs_remain_non_production(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            rows = build_protected_candidate_oos_review_eligibility_guard(**paths)
            csv_output = root / "guard.csv"
            markdown_output = root / "guard.md"

            save_protected_candidate_oos_review_eligibility_guard(rows, csv_output, markdown_output)

            saved = _read_rows(csv_output)
            markdown = markdown_output.read_text(encoding="utf-8")
            self.assertEqual("PASS", saved[0]["guard_status"])
            self.assertIn("Do Not Trade / Review Not Allowed", markdown)
            self.assertIn("does not authorize trading", markdown)
            self.assertEqual("False", saved[0]["trading_allowed"])
            self.assertEqual("none", saved[0]["production_effect"])


if __name__ == "__main__":
    unittest.main()
