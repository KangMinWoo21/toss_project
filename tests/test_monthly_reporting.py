import unittest

from backtester.monthly.reporting import (
    count_diagnostic_rows,
    format_equal_symbol_weights,
    format_optional_float,
    min_numeric_row,
    sum_numeric,
    unique_join,
)


class MonthlyReportingTests(unittest.TestCase):
    def test_format_optional_float_trims_trailing_zeroes(self) -> None:
        self.assertEqual(format_optional_float(None), "")
        self.assertEqual(format_optional_float(1.2300), "1.23")
        self.assertEqual(format_optional_float(1.0), "1")
        self.assertEqual(format_optional_float(-0.1250), "-0.125")

    def test_format_equal_symbol_weights_uses_stable_equal_weights(self) -> None:
        self.assertEqual(format_equal_symbol_weights([]), "")
        self.assertEqual(format_equal_symbol_weights(["005930"]), "005930:1")
        self.assertEqual(
            format_equal_symbol_weights(["005930", "000660", "035420"]),
            "005930:0.3333;000660:0.3333;035420:0.3333",
        )

    def test_sum_numeric_ignores_missing_and_non_numeric_values(self) -> None:
        self.assertEqual(sum_numeric(["1.5", "", None, "bad", 2]), 3.5)
        self.assertIsNone(sum_numeric(["", None, "bad"]))

    def test_min_numeric_row_returns_row_with_lowest_numeric_column(self) -> None:
        rows = [
            {"date": "2026-06-28", "drawdown_delta_pct": ""},
            {"date": "2026-06-29", "drawdown_delta_pct": "-1.2"},
            {"date": "2026-06-30", "drawdown_delta_pct": "-0.4"},
        ]

        self.assertEqual(
            min_numeric_row(rows, "drawdown_delta_pct"),
            {"date": "2026-06-29", "drawdown_delta_pct": "-1.2"},
        )
        self.assertEqual(min_numeric_row(rows, "missing"), {})

    def test_count_diagnostic_rows_counts_semicolon_separated_tokens(self) -> None:
        rows = [
            {"diagnostic": "equity_regression;drawdown_improved"},
            {"diagnostic": "equity_regression"},
            {"diagnostic": "same_path"},
        ]

        self.assertEqual(count_diagnostic_rows(rows, "equity_regression"), 2)
        self.assertEqual(count_diagnostic_rows(rows, "symbol_rotation"), 0)

    def test_unique_join_preserves_first_seen_nonempty_values(self) -> None:
        self.assertEqual(
            unique_join([" alpha ", "", "beta", "alpha", " gamma "]),
            "alpha; beta; gamma",
        )


if __name__ == "__main__":
    unittest.main()
