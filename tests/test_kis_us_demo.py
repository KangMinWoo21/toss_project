import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import backtester.__main__ as cli


ROOT = Path(__file__).resolve().parents[1]


class KisUsDemoTests(unittest.TestCase):
    def test_sample_inputs_are_present_with_expected_headers(self):
        expected_headers = {
            ROOT / "data/examples/kis_us_targets_sample.csv": ["symbol", "exchange", "target_weight"],
            ROOT / "data/examples/kis_us_protected_positions_sample.csv": ["symbol", "reason"],
            ROOT / "data/examples/kis_us_demo_positions.csv": [
                "symbol",
                "exchange",
                "quantity",
                "market_value",
                "average_price",
            ],
            ROOT / "data/examples/kis_us_demo_quotes.csv": ["symbol", "exchange", "price"],
        }
        for path, headers in expected_headers.items():
            with self.subTest(path=path):
                with path.open(newline="", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    self.assertEqual(reader.fieldnames, headers)
                    self.assertGreater(len(list(reader)), 0)

    def test_kis_us_paper_plan_demo_writes_outputs_without_kis_env(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "demo_plan.csv"
            summary = root / "demo_plan.md"
            with patch.dict("os.environ", {}, clear=True), patch.object(
                sys,
                "argv",
                [
                    "backtester",
                    "kis-us-paper-plan-demo",
                    "--as-of",
                    "2026-07-01",
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                ],
            ):
                code = cli.main()
            with output.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            markdown = summary.read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))
        self.assertIn("TSLA", {row["symbol"] for row in rows})
        self.assertTrue(
            any(row["symbol"] == "TSLA" and row["risk_status"] == "BLOCKED" for row in rows)
        )
        self.assertIn("paper-only", markdown)
        self.assertIn("dry-run", markdown)
        self.assertIn("no order submitted", markdown)

    def test_runbook_documents_env_cli_and_demo_safety(self):
        runbook = (ROOT / "docs/kis-us-paper-only-runbook.md").read_text(encoding="utf-8")
        self.assertIn("KIS_APP_KEY", runbook)
        self.assertIn("python -m backtester kis-us-paper-plan", runbook)
        self.assertIn("python -m backtester kis-us-paper-plan-demo", runbook)
        self.assertIn("execution_allowed=False", runbook)
        self.assertIn("실주문", runbook)


if __name__ == "__main__":
    unittest.main()
