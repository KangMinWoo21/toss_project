import unittest
from dataclasses import dataclass

from backtester.monthly.validation import (
    candidate_decision_required_for_report_paths,
    numeric_delta,
    risk_exit_code,
    risk_status,
    scenario_delta_classification,
    scenario_delta_diagnostic,
)


@dataclass(frozen=True)
class _Check:
    status: str


class MonthlyValidationHelperTests(unittest.TestCase):
    def test_candidate_decision_required_for_report_paths_matches_candidate_filename(self) -> None:
        self.assertTrue(
            candidate_decision_required_for_report_paths(
                [
                    None,
                    "data/reports/monthly_deployment_gate_candidate_proxy_guard.csv",
                    "data/reports/monthly_performance_audit.csv",
                ]
            )
        )
        self.assertFalse(
            candidate_decision_required_for_report_paths(
                [
                    "data/reports/monthly_deployment_gate.csv",
                    "data/reports/monthly_performance_audit.csv",
                ]
            )
        )

    def test_numeric_delta_returns_none_for_missing_inputs(self) -> None:
        self.assertIsNone(numeric_delta(None, 1.0))
        self.assertIsNone(numeric_delta(2.0, None))
        self.assertEqual(numeric_delta(2.5, 1.0), 1.5)

    def test_risk_status_prioritizes_block_then_warn_then_pass(self) -> None:
        self.assertEqual(risk_status([_Check("PASS"), _Check("WARN")]), "WARN")
        self.assertEqual(risk_status([_Check("PASS"), _Check("BLOCK"), _Check("WARN")]), "BLOCK")
        self.assertEqual(risk_status([_Check("PASS")]), "PASS")

    def test_risk_exit_code_blocks_only_for_block_status(self) -> None:
        self.assertEqual(risk_exit_code("PASS"), 0)
        self.assertEqual(risk_exit_code("WARN"), 0)
        self.assertEqual(risk_exit_code("BLOCK"), 2)

    def test_scenario_delta_classification_names_state_transition(self) -> None:
        self.assertEqual(scenario_delta_classification(True, False), "RESOLVED")
        self.assertEqual(scenario_delta_classification(False, True), "NEW_FAILURE")
        self.assertEqual(scenario_delta_classification(True, True), "UNCHANGED_FAILURE")
        self.assertEqual(scenario_delta_classification(False, False), "UNCHANGED_PASS")

    def test_scenario_delta_diagnostic_describes_new_failure_reason(self) -> None:
        self.assertEqual(
            scenario_delta_diagnostic(
                "NEW_FAILURE",
                baseline_reason="",
                candidate_reason="max_drawdown_breach",
                excess_delta=0.2,
                drawdown_delta=-1.0,
                trade_delta=0.0,
            ),
            "equity_improved_but_drawdown_buffer_worse",
        )
        self.assertEqual(
            scenario_delta_diagnostic(
                "NEW_FAILURE",
                baseline_reason="",
                candidate_reason="negative_excess_return",
                excess_delta=-0.4,
                drawdown_delta=0.0,
                trade_delta=0.0,
            ),
            "over_defense_or_filter_drag",
        )

    def test_scenario_delta_diagnostic_describes_unchanged_failure(self) -> None:
        self.assertEqual(
            scenario_delta_diagnostic(
                "UNCHANGED_FAILURE",
                baseline_reason="negative_excess_return",
                candidate_reason="negative_excess_return",
                excess_delta=0.0,
                drawdown_delta=0.0,
                trade_delta=0.0,
            ),
            "same_failure_persists",
        )


if __name__ == "__main__":
    unittest.main()
