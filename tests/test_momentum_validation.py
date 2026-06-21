import unittest
from datetime import date, timedelta

from backtester.models import Candle
from backtester.momentum_rotation import MomentumRotationResult
from backtester.momentum_validation import (
    MomentumValidationWindow,
    generate_calendar_year_subwindows,
    generate_train_stability_windows,
    generate_yearly_walk_forward_windows,
    run_walk_forward_validation,
    slice_asof_symbol_candles,
    select_best_train_candidate,
    summarize_deployment_gate,
)


def _candles(start: str, count: int) -> list[Candle]:
    start_date = date.fromisoformat(start)
    return [
        Candle(
            date=(start_date + timedelta(days=index)).isoformat(),
            open=100,
            high=101,
            low=99,
            close=100 + index,
            volume=1000,
        )
        for index in range(count)
    ]


def _price_candles(rows: list[tuple[str, float]]) -> list[Candle]:
    return [
        Candle(date=row_date, open=close, high=close + 1, low=close - 1, close=close, volume=1000)
        for row_date, close in rows
    ]


def _always_bad_train_runner(symbol_candles, config) -> MomentumRotationResult:
    return MomentumRotationResult(
        initial_cash=10_000_000,
        final_equity=9_000_000,
        total_return_pct=-10.0,
        buy_hold_return_pct=0.0,
        excess_return_pct=-10.0,
        max_drawdown_pct=-10.0,
        trade_count=1,
        trades=[],
        equity_curve=[10_000_000, 9_000_000],
        dates=[],
    )


def _always_good_train_bad_test_runner(symbol_candles, config) -> MomentumRotationResult:
    first_date = min(candle.date for candles in symbol_candles.values() for candle in candles)
    if first_date.startswith("2020"):
        return MomentumRotationResult(
            initial_cash=10_000_000,
            final_equity=12_000_000,
            total_return_pct=20.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=20.0,
            max_drawdown_pct=-5.0,
            trade_count=3,
            trades=[],
            equity_curve=[10_000_000, 12_000_000],
            dates=[],
        )
    return MomentumRotationResult(
        initial_cash=10_000_000,
        final_equity=8_000_000,
        total_return_pct=-20.0,
        buy_hold_return_pct=0.0,
        excess_return_pct=-20.0,
        max_drawdown_pct=-20.0,
        trade_count=3,
        trades=[],
        equity_curve=[10_000_000, 8_000_000],
        dates=[],
    )


