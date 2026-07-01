import csv
import io
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import backtester.__main__ as cli
from backtester.kis_us.models import KisUsPosition, KisUsQuote


class _FakeClient:
    instances = []
    fail_cash_reads = False

    def __init__(self, config):
        self.config = config
        self.balance_exchanges = []
        _FakeClient.instances.append(self)

    def issue_token(self):
        return "fake-token"

    def fetch_balance(self, exchange):
        self.balance_exchanges.append(exchange)
        if exchange == "NASD":
            return [KisUsPosition("AAPL", "NAS", 1, 100.0, 90.0)], 900.0
        return [], 0.0

    def fetch_present_cash_usd(self):
        if self.fail_cash_reads:
            raise AssertionError("cash override should skip present cash API")
        return 5000.0

    def fetch_integrated_margin_cash_usd(self):
        raise AssertionError("KIS US mock flow should not call integrated margin API")

    def fetch_quote(self, symbol, exchange):
        return KisUsQuote(symbol, exchange, 100.0)


class KisUsCliTests(unittest.TestCase):
    def test_kis_us_paper_plan_writes_outputs_with_mocked_client(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            targets = root / "targets.csv"
            output = root / "plan.csv"
            summary = root / "plan.md"
            targets.write_text("symbol,exchange,target_weight\nAAPL,NAS,0.5\n", encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "KIS_APP_KEY": "app",
                    "KIS_APP_SECRET": "secret",
                    "KIS_ACCOUNT_NO": "12345678",
                    "KIS_ACCOUNT_PRODUCT_CODE": "01",
                    "KIS_MOCK_BASE_URL": "https://openapivts.koreainvestment.com:29443",
                }
            )

            with patch.dict(os.environ, env, clear=True), patch.object(cli, "KisUsClient", _FakeClient), patch.object(
                sys,
                "argv",
                [
                    "backtester",
                    "kis-us-paper-plan",
                    "--targets",
                    str(targets),
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                ],
            ):
                code = cli.main()

            with output.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[0]["execution_allowed"], "False")
        self.assertIn("NASD", _FakeClient.instances[-1].balance_exchanges)

    def test_kis_us_paper_plan_uses_present_cash_when_available(self):
        _FakeClient.instances.clear()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            targets = root / "targets.csv"
            output = root / "plan.csv"
            summary = root / "plan.md"
            targets.write_text("symbol,exchange,target_weight\nNVDA,NAS,0.5\n", encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "KIS_APP_KEY": "app",
                    "KIS_APP_SECRET": "secret",
                    "KIS_ACCOUNT_NO": "12345678",
                    "KIS_ACCOUNT_PRODUCT_CODE": "01",
                    "KIS_MOCK_BASE_URL": "https://openapivts.koreainvestment.com:29443",
                }
            )

            with patch.dict(os.environ, env, clear=True), patch.object(cli, "KisUsClient", _FakeClient), patch.object(
                sys,
                "argv",
                [
                    "backtester",
                    "kis-us-paper-plan",
                    "--targets",
                    str(targets),
                    "--balance-exchanges",
                    "NASD",
                    "--output",
                    str(output),
                    "--summary-output",
                    str(summary),
                ],
            ):
                code = cli.main()

            with output.open(newline="", encoding="utf-8") as f:
                rows = {row["symbol"]: row for row in csv.DictReader(f)}

        self.assertEqual(code, 0)
        self.assertEqual(rows["NVDA"]["side"], "BUY")
        self.assertEqual(rows["NVDA"]["quantity"], "25")

    def test_kis_us_paper_plan_cash_override_skips_cash_read_apis(self):
        _FakeClient.instances.clear()
        _FakeClient.fail_cash_reads = True
        try:
            with TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                targets = root / "targets.csv"
                output = root / "plan.csv"
                summary = root / "plan.md"
                targets.write_text("symbol,exchange,target_weight\nNVDA,NAS,0.5\n", encoding="utf-8")
                env = os.environ.copy()
                env.update(
                    {
                        "KIS_APP_KEY": "app",
                        "KIS_APP_SECRET": "secret",
                        "KIS_ACCOUNT_NO": "12345678",
                        "KIS_ACCOUNT_PRODUCT_CODE": "01",
                        "KIS_MOCK_BASE_URL": "https://openapivts.koreainvestment.com:29443",
                    }
                )

                with patch.dict(os.environ, env, clear=True), patch.object(
                    cli, "KisUsClient", _FakeClient
                ), patch.object(
                    sys,
                    "argv",
                    [
                        "backtester",
                        "kis-us-paper-plan",
                        "--targets",
                        str(targets),
                        "--balance-exchanges",
                        "NASD",
                        "--cash-usd",
                        "10000",
                        "--output",
                        str(output),
                        "--summary-output",
                        str(summary),
                    ],
                ):
                    code = cli.main()

                with output.open(newline="", encoding="utf-8") as f:
                    rows = {row["symbol"]: row for row in csv.DictReader(f)}
        finally:
            _FakeClient.fail_cash_reads = False

        self.assertEqual(code, 0)
        self.assertEqual(rows["NVDA"]["side"], "BUY")
        self.assertEqual(rows["NVDA"]["quantity"], "50")

    def test_kis_us_smoke_check_writes_redacted_report_with_mocked_client(self):
        _FakeClient.instances.clear()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "smoke.md"
            env = os.environ.copy()
            env.update(
                {
                    "KIS_APP_KEY": "app",
                    "KIS_APP_SECRET": "secret",
                    "KIS_ACCOUNT_NO": "12345678",
                    "KIS_ACCOUNT_PRODUCT_CODE": "01",
                    "KIS_MOCK_BASE_URL": "https://openapivts.koreainvestment.com:29443",
                }
            )
            stdout = io.StringIO()

            with patch.dict(os.environ, env, clear=True), patch.object(cli, "KisUsClient", _FakeClient), patch.object(
                sys,
                "argv",
                [
                    "backtester",
                    "kis-us-smoke-check",
                    "--symbols",
                    "AAPL",
                    "--output",
                    str(output),
                ],
            ), patch("sys.stdout", stdout):
                code = cli.main()
            markdown = output.read_text(encoding="utf-8")
            console = stdout.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("token: PASS", markdown)
        self.assertIn("balance NASD: PASS", markdown)
        self.assertIn("quote AAPL/NAS: PASS", markdown)
        self.assertIn("paper-only", markdown)
        self.assertIn("no order submitted", markdown)
        self.assertNotIn("secret", markdown)
        self.assertNotIn("12345678", markdown)
        self.assertNotIn("secret", console)
        self.assertNotIn("12345678", console)
        self.assertIn("NASD", _FakeClient.instances[-1].balance_exchanges)

    def test_kis_us_smoke_check_can_throttle_multiple_quote_reads(self):
        _FakeClient.instances.clear()
        env = os.environ.copy()
        env.update(
            {
                "KIS_APP_KEY": "app",
                "KIS_APP_SECRET": "secret",
                "KIS_ACCOUNT_NO": "12345678",
                "KIS_ACCOUNT_PRODUCT_CODE": "01",
                "KIS_MOCK_BASE_URL": "https://openapivts.koreainvestment.com:29443",
            }
        )
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "smoke.md"
            with patch.dict(os.environ, env, clear=True), patch.object(cli, "KisUsClient", _FakeClient), patch.object(
                cli.time,
                "sleep",
            ) as sleep, patch.object(
                sys,
                "argv",
                [
                    "backtester",
                    "kis-us-smoke-check",
                    "--symbols",
                    "AAPL,NVDA",
                    "--request-interval-seconds",
                    "0.5",
                    "--output",
                    str(output),
                ],
            ):
                code = cli.main()

        self.assertEqual(code, 0)
        self.assertGreaterEqual(sleep.call_count, 2)
        sleep.assert_any_call(0.5)


if __name__ == "__main__":
    unittest.main()
