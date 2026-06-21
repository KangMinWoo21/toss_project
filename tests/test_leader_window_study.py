import unittest

from backtester.leader_window_study import classify_regime, generate_date_windows, summarize_window_rows
from backtester.models import Candle


class LeaderWindowStudyTests(unittest.TestCase):
    def test_generate_date_windows_uses_requested_length_and_step(self):
        dates = [f"2024-01-{day:02d}" for day in range(1, 8)]

        windows = generate_date_windows(dates, window_size=3, step_size=2)

        self.assertEqual(
            windows,
            [
                ("2024-01-01", "2024-01-03"),
                ("2024-01-03", "2024-01-05"),
                ("2024-01-05", "2024-01-07"),
            ],
        )

    def test_classify_regime_from_equal_weight_buy_hold(self):
        self.assertEqual(classify_regime(15.0), "up")
        self.assertEqual(classify_regime(-12.0), "down")
        self.assertEqual(classify_regime(3.0), "sideways")

    def test_summarize_window_rows_groups_by_config_length_and_regime(self):
        rows = [
            {
                "config_name": "base",
                "window_length": 126,
                "regime": "up",
                "return_pct": 10.0,
                "buy_hold_pct": 5.0,
                "excess_pct": 5.0,
                "mdd_pct": -3.0,
            },
            {
                "config_name": "base",
                "window_length": 126,
                "regime": "up",
                "return_pct": -2.0,
                "buy_hold_pct": 3.0,
                "excess_pct": -5.0,
                "mdd_pct": -4.0,
            },
        ]

        summary = summarize_window_rows(rows)

        self.assertEqual(summary[0]["windows"], 2)
        self.assertEqual(summary[0]["avg_return_pct"], 4.0)
        self.assertEqual(summary[0]["positive_window_pct"], 50.0)


def _candle(day: int, close: float) -> Candle:
    return Candle(
        date=f"2024-01-{day:02d}",
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


if __name__ == "__main__":
    unittest.main()
