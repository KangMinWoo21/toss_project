import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.tca import (
    TcaConfig,
    build_tca_rows,
    save_tca_reports,
)


class AutoTradingTcaTests(unittest.TestCase):
    def test_tca_calculates_buy_and_sell_implementation_shortfall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executions = root / "executions.csv"
            executions.write_text(
                "as_of,symbol,side,requested_quantity,filled_quantity,fill_status,fill_reasons,"
                "reference_price_basis,reference_price,simulated_fill_price,estimated_spread_cost_usd,"
                "estimated_slippage_cost_usd,simulated,paper_only,dry_run,execution_allowed,production_effect\n"
                "2026-07-01,AAPL,BUY,10,10,FILLED,filled,close,100.00,100.15,0.50,1.00,True,True,True,False,none\n"
                "2026-07-01,MSFT,SELL,5,5,FILLED,filled,close,200.00,199.50,0.25,1.00,True,True,True,False,none\n",
                encoding="utf-8",
            )
            impact = root / "impact.csv"
            impact.write_text(
                "symbol,scenario,order_value_usd,average_daily_dollar_volume,participation_rate,"
                "annualized_volatility,spread_rate,estimated_impact_rate,estimated_impact_usd,"
                "risk_bucket,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,base,1000,1000000,0.001,0.20,0.001,0.001,0.75,LOW,True,True,False,none\n"
                "MSFT,base,1000,1000000,0.001,0.20,0.001,0.001,1.50,LOW,True,True,False,none\n",
                encoding="utf-8",
            )

            rows = build_tca_rows(
                executions_path=executions,
                market_impact_path=impact,
                config=TcaConfig(max_shortfall_bps=30.0),
            )

            by_symbol = {row["symbol"]: row for row in rows}
            self.assertEqual(by_symbol["AAPL"]["implementation_shortfall_usd"], "1.500000")
            self.assertEqual(by_symbol["AAPL"]["implementation_shortfall_bps"], "15.000000")
            self.assertEqual(by_symbol["AAPL"]["tca_status"], "PASS")
            self.assertEqual(by_symbol["MSFT"]["implementation_shortfall_usd"], "2.500000")
            self.assertEqual(by_symbol["MSFT"]["implementation_shortfall_bps"], "25.000000")
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["dry_run"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in rows))

    def test_tca_reviews_no_fill_and_fails_closed_for_unsafe_execution_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executions = root / "executions.csv"
            executions.write_text(
                "as_of,symbol,side,requested_quantity,filled_quantity,fill_status,fill_reasons,"
                "reference_price_basis,reference_price,simulated_fill_price,estimated_spread_cost_usd,"
                "estimated_slippage_cost_usd,simulated,paper_only,dry_run,execution_allowed,production_effect\n"
                "2026-07-01,AAPL,BUY,10,0,NO_FILL,insufficient_liquidity,close,100.00,0,0,0,True,True,True,False,none\n",
                encoding="utf-8",
            )
            rows = build_tca_rows(executions_path=executions)
            self.assertEqual(rows[0]["tca_status"], "REVIEW")
            self.assertEqual(rows[0]["tca_reasons"], "no_fill")

            executions.write_text(
                "as_of,symbol,side,requested_quantity,filled_quantity,fill_status,fill_reasons,"
                "reference_price_basis,reference_price,simulated_fill_price,estimated_spread_cost_usd,"
                "estimated_slippage_cost_usd,simulated,paper_only,dry_run,execution_allowed,production_effect\n"
                "2026-07-01,AAPL,BUY,10,10,FILLED,filled,close,100.00,100.10,0.50,0.50,True,True,True,True,none\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_tca_rows(executions_path=executions)

    def test_tca_writes_csv_and_markdown_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executions = root / "executions.csv"
            executions.write_text(
                "as_of,symbol,side,requested_quantity,filled_quantity,fill_status,fill_reasons,"
                "reference_price_basis,reference_price,simulated_fill_price,estimated_spread_cost_usd,"
                "estimated_slippage_cost_usd,simulated,paper_only,dry_run,execution_allowed,production_effect\n"
                "2026-07-01,AAPL,BUY,1,1,FILLED,filled,close,100.00,100.10,0.05,0.10,True,True,True,False,none\n",
                encoding="utf-8",
            )
            rows = build_tca_rows(executions_path=executions)
            csv_path = root / "tca.csv"
            md_path = root / "tca.md"
            save_tca_reports(rows, csv_path, md_path)

            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["symbol"], "AAPL")
            self.assertEqual(written[0]["execution_allowed"], "False")
            self.assertIn("TCA Simulator", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
