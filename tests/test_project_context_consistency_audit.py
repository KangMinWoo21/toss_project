import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.project_context_consistency_audit import (
    build_project_context_consistency_audit,
    save_project_context_consistency_audit,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class ProjectContextConsistencyAuditTest(unittest.TestCase):
    def _write_valid_sources(self, root: Path) -> dict[str, Path]:
        docs = root / "docs"
        reports = root / "data" / "reports"
        minimal = docs / "goal-mode-minimal-prompt.md"
        checkpoint = docs / "GOAL_MODE_CHECKPOINT.md"
        gpt_context = docs / "GPT_PROJECT_CONTEXT.md"
        safety_index = reports / "paper_operation_safety_status_index.md"

        shared_status = (
            "production is not live-ready: BLOCK\n"
            "protected candidate remains PAPER_REVIEW\n"
            "OOS review eligibility is REVIEW_NOT_ALLOWED\n"
            "trading_allowed=False\n"
            "review_allowed=False\n"
            "production_effect=none\n"
            "actionable rows=0\n"
            "promoted candidates=0\n"
            "recommended_action=keep_observing_no_tuning_no_promotion\n"
            "scalper stale WARN is separate from monthly paper review/OOS\n"
        )
        _write(minimal, "# Goal Mode Minimal Prompt\n\n" + shared_status)
        _write(
            checkpoint,
            "# Goal Mode Checkpoint\n\n"
            "Production is not live-ready: `BLOCK`.\n"
            "Protected candidate remains `PAPER_REVIEW`.\n"
            "OOS review eligibility is `REVIEW_NOT_ALLOWED`.\n"
            "`trading_allowed=False`.\n"
            "`review_allowed=False`.\n"
            "`production_effect=none`.\n"
            "Monthly order-plan actionable rows remain `0`.\n"
            "Promoted candidates count remains `0`.\n"
            "Current recommended action: `keep_observing_no_tuning_no_promotion`.\n"
            "Scalper stale `WARN` is separated from monthly paper review/OOS.\n",
        )
        _write(
            gpt_context,
            "# GPT Project Context\n\n"
            "Production is not live-ready: `BLOCK`.\n"
            "Safety index: `overall_status=OBSERVE`.\n"
            "Protected candidate remains `PAPER_REVIEW`.\n"
            "OOS review eligibility is `REVIEW_NOT_ALLOWED`.\n"
            "`trading_allowed=False`.\n"
            "`review_allowed=False`.\n"
            "`production_effect=none`.\n"
            "Actionable rows: `0`.\n"
            "Promoted candidates: `0`.\n"
            "Recommended action: `keep_observing_no_tuning_no_promotion`.\n"
            "Scalper stale `WARN` is separate from monthly paper review/OOS.\n",
        )
        _write(
            safety_index,
            "# Paper Operation Safety Status Index\n\n"
            "## Do Not Trade / Status Index Only\n\n"
            "- Overall status: `OBSERVE`.\n"
            "- Trading allowed: `False`.\n"
            "- Review allowed: `False`.\n"
            "- Production effect: `none`.\n"
            "- Recommended action: `keep_observing_no_tuning_no_promotion`.\n"
            "| production_block_retained | PASS | production remains BLOCK |\n"
            "| protected_candidate_paper_review | PASS | protected candidate PAPER_REVIEW |\n"
            "| oos_review_eligibility_not_allowed | PASS | review_eligibility=REVIEW_NOT_ALLOWED |\n"
            "| actionable_rows_zero | PASS | actionable_rows=0 |\n"
            "| promoted_candidates_zero | PASS | promoted candidates count=0 |\n"
            "| scalper_warn_separated | PASS | scalper stale WARN separated from monthly paper review/OOS |\n",
        )
        return {
            "minimal_prompt_md": minimal,
            "checkpoint_md": checkpoint,
            "gpt_project_context_md": gpt_context,
            "safety_status_index_md": safety_index,
        }

    def test_valid_context_documents_pass(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))

            rows = build_project_context_consistency_audit(**paths)

            self.assertEqual("summary", rows[0]["check"])
            self.assertEqual("PASS", rows[0]["audit_status"])
            self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_outdated_status_text_warns(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            with paths["gpt_project_context_md"].open("a", encoding="utf-8") as f:
                f.write(
                    "\nLatest pushed commit: `0acf392 Block empty followup stress review output`.\n"
                    "Production readiness: `BLOCK=8`, `PASS=33`, `WARN=8`.\n"
                    "Tests: `613 PASS`.\n"
                )

            rows = build_project_context_consistency_audit(**paths)

            self.assertEqual("WARN", rows[0]["audit_status"])
            self.assertEqual("WARN", next(row for row in rows if row["check"] == "outdated_text_absent")["status"])

    def test_dangerous_trading_allowed_true_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["minimal_prompt_md"].read_text(encoding="utf-8")
            paths["minimal_prompt_md"].write_text(text.replace("trading_allowed=False", "trading_allowed=True"), encoding="utf-8")

            rows = build_project_context_consistency_audit(**paths)

            self.assertEqual("BLOCK", rows[0]["audit_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "dangerous_authorization_text_absent")["status"])

    def test_missing_required_status_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            text = paths["checkpoint_md"].read_text(encoding="utf-8")
            paths["checkpoint_md"].write_text(text.replace("PAPER_REVIEW", "PAPER_PROMOTED"), encoding="utf-8")

            rows = build_project_context_consistency_audit(**paths)

            self.assertEqual("BLOCK", rows[0]["audit_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "required_safety_status_present")["status"])

    def test_missing_source_blocks(self):
        with TemporaryDirectory() as tmp:
            paths = self._write_valid_sources(Path(tmp))
            paths["safety_status_index_md"].unlink()

            rows = build_project_context_consistency_audit(**paths)

            self.assertEqual("BLOCK", rows[0]["audit_status"])
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "source_files_present")["status"])

    def test_markdown_contains_do_not_trade_context_audit_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            rows = build_project_context_consistency_audit(**paths)
            csv_output = root / "audit.csv"
            markdown_output = root / "audit.md"

            save_project_context_consistency_audit(rows, csv_output, markdown_output)

            saved = _read_rows(csv_output)
            markdown = markdown_output.read_text(encoding="utf-8")
            self.assertEqual("PASS", saved[0]["audit_status"])
            self.assertIn("Do Not Trade / Context Audit Only", markdown)
            self.assertIn("does not authorize trading", markdown)


if __name__ == "__main__":
    unittest.main()
