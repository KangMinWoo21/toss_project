import unittest

from backtester.monthly.reporting import (
    format_equal_symbol_weights,
    format_optional_float,
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

    def test_unique_join_preserves_first_seen_nonempty_values(self) -> None:
        self.assertEqual(
            unique_join([" alpha ", "", "beta", "alpha", " gamma "]),
            "alpha; beta; gamma",
        )


if __name__ == "__main__":
    unittest.main()
