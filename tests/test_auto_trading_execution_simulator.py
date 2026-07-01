import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.execution_simulator import (
    ExecutionSimulationConfig,
    simulate_paper_execution,
    write_execution_simulation_report,
)


class AutoTradingExecutionSimulatorTests(unittest.TestCase):
    def test_simulates_partial_fill_with_liquidity_cap_and_slippage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "as_of,symbol,side,quantity,execution_allowed\n"
                "2026-06-30,AAPL,BUY,100,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-06-30,AAPL,100,110,90,105,105,1000,yahoo,2026-07-01T06:00:00+09:00\n",
                encoding="utf-8",
            )

            rows = simulate_paper_execution(
                orders_path=orders,
                prices_dir=prices,
                config=ExecutionSimulationConfig(
                    fill_policy="close",
                    max_adv_participation=0.05,
                    spread_rate=0.001,
                    slippage_rate=0.002,
                    execution_time_kst="2026-07-01T06:00:00+09:00",
                ),
            )

            self.assertEqual(rows[0]["fill_status"], "PARTIAL")
            self.assertEqual(rows[0]["requested_quantity"], "100")
            self.assertEqual(rows[0]["filled_quantity"], "50")
            self.assertEqual(rows[0]["simulated"], "True")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertGreater(float(rows[0]["simulated_fill_price"]), 105.0)

    def test_simulates_no_fill_when_liquidity_cap_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "as_of,symbol,side,quantity,execution_allowed\n"
                "2026-06-30,AAPL,BUY,10,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-06-30,AAPL,100,110,90,105,105,0,yahoo,2026-07-01T06:00:00+09:00\n",
                encoding="utf-8",
            )

            rows = simulate_paper_execution(
                orders_path=orders,
                prices_dir=prices,
                config=ExecutionSimulationConfig(fill_policy="open", execution_time_kst="2026-07-01T06:00:00+09:00"),
            )

            self.assertEqual(rows[0]["fill_status"], "NO_FILL")
            self.assertEqual(rows[0]["filled_quantity"], "0")
            self.assertIn("insufficient_liquidity", rows[0]["fill_reasons"])

    def test_next_bar_policy_blocks_lookahead_when_bar_not_usable_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "as_of,symbol,side,quantity,execution_allowed\n"
                "2026-06-30,AAPL,BUY,10,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-07-01,AAPL,106,110,100,108,108,1000,yahoo,2026-07-02T06:00:00+09:00\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                simulate_paper_execution(
                    orders_path=orders,
                    prices_dir=prices,
                    config=ExecutionSimulationConfig(
                        fill_policy="next_bar",
                        execution_time_kst="2026-07-01T09:30:00+09:00",
                    ),
                )

    def test_vwap_proxy_and_report_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "as_of,symbol,side,quantity,execution_allowed\n"
                "2026-06-30,AAPL,SELL,10,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-06-30,AAPL,100,112,98,110,110,1000,yahoo,2026-07-01T06:00:00+09:00\n",
                encoding="utf-8",
            )

            rows = simulate_paper_execution(
                orders_path=orders,
                prices_dir=prices,
                config=ExecutionSimulationConfig(fill_policy="vwap_proxy", execution_time_kst="2026-07-01T06:00:00+09:00"),
            )
            output = root / "fills.csv"
            write_execution_simulation_report(rows, output)

            self.assertEqual(rows[0]["reference_price_basis"], "vwap_proxy")
            with output.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["simulated"], "True")


if __name__ == "__main__":
    unittest.main()
