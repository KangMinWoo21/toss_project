import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.readiness import (
    evaluate_readiness,
    recommend_readiness_actions,
    readiness_exit_code,
    readiness_status,
    save_readiness_markdown,
    save_readiness_report,
)


class ProductionReadinessTests(unittest.TestCase):
    def test_missing_required_artifact_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.csv"

            checks = evaluate_readiness(required_artifacts=[missing])

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "artifact:missing.csv")
        self.assertEqual(checks[0].status, "BLOCK")

    def test_non_deployable_gate_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            gate = Path(temp_dir) / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "False,failed_required_scenarios,monthly-validate,0,0,0,0,0,False\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(deployment_gate_path=gate)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "deployment_gate")
        self.assertIn("failed_required_scenarios", checks[0].detail)

    def test_validation_scenario_failures_block_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,required,deployable,reason,universe_bias_reasons\n"
                "full_period,True,False,universe_bias_warning,high_average_symbol_return;extreme_return_share\n"
                "stress_drawdown,True,False,max_drawdown_breach\n"
                "duration_3m,True,True,passed\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "validation_scenarios")
        self.assertIn("full_period", checks[0].detail)
        self.assertIn("universe_bias_warning=1", checks[0].detail)
        self.assertIn("max_drawdown_breach=1", checks[0].detail)
        self.assertIn("extreme_return_share=1", checks[0].detail)

    def test_risk_report_block_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            risk = Path(temp_dir) / "risk.csv"
            risk.write_text(
                "name,status,detail\n"
                "deployment_gate,BLOCK,gate blocked\n"
                "orders,PASS,valid\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(risk_report_path=risk)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "risk_report")
        self.assertIn("deployment_gate", checks[0].detail)

    def test_performance_report_warning_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            performance = Path(temp_dir) / "performance.csv"
            performance.write_text(
                "name,status,detail\n"
                "walk_forward_margin,WARN,min_walk_forward_excess_pct=3.2\n"
                "required_scenarios,PASS,0 failed\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(performance_report_path=performance)

        self.assertEqual(readiness_status(checks), "WARN")
        self.assertEqual(checks[0].name, "performance_report")
        self.assertIn("walk_forward_margin", checks[0].detail)

    def test_readiness_exit_code_can_treat_warn_as_block(self):
        self.assertEqual(readiness_exit_code("PASS"), 0)
        self.assertEqual(readiness_exit_code("WARN"), 0)
        self.assertEqual(readiness_exit_code("WARN", strict=True), 2)
        self.assertEqual(readiness_exit_code("BLOCK"), 2)

    def test_low_universe_price_coverage_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            coverage = Path(temp_dir) / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,20,20,80,20.0,BLOCK,AAA;BBB\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(coverage_report_path=coverage)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "universe_price_coverage")
        self.assertIn("min_coverage_pct=20.0", checks[0].detail)
        self.assertIn("need_to_80pct=60", checks[0].detail)
        self.assertIn("batches_of_50=2", checks[0].detail)

    def test_save_readiness_reports(self):
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "readiness.csv"
            md_path = Path(temp_dir) / "readiness.md"
            checks = evaluate_readiness(required_artifacts=[])

            saved_csv = save_readiness_report(checks, csv_path)
            save_readiness_markdown(checks, md_path, title="Test Readiness")

            csv_text = csv_path.read_text(encoding="utf-8")
            md_text = md_path.read_text(encoding="utf-8")

        self.assertEqual(saved_csv, 2)
        self.assertIn("overall", csv_text)
        self.assertIn("PASS", csv_text)
        self.assertIn("# Test Readiness", md_text)
        self.assertIn("Overall status: PASS", md_text)

    def test_recommend_readiness_actions_prioritizes_bias_and_drawdown(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,required,deployable,reason,universe_bias_reasons\n"
                "full_period,True,False,universe_bias_warning,high_average_symbol_return;extreme_return_share\n"
                "stress_drawdown,True,False,max_drawdown_breach\n",
                encoding="utf-8",
            )
            checks = evaluate_readiness(validation_scenarios_path=scenarios)

            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Reduce data bias", action_text)
        self.assertIn("Reduce extreme-winner dependence", action_text)
        self.assertIn("Reduce stress drawdown", action_text)

    def test_recommend_readiness_actions_does_not_expand_coverage_when_coverage_passes(self):
        with TemporaryDirectory() as temp_dir:
            coverage = Path(temp_dir) / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2026-01-31,100,90,90,10,90.0,PASS,\n",
                encoding="utf-8",
            )
            checks = evaluate_readiness(coverage_report_path=coverage)

            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(action.action for action in actions)
        self.assertNotIn("Expand KRX price coverage", action_text)


if __name__ == "__main__":
    unittest.main()
