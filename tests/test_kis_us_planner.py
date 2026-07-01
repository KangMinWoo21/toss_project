import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.kis_us.models import KisUsPosition, KisUsQuote, ProtectedPosition
from backtester.kis_us.planner import build_kis_us_order_plan, load_targets


class KisUsPlannerTests(unittest.TestCase):
    def test_load_targets_requires_exchange_and_rejects_duplicates(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "targets.csv"
            path.write_text("symbol,exchange,target_weight\nAAPL,NAS,0.3\nAAPL,NAS,0.2\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_targets(path)

    def test_builds_buy_sell_and_protected_skip_with_all_execution_blocked(self):
        targets = [
            load_targets_row("AAPL", "NAS", 0.50),
            load_targets_row("MSFT", "NAS", 0.10),
        ]
        positions = [
            KisUsPosition(symbol="AAPL", exchange="NAS", quantity=1, market_value=100.0, average_price=90.0),
            KisUsPosition(symbol="MSFT", exchange="NAS", quantity=4, market_value=400.0, average_price=80.0),
            KisUsPosition(symbol="TSLA", exchange="NAS", quantity=2, market_value=200.0, average_price=100.0),
        ]
        quotes = {
            "AAPL": KisUsQuote("AAPL", "NAS", 100.0),
            "MSFT": KisUsQuote("MSFT", "NAS", 100.0),
            "TSLA": KisUsQuote("TSLA", "NAS", 100.0),
        }
        protected = {"TSLA": ProtectedPosition("TSLA", "do not sell")}

        orders = build_kis_us_order_plan(
            targets=targets,
            positions=positions,
            quotes=quotes,
            protected_positions=protected,
            cash_usd=500.0,
            as_of="2026-07-01",
            created_at="2026-07-01T09:00:00+09:00",
        )

        by_symbol = {order.symbol: order for order in orders}
        self.assertEqual(by_symbol["AAPL"].side, "BUY")
        self.assertEqual(by_symbol["AAPL"].quantity, 4)
        self.assertEqual(by_symbol["MSFT"].side, "SELL")
        self.assertEqual(by_symbol["MSFT"].quantity, 3)
        self.assertEqual(by_symbol["TSLA"].side, "SKIP")
        self.assertEqual(by_symbol["TSLA"].risk_status, "BLOCKED")
        self.assertIn("protected_position", by_symbol["TSLA"].risk_reasons)
        self.assertTrue(all(order.execution_allowed is False for order in orders))

    def test_missing_quote_blocks_target_symbol(self):
        [target] = [load_targets_row("AAPL", "NAS", 0.5)]

        orders = build_kis_us_order_plan(
            targets=[target],
            positions=[],
            quotes={},
            protected_positions={},
            cash_usd=1000.0,
            as_of="2026-07-01",
            created_at="2026-07-01T09:00:00+09:00",
        )

        self.assertEqual(orders[0].side, "SKIP")
        self.assertEqual(orders[0].risk_status, "BLOCKED")
        self.assertIn("missing_quote", orders[0].risk_reasons)


def load_targets_row(symbol: str, exchange: str, target_weight: float):
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "targets.csv"
        path.write_text(f"symbol,exchange,target_weight\n{symbol},{exchange},{target_weight}\n", encoding="utf-8")
        return load_targets(path)[0]


if __name__ == "__main__":
    unittest.main()
