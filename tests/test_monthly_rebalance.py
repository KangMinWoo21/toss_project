import csv
import os
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.monthly_rebalance import (
    DeploymentGate,
    MonthlyValidationCase,
    MonthlyRebalanceConfig,
    MonthlyBacktestResult,
    MonthlyBacktestTrade,
    MonthlyDecision,
    PerformanceGuard,
    Position,
    RiskCheck,
    RiskLimits,
    audit_monthly_validation_data,
    audit_point_in_time_price_coverage,
    analyze_monthly_performance_concentration,
    analyze_monthly_benchmark_excess,
    analyze_monthly_benchmark_contributions,
    analyze_monthly_benchmark_selection,
    analyze_monthly_benchmark_selection_summary,
    analyze_monthly_drawdown_attribution,
    analyze_monthly_decision_attribution,
    analyze_monthly_direct_alpha_holding_path,
    analyze_monthly_direct_alpha_path_drift,
    analyze_monthly_direct_alpha_rank_drift,
    analyze_monthly_direct_alpha_selection,
    analyze_monthly_direct_alpha_timing,
    analyze_monthly_path_attribution,
    analyze_monthly_execution_gap,
    analyze_monthly_proxy_guard_recovery_exits,
    analyze_monthly_proxy_guard_outcomes,
    analyze_monthly_guarded_loss_position_pressure,
    analyze_monthly_proxy_decision_diagnostics,
    analyze_monthly_proxy_decision_context_summary,
    analyze_monthly_recovery_attribution,
    analyze_monthly_position_loss_control_diagnostics,
    analyze_monthly_stress_drawdown_pressure,
    analyze_monthly_validation_failures,
    analyze_monthly_train_decision_path,
    analyze_monthly_train_stability_summary,
    analyze_monthly_train_stability_path_drift_experiments,
    analyze_monthly_train_stability_symbol_attribution,
    analyze_monthly_train_stability_windows,
    analyze_monthly_validation_failure_drilldown,
    analyze_monthly_validation_failure_patterns,
    analyze_monthly_validation_remediation,
    analyze_symbol_realized_pnl_attribution,
    build_monthly_validation_sweep_plan,
    build_monthly_validation_candidate_decision,
    build_monthly_validation_candidate_followup_rows,
    build_monthly_validation_candidate_summary,
    compare_monthly_attribution_reports,
    compare_monthly_benchmark_selection_summary_reports,
    compare_monthly_benchmark_selection_window_reports,
    compare_monthly_entry_month_reports,
    compare_monthly_entry_contribution_overlap_reports,
    compare_monthly_entry_selection_eligibility_reports,
    compare_monthly_entry_selection_rotation_reports,
    compare_monthly_entry_path_subperiod_reports,
    compare_monthly_decision_attribution_reports,
    compare_monthly_path_attribution_reports,
    summarize_monthly_path_attribution_comparison,
    compare_monthly_validation_scenario_deltas,
    compare_monthly_validation_reports,
    run_monthly_validation_sweep_results,
    apply_performance_guard,
    build_deployment_gate,
    build_monthly_performance_audit,
    build_monthly_validation_gate,
    compress_decision_to_buyable_targets,
    build_order_plan,
    build_universe_filter_report,
    decide_monthly_allocation,
    diagnose_universe_bias,
    equal_weight_buy_hold_period_return,
    exclude_invalid_price_symbols,
    exclude_top_period_return_symbols,
    filter_monthly_validation_sweep_plan,
    filter_symbol_candles_by_universe,
    generate_monthly_validation_cases,
    is_monthly_rebalance_due,
    load_last_rebalance_date,
    load_performance_guard,
    load_point_in_time_universe,
    liquidity_universe_exposure_scale,
    mark_order_plan_execution,
    market_beta_proxy_neutral_loss_guard_cap,
    market_beta_proxy_reversal_guard_cap,
    market_volatility_exposure_scale,
    risk_exit_code,
    risk_status,
    select_point_in_time_universe,
    select_liquid_universe,
    run_monthly_rebalance_backtest,
    run_monthly_walk_forward_validation,
    run_monthly_validation_suite,
    save_rebalance_state,
    save_monthly_performance_audit_rows,
    save_monthly_performance_concentration,
    save_monthly_benchmark_excess,
    save_monthly_benchmark_contributions,
    save_monthly_benchmark_selection,
    save_monthly_benchmark_selection_summary,
    save_monthly_benchmark_selection_summary_comparison,
    save_monthly_benchmark_selection_window_comparison,
    save_monthly_entry_month_comparison,
    save_monthly_entry_contribution_overlap_comparison,
    save_monthly_entry_selection_eligibility_comparison,
    save_monthly_entry_selection_rotation_comparison,
    save_monthly_entry_path_subperiod_comparison,
    save_monthly_validation_rows,
    save_monthly_validation_failures,
    save_monthly_validation_remediation,
    save_monthly_validation_sweep_plan,
    save_monthly_validation_sweep_results,
    save_monthly_validation_comparison,
    save_monthly_validation_candidate_decision,
    save_monthly_validation_candidate_followup_rows,
    save_monthly_validation_candidate_summary,
    save_monthly_validation_failure_drilldown,
    save_monthly_validation_failure_patterns,
    save_monthly_validation_scenario_deltas,
    save_monthly_attribution_rows,
    save_monthly_attribution_comparison,
    save_monthly_decision_attribution,
    save_monthly_decision_attribution_comparison,
    save_monthly_direct_alpha_holding_path,
    save_monthly_direct_alpha_path_drift,
    save_monthly_direct_alpha_rank_drift,
    save_monthly_direct_alpha_selection,
    save_monthly_direct_alpha_timing,
    save_monthly_path_attribution,
    save_monthly_path_attribution_comparison,
    save_monthly_path_attribution_comparison_summary,
    save_monthly_execution_gap,
    save_monthly_proxy_guard_outcomes,
    save_monthly_proxy_guard_recovery_exits,
    save_monthly_guarded_loss_position_pressure,
    save_monthly_proxy_decision_diagnostics,
    save_monthly_proxy_decision_context_summary,
    save_monthly_recovery_attribution,
    save_monthly_position_loss_control_diagnostics,
    save_monthly_stress_drawdown_pressure,
    save_monthly_train_decision_path,
    save_monthly_train_stability_summary,
    save_monthly_train_stability_path_drift_experiments,
    save_monthly_train_stability_symbol_attribution,
    save_monthly_train_stability_windows,
    save_order_plan,
    save_order_plan_summary,
    save_universe_filter_report,
    save_universe_price_coverage_rows,
    select_buyable_targets,
    scale_monthly_decision_targets,
    event_score_multipliers,
    filter_symbols_by_event_score,
    target_weights_for_symbols,
    validate_candidate_decision_risk,
    candidate_decision_required_for_report_paths,
    validate_report_freshness,
    validate_pre_trade_risk,
)
from backtester.events import EventScoreStore
from backtester.models import Candle


def _candle(day: str, open_price: float, close_price: float | None = None) -> Candle:
    close = open_price if close_price is None else close_price
    return Candle(date=day, open=open_price, high=max(open_price, close), low=min(open_price, close), close=close, volume=1_000)


def _monthly_result(
    *,
    excess_return_pct: float,
    max_drawdown_pct: float,
    trade_count: int = 1,
    decisions: list[MonthlyDecision] | None = None,
) -> MonthlyBacktestResult:
    return MonthlyBacktestResult(
        initial_cash=1_000_000,
        final_equity=1_100_000,
        total_return_pct=10.0,
        buy_hold_return_pct=10.0 - excess_return_pct,
        excess_return_pct=excess_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        trade_count=trade_count,
        decisions=decisions or [],
        trades=[],
        dates=["2026-06-20"],
        equity_curve=[1_100_000],
    )


def _daily_candles(start_day: str, count: int) -> list[Candle]:
    start = date.fromisoformat(start_day)
    return [
        Candle(
            date=(start + timedelta(days=index)).isoformat(),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=1_000,
        )
        for index in range(count)
    ]


def _daily_candles_with_volume(start_day: str, count: int, *, close: float, volume: float) -> list[Candle]:
    start = date.fromisoformat(start_day)
    return [
        Candle(
            date=(start + timedelta(days=index)).isoformat(),
            open=close + index,
            high=close + index + 1,
            low=close + index - 1,
            close=close + index,
            volume=volume,
        )
        for index in range(count)
    ]


def _trend_candles_with_volume(start_day: str, count: int, *, close: float, step: float, volume: float) -> list[Candle]:
    start = date.fromisoformat(start_day)
    rows: list[Candle] = []
    for index in range(count):
        price = close + (step * index)
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=price,
                high=price + 1,
                low=max(1, price - 1),
                close=price,
                volume=volume,
            )
        )
    return rows


def _piecewise_candles_with_volume(
    start_day: str,
    count: int,
    *,
    close: float,
    steps: list[tuple[int, float]],
    volume: float,
) -> list[Candle]:
    start = date.fromisoformat(start_day)
    rows: list[Candle] = []
    price = close
    step_index = 0
    current_step = steps[0][1]
    for index in range(count):
        while step_index + 1 < len(steps) and index >= steps[step_index + 1][0]:
            step_index += 1
            current_step = steps[step_index][1]
        if index > 0:
            price += current_step
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=price,
                high=price + 1,
                low=max(1, price - 1),
                close=price,
                volume=volume,
            )
        )
    return rows


def _priced_candles(start_day: str, prices: list[float], *, volume: float = 1_000) -> list[Candle]:
    start = date.fromisoformat(start_day)
    rows: list[Candle] = []
    for index, price in enumerate(prices):
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=price,
                high=price + 1,
                low=max(1, price - 1),
                close=price,
                volume=volume,
            )
        )
    return rows