class MomentumValidationTests(unittest.TestCase):
    def test_generate_yearly_windows_excludes_holdout_from_test_periods(self):
        windows = generate_yearly_walk_forward_windows(
            first_year=2018,
            last_year=2026,
            train_years=3,
            test_years=1,
            holdout_start="2025-01-01",
        )

        self.assertEqual(windows[0].train_start, "2018-01-01")
        self.assertEqual(windows[0].train_end, "2020-12-31")
        self.assertEqual(windows[0].test_start, "2021-01-01")
        self.assertEqual(windows[-1].test_end, "2024-12-31")
        self.assertTrue(all(window.test_end < "2025-01-01" for window in windows))

    def test_select_best_train_candidate_requires_positive_excess_and_trades(self):
        selected = select_best_train_candidate(
            [
                {"preset": "balanced", "excess_return_pct": 30.0, "max_drawdown_pct": -10.0, "trades": 0},
                {"preset": "aggressive", "excess_return_pct": -1.0, "max_drawdown_pct": -1.0, "trades": 10},
                {"preset": "retail", "excess_return_pct": 15.0, "max_drawdown_pct": -3.0, "trades": 4},
            ],
            min_train_trades=1,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["preset"], "retail")

    def test_select_best_train_candidate_penalizes_drawdown(self):
        selected = select_best_train_candidate(
            [
                {"preset": "balanced", "excess_return_pct": 20.0, "max_drawdown_pct": -4.0, "trades": 3},
                {"preset": "aggressive", "excess_return_pct": 25.0, "max_drawdown_pct": -20.0, "trades": 3},
            ],
            min_train_trades=1,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["preset"], "balanced")

    def test_select_best_train_candidate_requires_stability_ratio(self):
        selected = select_best_train_candidate(
            [
                {
                    "preset": "overfit",
                    "excess_return_pct": 80.0,
                    "max_drawdown_pct": -10.0,
                    "trades": 10,
                    "train_positive_ratio": 0.33,
                    "train_worst_subwindow_excess_pct": -20.0,
                },
                {
                    "preset": "stable",
                    "excess_return_pct": 30.0,
                    "max_drawdown_pct": -8.0,
                    "trades": 10,
                    "train_positive_ratio": 0.67,
                    "train_worst_subwindow_excess_pct": -2.0,
                },
            ],
            min_train_trades=1,
            min_train_positive_ratio=0.5,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["preset"], "stable")

    def test_generate_calendar_year_subwindows_uses_only_train_period(self):
        windows = generate_calendar_year_subwindows("2019-01-01", "2021-12-31")

        self.assertEqual([window.train_start for window in windows], ["2019-01-01", "2020-01-01", "2021-01-01"])
        self.assertEqual([window.train_end for window in windows], ["2019-12-31", "2020-12-31", "2021-12-31"])

    def test_generate_train_stability_windows_can_use_two_year_rolling_windows(self):
        windows = generate_train_stability_windows("2018-01-01", "2020-12-31", stability_years=2)

        self.assertEqual([window.train_start for window in windows], ["2018-01-01", "2019-01-01"])
        self.assertEqual([window.train_end for window in windows], ["2019-12-31", "2020-12-31"])

    def test_slice_asof_symbol_candles_requires_trading_near_window_start(self):
        sliced = slice_asof_symbol_candles(
            {
                "early": _candles("2024-01-03", 150),
                "late_listing": _candles("2024-03-01", 150),
            },
            start="2024-01-01",
            end="2024-12-31",
            min_rows=120,
            start_grace_days=14,
        )

        self.assertIn("early", sliced)
        self.assertNotIn("late_listing", sliced)

    def test_summarize_deployment_gate_rejects_low_walk_forward_hit_rate(self):
        summary = summarize_deployment_gate(
            [
                {"accepted": True, "test_excess_return_pct": 10.0},
                {"accepted": False, "test_excess_return_pct": -5.0},
                {"accepted": False, "test_excess_return_pct": 0.0},
            ],
            min_accepted_ratio=0.5,
        )

        self.assertFalse(summary["deployable"])
        self.assertEqual(summary["reject_reason"], "low_walk_forward_acceptance")

    def test_summarize_deployment_gate_accepts_consistent_positive_oos(self):
        summary = summarize_deployment_gate(
            [
                {"accepted": True, "test_excess_return_pct": 10.0},
                {"accepted": True, "test_excess_return_pct": 3.0},
                {"accepted": False, "test_excess_return_pct": 0.0},
            ],
            min_accepted_ratio=0.5,
        )

        self.assertTrue(summary["deployable"])

    def test_no_train_candidate_cash_row_beats_negative_buy_hold(self):
        rows = run_walk_forward_validation(
            {
                "111111": _price_candles(
                    [
                        ("2020-01-01", 100),
                        ("2020-01-02", 100),
                        ("2021-01-01", 100),
                        ("2021-01-02", 50),
                    ]
                )
            },
            [
                MomentumValidationWindow(
                    name="cash_defense",
                    train_start="2020-01-01",
                    train_end="2020-01-02",
                    test_start="2021-01-01",
                    test_end="2021-01-02",
                )
            ],
            presets=["balanced"],
            min_rows_per_window=2,
            min_train_positive_ratio=0.0,
            train_stability_years=1,
            runner=_always_bad_train_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "cash")
        self.assertTrue(rows[0]["accepted"])
        self.assertGreater(rows[0]["test_excess_return_pct"], 0)

    def test_no_train_candidate_cash_row_fails_positive_buy_hold(self):
        rows = run_walk_forward_validation(
            {
                "111111": _price_candles(
                    [
                        ("2020-01-01", 100),
                        ("2020-01-02", 100),
                        ("2021-01-01", 100),
                        ("2021-01-02", 150),
                    ]
                )
            },
            [
                MomentumValidationWindow(
                    name="missed_bull",
                    train_start="2020-01-01",
                    train_end="2020-01-02",
                    test_start="2021-01-01",
                    test_end="2021-01-02",
                )
            ],
            presets=["balanced"],
            min_rows_per_window=2,
            min_train_positive_ratio=0.0,
            train_stability_years=1,
            runner=_always_bad_train_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "cash")
        self.assertFalse(rows[0]["accepted"])
        self.assertLess(rows[0]["test_excess_return_pct"], 0)

    def test_no_train_candidate_uses_market_beta_when_prior_breadth_is_strong(self):
        rows = run_walk_forward_validation(
            {
                "111111": _price_candles(
                    [
                        ("2020-01-01", 100),
                        ("2020-01-02", 110),
                        ("2021-01-01", 110),
                        ("2021-01-02", 130),
                    ]
                )
            },
            [
                MomentumValidationWindow(
                    name="strong_breadth_beta",
                    train_start="2020-01-01",
                    train_end="2020-01-02",
                    test_start="2021-01-01",
                    test_end="2021-01-02",
                )
            ],
            presets=["balanced"],
            min_rows_per_window=2,
            min_train_positive_ratio=0.0,
            train_stability_years=1,
            fallback_breadth_days=2,
            fallback_breadth_threshold=0.5,
            runner=_always_bad_train_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "market_beta")
        self.assertTrue(rows[0]["accepted"])
        self.assertAlmostEqual(rows[0]["test_excess_return_pct"], 0.0)

    def test_weak_prior_breadth_blocks_selected_alpha_candidate(self):
        rows = run_walk_forward_validation(
            {
                "111111": _price_candles(
                    [
                        ("2020-01-01", 110),
                        ("2020-01-02", 100),
                        ("2021-01-01", 100),
                        ("2021-01-02", 90),
                    ]
                )
            },
            [
                MomentumValidationWindow(
                    name="weak_breadth_blocks_alpha",
                    train_start="2020-01-01",
                    train_end="2020-01-02",
                    test_start="2021-01-01",
                    test_end="2021-01-02",
                )
            ],
            presets=["balanced"],
            min_rows_per_window=2,
            min_train_positive_ratio=0.0,
            train_stability_years=1,
            fallback_breadth_days=2,
            fallback_breadth_threshold=0.5,
            weak_breadth_min_train_avg_excess_pct=25.0,
            runner=_always_good_train_bad_test_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "cash")
        self.assertTrue(rows[0]["accepted"])
        self.assertGreater(rows[0]["test_excess_return_pct"], 0)

    def test_weak_prior_breadth_allows_strong_train_alpha_candidate(self):
        rows = run_walk_forward_validation(
            {
                "111111": _price_candles(
                    [
                        ("2020-01-01", 110),
                        ("2020-01-02", 100),
                        ("2021-01-01", 100),
                        ("2021-01-02", 90),
                    ]
                )
            },
            [
                MomentumValidationWindow(
                    name="weak_breadth_allows_strong_alpha",
                    train_start="2020-01-01",
                    train_end="2020-01-02",
                    test_start="2021-01-01",
                    test_end="2021-01-02",
                )
            ],
            presets=["balanced"],
            min_rows_per_window=2,
            min_train_positive_ratio=0.0,
            train_stability_years=1,
            fallback_breadth_days=2,
            fallback_breadth_threshold=0.5,
            weak_breadth_min_train_avg_excess_pct=10.0,
            runner=_always_good_train_bad_test_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "balanced")


if __name__ == "__main__":
    unittest.main()
