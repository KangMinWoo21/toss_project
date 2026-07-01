import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.market_impact import (
    MarketImpactInput,
    estimate_market_impact,
    estimate_market_impact_rows,
    write_market_impact_report,
)


class AutoTradingMarketImpactTests(unittest.TestCase):
    def test_market_impact_increases_with_participation_rate(self):
        low = estimate_market_impact(
            MarketImpactInput(
                symbol="AAPL",
                order_value_usd=10_000.0,
                average_daily_dollar_volume=1_000_000.0,
                annualized_volatility=0.25,
                spread_rate=0.001,
                scenario="base",
            )
        )
        high = estimate_market_impact(
            MarketImpactInput(
                symbol="AAPL",
                order_value_usd=100_000.0,
                average_daily_dollar_volume=1_000_000.0,
                annualized_volatility=0.25,
                spread_rate=0.001,
                scenario="base",
            )
        )

        self.assertGreater(high.estimated_impact_rate, low.estimated_impact_rate)
        self.assertGreater(high.estimated_impact_usd, low.estimated_impact_usd)
        self.assertEqual(low.risk_bucket, "LOW")
        self.assertEqual(high.paper_only, True)
        self.assertEqual(high.execution_allowed, False)

    def test_stress_scenario_increases_impact(self):
        base_input = MarketImpactInput(
            symbol="AAPL",
            order_value_usd=50_000.0,
            average_daily_dollar_volume=1_000_000.0,
            annualized_volatility=0.30,
            spread_rate=0.001,
            scenario="base",
        )
        stress_input = MarketImpactInput(
            symbol="AAPL",
            order_value_usd=50_000.0,
            average_daily_dollar_volume=1_000_000.0,
            annualized_volatility=0.30,
            spread_rate=0.001,
            scenario="stress",
        )

        self.assertGreater(estimate_market_impact(stress_input).estimated_impact_rate, estimate_market_impact(base_input).estimated_impact_rate)

    def test_zero_or_negative_adv_fails_closed(self):
        with self.assertRaises(ValueError):
            estimate_market_impact(
                MarketImpactInput(
                    symbol="AAPL",
                    order_value_usd=50_000.0,
                    average_daily_dollar_volume=0.0,
                    annualized_volatility=0.30,
                    spread_rate=0.001,
                    scenario="base",
                )
            )

    def test_market_impact_rows_and_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "impact.csv"
            rows = estimate_market_impact_rows(
                [
                    MarketImpactInput(
                        symbol="AAPL",
                        order_value_usd=50_000.0,
                        average_daily_dollar_volume=1_000_000.0,
                        annualized_volatility=0.30,
                        spread_rate=0.001,
                        scenario="conservative",
                    )
                ]
            )
            write_market_impact_report(rows, path)

            with path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["symbol"], "AAPL")
            self.assertEqual(written[0]["scenario"], "conservative")
            self.assertEqual(written[0]["paper_only"], "True")


if __name__ == "__main__":
    unittest.main()
