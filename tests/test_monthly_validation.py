import unittest

from backtester.monthly.validation import (
    numeric_delta,
    scenario_delta_classification,
    scenario_delta_diagnostic,
)


class MonthlyValidationHelperTests(unittest.TestCase):
    def test_numeric_delta_returns_none_for_missing_inputs(self) -> None:
        self.assertIsNone(numeric_delta(None, 1.0))
        self.assertIsNone(numeric_delta(2.0, None))
        self.assertEqual(numeric_delta(2.5, 1.0), 1.5)

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
