import unittest

from backtester.models import Candle
from backtester.monthly.universe import exclude_invalid_price_symbols


class MonthlyUniverseTests(unittest.TestCase):
    def test_exclude_invalid_price_symbols_removes_nonpositive_price_history(self) -> None:
        filtered = exclude_invalid_price_symbols(
            {
                "GOOD": [
                    Candle("2024-01-01", 100, 101, 99, 100, 1_000),
                    Candle("2024-01-02", 101, 102, 100, 101, 1_000),
                ],
                "BAD": [
                    Candle("2024-01-01", 100, 101, 99, 100, 1_000),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                ],
                "EMPTY": [],
            }
        )

        self.assertEqual(set(filtered), {"GOOD"})


if __name__ == "__main__":
    unittest.main()
