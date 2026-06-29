import unittest

from backtester.risk import validate_portfolio_risk, risk_status


class RiskTests(unittest.TestCase):
    def test_validate_portfolio_risk_blocks_oversized_and_blocked_symbols(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.4, "000660": 0.1},
            prices={"005930": 50_000, "000660": 100_000},
            max_position_weight=0.3,
            max_positions=10,
            blocked_symbols={"005930"},
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        details = "; ".join(check.detail for check in checks)
        self.assertIn("005930", details)
        self.assertIn("max_position_weight", {check.name for check in checks})
        self.assertIn("blocked_symbols", {check.name for check in checks})

    def test_validate_portfolio_risk_blocks_missing_prices(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.2},
            prices={},
            max_position_weight=0.3,
            max_positions=10,
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertEqual([check.name for check in checks if check.status == "BLOCK"], ["missing_prices"])

    def test_validate_portfolio_risk_blocks_when_adv_is_missing(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.2},
            prices={"005930": 50_000},
            max_position_weight=0.3,
            max_positions=10,
            target_amounts={"005930": 1_000_000},
            average_daily_values={},
            max_adv_participation=0.1,
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        liquidity = [check for check in checks if check.name == "liquidity"][0]
        self.assertIn("adv_unavailable", liquidity.detail)

    def test_validate_portfolio_risk_blocks_when_participation_exceeds_max(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.2},
            prices={"005930": 50_000},
            max_position_weight=0.3,
            max_positions=10,
            target_amounts={"005930": 1_000_000},
            average_daily_values={"005930": 2_000_000},
            max_adv_participation=0.1,
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        liquidity = [check for check in checks if check.name == "liquidity"][0]
        self.assertIn("005930", liquidity.detail)
        self.assertIn(">0.1000", liquidity.detail)

    def test_validate_portfolio_risk_warns_when_participation_exceeds_warning_threshold(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.2},
            prices={"005930": 50_000},
            max_position_weight=0.3,
            max_positions=10,
            target_amounts={"005930": 150_000},
            average_daily_values={"005930": 2_000_000},
            max_adv_participation=0.1,
            warn_adv_participation_rate=0.05,
        )

        self.assertEqual(risk_status(checks), "WARN")
        liquidity = [check for check in checks if check.name == "liquidity"][0]
        self.assertIn(">0.0500", liquidity.detail)

    def test_validate_portfolio_risk_passes_for_normal_liquidity(self):
        checks = validate_portfolio_risk(
            target_weights={"005930": 0.2},
            prices={"005930": 50_000},
            max_position_weight=0.3,
            max_positions=10,
            target_amounts={"005930": 50_000},
            average_daily_values={"005930": 2_000_000},
            max_adv_participation=0.1,
            warn_adv_participation_rate=0.05,
        )

        liquidity = [check for check in checks if check.name == "liquidity"][0]
        self.assertEqual(liquidity.status, "PASS")


if __name__ == "__main__":
    unittest.main()