class MonthlyRebalanceTests(unittest.TestCase):
    def test_monthly_config_defaults_to_five_candidate_slots(self):
        self.assertEqual(MonthlyRebalanceConfig().train_years, 5)
        self.assertEqual(MonthlyRebalanceConfig().presets, ("balanced",))
        self.assertEqual(MonthlyRebalanceConfig().candidate_pool_size, 7)
        self.assertEqual(MonthlyRebalanceConfig().max_candidate_lookback_return_pct, 90.0)
        self.assertEqual(MonthlyRebalanceConfig().fallback_breadth_threshold, 0.5)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_breadth_threshold, 0.25)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_filter_days, 60)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_min_return_pct, -5.0)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_risk_scale, 0.25)
        self.assertEqual(MonthlyRebalanceConfig().market_volatility_filter_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_trigger_pct, -15.0)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_scale, 0.75)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_deep_trigger_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_deep_scale, 0.5)
        self.assertEqual(MonthlyRebalanceConfig().daily_drawdown_stop_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().cash_buffer_weight, 0.01)
        self.assertEqual(MonthlyRebalanceConfig().position_trailing_stop_reason_contains, "")
        self.assertEqual(MonthlyRebalanceConfig().max_position_weight, 0.15)
        self.assertEqual(MonthlyRebalanceConfig().point_in_time_liquidity_top_n, 100)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_reference_top_n, 100)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_min_scale, 0.8)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_min_top_n, 20)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_size, 12)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_max_exposure, 1.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_breadth_max_exposure, 1.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_loss_guard_max_exposure, 1.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_loss_guard_medium_lookback_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_loss_guard_medium_max_return_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_loss_guard_short_lookback_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_neutral_loss_guard_short_max_return_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_max_exposure, 1.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_medium_lookback_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_medium_return_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_short_lookback_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_short_max_return_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_extreme_return_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_medium_drawdown_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_reversal_guard_recovery_exit_short_return_pct, 0.0)
        self.assertFalse(MonthlyRebalanceConfig().market_beta_proxy_buyable_only)
        self.assertFalse(MonthlyRebalanceConfig().market_beta_proxy_unbuyable_cash_reserve)
        self.assertEqual(MonthlyRebalanceConfig().direct_alpha_target_persistence_signals, 1)
        self.assertEqual(RiskLimits().max_total_target_weight, 1.0)
        self.assertEqual(RiskLimits().max_total_buy_value, 10_000_000.0)
        self.assertEqual(RiskLimits().max_order_count, 15)

    def test_market_beta_proxy_neutral_loss_guard_caps_only_neutral_weak_proxy_momentum(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_neutral_loss_guard_max_exposure=0.55,
            market_beta_proxy_neutral_loss_guard_medium_lookback_days=4,
            market_beta_proxy_neutral_loss_guard_medium_max_return_pct=30.0,
            market_beta_proxy_neutral_loss_guard_short_lookback_days=2,
            market_beta_proxy_neutral_loss_guard_short_max_return_pct=15.0,
            fallback_breadth_threshold=0.8,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles("2025-01-01", [100, 106, 110, 112, 114], volume=10_000),
            "BBB": _priced_candles("2025-01-01", [100, 105, 109, 111, 113], volume=9_000),
        }

        cap, reason = market_beta_proxy_neutral_loss_guard_cap(
            symbol_candles,
            signal_date="2025-01-05",
            current_cap=1.0,
            prior_breadth=0.47,
            config=config,
        )
        strong_cap, strong_reason = market_beta_proxy_neutral_loss_guard_cap(
            symbol_candles,
            signal_date="2025-01-05",
            current_cap=1.0,
            prior_breadth=0.85,
            config=config,
        )

        self.assertEqual(cap, 0.55)
        self.assertEqual(reason, "proxy_neutral_loss_guard_capped")
        self.assertEqual(strong_cap, 1.0)
        self.assertEqual(strong_reason, "proxy_exposure_capped")

    def test_market_beta_proxy_neutral_loss_guard_preserves_neutral_strong_proxy_momentum(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_neutral_loss_guard_max_exposure=0.55,
            market_beta_proxy_neutral_loss_guard_medium_lookback_days=4,
            market_beta_proxy_neutral_loss_guard_medium_max_return_pct=30.0,
            market_beta_proxy_neutral_loss_guard_short_lookback_days=2,
            market_beta_proxy_neutral_loss_guard_short_max_return_pct=15.0,
            fallback_breadth_threshold=0.8,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles("2025-01-01", [100, 118, 130, 145, 155], volume=10_000),
            "BBB": _priced_candles("2025-01-01", [100, 117, 129, 143, 154], volume=9_000),
        }

        cap, reason = market_beta_proxy_neutral_loss_guard_cap(
            symbol_candles,
            signal_date="2025-01-05",
            current_cap=1.0,
            prior_breadth=0.47,
            config=config,
        )

        self.assertEqual(cap, 1.0)
        self.assertEqual(reason, "proxy_exposure_capped")

    def test_market_beta_proxy_reversal_guard_caps_rollover_after_medium_overheat(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=40.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=10.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=70.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [160.0] * 20 + [165.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [150.0] * 20 + [154.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 0.55)
        self.assertEqual(reason, "proxy_reversal_guard_capped")

    def test_market_beta_proxy_reversal_guard_preserves_strong_short_momentum_below_extreme(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=40.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=10.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=70.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [140.0] * 20 + [165.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [145.0] * 20 + [168.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 1.0)
        self.assertEqual(reason, "proxy_exposure_capped")

    def test_market_beta_proxy_reversal_guard_caps_extreme_medium_overheat(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=40.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=10.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=70.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [150.0] * 20 + [190.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [148.0] * 20 + [186.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 0.55)
        self.assertEqual(reason, "proxy_reversal_guard_capped")

    def test_market_beta_proxy_reversal_guard_caps_medium_drawdown_after_overheat(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=5.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=50.0,
            market_beta_proxy_reversal_guard_medium_drawdown_pct=-10.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [150.0] * 10 + [130.0] * 10 + [145.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [148.0] * 10 + [128.0] * 10 + [144.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 0.55)
        self.assertEqual(reason, "proxy_reversal_guard_capped")

    def test_market_beta_proxy_reversal_guard_preserves_continuation_without_medium_drawdown(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=5.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=50.0,
            market_beta_proxy_reversal_guard_medium_drawdown_pct=-10.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [125.0] * 20 + [145.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [126.0] * 20 + [144.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 1.0)
        self.assertEqual(reason, "proxy_exposure_capped")

    def test_market_beta_proxy_reversal_guard_exits_drawdown_cap_after_short_reversal(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=5.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=50.0,
            market_beta_proxy_reversal_guard_medium_drawdown_pct=-10.0,
            market_beta_proxy_reversal_guard_recovery_exit_short_return_pct=-5.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [160.0] * 20 + [140.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [158.0] * 20 + [138.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 1.0)
        self.assertEqual(reason, "proxy_reversal_guard_recovery_exit")

    def test_market_beta_proxy_reversal_guard_keeps_extreme_cap_despite_recovery_exit(self):
        config = MonthlyRebalanceConfig(
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=40,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=20,
            market_beta_proxy_reversal_guard_short_max_return_pct=5.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=50.0,
            market_beta_proxy_reversal_guard_medium_drawdown_pct=-10.0,
            market_beta_proxy_reversal_guard_recovery_exit_short_return_pct=-5.0,
            market_beta_proxy_size=2,
            point_in_time_liquidity_window_days=1,
        )
        symbol_candles = {
            "AAA": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [180.0] * 20 + [170.0] * 20,
                volume=10_000,
            ),
            "BBB": _priced_candles(
                "2025-01-01",
                [100.0] * 21 + [178.0] * 20 + [168.0] * 20,
                volume=9_000,
            ),
        }

        cap, reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date="2025-03-02",
            current_cap=1.0,
            config=config,
        )

        self.assertAlmostEqual(cap, 0.55)
        self.assertEqual(reason, "proxy_reversal_guard_capped")

    def test_risk_gate_blocks_kill_switch_file(self):
        with TemporaryDirectory() as temp_dir:
            kill_switch = Path(temp_dir) / "KILL_SWITCH"
            kill_switch.write_text("pause trading", encoding="utf-8")

            checks = validate_pre_trade_risk(
                MonthlyDecision(
                    as_of_date="2026-06-20",
                    signal_date="2026-06-19",
                    mode="cash",
                    selected_preset="cash",
                    target_weights={},
                    reason="unit-test",
                ),
                [],
                kill_switch_path=kill_switch,
            )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("kill_switch", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_blocks_excess_total_target_weight(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.6, "222222": 0.3},
                reason="unit-test",
            ),
            [],
            limits=RiskLimits(max_total_target_weight=0.8),
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("total_target_weight", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_passes_conservative_buy_plan(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="alpha",
            selected_preset="balanced",
            target_weights={"111111": 0.4, "222222": 0.4},
            reason="unit-test",
        )
        orders = build_order_plan(
            decision,
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 100_000, "222222": 100_000},
            min_trade_value=0,
        )

        checks = validate_pre_trade_risk(
            decision,
            orders,
            limits=RiskLimits(
                max_total_target_weight=0.8,
                max_single_order_value=500_000,
                max_total_buy_value=1_000_000,
                max_order_count=5,
            ),
            day_start_equity=1_000_000,
            current_equity=1_000_000,
        )

        self.assertEqual(risk_status(checks), "PASS")

    def test_risk_gate_blocks_daily_loss_limit(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="cash",
                selected_preset="cash",
                target_weights={},
                reason="unit-test",
            ),
            [],
            limits=RiskLimits(max_daily_loss_pct=3.0),
            day_start_equity=1_000_000,
            current_equity=960_000,
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("daily_loss", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_blocks_failed_deployment_gate(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.4},
                reason="unit-test",
            ),
            [],
            deployment_gate=DeploymentGate(deployable=False, reason="negative_excess_return", source="unit"),
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("deployment_gate", {check.name for check in checks if check.status == "BLOCK"})

    def test_performance_guard_warn_scales_decision_targets(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="alpha",
            selected_preset="balanced",
            target_weights={"111111": 0.5, "222222": 0.4},
            reason="unit-test",
        )

        guarded = apply_performance_guard(
            decision,
            PerformanceGuard(status="WARN", detail="thin margin", scale=0.1, source="unit"),
        )

        self.assertAlmostEqual(guarded.target_weights["111111"], 0.05)
        self.assertAlmostEqual(guarded.target_weights["222222"], 0.04)
        self.assertIn("performance_warn_scale_0.1000", guarded.reason)

    def test_risk_gate_warns_on_performance_guard_warning(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            [],
            performance_guard=PerformanceGuard(status="WARN", detail="thin margin", scale=0.1, source="unit"),
        )

        self.assertEqual(risk_status(checks), "WARN")
        self.assertIn("performance_guard", {check.name for check in checks if check.status == "WARN"})

    def test_candidate_decision_risk_blocks_paper_review_candidate(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "neutral_loss_guard55_min_history244",
                    "decision": "PAPER_REVIEW",
                    "decision_reasons": "no_required_failure_regression",
                    "recommendation": "keep paper-only",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertEqual(check.name, "candidate_decision")
        self.assertIn("PAPER_REVIEW", check.detail)

    def test_candidate_decision_risk_surfaces_pending_oos_marker(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "neutral_loss_guard55_min_history244",
                    "decision": "PAPER_REVIEW",
                    "decision_reasons": "no_required_failure_regression",
                    "post_cutoff_oos_end_date": "PENDING_POST_CUTOFF_OOS",
                    "recommendation": "keep paper-only",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_status=pending", check.detail)

    def test_candidate_decision_risk_explains_auto_required_missing_report(self):
        check = validate_candidate_decision_risk(None, source="", require=True)

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("candidate artifacts detected", check.detail)

    def test_candidate_decision_risk_requires_acceptance_proof(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "no_required_failure_regression",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("promotion_proof_missing", check.detail)

    def test_candidate_decision_risk_requires_post_cutoff_oos_date(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_missing", check.detail)

    def test_candidate_decision_risk_blocks_baseline_oos_start_date(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_start_date": "2026-06-18",
                    "post_cutoff_oos_end_date": "2026-06-19",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_start_not_post_cutoff", check.detail)

    def test_candidate_decision_risk_blocks_oos_start_after_end_date(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_start_date": "2026-06-20",
                    "post_cutoff_oos_end_date": "2026-06-19",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_date_order_invalid", check.detail)

    def test_candidate_decision_risk_requires_post_cutoff_oos_start_date(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_end_date": "2026-06-19",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_start_missing", check.detail)

    def test_candidate_decision_risk_marks_pending_oos_proof(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_end_date": "PENDING_POST_CUTOFF_OOS",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_pending", check.detail)

    def test_candidate_decision_risk_marks_pending_oos_start_alias(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "oos_review_start_date": "PENDING_POST_CUTOFF_OOS",
                    "post_cutoff_oos_end_date": "2026-06-19",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_pending", check.detail)

    def test_candidate_decision_risk_marks_pending_oos_reason_marker(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": (
                        "oos_review_passed;production_readiness_approved;"
                        "post_cutoff_oos_start_date=PENDING_POST_CUTOFF_OOS;"
                        "post_cutoff_oos_end_date=2026-06-19"
                    ),
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_pending", check.detail)

    def test_candidate_decision_risk_marks_pending_oos_reason_marker_with_spaces(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": (
                        "oos_review_passed;production_readiness_approved;"
                        "post_cutoff_oos_start_date = PENDING_POST_CUTOFF_OOS;"
                        "post_cutoff_oos_end_date = 2026-06-19"
                    ),
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_pending", check.detail)

    def test_candidate_decision_risk_does_not_prefix_match_pending_oos_reason_marker(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": (
                        "oos_review_passed;production_readiness_approved;"
                        "post_cutoff_oos_start_date=pending_post_cutoff_oos_done;"
                        "post_cutoff_oos_end_date=2026-06-19"
                    ),
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_start_invalid", check.detail)

    def test_candidate_decision_risk_marks_invalid_oos_reason_date(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": (
                        "oos_review_passed;production_readiness_approved;"
                        "post_cutoff_oos_start_date=not-a-date;"
                        "post_cutoff_oos_end_date=2026-06-19"
                    ),
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_start_invalid", check.detail)

    def test_candidate_decision_risk_accepts_comma_separated_oos_reason_dates(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": (
                        "oos_review_passed;production_readiness_approved;"
                        "post_cutoff_oos_start_date=2026-06-19,"
                        "post_cutoff_oos_end_date=2026-06-19"
                    ),
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "PASS")

    def test_candidate_decision_risk_marks_lowercase_pending_oos_proof(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_end_date": "pending_post_cutoff_oos",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "BLOCK")
        self.assertIn("post_cutoff_oos_pending", check.detail)

    def test_candidate_decision_risk_passes_acceptance_with_proof(self):
        check = validate_candidate_decision_risk(
            [
                {
                    "candidate_label": "manual_accept",
                    "decision": "ACCEPT",
                    "decision_reasons": "oos_review_passed;production_readiness_approved",
                    "post_cutoff_oos_start_date": "2026-06-19",
                    "post_cutoff_oos_end_date": "2026-06-19",
                    "recommendation": "manual accept",
                }
            ],
            source="unit",
            require=True,
        )

        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.status, "PASS")

    def test_candidate_decision_required_for_candidate_reports(self):
        self.assertTrue(
            candidate_decision_required_for_report_paths(
                [
                    "data/reports/monthly_deployment_gate_candidate_proxy_guard.csv",
                    "data/reports/monthly_performance_audit.csv",
                ]
            )
        )

    def test_candidate_decision_not_required_for_canonical_reports(self):
        self.assertFalse(
            candidate_decision_required_for_report_paths(
                [
                    "data/reports/monthly_deployment_gate.csv",
                    "data/reports/monthly_performance_audit.csv",
                ]
            )
        )

    def test_report_freshness_blocks_stale_validation_reports(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "performance.csv"
            report.write_text("name,status,detail\nrequired_scenarios,PASS,ok\n", encoding="utf-8")
            stale_timestamp = datetime(2026, 4, 1, 12, 0).timestamp()
            os.utime(report, (stale_timestamp, stale_timestamp))

            checks = validate_report_freshness(
                {"performance_report": report},
                as_of_date="2026-06-20",
                max_age_days=30,
            )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "performance_report_freshness")
        self.assertIn("age 80d exceeds 30d", checks[0].detail)

    def test_report_freshness_passes_recent_validation_reports(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "deployment.csv"
            report.write_text("deployable,reason\nTrue,passed\n", encoding="utf-8")
            recent_timestamp = datetime(2026, 6, 10, 12, 0).timestamp()
            os.utime(report, (recent_timestamp, recent_timestamp))

            checks = validate_report_freshness(
                {"deployment_gate": report},
                as_of_date="2026-06-20",
                max_age_days=30,
            )

        self.assertEqual(risk_status(checks), "PASS")
        self.assertEqual(checks[0].name, "deployment_gate_freshness")

    def test_load_performance_guard_warn_uses_configured_scale(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "performance.csv"
            report.write_text(
                "name,status,detail\n"
                "required_scenarios,PASS,ok\n"
                "walk_forward_margin,WARN,min_walk_forward_excess_pct=3.2\n",
                encoding="utf-8",
            )

            guard = load_performance_guard(report, warn_scale=0.2, block_scale=0.0)

        self.assertIsNotNone(guard)
        assert guard is not None
        self.assertEqual(guard.status, "WARN")
        self.assertEqual(guard.scale, 0.2)
        self.assertIn("walk_forward_margin", guard.detail)

    def test_compress_decision_to_buyable_targets_drops_unbuyable_high_price_names(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="market_beta_proxy",
            selected_preset="market_beta_proxy",
            target_weights={"HIGH": 0.033, "LOW1": 0.033, "LOW2": 0.033},
            reason="unit-test",
        )

        compressed = compress_decision_to_buyable_targets(
            decision,
            reference_prices={"HIGH": 120_000, "LOW1": 10_000, "LOW2": 20_000},
            portfolio_value=1_000_000,
            max_position_weight=0.15,
            min_target_value=10_000,
        )

        self.assertNotIn("HIGH", compressed.target_weights)
        self.assertAlmostEqual(sum(compressed.target_weights.values()), 0.099)
        self.assertIn("buyable_targets_2of3", compressed.reason)

    def test_market_beta_proxy_buyable_only_drops_unbuyable_proxy_names(self):
        symbol_candles = {
            "HIGH": _daily_candles_with_volume("2026-01-01", 10, close=600_000, volume=10_000),
            "MID1": _daily_candles_with_volume("2026-01-01", 10, close=100_000, volume=9_000),
            "MID2": _daily_candles_with_volume("2026-01-01", 10, close=90_000, volume=8_000),
        }

        decision = decide_monthly_allocation(
            symbol_candles,
            as_of_date="2026-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2026-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                market_beta_breadth_threshold=0.0,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_symbol="ETF",
                market_beta_proxy_size=3,
                market_beta_proxy_buyable_only=True,
                max_position_weight=0.4,
            ),
            portfolio_value=1_000_000,
            reference_prices={"HIGH": 600_009, "MID1": 100_009, "MID2": 90_009},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertNotIn("HIGH", decision.target_weights)
        self.assertIn("MID1", decision.target_weights)
        self.assertIn("MID2", decision.target_weights)
        self.assertIn("buyable_targets_2of3", decision.reason)

    def test_market_beta_proxy_cash_reserve_drops_unbuyable_without_reweighting(self):
        symbol_candles = {
            "HIGH": _daily_candles_with_volume("2026-01-01", 10, close=600_000, volume=10_000),
            "MID1": _daily_candles_with_volume("2026-01-01", 10, close=100_000, volume=9_000),
            "MID2": _daily_candles_with_volume("2026-01-01", 10, close=90_000, volume=8_000),
        }

        decision = decide_monthly_allocation(
            symbol_candles,
            as_of_date="2026-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2026-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                market_beta_breadth_threshold=0.0,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_symbol="ETF",
                market_beta_proxy_size=3,
                market_beta_proxy_unbuyable_cash_reserve=True,
                max_position_weight=0.4,
            ),
            portfolio_value=1_000_000,
            reference_prices={"HIGH": 600_009, "MID1": 100_009, "MID2": 90_009},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertNotIn("HIGH", decision.target_weights)
        self.assertEqual(decision.target_weights, {"MID1": 0.33, "MID2": 0.33})
        self.assertIn("unbuyable_cash_reserve_2of3", decision.reason)

    def test_risk_exit_code_is_nonzero_for_blocked_plan(self):
        self.assertEqual(risk_exit_code("PASS"), 0)
        self.assertEqual(risk_exit_code("WARN"), 0)
        self.assertEqual(risk_exit_code("BLOCK"), 2)

    def test_deployment_gate_rejects_negative_excess_return(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=-1.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": False},
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "negative_excess_return")

    def test_monthly_performance_audit_warns_on_thin_walk_forward_margin(self):
        rows = [
            {
                "name": "full_period",
                "category": "duration",
                "required": True,
                "deployable": True,
                "excess_return_pct": 30.0,
                "max_drawdown_pct": -10.0,
                "trade_count": 10,
            },
            {
                "name": "walk_forward_001",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 3.0,
                "max_drawdown_pct": -8.0,
                "trade_count": 5,
            },
        ]

        checks = build_monthly_performance_audit(rows, min_walk_forward_warn_excess_pct=5.0)

        warning_names = {check["name"] for check in checks if check["status"] == "WARN"}
        self.assertIn("walk_forward_margin", warning_names)

    def test_monthly_performance_audit_warns_when_full_period_dominates_oos(self):
        rows = [
            {
                "name": "full_period",
                "category": "duration",
                "required": True,
                "deployable": True,
                "excess_return_pct": 120.0,
                "max_drawdown_pct": -10.0,
                "trade_count": 10,
            },
            {
                "name": "walk_forward_001",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 3.0,
                "max_drawdown_pct": -8.0,
                "trade_count": 5,
            },
            {
                "name": "walk_forward_002",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 5.0,
                "max_drawdown_pct": -9.0,
                "trade_count": 5,
            },
        ]

        checks = build_monthly_performance_audit(rows, max_full_to_walk_median_excess_ratio=20.0)

        warning_names = {check["name"] for check in checks if check["status"] == "WARN"}
        self.assertIn("return_concentration", warning_names)

    def test_save_monthly_performance_audit_rows(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "audit.csv"
            count = save_monthly_performance_audit_rows(
                [{"name": "walk_forward_margin", "status": "PASS", "detail": "ok"}],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(count, 1)
        self.assertIn("walk_forward_margin", text)

    def test_performance_concentration_warns_when_one_month_dominates(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000_000,
            final_equity=2_040_000,
            total_return_pct=104.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=104.0,
            max_drawdown_pct=0.0,
            trade_count=0,
            decisions=[],
            trades=[],
            dates=[
                "2024-01-31",
                "2024-02-29",
                "2024-03-31",
                "2024-04-30",
                "2024-05-31",
                "2024-06-30",
            ],
            equity_curve=[1_010_000, 1_020_000, 2_000_000, 2_010_000, 2_020_000, 2_040_000],
        )

        row = analyze_monthly_performance_concentration(result)

        self.assertIn(row["concentration_status"], {"WARN", "BLOCK"})
        self.assertGreater(float(row["top_1_month_contribution"]), 0.7)
        self.assertEqual(row["best_month"], "2024-03")
        self.assertIn("top_1_month_contribution", row["concentration_reasons"])

    def test_performance_concentration_passes_when_monthly_returns_are_distributed(self):
        equities = []
        current = 1_000_000.0
        dates = []
        for month in range(1, 9):
            current *= 1.02
            dates.append(f"2024-{month:02d}-28")
            equities.append(current)
        result = MonthlyBacktestResult(
            initial_cash=1_000_000,
            final_equity=equities[-1],
            total_return_pct=17.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=17.0,
            max_drawdown_pct=0.0,
            trade_count=0,
            decisions=[],
            trades=[],
            dates=dates,
            equity_curve=equities,
        )

        row = analyze_monthly_performance_concentration(result)

        self.assertEqual(row["concentration_status"], "PASS")
        self.assertLess(float(row["top_1_month_contribution"]), 0.2)
        self.assertGreater(float(row["positive_month_ratio"]), 0.9)

    def test_performance_concentration_detects_symbol_contribution_concentration(self):
        trades = [
            MonthlyBacktestTrade("2024-01-02", "BIG", "BUY", 100, 100, 0, "test"),
            MonthlyBacktestTrade("2024-06-28", "BIG", "SELL", 200, 100, 0, "test"),
        ]
        for index in range(9):
            symbol = f"S{index}"
            trades.extend(
                [
                    MonthlyBacktestTrade("2024-01-02", symbol, "BUY", 100, 10, 0, "test"),
                    MonthlyBacktestTrade("2024-06-28", symbol, "SELL", 105, 10, 0, "test"),
                ]
            )
        result = MonthlyBacktestResult(
            initial_cash=1_000_000,
            final_equity=1_010_450,
            total_return_pct=1.045,
            buy_hold_return_pct=0.0,
            excess_return_pct=1.045,
            max_drawdown_pct=0.0,
            trade_count=len(trades),
            decisions=[],
            trades=trades,
            dates=["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30", "2024-05-31", "2024-06-30"],
            equity_curve=[1_001_000, 1_002_000, 1_003_000, 1_004_000, 1_005_000, 1_010_450],
        )

        row = analyze_monthly_performance_concentration(result)

        self.assertIn(row["concentration_status"], {"WARN", "BLOCK"})
        self.assertGreater(float(row["top_5_symbol_contribution"]), 0.9)
        self.assertIn("top_5_symbol_contribution", row["concentration_reasons"])

    def test_save_monthly_performance_concentration_writes_report(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "concentration.csv"
            count = save_monthly_performance_concentration(
                [
                    {
                        "source": "unit",
                        "start": "2024-01-01",
                        "end": "2024-06-30",
                        "top_1_month_contribution": 0.1,
                        "top_3_month_contribution": 0.3,
                        "top_5_symbol_contribution": 0.4,
                        "best_month": "2024-01",
                        "worst_month": "2024-02",
                        "positive_month_ratio": 0.8,
                        "rolling_3m_return_min": 0.02,
                        "rolling_6m_return_min": 0.04,
                        "max_recovery_months_if_possible": 0,
                        "concentration_status": "PASS",
                        "concentration_reasons": "",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(count, 1)
        self.assertIn("top_1_month_contribution", text)

    def test_save_monthly_validation_rows_preserves_source_marker(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "validation.csv"
            save_monthly_validation_rows(
                [
                    {
                        "name": "full_period",
                        "category": "duration",
                        "required": True,
                        "deployable": True,
                        "reason": "passed",
                        "train_candidate_scores": "balanced:excess=10,drawdown=-5,trades=3,score=5",
                        "source": "monthly-validate;data_quality_exclusions=auto:data/reports/data_quality_excluded_symbols.csv",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn("source", text.splitlines()[0])
        self.assertIn("train_candidate_scores", text.splitlines()[0])
        self.assertIn("balanced:excess=10", text)
        self.assertIn("data_quality_exclusions=auto:", text)

    def test_analyze_monthly_validation_failures_adds_actions_and_parameter_hints(self):
        rows = [
            {
                "name": "stress_exclude_500pct_winners",
                "category": "stress",
                "required": True,
                "deployable": False,
                "reason": "max_drawdown_breach",
                "max_drawdown_pct": "-28.0",
                "excess_return_pct": "12.0",
                "trade_count": "335",
            },
            {
                "name": "walk_forward_005",
                "category": "walk_forward",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
                "max_drawdown_pct": "-20.5",
                "excess_return_pct": "-5.5",
                "trade_count": "42",
            },
            {
                "name": "walk_forward_003",
                "category": "walk_forward",
                "required": True,
                "deployable": False,
                "reason": "train_window_rejected",
                "train_excess_return_pct": "-1.3",
                "excess_return_pct": "8.7",
                "trade_count": "47",
            },
        ]

        diagnostics = analyze_monthly_validation_failures(rows)
        by_name = {row["name"]: row for row in diagnostics}

        self.assertEqual(by_name["stress_exclude_500pct_winners"]["failed_metric"], "max_drawdown_pct")
        self.assertEqual(by_name["stress_exclude_500pct_winners"]["suggested_action"], "REDUCE_DRAWDOWN")
        self.assertIn("max_position_weight", by_name["stress_exclude_500pct_winners"]["parameter_hints"])
        self.assertEqual(by_name["walk_forward_005"]["suggested_action"], "IMPROVE_WEAK_WINDOW_DEFENSE")
        self.assertIn("cash_buffer_weight", by_name["walk_forward_005"]["parameter_hints"])
        self.assertEqual(by_name["walk_forward_003"]["suggested_action"], "KEEP_TRAIN_WINDOW_REJECTED")

    def test_save_monthly_validation_failures_writes_actionable_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "validation_failures.csv"
            saved = save_monthly_validation_failures(
                [
                    {
                        "name": "walk_forward_005",
                        "category": "walk_forward",
                        "reason": "negative_excess_return",
                        "severity": "BLOCK",
                        "failed_metric": "excess_return_pct",
                        "metric_value": "-5.5",
                        "threshold": "0.0",
                        "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                        "parameter_hints": "increase cash_buffer_weight",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("suggested_action", text.splitlines()[0])
        self.assertIn("IMPROVE_WEAK_WINDOW_DEFENSE", text)

    def test_analyze_monthly_validation_remediation_prioritizes_actions(self):
        failures = [
            {
                "name": "regime_sideways",
                "category": "regime",
                "reason": "negative_excess_return",
                "severity": "BLOCK",
                "failed_metric": "excess_return_pct",
                "metric_value": "-7.1648",
                "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                "parameter_hints": "increase cash_buffer_weight; tighten min_train_positive_ratio",
                "start": "2024-10-14",
                "end": "2025-04-17",
            },
            {
                "name": "walk_forward_005",
                "category": "walk_forward",
                "reason": "negative_excess_return",
                "severity": "BLOCK",
                "failed_metric": "excess_return_pct",
                "metric_value": "-5.5812",
                "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                "parameter_hints": "increase cash_buffer_weight; tighten min_train_positive_ratio",
                "start": "2026-01-28",
                "end": "2026-04-30",
            },
            {
                "name": "stress_exclude_500pct_winners",
                "category": "stress",
                "reason": "max_drawdown_breach",
                "severity": "BLOCK",
                "failed_metric": "max_drawdown_pct",
                "metric_value": "-28.0835",
                "suggested_action": "REDUCE_DRAWDOWN",
                "parameter_hints": "lower max_position_weight; increase cash_buffer_weight",
                "start": "2024-01-02",
                "end": "2026-06-18",
            },
        ]

        rows = analyze_monthly_validation_remediation(failures)

        self.assertEqual(rows[0]["suggested_action"], "IMPROVE_WEAK_WINDOW_DEFENSE")
        self.assertEqual(rows[0]["failure_count"], 2)
        self.assertEqual(rows[0]["worst_metric_value"], "-7.1648")
        self.assertEqual(rows[0]["priority"], "P1")
        self.assertIn("cash_buffer_weight", rows[0]["parameter_hints"])
        self.assertIn("regime_sideways", rows[0]["affected_scenarios"])
        self.assertEqual(rows[1]["suggested_action"], "REDUCE_DRAWDOWN")

    def test_save_monthly_validation_remediation_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "remediation.csv"
            saved = save_monthly_validation_remediation(
                [
                    {
                        "priority": "P1",
                        "suggested_action": "REDUCE_DRAWDOWN",
                        "failure_count": 1,
                        "blocked_count": 1,
                        "affected_categories": "stress",
                        "affected_scenarios": "stress_exclude_500pct_winners",
                        "failed_metrics": "max_drawdown_pct",
                        "worst_metric_value": "-28.0835",
                        "parameter_hints": "lower max_position_weight",
                        "next_experiment": "Test lower max_position_weight.",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("next_experiment", text.splitlines()[0])
        self.assertIn("REDUCE_DRAWDOWN", text)

    def test_build_monthly_validation_sweep_plan_creates_weak_window_candidates(self):
        remediation_rows = [
            {
                "priority": "P1",
                "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                "failure_count": 3,
                "blocked_count": 3,
                "affected_scenarios": "regime_sideways; walk_forward_001; walk_forward_005",
                "worst_metric_value": "-7.1648",
            },
            {
                "priority": "P1",
                "suggested_action": "REDUCE_DRAWDOWN",
                "failure_count": 1,
                "blocked_count": 1,
                "affected_scenarios": "stress_exclude_500pct_winners",
                "worst_metric_value": "-28.0835",
            },
        ]

        rows = build_monthly_validation_sweep_plan(
            remediation_rows,
            base_config=MonthlyRebalanceConfig(
                cash_buffer_weight=0.01,
                min_train_positive_ratio=0.5,
                candidate_pool_size=7,
                max_position_weight=0.15,
                drawdown_guard_scale=0.75,
                market_volatility_min_scale=0.25,
            ),
        )

        by_id = {row["experiment_id"]: row for row in rows}
        self.assertIn("weak_defense_cash_05", by_id)
        self.assertEqual(by_id["weak_defense_cash_05"]["cash_buffer_weight"], "0.05")
        self.assertEqual(by_id["weak_defense_cash_05"]["candidate_pool_size"], "5")
        self.assertIn("regime_sideways", by_id["weak_defense_cash_05"]["target_scenarios"])
        self.assertIn("market_beta_proxy_cap_75", by_id)
        self.assertEqual(by_id["market_beta_proxy_cap_75"]["market_beta_proxy_max_exposure"], "0.75")
        self.assertIn("neutral_breadth_proxy_cap_50", by_id)
        self.assertEqual(
            by_id["neutral_breadth_proxy_cap_50"]["market_beta_proxy_neutral_breadth_max_exposure"],
            "0.5",
        )
        self.assertIn("neutral_proxy_deep_guard_35", by_id)
        neutral_guard = by_id["neutral_proxy_deep_guard_35"]
        self.assertEqual(neutral_guard["market_beta_proxy_neutral_breadth_max_exposure"], "0.5")
        self.assertEqual(neutral_guard["drawdown_guard_deep_trigger_pct"], "-20")
        self.assertEqual(neutral_guard["drawdown_guard_deep_scale"], "0.35")
        self.assertIn("drawdown_guard_stronger", by_id)
        self.assertEqual(by_id["drawdown_guard_stronger"]["max_position_weight"], "0.1")
        self.assertEqual(by_id["drawdown_guard_stronger"]["market_volatility_min_scale"], "0.5")
        self.assertIn("drawdown_guard_very_strict", by_id)
        self.assertEqual(by_id["drawdown_guard_very_strict"]["max_position_weight"], "0.08")
        self.assertEqual(by_id["drawdown_guard_very_strict"]["drawdown_guard_scale"], "0.35")
        self.assertEqual(by_id["drawdown_guard_very_strict"]["market_volatility_min_scale"], "0.65")
        self.assertIn("drawdown_cash_buffer_05", by_id)
        self.assertEqual(by_id["drawdown_cash_buffer_05"]["cash_buffer_weight"], "0.05")
        self.assertEqual(by_id["drawdown_cash_buffer_05"]["max_position_weight"], "0.1")
        self.assertIn("position_stop_12", by_id)
        self.assertEqual(by_id["position_stop_12"]["position_trailing_stop_pct"], "-12")
        self.assertIn("guarded_loss_position_stop_12", by_id)
        guarded_stop = by_id["guarded_loss_position_stop_12"]
        self.assertEqual(guarded_stop["position_trailing_stop_pct"], "-12")
        self.assertEqual(
            guarded_stop["position_trailing_stop_reason_contains"],
            "proxy_neutral_loss_guard_capped",
        )
        self.assertIn("weak_cash_10_position_stop_12", by_id)
        combo = by_id["weak_cash_10_position_stop_12"]
        self.assertEqual(combo["cash_buffer_weight"], "0.1")
        self.assertEqual(combo["min_train_positive_ratio"], "0.6")
        self.assertEqual(combo["candidate_pool_size"], "5")
        self.assertEqual(combo["position_trailing_stop_pct"], "-12")
        self.assertIn("regime_sideways", combo["target_scenarios"])
        self.assertIn("stress_exclude_500pct_winners", combo["target_scenarios"])

    def test_filter_monthly_validation_sweep_plan_filters_in_plan_order_and_limits(self):
        rows = [
            {"experiment_id": "weak_defense_cash_05"},
            {"experiment_id": "position_stop_12"},
            {"experiment_id": "weak_cash_10_position_stop_12"},
        ]

        filtered = filter_monthly_validation_sweep_plan(
            rows,
            experiment_ids=["weak_cash_10_position_stop_12", "weak_defense_cash_05"],
            limit=1,
        )

        self.assertEqual([row["experiment_id"] for row in filtered], ["weak_defense_cash_05"])

    def test_filter_monthly_validation_sweep_plan_rejects_negative_limit(self):
        with self.assertRaises(ValueError):
            filter_monthly_validation_sweep_plan(
                [{"experiment_id": "weak_defense_cash_05"}],
                limit=-1,
            )

    def test_save_monthly_validation_sweep_plan_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sweep_plan.csv"
            saved = save_monthly_validation_sweep_plan(
                [
                    {
                        "priority": "P1",
                        "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                        "experiment_id": "weak_defense_cash_05",
                        "target_scenarios": "regime_sideways",
                        "cash_buffer_weight": "0.05",
                        "min_train_positive_ratio": "0.55",
                        "candidate_pool_size": "5",
                        "max_position_weight": "",
                        "drawdown_guard_scale": "",
                        "market_volatility_min_scale": "",
                        "expected_effect": "Reduce weak-window exposure.",
                        "risk_note": "Re-run validation before adopting.",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("experiment_id", text.splitlines()[0])
        self.assertIn("weak_defense_cash_05", text)

    def test_run_monthly_validation_sweep_results_marks_improvement(self):
        cases = [
            MonthlyValidationCase(
                name="regime_sideways",
                category="regime",
                start="2024-01-01",
                end="2024-03-31",
            )
        ]
        baseline_rows = [
            {
                "name": "regime_sideways",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
            }
        ]
        plan_rows = [
            {
                "priority": "P1",
                "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                "experiment_id": "weak_defense_cash_05",
                "target_scenarios": "regime_sideways",
                "cash_buffer_weight": "0.05",
                "min_train_positive_ratio": "0.55",
                "candidate_pool_size": "5",
                "risk_note": "Re-run validation before adopting.",
            }
        ]
        calls = []

        def runner(symbol_candles, *, start, end, config, **kwargs):
            calls.append(config)
            return _monthly_result(
                excess_return_pct=1.2 if config.cash_buffer_weight == 0.05 else -3.0,
                max_drawdown_pct=-8.0,
            )

        rows = run_monthly_validation_sweep_results(
            {"005930": [_candle("2024-01-02", 100), _candle("2024-03-29", 110)]},
            cases=cases,
            sweep_plan_rows=plan_rows,
            base_config=MonthlyRebalanceConfig(cash_buffer_weight=0.01, candidate_pool_size=7),
            baseline_rows=baseline_rows,
            backtest_runner=runner,
        )

        self.assertEqual(rows[0]["status"], "IMPROVED")
        self.assertEqual(rows[0]["failed_required"], 0)
        self.assertEqual(rows[0]["baseline_failed_required"], 1)
        self.assertEqual(rows[0]["failed_delta"], -1)
        self.assertEqual(rows[0]["validation_scope"], "TARGET_ONLY")
        self.assertEqual(rows[0]["adoption_status"], "FULL_VALIDATION_REQUIRED")
        self.assertIn("monthly-validate", rows[0]["adoption_requirements"])
        self.assertIn("--cash-buffer-weight 0.05", rows[0]["candidate_validation_args"])
        self.assertIn("--min-train-positive-ratio 0.55", rows[0]["candidate_validation_args"])
        self.assertIn("--candidate-pool-size 5", rows[0]["candidate_validation_args"])
        self.assertEqual(calls[0].cash_buffer_weight, 0.05)
        self.assertEqual(calls[0].candidate_pool_size, 5)

    def test_run_monthly_validation_sweep_results_emits_deep_guard_args(self):
        cases = [
            MonthlyValidationCase(
                name="regime_sideways",
                category="regime",
                start="2024-01-01",
                end="2024-03-31",
            )
        ]
        baseline_rows = [
            {
                "name": "regime_sideways",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
            }
        ]
        plan_rows = [
            {
                "priority": "P1",
                "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                "experiment_id": "neutral_proxy_deep_guard_35",
                "target_scenarios": "regime_sideways",
                "market_beta_proxy_neutral_breadth_max_exposure": "0.5",
                "drawdown_guard_deep_trigger_pct": "-20",
                "drawdown_guard_deep_scale": "0.35",
                "risk_note": "Re-run validation before adopting.",
            }
        ]
        calls = []

        def runner(symbol_candles, *, start, end, config, **kwargs):
            calls.append(config)
            return _monthly_result(excess_return_pct=1.2, max_drawdown_pct=-8.0)

        rows = run_monthly_validation_sweep_results(
            {"005930": [_candle("2024-01-02", 100), _candle("2024-03-29", 110)]},
            cases=cases,
            sweep_plan_rows=plan_rows,
            base_config=MonthlyRebalanceConfig(),
            baseline_rows=baseline_rows,
            backtest_runner=runner,
        )

        args = rows[0]["candidate_validation_args"]
        self.assertIn("--market-beta-proxy-neutral-breadth-max-exposure 0.5", args)
        self.assertIn("--drawdown-guard-deep-trigger-pct -20", args)
        self.assertIn("--drawdown-guard-deep-scale 0.35", args)
        self.assertEqual(calls[0].market_beta_proxy_neutral_breadth_max_exposure, 0.5)
        self.assertEqual(calls[0].drawdown_guard_deep_trigger_pct, -20.0)
        self.assertEqual(calls[0].drawdown_guard_deep_scale, 0.35)

    def test_save_monthly_validation_sweep_results_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sweep_results.csv"
            saved = save_monthly_validation_sweep_results(
                [
                    {
                        "experiment_id": "weak_defense_cash_05",
                        "suggested_action": "IMPROVE_WEAK_WINDOW_DEFENSE",
                        "status": "IMPROVED",
                        "target_scenarios": "regime_sideways",
                        "scenario_count": 1,
                        "failed_required": 0,
                        "baseline_failed_required": 1,
                        "failed_delta": -1,
                        "min_excess_return_pct": "1.2",
                        "worst_drawdown_pct": "-8",
                        "trade_count": 1,
                        "config_changes": "cash_buffer_weight=0.05",
                        "result_summary": "failed_required 1 -> 0",
                        "risk_note": "Re-run validation before adopting.",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("failed_delta", text.splitlines()[0])
        self.assertIn("candidate_validation_args", text.splitlines()[0])
        self.assertIn("--cash-buffer-weight 0.05", text)
        self.assertIn("adoption_status", text.splitlines()[0])
        self.assertIn("IMPROVED", text)
        self.assertIn("FULL_VALIDATION_REQUIRED", text)

    def test_save_monthly_validation_sweep_results_marks_unchanged_no_config(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sweep_results.csv"
            saved = save_monthly_validation_sweep_results(
                [
                    {
                        "experiment_id": "train_gate_keep_blocked",
                        "suggested_action": "KEEP_TRAIN_WINDOW_REJECTED",
                        "status": "UNCHANGED",
                        "target_scenarios": "walk_forward_003",
                        "scenario_count": 1,
                        "failed_required": 1,
                        "baseline_failed_required": 1,
                        "failed_delta": 0,
                        "config_changes": "",
                        "result_summary": "train gate remained blocked",
                        "risk_note": "No candidate config change; preserve train-gate discipline.",
                    }
                ],
                output,
            )
            with output.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(saved, 1)
        self.assertEqual(rows[0]["candidate_validation_args"], "NO_CONFIG_CHANGE")
        self.assertEqual(rows[0]["adoption_status"], "PAPER_DIAGNOSTIC_ONLY")

    def test_build_monthly_validation_candidate_followup_rows_prioritizes_full_validation_candidates(self):
        rows = build_monthly_validation_candidate_followup_rows(
            [
                {
                    "experiment_id": "unchanged",
                    "status": "UNCHANGED",
                    "adoption_status": "PAPER_DIAGNOSTIC_ONLY",
                    "failed_delta": "0",
                    "candidate_validation_args": "--cash-buffer-weight 0.05",
                },
                {
                    "experiment_id": "weak_cash_10_position_stop_12",
                    "status": "IMPROVED",
                    "adoption_status": "FULL_VALIDATION_REQUIRED",
                    "failed_delta": "-2",
                    "candidate_validation_args": "--cash-buffer-weight 0.1 --position-trailing-stop-pct -12",
                    "risk_note": "Plan only.",
                },
            ],
            data_dir="data/krx_expanded",
            start="2024-01-01",
            end="2026-06-18",
            baseline_scenarios="data/reports/monthly_validation_scenarios_pit_universe.csv",
            reports_dir="data/reports",
            point_in_time_universe="data/krx_metadata/krx_universe_monthly.csv",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["priority_rank"], 1)
        self.assertEqual(row["experiment_id"], "weak_cash_10_position_stop_12")
        self.assertIn("monthly-validate", row["validation_command"])
        self.assertIn("--cash-buffer-weight 0.1", row["validation_command"])
        self.assertIn("--position-trailing-stop-pct -12", row["validation_command"])
        self.assertIn("monthly_validation_candidate_weak_cash_10_position_stop_12.csv", row["candidate_scenario_output"])
        isolated_output_flags = [
            "--data-quality-output",
            "--coverage-output",
            "--performance-output",
            "--concentration-output",
            "--failure-output",
            "--remediation-output",
            "--sweep-plan-output",
            "--universe-filter-report",
        ]
        for flag in isolated_output_flags:
            self.assertIn(flag, row["validation_command"])
            self.assertIn("weak_cash_10_position_stop_12", row["validation_command"])
        self.assertIn("monthly_validation_failures_candidate_weak_cash_10_position_stop_12.csv", row["validation_command"])
        self.assertIn("monthly_performance_audit_candidate_weak_cash_10_position_stop_12.csv", row["validation_command"])
        self.assertIn("monthly-compare-validation", row["comparison_command"])
        self.assertIn("--candidate-label weak_cash_10_position_stop_12", row["comparison_command"])

    def test_save_monthly_validation_candidate_followup_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "followup.csv"
            saved = save_monthly_validation_candidate_followup_rows(
                [
                    {
                        "priority_rank": 1,
                        "experiment_id": "weak_cash_10_position_stop_12",
                        "status": "IMPROVED",
                        "failed_delta": "-2",
                        "candidate_validation_args": "--cash-buffer-weight 0.1",
                        "validation_command": "python -m backtester monthly-validate --cash-buffer-weight 0.1",
                        "comparison_command": "python -m backtester monthly-compare-validation",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("validation_command", text.splitlines()[0])
        self.assertIn("weak_cash_10_position_stop_12", text)

    def test_analyze_monthly_validation_failure_patterns_flags_persistent_and_regression(self):
        baseline_rows = [
            {"name": "stress", "required": True, "deployable": False, "reason": "max_drawdown_breach"},
            {"name": "walk_001", "required": True, "deployable": False, "reason": "negative_excess_return"},
            {"name": "walk_002", "required": True, "deployable": True, "reason": "passed"},
        ]
        delta_rows = [
            {
                "name": "stress",
                "candidate_label": "cash_10",
                "classification": "RESOLVED",
                "diagnostic": "candidate_fixed_required_failure",
            },
            {
                "name": "walk_001",
                "candidate_label": "cash_10",
                "classification": "UNCHANGED_FAILURE",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "walk_002",
                "candidate_label": "cash_10",
                "classification": "NEW_FAILURE",
                "diagnostic": "selection_or_exposure_drag",
            },
            {
                "name": "stress",
                "candidate_label": "stop_12",
                "classification": "UNCHANGED_FAILURE",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "walk_001",
                "candidate_label": "stop_12",
                "classification": "UNCHANGED_FAILURE",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "walk_002",
                "candidate_label": "stop_12",
                "classification": "NEW_FAILURE",
                "diagnostic": "selection_or_exposure_drag",
            },
        ]

        rows = analyze_monthly_validation_failure_patterns(baseline_rows, delta_rows)
        by_name = {row["scenario"]: row for row in rows}

        self.assertEqual(by_name["walk_001"]["pattern_status"], "PERSISTENT_BLOCK")
        self.assertEqual(by_name["walk_001"]["failed_candidate_count"], 2)
        self.assertEqual(by_name["walk_001"]["unchanged_failure_candidate_count"], 2)
        self.assertIn("same_failure_persists", by_name["walk_001"]["dominant_diagnostic"])
        self.assertEqual(by_name["walk_001"]["suggested_action"], "REVIEW_PERSISTENT_FAILURE")
        self.assertEqual(by_name["walk_002"]["pattern_status"], "REGRESSION_RISK")
        self.assertEqual(by_name["walk_002"]["new_failure_candidate_count"], 2)
        self.assertEqual(by_name["walk_002"]["suggested_action"], "AVOID_REGRESSION_CONFIGS")

    def test_save_monthly_validation_failure_patterns_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "failure_patterns.csv"
            saved = save_monthly_validation_failure_patterns(
                [
                    {
                        "scenario": "walk_001",
                        "baseline_failed": True,
                        "failed_candidate_count": 2,
                        "new_failure_candidate_count": 0,
                        "resolved_candidate_count": 0,
                        "unchanged_failure_candidate_count": 2,
                        "dominant_diagnostic": "same_failure_persists",
                        "pattern_status": "PERSISTENT_BLOCK",
                        "suggested_action": "REVIEW_PERSISTENT_FAILURE",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("pattern_status", text.splitlines()[0])
        self.assertIn("walk_001", text)
        self.assertIn("PERSISTENT_BLOCK", text)

    def test_analyze_monthly_validation_failure_drilldown_summarizes_root_cause_and_gaps(self):
        baseline_rows = [
            {
                "name": "regime_sideways",
                "category": "regime",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
                "train_start": "2024-01-01",
                "train_end": "2024-12-31",
                "selected_preset": "balanced",
                "train_excess_return_pct": "3.5",
                "start": "2025-01-01",
                "end": "2025-06-30",
                "excess_return_pct": "-7.1",
                "max_drawdown_pct": "-18.2",
                "trade_count": "42",
            },
            {
                "name": "walk_forward_003",
                "category": "walk_forward",
                "required": True,
                "deployable": False,
                "reason": "train_window_rejected",
                "train_start": "2024-01-01",
                "train_end": "2024-06-30",
                "selected_preset": "",
                "train_excess_return_pct": "-2.0",
                "start": "2024-07-01",
                "end": "2024-12-31",
                "excess_return_pct": "",
                "max_drawdown_pct": "",
                "trade_count": "0",
            },
            {
                "name": "regime_improved_but_failed",
                "category": "regime",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
                "train_start": "2024-01-01",
                "train_end": "2024-12-31",
                "selected_preset": "balanced",
                "train_excess_return_pct": "4.0",
                "start": "2025-01-01",
                "end": "2025-06-30",
                "excess_return_pct": "-2.0",
                "max_drawdown_pct": "-10.0",
                "trade_count": "20",
            },
        ]
        pattern_rows = [
            {
                "scenario": "regime_sideways",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "failed_candidate_count": "3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
            {
                "scenario": "walk_forward_003",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "failed_candidate_count": "3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
            {
                "scenario": "regime_improved_but_failed",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "failed_candidate_count": "3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
        ]
        delta_rows = [
            {
                "name": "regime_sideways",
                "classification": "UNCHANGED_FAILURE",
                "candidate_label": "cash_10",
                "excess_return_delta": "-2.0",
                "max_drawdown_delta": "1.0",
                "trade_count_delta": "-4",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "regime_sideways",
                "classification": "UNCHANGED_FAILURE",
                "candidate_label": "stop_12",
                "excess_return_delta": "-4.0",
                "max_drawdown_delta": "2.0",
                "trade_count_delta": "8",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "regime_improved_but_failed",
                "classification": "UNCHANGED_FAILURE",
                "candidate_label": "cash_10",
                "excess_return_delta": "1.0",
                "max_drawdown_delta": "1.0",
                "trade_count_delta": "-2",
                "diagnostic": "same_failure_persists",
            },
            {
                "name": "regime_improved_but_failed",
                "classification": "UNCHANGED_FAILURE",
                "candidate_label": "stop_12",
                "excess_return_delta": "3.0",
                "max_drawdown_delta": "1.0",
                "trade_count_delta": "2",
                "diagnostic": "same_failure_persists",
            },
        ]

        rows = analyze_monthly_validation_failure_drilldown(baseline_rows, pattern_rows, delta_rows)
        by_name = {row["scenario"]: row for row in rows}

        sideways = by_name["regime_sideways"]
        self.assertEqual(sideways["likely_root_cause"], "weak_window_return_drag")
        self.assertEqual(sideways["candidate_count"], 2)
        self.assertEqual(sideways["candidate_excess_delta_median"], "-3")
        self.assertIn("selected_symbols", sideways["evidence_gaps"])
        self.assertIn("scenario attribution", sideways["next_action"])
        walk = by_name["walk_forward_003"]
        self.assertEqual(walk["likely_root_cause"], "train_window_selection")
        self.assertIn("training window", walk["next_action"])
        improved = by_name["regime_improved_but_failed"]
        self.assertEqual(improved["candidate_excess_delta_median"], "2")
        self.assertEqual(improved["likely_root_cause"], "insufficient_recovery")

    def test_analyze_monthly_validation_failure_drilldown_marks_non_walk_train_metadata(self):
        baseline_rows = [
            {
                "name": "regime_sideways",
                "category": "regime",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
                "start": "2025-01-01",
                "end": "2025-04-17",
                "excess_return_pct": "-7.1",
                "max_drawdown_pct": "-23.9",
                "trade_count": "42",
            }
        ]
        pattern_rows = [
            {
                "scenario": "regime_sideways",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "failed_candidate_count": "3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            }
        ]

        rows = analyze_monthly_validation_failure_drilldown(baseline_rows, pattern_rows, [])

        row = rows[0]
        for field in (
            "train_start",
            "train_end",
            "selected_preset",
            "train_excess_return_pct",
            "train_candidate_scores",
            "train_candidate_decision_profiles",
            "train_candidate_direct_scores",
            "train_direct_diagnostics",
        ):
            self.assertEqual(row[field], "NOT_APPLICABLE_NON_WALK_FORWARD")

    def test_analyze_monthly_validation_failure_drilldown_uses_attribution_evidence(self):
        baseline_rows = [
            {
                "name": "regime_sideways",
                "category": "regime",
                "required": True,
                "deployable": False,
                "reason": "negative_excess_return",
                "start": "2025-01-01",
                "end": "2025-06-30",
                "excess_return_pct": "-7.1",
                "max_drawdown_pct": "-18.2",
                "trade_count": "42",
            },
        ]
        pattern_rows = [
            {
                "scenario": "regime_sideways",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "failed_candidate_count": "3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
        ]
        delta_rows = [
            {
                "name": "regime_sideways",
                "classification": "UNCHANGED_FAILURE",
                "candidate_label": "cash_10",
                "excess_return_delta": "1.0",
                "max_drawdown_delta": "1.0",
                "trade_count_delta": "-4",
                "diagnostic": "same_failure_persists",
            },
        ]
        decision_rows = [
            {
                "scenario": "regime_sideways",
                "selected_symbols": "005490;051910",
                "target_exposure": "0.99",
                "cash_weight": "0.01",
            },
        ]
        symbol_rows = [
            {
                "scenario": "regime_sideways",
                "symbol": "005490",
                "realized_pnl": "-218620",
            },
        ]

        rows = analyze_monthly_validation_failure_drilldown(
            baseline_rows,
            pattern_rows,
            delta_rows,
            decision_attribution_rows=decision_rows,
            symbol_attribution_rows=symbol_rows,
        )

        self.assertEqual(rows[0]["scenario"], "regime_sideways")
        self.assertEqual(rows[0]["likely_root_cause"], "insufficient_recovery")
        self.assertEqual(rows[0]["evidence_gaps"], "")
        self.assertIn("attribution evidence", rows[0]["next_action"])

    def test_analyze_monthly_validation_failure_drilldown_uses_train_candidate_scores(self):
        baseline_rows = [
            {
                "name": "walk_forward_003",
                "category": "walk_forward",
                "required": True,
                "deployable": False,
                "reason": "train_window_rejected",
                "train_start": "2024-01-01",
                "train_end": "2024-06-30",
                "selected_preset": "balanced",
                "train_excess_return_pct": "-1.3",
                "train_candidate_scores": "balanced:excess=-1.3,drawdown=-5,trades=4,score=-6.3",
                "start": "2024-07-01",
                "end": "2024-12-31",
            },
        ]
        pattern_rows = [
            {
                "scenario": "walk_forward_003",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
        ]

        decision_rows = [
            {
                "scenario": "walk_forward_003",
                "selected_symbols": "005930;000660",
                "target_exposure": "0.99",
                "cash_weight": "0.01",
            }
        ]

        rows = analyze_monthly_validation_failure_drilldown(
            baseline_rows,
            pattern_rows,
            [],
            decision_attribution_rows=decision_rows,
        )

        self.assertEqual(rows[0]["likely_root_cause"], "train_window_selection")
        self.assertEqual(rows[0]["evidence_gaps"], "")

    def test_analyze_monthly_validation_failure_drilldown_flags_direct_alpha_ineligible(self):
        baseline_rows = [
            {
                "name": "walk_forward_003",
                "category": "walk_forward",
                "required": True,
                "deployable": False,
                "reason": "train_window_rejected",
                "train_start": "2024-01-01",
                "train_end": "2024-06-30",
                "selected_preset": "balanced",
                "train_excess_return_pct": "-1.3",
                "train_candidate_scores": "balanced:excess=-1.3,drawdown=-5,trades=4,score=-6.3",
                "train_candidate_direct_scores": (
                    "balanced:excess=-4,drawdown=-8,trades=3,score=-12; "
                    "aggressive:excess=-2,drawdown=-9,trades=2,score=-11"
                ),
                "train_direct_diagnostics": (
                    "period_days=182; market_regime=weak; universe_symbols=125; "
                    "liquid_symbols=80; pit_filter_removed=30"
                ),
                "start": "2024-07-01",
                "end": "2024-12-31",
            },
        ]
        pattern_rows = [
            {
                "scenario": "walk_forward_003",
                "pattern_status": "PERSISTENT_BLOCK",
                "dominant_diagnostic": "same_failure_persists=3",
                "suggested_action": "REVIEW_PERSISTENT_FAILURE",
            },
        ]
        decision_rows = [
            {
                "scenario": "walk_forward_003",
                "selected_symbols": "005930;000660",
                "target_exposure": "0.99",
                "cash_weight": "0.01",
            }
        ]

        rows = analyze_monthly_validation_failure_drilldown(
            baseline_rows,
            pattern_rows,
            [],
            decision_attribution_rows=decision_rows,
        )

        self.assertEqual(rows[0]["likely_root_cause"], "direct_alpha_ineligible")
        self.assertEqual(rows[0]["evidence_gaps"], "")
        self.assertIn("market_regime=weak", rows[0]["train_direct_diagnostics"])
        self.assertIn("pit_filter_removed=30", rows[0]["train_direct_diagnostics"])
        self.assertIn("direct alpha train candidates", rows[0]["next_action"])

    def test_save_monthly_validation_failure_drilldown_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "drilldown.csv"
            saved = save_monthly_validation_failure_drilldown(
                [
                    {
                        "scenario": "regime_sideways",
                        "pattern_status": "PERSISTENT_BLOCK",
                        "likely_root_cause": "weak_window_return_drag",
                        "train_direct_diagnostics": "market_regime=weak",
                        "evidence_gaps": "selected_symbols; exposure",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("likely_root_cause", text.splitlines()[0])
        self.assertIn("train_direct_diagnostics", text.splitlines()[0])
        self.assertIn("regime_sideways", text)
        self.assertIn("weak_window_return_drag", text)

    def test_compare_monthly_validation_reports_detects_shifted_failures(self):
        baseline_rows = [
            {"name": "stress", "required": True, "deployable": False, "reason": "max_drawdown_breach", "excess_return_pct": "5", "max_drawdown_pct": "-28"},
            {"name": "walk_001", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-1", "max_drawdown_pct": "-25"},
            {"name": "walk_002", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "1", "max_drawdown_pct": "-5"},
        ]
        candidate_rows = [
            {"name": "stress", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "6", "max_drawdown_pct": "-24"},
            {"name": "walk_001", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-2", "max_drawdown_pct": "-23"},
            {"name": "walk_002", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-0.2", "max_drawdown_pct": "-4"},
        ]

        comparison = compare_monthly_validation_reports(
            baseline_rows,
            candidate_rows,
            baseline_label="baseline",
            candidate_label="weak_defense_cash_10",
        )

        self.assertEqual(comparison["status"], "REJECT")
        self.assertEqual(comparison["baseline_failed_required"], 2)
        self.assertEqual(comparison["candidate_failed_required"], 2)
        self.assertEqual(comparison["failed_delta"], 0)
        self.assertEqual(comparison["resolved_failures"], "stress")
        self.assertEqual(comparison["new_failures"], "walk_002")
        self.assertIn("new failures", comparison["summary"])

    def test_compare_monthly_validation_scenario_deltas_classifies_each_scenario(self):
        baseline_rows = [
            {"name": "stress", "required": True, "deployable": False, "reason": "max_drawdown_breach", "excess_return_pct": "5", "max_drawdown_pct": "-28", "trade_count": "10"},
            {"name": "walk_001", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-1", "max_drawdown_pct": "-25", "trade_count": "8"},
            {"name": "walk_002", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "1", "max_drawdown_pct": "-5", "trade_count": "4"},
        ]
        candidate_rows = [
            {"name": "stress", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "6", "max_drawdown_pct": "-24", "trade_count": "11"},
            {"name": "walk_001", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-2", "max_drawdown_pct": "-23", "trade_count": "7"},
            {"name": "walk_002", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-0.2", "max_drawdown_pct": "-4", "trade_count": "2"},
        ]

        rows = compare_monthly_validation_scenario_deltas(
            baseline_rows,
            candidate_rows,
            baseline_label="baseline",
            candidate_label="candidate",
        )

        by_name = {row["name"]: row for row in rows}
        self.assertEqual(by_name["stress"]["classification"], "RESOLVED")
        self.assertEqual(by_name["walk_001"]["classification"], "UNCHANGED_FAILURE")
        self.assertEqual(by_name["walk_002"]["classification"], "NEW_FAILURE")
        self.assertEqual(by_name["walk_002"]["excess_return_delta"], "-1.2")
        self.assertEqual(by_name["walk_002"]["trade_count_delta"], "-2")
        self.assertIn("over_defense_or_filter_drag", by_name["walk_002"]["diagnostic"])

    def test_compare_monthly_validation_scenario_deltas_diagnoses_new_failure_modes(self):
        baseline_rows = [
            {"name": "regime_bear", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "4", "max_drawdown_pct": "-12", "trade_count": "20"},
            {"name": "walk_004", "required": True, "deployable": True, "reason": "passed", "excess_return_pct": "10", "max_drawdown_pct": "-8", "trade_count": "15"},
        ]
        candidate_rows = [
            {"name": "regime_bear", "required": True, "deployable": False, "reason": "negative_excess_return", "excess_return_pct": "-2", "max_drawdown_pct": "-14", "trade_count": "45"},
            {"name": "walk_004", "required": True, "deployable": False, "reason": "train_window_rejected", "excess_return_pct": "5", "max_drawdown_pct": "-5", "trade_count": "16"},
        ]

        rows = compare_monthly_validation_scenario_deltas(baseline_rows, candidate_rows)

        by_name = {row["name"]: row for row in rows}
        self.assertEqual(by_name["regime_bear"]["diagnostic"], "selection_or_exposure_drag")
        self.assertEqual(by_name["walk_004"]["diagnostic"], "train_gate_regression")

    def test_compare_monthly_validation_scenario_deltas_flags_drawdown_buffer_regression(self):
        baseline_rows = [
            {
                "name": "full_period",
                "required": True,
                "deployable": True,
                "reason": "passed",
                "excess_return_pct": "60.70",
                "max_drawdown_pct": "-24.04",
                "trade_count": "80",
            }
        ]
        candidate_rows = [
            {
                "name": "full_period",
                "required": True,
                "deployable": False,
                "reason": "max_drawdown_breach",
                "excess_return_pct": "61.20",
                "max_drawdown_pct": "-25.13",
                "trade_count": "80",
            }
        ]

        rows = compare_monthly_validation_scenario_deltas(
            baseline_rows,
            candidate_rows,
            candidate_label="neutral_breadth_proxy_cap_50",
        )

        self.assertEqual(rows[0]["classification"], "NEW_FAILURE")
        self.assertEqual(rows[0]["excess_return_delta"], "0.5")
        self.assertEqual(rows[0]["max_drawdown_delta"], "-1.09")
        self.assertEqual(rows[0]["diagnostic"], "equity_improved_but_drawdown_buffer_worse")

    def test_save_monthly_validation_scenario_deltas_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "deltas.csv"
            saved = save_monthly_validation_scenario_deltas(
                [
                    {
                        "name": "walk_002",
                        "classification": "NEW_FAILURE",
                        "baseline_label": "baseline",
                        "candidate_label": "candidate",
                        "baseline_deployable": "True",
                        "candidate_deployable": "False",
                        "baseline_reason": "passed",
                        "candidate_reason": "negative_excess_return",
                        "baseline_excess_return_pct": "1",
                        "candidate_excess_return_pct": "-0.2",
                        "excess_return_delta": "-1.2",
                        "baseline_max_drawdown_pct": "-5",
                        "candidate_max_drawdown_pct": "-4",
                        "max_drawdown_delta": "1",
                        "baseline_trade_count": "4",
                        "candidate_trade_count": "2",
                        "trade_count_delta": "-2",
                        "diagnostic": "over_defense_or_filter_drag",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("classification", text.splitlines()[0])
        self.assertIn("NEW_FAILURE", text)

    def test_save_monthly_validation_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "comparison.csv"
            saved = save_monthly_validation_comparison(
                [
                    {
                        "baseline_label": "baseline",
                        "candidate_label": "candidate",
                        "status": "REJECT",
                        "baseline_failed_required": 2,
                        "candidate_failed_required": 2,
                        "failed_delta": 0,
                        "resolved_failures": "stress",
                        "new_failures": "walk_002",
                        "unchanged_failures": "walk_001",
                        "summary": "No net improvement.",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("new_failures", text.splitlines()[0])
        self.assertIn("REJECT", text)

    def test_build_monthly_validation_candidate_decision_rejects_new_failures(self):
        decision = build_monthly_validation_candidate_decision(
            {
                "candidate_label": "weak_cash10_stop12",
                "status": "REJECT",
                "baseline_failed_required": 5,
                "candidate_failed_required": 6,
                "failed_delta": 1,
                "resolved_failures": "stress; walk_001",
                "new_failures": "regime_bear; walk_002",
                "unchanged_failures": "walk_005",
            },
            [
                {"classification": "NEW_FAILURE", "diagnostic": "selection_or_exposure_drag", "name": "regime_bear"},
                {"classification": "NEW_FAILURE", "diagnostic": "train_gate_regression", "name": "walk_002"},
                {"classification": "RESOLVED", "diagnostic": "candidate_fixed_required_failure", "name": "stress"},
            ],
        )

        self.assertEqual(decision[0]["candidate_label"], "weak_cash10_stop12")
        self.assertEqual(decision[0]["decision"], "REJECT")
        self.assertIn("new_failures=2", decision[0]["decision_reasons"])
        self.assertIn("selection_or_exposure_drag=1", decision[0]["new_failure_diagnostics"])
        self.assertIn("regime_bear", decision[0]["new_failure_names"])
        self.assertIn("stress", decision[0]["resolved_failure_names"])
        self.assertIn("Do not adopt", decision[0]["recommendation"])

    def test_build_monthly_validation_candidate_decision_requires_oos_before_promotion(self):
        decision = build_monthly_validation_candidate_decision(
            {
                "candidate_label": "neutral_loss_guard55_min_history244",
                "status": "IMPROVED",
                "baseline_failed_required": 1,
                "candidate_failed_required": 0,
                "failed_delta": -1,
                "resolved_failures": "regime_sideways",
                "new_failures": "",
                "unchanged_failures": "",
            },
            [
                {
                    "classification": "RESOLVED",
                    "diagnostic": "candidate_fixed_required_failure",
                    "name": "regime_sideways",
                },
            ],
        )

        row = decision[0]
        self.assertEqual(row["decision"], "PAPER_REVIEW")
        self.assertEqual(row["post_cutoff_oos_start_date"], "PENDING_POST_CUTOFF_OOS")
        self.assertEqual(row["post_cutoff_oos_end_date"], "PENDING_POST_CUTOFF_OOS")
        self.assertIn("paper-only", row["recommendation"])
        self.assertIn("OOS/post-cutoff", row["recommendation"])
        self.assertIn("production readiness", row["recommendation"])

    def test_build_monthly_validation_candidate_decision_rejects_drawdown_buffer_loss(self):
        decision = build_monthly_validation_candidate_decision(
            {
                "candidate_label": "neutral_breadth_proxy_cap_50",
                "status": "REJECT",
                "baseline_failed_required": 5,
                "candidate_failed_required": 6,
                "failed_delta": 1,
                "resolved_failures": "walk_forward_003",
                "new_failures": "full_period",
                "unchanged_failures": "regime_sideways; walk_forward_005",
            },
            [
                {
                    "classification": "NEW_FAILURE",
                    "diagnostic": "equity_improved_but_drawdown_buffer_worse",
                    "name": "full_period",
                },
                {"classification": "RESOLVED", "diagnostic": "candidate_fixed_required_failure", "name": "walk_forward_003"},
            ],
        )

        row = decision[0]
        self.assertEqual(row["decision"], "REJECT")
        self.assertIn("drawdown_buffer_regressions=1", row["decision_reasons"])
        self.assertIn("equity_improved_but_drawdown_buffer_worse=1", row["new_failure_diagnostics"])
        self.assertIn("drawdown buffer", row["recommendation"])

    def test_build_monthly_validation_candidate_summary_combines_delta_and_path_evidence(self):
        rows = build_monthly_validation_candidate_summary(
            decision_rows=[
                {
                    "candidate_label": "neutral_breadth_proxy_cap_50",
                    "comparison_status": "REJECT",
                    "decision": "REJECT",
                    "decision_reasons": "comparison_rejected; new_failures=2; drawdown_buffer_regressions=2",
                    "baseline_failed_required": "5",
                    "candidate_failed_required": "6",
                    "failed_delta": "1",
                    "resolved_count": "1",
                    "new_failure_count": "2",
                    "unchanged_failure_count": "4",
                    "resolved_failure_names": "walk_forward_003",
                    "new_failure_names": "full_period; stress_slippage_x3",
                    "new_failure_diagnostics": "equity_improved_but_drawdown_buffer_worse=2",
                    "recommendation": "Do not adopt this candidate.",
                }
            ],
            delta_rows=[
                {
                    "candidate_label": "neutral_breadth_proxy_cap_50",
                    "name": "walk_forward_003",
                    "classification": "RESOLVED",
                    "diagnostic": "candidate_fixed_required_failure",
                },
                {
                    "candidate_label": "neutral_breadth_proxy_cap_50",
                    "name": "full_period",
                    "classification": "NEW_FAILURE",
                    "diagnostic": "equity_improved_but_drawdown_buffer_worse",
                    "excess_return_delta": "0.0247",
                    "max_drawdown_delta": "-1.0891",
                },
            ],
            path_comparison_rows=[
                {
                    "candidate_label": "neutral_breadth_proxy_cap_50",
                    "scenario": "full_period",
                    "date": "2025-04-07",
                    "equity_delta": "154349.6019",
                    "candidate_drawdown_pct": "-25.1331",
                    "rolling_peak_delta": "387782.9119",
                    "drawdown_delta_pct": "-1.1549",
                    "diagnostic": "equity_improved;drawdown_regression;higher_turnover",
                },
                {
                    "candidate_label": "neutral_breadth_proxy_cap_50",
                    "scenario": "stress_slippage_x3",
                    "date": "2025-04-07",
                    "equity_delta": "140457.5058",
                    "candidate_drawdown_pct": "-25.0493",
                    "rolling_peak_delta": "359575.5263",
                    "drawdown_delta_pct": "-1.1128",
                    "diagnostic": "equity_improved;drawdown_regression",
                },
            ],
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["candidate_rank"], "1")
        self.assertEqual(row["candidate_label"], "neutral_breadth_proxy_cap_50")
        self.assertEqual(row["decision"], "REJECT")
        self.assertEqual(row["resolved_count"], "1")
        self.assertEqual(row["new_failure_count"], "2")
        self.assertEqual(row["drawdown_buffer_regression_count"], "2")
        self.assertEqual(row["path_days_compared"], "2")
        self.assertEqual(row["path_equity_regression_days"], "0")
        self.assertEqual(row["path_equity_improved_days"], "2")
        self.assertEqual(row["path_drawdown_regression_days"], "2")
        self.assertEqual(row["path_higher_turnover_days"], "1")
        self.assertEqual(row["path_min_equity_delta"], "140457.5058")
        self.assertEqual(row["path_worst_drawdown_delta_pct"], "-1.1549")
        self.assertEqual(row["path_max_rolling_peak_delta"], "387782.9119")
        self.assertEqual(row["path_acceptance_decision"], "REJECT")
        self.assertEqual(row["path_candidate_drawdown_breach_days"], "2")
        self.assertEqual(row["path_equity_improved_drawdown_breach_days"], "2")
        self.assertEqual(row["path_peak_buffer_loss_days"], "2")
        self.assertIn("higher_rolling_peak_drawdown_buffer_loss", row["path_rejection_reasons"])
        self.assertIn("resolved=1", row["summary"])
        self.assertIn("new_failures=2", row["summary"])
        self.assertIn("drawdown_buffer_regressions=2", row["summary"])
        self.assertIn("path_acceptance=REJECT", row["summary"])

    def test_build_monthly_validation_candidate_summary_marks_pending_oos(self):
        rows = build_monthly_validation_candidate_summary(
            decision_rows=[
                {
                    "candidate_label": "neutral_loss_guard55_min_history244",
                    "comparison_status": "IMPROVED",
                    "decision": "PAPER_REVIEW",
                    "post_cutoff_oos_start_date": "PENDING_POST_CUTOFF_OOS",
                    "post_cutoff_oos_end_date": "PENDING_POST_CUTOFF_OOS",
                    "baseline_failed_required": "5",
                    "candidate_failed_required": "0",
                    "failed_delta": "-5",
                    "resolved_count": "5",
                    "new_failure_count": "0",
                    "unchanged_failure_count": "0",
                    "recommendation": "keep paper-only",
                }
            ],
            delta_rows=[],
        )

        self.assertEqual(rows[0]["post_cutoff_oos_status"], "pending")
        self.assertIn("post_cutoff_oos_status=pending", rows[0]["summary"])

    def test_save_monthly_validation_candidate_summary_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "candidate_summary.csv"
            saved = save_monthly_validation_candidate_summary(
                [
                    {
                        "candidate_rank": "1",
                        "candidate_label": "neutral_breadth_proxy_cap_50",
                        "decision": "REJECT",
                        "summary": "resolved=1; new_failures=2",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("candidate_rank", text.splitlines()[0])
        self.assertIn("post_cutoff_oos_status", text.splitlines()[0])
        self.assertIn("neutral_breadth_proxy_cap_50", text)

    def test_save_monthly_validation_candidate_decision_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "candidate_decision.csv"
            saved = save_monthly_validation_candidate_decision(
                [
                    {
                        "candidate_label": "candidate",
                        "comparison_status": "REJECT",
                        "decision": "REJECT",
                        "decision_reasons": "new_failures=1",
                        "post_cutoff_oos_start_date": "2026-06-19",
                        "post_cutoff_oos_end_date": "2026-07-03",
                        "baseline_failed_required": 5,
                        "candidate_failed_required": 6,
                        "failed_delta": 1,
                        "resolved_count": 1,
                        "new_failure_count": 1,
                        "unchanged_failure_count": 5,
                        "new_failure_diagnostics": "selection_or_exposure_drag=1",
                        "recommendation": "Do not adopt.",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("decision_reasons", text.splitlines()[0])
        self.assertIn("post_cutoff_oos_end_date", text.splitlines()[0])
        self.assertIn("2026-07-03", text)
        self.assertIn("REJECT", text)

    def test_analyze_monthly_drawdown_attribution_groups_equity_losses(self):
        result = _monthly_result(excess_return_pct=-5.0, max_drawdown_pct=-15.0)
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=920,
            total_return_pct=-8.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-8.0,
            max_drawdown_pct=-15.0,
            trade_count=0,
            decisions=[],
            trades=[],
            dates=["2024-01-02", "2024-01-31", "2024-02-01", "2024-02-29"],
            equity_curve=[1_050, 1_000, 980, 920],
        )

        rows = analyze_monthly_drawdown_attribution(result)

        by_month = {row["month"]: row for row in rows}
        self.assertEqual(by_month["2024-01"]["equity_change"], "0")
        self.assertEqual(by_month["2024-02"]["equity_change"], "-80")
        self.assertEqual(by_month["2024-02"]["status"], "LOSS")
        self.assertEqual(by_month["2024-02"]["worst_drawdown_pct"], "-12.381")

    def test_analyze_monthly_stress_drawdown_pressure_links_breach_days_to_loss_symbols(self):
        rows = analyze_monthly_stress_drawdown_pressure(
            scenario="stress_unit",
            monthly_rows=[
                {
                    "month": "2024-01",
                    "equity_change": "-500",
                    "return_pct": "-5",
                    "worst_drawdown_pct": "-12",
                },
                {
                    "month": "2024-02",
                    "equity_change": "-900",
                    "return_pct": "-9",
                    "worst_drawdown_pct": "-27",
                },
            ],
            symbol_rows=[
                {"symbol": "AAA", "realized_pnl": "-600"},
                {"symbol": "BBB", "realized_pnl": "-300"},
                {"symbol": "CCC", "realized_pnl": "200"},
            ],
            decision_rows=[
                {
                    "as_of_date": "2024-02-01",
                    "month": "2024-02",
                    "mode": "market_beta_proxy",
                    "reason": "no_train_candidate_strong_breadth_proxy",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "selected_symbols": "AAA;DDD",
                    "diagnostic": "market_beta_proxy;high_exposure_proxy;high_exposure_proxy_loss",
                }
            ],
            path_rows=[
                {
                    "date": "2024-02-15",
                    "equity": "730",
                    "cash": "10",
                    "exposure": "0.99",
                    "drawdown_pct": "-27",
                    "daily_return_pct": "-4",
                    "position_symbols": "AAA;DDD",
                },
                {
                    "date": "2024-02-16",
                    "equity": "760",
                    "cash": "20",
                    "exposure": "0.97",
                    "drawdown_pct": "-24",
                    "daily_return_pct": "3",
                    "position_symbols": "BBB;EEE",
                },
            ],
            recovery_rows=[
                {
                    "worst_month": "2024-02",
                    "worst_month_mode": "market_beta_proxy",
                    "worst_month_target_exposure": "0.99",
                    "top_loss_symbol": "AAA",
                    "top_loss_symbols": "AAA:-600;BBB:-300",
                    "diagnostic": "high_exposure_worst_month;symbol_loss_concentration",
                }
            ],
            drawdown_threshold_pct=-25.0,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "stress_unit")
        self.assertEqual(row["worst_loss_month"], "2024-02")
        self.assertEqual(row["worst_drawdown_date"], "2024-02-15")
        self.assertEqual(row["breach_day_count"], "1")
        self.assertEqual(row["breach_months"], "2024-02")
        self.assertEqual(row["top_loss_symbol"], "AAA")
        self.assertEqual(row["top_loss_symbols_in_breach_positions"], "AAA")
        self.assertEqual(row["top_loss_symbol_overlap_count"], "1")
        self.assertEqual(row["worst_month_mode"], "market_beta_proxy")
        self.assertEqual(row["high_exposure_loss_month_count"], "1")
        self.assertIn("loss_symbols_active_during_breach", row["diagnostic"])
        self.assertEqual(row["recommended_candidate_focus"], "test_conditional_proxy_or_position_loss_guard")

    def test_save_monthly_stress_drawdown_pressure_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "stress_drawdown.csv"
            saved = save_monthly_stress_drawdown_pressure(
                [
                    {
                        "scenario": "stress_unit",
                        "worst_drawdown_date": "2024-02-15",
                        "breach_day_count": "1",
                        "top_loss_symbol": "AAA",
                        "recommended_candidate_focus": "test_conditional_proxy_or_position_loss_guard",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,worst_drawdown_date", text.splitlines()[0])
        self.assertIn("recommended_candidate_focus", text.splitlines()[0])
        self.assertIn("stress_unit", text)

    def test_analyze_monthly_guarded_loss_position_pressure_links_selected_and_exit_losses(self):
        rows = analyze_monthly_guarded_loss_position_pressure(
            proxy_rows=[
                {
                    "scenario": "regime_sideways",
                    "as_of_date": "2025-03-04",
                    "signal_date": "2025-02-28",
                    "month": "2025-03",
                    "month_return_pct": "-6.4",
                    "mode": "market_beta_proxy",
                    "target_exposure": "0.55",
                    "cash_weight": "0.45",
                    "selected_symbols": "AAA;BBB",
                    "proxy_reversal_guard_triggered": "true",
                    "proxy_reversal_guard_reason": "proxy_reversal_guard_capped",
                    "diagnostic": "market_beta_proxy;strong_breadth",
                },
                {
                    "scenario": "regime_sideways",
                    "as_of_date": "2025-04-01",
                    "signal_date": "2025-03-31",
                    "month": "2025-04",
                    "month_return_pct": "2.1",
                    "mode": "market_beta_proxy",
                    "target_exposure": "0.7425",
                    "selected_symbols": "AAA;CCC",
                    "proxy_reversal_guard_triggered": "false",
                },
            ],
            symbol_rows=[
                {"symbol": "CCC", "realized_pnl": "-150", "first_trade_date": "2025-02-03", "last_trade_date": "2025-03-04"},
                {"symbol": "AAA", "realized_pnl": "-100", "first_trade_date": "2025-03-04", "last_trade_date": "2025-03-31"},
                {"symbol": "DDD", "realized_pnl": "-50", "first_trade_date": "2025-01-02", "last_trade_date": "2025-02-03"},
                {"symbol": "BBB", "realized_pnl": "20", "first_trade_date": "2025-03-04", "last_trade_date": "2025-03-31"},
            ],
            path_rows=[
                {"date": "2025-03-04", "drawdown_pct": "-12", "exposure": "0.53"},
                {"date": "2025-03-17", "drawdown_pct": "-17.5", "exposure": "0.55"},
                {"date": "2025-04-01", "drawdown_pct": "-15", "exposure": "0.70"},
            ],
            top_symbol_count=3,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "regime_sideways")
        self.assertEqual(row["month"], "2025-03")
        self.assertEqual(row["selected_loss_symbols"], "AAA:-100")
        self.assertEqual(row["selected_loss_realized_pnl"], "-100")
        self.assertEqual(row["month_exit_loss_symbols"], "CCC:-150;AAA:-100")
        self.assertEqual(row["month_exit_loss_realized_pnl"], "-250")
        self.assertEqual(row["carryover_exit_loss_symbols"], "CCC:-150")
        self.assertEqual(row["carryover_exit_loss_windows"], "CCC:2025-02-03..2025-03-04")
        self.assertEqual(row["worst_drawdown_date"], "2025-03-17")
        self.assertEqual(row["worst_drawdown_pct"], "-17.5")
        self.assertEqual(row["average_month_path_exposure"], "0.54")
        self.assertIn("carryover_exit_losses", row["diagnostic"])
        self.assertEqual(row["recommended_candidate_focus"], "analyze_position_level_loss_controls_without_broad_stop")
        self.assertEqual(row["paper_only"], "true")

    def test_save_monthly_guarded_loss_position_pressure_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "guarded_loss_pressure.csv"
            saved = save_monthly_guarded_loss_position_pressure(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-03",
                        "selected_loss_symbols": "AAA:-100",
                        "recommended_candidate_focus": "analyze_position_level_loss_controls_without_broad_stop",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("selected_loss_symbols", text.splitlines()[0])
        self.assertIn("analyze_position_level_loss_controls_without_broad_stop", text)

    def test_analyze_monthly_position_loss_control_diagnostics_flags_threshold_hits_before_worst_drawdown(self):
        rows = analyze_monthly_position_loss_control_diagnostics(
            pressure_rows=[
                {
                    "scenario": "regime_sideways",
                    "month": "2025-03",
                    "as_of_date": "2025-03-04",
                    "worst_drawdown_date": "2025-03-17",
                    "selected_loss_symbols": "AAA:-100",
                    "carryover_exit_loss_symbols": "CCC:-150",
                }
            ],
            symbol_candles={
                "AAA": [
                    Candle("2025-03-04", 100, 103, 99, 100, 1_000),
                    Candle("2025-03-10", 96, 98, 92, 94, 1_000),
                    Candle("2025-03-17", 91, 93, 84, 86, 1_000),
                ],
                "CCC": [
                    Candle("2025-03-04", 200, 202, 198, 200, 1_000),
                    Candle("2025-03-12", 184, 186, 175, 180, 1_000),
                    Candle("2025-03-17", 178, 181, 176, 179, 1_000),
                ],
                "DDD": [
                    Candle("2025-03-04", 50, 51, 49, 50, 1_000),
                ],
            },
            loss_threshold_pct=10.0,
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["pressure_source"], "selected_loss")
        self.assertEqual(by_symbol["AAA"]["max_adverse_return_pct"], "-16")
        self.assertEqual(by_symbol["AAA"]["would_trigger"], "true")
        self.assertEqual(by_symbol["AAA"]["stop_trigger_date"], "2025-03-17")
        self.assertEqual(by_symbol["AAA"]["triggered_before_worst_drawdown"], "true")
        self.assertEqual(by_symbol["AAA"]["recommended_candidate_focus"], "paper_position_stop_candidate_before_worst_drawdown")
        self.assertEqual(by_symbol["CCC"]["pressure_source"], "carryover_exit_loss")
        self.assertEqual(by_symbol["CCC"]["stop_trigger_date"], "2025-03-12")
        self.assertEqual(by_symbol["CCC"]["loss_realized_pnl"], "-150")
        self.assertEqual(by_symbol["CCC"]["paper_only"], "true")

    def test_analyze_monthly_position_loss_control_diagnostics_respects_carryover_exit_window(self):
        rows = analyze_monthly_position_loss_control_diagnostics(
            pressure_rows=[
                {
                    "scenario": "regime_sideways",
                    "month": "2025-03",
                    "as_of_date": "2025-03-04",
                    "worst_drawdown_date": "2025-03-17",
                    "carryover_exit_loss_symbols": "CCC:-150",
                    "carryover_exit_loss_windows": "CCC:2025-03-04..2025-03-04",
                }
            ],
            symbol_candles={
                "CCC": [
                    Candle("2025-03-04", 200, 202, 198, 200, 1_000),
                    Candle("2025-03-12", 184, 186, 175, 180, 1_000),
                ],
            },
            loss_threshold_pct=10.0,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["symbol"], "CCC")
        self.assertEqual(row["entry_date"], "2025-03-04")
        self.assertEqual(row["max_adverse_return_pct"], "-1")
        self.assertEqual(row["would_trigger"], "false")
        self.assertEqual(row["stop_trigger_date"], "")
        self.assertIn("explicit_holding_window", row["diagnostic"])

    def test_save_monthly_position_loss_control_diagnostics_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "position_loss_controls.csv"
            saved = save_monthly_position_loss_control_diagnostics(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-03",
                        "symbol": "AAA",
                        "would_trigger": "true",
                        "recommended_candidate_focus": "paper_position_stop_candidate_before_worst_drawdown",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("would_trigger", text.splitlines()[0])
        self.assertIn("paper_position_stop_candidate_before_worst_drawdown", text)

    def test_analyze_symbol_realized_pnl_attribution_uses_fifo(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=900,
            total_return_pct=-10.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-10.0,
            max_drawdown_pct=-10.0,
            trade_count=4,
            decisions=[],
            trades=[
                MonthlyBacktestTrade("2024-01-02", "AAA", "BUY", 100, 5, 500, "entry"),
                MonthlyBacktestTrade("2024-01-03", "AAA", "BUY", 90, 5, 50, "entry"),
                MonthlyBacktestTrade("2024-02-01", "AAA", "SELL", 80, 6, 530, "exit"),
                MonthlyBacktestTrade("2024-02-02", "BBB", "SELL", 50, 2, 630, "orphan"),
            ],
            dates=["2024-01-02", "2024-02-02"],
            equity_curve=[1_000, 900],
        )

        rows = analyze_symbol_realized_pnl_attribution(result)

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["realized_pnl"], "-110")
        self.assertEqual(by_symbol["AAA"]["open_quantity"], "4")
        self.assertEqual(by_symbol["AAA"]["status"], "LOSS")
        self.assertEqual(by_symbol["BBB"]["unmatched_sell_quantity"], "2")

    def test_analyze_monthly_decision_attribution_summarizes_selected_symbols_and_exposure(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000_000,
            final_equity=1_050_000,
            total_return_pct=5.0,
            buy_hold_return_pct=2.0,
            excess_return_pct=3.0,
            max_drawdown_pct=-4.0,
            trade_count=2,
            decisions=[
                MonthlyDecision(
                    as_of_date="2026-01-31",
                    signal_date="2026-02-02",
                    mode="risk_on",
                    selected_preset="balanced",
                    target_weights={"005930": 0.4, "000660": 0.35},
                    reason="unit",
                ),
                MonthlyDecision(
                    as_of_date="2026-02-28",
                    signal_date="2026-03-02",
                    mode="cash",
                    selected_preset="balanced",
                    target_weights={},
                    reason="risk_off",
                ),
            ],
            trades=[],
            dates=["2026-01-31", "2026-02-28"],
            equity_curve=[1_000_000, 1_050_000],
        )

        rows = analyze_monthly_decision_attribution(result)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["selected_symbols"], "005930;000660")
        self.assertEqual(rows[0]["position_count"], "2")
        self.assertEqual(rows[0]["target_exposure"], "0.75")
        self.assertEqual(rows[0]["cash_weight"], "0.25")
        self.assertEqual(rows[0]["max_position_weight"], "0.4")
        self.assertEqual(rows[1]["selected_symbols"], "")
        self.assertEqual(rows[1]["target_exposure"], "0")
        self.assertEqual(rows[1]["cash_weight"], "1")

    def test_save_monthly_decision_attribution_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "decision_attribution.csv"
            saved = save_monthly_decision_attribution(
                [
                    {
                        "as_of_date": "2026-01-31",
                        "signal_date": "2026-02-02",
                        "mode": "risk_on",
                        "selected_symbols": "005930;000660",
                        "target_exposure": "0.75",
                        "cash_weight": "0.25",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("selected_symbols", text.splitlines()[0])
        self.assertIn("005930;000660", text)

    def test_analyze_monthly_proxy_decision_diagnostics_flags_loss_and_recovery_context(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=1_050,
            total_return_pct=5.0,
            buy_hold_return_pct=15.0,
            excess_return_pct=-10.0,
            max_drawdown_pct=-10.0,
            trade_count=0,
            decisions=[
                MonthlyDecision(
                    as_of_date="2025-01-31",
                    signal_date="2025-01-30",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.5, "BBB": 0.49},
                    reason="no_train_candidate_strong_breadth_proxy",
                ),
                MonthlyDecision(
                    as_of_date="2025-02-28",
                    signal_date="2025-02-27",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.375, "BBB": 0.3675},
                    reason="no_train_candidate_strong_breadth_proxy_drawdown_guard",
                ),
                MonthlyDecision(
                    as_of_date="2025-03-31",
                    signal_date="2025-03-28",
                    mode="alpha",
                    selected_preset="balanced",
                    target_weights={"CCC": 0.7425},
                    reason="selected_monthly_alpha_drawdown_guard",
                ),
            ],
            trades=[],
            dates=["2025-01-31", "2025-02-28", "2025-03-31"],
            equity_curve=[900, 990, 1_050],
        )
        evidence = {
            "2025-01-31": {
                "prior_breadth": "0.72",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "trend_scale": "1",
                "volatility_scale": "1",
                "liquidity_scale": "1",
                "exposure_scale": "1",
                "direct_candidate_count": 1,
                "eligible_direct_candidate_count": 0,
                "direct_candidate_rejection_reasons": "low_positive_ratio=1",
                "best_direct_excess_return_pct": "-3.5",
                "best_direct_train_positive_ratio": "0.25",
            },
            "2025-02-28": {
                "prior_breadth": "0.68",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "trend_scale": "1",
                "volatility_scale": "1",
                "liquidity_scale": "1",
                "exposure_scale": "1",
                "direct_candidate_count": 1,
                "eligible_direct_candidate_count": 0,
                "direct_candidate_rejection_reasons": "low_positive_ratio=1",
                "best_direct_excess_return_pct": "-1.0",
                "best_direct_train_positive_ratio": "0.5",
            },
            "2025-03-31": {
                "prior_breadth": "0.45",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "trend_scale": "1",
                "volatility_scale": "1",
                "liquidity_scale": "1",
                "exposure_scale": "1",
                "direct_candidate_count": 1,
                "eligible_direct_candidate_count": 1,
                "direct_candidate_rejection_reasons": "eligible=1",
                "best_direct_excess_return_pct": "8.0",
                "best_direct_train_positive_ratio": "1",
            },
        }

        rows = analyze_monthly_proxy_decision_diagnostics(
            result,
            symbol_candles={},
            config=MonthlyRebalanceConfig(),
            scenario="unit_proxy",
            evidence_provider=lambda _candles, *, as_of_date, config: evidence[as_of_date],
        )

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["scenario"], "unit_proxy")
        self.assertEqual(rows[0]["month_return_pct"], "-10")
        self.assertIn("market_beta_proxy", rows[0]["diagnostic"])
        self.assertIn("high_exposure_proxy_loss", rows[0]["diagnostic"])
        self.assertIn("strong_breadth", rows[0]["diagnostic"])
        self.assertIn("no_eligible_direct_candidate", rows[0]["diagnostic"])
        self.assertIn("proxy_gain_participation", rows[1]["diagnostic"])
        self.assertIn("already_scaled_by_drawdown_guard", rows[1]["diagnostic"])
        self.assertIn("scaled_alpha_recovery", rows[2]["diagnostic"])
        self.assertEqual(rows[0]["recommended_next_action"], "test_conditional_proxy_entry_guard")
        self.assertEqual(rows[1]["recommended_next_action"], "preserve_scaled_recovery_participation")

    def test_analyze_monthly_proxy_decision_diagnostics_includes_reversal_guard_evidence(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=980,
            total_return_pct=-2.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-2.0,
            max_drawdown_pct=-2.0,
            trade_count=0,
            decisions=[
                MonthlyDecision(
                    as_of_date="2025-01-05",
                    signal_date="2025-01-05",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.275, "BBB": 0.275},
                    reason="no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped",
                )
            ],
            trades=[],
            dates=["2025-01-05"],
            equity_curve=[980],
        )
        config = MonthlyRebalanceConfig(
            market_beta_proxy_size=2,
            point_in_time_min_history_days=1,
            point_in_time_min_reference_price=0.0,
            point_in_time_liquidity_window_days=2,
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=4,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=2,
            market_beta_proxy_reversal_guard_short_max_return_pct=10.0,
            market_beta_proxy_reversal_guard_extreme_return_pct=0.0,
            market_beta_proxy_reversal_guard_medium_drawdown_pct=-10.0,
        )
        symbol_candles = {
            "AAA": [
                Candle("2025-01-01", 100, 100, 100, 100, 10_000),
                Candle("2025-01-02", 125, 125, 125, 125, 10_000),
                Candle("2025-01-03", 145, 145, 145, 145, 10_000),
                Candle("2025-01-04", 148, 148, 148, 148, 10_000),
                Candle("2025-01-05", 150, 150, 150, 150, 10_000),
            ],
            "BBB": [
                Candle("2025-01-01", 100, 100, 100, 100, 9_000),
                Candle("2025-01-02", 125, 125, 125, 125, 9_000),
                Candle("2025-01-03", 145, 145, 145, 145, 9_000),
                Candle("2025-01-04", 148, 148, 148, 148, 9_000),
                Candle("2025-01-05", 150, 150, 150, 150, 9_000),
            ],
        }

        rows = analyze_monthly_proxy_decision_diagnostics(
            result,
            symbol_candles=symbol_candles,
            config=config,
            scenario="unit_proxy_guard",
            evidence_provider=lambda _candles, *, as_of_date, config: {
                "prior_breadth": "0.72",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "eligible_direct_candidate_count": 0,
            },
        )

        self.assertEqual(rows[0]["proxy_reversal_guard_triggered"], "true")
        self.assertEqual(rows[0]["proxy_reversal_guard_cap"], "0.55")
        self.assertEqual(rows[0]["proxy_reversal_guard_medium_return_pct"], "50")
        self.assertEqual(rows[0]["proxy_reversal_guard_reason"], "proxy_reversal_guard_capped")
        self.assertIn("proxy_reversal_guard_medium_drawdown_pct", rows[0])
        self.assertNotEqual(rows[0]["proxy_reversal_guard_short_return_pct"], "")

    def test_analyze_monthly_proxy_decision_diagnostics_uses_decision_universe_for_guard_evidence(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=990,
            total_return_pct=-1.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-1.0,
            max_drawdown_pct=-1.0,
            trade_count=0,
            decisions=[
                MonthlyDecision(
                    as_of_date="2025-01-05",
                    signal_date="2025-01-05",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.99},
                    reason="no_train_candidate_strong_breadth_proxy",
                )
            ],
            trades=[],
            dates=["2025-01-05"],
            equity_curve=[990],
        )
        config = MonthlyRebalanceConfig(
            market_beta_proxy_size=2,
            point_in_time_min_history_days=1,
            point_in_time_min_reference_price=0.0,
            point_in_time_liquidity_top_n=1,
            point_in_time_liquidity_window_days=2,
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=4,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=2,
            market_beta_proxy_reversal_guard_short_max_return_pct=300.0,
        )
        symbol_candles = {
            "AAA": [
                Candle("2025-01-01", 100, 100, 100, 100, 10_000),
                Candle("2025-01-02", 100, 100, 100, 100, 10_000),
                Candle("2025-01-03", 101, 101, 101, 101, 10_000),
                Candle("2025-01-04", 101, 101, 101, 101, 10_000),
                Candle("2025-01-05", 102, 102, 102, 102, 10_000),
            ],
            "HOT": [
                Candle("2025-01-01", 100, 100, 100, 100, 1),
                Candle("2025-01-02", 150, 150, 150, 150, 1),
                Candle("2025-01-03", 200, 200, 200, 200, 1),
                Candle("2025-01-04", 250, 250, 250, 250, 1),
                Candle("2025-01-05", 300, 300, 300, 300, 1),
            ],
        }

        rows = analyze_monthly_proxy_decision_diagnostics(
            result,
            symbol_candles=symbol_candles,
            config=config,
            scenario="unit_proxy_guard_liquidity",
            evidence_provider=lambda _candles, *, as_of_date, config: {
                "prior_breadth": "0.72",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "eligible_direct_candidate_count": 0,
            },
        )

        self.assertEqual(rows[0]["proxy_reversal_guard_triggered"], "false")
        self.assertEqual(rows[0]["proxy_reversal_guard_medium_return_pct"], "2")
        self.assertEqual(rows[0]["proxy_reversal_guard_reason"], "proxy_exposure_capped")

    def test_analyze_monthly_proxy_decision_diagnostics_marks_reversal_guard_not_applicable_for_alpha(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=990,
            total_return_pct=-1.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-1.0,
            max_drawdown_pct=-1.0,
            trade_count=0,
            decisions=[
                MonthlyDecision(
                    as_of_date="2025-01-05",
                    signal_date="2025-01-05",
                    mode="alpha",
                    selected_preset="balanced",
                    target_weights={"AAA": 0.99},
                    reason="selected_monthly_alpha",
                )
            ],
            trades=[],
            dates=["2025-01-05"],
            equity_curve=[990],
        )
        config = MonthlyRebalanceConfig(
            market_beta_proxy_size=1,
            point_in_time_min_history_days=1,
            point_in_time_min_reference_price=0.0,
            point_in_time_liquidity_window_days=2,
            market_beta_proxy_reversal_guard_max_exposure=0.55,
            market_beta_proxy_reversal_guard_medium_lookback_days=4,
            market_beta_proxy_reversal_guard_medium_return_pct=35.0,
            market_beta_proxy_reversal_guard_short_lookback_days=2,
            market_beta_proxy_reversal_guard_short_max_return_pct=30.0,
        )
        symbol_candles = {
            "AAA": [
                Candle("2025-01-01", 100, 100, 100, 100, 10_000),
                Candle("2025-01-02", 125, 125, 125, 125, 10_000),
                Candle("2025-01-03", 145, 145, 145, 145, 10_000),
                Candle("2025-01-04", 148, 148, 148, 148, 10_000),
                Candle("2025-01-05", 150, 150, 150, 150, 10_000),
            ],
        }

        rows = analyze_monthly_proxy_decision_diagnostics(
            result,
            symbol_candles=symbol_candles,
            config=config,
            scenario="unit_alpha_guard",
            evidence_provider=lambda _candles, *, as_of_date, config: {
                "prior_breadth": "0.72",
                "fallback_breadth_threshold": "0.5",
                "market_beta_breadth_threshold": "0.25",
                "eligible_direct_candidate_count": 1,
            },
        )

        self.assertEqual(rows[0]["proxy_reversal_guard_triggered"], "false")
        self.assertEqual(rows[0]["proxy_reversal_guard_reason"], "not_market_beta_proxy")
        self.assertEqual(rows[0]["proxy_reversal_guard_medium_return_pct"], "")

    def test_save_monthly_proxy_decision_diagnostics_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "proxy.csv"
            saved = save_monthly_proxy_decision_diagnostics(
                [
                    {
                        "scenario": "unit",
                        "as_of_date": "2025-01-31",
                        "mode": "market_beta_proxy",
                        "diagnostic": "high_exposure_proxy_loss",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("recommended_next_action", text.splitlines()[0])
        self.assertIn("high_exposure_proxy_loss", text)

    def test_analyze_monthly_proxy_guard_outcomes_flags_profitable_continuation_caps(self):
        rows = analyze_monthly_proxy_guard_outcomes(
            [
                {
                    "scenario": "candidate_guard",
                    "as_of_date": "2025-06-02",
                    "signal_date": "2025-05-30",
                    "month": "2025-06",
                    "month_return_pct": "7.4531",
                    "month_status": "GAIN",
                    "mode": "market_beta_proxy",
                    "reason": "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped",
                    "target_exposure": "0.55",
                    "cash_weight": "0.45",
                    "proxy_reversal_guard_triggered": "true",
                    "proxy_reversal_guard_cap": "0.55",
                    "proxy_reversal_guard_medium_return_pct": "38.5407",
                    "proxy_reversal_guard_short_return_pct": "8.6214",
                    "proxy_reversal_guard_reason": "proxy_reversal_guard_capped",
                    "diagnostic": "market_beta_proxy;proxy_gain_participation;strong_breadth",
                    "recommended_next_action": "preserve_train_gate_and_improve_alpha_candidates",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["guard_outcome"], "profitable_continuation_capped")
        self.assertEqual(rows[0]["guard_triggered"], "true")
        self.assertEqual(rows[0]["candidate_design_hint"], "add_continuation_discriminator_before_capping")
        self.assertEqual(rows[0]["paper_only"], "true")

    def test_analyze_monthly_proxy_guard_outcomes_flags_missed_high_exposure_losses(self):
        rows = analyze_monthly_proxy_guard_outcomes(
            [
                {
                    "scenario": "candidate_guard",
                    "as_of_date": "2026-06-01",
                    "signal_date": "2026-05-29",
                    "month": "2026-06",
                    "month_return_pct": "-9.3983",
                    "month_status": "LOSS",
                    "mode": "market_beta_proxy",
                    "reason": "no_train_candidate_strong_breadth_proxy",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "proxy_reversal_guard_triggered": "false",
                    "proxy_reversal_guard_cap": "1",
                    "proxy_reversal_guard_medium_return_pct": "62",
                    "proxy_reversal_guard_short_return_pct": "41",
                    "proxy_reversal_guard_reason": "proxy_exposure_capped",
                    "diagnostic": "market_beta_proxy;high_exposure_proxy;high_exposure_proxy_loss",
                    "recommended_next_action": "test_conditional_proxy_entry_guard",
                }
            ]
        )

        self.assertEqual(rows[0]["guard_outcome"], "missed_high_exposure_loss")
        self.assertEqual(rows[0]["candidate_design_hint"], "tighten_loss_discriminator_without_broad_cash_drag")
        self.assertEqual(rows[0]["loss_month"], "true")

    def test_save_monthly_proxy_guard_outcomes_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "proxy_guard_outcomes.csv"
            saved = save_monthly_proxy_guard_outcomes(
                [
                    {
                        "scenario": "candidate_guard",
                        "month": "2025-06",
                        "guard_outcome": "profitable_continuation_capped",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("guard_outcome", text)
        self.assertIn("candidate_design_hint", text)

    def test_analyze_monthly_proxy_decision_context_summary_groups_loss_and_recovery_context(self):
        rows = analyze_monthly_proxy_decision_context_summary(
            [
                {
                    "scenario": "regime_sideways",
                    "month": "2024-10",
                    "mode": "market_beta_proxy",
                    "month_return_pct": "-2.7",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "prior_breadth": "0.47",
                    "proxy_reversal_guard_triggered": "false",
                    "diagnostic": "market_beta_proxy;high_exposure_proxy;high_exposure_proxy_loss;neutral_breadth",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2024-11",
                    "mode": "market_beta_proxy",
                    "month_return_pct": "-1.8",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "prior_breadth": "0.48",
                    "proxy_reversal_guard_triggered": "false",
                    "diagnostic": "market_beta_proxy;high_exposure_proxy;high_exposure_proxy_loss;neutral_breadth",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-02",
                    "mode": "market_beta_proxy",
                    "month_return_pct": "3.4",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "prior_breadth": "0.75",
                    "proxy_reversal_guard_triggered": "false",
                    "diagnostic": "market_beta_proxy;high_exposure_proxy;proxy_gain_participation;strong_breadth",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-03",
                    "mode": "market_beta_proxy",
                    "month_return_pct": "-6.4",
                    "target_exposure": "0.55",
                    "cash_weight": "0.45",
                    "prior_breadth": "0.70",
                    "proxy_reversal_guard_triggered": "true",
                    "diagnostic": "market_beta_proxy;strong_breadth;no_eligible_direct_candidate",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "mode": "market_beta_proxy",
                    "month_return_pct": "0.6",
                    "target_exposure": "0.7425",
                    "cash_weight": "0.2575",
                    "prior_breadth": "0.55",
                    "proxy_reversal_guard_triggered": "false",
                    "diagnostic": "market_beta_proxy;proxy_gain_participation;already_scaled_by_drawdown_guard;scaled_proxy_recovery;strong_breadth",
                },
            ]
        )

        by_context = {
            (row["breadth_context"], row["exposure_bucket"]): row
            for row in rows
        }
        neutral_high = by_context[("neutral_breadth", "high_exposure")]
        self.assertEqual(neutral_high["proxy_month_count"], "2")
        self.assertEqual(neutral_high["loss_month_count"], "2")
        self.assertEqual(neutral_high["high_exposure_loss_count"], "2")
        self.assertEqual(neutral_high["gain_participation_count"], "0")
        self.assertEqual(neutral_high["avg_target_exposure"], "0.99")
        self.assertEqual(neutral_high["recommended_candidate_focus"], "test_neutral_breadth_loss_discriminator")
        strong_high = by_context[("strong_breadth", "high_exposure")]
        self.assertEqual(strong_high["gain_participation_count"], "1")
        self.assertEqual(strong_high["recommended_candidate_focus"], "preserve_strong_breadth_recovery")
        strong_guarded = by_context[("strong_breadth", "guarded_exposure")]
        self.assertEqual(strong_guarded["months"], "2025-03")
        self.assertEqual(strong_guarded["loss_month_count"], "1")
        self.assertEqual(strong_guarded["guard_triggered_count"], "1")
        self.assertEqual(strong_guarded["recommended_candidate_focus"], "analyze_guarded_loss_position_pressure")
        self.assertIn("guarded_loss_residual", strong_guarded["diagnostic"])
        strong_scaled = by_context[("strong_breadth", "scaled_exposure")]
        self.assertEqual(strong_scaled["months"], "2025-04")
        self.assertEqual(strong_scaled["paper_only"], "true")

    def test_save_monthly_proxy_decision_context_summary_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "proxy_context_summary.csv"
            saved = save_monthly_proxy_decision_context_summary(
                [
                    {
                        "scenario": "regime_sideways",
                        "breadth_context": "neutral_breadth",
                        "exposure_bucket": "high_exposure",
                        "proxy_month_count": "2",
                        "recommended_candidate_focus": "test_neutral_breadth_loss_discriminator",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("breadth_context", text.splitlines()[0])
        self.assertIn("test_neutral_breadth_loss_discriminator", text)

    def test_analyze_monthly_proxy_guard_recovery_exits_flags_recovery_drag_after_loss_cap(self):
        rows = analyze_monthly_proxy_guard_recovery_exits(
            [
                {
                    "scenario": "walk_forward_005",
                    "month": "2026-03",
                    "mode": "market_beta_proxy",
                    "reason": "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped",
                    "target_exposure": "0.55",
                    "cash_weight": "0.45",
                    "month_return_pct": "-13.954",
                    "month_status": "LOSS",
                    "proxy_reversal_guard_triggered": "true",
                    "proxy_reversal_guard_medium_return_pct": "63.4465",
                    "proxy_reversal_guard_short_return_pct": "32.5244",
                    "proxy_reversal_guard_medium_drawdown_pct": "-4.9111",
                    "diagnostic": "market_beta_proxy;strong_breadth;no_eligible_direct_candidate",
                },
                {
                    "scenario": "walk_forward_005",
                    "month": "2026-04",
                    "mode": "market_beta_proxy",
                    "reason": "no_train_candidate_strong_breadth_proxy_proxy_reversal_guard_capped",
                    "target_exposure": "0.55",
                    "cash_weight": "0.45",
                    "month_return_pct": "16.3361",
                    "month_status": "GAIN",
                    "proxy_reversal_guard_triggered": "true",
                    "proxy_reversal_guard_medium_return_pct": "36.6735",
                    "proxy_reversal_guard_short_return_pct": "-6.6038",
                    "proxy_reversal_guard_medium_drawdown_pct": "-12.4731",
                    "diagnostic": "market_beta_proxy;proxy_gain_participation;strong_breadth",
                },
            ],
            [
                {
                    "scenario": "walk_forward_005",
                    "month": "2026-03",
                    "baseline_return_pct": "-19.2651",
                    "candidate_return_pct": "-13.954",
                    "return_delta_pct": "5.3111",
                    "baseline_worst_drawdown_pct": "-20.5503",
                    "candidate_worst_drawdown_pct": "-15.2709",
                    "drawdown_delta_pct": "5.2794",
                    "diagnostic": "drawdown_improved",
                },
                {
                    "scenario": "walk_forward_005",
                    "month": "2026-04",
                    "baseline_return_pct": "20.1371",
                    "candidate_return_pct": "16.3361",
                    "return_delta_pct": "-3.801",
                    "baseline_worst_drawdown_pct": "-14.7816",
                    "candidate_worst_drawdown_pct": "-10.6855",
                    "drawdown_delta_pct": "4.0961",
                    "diagnostic": "return_drag",
                },
            ],
            scenario="walk_forward_005",
            candidate_label="proxy_guard_short5_extreme50_mdd10",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["loss_month"], "2026-03")
        self.assertEqual(row["recovery_month"], "2026-04")
        self.assertEqual(row["loss_guard_triggered"], "true")
        self.assertEqual(row["recovery_guard_triggered"], "true")
        self.assertEqual(row["recovery_exit_outcome"], "recovery_drag_after_loss_cap")
        self.assertEqual(row["candidate_design_hint"], "test_guard_exit_after_loss_cap_confirmation")
        self.assertIn("do_not_broaden_loss_cap", row["risk_note"])
        self.assertEqual(row["paper_only"], "true")

    def test_save_monthly_proxy_guard_recovery_exits_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "proxy_guard_recovery_exits.csv"
            saved = save_monthly_proxy_guard_recovery_exits(
                [
                    {
                        "scenario": "walk_forward_005",
                        "loss_month": "2026-03",
                        "recovery_month": "2026-04",
                        "recovery_exit_outcome": "recovery_drag_after_loss_cap",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("recovery_exit_outcome", text.splitlines()[0])
        self.assertIn("recovery_drag_after_loss_cap", text)

    def test_analyze_monthly_benchmark_excess_flags_negative_excess_month(self):
        rows = analyze_monthly_benchmark_excess(
            [
                {
                    "month": "2025-03",
                    "start_date": "2025-03-03",
                    "end_date": "2025-03-31",
                    "return_pct": "-6.0",
                    "equity_change": "-600",
                    "worst_drawdown_pct": "-12",
                },
                {
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-30",
                    "return_pct": "3.0",
                    "equity_change": "300",
                    "worst_drawdown_pct": "-4",
                },
            ],
            {
                "AAA": [
                    _candle("2025-03-03", 100, 100),
                    _candle("2025-03-31", 110, 110),
                    _candle("2025-04-01", 110, 110),
                    _candle("2025-04-30", 112, 112),
                ],
                "BBB": [
                    _candle("2025-03-03", 100, 100),
                    _candle("2025-03-31", 100, 100),
                    _candle("2025-04-01", 100, 100),
                    _candle("2025-04-30", 98, 98),
                ],
            },
            scenario="regime_sideways",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )

        march = rows[0]
        april = rows[1]
        self.assertEqual(march["scenario"], "regime_sideways")
        self.assertEqual(march["month"], "2025-03")
        self.assertEqual(march["strategy_return_pct"], "-6")
        self.assertEqual(march["benchmark_return_pct"], "5")
        self.assertEqual(march["monthly_excess_return_pct"], "-11")
        self.assertEqual(march["excess_status"], "NEGATIVE_EXCESS")
        self.assertIn("benchmark_outperformed", march["diagnostic"])
        self.assertEqual(april["excess_status"], "POSITIVE_EXCESS")

    def test_save_monthly_benchmark_excess_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_excess.csv"
            saved = save_monthly_benchmark_excess(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-03",
                        "monthly_excess_return_pct": "-11",
                        "excess_status": "NEGATIVE_EXCESS",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("monthly_excess_return_pct", text.splitlines()[0])
        self.assertIn("NEGATIVE_EXCESS", text)

    def test_analyze_monthly_benchmark_contributions_flags_missed_benchmark_winners(self):
        rows = analyze_monthly_benchmark_contributions(
            [
                {
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-30",
                    "return_pct": "2.0",
                }
            ],
            [
                {
                    "as_of_date": "2025-04-01",
                    "reason": "unit_proxy",
                    "target_weights": "AAA:0.1;BBB:0.2",
                }
            ],
            {
                "AAA": [_candle("2025-04-01", 100, 100), _candle("2025-04-30", 120, 120)],
                "BBB": [_candle("2025-04-01", 100, 100), _candle("2025-04-30", 100, 100)],
                "CCC": [_candle("2025-04-01", 100, 100), _candle("2025-04-30", 110, 110)],
            },
            scenario="regime_sideways",
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["CCC"]["contribution_role"], "benchmark_only")
        self.assertEqual(by_symbol["CCC"]["strategy_weight"], "0")
        self.assertEqual(by_symbol["CCC"]["benchmark_weight"], "0.3333")
        self.assertEqual(by_symbol["CCC"]["symbol_return_pct"], "10")
        self.assertEqual(by_symbol["CCC"]["strategy_contribution_pct"], "0")
        self.assertEqual(by_symbol["CCC"]["benchmark_contribution_pct"], "3.3333")
        self.assertEqual(by_symbol["CCC"]["contribution_delta_pct"], "-3.3333")
        self.assertIn("missed_benchmark_winner", by_symbol["CCC"]["diagnostic"])
        self.assertEqual(by_symbol["AAA"]["contribution_role"], "strategy_underweight")
        self.assertIn("underweighted_benchmark_winner", by_symbol["AAA"]["diagnostic"])

    def test_save_monthly_benchmark_contributions_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_contributions.csv"
            saved = save_monthly_benchmark_contributions(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-04",
                        "symbol": "CCC",
                        "contribution_role": "benchmark_only",
                        "diagnostic": "missed_benchmark_winner",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("contribution_delta_pct", text.splitlines()[0])
        self.assertIn("missed_benchmark_winner", text)

    def test_analyze_monthly_benchmark_selection_marks_missed_winner_outside_proxy_rank_cutoff(self):
        rows = analyze_monthly_benchmark_selection(
            [
                {
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-30",
                    "return_pct": "2.0",
                }
            ],
            [
                {
                    "as_of_date": "2025-04-01",
                    "signal_date": "2025-03-31",
                    "reason": "unit_proxy",
                    "target_weights": "AAA:1.0",
                }
            ],
            {
                "AAA": [
                    Candle("2025-03-30", 100, 100, 100, 100, 10_000),
                    Candle("2025-03-31", 100, 100, 100, 100, 10_000),
                    Candle("2025-04-01", 100, 100, 100, 100, 10_000),
                    Candle("2025-04-30", 90, 90, 90, 90, 10_000),
                ],
                "BBB": [
                    Candle("2025-03-30", 100, 100, 100, 100, 5_000),
                    Candle("2025-03-31", 100, 100, 100, 100, 5_000),
                    Candle("2025-04-01", 100, 100, 100, 100, 5_000),
                    Candle("2025-04-30", 150, 150, 150, 150, 5_000),
                ],
            },
            config=MonthlyRebalanceConfig(
                market_beta_proxy_size=1,
                point_in_time_liquidity_window_days=2,
            ),
            scenario="regime_sideways",
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["liquidity_rank"], "1")
        self.assertEqual(by_symbol["AAA"]["selection_diagnostic"], "selected_proxy_loser")
        self.assertEqual(by_symbol["BBB"]["contribution_diagnostic"], "missed_benchmark_winner")
        self.assertEqual(by_symbol["BBB"]["liquidity_rank"], "2")
        self.assertEqual(by_symbol["BBB"]["proxy_cutoff_rank"], "1")
        self.assertEqual(by_symbol["BBB"]["rank_gap_to_proxy_cutoff"], "1")
        self.assertEqual(
            by_symbol["BBB"]["selection_diagnostic"],
            "missed_outside_proxy_liquidity_cutoff",
        )

    def test_save_monthly_benchmark_selection_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_selection.csv"
            saved = save_monthly_benchmark_selection(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-04",
                        "symbol": "BBB",
                        "liquidity_rank": "2",
                        "selection_diagnostic": "missed_outside_proxy_liquidity_cutoff",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("liquidity_rank", text.splitlines()[0])
        self.assertIn("missed_outside_proxy_liquidity_cutoff", text)

    def test_analyze_monthly_benchmark_selection_summary_buckets_monthly_missed_winner_drag(self):
        rows = analyze_monthly_benchmark_selection_summary(
            [
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "AAA",
                    "strategy_weight": "0.08",
                    "liquidity_rank": "1",
                    "contribution_delta_pct": "0.5",
                    "contribution_diagnostic": "positive_contribution_delta",
                    "selection_diagnostic": "selected_proxy_winner",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "BBB",
                    "strategy_weight": "0.08",
                    "liquidity_rank": "2",
                    "contribution_delta_pct": "-0.4",
                    "contribution_diagnostic": "overweighted_loser",
                    "selection_diagnostic": "selected_proxy_loser",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "CCC",
                    "strategy_weight": "0",
                    "liquidity_rank": "20",
                    "contribution_delta_pct": "-0.1",
                    "contribution_diagnostic": "missed_benchmark_winner",
                    "selection_diagnostic": "missed_outside_proxy_liquidity_cutoff",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "DDD",
                    "strategy_weight": "0",
                    "liquidity_rank": "80",
                    "contribution_delta_pct": "-0.2",
                    "contribution_diagnostic": "missed_benchmark_winner",
                    "selection_diagnostic": "missed_outside_proxy_liquidity_cutoff",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "EEE",
                    "strategy_weight": "0",
                    "liquidity_rank": "650",
                    "contribution_delta_pct": "-0.7",
                    "contribution_diagnostic": "missed_benchmark_winner",
                    "selection_diagnostic": "missed_outside_proxy_liquidity_cutoff",
                },
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-17",
                    "symbol": "FFF",
                    "strategy_weight": "0",
                    "liquidity_rank": "700",
                    "contribution_delta_pct": "0.05",
                    "contribution_diagnostic": "avoided_benchmark_loser",
                    "selection_diagnostic": "avoided_benchmark_loser",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "regime_sideways")
        self.assertEqual(row["month"], "2025-04")
        self.assertEqual(row["row_count"], "6")
        self.assertEqual(row["selected_proxy_winner_count"], "1")
        self.assertEqual(row["selected_proxy_loser_count"], "1")
        self.assertEqual(row["selected_proxy_delta_pct"], "0.1")
        self.assertEqual(row["missed_benchmark_winner_count"], "3")
        self.assertEqual(row["missed_benchmark_winner_delta_pct"], "-1")
        self.assertEqual(row["missed_rank_13_50_count"], "1")
        self.assertEqual(row["missed_rank_13_50_delta_pct"], "-0.1")
        self.assertEqual(row["missed_rank_51_100_count"], "1")
        self.assertEqual(row["missed_rank_51_100_delta_pct"], "-0.2")
        self.assertEqual(row["missed_rank_501_plus_count"], "1")
        self.assertEqual(row["missed_rank_501_plus_delta_pct"], "-0.7")
        self.assertEqual(row["low_liquidity_missed_winner_delta_share"], "0.7")
        self.assertEqual(row["avoided_benchmark_loser_count"], "1")
        self.assertEqual(row["avoided_benchmark_loser_delta_pct"], "0.05")
        self.assertEqual(row["diagnostic"], "low_liquidity_recovery_drag")

    def test_save_monthly_benchmark_selection_summary_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_selection_summary.csv"
            saved = save_monthly_benchmark_selection_summary(
                [
                    {
                        "scenario": "regime_sideways",
                        "month": "2025-04",
                        "missed_benchmark_winner_count": "3",
                        "low_liquidity_missed_winner_delta_share": "0.7",
                        "diagnostic": "low_liquidity_recovery_drag",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("low_liquidity_missed_winner_delta_share", text.splitlines()[0])
        self.assertIn("low_liquidity_recovery_drag", text)

    def test_compare_monthly_benchmark_selection_summary_reports_flags_shared_low_liquidity_drag(self):
        rows = compare_monthly_benchmark_selection_summary_reports(
            [
                {
                    "scenario": "regime_sideways",
                    "month": "2025-04",
                    "selected_proxy_count": "12",
                    "selected_proxy_winner_count": "6",
                    "selected_proxy_loser_count": "6",
                    "selected_proxy_delta_pct": "-0.3",
                    "missed_benchmark_winner_delta_pct": "-6.8",
                    "missed_rank_501_plus_delta_pct": "-5.3",
                    "low_liquidity_missed_winner_delta_share": "0.78",
                    "diagnostic": "low_liquidity_recovery_drag",
                },
                {
                    "scenario": "walk_forward_001",
                    "month": "2025-04",
                    "selected_proxy_count": "12",
                    "selected_proxy_winner_count": "8",
                    "selected_proxy_loser_count": "4",
                    "selected_proxy_delta_pct": "1.1",
                    "missed_benchmark_winner_delta_pct": "-2.0",
                    "missed_rank_501_plus_delta_pct": "-1.4",
                    "low_liquidity_missed_winner_delta_share": "0.70",
                    "diagnostic": "low_liquidity_recovery_drag",
                },
            ],
            [
                {
                    "name": "regime_sideways",
                    "deployable": "False",
                    "reason": "negative_excess_return",
                    "excess_return_pct": "-4.0548",
                    "max_drawdown_pct": "-21.7902",
                },
                {
                    "name": "walk_forward_001",
                    "deployable": "True",
                    "reason": "passed",
                    "excess_return_pct": "3.0038",
                    "max_drawdown_pct": "-21.5789",
                },
            ],
        )

        by_scenario = {row["scenario"]: row for row in rows}
        failed = by_scenario["regime_sideways"]
        passed = by_scenario["walk_forward_001"]
        self.assertEqual(failed["deployable"], "False")
        self.assertEqual(failed["month_count"], "1")
        self.assertEqual(failed["low_liquidity_drag_month_count"], "1")
        self.assertEqual(failed["selected_proxy_count"], "12")
        self.assertEqual(failed["selected_proxy_winner_count"], "6")
        self.assertEqual(failed["selected_proxy_loser_count"], "6")
        self.assertEqual(failed["selected_proxy_loser_share"], "0.5")
        self.assertEqual(failed["missed_benchmark_winner_delta_pct"], "-6.8")
        self.assertEqual(failed["missed_rank_501_plus_delta_pct"], "-5.3")
        self.assertEqual(failed["low_liquidity_missed_winner_delta_share"], "0.7794")
        self.assertEqual(failed["selected_proxy_delta_per_selected_pct"], "-0.025")
        self.assertEqual(failed["negative_selected_proxy_month_count"], "1")
        self.assertEqual(failed["worst_selected_proxy_month"], "2025-04")
        self.assertEqual(failed["worst_selected_proxy_delta_pct"], "-0.3")
        self.assertEqual(failed["worst_missed_month"], "2025-04")
        self.assertEqual(
            failed["diagnostic"],
            "failed_with_shared_low_liquidity_recovery_drag",
        )
        self.assertEqual(passed["deployable"], "True")
        self.assertEqual(passed["selected_proxy_delta_per_selected_pct"], "0.0917")
        self.assertEqual(passed["negative_selected_proxy_month_count"], "0")
        self.assertEqual(passed["diagnostic"], "passed_despite_low_liquidity_recovery_drag")

    def test_save_monthly_benchmark_selection_summary_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_selection_compare.csv"
            saved = save_monthly_benchmark_selection_summary_comparison(
                [
                    {
                        "scenario": "regime_sideways",
                        "deployable": "False",
                        "diagnostic": "failed_with_shared_low_liquidity_recovery_drag",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("selected_proxy_delta_per_selected_pct", text.splitlines()[0])
        self.assertIn("low_liquidity_missed_winner_delta_share", text.splitlines()[0])
        self.assertIn("failed_with_shared_low_liquidity_recovery_drag", text)

    def test_compare_monthly_benchmark_selection_window_reports_splits_pre_window_drag(self):
        selection_rows = [
            {
                "scenario": "regime_sideways",
                "month": "2024-12",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "-2",
                "missed_benchmark_winner_delta_pct": "-4",
            },
            {
                "scenario": "regime_sideways",
                "month": "2025-01",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "1",
                "missed_benchmark_winner_delta_pct": "-2",
            },
            {
                "scenario": "regime_sideways",
                "month": "2025-02",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "-1",
                "missed_benchmark_winner_delta_pct": "-1",
            },
            {
                "scenario": "walk_forward_001",
                "month": "2025-01",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "1",
                "missed_benchmark_winner_delta_pct": "-2",
            },
            {
                "scenario": "walk_forward_001",
                "month": "2025-02",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "-1",
                "missed_benchmark_winner_delta_pct": "-1",
            },
            {
                "scenario": "failed_overlap_drag",
                "month": "2025-01",
                "selected_proxy_count": "10",
                "selected_proxy_delta_pct": "0",
                "missed_benchmark_winner_delta_pct": "-3",
            },
        ]
        benchmark_rows = [
            {
                "scenario": "regime_sideways",
                "month": "2024-12",
                "start_date": "2024-12-02",
                "end_date": "2024-12-31",
                "strategy_return_pct": "-5",
                "benchmark_return_pct": "0",
            },
            {
                "scenario": "regime_sideways",
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "strategy_return_pct": "10",
                "benchmark_return_pct": "5",
            },
            {
                "scenario": "regime_sideways",
                "month": "2025-02",
                "start_date": "2025-02-03",
                "end_date": "2025-02-28",
                "strategy_return_pct": "-2",
                "benchmark_return_pct": "0",
            },
            {
                "scenario": "walk_forward_001",
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "strategy_return_pct": "10",
                "benchmark_return_pct": "5",
            },
            {
                "scenario": "walk_forward_001",
                "month": "2025-02",
                "start_date": "2025-02-03",
                "end_date": "2025-02-28",
                "strategy_return_pct": "-2",
                "benchmark_return_pct": "0",
            },
            {
                "scenario": "failed_overlap_drag",
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "strategy_return_pct": "-2",
                "benchmark_return_pct": "2",
            },
        ]
        rows = compare_monthly_benchmark_selection_window_reports(
            selection_rows,
            benchmark_rows,
            [
                {"name": "regime_sideways", "deployable": "False", "reason": "negative_excess_return"},
                {"name": "walk_forward_001", "deployable": "True", "reason": "passed"},
                {"name": "failed_overlap_drag", "deployable": "False", "reason": "negative_excess_return"},
            ],
            window_start_month="2025-01",
            window_end_month="2025-02",
        )

        by_key = {(row["scenario"], row["window"]): row for row in rows}
        failed_pre = by_key[("regime_sideways", "pre_window")]
        failed_window = by_key[("regime_sideways", "window")]
        passed_window = by_key[("walk_forward_001", "window")]
        self.assertEqual(failed_pre["deployable"], "False")
        self.assertEqual(failed_pre["month_count"], "1")
        self.assertEqual(failed_pre["window_start_date"], "2024-12-02")
        self.assertEqual(failed_pre["window_end_date"], "2024-12-31")
        self.assertEqual(failed_pre["strategy_return_pct"], "-5")
        self.assertEqual(failed_pre["window_excess_return_pct"], "-5")
        self.assertEqual(failed_pre["selected_proxy_delta_pct"], "-2")
        self.assertEqual(failed_pre["diagnostic"], "failed_pre_window_excess_drag")
        self.assertEqual(failed_window["strategy_return_pct"], "7.8")
        self.assertEqual(failed_window["window_start_date"], "2025-01-02")
        self.assertEqual(failed_window["window_excess_return_pct"], "2.8")
        self.assertEqual(failed_window["selected_proxy_delta_pct"], "0")
        self.assertEqual(failed_window["diagnostic"], "failed_window_not_primary_drag")
        self.assertEqual(passed_window["strategy_return_pct"], "7.8")
        self.assertEqual(passed_window["window_start_date"], "2025-01-14")
        self.assertEqual(
            by_key[("failed_overlap_drag", "window")]["diagnostic"],
            "failed_window_excess_drag",
        )
        self.assertNotIn(("walk_forward_001", "pre_window"), by_key)

    def test_save_monthly_benchmark_selection_window_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "benchmark_selection_windows.csv"
            saved = save_monthly_benchmark_selection_window_comparison(
                [
                    {
                        "scenario": "regime_sideways",
                        "window": "pre_window",
                        "diagnostic": "failed_pre_window_excess_drag",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("window_start_date", text.splitlines()[0])
        self.assertIn("window_excess_return_pct", text.splitlines()[0])
        self.assertIn("failed_pre_window_excess_drag", text)

    def test_compare_monthly_entry_month_reports_flags_date_excess_and_holdings_gap(self):
        rows = compare_monthly_entry_month_reports(
            [{"month": "2025-01", "start_date": "2025-01-02", "end_date": "2025-01-31", "strategy_return_pct": "2", "benchmark_return_pct": "4", "monthly_excess_return_pct": "-2"}],
            [{"month": "2025-01", "start_date": "2025-01-14", "end_date": "2025-01-31", "strategy_return_pct": "8", "benchmark_return_pct": "-1", "monthly_excess_return_pct": "9"}],
            [{"month": "2025-01", "selected_proxy_delta_pct": "1", "missed_benchmark_winner_delta_pct": "-5"}],
            [{"month": "2025-01", "selected_proxy_delta_pct": "7", "missed_benchmark_winner_delta_pct": "-2"}],
            [
                {
                    "as_of_date": "2025-01-02",
                    "signal_date": "2024-12-30",
                    "target_exposure": "0.2475",
                    "cash_weight": "0.7525",
                    "selected_symbols": "AAA;BBB;CCC",
                    "reason": "weak_train_neutral_breadth_proxy_trend_scaled",
                }
            ],
            [
                {
                    "as_of_date": "2025-01-14",
                    "signal_date": "2025-01-13",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "selected_symbols": "AAA;DDD;EEE",
                    "reason": "no_train_candidate_strong_breadth_proxy",
                }
            ],
            failed_label="regime_sideways",
            reference_label="walk_forward_001",
            month="2025-01",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["failed_label"], "regime_sideways")
        self.assertEqual(row["reference_label"], "walk_forward_001")
        self.assertEqual(row["start_date_delta_days"], "12")
        self.assertEqual(row["monthly_excess_delta"], "11")
        self.assertEqual(row["selected_proxy_delta_delta"], "6")
        self.assertEqual(row["target_exposure_delta"], "0.7425")
        self.assertEqual(row["cash_weight_delta"], "-0.7425")
        self.assertEqual(row["shared_symbol_count"], "1")
        self.assertEqual(row["failed_only_symbols"], "BBB;CCC")
        self.assertEqual(row["reference_only_symbols"], "DDD;EEE")
        self.assertIn("entry_date_mismatch", row["diagnostic"])
        self.assertIn("reference_excess_better", row["diagnostic"])
        self.assertIn("reference_exposure_higher", row["diagnostic"])
        self.assertIn("symbol_rotation", row["diagnostic"])

    def test_save_monthly_entry_month_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "entry_month.csv"
            saved = save_monthly_entry_month_comparison(
                [
                    {
                        "month": "2025-01",
                        "failed_label": "regime_sideways",
                        "diagnostic": "entry_date_mismatch",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("start_date_delta_days", text.splitlines()[0])
        self.assertIn("entry_date_mismatch", text)

    def test_compare_monthly_entry_path_subperiod_reports_splits_timing_and_exposure(self):
        failed_path_rows = [
            {"date": "2025-01-02", "equity": "100", "exposure": "0.25", "position_symbols": "AAA;BBB"},
            {"date": "2025-01-13", "equity": "102", "exposure": "0.25", "position_symbols": "AAA;BBB"},
            {"date": "2025-01-14", "equity": "102", "exposure": "0.3", "position_symbols": "AAA;BBB"},
            {"date": "2025-01-31", "equity": "103.02", "exposure": "0.3", "position_symbols": "AAA;BBB"},
        ]
        reference_path_rows = [
            {"date": "2025-01-14", "equity": "100", "exposure": "0.9", "position_symbols": "AAA;CCC"},
            {"date": "2025-01-31", "equity": "108", "exposure": "0.9", "position_symbols": "AAA;CCC"},
        ]

        rows = compare_monthly_entry_path_subperiod_reports(
            failed_path_rows,
            reference_path_rows,
            failed_label="regime_sideways",
            reference_label="walk_forward_001",
            month_start="2025-01-02",
            month_end="2025-01-31",
            split_date="2025-01-14",
        )

        by_role = {row["subperiod"]: row for row in rows}
        self.assertEqual(by_role["failed_pre_split"]["return_pct"], "2")
        self.assertEqual(by_role["failed_pre_split"]["average_exposure"], "0.25")
        self.assertEqual(by_role["failed_post_split"]["return_pct"], "1")
        self.assertEqual(by_role["failed_post_split"]["average_exposure"], "0.3")
        self.assertEqual(by_role["reference_post_split"]["return_pct"], "8")
        self.assertEqual(by_role["failed_post_split"]["return_delta_vs_reference_post"], "-7")
        self.assertEqual(by_role["failed_post_split"]["average_exposure_delta_vs_reference_post"], "-0.6")
        self.assertEqual(by_role["failed_post_split"]["shared_with_reference_post_symbol_count"], "1")
        self.assertEqual(by_role["failed_post_split"]["only_symbols_vs_reference_post"], "BBB")
        self.assertEqual(by_role["failed_post_split"]["reference_only_symbols"], "CCC")
        self.assertIn("reference_post_outperformed", by_role["failed_post_split"]["diagnostic"])
        self.assertIn("reference_exposure_higher", by_role["failed_post_split"]["diagnostic"])
        self.assertIn("symbol_rotation", by_role["failed_post_split"]["diagnostic"])

    def test_save_monthly_entry_path_subperiod_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "entry_path_subperiod.csv"
            saved = save_monthly_entry_path_subperiod_comparison(
                [
                    {
                        "subperiod": "failed_post_split",
                        "diagnostic": "reference_post_outperformed",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("return_delta_vs_reference_post", text.splitlines()[0])
        self.assertIn("reference_post_outperformed", text)

    def test_compare_monthly_entry_contribution_overlap_reports_splits_shared_and_rotation_gap(self):
        failed_rows = [
            {
                "scenario": "regime_sideways",
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "symbol": "AAA",
                "strategy_weight": "0.2",
                "strategy_contribution_pct": "2.0",
            },
            {
                "scenario": "regime_sideways",
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "symbol": "BBB",
                "strategy_weight": "0.1",
                "strategy_contribution_pct": "2.0",
            },
        ]
        reference_rows = [
            {
                "scenario": "walk_forward_001",
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "symbol": "AAA",
                "strategy_weight": "0.4",
                "strategy_contribution_pct": "4.0",
            },
            {
                "scenario": "walk_forward_001",
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "symbol": "CCC",
                "strategy_weight": "0.3",
                "strategy_contribution_pct": "9.0",
            },
        ]

        rows = compare_monthly_entry_contribution_overlap_reports(
            failed_rows,
            reference_rows,
            failed_label="regime_sideways",
            reference_label="walk_forward_001",
            month="2025-01",
        )

        by_bucket = {row["bucket"]: row for row in rows}
        self.assertEqual(by_bucket["selected_total"]["failed_strategy_weight"], "0.3")
        self.assertEqual(by_bucket["selected_total"]["reference_strategy_weight"], "0.7")
        self.assertEqual(by_bucket["selected_total"]["contribution_delta_pct"], "9")
        self.assertIn("rotation_gap_dominant", by_bucket["selected_total"]["diagnostic"])
        self.assertEqual(by_bucket["shared_symbols"]["failed_symbols"], "AAA")
        self.assertEqual(by_bucket["shared_symbols"]["reference_symbols"], "AAA")
        self.assertEqual(by_bucket["shared_symbols"]["contribution_delta_pct"], "2")
        self.assertEqual(by_bucket["shared_symbols"]["contribution_gap_share_pct"], "22.2222")
        self.assertEqual(by_bucket["rotation_symbols"]["failed_symbols"], "BBB")
        self.assertEqual(by_bucket["rotation_symbols"]["reference_symbols"], "CCC")
        self.assertEqual(by_bucket["rotation_symbols"]["contribution_delta_pct"], "7")
        self.assertEqual(by_bucket["rotation_symbols"]["contribution_gap_share_pct"], "77.7778")

    def test_save_monthly_entry_contribution_overlap_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "entry_contribution_overlap.csv"
            saved = save_monthly_entry_contribution_overlap_comparison(
                [
                    {
                        "bucket": "rotation_symbols",
                        "diagnostic": "rotation_gap_dominant",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("contribution_gap_share_pct", text.splitlines()[0])
        self.assertIn("rotation_gap_dominant", text)

    def test_compare_monthly_entry_selection_rotation_reports_explains_rotated_symbols(self):
        failed_rows = [
            {
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-02",
                "decision_reason": "weak_train",
                "symbol": "AAA",
                "strategy_weight": "0.2",
                "symbol_return_pct": "10",
                "contribution_delta_pct": "1.8",
                "liquidity_rank": "5",
                "selection_diagnostic": "selected_proxy_winner",
            },
            {
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-02",
                "decision_reason": "weak_train",
                "symbol": "BBB",
                "strategy_weight": "0.1",
                "symbol_return_pct": "-5",
                "contribution_delta_pct": "-0.6",
                "liquidity_rank": "40",
                "selection_diagnostic": "selected_proxy_loser",
            },
            {
                "month": "2025-01",
                "start_date": "2025-01-02",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-02",
                "decision_reason": "weak_train",
                "symbol": "CCC",
                "strategy_weight": "0",
                "symbol_return_pct": "20",
                "contribution_delta_pct": "-0.02",
                "liquidity_rank": "35",
                "selection_diagnostic": "missed_inside_proxy_cutoff",
            },
        ]
        reference_rows = [
            {
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-14",
                "decision_reason": "strong_breadth",
                "symbol": "AAA",
                "strategy_weight": "0.4",
                "symbol_return_pct": "12",
                "contribution_delta_pct": "4.7",
                "liquidity_rank": "3",
                "selection_diagnostic": "selected_proxy_winner",
            },
            {
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-14",
                "decision_reason": "strong_breadth",
                "symbol": "BBB",
                "strategy_weight": "0",
                "symbol_return_pct": "-4",
                "contribution_delta_pct": "-0.01",
                "liquidity_rank": "44",
                "selection_diagnostic": "avoided_benchmark_loser",
            },
            {
                "month": "2025-01",
                "start_date": "2025-01-14",
                "end_date": "2025-01-31",
                "decision_as_of_date": "2025-01-14",
                "decision_reason": "strong_breadth",
                "symbol": "CCC",
                "strategy_weight": "0.3",
                "symbol_return_pct": "30",
                "contribution_delta_pct": "8.9",
                "liquidity_rank": "7",
                "selection_diagnostic": "selected_proxy_winner",
            },
        ]

        rows = compare_monthly_entry_selection_rotation_reports(
            failed_rows,
            reference_rows,
            failed_label="regime_sideways",
            reference_label="walk_forward_001",
            month="2025-01",
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["rotation_role"], "shared_symbols")
        self.assertEqual(by_symbol["AAA"]["strategy_weight_delta"], "0.2")
        self.assertEqual(by_symbol["AAA"]["symbol_return_delta"], "2")
        self.assertEqual(by_symbol["BBB"]["rotation_role"], "failed_only_symbols")
        self.assertEqual(by_symbol["BBB"]["failed_selected"], "true")
        self.assertEqual(by_symbol["BBB"]["reference_selected"], "false")
        self.assertIn("failed_selected_only", by_symbol["BBB"]["diagnostic"])
        self.assertIn("failed_selected_loser", by_symbol["BBB"]["diagnostic"])
        self.assertEqual(by_symbol["CCC"]["rotation_role"], "reference_only_symbols")
        self.assertEqual(by_symbol["CCC"]["failed_selected"], "false")
        self.assertEqual(by_symbol["CCC"]["reference_selected"], "true")
        self.assertEqual(by_symbol["CCC"]["contribution_delta_gap_pct"], "8.92")
        self.assertEqual(by_symbol["CCC"]["liquidity_rank_delta"], "-28")
        self.assertIn("reference_selected_only", by_symbol["CCC"]["diagnostic"])
        self.assertIn("reference_contribution_higher", by_symbol["CCC"]["diagnostic"])
        self.assertIn("reference_liquidity_rank_better", by_symbol["CCC"]["diagnostic"])

    def test_save_monthly_entry_selection_rotation_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "entry_selection_rotation.csv"
            saved = save_monthly_entry_selection_rotation_comparison(
                [
                    {
                        "symbol": "CCC",
                        "rotation_role": "reference_only_symbols",
                        "diagnostic": "reference_selected_only",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("symbol_return_delta", text.splitlines()[0])
        self.assertIn("reference_selected_only", text)

    def test_compare_monthly_entry_selection_eligibility_reports_joins_filter_reasons(self):
        rotation_rows = [
            {
                "symbol": "CCC",
                "rotation_role": "reference_only_symbols",
                "failed_selected": "false",
                "reference_selected": "true",
                "failed_signal_date": "2025-01-02",
                "reference_signal_date": "2025-01-14",
                "failed_selection_diagnostic": "missed_inside_proxy_liquidity_cutoff",
                "reference_selection_diagnostic": "selected_proxy_winner",
                "contribution_delta_gap_pct": "8.92",
            },
            {
                "symbol": "BBB",
                "rotation_role": "failed_only_symbols",
                "failed_selected": "true",
                "reference_selected": "false",
                "failed_signal_date": "2025-01-02",
                "reference_signal_date": "2025-01-14",
                "failed_selection_diagnostic": "selected_proxy_loser",
                "reference_selection_diagnostic": "avoided_benchmark_loser",
                "contribution_delta_gap_pct": "-0.5",
            },
        ]
        universe_filter_rows = [
            {
                "as_of_date": "2025-01-02",
                "symbol": "CCC",
                "status": "EXCLUDED",
                "reason": "insufficient_history",
                "detail": "history_rows=244; required=252",
            }
        ]

        rows = compare_monthly_entry_selection_eligibility_reports(
            rotation_rows,
            universe_filter_rows,
            failed_label="regime_sideways",
            reference_label="walk_forward_001",
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["CCC"]["failed_universe_status"], "EXCLUDED")
        self.assertEqual(by_symbol["CCC"]["failed_universe_reason"], "insufficient_history")
        self.assertEqual(by_symbol["CCC"]["reference_universe_status"], "INCLUDED")
        self.assertIn("failed_universe_insufficient_history", by_symbol["CCC"]["diagnostic"])
        self.assertIn("reference_selected_after_failed_exclusion", by_symbol["CCC"]["diagnostic"])
        self.assertEqual(by_symbol["BBB"]["failed_universe_status"], "INCLUDED")
        self.assertEqual(by_symbol["BBB"]["reference_universe_status"], "INCLUDED")

    def test_save_monthly_entry_selection_eligibility_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "entry_selection_eligibility.csv"
            saved = save_monthly_entry_selection_eligibility_comparison(
                [
                    {
                        "symbol": "CCC",
                        "diagnostic": "failed_universe_insufficient_history",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("failed_universe_reason", text.splitlines()[0])
        self.assertIn("failed_universe_insufficient_history", text)

    def test_save_monthly_attribution_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "monthly.csv"
            saved = save_monthly_attribution_rows(
                [
                    {
                        "month": "2024-02",
                        "start_date": "2024-02-01",
                        "end_date": "2024-02-29",
                        "start_equity": "1000",
                        "end_equity": "920",
                        "equity_change": "-80",
                        "return_pct": "-8",
                        "worst_equity": "920",
                        "worst_drawdown_pct": "-12.381",
                        "status": "LOSS",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("worst_drawdown_pct", text.splitlines()[0])
        self.assertIn("LOSS", text)

    def test_compare_monthly_attribution_reports_flags_new_drawdown_breach(self):
        rows = compare_monthly_attribution_reports(
            [
                {
                    "month": "2026-02",
                    "return_pct": "8",
                    "equity_change": "800",
                    "worst_drawdown_pct": "-10",
                    "status": "GAIN",
                },
                {
                    "month": "2026-03",
                    "return_pct": "-18",
                    "equity_change": "-1800",
                    "worst_drawdown_pct": "-24.0",
                    "status": "LOSS",
                },
            ],
            [
                {
                    "month": "2026-02",
                    "return_pct": "7",
                    "equity_change": "700",
                    "worst_drawdown_pct": "-11",
                    "status": "GAIN",
                },
                {
                    "month": "2026-03",
                    "return_pct": "-20",
                    "equity_change": "-2100",
                    "worst_drawdown_pct": "-25.2",
                    "status": "LOSS",
                },
            ],
            scenario="full_period",
            candidate_label="neutral_cap",
            drawdown_threshold_pct=-25.0,
        )

        by_month = {row["month"]: row for row in rows}
        self.assertEqual(by_month["2026-03"]["scenario"], "full_period")
        self.assertEqual(by_month["2026-03"]["candidate_label"], "neutral_cap")
        self.assertEqual(by_month["2026-03"]["return_delta_pct"], "-2")
        self.assertEqual(by_month["2026-03"]["equity_change_delta"], "-300")
        self.assertEqual(by_month["2026-03"]["drawdown_delta_pct"], "-1.2")
        self.assertEqual(by_month["2026-03"]["candidate_crossed_drawdown_threshold"], "True")
        self.assertEqual(by_month["2026-03"]["diagnostic"], "new_drawdown_breach")
        self.assertEqual(by_month["2026-02"]["diagnostic"], "drawdown_regression")

    def test_save_monthly_attribution_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "attribution_compare.csv"
            saved = save_monthly_attribution_comparison(
                [
                    {
                        "scenario": "unit",
                        "month": "2026-03",
                        "diagnostic": "new_drawdown_breach",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("candidate_crossed_drawdown_threshold", text.splitlines()[0])
        self.assertIn("new_drawdown_breach", text)

    def test_compare_monthly_decision_attribution_reports_flags_exposure_and_symbol_rotation(self):
        rows = compare_monthly_decision_attribution_reports(
            [
                {
                    "as_of_date": "2025-03-31",
                    "signal_date": "2025-03-28",
                    "mode": "market_beta_proxy",
                    "selected_preset": "balanced",
                    "selected_symbols": "AAA;BBB;CCC",
                    "target_exposure": "0.99",
                    "cash_weight": "0.01",
                    "position_count": "3",
                    "reason": "baseline_high_exposure",
                }
            ],
            [
                {
                    "as_of_date": "2025-03-31",
                    "signal_date": "2025-03-28",
                    "mode": "market_beta_proxy",
                    "selected_preset": "balanced",
                    "selected_symbols": "AAA;DDD",
                    "target_exposure": "0.5",
                    "cash_weight": "0.5",
                    "position_count": "2",
                    "reason": "neutral_breadth_proxy_cap",
                }
            ],
            scenario="full_period",
            candidate_label="neutral_cap",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "full_period")
        self.assertEqual(row["candidate_label"], "neutral_cap")
        self.assertEqual(row["month"], "2025-03")
        self.assertEqual(row["target_exposure_delta"], "-0.49")
        self.assertEqual(row["cash_weight_delta"], "0.49")
        self.assertEqual(row["position_count_delta"], "-1")
        self.assertEqual(row["shared_symbol_count"], "1")
        self.assertEqual(row["baseline_only_symbols"], "BBB;CCC")
        self.assertEqual(row["candidate_only_symbols"], "DDD")
        self.assertIn("exposure_reduced", row["diagnostic"])
        self.assertIn("cash_increased", row["diagnostic"])
        self.assertIn("symbol_rotation", row["diagnostic"])
        self.assertIn("reason_changed", row["diagnostic"])

    def test_save_monthly_decision_attribution_comparison_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "decision_compare.csv"
            saved = save_monthly_decision_attribution_comparison(
                [
                    {
                        "scenario": "unit",
                        "as_of_date": "2025-03-31",
                        "diagnostic": "exposure_reduced;symbol_rotation",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("target_exposure_delta", text.splitlines()[0])
        self.assertIn("symbol_rotation", text)

    def test_analyze_monthly_path_attribution_reconstructs_cash_positions_turnover_and_cost(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=950,
            total_return_pct=-5.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=-5.0,
            max_drawdown_pct=-5.0,
            trade_count=2,
            decisions=[],
            trades=[
                MonthlyBacktestTrade("2025-03-03", "AAA", "BUY", 100, 5, 499.5, "entry"),
                MonthlyBacktestTrade("2025-03-04", "AAA", "SELL", 90, 2, 679.0, "trim"),
            ],
            dates=["2025-03-03", "2025-03-04"],
            equity_curve=[1_000, 950],
        )

        rows = analyze_monthly_path_attribution(
            result,
            fee_rate=0.001,
            tax_rate=0.002,
            start="2025-03-03",
            end="2025-03-04",
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "2025-03-03")
        self.assertEqual(rows[0]["cash"], "499.5")
        self.assertEqual(rows[0]["position_symbols"], "AAA")
        self.assertEqual(rows[0]["position_quantities"], "AAA:5")
        self.assertEqual(rows[0]["buy_value"], "500")
        self.assertEqual(rows[0]["estimated_trade_cost"], "0.5")
        self.assertEqual(rows[1]["rolling_peak"], "1000")
        self.assertEqual(rows[1]["position_quantities"], "AAA:3")
        self.assertEqual(rows[1]["sell_value"], "180")
        self.assertEqual(rows[1]["estimated_trade_cost"], "0.54")
        self.assertEqual(rows[1]["drawdown_pct"], "-5")
        self.assertEqual(rows[1]["daily_return_pct"], "-5")

    def test_compare_monthly_path_attribution_reports_flags_equity_and_holding_path_regression(self):
        rows = compare_monthly_path_attribution_reports(
            [
                {
                    "date": "2025-03-04",
                    "equity": "1000",
                    "drawdown_pct": "-5",
                    "cash": "200",
                    "rolling_peak": "1100",
                    "exposure": "0.8",
                    "position_count": "2",
                    "total_position_quantity": "12",
                    "position_symbols": "AAA;BBB",
                    "turnover_value": "100",
                    "estimated_trade_cost": "0.1",
                }
            ],
            [
                {
                    "date": "2025-03-04",
                    "equity": "980",
                    "drawdown_pct": "-7",
                    "cash": "392",
                    "rolling_peak": "1150",
                    "exposure": "0.6",
                    "position_count": "2",
                    "total_position_quantity": "10",
                    "position_symbols": "AAA;CCC",
                    "turnover_value": "200",
                    "estimated_trade_cost": "0.2",
                }
            ],
            scenario="full_period",
            candidate_label="neutral_cap",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "full_period")
        self.assertEqual(row["equity_delta"], "-20")
        self.assertEqual(row["drawdown_delta_pct"], "-2")
        self.assertEqual(row["cash_delta"], "192")
        self.assertEqual(row["rolling_peak_delta"], "50")
        self.assertEqual(row["exposure_delta"], "-0.2")
        self.assertEqual(row["total_position_quantity_delta"], "-2")
        self.assertEqual(row["baseline_only_symbols"], "BBB")
        self.assertEqual(row["candidate_only_symbols"], "CCC")
        self.assertEqual(row["turnover_delta"], "100")
        self.assertEqual(row["estimated_trade_cost_delta"], "0.1")
        self.assertIn("equity_regression", row["diagnostic"])
        self.assertIn("drawdown_regression", row["diagnostic"])
        self.assertIn("symbol_rotation", row["diagnostic"])
        self.assertIn("higher_turnover", row["diagnostic"])
        self.assertIn("higher_trade_cost", row["diagnostic"])

    def test_summarize_monthly_path_attribution_comparison_groups_regression_days(self):
        rows = summarize_monthly_path_attribution_comparison(
            [
                {
                    "scenario": "regime_sideways",
                    "candidate_label": "neutral_cap",
                    "date": "2025-03-03",
                    "equity_delta": "-120",
                    "drawdown_delta_pct": "-1.5",
                    "exposure_delta": "-0.20",
                    "cash_delta": "120",
                    "turnover_delta": "50",
                    "estimated_trade_cost_delta": "0.5",
                    "diagnostic": "equity_regression;drawdown_regression;exposure_reduced;symbol_rotation",
                },
                {
                    "scenario": "regime_sideways",
                    "candidate_label": "neutral_cap",
                    "date": "2025-03-04",
                    "equity_delta": "40",
                    "drawdown_delta_pct": "0.5",
                    "exposure_delta": "-0.10",
                    "cash_delta": "80",
                    "turnover_delta": "0",
                    "estimated_trade_cost_delta": "0",
                    "diagnostic": "equity_improved;drawdown_improved;exposure_reduced",
                },
                {
                    "scenario": "regime_sideways",
                    "candidate_label": "neutral_cap",
                    "date": "2025-04-01",
                    "equity_delta": "-20",
                    "drawdown_delta_pct": "0.1",
                    "exposure_delta": "0.05",
                    "cash_delta": "-30",
                    "turnover_delta": "10",
                    "estimated_trade_cost_delta": "0.1",
                    "diagnostic": "equity_regression;exposure_increased",
                },
            ]
        )

        by_month = {row["month"]: row for row in rows}
        march = by_month["2025-03"]
        self.assertEqual(march["day_count"], "2")
        self.assertEqual(march["equity_regression_day_count"], "1")
        self.assertEqual(march["drawdown_regression_day_count"], "1")
        self.assertEqual(march["symbol_rotation_day_count"], "1")
        self.assertEqual(march["avg_exposure_delta"], "-0.15")
        self.assertEqual(march["total_turnover_delta"], "50")
        self.assertEqual(march["worst_equity_delta"], "-120")
        self.assertEqual(march["worst_equity_delta_date"], "2025-03-03")
        self.assertEqual(march["dominant_diagnostic"], "exposure_reduced")
        self.assertEqual(march["paper_only"], "true")

    def test_save_monthly_path_attribution_comparison_summary_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "path_summary.csv"
            saved = save_monthly_path_attribution_comparison_summary(
                [
                    {
                        "scenario": "regime_sideways",
                        "candidate_label": "neutral_cap",
                        "month": "2025-03",
                        "day_count": "2",
                        "equity_regression_day_count": "1",
                        "dominant_diagnostic": "exposure_reduced",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("equity_regression_day_count", text.splitlines()[0])
        self.assertIn("regime_sideways", text)

    def test_save_monthly_path_attribution_reports_write_csv(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path_output = root / "path.csv"
            compare_output = root / "path_compare.csv"
            path_saved = save_monthly_path_attribution(
                [{"date": "2025-03-04", "equity": "980", "diagnostic": "unit"}],
                path_output,
            )
            compare_saved = save_monthly_path_attribution_comparison(
                [{"date": "2025-03-04", "diagnostic": "equity_regression"}],
                compare_output,
            )
            path_text = path_output.read_text(encoding="utf-8")
            compare_text = compare_output.read_text(encoding="utf-8")

        self.assertEqual(path_saved, 1)
        self.assertEqual(compare_saved, 1)
        self.assertIn("rolling_peak", path_text.splitlines()[0])
        self.assertIn("estimated_trade_cost_delta", compare_text.splitlines()[0])
        self.assertIn("equity_regression", compare_text)

    def test_analyze_monthly_execution_gap_flags_target_below_one_share(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000_000,
            final_equity=1_000_000,
            total_return_pct=0.0,
            buy_hold_return_pct=0.0,
            excess_return_pct=0.0,
            max_drawdown_pct=0.0,
            trade_count=1,
            decisions=[
                MonthlyDecision(
                    as_of_date="2026-01-02",
                    signal_date="2026-01-01",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.5, "BIG": 0.4},
                    reason="unit_proxy",
                )
            ],
            trades=[
                MonthlyBacktestTrade("2026-01-02", "AAA", "BUY", 100, 5_000, 499_500, "unit_proxy"),
            ],
            dates=["2026-01-02"],
            equity_curve=[1_000_000],
        )

        rows = analyze_monthly_execution_gap(
            result,
            {
                "AAA": [Candle("2026-01-02", 100, 100, 100, 100, 10_000)],
                "BIG": [Candle("2026-01-02", 600_000, 600_000, 600_000, 600_000, 10_000)],
            },
            scenario="regime_unit",
            min_trade_value=10_000,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "regime_unit")
        self.assertEqual(row["as_of_date"], "2026-01-02")
        self.assertEqual(row["symbol"], "BIG")
        self.assertEqual(row["target_weight"], "0.4")
        self.assertEqual(row["target_value"], "400000")
        self.assertEqual(row["reference_price"], "600000")
        self.assertEqual(row["actual_quantity"], "0")
        self.assertEqual(row["execution_gap"], "missed_target_symbol")
        self.assertEqual(row["diagnostic"], "target_value_below_one_share")
        self.assertEqual(row["paper_only"], "true")

    def test_save_monthly_execution_gap_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "execution_gap.csv"
            saved = save_monthly_execution_gap(
                [
                    {
                        "scenario": "regime_unit",
                        "as_of_date": "2026-01-02",
                        "symbol": "BIG",
                        "execution_gap": "missed_target_symbol",
                        "diagnostic": "target_value_below_one_share",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("execution_gap", text.splitlines()[0])
        self.assertIn("target_value_below_one_share", text)

    def test_analyze_monthly_recovery_attribution_summarizes_exposure_and_loss_symbols(self):
        result = MonthlyBacktestResult(
            initial_cash=1_000,
            final_equity=1_100,
            total_return_pct=10.0,
            buy_hold_return_pct=20.0,
            excess_return_pct=-10.0,
            max_drawdown_pct=-25.0,
            trade_count=4,
            decisions=[
                MonthlyDecision(
                    as_of_date="2026-01-31",
                    signal_date="2026-01-30",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.5, "BBB": 0.49},
                    reason="unit_high_exposure",
                ),
                MonthlyDecision(
                    as_of_date="2026-02-28",
                    signal_date="2026-02-27",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.25, "BBB": 0.25},
                    reason="unit_cash_drag",
                ),
                MonthlyDecision(
                    as_of_date="2026-03-31",
                    signal_date="2026-03-30",
                    mode="market_beta_proxy",
                    selected_preset="market_beta_proxy",
                    target_weights={"AAA": 0.6, "BBB": 0.35},
                    reason="unit_worst_month",
                ),
                MonthlyDecision(
                    as_of_date="2026-04-30",
                    signal_date="2026-04-29",
                    mode="alpha",
                    selected_preset="balanced",
                    target_weights={"CCC": 0.7},
                    reason="unit_recovery",
                ),
            ],
            trades=[
                MonthlyBacktestTrade("2026-01-31", "AAA", "BUY", 100, 5, 500, "entry"),
                MonthlyBacktestTrade("2026-03-31", "AAA", "SELL", 70, 5, 350, "exit"),
                MonthlyBacktestTrade("2026-02-28", "BBB", "BUY", 100, 2, 150, "entry"),
                MonthlyBacktestTrade("2026-04-30", "BBB", "SELL", 110, 2, 370, "exit"),
            ],
            dates=["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
            equity_curve=[1_000, 1_200, 900, 1_100],
        )

        rows = analyze_monthly_recovery_attribution(result, scenario="walk_forward_unit")

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "walk_forward_unit")
        self.assertEqual(row["worst_month"], "2026-03")
        self.assertEqual(row["best_month"], "2026-04")
        self.assertEqual(row["worst_month_target_exposure"], "0.95")
        self.assertEqual(row["best_month_cash_weight"], "0.3")
        self.assertEqual(row["top_loss_symbol"], "AAA")
        self.assertIn("AAA:-150", row["top_loss_symbols"])
        self.assertIn("benchmark_recovered_more", row["diagnostic"])
        self.assertIn("high_exposure_worst_month", row["diagnostic"])
        self.assertIn("cash_drag_best_month", row["diagnostic"])

    def test_save_monthly_recovery_attribution_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "recovery.csv"
            saved = save_monthly_recovery_attribution(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "worst_month": "2026-03",
                        "diagnostic": "high_exposure_worst_month",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,start,end", text.splitlines()[0])
        self.assertIn("high_exposure_worst_month", text)

    def test_deployment_gate_rejects_universe_bias_warning(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": True},
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "universe_bias_warning")

    def test_deployment_gate_accepts_positive_excess_with_controlled_drawdown(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": False},
        )

        self.assertTrue(gate.deployable)
        self.assertEqual(gate.reason, "passed")

    def test_monthly_validation_gate_rejects_any_failed_required_scenario(self):
        gate = build_monthly_validation_gate(
            [
                {"name": "base", "deployable": True, "required": True},
                {"name": "stress_top_winners", "deployable": False, "required": True},
            ],
            source="unit",
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "failed_required_scenarios:stress_top_winners")

    def test_monthly_validation_gate_accepts_when_all_required_scenarios_pass(self):
        gate = build_monthly_validation_gate(
            [
                {"name": "base", "deployable": True, "required": True},
                {"name": "optional_probe", "deployable": False, "required": False},
            ],
            source="unit",
        )

        self.assertTrue(gate.deployable)
        self.assertEqual(gate.reason, "passed")

    def test_run_monthly_validation_suite_marks_failed_scenario(self):
        def fake_runner(symbol_candles, **kwargs):
            excess = 5.0 if kwargs["start"] == "2024-01-01" else -1.0
            return _monthly_result(excess_return_pct=excess, max_drawdown_pct=-10.0)

        rows = run_monthly_validation_suite(
            {"111111": [_candle("2024-01-02", 100, 110), _candle("2024-02-01", 110, 120)]},
            cases=[
                MonthlyValidationCase(name="passing", category="duration", start="2024-01-01", end="2024-01-31"),
                MonthlyValidationCase(name="failing", category="stress", start="2024-02-01", end="2024-02-29"),
            ],
            config=MonthlyRebalanceConfig(),
            backtest_runner=fake_runner,
        )

        self.assertEqual([row["deployable"] for row in rows], [True, False])
        self.assertEqual(build_monthly_validation_gate(rows).reason, "failed_required_scenarios:failing")

    def test_run_monthly_validation_suite_applies_slippage_multiplier(self):
        seen_slippage_rates: list[float] = []

        def fake_runner(symbol_candles, **kwargs):
            seen_slippage_rates.append(kwargs["slippage_rate"])
            return _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0)

        run_monthly_validation_suite(
            {"111111": [_candle("2024-01-02", 100, 110)]},
            cases=[
                MonthlyValidationCase(
                    name="slippage_x3",
                    category="stress",
                    start="2024-01-01",
                    end="2024-01-31",
                    slippage_multiplier=3.0,
                ),
            ],
            config=MonthlyRebalanceConfig(),
            slippage_rate=0.001,
            backtest_runner=fake_runner,
        )

        self.assertEqual(seen_slippage_rates, [0.003])

    def test_run_monthly_validation_suite_records_universe_bias_details(self):
        def fake_runner(symbol_candles, **kwargs):
            return _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0)

        rows = run_monthly_validation_suite(
            {
                "NORMAL": [_candle("2024-01-02", 100, 120)],
                "WINNER": [_candle("2024-01-02", 100, 800)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            cases=[MonthlyValidationCase(name="biased", category="duration", start="2024-01-01", end="2024-01-31")],
            config=MonthlyRebalanceConfig(),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["reason"], "universe_bias_warning")
        self.assertIn("high_average_symbol_return", rows[0]["universe_bias_reasons"])
        self.assertIn("extreme_return_share", rows[0]["universe_bias_reasons"])
        self.assertEqual(rows[0]["universe_extreme_return_symbols"], 1)

    def test_run_monthly_walk_forward_validation_selects_train_winner_for_test(self):
        test_presets: list[str] = []

        def fake_runner(symbol_candles, **kwargs):
            preset = kwargs["config"].presets[0]
            if kwargs["end"] == "2024-03-31":
                excess = 10.0 if preset == "balanced" else -5.0
            else:
                test_presets.append(preset)
                excess = 3.0 if preset == "balanced" else -3.0
            return _monthly_result(excess_return_pct=excess, max_drawdown_pct=-10.0)

        rows = run_monthly_walk_forward_validation(
            {"111111": _daily_candles("2024-01-01", 180)},
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(presets=("balanced", "aggressive")),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "balanced")
        self.assertEqual(rows[0]["train_excess_return_pct"], 10.0)
        self.assertIn("balanced:excess=10", rows[0]["train_candidate_scores"])
        self.assertIn("aggressive:excess=-5", rows[0]["train_candidate_scores"])
        self.assertIn("score=0", rows[0]["train_candidate_scores"])
        self.assertEqual(rows[0]["deployable"], True)
        self.assertEqual(test_presets, ["balanced"])

    def test_run_monthly_walk_forward_validation_penalizes_fragile_train_winner(self):
        test_presets: list[str] = []

        def fake_runner(symbol_candles, **kwargs):
            preset = kwargs["config"].presets[0]
            if kwargs["end"] == "2024-03-31":
                if preset == "aggressive":
                    return _monthly_result(excess_return_pct=20.0, max_drawdown_pct=-35.0, trade_count=4)
                return _monthly_result(excess_return_pct=12.0, max_drawdown_pct=-4.0, trade_count=4)
            test_presets.append(preset)
            return _monthly_result(excess_return_pct=2.0, max_drawdown_pct=-8.0, trade_count=2)

        rows = run_monthly_walk_forward_validation(
            {"111111": _daily_candles("2024-01-01", 180)},
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(presets=("balanced", "aggressive")),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "balanced")
        self.assertEqual(rows[0]["train_excess_return_pct"], 12.0)
        self.assertEqual(test_presets, ["balanced"])

    def test_run_monthly_walk_forward_validation_records_train_decision_profiles(self):
        def train_decision(mode: str, selected_preset: str) -> MonthlyDecision:
            return MonthlyDecision(
                as_of_date="2024-03-01",
                signal_date="2024-02-29",
                mode=mode,
                selected_preset=selected_preset,
                target_weights={},
                reason="unit",
            )

        def fake_runner(symbol_candles, **kwargs):
            preset = kwargs["config"].presets[0]
            if kwargs["end"] == "2024-03-31":
                decisions = (
                    [train_decision("alpha", preset), train_decision("market_beta_proxy", "market_beta_proxy")]
                    if preset == "balanced"
                    else [train_decision("market_beta_proxy", "market_beta_proxy")]
                )
                return _monthly_result(
                    excess_return_pct=10.0 if preset == "balanced" else 8.0,
                    max_drawdown_pct=-5.0,
                    trade_count=4,
                    decisions=decisions,
                )
            return _monthly_result(excess_return_pct=3.0, max_drawdown_pct=-8.0, trade_count=2)

        rows = run_monthly_walk_forward_validation(
            {"111111": _daily_candles("2024-01-01", 180)},
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(presets=("balanced", "aggressive")),
            backtest_runner=fake_runner,
        )

        profile = rows[0]["train_candidate_decision_profiles"]
        self.assertIn("balanced:modes=alpha:1|market_beta_proxy:1", profile)
        self.assertIn("alpha_ratio=0.5", profile)
        self.assertIn("aggressive:modes=market_beta_proxy:1", profile)
        self.assertIn("alpha_ratio=0", profile)

    def test_run_monthly_walk_forward_validation_records_direct_train_candidate_scores(self):
        def fake_runner(symbol_candles, **kwargs):
            return _monthly_result(
                excess_return_pct=-2.0 if kwargs["end"] == "2024-03-31" else 3.0,
                max_drawdown_pct=-8.0,
                trade_count=2,
                decisions=[
                    MonthlyDecision(
                        as_of_date="2024-03-01",
                        signal_date="2024-02-29",
                        mode="market_beta_proxy",
                        selected_preset="market_beta_proxy",
                        target_weights={},
                        reason="unit",
                    )
                ],
            )

        rows = run_monthly_walk_forward_validation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 180, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 180, close=90, step=0.5, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 180, close=120, step=-0.2, volume=1_000),
            },
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(
                presets=("balanced", "aggressive"),
                min_rows_per_window=20,
                start_grace_days=0,
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_top_n=0,
                train_stability_years=1,
            ),
            backtest_runner=fake_runner,
        )

        direct_scores = rows[0]["train_candidate_direct_scores"]
        self.assertIn("balanced:excess=", direct_scores)
        self.assertIn("aggressive:excess=", direct_scores)
        self.assertIn("trades=", direct_scores)

    def test_run_monthly_walk_forward_validation_records_direct_train_diagnostics(self):
        def fake_runner(symbol_candles, **kwargs):
            return _monthly_result(
                excess_return_pct=-2.0 if kwargs["end"] == "2024-03-31" else 3.0,
                max_drawdown_pct=-8.0,
                trade_count=2,
            )

        rows = run_monthly_walk_forward_validation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 120, close=100, step=-0.2, volume=4_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 120, close=90, step=0.1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 120, close=10, step=0.01, volume=3_000),
                "DDD": _trend_candles_with_volume("2024-01-01", 120, close=80, step=0.1, volume=5_000),
            },
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                min_rows_per_window=20,
                start_grace_days=0,
                point_in_time_universe={"2024-03-31": {"AAA", "BBB", "CCC"}},
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=1,
                point_in_time_liquidity_window_days=20,
                train_stability_years=1,
            ),
            backtest_runner=fake_runner,
        )

        diagnostics = rows[0]["train_direct_diagnostics"]
        self.assertIn("period_days=91", diagnostics)
        self.assertIn("raw_symbols=4", diagnostics)
        self.assertIn("universe_symbols=3", diagnostics)
        self.assertIn("pit_symbols=2", diagnostics)
        self.assertIn("liquid_symbols=1", diagnostics)
        self.assertIn("train_symbols=1", diagnostics)
        self.assertIn("liquidity_top_n=1", diagnostics)
        self.assertIn("universe_removed=1", diagnostics)
        self.assertIn("pit_filter_removed=1", diagnostics)
        self.assertIn("liquidity_removed=1", diagnostics)
        self.assertIn("market_regime=weak", diagnostics)
        self.assertIn("direct_candidate_count=", diagnostics)
        self.assertIn("best_direct_total_return_pct=", diagnostics)
        self.assertIn("best_direct_buy_hold_return_pct=", diagnostics)

    def test_analyze_monthly_direct_alpha_selection_explains_selected_and_rejected_symbols(self):
        symbol_candles = {
            "AAA": _trend_candles_with_volume("2024-01-01", 220, close=100, step=1.2, volume=10_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 220, close=100, step=1.0, volume=9_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 220, close=100, step=0.8, volume=8_000),
            "DDD": _trend_candles_with_volume("2024-01-01", 220, close=100, step=0.6, volume=7_000),
            "EEE": _trend_candles_with_volume("2024-01-01", 220, close=100, step=0.4, volume=6_000),
            "FFF": _trend_candles_with_volume("2024-01-01", 220, close=100, step=0.2, volume=5_000),
            "PENNY": _trend_candles_with_volume("2024-01-01", 220, close=10, step=0.01, volume=20_000),
            "OUT": _trend_candles_with_volume("2024-01-01", 220, close=100, step=2.0, volume=30_000),
        }
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-08-07",
            start="2024-08-08",
            end="2024-09-30",
        )

        rows = analyze_monthly_direct_alpha_selection(
            symbol_candles,
            cases=[case],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                point_in_time_universe={"2024-08-07": {"AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "PENNY"}},
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=6,
                point_in_time_liquidity_window_days=20,
                min_rows_per_window=20,
                start_grace_days=0,
                train_stability_years=1,
            ),
        )

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["selection_status"], "selected")
        self.assertEqual(by_symbol["AAA"]["selection_weight"], "0.2")
        self.assertGreater(float(by_symbol["AAA"]["momentum_score_pct"]), float(by_symbol["FFF"]["momentum_score_pct"]))
        self.assertEqual(by_symbol["FFF"]["selection_status"], "rejected")
        self.assertEqual(by_symbol["FFF"]["rejection_reason"], "below_selected_rank")
        self.assertEqual(by_symbol["AAA"]["raw_symbols"], 8)
        self.assertEqual(by_symbol["AAA"]["universe_symbols"], 7)
        self.assertEqual(by_symbol["AAA"]["pit_symbols"], 6)
        self.assertEqual(by_symbol["AAA"]["liquid_symbols"], 6)
        self.assertEqual(by_symbol["AAA"]["train_symbols"], 6)
        self.assertEqual(by_symbol["AAA"]["universe_removed"], 1)
        self.assertEqual(by_symbol["AAA"]["pit_filter_removed"], 1)
        self.assertEqual(by_symbol["AAA"]["liquidity_removed"], 0)
        self.assertIn("benchmark_avg_return_pct", by_symbol["AAA"])
        self.assertIn("candidate_excess_return_pct", by_symbol["AAA"])
        self.assertIn("candidate_trade_count", by_symbol["AAA"])
        self.assertIn("candidate_buy_count", by_symbol["AAA"])
        self.assertIn("candidate_sell_count", by_symbol["AAA"])
        self.assertIn("candidate_unique_traded_symbols", by_symbol["AAA"])

    def test_save_monthly_direct_alpha_selection_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "direct_alpha_selection.csv"
            saved = save_monthly_direct_alpha_selection(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "preset": "balanced",
                        "symbol": "AAA",
                        "selection_status": "selected",
                        "momentum_score_pct": "12.3",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,preset,symbol", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_direct_alpha_holding_path_compares_rebalance_holdings_to_train_end_snapshot(self):
        symbol_candles = {
            "AAA": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.2, volume=10_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.0, volume=9_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.8, volume=8_000),
            "DDD": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.6, volume=7_000),
            "EEE": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.4, volume=6_000),
            "FFF": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.2, volume=5_000),
        }
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-09-16",
            start="2024-09-17",
            end="2024-10-31",
        )

        rows = analyze_monthly_direct_alpha_holding_path(
            symbol_candles,
            cases=[case],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=6,
                point_in_time_liquidity_window_days=20,
                min_rows_per_window=20,
                start_grace_days=0,
                train_stability_years=1,
            ),
        )

        buy_rows = [row for row in rows if row["entered_symbols"]]
        self.assertTrue(buy_rows)
        first_buy = buy_rows[0]
        self.assertEqual(first_buy["scenario"], "walk_forward_unit")
        self.assertEqual(first_buy["preset"], "balanced")
        self.assertIn("AAA", first_buy["held_symbols"].split(";"))
        self.assertIn("AAA", first_buy["train_end_selected_symbols"].split(";"))
        self.assertGreater(first_buy["snapshot_overlap_count"], 0)
        self.assertIn("held_weights", first_buy)
        self.assertIn("candidate_excess_return_pct", first_buy)
        self.assertEqual(first_buy["benchmark_symbol_count"], 6)
        self.assertTrue(
            any(row["rebalance_trade_count"] == 0 and row["holding_count"] == 5 for row in rows)
        )
        self.assertTrue(any(row["exited_symbols"] for row in rows))

    def test_save_monthly_direct_alpha_holding_path_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "direct_alpha_path.csv"
            saved = save_monthly_direct_alpha_holding_path(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "preset": "balanced",
                        "rebalance_date": "2024-07-01",
                        "entered_symbols": "AAA",
                        "held_symbols": "AAA",
                        "snapshot_overlap_count": 1,
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,preset,rebalance_date", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_direct_alpha_path_drift_decomposes_symbol_contributions(self):
        symbol_candles = {
            "AAA": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.2, volume=10_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.0, volume=9_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.8, volume=8_000),
            "DDD": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.6, volume=7_000),
            "EEE": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.4, volume=6_000),
            "FFF": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.2, volume=5_000),
        }
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-09-16",
            start="2024-09-17",
            end="2024-10-31",
        )

        rows = analyze_monthly_direct_alpha_path_drift(
            symbol_candles,
            cases=[case],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=6,
                point_in_time_liquidity_window_days=20,
                min_rows_per_window=20,
                start_grace_days=0,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        active_dates = {row["rebalance_date"] for row in rows}
        self.assertTrue(active_dates)
        first = rows[0]
        self.assertEqual(first["scenario"], "walk_forward_unit")
        self.assertEqual(first["preset"], "balanced")
        self.assertIn("symbol", first)
        self.assertIn(first["path_role"], {"held_and_snapshot", "held_not_snapshot", "snapshot_missing_from_holdings", "benchmark_only"})
        self.assertIn("actual_weight", first)
        self.assertIn("benchmark_weight", first)
        self.assertIn("symbol_train_return_pct", first)
        self.assertIn("actual_contribution_pct", first)
        self.assertIn("benchmark_contribution_pct", first)
        self.assertIn("contribution_delta_pct", first)
        self.assertIn("first_trade_delay_days", first)
        self.assertIn("days_since_previous_active_rebalance", first)
        self.assertTrue(any(float(row["benchmark_weight"]) > 0 for row in rows))
        self.assertTrue(any(row["path_gap_reason"] for row in rows))

    def test_save_monthly_direct_alpha_path_drift_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "direct_alpha_path_drift.csv"
            saved = save_monthly_direct_alpha_path_drift(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "preset": "balanced",
                        "rebalance_date": "2024-07-01",
                        "symbol": "AAA",
                        "path_role": "held_and_snapshot",
                        "contribution_delta_pct": "1.23",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,preset,rebalance_date", text.splitlines()[0])
        self.assertIn("contribution_delta_pct", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_direct_alpha_timing_explains_snapshot_misses_by_rebalance_date(self):
        symbol_candles = {
            "AAA": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.2, volume=10_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.0, volume=9_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.8, volume=8_000),
            "DDD": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.6, volume=7_000),
            "EEE": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.4, volume=6_000),
            "FFF": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.2, volume=5_000),
        }
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-09-16",
            start="2024-09-17",
            end="2024-10-31",
        )

        rows = analyze_monthly_direct_alpha_timing(
            symbol_candles,
            cases=[case],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=6,
                point_in_time_liquidity_window_days=20,
                min_rows_per_window=20,
                start_grace_days=0,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        row = rows[0]
        self.assertEqual(row["scenario"], "walk_forward_unit")
        self.assertEqual(row["preset"], "balanced")
        self.assertIn("scheduled_rebalance_date", row)
        self.assertIn("signal_date", row)
        self.assertIn("train_end_selected_symbols", row)
        self.assertIn("scheduled_target_symbols", row)
        self.assertIn("snapshot_target_overlap_count", row)
        self.assertIn("snapshot_missing_from_scheduled_targets", row)
        self.assertIn("missed_snapshot_reason", row)
        self.assertIn("previous_target_overlap_count", row)
        self.assertIn("next_target_overlap_count", row)
        self.assertIn(row["best_timing_offset"], {"previous", "current", "next"})
        self.assertIn("timing_diagnostic", row)
        self.assertIn("first_trade_delay_days", row)
        self.assertIn("scheduled_rebalance_index", row)

    def test_save_monthly_direct_alpha_timing_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "direct_alpha_timing.csv"
            saved = save_monthly_direct_alpha_timing(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "preset": "balanced",
                        "scheduled_rebalance_date": "2024-07-01",
                        "snapshot_target_overlap_count": 2,
                        "timing_diagnostic": "current_timing_best",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,preset,scheduled_rebalance_date", text.splitlines()[0])
        self.assertIn("timing_diagnostic", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_direct_alpha_rank_drift_compares_train_end_and_rebalance_signal_ranks(self):
        symbol_candles = {
            "LATE": _piecewise_candles_with_volume(
                "2024-01-01",
                260,
                close=100,
                steps=[(0, 0.04), (181, 2.3)],
                volume=10_000,
            ),
            "EARLY": _piecewise_candles_with_volume(
                "2024-01-01",
                260,
                close=100,
                steps=[(0, 1.5), (181, 0.02)],
                volume=9_000,
            ),
            "AAA": _trend_candles_with_volume("2024-01-01", 260, close=100, step=1.0, volume=8_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.8, volume=7_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.6, volume=6_000),
            "DDD": _trend_candles_with_volume("2024-01-01", 260, close=100, step=0.4, volume=5_000),
        }
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-09-16",
            start="2024-09-17",
            end="2024-10-31",
        )

        rows = analyze_monthly_direct_alpha_rank_drift(
            symbol_candles,
            cases=[case],
            config=MonthlyRebalanceConfig(
                presets=("balanced",),
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=50,
                point_in_time_liquidity_top_n=6,
                point_in_time_liquidity_window_days=20,
                min_rows_per_window=20,
                start_grace_days=0,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        late_rows = [row for row in rows if row["symbol"] == "LATE"]
        self.assertTrue(late_rows)
        late = late_rows[0]
        self.assertEqual(late["scenario"], "walk_forward_unit")
        self.assertEqual(late["preset"], "balanced")
        self.assertEqual(late["in_train_end_selected_snapshot"], "true")
        self.assertEqual(late["in_scheduled_targets"], "false")
        self.assertIn("scheduled_rebalance_date", late)
        self.assertIn("signal_date", late)
        self.assertIn("train_end_momentum_score_pct", late)
        self.assertIn("scheduled_momentum_score_pct", late)
        self.assertIn("momentum_delta_pct", late)
        self.assertIn("train_end_rank", late)
        self.assertIn("scheduled_rank", late)
        self.assertIn("market_breadth_at_signal", late)
        self.assertIn("market_breadth_allows_entry", late)
        self.assertIn("ranking_top_n_at_signal", late)
        self.assertIn("ranking_trend_filter_days_at_signal", late)
        self.assertIn(late["drop_reason"], {"rank_dropped_below_top_n", "below_selected_rank"})
        self.assertTrue(any(row["symbol_role"] == "both" for row in rows))

    def test_save_monthly_direct_alpha_rank_drift_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "direct_alpha_rank_drift.csv"
            saved = save_monthly_direct_alpha_rank_drift(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "preset": "balanced",
                        "scheduled_rebalance_date": "2024-07-01",
                        "symbol": "AAA",
                        "momentum_delta_pct": "1.23",
                        "drop_reason": "still_selected",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,preset,scheduled_rebalance_date", text.splitlines()[0])
        self.assertIn("momentum_delta_pct", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_train_decision_path_explains_fallback_choices(self):
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-03-30",
            start="2024-04-01",
            end="2024-04-30",
        )
        rows = analyze_monthly_train_decision_path(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 90, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 90, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 90, close=110, step=-1, volume=1_000),
            },
            cases=[case],
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                presets=("balanced",),
                min_train_trades=999,
                min_rows_per_window=3,
                start_grace_days=0,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        fallback_rows = [row for row in rows if row["decision_mode"] == "market_beta_proxy"]
        self.assertTrue(fallback_rows)
        row = fallback_rows[0]
        self.assertEqual(row["scenario"], "walk_forward_unit")
        self.assertEqual(row["walk_forward_preset"], "balanced")
        self.assertIn("no_train_candidate", row["decision_reason"])
        self.assertEqual(row["alpha_block_reason"], "no_eligible_direct_candidate")
        self.assertIn("AAA", row["target_symbols"].split(";"))
        self.assertGreater(row["direct_candidate_count"], 0)
        self.assertEqual(row["eligible_direct_candidate_count"], 0)
        self.assertIn("balanced:excess=", row["direct_candidate_scores"])
        self.assertIn("insufficient_trades", row["direct_candidate_rejection_reasons"])
        self.assertIn("outer_train_alpha_ratio", row)
        self.assertLess(float(row["cash_weight"]), 1.0)

    def test_analyze_monthly_train_decision_path_labels_empty_train_windows_without_internal_error(self):
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-04-30",
            start="2024-05-01",
            end="2024-05-31",
        )
        rows = analyze_monthly_train_decision_path(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 130, close=100, step=0.7, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 130, close=100, step=0.5, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 130, close=180, step=-0.2, volume=1_000),
            },
            cases=[case],
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                presets=("balanced",),
                min_rows_per_window=120,
                start_grace_days=0,
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=20,
                point_in_time_liquidity_top_n=3,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        early_rows = [row for row in rows if row["train_symbols"] == 0]
        self.assertTrue(early_rows)
        self.assertFalse(any(row["decision_reason"].startswith("decision_error:") for row in early_rows))
        self.assertTrue(any(row["filter_error"] == "no_train_symbols" for row in early_rows))
        self.assertTrue(any(row["alpha_block_reason"] == "no_train_symbols" for row in early_rows))

    def test_save_monthly_train_decision_path_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "train_decisions.csv"
            saved = save_monthly_train_decision_path(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "walk_forward_preset": "balanced",
                        "as_of_date": "2024-02-01",
                        "decision_mode": "market_beta_proxy",
                        "direct_candidate_rejection_reasons": "insufficient_trades",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,walk_forward_preset,as_of_date", text.splitlines()[0])
        self.assertIn("insufficient_trades", text)

    def test_analyze_monthly_train_stability_windows_breaks_positive_ratio_into_subwindows(self):
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2025-03-31",
            start="2025-04-01",
            end="2025-04-30",
        )
        rows = analyze_monthly_train_stability_windows(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 460, close=100, step=0.7, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 460, close=100, step=0.5, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 460, close=180, step=-0.2, volume=1_000),
            },
            cases=[case],
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                presets=("balanced",),
                min_train_positive_ratio=1.1,
                min_rows_per_window=20,
                start_grace_days=0,
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=20,
                point_in_time_liquidity_top_n=3,
                train_stability_years=1,
            ),
        )

        counted_rows = [row for row in rows if row["subwindow_counted_flag"] == "true"]
        self.assertTrue(counted_rows)
        row = counted_rows[0]
        self.assertEqual(row["scenario"], "walk_forward_unit")
        self.assertEqual(row["walk_forward_preset"], "balanced")
        self.assertEqual(row["preset"], "balanced")
        self.assertIn("train_stability_", row["stability_window"])
        self.assertIn(row["subwindow_positive_flag"], {"true", "false"})
        self.assertIn("candidate_train_positive_ratio", row)
        self.assertIn("low_positive_ratio", row["candidate_rejection_reasons"])
        self.assertIn("candidate_excess_return_pct", row)
        self.assertGreaterEqual(int(float(row["candidate_train_subwindows"])), 1)
        self.assertEqual(row["train_decision_as_of"], row["as_of_date"])
        self.assertEqual(row["candidate_name"], "balanced")
        self.assertEqual(row["candidate_rank"], "1")
        self.assertEqual(row["candidate_eligible"], "false")
        self.assertEqual(row["candidate_positive_ratio"], row["candidate_train_positive_ratio"])
        self.assertIn("prior_breadth", row)
        self.assertIn("trend_scale", row)
        self.assertIn("liquidity_scale", row)
        self.assertIn("direct_candidate_count", row)
        self.assertGreaterEqual(int(float(row["stability_window_index"])), 1)
        self.assertGreater(int(float(row["stability_window_days"])), 0)
        self.assertEqual(row["stability_excess_return_pct"], row["subwindow_excess_return_pct"])
        self.assertEqual(row["stability_positive"], row["subwindow_positive_flag"])
        if row["stability_positive"] == "false":
            self.assertTrue(row["stability_failed_reason"])

    def test_analyze_monthly_train_stability_windows_adds_selection_and_path_context(self):
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2025-03-31",
            start="2025-04-01",
            end="2025-04-30",
        )
        rows = analyze_monthly_train_stability_windows(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 460, close=100, step=0.7, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 460, close=100, step=0.5, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 460, close=180, step=-0.2, volume=1_000),
            },
            cases=[case],
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                presets=("balanced",),
                min_train_positive_ratio=1.1,
                min_rows_per_window=20,
                start_grace_days=0,
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=20,
                point_in_time_liquidity_top_n=3,
                train_stability_years=1,
            ),
        )

        row = next(row for row in rows if row["subwindow_counted_flag"] == "true")
        self.assertIn("stability_selected_symbols", row)
        self.assertIn("stability_selected_symbol_count", row)
        self.assertIn("stability_benchmark_avg_return_pct", row)
        self.assertIn("stability_selected_avg_return_pct", row)
        self.assertIn("stability_selected_vs_benchmark_avg_return_delta_pct", row)
        self.assertIn(row["stability_selected_underperformed_benchmark"], {"true", "false", ""})
        self.assertIn("stability_traded_symbols", row)
        self.assertIn("stability_traded_symbol_count", row)
        self.assertIn("stability_selected_not_traded_symbols", row)
        self.assertIn("stability_traded_not_selected_symbols", row)
        self.assertTrue(row["stability_underperformance_driver"])

    def test_analyze_monthly_train_stability_windows_labels_empty_train_windows_without_internal_error(self):
        case = MonthlyValidationCase(
            name="walk_forward_unit",
            category="walk_forward",
            train_start="2024-01-01",
            train_end="2024-04-30",
            start="2024-05-01",
            end="2024-05-31",
        )
        rows = analyze_monthly_train_stability_windows(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 130, close=100, step=0.7, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 130, close=100, step=0.5, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 130, close=180, step=-0.2, volume=1_000),
            },
            cases=[case],
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                presets=("balanced",),
                min_rows_per_window=120,
                start_grace_days=0,
                point_in_time_min_history_days=20,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=20,
                point_in_time_liquidity_top_n=3,
                train_stability_years=1,
            ),
        )

        self.assertTrue(rows)
        early_rows = [row for row in rows if row["subwindow_counted_flag"] == "false"]
        self.assertTrue(early_rows)
        self.assertFalse(any(row["filter_error"] == "symbol_candles_cannot_be_empty" for row in early_rows))
        self.assertTrue(any(row["stability_failed_reason"] == "no_train_symbols" for row in early_rows))
        self.assertTrue(any(row["stability_underperformance_driver"] == "no_train_symbols" for row in early_rows))

    def test_analyze_monthly_train_stability_symbol_attribution_expands_selected_and_traded_roles(self):
        symbol_candles = {
            "AAA": _trend_candles_with_volume("2024-01-01", 20, close=100, step=2.0, volume=3_000),
            "BBB": _trend_candles_with_volume("2024-01-01", 20, close=100, step=1.0, volume=2_000),
            "CCC": _trend_candles_with_volume("2024-01-01", 20, close=100, step=-0.5, volume=1_000),
        }
        stability_rows = [
            {
                "scenario": "walk_forward_unit",
                "walk_forward_preset": "balanced",
                "as_of_date": "2024-01-20",
                "signal_date": "2024-01-19",
                "category": "walk_forward",
                "decision_mode": "market_beta_proxy",
                "alpha_block_reason": "no_eligible_direct_candidate",
                "candidate_rejection_reasons": "low_positive_ratio",
                "candidate_positive_ratio": "0.0",
                "subwindow_counted_flag": "true",
                "stability_window_start": "2024-01-01",
                "stability_window_end": "2024-01-20",
                "stability_excess_return_pct": "-3.2",
                "stability_trade_count": "2",
                "stability_failed_reason": "nonpositive_excess",
                "stability_selected_symbols": "AAA;BBB",
                "stability_traded_symbols": "BBB;CCC",
                "stability_underperformance_driver": "holding_path_differs_from_selection_snapshot",
                "train_symbols": "3",
            }
        ]

        rows = analyze_monthly_train_stability_symbol_attribution(stability_rows, symbol_candles)

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertEqual(by_symbol["AAA"]["stability_symbol_role"], "selected_not_traded")
        self.assertEqual(by_symbol["BBB"]["stability_symbol_role"], "selected_and_traded")
        self.assertEqual(by_symbol["CCC"]["stability_symbol_role"], "traded_not_selected")
        self.assertEqual(by_symbol["AAA"]["in_stability_selected"], "true")
        self.assertEqual(by_symbol["AAA"]["in_stability_traded"], "false")
        self.assertEqual(by_symbol["CCC"]["in_stability_selected"], "false")
        self.assertEqual(by_symbol["CCC"]["in_stability_traded"], "true")
        self.assertIn("symbol_return_pct", by_symbol["AAA"])
        self.assertIn("selected_contribution_pct", by_symbol["AAA"])
        self.assertIn("traded_contribution_pct", by_symbol["CCC"])
        self.assertIn("benchmark_contribution_pct", by_symbol["BBB"])
        self.assertIn("traded_vs_selected_contribution_delta_pct", by_symbol["CCC"])
        self.assertEqual(by_symbol["AAA"]["stability_underperformance_driver"], "holding_path_differs_from_selection_snapshot")
        self.assertGreater(float(by_symbol["AAA"]["selected_contribution_pct"]), 0)

    def test_save_monthly_train_stability_symbol_attribution_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "train_stability_symbols.csv"
            saved = save_monthly_train_stability_symbol_attribution(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "walk_forward_preset": "balanced",
                        "as_of_date": "2024-01-20",
                        "symbol": "AAA",
                        "stability_symbol_role": "selected_not_traded",
                        "symbol_return_pct": "12.3",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,walk_forward_preset,as_of_date", text.splitlines()[0])
        self.assertIn("stability_symbol_role", text.splitlines()[0])
        self.assertIn("walk_forward_unit", text)

    def test_analyze_monthly_train_stability_summary_aggregates_low_positive_ratio_drivers(self):
        stability_rows = [
            {
                "scenario": "walk_forward_003",
                "walk_forward_preset": "balanced",
                "category": "walk_forward",
                "as_of_date": "2025-07-23",
                "candidate_name": "balanced",
                "candidate_rank": "1",
                "candidate_eligible": "false",
                "candidate_rejection_reasons": "low_positive_ratio",
                "candidate_positive_ratio": "0.25",
                "subwindow_counted_flag": "true",
                "stability_window": "train_stability_1",
                "stability_window_start": "2024-07-01",
                "stability_window_end": "2025-01-01",
                "stability_excess_return_pct": "-4.0",
                "stability_positive": "false",
                "stability_failed_reason": "nonpositive_excess",
                "stability_underperformance_driver": "selected_underperformed_benchmark",
            },
            {
                "scenario": "walk_forward_003",
                "walk_forward_preset": "balanced",
                "category": "walk_forward",
                "as_of_date": "2025-07-23",
                "candidate_name": "balanced",
                "candidate_rank": "1",
                "candidate_eligible": "false",
                "candidate_rejection_reasons": "low_positive_ratio",
                "candidate_positive_ratio": "0.25",
                "subwindow_counted_flag": "true",
                "stability_window": "train_stability_2",
                "stability_window_start": "2025-01-02",
                "stability_window_end": "2025-07-22",
                "stability_excess_return_pct": "3.0",
                "stability_positive": "true",
                "stability_failed_reason": "",
                "stability_underperformance_driver": "selected_outperformed_benchmark",
            },
            {
                "scenario": "walk_forward_003",
                "walk_forward_preset": "balanced",
                "category": "walk_forward",
                "as_of_date": "2025-08-22",
                "candidate_name": "balanced",
                "candidate_rank": "1",
                "candidate_eligible": "false",
                "candidate_rejection_reasons": "low_positive_ratio;nonpositive_excess",
                "candidate_positive_ratio": "0.0",
                "subwindow_counted_flag": "true",
                "stability_window": "train_stability_1",
                "stability_window_start": "2024-08-01",
                "stability_window_end": "2025-02-01",
                "stability_excess_return_pct": "-2.0",
                "stability_positive": "false",
                "stability_failed_reason": "nonpositive_excess",
                "stability_underperformance_driver": "holding_path_differs_from_selection_snapshot",
            },
            {
                "scenario": "walk_forward_003",
                "walk_forward_preset": "balanced",
                "category": "walk_forward",
                "as_of_date": "2025-08-22",
                "candidate_name": "balanced",
                "candidate_rank": "1",
                "candidate_eligible": "false",
                "candidate_rejection_reasons": "low_positive_ratio;nonpositive_excess",
                "candidate_positive_ratio": "0.0",
                "subwindow_counted_flag": "true",
                "stability_window": "train_stability_2",
                "stability_window_start": "2025-02-02",
                "stability_window_end": "2025-08-21",
                "stability_excess_return_pct": "-1.0",
                "stability_buy_hold_return_pct": "6.0",
                "stability_positive": "false",
                "stability_failed_reason": "no_trades",
                "stability_underperformance_driver": "no_trades;benchmark_positive_selection_nonpositive",
            },
        ]

        rows = analyze_monthly_train_stability_summary(stability_rows)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "walk_forward_003")
        self.assertEqual(row["walk_forward_preset"], "balanced")
        self.assertEqual(row["candidate_name"], "balanced")
        self.assertEqual(row["train_decision_count"], "2")
        self.assertEqual(row["low_positive_ratio_decision_count"], "2")
        self.assertEqual(row["eligible_decision_count"], "0")
        self.assertEqual(row["counted_subwindow_count"], "4")
        self.assertEqual(row["positive_subwindow_count"], "1")
        self.assertEqual(row["negative_subwindow_count"], "3")
        self.assertEqual(row["negative_subwindow_ratio"], "0.75")
        self.assertEqual(row["no_trade_subwindow_count"], "1")
        self.assertEqual(row["no_trade_benchmark_positive_count"], "1")
        self.assertEqual(row["no_trade_total_benchmark_return_pct"], "6")
        self.assertEqual(row["no_trade_avg_benchmark_return_pct"], "6")
        self.assertEqual(row["candidate_positive_ratio_min"], "0")
        self.assertEqual(row["candidate_positive_ratio_max"], "0.25")
        self.assertEqual(row["avg_stability_excess_return_pct"], "-1")
        self.assertEqual(row["worst_stability_excess_return_pct"], "-4")
        self.assertEqual(row["dominant_failed_reason"], "nonpositive_excess")
        self.assertIn("nonpositive_excess=2", row["failed_reason_counts"])
        self.assertIn("no_trades=1", row["failed_reason_counts"])
        self.assertIn("holding_path_differs_from_selection_snapshot=1", row["underperformance_driver_counts"])
        self.assertIn("benchmark_positive_selection_nonpositive=1", row["underperformance_driver_counts"])
        self.assertIn("no_trades=1", row["underperformance_driver_counts"])
        self.assertIn("2025-07-23:train_stability_1", row["negative_stability_windows"])
        self.assertEqual(row["diagnostic"], "low_positive_ratio_due_to_negative_stability_windows")
        self.assertIn("Inspect negative stability windows", row["next_action"])

    def test_save_monthly_train_stability_summary_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "train_stability_summary.csv"
            saved = save_monthly_train_stability_summary(
                [
                    {
                        "scenario": "walk_forward_003",
                        "walk_forward_preset": "balanced",
                        "candidate_name": "balanced",
                        "train_decision_count": "1",
                        "diagnostic": "low_positive_ratio_due_to_negative_stability_windows",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,walk_forward_preset", text.splitlines()[0])
        self.assertIn("no_trade_total_benchmark_return_pct", text.splitlines()[0])
        self.assertIn("low_positive_ratio_due_to_negative_stability_windows", text)

    def test_analyze_monthly_train_stability_summary_keeps_no_candidate_windows(self):
        rows = analyze_monthly_train_stability_summary(
            [
                {
                    "scenario": "walk_forward_003",
                    "walk_forward_preset": "balanced",
                    "category": "walk_forward",
                    "as_of_date": "2025-04-01",
                    "candidate_name": "",
                    "preset": "",
                    "subwindow_counted_flag": "false",
                    "stability_failed_reason": "no_train_symbols",
                    "stability_underperformance_driver": "no_train_symbols",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate_name"], "no_direct_candidate")
        self.assertEqual(rows[0]["train_decision_count"], "1")
        self.assertEqual(rows[0]["counted_subwindow_count"], "0")
        self.assertEqual(rows[0]["diagnostic"], "no_counted_stability_windows")
        self.assertIn("no_train_symbols=1", rows[0]["failed_reason_counts"])
        self.assertIn("no_train_symbols=1", rows[0]["underperformance_driver_counts"])

    def test_analyze_monthly_train_stability_path_drift_experiments_summarizes_paper_only_candidates(self):
        stability_rows = [
            {
                "scenario": "walk_forward_unit",
                "walk_forward_preset": "balanced",
                "as_of_date": "2024-01-20",
                "signal_date": "2024-01-19",
                "category": "walk_forward",
                "decision_mode": "market_beta_proxy",
                "alpha_block_reason": "no_eligible_direct_candidate",
                "candidate_rejection_reasons": "low_positive_ratio",
                "candidate_positive_ratio": "0.0",
                "subwindow_counted_flag": "true",
                "stability_window_start": "2024-01-01",
                "stability_window_end": "2024-01-20",
                "stability_excess_return_pct": "-12.0",
                "stability_trade_count": "4",
                "stability_failed_reason": "nonpositive_excess",
                "stability_underperformance_driver": "holding_path_differs_from_selection_snapshot",
            }
        ]
        symbol_rows = [
            {
                "scenario": "walk_forward_unit",
                "as_of_date": "2024-01-20",
                "stability_window_start": "2024-01-01",
                "stability_window_end": "2024-01-20",
                "stability_symbol_role": "selected_not_traded",
                "selected_contribution_pct": "20.0",
                "traded_contribution_pct": "0.0",
                "benchmark_contribution_pct": "5.0",
                "traded_vs_selected_contribution_delta_pct": "-20.0",
            },
            {
                "scenario": "walk_forward_unit",
                "as_of_date": "2024-01-20",
                "stability_window_start": "2024-01-01",
                "stability_window_end": "2024-01-20",
                "stability_symbol_role": "traded_not_selected",
                "selected_contribution_pct": "0.0",
                "traded_contribution_pct": "6.0",
                "benchmark_contribution_pct": "2.0",
                "traded_vs_selected_contribution_delta_pct": "6.0",
            },
            {
                "scenario": "walk_forward_unit",
                "as_of_date": "2024-01-20",
                "stability_window_start": "2024-01-01",
                "stability_window_end": "2024-01-20",
                "stability_symbol_role": "selected_and_traded",
                "selected_contribution_pct": "10.0",
                "traded_contribution_pct": "10.0",
                "benchmark_contribution_pct": "3.0",
                "traded_vs_selected_contribution_delta_pct": "0.0",
            },
        ]

        rows = analyze_monthly_train_stability_path_drift_experiments(stability_rows, symbol_rows)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["scenario"], "walk_forward_unit")
        self.assertEqual(row["experiment_family"], "path_drift_reduction")
        self.assertEqual(row["paper_only"], "true")
        self.assertEqual(row["target_persistence_candidate"], "true")
        self.assertEqual(row["slower_rebalance_candidate"], "true")
        self.assertEqual(row["delayed_entry_candidate"], "false")
        self.assertEqual(row["experiment_recommendation"], "test_stricter_target_persistence")
        self.assertEqual(row["candidate_status"], "paper_only_needs_full_validation")
        self.assertAlmostEqual(float(row["actual_traded_contribution_pct"]), 16.0)
        self.assertAlmostEqual(float(row["selected_snapshot_contribution_pct"]), 30.0)
        self.assertAlmostEqual(float(row["estimated_target_persistence_delta_pct"]), 14.0)
        self.assertAlmostEqual(float(row["selected_not_traded_contribution_pct"]), 20.0)
        self.assertAlmostEqual(float(row["traded_not_selected_contribution_pct"]), 6.0)

    def test_save_monthly_train_stability_path_drift_experiments_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "path_drift_experiments.csv"
            saved = save_monthly_train_stability_path_drift_experiments(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "as_of_date": "2024-01-20",
                        "experiment_family": "path_drift_reduction",
                        "paper_only": "true",
                        "experiment_recommendation": "test_stricter_target_persistence",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("experiment_family", text.splitlines()[0])
        self.assertIn("paper_only", text.splitlines()[0])
        self.assertIn("test_stricter_target_persistence", text)

    def test_save_monthly_train_stability_windows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "train_stability.csv"
            saved = save_monthly_train_stability_windows(
                [
                    {
                        "scenario": "walk_forward_unit",
                        "walk_forward_preset": "balanced",
                        "as_of_date": "2025-02-01",
                        "stability_window": "train_stability_2024",
                        "subwindow_positive_flag": "false",
                        "candidate_rejection_reasons": "low_positive_ratio",
                    }
                ],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("scenario,walk_forward_preset,as_of_date", text.splitlines()[0])
        self.assertIn("candidate_eligible", text.splitlines()[0])
        self.assertIn("stability_failed_reason", text.splitlines()[0])
        self.assertIn("prior_breadth", text.splitlines()[0])
        self.assertIn("stability_underperformance_driver", text.splitlines()[0])
        self.assertIn("low_positive_ratio", text)

    def test_generate_monthly_validation_cases_includes_duration_regime_and_stress(self):
        cases = generate_monthly_validation_cases(
            {"111111": _daily_candles("2024-01-01", 320)},
            start="2024-01-01",
            end="2024-11-15",
        )
        names = {case.name for case in cases}
        categories = {case.category for case in cases}

        self.assertIn("full_period", names)
        self.assertIn("duration_3m", names)
        self.assertIn("stress_exclude_500pct_winners", names)
        self.assertIn("stress_exclude_top_5_winners", names)
        self.assertIn("stress_slippage_x3", names)
        self.assertTrue(any(case.category == "walk_forward" for case in cases))
        self.assertIn("duration", categories)
        self.assertIn("regime", categories)
        self.assertIn("stress", categories)
        self.assertIn("walk_forward", categories)

    def test_audit_monthly_validation_data_flags_quality_issues(self):
        rows = audit_monthly_validation_data(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101)],
                "SHORT": [_candle("2024-01-02", 100)],
                "BADPRICE": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                ],
            },
            start="2024-01-01",
            end="2024-01-02",
            min_rows=2,
        )

        statuses = {row["symbol"]: row["status"] for row in rows}
        self.assertEqual(statuses["GOOD"], "PASS")
        self.assertEqual(statuses["SHORT"], "BLOCK")
        self.assertEqual(statuses["BADPRICE"], "BLOCK")

    def test_audit_point_in_time_price_coverage_blocks_low_snapshot_coverage(self):
        rows = audit_point_in_time_price_coverage(
            {
                "AAA": [_candle("2024-01-15", 100)],
                "CCC": [_candle("2024-02-15", 100)],
            },
            {
                "2024-01-31": {"AAA", "BBB", "CCC"},
                "2024-02-29": {"AAA"},
            },
            min_coverage_pct=80.0,
        )

        self.assertEqual(rows[0]["date"], "2024-01-31")
        self.assertEqual(rows[0]["covered_symbols"], 1)
        self.assertEqual(rows[0]["missing_symbols"], 2)
        self.assertEqual(rows[0]["status"], "BLOCK")
        self.assertIn("BBB", rows[0]["missing_preview"])
        self.assertEqual(rows[1]["status"], "PASS")

    def test_audit_point_in_time_price_coverage_separates_data_quality_exclusions(self):
        rows = audit_point_in_time_price_coverage(
            {
                "AAA": [_candle("2024-01-15", 100)],
            },
            {
                "2024-01-31": {"AAA", "BBB", "CCC"},
            },
            min_coverage_pct=80.0,
            excluded_symbols={"BBB"},
        )

        self.assertEqual(rows[0]["universe_symbols"], 2)
        self.assertEqual(rows[0]["covered_symbols"], 1)
        self.assertEqual(rows[0]["missing_symbols"], 1)
        self.assertEqual(rows[0]["excluded_symbols"], 1)
        self.assertIn("CCC", rows[0]["missing_preview"])
        self.assertNotIn("BBB", rows[0]["missing_preview"])

    def test_audit_point_in_time_price_coverage_excludes_metadata_filtered_members(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "snapshot_date,symbol,name,market\n"
                "2024-01-31,111111,정상기업,KOSPI\n"
                "2024-01-31,222222,신한제13호스팩,KOSDAQ\n"
                "2024-01-31,333333,대신증권우,KOSPI\n",
                encoding="utf-8",
            )
            universe = load_point_in_time_universe(path)

            rows = audit_point_in_time_price_coverage(
                {"111111": [_candle("2024-01-15", 100)]},
                universe,
                min_coverage_pct=80.0,
            )

        self.assertEqual(rows[0]["universe_symbols"], 1)
        self.assertEqual(rows[0]["covered_symbols"], 1)
        self.assertEqual(rows[0]["missing_symbols"], 0)
        self.assertEqual(rows[0]["coverage_pct"], 100.0)
        self.assertEqual(rows[0]["status"], "PASS")

    def test_save_universe_price_coverage_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coverage.csv"
            saved = save_universe_price_coverage_rows(
                [
                    {
                        "date": "2024-01-31",
                        "universe_symbols": 2,
                        "price_symbols": 1,
                        "covered_symbols": 1,
                        "missing_symbols": 1,
                        "coverage_pct": 50.0,
                        "status": "BLOCK",
                        "missing_preview": "BBB",
                    }
                ],
                path,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("coverage_pct", text)
        self.assertIn("BBB", text)

    def test_select_point_in_time_universe_excludes_nonpositive_price_history(self):
        selected = select_point_in_time_universe(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101), _candle("2024-01-03", 102)],
                "BAD": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                    _candle("2024-01-03", 102),
                ],
            },
            signal_date="2024-01-03",
            min_history_days=3,
            min_reference_price=1,
            max_trailing_return_pct=300,
            trailing_return_days=3,
        )

        self.assertEqual(set(selected), {"GOOD"})

    def test_exclude_invalid_price_symbols_removes_nonpositive_price_history(self):
        filtered = exclude_invalid_price_symbols(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101)],
                "BAD": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                ],
            }
        )

        self.assertEqual(set(filtered), {"GOOD"})

    def test_market_volatility_exposure_scale_reduces_high_volatility(self):
        scale = market_volatility_exposure_scale(
            {
                "VOL": [
                    _candle("2024-01-01", 100),
                    _candle("2024-01-02", 120),
                    _candle("2024-01-03", 90),
                    _candle("2024-01-04", 125),
                    _candle("2024-01-05", 95),
                    _candle("2024-01-06", 130),
                ]
            },
            before_date="2024-01-07",
            lookback_days=5,
            target_volatility_pct=10.0,
            min_scale=0.25,
        )

        self.assertGreaterEqual(scale, 0.25)
        self.assertLess(scale, 1.0)

    def test_market_volatility_exposure_scale_keeps_low_volatility_full_size(self):
        scale = market_volatility_exposure_scale(
            {"CALM": _daily_candles("2024-01-01", 20)},
            before_date="2024-01-21",
            lookback_days=10,
            target_volatility_pct=50.0,
            min_scale=0.25,
        )

        self.assertEqual(scale, 1.0)

    def test_decide_monthly_allocation_uses_liquid_proxy_when_market_beta_symbol_missing(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=3_000),
                "BBB": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=2_000),
                "CCC": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 109},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.selected_preset, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_strong_breadth_proxy")
        self.assertEqual(decision.target_weights, {"AAA": 0.495, "BBB": 0.495})

    def test_decide_monthly_allocation_caps_proxy_exposure_only(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=3_000),
                "BBB": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=2_000),
                "CCC": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                market_beta_proxy_max_exposure=0.75,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 109},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_strong_breadth_proxy_proxy_exposure_capped")
        self.assertEqual(decision.target_weights, {"AAA": 0.375, "BBB": 0.375})

    def test_decide_monthly_allocation_does_not_cap_direct_market_beta_symbol(self):
        decision = decide_monthly_allocation(
            {
                "069500": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=3_000),
                "AAA": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=2_000),
                "BBB": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_top_n=0,
                market_beta_proxy_max_exposure=0.50,
            ),
            portfolio_value=1_000_000,
            reference_prices={"069500": 109, "AAA": 109, "BBB": 109},
        )

        self.assertEqual(decision.mode, "market_beta")
        self.assertEqual(decision.reason, "no_train_candidate_strong_breadth")
        self.assertEqual(decision.target_weights, {"069500": 0.99})

    def test_decide_monthly_allocation_uses_proxy_for_neutral_breadth_below_alpha_threshold(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy")
        self.assertEqual(decision.target_weights, {"AAA": 0.495, "BBB": 0.495})

    def test_decide_monthly_allocation_caps_neutral_breadth_proxy_only(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                market_beta_proxy_neutral_breadth_max_exposure=0.50,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_proxy_neutral_breadth_capped")
        self.assertEqual(decision.target_weights, {"AAA": 0.25, "BBB": 0.25})

    def test_decide_monthly_allocation_keeps_strong_breadth_proxy_full_size_when_neutral_cap_set(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=3_000),
                "BBB": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=2_000),
                "CCC": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                market_beta_proxy_neutral_breadth_max_exposure=0.50,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 109},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_strong_breadth_proxy")
        self.assertEqual(decision.target_weights, {"AAA": 0.495, "BBB": 0.495})

    def test_decide_monthly_allocation_caps_neutral_high_exposure_proxy_loss_context_only(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _priced_candles("2024-01-01", [100, 106, 110, 112, 114, 115], volume=3_000),
                "BBB": _priced_candles("2024-01-01", [100, 105, 109, 111, 113, 114], volume=2_000),
                "CCC": _priced_candles("2024-01-01", [110, 108, 106, 104, 102, 101], volume=1_000),
            },
            as_of_date="2024-01-06",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=1,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                market_beta_proxy_neutral_loss_guard_max_exposure=0.55,
                market_beta_proxy_neutral_loss_guard_medium_lookback_days=4,
                market_beta_proxy_neutral_loss_guard_medium_max_return_pct=30.0,
                market_beta_proxy_neutral_loss_guard_short_lookback_days=2,
                market_beta_proxy_neutral_loss_guard_short_max_return_pct=15.0,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 115, "BBB": 114, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_proxy_neutral_loss_guard_capped")
        self.assertEqual(decision.target_weights, {"AAA": 0.275, "BBB": 0.275})

    def test_decide_monthly_allocation_scales_exposure_when_market_trend_is_negative(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.0,
                market_trend_filter_days=3,
                market_trend_min_return_pct=0.0,
                market_trend_risk_scale=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 101, "BBB": 101, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_trend_scaled")
        self.assertEqual(decision.target_weights, {"AAA": 0.2475, "BBB": 0.2475})

    def test_liquidity_universe_exposure_scale_reduces_only_meaningful_narrow_universe(self):
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=100,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            1.0,
        )
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=50,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            0.8,
        )
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=3,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            1.0,
        )

    def test_decide_monthly_allocation_scales_exposure_when_liquidity_universe_is_narrow(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                liquidity_risk_reference_top_n=6,
                liquidity_risk_min_top_n=3,
                liquidity_risk_min_scale=0.8,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_liquidity_scaled")
        self.assertEqual(decision.target_weights, {"AAA": 0.396, "BBB": 0.396})

    def test_scale_monthly_decision_targets_reduces_weights_and_marks_reason(self):
        decision = scale_monthly_decision_targets(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"AAA": 0.4, "BBB": 0.2},
                reason="selected_monthly_alpha",
            ),
            scale=0.5,
            reason_suffix="_drawdown_guard",
        )

        self.assertEqual(decision.target_weights, {"AAA": 0.2, "BBB": 0.1})
        self.assertEqual(decision.reason, "selected_monthly_alpha_drawdown_guard")

    def test_filter_symbols_by_event_score_blocks_negative_weighted_news(self):
        store = EventScoreStore(
            {
                ("AAA", "2024-01-09"): -0.9,
                ("BBB", "2024-01-09"): 0.2,
            }
        )

        symbols = filter_symbols_by_event_score(
            ["AAA", "BBB"],
            event_scores=store,
            signal_date="2024-01-10",
            lookback_days=5,
            min_entry_event_score=-0.2,
        )

        self.assertEqual(symbols, ["BBB"])

    def test_event_score_multipliers_overweight_positive_news_without_future_data(self):
        store = EventScoreStore(
            {
                ("AAA", "2024-01-09"): 0.5,
                ("AAA", "2024-01-11"): -1.0,
                ("BBB", "2024-01-09"): 0.0,
            }
        )

        multipliers = event_score_multipliers(
            ["AAA", "BBB"],
            event_scores=store,
            signal_date="2024-01-10",
            lookback_days=5,
            event_weight=0.4,
        )
        weights = target_weights_for_symbols(
            ["AAA", "BBB"],
            target_budget=0.9,
            max_position_weight=1.0,
            symbol_multipliers=multipliers,
        )

        self.assertGreater(multipliers["AAA"], multipliers["BBB"])
        self.assertGreater(weights["AAA"], weights["BBB"])

    def test_load_point_in_time_universe_groups_symbols_by_snapshot_date(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "date,symbol,name,market\n"
                "2024-01-31,5930,Samsung,KOSPI\n"
                "2024-01-31,000660,SK hynix,KOSPI\n"
                "2024-02-29,005930,Samsung,KOSPI\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)

        self.assertEqual(universe["2024-01-31"], {"005930", "000660"})
        self.assertEqual(universe["2024-02-29"], {"005930"})

    def test_point_in_time_universe_uses_snapshot_date_without_future_snapshots(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "snapshot_date,symbol,name,market\n"
                "2024-01-31,111111,Old,KOSPI\n"
                "2024-02-29,222222,Future,KOSPI\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)
            filtered = filter_symbol_candles_by_universe(
                {
                    "111111": [_candle("2024-01-01", 100), _candle("2024-01-31", 101)],
                    "222222": [_candle("2024-01-01", 100), _candle("2024-01-31", 101)],
                },
                universe,
                signal_date="2024-02-15",
                min_history_days=1,
            )

        self.assertEqual(set(filtered), {"111111"})

    def test_point_in_time_universe_excludes_after_delisting_and_before_listing(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "snapshot_date,symbol,name,market,listed_date,delisted_date\n"
                "2024-03-31,111111,Live,KOSPI,2020-01-01,\n"
                "2024-03-31,222222,Delisted,KOSPI,2020-01-01,2024-03-01\n"
                "2024-03-31,333333,Not Yet,KOSPI,2024-04-01,\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)
            filtered = filter_symbol_candles_by_universe(
                {
                    "111111": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "222222": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "333333": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                },
                universe,
                signal_date="2024-03-31",
                min_history_days=1,
            )

        self.assertEqual(set(filtered), {"111111"})

    def test_point_in_time_universe_excludes_untradable_suspended_and_managed(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "snapshot_date,symbol,name,market,tradable,is_suspended,is_managed\n"
                "2024-03-31,111111,Ok,KOSPI,true,false,false\n"
                "2024-03-31,222222,Untradable,KOSPI,false,false,false\n"
                "2024-03-31,333333,Suspended,KOSPI,true,true,false\n"
                "2024-03-31,444444,Managed,KOSPI,true,false,true\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)
            filtered = filter_symbol_candles_by_universe(
                {
                    "111111": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "222222": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "333333": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "444444": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                },
                universe,
                signal_date="2024-03-31",
                min_history_days=1,
            )

        self.assertEqual(set(filtered), {"111111"})

    def test_legacy_point_in_time_universe_infers_spac_and_preferred_from_name(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "snapshot_date,symbol,name,market\n"
                "2024-03-31,111111,정상기업,KOSPI\n"
                "2024-03-31,222222,신한제13호스팩,KOSDAQ\n"
                "2024-03-31,333333,대신증권우,KOSPI\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)
            filtered = filter_symbol_candles_by_universe(
                {
                    "111111": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "222222": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "333333": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                },
                universe,
                signal_date="2024-03-31",
                min_history_days=1,
            )

        self.assertEqual(set(filtered), {"111111"})

    def test_universe_filter_report_records_exclusion_reasons(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "universe.csv"
            output = root / "universe_filter_report.csv"
            path.write_text(
                "snapshot_date,symbol,name,market,listed_date,delisted_date,tradable,is_suspended\n"
                "2024-03-31,111111,Ok,KOSPI,2020-01-01,,true,false\n"
                "2024-03-31,222222,Delisted,KOSPI,2020-01-01,2024-03-01,true,false\n"
                "2024-03-31,333333,New,KOSPI,2024-03-01,,true,false\n"
                "2024-03-31,444444,Suspended,KOSPI,2020-01-01,,true,true\n",
                encoding="utf-8",
            )
            universe = load_point_in_time_universe(path)

            rows = build_universe_filter_report(
                {
                    "111111": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "222222": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                    "333333": [_candle("2024-03-29", 101)],
                    "444444": [_candle("2024-01-01", 100), _candle("2024-03-29", 101)],
                },
                universe,
                as_of_dates=["2024-03-31"],
                min_history_days=2,
            )
            saved = save_universe_filter_report(rows, output)
            text = output.read_text(encoding="utf-8")

        reasons = {row["symbol"]: row["reason"] for row in rows}
        self.assertEqual(saved, 3)
        self.assertEqual(reasons["222222"], "delisted")
        self.assertEqual(reasons["333333"], "insufficient_history")
        self.assertEqual(reasons["444444"], "suspended")
        self.assertIn("reason", text)

    def test_filter_symbol_candles_by_universe_uses_latest_snapshot_before_signal_date(self):
        universe = {
            "2024-01-31": {"LIVE"},
            "2024-02-29": {"LIVE", "NEW"},
        }

        filtered = filter_symbol_candles_by_universe(
            {
                "LIVE": [_candle("2024-01-31", 100)],
                "NEW": [_candle("2024-01-31", 100)],
            },
            universe,
            signal_date="2024-02-15",
        )

        self.assertEqual(set(filtered), {"LIVE"})

    def test_is_monthly_rebalance_due_only_once_per_month(self):
        self.assertTrue(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date=None))
        self.assertFalse(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date="2026-06-03"))
        self.assertTrue(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date="2026-05-31"))

    def test_build_order_plan_sells_removed_position_and_buys_target(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="aggressive",
                target_weights={"222222": 1.0},
                reason="unit-test",
            ),
            positions=[Position(symbol="111111", quantity=10, average_price=100)],
            cash=0,
            reference_prices={"111111": 100, "222222": 50},
            min_trade_value=0,
        )

        self.assertEqual([(order.action, order.symbol, order.quantity) for order in orders], [
            ("SELL", "111111", 10),
            ("BUY", "222222", 20),
        ])

    def test_build_order_plan_respects_cash_buffer_in_target_weights(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.49, "222222": 0.49},
                reason="cash-buffer",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000, "222222": 10_000},
            min_trade_value=0,
        )

        self.assertEqual(sum(order.estimated_value for order in orders), 980_000)

    def test_build_order_plan_reports_target_below_one_share(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.2},
                reason="small-slot",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 300_000},
            min_trade_value=0,
        )

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].action, "SKIP")
        self.assertEqual(orders[0].reason, "target_value_below_one_share")

    def test_build_order_plan_adds_adv_liquidity_and_cost_estimates(self):
        candles = [
            _candle(f"2026-05-{day:02d}", 1_000)
            for day in range(20, 32)
        ] + [
            _candle(f"2026-06-{day:02d}", 1_000)
            for day in range(1, 9)
        ]
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-10",
                signal_date="2026-06-09",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="liquidity-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 1_000},
            min_trade_value=0,
            symbol_candles={"111111": candles},
            base_slippage_rate=0.001,
            impact_slippage_multiplier=0.02,
            warn_adv_participation_rate=0.15,
            max_adv_participation_rate=0.2,
        )

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].adv_20d, 1_000_000)
        self.assertAlmostEqual(orders[0].adv_participation_rate, 0.1)
        self.assertEqual(orders[0].liquidity_status, "PASS")
        self.assertAlmostEqual(orders[0].estimated_slippage_rate, 0.003)
        self.assertAlmostEqual(orders[0].estimated_total_cost, 300)

    def test_build_order_plan_blocks_when_adv_is_unavailable(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="liquidity-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
            symbol_candles={"111111": []},
        )

        self.assertEqual(orders[0].liquidity_status, "BLOCK")
        self.assertIn("adv_unavailable", orders[0].liquidity_reason)

    def test_warn_order_plan_is_not_execution_allowed(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )

        guarded = mark_order_plan_execution(orders, risk_status_value="WARN")

        self.assertFalse(guarded[0].execution_allowed)
        self.assertEqual(guarded[0].execution_mode, "blocked")
        self.assertEqual(guarded[0].execution_block_reason, "risk_status_WARN")
        self.assertEqual(guarded[0].risk_status, "BLOCKED")
        self.assertIn("risk_status_WARN", guarded[0].risk_reasons)

    def test_pass_order_plan_is_blocked_when_production_trading_disabled(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )

        guarded = mark_order_plan_execution(orders, risk_status_value="PASS")

        self.assertFalse(guarded[0].execution_allowed)
        self.assertEqual(guarded[0].execution_mode, "blocked")
        self.assertEqual(guarded[0].execution_block_reason, "production_trading_disabled")
        self.assertEqual(guarded[0].risk_status, "BLOCKED")
        self.assertIn("production_trading_disabled", guarded[0].risk_reasons)

    def test_pass_order_plan_is_execution_allowed_only_when_enabled(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )

        guarded = mark_order_plan_execution(
            orders,
            risk_status_value="PASS",
            production_trading_enabled=True,
        )

        self.assertTrue(guarded[0].execution_allowed)
        self.assertEqual(guarded[0].execution_mode, "live_ready")
        self.assertEqual(guarded[0].execution_block_reason, "")
        self.assertEqual(guarded[0].risk_status, "PASS")
        self.assertEqual(guarded[0].risk_reasons, "")

    def test_save_order_plan_writes_execution_guard_columns(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )
        guarded = mark_order_plan_execution(orders, risk_status_value="WARN")
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "orders.csv"
            save_order_plan(guarded, output)
            with output.open(newline="", encoding="utf-8-sig") as f:
                row = next(csv.DictReader(f))

        self.assertEqual(row["execution_allowed"], "False")
        self.assertEqual(row["execution_mode"], "blocked")
        self.assertEqual(row["execution_block_reason"], "risk_status_WARN")
        self.assertEqual(row["risk_status"], "BLOCKED")
        self.assertIn("risk_status_WARN", row["risk_reasons"])
        self.assertIn("adv_20d", row)
        self.assertIn("adv_participation_rate", row)
        self.assertIn("liquidity_status", row)
        self.assertIn("liquidity_reason", row)
        self.assertIn("estimated_slippage_rate", row)
        self.assertIn("estimated_total_cost", row)

    def test_save_order_plan_summary_warns_when_orders_are_blocked(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="alpha",
            selected_preset="balanced",
            target_weights={"111111": 0.1},
            reason="unit-test",
        )
        orders = build_order_plan(
            decision,
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )
        guarded = mark_order_plan_execution(orders, risk_status_value="WARN")
        checks = [RiskCheck("performance_guard", "WARN", "thin walk-forward margin")]

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "order_summary.md"
            save_order_plan_summary(
                decision=decision,
                orders=guarded,
                risk_checks=checks,
                risk_status_value="WARN",
                output_path=output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn("Execution status: BLOCKED", text)
        self.assertIn("risk_status_WARN", text)
        self.assertIn("performance_guard", text)
        self.assertIn("BUY orders: 1", text)
        self.assertIn("Total buy value: 100000", text)

    def test_save_order_plan_summary_lists_risk_block_reasons_without_orders(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-21",
            signal_date="2026-06-18",
            mode="alpha",
            selected_preset="balanced",
            target_weights={},
            reason="performance_block_scale_0",
        )
        checks = [
            RiskCheck("deployment_gate", "BLOCK", "failed_required_scenarios:walk_forward_001"),
            RiskCheck("performance_guard", "BLOCK", "target_scale=0.0000"),
        ]

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "order_summary.md"
            save_order_plan_summary(
                decision=decision,
                orders=[],
                risk_checks=checks,
                risk_status_value="BLOCK",
                output_path=output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn("Execution status: BLOCKED", text)
        self.assertIn("Risk status: BLOCK", text)
        self.assertNotIn("- none", text)
        self.assertIn("deployment_gate: failed_required_scenarios:walk_forward_001", text)
        self.assertIn("performance_guard: target_scale=0.0000", text)

    def test_target_weights_cap_single_position_exposure(self):
        weights = target_weights_for_symbols(
            ["111111", "222222", "333333"],
            target_budget=0.98,
            max_position_weight=0.2,
        )

        self.assertEqual(weights, {"111111": 0.2, "222222": 0.2, "333333": 0.2})

    def test_select_buyable_targets_skips_unaffordable_ranked_symbols(self):
        selected = select_buyable_targets(
            ["EXPENS", "MIDCAP", "CHEAP1", "CHEAP2"],
            reference_prices={
                "EXPENS": 300_000,
                "MIDCAP": 190_000,
                "CHEAP1": 50_000,
                "CHEAP2": 30_000,
            },
            portfolio_value=1_000_000,
            target_budget=0.98,
            max_position_weight=0.2,
            min_target_value=0,
        )

        self.assertEqual(selected, ["MIDCAP", "CHEAP1", "CHEAP2"])

    def test_select_liquid_universe_uses_only_signal_date_history(self):
        selected = select_liquid_universe(
            {
                "NOW": [
                    Candle("2024-01-01", 10, 10, 10, 10, 100),
                    Candle("2024-01-02", 10, 10, 10, 10, 100),
                ],
                "FUTURE": [
                    Candle("2024-01-01", 10, 10, 10, 10, 1),
                    Candle("2024-01-02", 10, 10, 10, 10, 10_000),
                ],
            },
            signal_date="2024-01-01",
            top_n=1,
            window_days=1,
        )

        self.assertEqual(list(selected), ["NOW"])

    def test_select_point_in_time_universe_excludes_only_asof_bias_risks(self):
        selected = select_point_in_time_universe(
            {
                "STABLE": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 110),
                    _candle("2024-01-03", 110, 120),
                ],
                "FUTURE_WINNER": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 110),
                    _candle("2024-01-03", 110, 120),
                    _candle("2024-01-04", 120, 1_000),
                ],
                "RECENT_SPIKE": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 500),
                    _candle("2024-01-03", 500, 550),
                ],
                "SHORT_HISTORY": [
                    _candle("2024-01-03", 100, 120),
                ],
                "PENNY": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 90),
                    _candle("2024-01-03", 90, 80),
                ],
            },
            signal_date="2024-01-03",
            min_history_days=3,
            min_reference_price=90,
            max_trailing_return_pct=300,
            trailing_return_days=3,
        )

        self.assertEqual(list(selected), ["STABLE", "FUTURE_WINNER"])

    def test_equal_weight_buy_hold_counts_expensive_symbols_fractionally(self):
        result = equal_weight_buy_hold_period_return(
            {
                "CHEAP": [_candle("2024-01-02", 100, 200)],
                "EXPENS": [_candle("2024-01-02", 1_000, 2_000)],
            },
            start="2024-01-01",
            end="2024-01-31",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )

        self.assertAlmostEqual(result, 100.0)

    def test_diagnose_universe_bias_flags_extreme_winner_dependence(self):
        row = diagnose_universe_bias(
            {
                "NORMAL": [_candle("2024-01-02", 100, 120)],
                "WINNER": [_candle("2024-01-02", 100, 800)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            start="2024-01-01",
            end="2024-01-31",
            extreme_return_threshold_pct=500.0,
        )

        self.assertEqual(row["symbol_count"], 3)
        self.assertEqual(row["extreme_return_symbols"], 1)
        self.assertIn("high_average_symbol_return", row["warning_reasons"])
        self.assertIn("extreme_return_share", row["warning_reasons"])
        self.assertTrue(row["warning"])

    def test_exclude_top_period_return_symbols_is_stress_only_filter(self):
        selected = exclude_top_period_return_symbols(
            {
                "FLAT": [_candle("2024-01-02", 100, 100)],
                "WINNER": [_candle("2024-01-02", 100, 200)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            start="2024-01-01",
            end="2024-01-31",
            top_n=1,
        )

        self.assertEqual(set(selected), {"FLAT", "LOSER"})

    def test_rebalance_state_round_trips_last_plan_date(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.csv"
            decision = MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-18",
                mode="alpha",
                selected_preset="aggressive",
                target_weights={"005930": 0.98},
                reason="unit-test",
            )

            save_rebalance_state(decision, path)

            self.assertEqual(load_last_rebalance_date(path), "2026-06-20")

    def test_monthly_backtest_uses_only_prior_candles_and_trades_at_open(self):
        seen: list[tuple[str, str]] = []

        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            seen.append((as_of_date, latest_seen))
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 90, 90),
                    _candle("2024-02-01", 100, 110),
                    _candle("2024-02-29", 120, 120),
                ]
            },
            start="2024-02-01",
            end="2024-02-29",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            decision_provider=decision_provider,
        )

        self.assertEqual(seen, [("2024-02-01", "2024-01-31")])
        self.assertEqual(result.trade_count, 1)
        self.assertAlmostEqual(result.final_equity, 1_200)

    def test_daily_drawdown_stop_liquidates_on_next_open(self):
        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 100, 100),
                    _candle("2024-02-01", 100, 100),
                    _candle("2024-02-02", 70, 70),
                    _candle("2024-02-05", 70, 70),
                ]
            },
            start="2024-02-01",
            end="2024-02-05",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            config=MonthlyRebalanceConfig(daily_drawdown_stop_pct=-10.0),
            decision_provider=decision_provider,
        )

        self.assertEqual([(trade.date, trade.action, trade.reason) for trade in result.trades], [
            ("2024-02-01", "BUY", "unit-test"),
            ("2024-02-05", "SELL", "daily_drawdown_stop"),
        ])
        self.assertAlmostEqual(result.final_equity, 700)

    def test_position_trailing_stop_liquidates_on_next_open(self):
        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 100, 100),
                    _candle("2024-02-01", 100, 100),
                    _candle("2024-02-02", 85, 85),
                    _candle("2024-02-05", 80, 80),
                ]
            },
            start="2024-02-01",
            end="2024-02-05",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            config=MonthlyRebalanceConfig(position_trailing_stop_pct=-10.0),
            decision_provider=decision_provider,
        )

        self.assertEqual([(trade.date, trade.action, trade.reason) for trade in result.trades], [
            ("2024-02-01", "BUY", "unit-test"),
            ("2024-02-05", "SELL", "position_trailing_stop"),
        ])
        self.assertAlmostEqual(result.final_equity, 800)

    def test_position_trailing_stop_reason_filter_limits_eligible_positions(self):
        def run_with_reason(reason: str):
            def decision_provider(symbol_candles, *, as_of_date, config):
                latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
                return MonthlyDecision(
                    as_of_date=as_of_date,
                    signal_date=latest_seen,
                    mode="market_beta_proxy",
                    selected_preset="unit",
                    target_weights={"111111": 1.0},
                    reason=reason,
                )

            return run_monthly_rebalance_backtest(
                {
                    "111111": [
                        _candle("2024-01-31", 100, 100),
                        _candle("2024-02-01", 100, 100),
                        _candle("2024-02-02", 85, 85),
                        _candle("2024-02-05", 80, 80),
                    ]
                },
                start="2024-02-01",
                end="2024-02-05",
                initial_cash=1_000,
                fee_rate=0.0,
                tax_rate=0.0,
                slippage_rate=0.0,
                min_trade_value=0.0,
                config=MonthlyRebalanceConfig(
                    position_trailing_stop_pct=-10.0,
                    position_trailing_stop_reason_contains="proxy_neutral_loss_guard_capped",
                ),
                decision_provider=decision_provider,
            )

        unguarded = run_with_reason("no_train_candidate_strong_breadth_proxy")
        guarded = run_with_reason(
            "no_train_candidate_neutral_breadth_proxy_proxy_neutral_loss_guard_capped"
        )

        self.assertNotIn("position_trailing_stop", [trade.reason for trade in unguarded.trades])
        self.assertIn("position_trailing_stop", [trade.reason for trade in guarded.trades])

    def test_deep_drawdown_guard_uses_stronger_scale_on_monthly_rebalance(self):
        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 100, 100),
                    _candle("2024-02-01", 100, 100),
                    _candle("2024-02-02", 70, 70),
                    _candle("2024-03-01", 70, 70),
                ]
            },
            start="2024-02-01",
            end="2024-03-01",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            config=self._config_with_deep_drawdown_guard(),
            decision_provider=decision_provider,
        )

        self.assertEqual([(trade.date, trade.action, trade.quantity, trade.reason) for trade in result.trades], [
            ("2024-02-01", "BUY", 10, "unit-test"),
            ("2024-03-01", "SELL", 7, "unit-test_deep_drawdown_guard"),
        ])

    def _config_with_deep_drawdown_guard(self):
        return MonthlyRebalanceConfig(
            drawdown_guard_trigger_pct=-10.0,
            drawdown_guard_scale=0.75,
            drawdown_guard_deep_trigger_pct=-20.0,
            drawdown_guard_deep_scale=0.25,
        )


if __name__ == "__main__":
    unittest.main()
