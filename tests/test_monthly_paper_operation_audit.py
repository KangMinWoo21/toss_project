import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.monthly_paper_operation_audit import (
    REQUIRED_BLOCKED_SYMBOLS,
    build_monthly_paper_operation_consistency_audit,
    save_monthly_paper_operation_consistency_audit,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MonthlyPaperOperationConsistencyAuditTest(unittest.TestCase):
    def _write_valid_sources(self, root: Path) -> dict[str, Path]:
        reports = root / "data" / "reports"
        review_packet_csv = reports / "monthly_paper_operation_review_packet.csv"
        markdown_blocked_audit_csv = reports / "monthly_order_plan_markdown_blocked_row_audit.csv"
        order_plan_csv = reports / "monthly_order_plan_neutral_loss_guard55_min_history244.csv"
        review_packet_md = reports / "monthly_paper_operation_review_packet.md"
        markdown_blocked_audit_md = reports / "monthly_order_plan_markdown_blocked_row_audit.md"
        blocked_summary_md = reports / "monthly_order_plan_blocked_rows_review_summary.md"
        order_plan_md = reports / "monthly_order_plan_neutral_loss_guard55_min_history244.md"

        _write_csv(
            review_packet_csv,
            [
                "section",
                "status",
                "key_value",
                "manual_action_required",
                "trading_allowed",
                "reason",
                "source_report",
            ],
            [
                {
                    "section": "production_readiness",
                    "status": "BLOCK",
                    "key_value": "production_status=BLOCK;production_effect=none",
                    "manual_action_required": "True",
                    "trading_allowed": "False",
                    "reason": "Production BLOCK is retained.",
                    "source_report": "production_readiness_evidence_gap_plan.csv",
                },
                {
                    "section": "protected_candidate",
                    "status": "PAPER_REVIEW",
                    "key_value": "candidate=example;promotion_allowed=False",
                    "manual_action_required": "True",
                    "trading_allowed": "False",
                    "reason": "Protected candidate remains PAPER_REVIEW.",
                    "source_report": "monthly_candidate_research_trial_summary.csv",
                },
                {
                    "section": "oos_observation",
                    "status": "OBSERVE",
                    "key_value": "review_allowed=False;observed_days=0",
                    "manual_action_required": "True",
                    "trading_allowed": "False",
                    "reason": "Review is not allowed.",
                    "source_report": "post_cutoff_oos_observation_status.csv",
                },
                {
                    "section": "monthly_order_plan",
                    "status": "BLOCKED_REVIEW_ONLY",
                    "key_value": "rows=5;blocked_rows=5;actionable_rows=0",
                    "manual_action_required": "True",
                    "trading_allowed": "False",
                    "reason": "Zero actionable rows.",
                    "source_report": "monthly_paper_order_plan_review_audit.csv",
                },
                {
                    "section": "do_not_trade",
                    "status": "HARD_STOP",
                    "key_value": "trading_allowed=False;broker_submission=forbidden;production_effect=none",
                    "manual_action_required": "True",
                    "trading_allowed": "False",
                    "reason": "Do not trade.",
                    "source_report": "monthly_paper_order_plan_review_checklist.md",
                },
            ],
        )
        _write_csv(
            markdown_blocked_audit_csv,
            [
                "as_of_date",
                "csv_order_rows",
                "markdown_order_rows_visible",
                "csv_blocked_rows",
                "markdown_blocked_rows_visible",
                "all_blocked_rows_explained",
                "missing_blocked_row_count",
                "risk_status_visible",
                "risk_reasons_visible",
                "production_block_visible",
                "recommendation",
                "reason",
            ],
            [
                {
                    "as_of_date": "2026-06-18",
                    "csv_order_rows": "5",
                    "markdown_order_rows_visible": "5",
                    "csv_blocked_rows": "5",
                    "markdown_blocked_rows_visible": "5",
                    "all_blocked_rows_explained": "True",
                    "missing_blocked_row_count": "0",
                    "risk_status_visible": "True",
                    "risk_reasons_visible": "True",
                    "production_block_visible": "True",
                    "recommendation": "create_review_only_blocked_rows_summary",
                    "reason": "risk_status_BLOCK visible for all blocked rows.",
                }
            ],
        )
        order_rows = [
            {
                "as_of_date": "2026-06-18",
                "symbol": symbol,
                "action": "BUY",
                "quantity": index + 1,
                "execution_allowed": "False",
                "execution_mode": "blocked",
                "execution_block_reason": "risk_status_BLOCK",
                "risk_status": "BLOCKED",
                "risk_reasons": "risk_status_BLOCK",
            }
            for index, symbol in enumerate(REQUIRED_BLOCKED_SYMBOLS)
        ]
        _write_csv(
            order_plan_csv,
            [
                "as_of_date",
                "symbol",
                "action",
                "quantity",
                "execution_allowed",
                "execution_mode",
                "execution_block_reason",
                "risk_status",
                "risk_reasons",
            ],
            order_rows,
        )
        review_packet_md.write_text(
            "# Monthly Paper Operation Review Packet\n\n"
            "- Production readiness remains `BLOCK`.\n"
            "- Production effect: `none`.\n"
            "- Status: `PAPER_REVIEW`.\n"
            "- OOS `review_allowed=False`.\n"
            "- Actionable rows: `0`.\n"
            "Do not submit broker orders.\n",
            encoding="utf-8",
        )
        markdown_blocked_audit_md.write_text(
            "# Monthly Order Plan Markdown Blocked-Row Audit\n\n"
            "All five symbols from the CSV are visible: "
            + ", ".join(f"`{symbol}`" for symbol in REQUIRED_BLOCKED_SYMBOLS)
            + ".\nThe hard-stop reason is `risk_status_BLOCK`.\n",
            encoding="utf-8",
        )
        blocked_summary_md.write_text(
            "# Monthly Order Plan Blocked Rows Review Summary\n\n"
            "## Do Not Trade\n\n"
            "Broker submission: forbidden\n\n"
            "All order-plan rows are `BLOCKED`. Each row has "
            "`execution_allowed=False`, `execution_mode=blocked`, "
            "`execution_block_reason=risk_status_BLOCK`, and "
            "`risk_reasons=risk_status_BLOCK`.\n\n"
            "| Symbol | Action | Quantity | Execution allowed | Execution mode | Risk status | Hard-stop reason |\n"
            "| --- | --- | ---: | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| {row['symbol']} | BUY | {row['quantity']} | False | blocked | BLOCKED | risk_status_BLOCK |"
                for row in order_rows
            )
            + "\n",
            encoding="utf-8",
        )
        order_plan_md.write_text(
            "# Monthly Order Plan\n\n"
            "Execution status: BLOCKED\n"
            "Blocked orders: 5\n"
            + "\n".join(
                f"- {row['symbol']} BUY {row['quantity']}: risk_status_BLOCK"
                for row in order_rows
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "review_packet_csv": review_packet_csv,
            "markdown_blocked_audit_csv": markdown_blocked_audit_csv,
            "order_plan_csv": order_plan_csv,
            "review_packet_md": review_packet_md,
            "markdown_blocked_audit_md": markdown_blocked_audit_md,
            "blocked_summary_md": blocked_summary_md,
            "order_plan_md": order_plan_md,
        }

    def test_valid_inputs_generate_review_only_pass_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertTrue(rows)
            self.assertTrue(all(row["status"] == "PASS" for row in rows))
            self.assertTrue(any(row["check"] == "do_not_trade_banner" for row in rows))

    def test_execution_allowed_true_blocks_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            text = paths["order_plan_csv"].read_text(encoding="utf-8")
            paths["order_plan_csv"].write_text(text.replace("000270,BUY,1,False", "000270,BUY,1,True"), encoding="utf-8")

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertIn("BLOCK", {row["status"] for row in rows})
            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "no_execution_allowed_true")["status"])

    def test_missing_blocked_row_in_summary_blocks_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            text = paths["blocked_summary_md"].read_text(encoding="utf-8")
            paths["blocked_summary_md"].write_text(text.replace("161390", "161399"), encoding="utf-8")

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "blocked_rows_visible")["status"])

    def test_actionable_rows_not_zero_blocks_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            text = paths["review_packet_csv"].read_text(encoding="utf-8")
            paths["review_packet_csv"].write_text(text.replace("actionable_rows=0", "actionable_rows=1"), encoding="utf-8")

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "actionable_rows_zero")["status"])

    def test_broker_submission_allowed_in_packet_blocks_even_when_summary_is_stale(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            text = paths["review_packet_csv"].read_text(encoding="utf-8")
            paths["review_packet_csv"].write_text(
                text.replace("broker_submission=forbidden", "broker_submission=allowed"),
                encoding="utf-8",
            )

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            check = next(row for row in rows if row["check"] == "broker_submission_forbidden")
            self.assertEqual("BLOCK", check["status"])
            self.assertIn("broker_submission=allowed", check["observed"])

    def test_trading_allowed_true_blocks_audit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            text = paths["review_packet_csv"].read_text(encoding="utf-8")
            paths["review_packet_csv"].write_text(text.replace("False", "True", 1), encoding="utf-8")

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "trading_allowed_false")["status"])

    def test_missing_source_file_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            paths["order_plan_csv"].unlink()

            rows = build_monthly_paper_operation_consistency_audit(**paths)

            self.assertEqual("BLOCK", next(row for row in rows if row["check"] == "source_files_present")["status"])

    def test_saver_writes_csv_and_review_only_markdown(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._write_valid_sources(root)
            rows = build_monthly_paper_operation_consistency_audit(**paths)
            csv_output = root / "audit.csv"
            md_output = root / "audit.md"

            save_monthly_paper_operation_consistency_audit(rows, csv_output, md_output)

            saved_rows = _read_csv(csv_output)
            markdown = md_output.read_text(encoding="utf-8")
            self.assertEqual(len(rows), len(saved_rows))
            self.assertIn("Do Not Trade / Review Only", markdown)
            self.assertIn("broker submission", markdown)
            self.assertIn("actionable row count remains `0`", markdown)


if __name__ == "__main__":
    unittest.main()
