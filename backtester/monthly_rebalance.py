import csv
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

from .events import EventScoreStore
from .models import Candle
from .momentum_rotation import (
    MomentumRotationConfig,
    momentum_rotation_config_for_preset,
    rank_momentum_targets,
    run_momentum_rotation_backtest,
)
from .momentum_validation import (
    generate_train_stability_windows,
    market_breadth_before_date,
    select_best_train_candidate,
    slice_asof_symbol_candles,
)


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: int
    average_price: float = 0.0


@dataclass(frozen=True)
class MonthlyDecision:
    as_of_date: str
    signal_date: str
    mode: str
    selected_preset: str
    target_weights: dict[str, float]
    reason: str


@dataclass(frozen=True)
class PlannedOrder:
    as_of_date: str
    symbol: str
    action: str
    quantity: int
    reference_price: float
    estimated_value: float
    target_weight: float
    current_quantity: int
    reason: str
    adv_20d: float = 0.0
    adv_participation_rate: float = 0.0
    liquidity_status: str = "NOT_CHECKED"
    liquidity_reason: str = ""
    estimated_slippage_rate: float = 0.0
    estimated_total_cost: float = 0.0
    execution_allowed: bool = False
    execution_mode: str = "blocked"
    execution_block_reason: str = "unmarked_order_plan"
    risk_status: str = "BLOCKED"
    risk_reasons: str = "unmarked_order_plan"


@dataclass(frozen=True)
class RiskLimits:
    max_total_target_weight: float = 1.0
    max_single_order_value: float = 2_000_000.0
    max_total_buy_value: float = 10_000_000.0
    max_total_sell_value: float = 10_000_000.0
    max_order_count: int = 15
    max_signal_age_days: int = 7
    max_daily_loss_pct: float = 3.0
    block_skip_orders: bool = True
    max_adv_participation_rate: float = 0.10
    warn_adv_participation_rate: float = 0.05
    liquidity_missing_adv_status: str = "BLOCK"


@dataclass(frozen=True)
class RiskCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class DeploymentGate:
    deployable: bool
    reason: str
    source: str = ""
    total_return_pct: float = 0.0
    buy_hold_return_pct: float = 0.0
    excess_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    trade_count: int = 0
    universe_bias_warning: bool = False


@dataclass(frozen=True)
class PerformanceGuard:
    status: str
    detail: str
    scale: float
    source: str = ""


@dataclass(frozen=True)
class MonthlyBacktestTrade:
    date: str
    symbol: str
    action: str
    price: float
    quantity: int
    cash_after: float
    reason: str


@dataclass(frozen=True)
class MonthlyBacktestResult:
    initial_cash: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    decisions: list[MonthlyDecision]
    trades: list[MonthlyBacktestTrade]
    dates: list[str]
    equity_curve: list[float]


@dataclass(frozen=True)
class MonthlyValidationCase:
    name: str
    category: str
    start: str
    end: str
    train_start: str = ""
    train_end: str = ""
    required: bool = True
    slippage_multiplier: float = 1.0
    stress_exclude_return_above: float | None = None
    stress_exclude_top_return_symbols: int = 0
    liquidity_top_n: int | None = None
    stress: str = ""


@dataclass(frozen=True)
class MonthlyRebalanceConfig:
    train_years: int = 5
    train_start: str | None = None
    presets: tuple[str, ...] = ("balanced",)
    min_train_trades: int = 1
    min_train_positive_ratio: float = 0.5
    train_stability_years: int = 2
    min_rows_per_window: int = 120
    start_grace_days: int = 14
    fallback_breadth_days: int = 120
    fallback_breadth_threshold: float = 0.5
    market_beta_breadth_threshold: float = 0.25
    market_trend_filter_days: int = 60
    market_trend_min_return_pct: float = -5.0
    market_trend_risk_scale: float = 0.25
    market_volatility_filter_days: int = 0
    market_volatility_target_pct: float = 25.0
    market_volatility_min_scale: float = 0.25
    drawdown_guard_trigger_pct: float = -15.0
    drawdown_guard_scale: float = 0.75
    drawdown_guard_deep_trigger_pct: float = 0.0
    drawdown_guard_deep_scale: float = 0.5
    daily_drawdown_stop_pct: float = 0.0
    daily_drawdown_cooldown_days: int = 20
    position_trailing_stop_pct: float = 0.0
    position_trailing_stop_reason_contains: str = ""
    weak_breadth_min_train_avg_excess_pct: float = 10.0
    cash_buffer_weight: float = 0.01
    max_position_weight: float = 0.15
    candidate_pool_size: int = 7
    min_target_value: float = 10_000.0
    max_candidate_lookback_return_pct: float = 90.0
    direct_alpha_target_persistence_signals: int = 1
    point_in_time_liquidity_top_n: int = 100
    point_in_time_liquidity_window_days: int = 20
    liquidity_risk_reference_top_n: int = 100
    liquidity_risk_min_scale: float = 0.8
    liquidity_risk_min_top_n: int = 20
    point_in_time_min_history_days: int = 252
    point_in_time_min_reference_price: float = 1_000.0
    point_in_time_max_trailing_return_pct: float = 300.0
    point_in_time_trailing_return_days: int = 252
    point_in_time_universe: dict[str, set[str]] | None = None
    market_beta_symbol: str = "069500"
    market_beta_proxy_size: int = 12
    market_beta_proxy_max_exposure: float = 1.0
    market_beta_proxy_neutral_breadth_max_exposure: float = 1.0
    market_beta_proxy_neutral_loss_guard_max_exposure: float = 1.0
    market_beta_proxy_neutral_loss_guard_medium_lookback_days: int = 0
    market_beta_proxy_neutral_loss_guard_medium_max_return_pct: float = 0.0
    market_beta_proxy_neutral_loss_guard_short_lookback_days: int = 0
    market_beta_proxy_neutral_loss_guard_short_max_return_pct: float = 0.0
    market_beta_proxy_reversal_guard_max_exposure: float = 1.0
    market_beta_proxy_reversal_guard_medium_lookback_days: int = 0
    market_beta_proxy_reversal_guard_medium_return_pct: float = 0.0
    market_beta_proxy_reversal_guard_short_lookback_days: int = 0
    market_beta_proxy_reversal_guard_short_max_return_pct: float = 0.0
    market_beta_proxy_reversal_guard_extreme_return_pct: float = 0.0
    market_beta_proxy_reversal_guard_medium_drawdown_pct: float = 0.0
    market_beta_proxy_reversal_guard_recovery_exit_short_return_pct: float = 0.0
    market_beta_proxy_buyable_only: bool = False
    market_beta_proxy_unbuyable_cash_reserve: bool = False
    event_scores: EventScoreStore | None = None
    event_lookback_days: int = 5
    min_entry_event_score: float = -0.2
    event_weight: float = 0.25
    min_event_weight_multiplier: float = 0.5
    max_event_weight_multiplier: float = 1.5


@dataclass(frozen=True)
class UniverseMember:
    snapshot_date: str
    symbol: str
    name: str = ""
    market: str = ""
    listed_date: str = ""
    delisted_date: str = ""
    is_active: str = ""
    is_suspended: str = ""
    is_managed: str = ""
    is_spac: str = ""
    is_preferred: str = ""
    tradable: str = ""


class PointInTimeUniverse(dict[str, set[str]]):
    def __init__(
        self,
        snapshots: dict[str, set[str]] | None = None,
        *,
        members_by_date: dict[str, list[UniverseMember]] | None = None,
    ) -> None:
        super().__init__(snapshots or {})
        self.members_by_date = members_by_date or {}


ORDER_COLUMNS = [
    "as_of_date",
    "symbol",
    "action",
    "quantity",
    "reference_price",
    "estimated_value",
    "target_weight",
    "current_quantity",
    "reason",
    "adv_20d",
    "adv_participation_rate",
    "liquidity_status",
    "liquidity_reason",
    "estimated_slippage_rate",
    "estimated_total_cost",
    "execution_allowed",
    "execution_mode",
    "execution_block_reason",
    "risk_status",
    "risk_reasons",
]

DECISION_COLUMNS = ["as_of_date", "signal_date", "mode", "selected_preset", "reason", "target_weights"]

STATE_COLUMNS = ["last_rebalance_date", "signal_date", "mode", "selected_preset", "reason"]

RISK_COLUMNS = ["name", "status", "detail"]
PERFORMANCE_AUDIT_COLUMNS = ["name", "status", "detail"]

VALIDATION_FAILURE_COLUMNS = [
    "name",
    "category",
    "reason",
    "severity",
    "failed_metric",
    "metric_value",
    "threshold",
    "suggested_action",
    "parameter_hints",
    "start",
    "end",
    "selected_preset",
    "train_excess_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "trade_count",
    "stress",
    "source",
]

VALIDATION_REMEDIATION_COLUMNS = [
    "priority",
    "suggested_action",
    "failure_count",
    "blocked_count",
    "affected_categories",
    "affected_scenarios",
    "failed_metrics",
    "worst_metric_value",
    "parameter_hints",
    "next_experiment",
]

VALIDATION_SWEEP_PLAN_COLUMNS = [
    "priority",
    "suggested_action",
    "experiment_id",
    "target_scenarios",
    "cash_buffer_weight",
    "min_train_positive_ratio",
    "candidate_pool_size",
    "market_beta_proxy_max_exposure",
    "market_beta_proxy_neutral_breadth_max_exposure",
    "max_position_weight",
    "drawdown_guard_scale",
    "drawdown_guard_deep_trigger_pct",
    "drawdown_guard_deep_scale",
    "market_volatility_min_scale",
    "position_trailing_stop_pct",
    "position_trailing_stop_reason_contains",
    "expected_effect",
    "risk_note",
]

VALIDATION_SWEEP_RESULT_COLUMNS = [
    "experiment_id",
    "suggested_action",
    "status",
    "target_scenarios",
    "scenario_count",
    "failed_required",
    "baseline_failed_required",
    "failed_delta",
    "min_excess_return_pct",
    "worst_drawdown_pct",
    "trade_count",
    "config_changes",
    "candidate_validation_args",
    "validation_scope",
    "adoption_status",
    "adoption_requirements",
    "result_summary",
    "risk_note",
]

VALIDATION_CANDIDATE_FOLLOWUP_COLUMNS = [
    "priority_rank",
    "experiment_id",
    "status",
    "adoption_status",
    "failed_delta",
    "candidate_validation_args",
    "candidate_scenario_output",
    "candidate_gate_output",
    "comparison_output",
    "delta_output",
    "decision_output",
    "validation_command",
    "comparison_command",
    "risk_note",
]

VALIDATION_COMPARISON_COLUMNS = [
    "baseline_label",
    "candidate_label",
    "status",
    "baseline_failed_required",
    "candidate_failed_required",
    "failed_delta",
    "resolved_failures",
    "new_failures",
    "unchanged_failures",
    "summary",
]

VALIDATION_SCENARIO_DELTA_COLUMNS = [
    "name",
    "classification",
    "baseline_label",
    "candidate_label",
    "baseline_deployable",
    "candidate_deployable",
    "baseline_reason",
    "candidate_reason",
    "baseline_excess_return_pct",
    "candidate_excess_return_pct",
    "excess_return_delta",
    "baseline_max_drawdown_pct",
    "candidate_max_drawdown_pct",
    "max_drawdown_delta",
    "baseline_trade_count",
    "candidate_trade_count",
    "trade_count_delta",
    "diagnostic",
]

VALIDATION_CANDIDATE_DECISION_COLUMNS = [
    "candidate_label",
    "comparison_status",
    "decision",
    "decision_reasons",
    "baseline_failed_required",
    "candidate_failed_required",
    "failed_delta",
    "resolved_count",
    "new_failure_count",
    "unchanged_failure_count",
    "resolved_failure_names",
    "new_failure_names",
    "unchanged_failure_names",
    "new_failure_diagnostics",
    "recommendation",
]

VALIDATION_CANDIDATE_SUMMARY_COLUMNS = [
    "candidate_rank",
    "candidate_label",
    "decision",
    "comparison_status",
    "baseline_failed_required",
    "candidate_failed_required",
    "failed_delta",
    "resolved_count",
    "new_failure_count",
    "unchanged_failure_count",
    "drawdown_buffer_regression_count",
    "equity_improved_new_failure_count",
    "path_scenario_count",
    "path_days_compared",
    "path_equity_regression_days",
    "path_equity_improved_days",
    "path_drawdown_regression_days",
    "path_symbol_rotation_days",
    "path_higher_turnover_days",
    "path_higher_trade_cost_days",
    "path_min_equity_delta",
    "path_worst_drawdown_delta_pct",
    "path_max_rolling_peak_delta",
    "path_drawdown_threshold_pct",
    "path_acceptance_decision",
    "path_rejection_reasons",
    "path_candidate_drawdown_breach_days",
    "path_equity_improved_drawdown_breach_days",
    "path_peak_buffer_loss_days",
    "evaluation_score",
    "resolved_failure_names",
    "new_failure_names",
    "new_failure_diagnostics",
    "summary",
    "recommendation",
]

VALIDATION_FAILURE_PATTERN_COLUMNS = [
    "scenario",
    "baseline_failed",
    "baseline_reason",
    "failed_candidate_count",
    "new_failure_candidate_count",
    "resolved_candidate_count",
    "unchanged_failure_candidate_count",
    "candidate_labels_failed",
    "candidate_labels_new_failure",
    "candidate_labels_resolved",
    "candidate_labels_unchanged",
    "dominant_diagnostic",
    "pattern_status",
    "suggested_action",
    "notes",
]

VALIDATION_FAILURE_DRILLDOWN_COLUMNS = [
    "scenario",
    "category",
    "pattern_status",
    "suggested_action",
    "baseline_reason",
    "likely_root_cause",
    "train_start",
    "train_end",
    "selected_preset",
    "train_excess_return_pct",
    "train_candidate_scores",
    "train_candidate_decision_profiles",
    "train_candidate_direct_scores",
    "train_direct_diagnostics",
    "start",
    "end",
    "baseline_excess_return_pct",
    "baseline_max_drawdown_pct",
    "baseline_trade_count",
    "candidate_count",
    "candidate_labels",
    "candidate_excess_delta_min",
    "candidate_excess_delta_median",
    "candidate_drawdown_delta_median",
    "candidate_trade_delta_median",
    "dominant_diagnostic",
    "evidence_gaps",
    "next_action",
]

DIRECT_ALPHA_SELECTION_COLUMNS = [
    "scenario",
    "preset",
    "symbol",
    "category",
    "train_start",
    "train_end",
    "selection_status",
    "selection_rank",
    "selection_weight",
    "rejection_reason",
    "momentum_score_pct",
    "average_trading_value",
    "symbol_train_return_pct",
    "benchmark_weight",
    "benchmark_avg_return_pct",
    "benchmark_median_return_pct",
    "candidate_total_return_pct",
    "candidate_buy_hold_return_pct",
    "candidate_excess_return_pct",
    "candidate_max_drawdown_pct",
    "candidate_trade_count",
    "candidate_buy_count",
    "candidate_sell_count",
    "candidate_unique_traded_symbols",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
]

DIRECT_ALPHA_HOLDING_PATH_COLUMNS = [
    "scenario",
    "preset",
    "rebalance_date",
    "category",
    "train_start",
    "train_end",
    "event_type",
    "holding_count",
    "held_symbols",
    "held_weights",
    "entered_symbols",
    "exited_symbols",
    "train_end_selected_symbols",
    "snapshot_overlap_count",
    "snapshot_overlap_symbols",
    "holding_not_in_train_end_snapshot",
    "train_end_selected_missing_from_holdings",
    "benchmark_symbol_count",
    "benchmark_symbols",
    "benchmark_avg_return_pct",
    "benchmark_median_return_pct",
    "candidate_total_return_pct",
    "candidate_buy_hold_return_pct",
    "candidate_excess_return_pct",
    "candidate_max_drawdown_pct",
    "candidate_trade_count",
    "candidate_buy_count",
    "candidate_sell_count",
    "candidate_unique_traded_symbols",
    "rebalance_trade_count",
    "rebalance_buy_count",
    "rebalance_sell_count",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
]

DIRECT_ALPHA_PATH_DRIFT_COLUMNS = [
    "scenario",
    "preset",
    "rebalance_date",
    "category",
    "train_start",
    "train_end",
    "event_type",
    "active_rebalance_index",
    "previous_active_rebalance_date",
    "days_since_previous_active_rebalance",
    "first_trade_date",
    "first_trade_delay_days",
    "holding_count",
    "held_symbols",
    "train_end_selected_symbols",
    "snapshot_overlap_count",
    "symbol",
    "path_role",
    "path_gap_reason",
    "in_actual_holdings",
    "in_train_end_selected_snapshot",
    "actual_weight",
    "snapshot_weight",
    "benchmark_weight",
    "symbol_train_return_pct",
    "actual_contribution_pct",
    "snapshot_contribution_pct",
    "benchmark_contribution_pct",
    "contribution_delta_pct",
    "actual_vs_snapshot_contribution_delta_pct",
    "candidate_excess_return_pct",
    "benchmark_avg_return_pct",
    "benchmark_median_return_pct",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
]

DIRECT_ALPHA_TIMING_COLUMNS = [
    "scenario",
    "preset",
    "scheduled_rebalance_date",
    "category",
    "train_start",
    "train_end",
    "scheduled_rebalance_index",
    "signal_date",
    "previous_scheduled_rebalance_date",
    "days_since_previous_scheduled_rebalance",
    "first_trade_date",
    "first_trade_delay_days",
    "train_end_selected_count",
    "train_end_selected_symbols",
    "scheduled_target_count",
    "scheduled_target_symbols",
    "actual_held_count",
    "actual_held_symbols",
    "snapshot_target_overlap_count",
    "snapshot_target_overlap_symbols",
    "snapshot_actual_overlap_count",
    "snapshot_actual_overlap_symbols",
    "snapshot_missing_from_scheduled_targets",
    "snapshot_missing_from_actual_holdings",
    "scheduled_targets_not_in_snapshot",
    "available_snapshot_symbols",
    "unavailable_snapshot_symbols",
    "missed_snapshot_reason",
    "previous_target_overlap_count",
    "current_target_overlap_count",
    "next_target_overlap_count",
    "best_timing_offset",
    "best_timing_overlap_count",
    "timing_diagnostic",
    "candidate_excess_return_pct",
    "benchmark_avg_return_pct",
    "benchmark_median_return_pct",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
]

DIRECT_ALPHA_RANK_DRIFT_COLUMNS = [
    "scenario",
    "preset",
    "scheduled_rebalance_date",
    "signal_date",
    "category",
    "train_start",
    "train_end",
    "scheduled_rebalance_index",
    "symbol",
    "symbol_role",
    "in_train_end_selected_snapshot",
    "in_scheduled_targets",
    "in_actual_holdings",
    "train_end_rank",
    "scheduled_rank",
    "rank_delta",
    "train_end_target_rank",
    "scheduled_target_rank",
    "train_end_momentum_score_pct",
    "scheduled_momentum_score_pct",
    "momentum_delta_pct",
    "train_end_rejection_reason",
    "scheduled_rejection_reason",
    "train_end_average_trading_value",
    "scheduled_average_trading_value",
    "market_breadth_at_signal",
    "market_breadth_allows_entry",
    "ranking_top_n_at_signal",
    "ranking_trend_filter_days_at_signal",
    "train_end_selected_count",
    "scheduled_target_count",
    "actual_held_count",
    "train_end_selected_symbols",
    "scheduled_target_symbols",
    "actual_held_symbols",
    "snapshot_target_overlap_count",
    "drop_reason",
    "timing_diagnostic",
    "candidate_excess_return_pct",
    "benchmark_avg_return_pct",
    "benchmark_median_return_pct",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
]

MONTHLY_TRAIN_DECISION_PATH_COLUMNS = [
    "scenario",
    "walk_forward_preset",
    "as_of_date",
    "signal_date",
    "category",
    "decision_mode",
    "decision_selected_preset",
    "decision_reason",
    "alpha_block_reason",
    "decision_family",
    "target_symbol_count",
    "target_symbols",
    "target_exposure",
    "cash_weight",
    "inner_train_start",
    "inner_train_end",
    "prior_breadth",
    "fallback_breadth_threshold",
    "market_beta_breadth_threshold",
    "trend_scale",
    "volatility_scale",
    "liquidity_scale",
    "exposure_scale",
    "direct_candidate_count",
    "eligible_direct_candidate_count",
    "direct_candidate_scores",
    "direct_candidate_rejection_reasons",
    "best_direct_preset",
    "best_direct_score",
    "best_direct_excess_return_pct",
    "best_direct_trade_count",
    "best_direct_train_positive_ratio",
    "outer_train_total_return_pct",
    "outer_train_buy_hold_return_pct",
    "outer_train_excess_return_pct",
    "outer_train_max_drawdown_pct",
    "outer_train_trade_count",
    "outer_train_decision_count",
    "outer_train_alpha_ratio",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
    "filter_error",
]

MONTHLY_TRAIN_STABILITY_WINDOW_COLUMNS = [
    "scenario",
    "walk_forward_preset",
    "as_of_date",
    "signal_date",
    "category",
    "decision_mode",
    "decision_selected_preset",
    "decision_reason",
    "alpha_block_reason",
    "prior_breadth",
    "fallback_breadth_threshold",
    "market_beta_breadth_threshold",
    "trend_scale",
    "volatility_scale",
    "liquidity_scale",
    "exposure_scale",
    "direct_candidate_count",
    "eligible_direct_candidate_count",
    "best_direct_preset",
    "best_direct_excess_return_pct",
    "best_direct_train_positive_ratio",
    "train_decision_as_of",
    "inner_train_start",
    "inner_train_end",
    "candidate_name",
    "candidate_rank",
    "candidate_positive_ratio",
    "candidate_eligible",
    "stability_window",
    "stability_window_index",
    "stability_start",
    "stability_end",
    "stability_window_start",
    "stability_window_end",
    "stability_window_days",
    "preset",
    "subwindow_counted_flag",
    "subwindow_symbol_count",
    "subwindow_total_return_pct",
    "subwindow_buy_hold_return_pct",
    "subwindow_excess_return_pct",
    "subwindow_max_drawdown_pct",
    "subwindow_trade_count",
    "subwindow_positive_flag",
    "subwindow_rejection_reasons",
    "stability_total_return_pct",
    "stability_buy_hold_return_pct",
    "stability_excess_return_pct",
    "stability_max_drawdown_pct",
    "stability_trade_count",
    "stability_positive",
    "stability_failed_reason",
    "stability_selected_symbol_count",
    "stability_selected_symbols",
    "stability_benchmark_avg_return_pct",
    "stability_benchmark_median_return_pct",
    "stability_selected_avg_return_pct",
    "stability_selected_median_return_pct",
    "stability_selected_vs_benchmark_avg_return_delta_pct",
    "stability_selected_underperformed_benchmark",
    "stability_traded_symbol_count",
    "stability_traded_symbols",
    "stability_selected_not_traded_symbols",
    "stability_traded_not_selected_symbols",
    "stability_underperformance_driver",
    "candidate_total_return_pct",
    "candidate_buy_hold_return_pct",
    "candidate_excess_return_pct",
    "candidate_max_drawdown_pct",
    "candidate_trade_count",
    "candidate_train_subwindows",
    "candidate_train_positive_subwindows",
    "candidate_train_positive_ratio",
    "candidate_train_avg_subwindow_excess_pct",
    "candidate_train_worst_subwindow_excess_pct",
    "candidate_rejection_reasons",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "train_symbols",
    "universe_removed",
    "pit_filter_removed",
    "liquidity_removed",
    "train_coverage_removed",
    "filter_error",
]

MONTHLY_TRAIN_STABILITY_SUMMARY_COLUMNS = [
    "scenario",
    "walk_forward_preset",
    "category",
    "candidate_name",
    "candidate_rank",
    "train_decision_count",
    "eligible_decision_count",
    "low_positive_ratio_decision_count",
    "counted_subwindow_count",
    "positive_subwindow_count",
    "negative_subwindow_count",
    "negative_subwindow_ratio",
    "no_trade_subwindow_count",
    "no_trade_benchmark_positive_count",
    "no_trade_total_benchmark_return_pct",
    "no_trade_avg_benchmark_return_pct",
    "candidate_positive_ratio_min",
    "candidate_positive_ratio_max",
    "candidate_positive_ratio_median",
    "avg_stability_excess_return_pct",
    "worst_stability_excess_return_pct",
    "dominant_failed_reason",
    "failed_reason_counts",
    "underperformance_driver_counts",
    "negative_stability_windows",
    "diagnostic",
    "next_action",
]

MONTHLY_TRAIN_STABILITY_SYMBOL_ATTRIBUTION_COLUMNS = [
    "scenario",
    "walk_forward_preset",
    "as_of_date",
    "signal_date",
    "category",
    "decision_mode",
    "alpha_block_reason",
    "candidate_rejection_reasons",
    "candidate_positive_ratio",
    "stability_window_start",
    "stability_window_end",
    "stability_excess_return_pct",
    "stability_trade_count",
    "stability_failed_reason",
    "stability_underperformance_driver",
    "symbol",
    "stability_symbol_role",
    "in_stability_selected",
    "in_stability_traded",
    "symbol_return_pct",
    "selected_weight",
    "traded_weight",
    "benchmark_weight",
    "selected_contribution_pct",
    "traded_contribution_pct",
    "benchmark_contribution_pct",
    "selected_vs_benchmark_contribution_delta_pct",
    "traded_vs_selected_contribution_delta_pct",
    "selected_symbol_count",
    "traded_symbol_count",
    "train_symbols",
    "raw_symbols",
    "universe_symbols",
    "pit_symbols",
    "liquid_symbols",
    "liquidity_removed",
    "train_coverage_removed",
]

MONTHLY_TRAIN_STABILITY_PATH_DRIFT_EXPERIMENT_COLUMNS = [
    "scenario",
    "walk_forward_preset",
    "as_of_date",
    "signal_date",
    "category",
    "decision_mode",
    "alpha_block_reason",
    "candidate_rejection_reasons",
    "candidate_positive_ratio",
    "stability_window_start",
    "stability_window_end",
    "stability_excess_return_pct",
    "stability_trade_count",
    "stability_failed_reason",
    "stability_underperformance_driver",
    "experiment_family",
    "paper_only",
    "actual_traded_contribution_pct",
    "selected_snapshot_contribution_pct",
    "benchmark_contribution_pct",
    "path_drift_delta_pct",
    "estimated_target_persistence_delta_pct",
    "selected_not_traded_count",
    "traded_not_selected_count",
    "selected_and_traded_count",
    "selected_not_traded_contribution_pct",
    "traded_not_selected_contribution_pct",
    "target_persistence_candidate",
    "slower_rebalance_candidate",
    "delayed_entry_candidate",
    "experiment_recommendation",
    "candidate_status",
    "risk_note",
]

PERFORMANCE_CONCENTRATION_COLUMNS = [
    "source",
    "start",
    "end",
    "top_1_month_contribution",
    "top_3_month_contribution",
    "top_5_symbol_contribution",
    "best_month",
    "worst_month",
    "positive_month_ratio",
    "rolling_3m_return_min",
    "rolling_6m_return_min",
    "max_recovery_months_if_possible",
    "concentration_status",
    "concentration_reasons",
]

MONTHLY_DRAWDOWN_ATTRIBUTION_COLUMNS = [
    "month",
    "start_date",
    "end_date",
    "start_equity",
    "end_equity",
    "equity_change",
    "return_pct",
    "worst_equity",
    "worst_drawdown_pct",
    "status",
]

MONTHLY_BENCHMARK_EXCESS_COLUMNS = [
    "scenario",
    "month",
    "start_date",
    "end_date",
    "strategy_return_pct",
    "benchmark_return_pct",
    "monthly_excess_return_pct",
    "strategy_equity_change",
    "strategy_worst_drawdown_pct",
    "excess_status",
    "diagnostic",
]

MONTHLY_BENCHMARK_CONTRIBUTION_COLUMNS = [
    "scenario",
    "month",
    "start_date",
    "end_date",
    "decision_as_of_date",
    "decision_reason",
    "symbol",
    "contribution_role",
    "strategy_weight",
    "benchmark_weight",
    "symbol_return_pct",
    "strategy_contribution_pct",
    "benchmark_contribution_pct",
    "contribution_delta_pct",
    "diagnostic",
]

MONTHLY_BENCHMARK_SELECTION_COLUMNS = [
    "scenario",
    "month",
    "start_date",
    "end_date",
    "decision_as_of_date",
    "decision_signal_date",
    "decision_reason",
    "symbol",
    "contribution_role",
    "strategy_weight",
    "benchmark_weight",
    "symbol_return_pct",
    "contribution_delta_pct",
    "contribution_diagnostic",
    "liquidity_rank",
    "average_trading_value",
    "proxy_cutoff_rank",
    "rank_gap_to_proxy_cutoff",
    "selection_diagnostic",
]

MONTHLY_BENCHMARK_SELECTION_SUMMARY_COLUMNS = [
    "scenario",
    "month",
    "start_date",
    "end_date",
    "row_count",
    "selected_proxy_count",
    "selected_proxy_winner_count",
    "selected_proxy_loser_count",
    "selected_proxy_delta_pct",
    "missed_benchmark_winner_count",
    "missed_benchmark_winner_delta_pct",
    "missed_inside_proxy_cutoff_count",
    "missed_inside_proxy_cutoff_delta_pct",
    "missed_rank_13_50_count",
    "missed_rank_13_50_delta_pct",
    "missed_rank_51_100_count",
    "missed_rank_51_100_delta_pct",
    "missed_rank_101_200_count",
    "missed_rank_101_200_delta_pct",
    "missed_rank_201_500_count",
    "missed_rank_201_500_delta_pct",
    "missed_rank_501_plus_count",
    "missed_rank_501_plus_delta_pct",
    "missed_rank_missing_count",
    "missed_rank_missing_delta_pct",
    "low_liquidity_missed_winner_delta_share",
    "avoided_benchmark_loser_count",
    "avoided_benchmark_loser_delta_pct",
    "diagnostic",
]

MONTHLY_BENCHMARK_SELECTION_SUMMARY_COMPARISON_COLUMNS = [
    "scenario",
    "deployable",
    "reason",
    "excess_return_pct",
    "max_drawdown_pct",
    "month_count",
    "low_liquidity_drag_month_count",
    "selected_proxy_count",
    "selected_proxy_winner_count",
    "selected_proxy_loser_count",
    "selected_proxy_loser_share",
    "selected_proxy_delta_pct",
    "selected_proxy_delta_per_selected_pct",
    "negative_selected_proxy_month_count",
    "worst_selected_proxy_month",
    "worst_selected_proxy_delta_pct",
    "missed_benchmark_winner_delta_pct",
    "missed_rank_501_plus_delta_pct",
    "low_liquidity_missed_winner_delta_share",
    "worst_missed_month",
    "worst_missed_month_delta_pct",
    "diagnostic",
]

MONTHLY_BENCHMARK_SELECTION_WINDOW_COMPARISON_COLUMNS = [
    "scenario",
    "window",
    "deployable",
    "reason",
    "window_start_month",
    "window_end_month",
    "window_start_date",
    "window_end_date",
    "month_count",
    "strategy_return_pct",
    "benchmark_return_pct",
    "window_excess_return_pct",
    "selected_proxy_count",
    "selected_proxy_delta_pct",
    "selected_proxy_delta_per_selected_pct",
    "negative_selected_proxy_month_count",
    "missed_benchmark_winner_delta_pct",
    "diagnostic",
]

MONTHLY_ENTRY_MONTH_COMPARISON_COLUMNS = [
    "month",
    "failed_label",
    "reference_label",
    "failed_start_date",
    "reference_start_date",
    "start_date_delta_days",
    "failed_end_date",
    "reference_end_date",
    "failed_strategy_return_pct",
    "reference_strategy_return_pct",
    "strategy_return_delta",
    "failed_benchmark_return_pct",
    "reference_benchmark_return_pct",
    "benchmark_return_delta",
    "failed_monthly_excess_return_pct",
    "reference_monthly_excess_return_pct",
    "monthly_excess_delta",
    "failed_selected_proxy_delta_pct",
    "reference_selected_proxy_delta_pct",
    "selected_proxy_delta_delta",
    "failed_missed_benchmark_winner_delta_pct",
    "reference_missed_benchmark_winner_delta_pct",
    "missed_benchmark_winner_delta_delta",
    "failed_decision_as_of_date",
    "reference_decision_as_of_date",
    "failed_signal_date",
    "reference_signal_date",
    "failed_reason",
    "reference_reason",
    "failed_target_exposure",
    "reference_target_exposure",
    "target_exposure_delta",
    "failed_cash_weight",
    "reference_cash_weight",
    "cash_weight_delta",
    "shared_symbol_count",
    "failed_only_symbols",
    "reference_only_symbols",
    "failed_selected_symbols",
    "reference_selected_symbols",
    "diagnostic",
]

MONTHLY_ENTRY_PATH_SUBPERIOD_COMPARISON_COLUMNS = [
    "subperiod",
    "failed_label",
    "reference_label",
    "start_date",
    "end_date",
    "trading_days",
    "return_pct",
    "average_exposure",
    "end_position_symbols",
    "return_delta_vs_reference_post",
    "average_exposure_delta_vs_reference_post",
    "shared_with_reference_post_symbol_count",
    "only_symbols_vs_reference_post",
    "reference_only_symbols",
    "diagnostic",
]

MONTHLY_ENTRY_CONTRIBUTION_OVERLAP_COMPARISON_COLUMNS = [
    "bucket",
    "failed_label",
    "reference_label",
    "month",
    "failed_start_date",
    "reference_start_date",
    "failed_end_date",
    "reference_end_date",
    "failed_symbol_count",
    "reference_symbol_count",
    "shared_symbol_count",
    "failed_symbols",
    "reference_symbols",
    "failed_strategy_weight",
    "reference_strategy_weight",
    "strategy_weight_delta",
    "failed_strategy_contribution_pct",
    "reference_strategy_contribution_pct",
    "contribution_delta_pct",
    "contribution_gap_share_pct",
    "diagnostic",
]

MONTHLY_ENTRY_SELECTION_ROTATION_COMPARISON_COLUMNS = [
    "symbol",
    "rotation_role",
    "failed_label",
    "reference_label",
    "month",
    "failed_selected",
    "reference_selected",
    "failed_start_date",
    "reference_start_date",
    "failed_decision_as_of_date",
    "reference_decision_as_of_date",
    "failed_signal_date",
    "reference_signal_date",
    "failed_decision_reason",
    "reference_decision_reason",
    "failed_strategy_weight",
    "reference_strategy_weight",
    "strategy_weight_delta",
    "failed_symbol_return_pct",
    "reference_symbol_return_pct",
    "symbol_return_delta",
    "failed_contribution_delta_pct",
    "reference_contribution_delta_pct",
    "contribution_delta_gap_pct",
    "failed_liquidity_rank",
    "reference_liquidity_rank",
    "liquidity_rank_delta",
    "failed_selection_diagnostic",
    "reference_selection_diagnostic",
    "diagnostic",
]

MONTHLY_ENTRY_SELECTION_ELIGIBILITY_COMPARISON_COLUMNS = [
    "symbol",
    "rotation_role",
    "failed_label",
    "reference_label",
    "failed_selected",
    "reference_selected",
    "failed_signal_date",
    "reference_signal_date",
    "failed_universe_status",
    "failed_universe_reason",
    "failed_universe_detail",
    "reference_universe_status",
    "reference_universe_reason",
    "reference_universe_detail",
    "failed_selection_diagnostic",
    "reference_selection_diagnostic",
    "contribution_delta_gap_pct",
    "diagnostic",
]

SYMBOL_REALIZED_PNL_ATTRIBUTION_COLUMNS = [
    "symbol",
    "realized_pnl",
    "realized_return_pct",
    "buy_value",
    "sell_value",
    "quantity_bought",
    "quantity_sold",
    "open_quantity",
    "unmatched_sell_quantity",
    "trade_count",
    "first_trade_date",
    "last_trade_date",
    "status",
]

MONTHLY_DECISION_ATTRIBUTION_COLUMNS = [
    "as_of_date",
    "signal_date",
    "mode",
    "selected_preset",
    "position_count",
    "selected_symbols",
    "target_exposure",
    "cash_weight",
    "max_position_weight",
    "min_position_weight",
    "target_weights",
    "reason",
]

MONTHLY_PROXY_DECISION_DIAGNOSTIC_COLUMNS = [
    "scenario",
    "as_of_date",
    "signal_date",
    "month",
    "month_return_pct",
    "month_status",
    "month_equity_change",
    "mode",
    "reason",
    "target_exposure",
    "cash_weight",
    "position_count",
    "selected_symbols",
    "prior_breadth",
    "fallback_breadth_threshold",
    "market_beta_breadth_threshold",
    "trend_scale",
    "volatility_scale",
    "liquidity_scale",
    "exposure_scale",
    "direct_candidate_count",
    "eligible_direct_candidate_count",
    "best_direct_excess_return_pct",
    "best_direct_train_positive_ratio",
    "direct_candidate_rejection_reasons",
    "proxy_reversal_guard_triggered",
    "proxy_reversal_guard_cap",
    "proxy_reversal_guard_medium_return_pct",
    "proxy_reversal_guard_short_return_pct",
    "proxy_reversal_guard_medium_drawdown_pct",
    "proxy_reversal_guard_reason",
    "diagnostic",
    "recommended_next_action",
]

MONTHLY_PROXY_DECISION_CONTEXT_SUMMARY_COLUMNS = [
    "scenario",
    "breadth_context",
    "exposure_bucket",
    "proxy_month_count",
    "loss_month_count",
    "gain_month_count",
    "high_exposure_loss_count",
    "gain_participation_count",
    "guard_triggered_count",
    "avg_month_return_pct",
    "total_month_return_pct",
    "avg_target_exposure",
    "avg_cash_weight",
    "min_prior_breadth",
    "max_prior_breadth",
    "months",
    "recommended_candidate_focus",
    "diagnostic",
    "paper_only",
    "risk_note",
]

MONTHLY_GUARDED_LOSS_POSITION_PRESSURE_COLUMNS = [
    "scenario",
    "month",
    "as_of_date",
    "signal_date",
    "month_return_pct",
    "target_exposure",
    "cash_weight",
    "guard_reason",
    "guard_medium_return_pct",
    "guard_short_return_pct",
    "guard_medium_drawdown_pct",
    "selected_symbol_count",
    "selected_loss_symbol_count",
    "selected_loss_symbols",
    "selected_loss_windows",
    "selected_loss_realized_pnl",
    "month_exit_loss_symbol_count",
    "month_exit_loss_symbols",
    "month_exit_loss_windows",
    "month_exit_loss_realized_pnl",
    "carryover_exit_loss_symbols",
    "carryover_exit_loss_windows",
    "worst_drawdown_date",
    "worst_drawdown_pct",
    "average_month_path_exposure",
    "max_month_path_exposure",
    "diagnostic",
    "recommended_candidate_focus",
    "paper_only",
    "risk_note",
]

MONTHLY_POSITION_LOSS_CONTROL_COLUMNS = [
    "scenario",
    "month",
    "symbol",
    "pressure_source",
    "loss_realized_pnl",
    "as_of_date",
    "worst_drawdown_date",
    "entry_date",
    "entry_close",
    "min_low_date",
    "min_low",
    "max_adverse_return_pct",
    "loss_threshold_pct",
    "would_trigger",
    "stop_trigger_date",
    "triggered_before_worst_drawdown",
    "close_return_to_worst_drawdown_pct",
    "recommended_candidate_focus",
    "diagnostic",
    "paper_only",
    "risk_note",
]

MONTHLY_PROXY_GUARD_OUTCOME_COLUMNS = [
    "scenario",
    "as_of_date",
    "signal_date",
    "month",
    "mode",
    "reason",
    "target_exposure",
    "cash_weight",
    "month_return_pct",
    "month_status",
    "guard_triggered",
    "guard_cap",
    "guard_medium_return_pct",
    "guard_short_return_pct",
    "guard_medium_drawdown_pct",
    "guard_reason",
    "loss_month",
    "gain_month",
    "high_exposure_proxy_loss",
    "proxy_gain_participation",
    "guard_outcome",
    "candidate_design_hint",
    "original_diagnostic",
    "original_recommended_next_action",
    "paper_only",
    "risk_note",
]

MONTHLY_PROXY_GUARD_RECOVERY_EXIT_COLUMNS = [
    "scenario",
    "candidate_label",
    "loss_month",
    "recovery_month",
    "loss_month_return_pct",
    "loss_return_delta_pct",
    "loss_drawdown_delta_pct",
    "loss_target_exposure",
    "loss_cash_weight",
    "loss_guard_triggered",
    "loss_guard_reason",
    "loss_guard_medium_return_pct",
    "loss_guard_short_return_pct",
    "loss_guard_medium_drawdown_pct",
    "recovery_month_return_pct",
    "recovery_baseline_return_pct",
    "recovery_candidate_return_pct",
    "recovery_return_delta_pct",
    "recovery_drawdown_delta_pct",
    "recovery_target_exposure",
    "recovery_cash_weight",
    "recovery_guard_triggered",
    "recovery_guard_reason",
    "recovery_guard_medium_return_pct",
    "recovery_guard_short_return_pct",
    "recovery_guard_medium_drawdown_pct",
    "recovery_exit_outcome",
    "candidate_design_hint",
    "risk_note",
    "paper_only",
]

MONTHLY_RECOVERY_ATTRIBUTION_COLUMNS = [
    "scenario",
    "start",
    "end",
    "total_return_pct",
    "buy_hold_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "month_count",
    "loss_month_count",
    "gain_month_count",
    "positive_month_ratio",
    "average_target_exposure",
    "average_cash_weight",
    "worst_month",
    "worst_month_return_pct",
    "worst_month_equity_change",
    "worst_month_target_exposure",
    "worst_month_cash_weight",
    "worst_month_mode",
    "worst_month_reason",
    "best_month",
    "best_month_return_pct",
    "best_month_target_exposure",
    "best_month_cash_weight",
    "post_worst_month_count",
    "post_worst_total_return_pct",
    "top_loss_symbol",
    "top_loss_symbol_realized_pnl",
    "top_loss_symbols",
    "loss_symbol_count",
    "gain_symbol_count",
    "failure_mode",
    "diagnostic",
]

MONTHLY_STRESS_DRAWDOWN_PRESSURE_COLUMNS = [
    "scenario",
    "worst_drawdown_date",
    "max_drawdown_pct",
    "drawdown_threshold_pct",
    "breach_day_count",
    "breach_start",
    "breach_end",
    "breach_months",
    "average_breach_exposure",
    "max_breach_exposure",
    "average_breach_cash",
    "worst_loss_month",
    "worst_month_return_pct",
    "worst_month_equity_change",
    "worst_month_mode",
    "worst_month_target_exposure",
    "worst_month_cash_weight",
    "top_loss_symbol",
    "top_loss_symbol_realized_pnl",
    "top_loss_symbols",
    "breach_position_symbols",
    "top_loss_symbols_in_breach_positions",
    "top_loss_symbol_overlap_count",
    "high_exposure_loss_month_count",
    "decision_mode_counts",
    "diagnostic",
    "recommended_candidate_focus",
    "paper_only",
    "risk_note",
]

MONTHLY_ATTRIBUTION_COMPARISON_COLUMNS = [
    "scenario",
    "candidate_label",
    "month",
    "baseline_start_date",
    "baseline_end_date",
    "candidate_start_date",
    "candidate_end_date",
    "baseline_return_pct",
    "candidate_return_pct",
    "return_delta_pct",
    "baseline_equity_change",
    "candidate_equity_change",
    "equity_change_delta",
    "baseline_worst_equity",
    "candidate_worst_equity",
    "baseline_worst_drawdown_pct",
    "candidate_worst_drawdown_pct",
    "drawdown_delta_pct",
    "baseline_status",
    "candidate_status",
    "drawdown_threshold_pct",
    "baseline_breached_drawdown_threshold",
    "candidate_breached_drawdown_threshold",
    "candidate_crossed_drawdown_threshold",
    "diagnostic",
]

MONTHLY_DECISION_ATTRIBUTION_COMPARISON_COLUMNS = [
    "scenario",
    "candidate_label",
    "as_of_date",
    "month",
    "baseline_signal_date",
    "candidate_signal_date",
    "baseline_mode",
    "candidate_mode",
    "baseline_selected_preset",
    "candidate_selected_preset",
    "baseline_reason",
    "candidate_reason",
    "baseline_target_exposure",
    "candidate_target_exposure",
    "target_exposure_delta",
    "baseline_cash_weight",
    "candidate_cash_weight",
    "cash_weight_delta",
    "baseline_position_count",
    "candidate_position_count",
    "position_count_delta",
    "shared_symbol_count",
    "baseline_only_symbol_count",
    "candidate_only_symbol_count",
    "baseline_only_symbols",
    "candidate_only_symbols",
    "baseline_selected_symbols",
    "candidate_selected_symbols",
    "diagnostic",
]

MONTHLY_PATH_ATTRIBUTION_COLUMNS = [
    "date",
    "equity",
    "rolling_peak",
    "cash",
    "position_market_value",
    "exposure",
    "position_count",
    "total_position_quantity",
    "position_symbols",
    "position_quantities",
    "buy_value",
    "sell_value",
    "turnover_value",
    "trade_count",
    "estimated_trade_cost",
    "drawdown_pct",
    "daily_return_pct",
]

MONTHLY_EXECUTION_GAP_COLUMNS = [
    "scenario",
    "as_of_date",
    "signal_date",
    "mode",
    "selected_preset",
    "reason",
    "symbol",
    "target_weight",
    "target_value",
    "reference_price",
    "min_trade_value",
    "actual_quantity",
    "actual_market_value",
    "actual_weight",
    "execution_gap",
    "diagnostic",
    "paper_only",
    "risk_note",
]

MONTHLY_PATH_ATTRIBUTION_COMPARISON_COLUMNS = [
    "scenario",
    "candidate_label",
    "date",
    "baseline_equity",
    "candidate_equity",
    "equity_delta",
    "baseline_rolling_peak",
    "candidate_rolling_peak",
    "rolling_peak_delta",
    "baseline_drawdown_pct",
    "candidate_drawdown_pct",
    "drawdown_delta_pct",
    "baseline_daily_return_pct",
    "candidate_daily_return_pct",
    "daily_return_delta_pct",
    "baseline_cash",
    "candidate_cash",
    "cash_delta",
    "baseline_exposure",
    "candidate_exposure",
    "exposure_delta",
    "baseline_position_count",
    "candidate_position_count",
    "position_count_delta",
    "baseline_total_position_quantity",
    "candidate_total_position_quantity",
    "total_position_quantity_delta",
    "shared_symbol_count",
    "baseline_only_symbols",
    "candidate_only_symbols",
    "baseline_turnover_value",
    "candidate_turnover_value",
    "turnover_delta",
    "baseline_estimated_trade_cost",
    "candidate_estimated_trade_cost",
    "estimated_trade_cost_delta",
    "diagnostic",
]

MONTHLY_PATH_ATTRIBUTION_COMPARISON_SUMMARY_COLUMNS = [
    "scenario",
    "candidate_label",
    "month",
    "day_count",
    "equity_regression_day_count",
    "equity_improved_day_count",
    "drawdown_regression_day_count",
    "drawdown_improved_day_count",
    "exposure_reduced_day_count",
    "exposure_increased_day_count",
    "symbol_rotation_day_count",
    "avg_equity_delta",
    "worst_equity_delta",
    "worst_equity_delta_date",
    "avg_drawdown_delta_pct",
    "worst_drawdown_delta_pct",
    "worst_drawdown_delta_date",
    "avg_exposure_delta",
    "avg_cash_delta",
    "total_turnover_delta",
    "total_estimated_trade_cost_delta",
    "dominant_diagnostic",
    "diagnostic",
    "paper_only",
    "risk_note",
]

DEPLOYMENT_GATE_COLUMNS = [
    "deployable",
    "reason",
    "source",
    "total_return_pct",
    "buy_hold_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "trade_count",
    "universe_bias_warning",
]

MONTHLY_VALIDATION_COLUMNS = [
    "name",
    "category",
    "required",
    "train_start",
    "train_end",
    "selected_preset",
    "train_excess_return_pct",
    "train_candidate_scores",
    "train_candidate_decision_profiles",
    "train_candidate_direct_scores",
    "train_direct_diagnostics",
    "start",
    "end",
    "slippage_multiplier",
    "stress",
    "final_equity",
    "total_return_pct",
    "buy_hold_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "trade_count",
    "universe_bias_warning",
    "universe_bias_reasons",
    "universe_symbol_count",
    "universe_avg_symbol_return_pct",
    "universe_median_symbol_return_pct",
    "universe_extreme_return_symbols",
    "universe_extreme_return_share",
    "deployable",
    "reason",
    "source",
]

VALIDATION_DATA_QUALITY_COLUMNS = [
    "symbol",
    "status",
    "first_date",
    "last_date",
    "rows",
    "duplicate_dates",
    "nonpositive_price_rows",
    "reason",
]

UNIVERSE_PRICE_COVERAGE_COLUMNS = [
    "date",
    "universe_symbols",
    "price_symbols",
    "covered_symbols",
    "excluded_symbols",
    "missing_symbols",
    "coverage_pct",
    "status",
    "missing_preview",
    "excluded_preview",
]

UNIVERSE_FILTER_REPORT_COLUMNS = [
    "as_of_date",
    "snapshot_date",
    "symbol",
    "name",
    "market",
    "status",
    "reason",
    "detail",
]


def is_monthly_rebalance_due(*, as_of_date: str, last_rebalance_date: str | None) -> bool:
    if not last_rebalance_date:
        return True
    return as_of_date[:7] != last_rebalance_date[:7]


def decide_monthly_allocation(
    symbol_candles: dict[str, list[Candle]],
    *,
    as_of_date: str,
    config: MonthlyRebalanceConfig | None = None,
    preset_configs: dict[str, MomentumRotationConfig] | None = None,
    portfolio_value: float | None = None,
    reference_prices: dict[str, float] | None = None,
) -> MonthlyDecision:
    cfg = config or MonthlyRebalanceConfig()
    selected_configs = preset_configs or _monthly_preset_configs(cfg)
    signal_date = latest_signal_date(symbol_candles, as_of_date=as_of_date)
    universe_candles = filter_symbol_candles_by_universe(
        symbol_candles,
        cfg.point_in_time_universe,
        signal_date=signal_date,
        min_history_days=cfg.point_in_time_min_history_days,
    )
    point_in_time_candles = select_point_in_time_universe(
        universe_candles,
        signal_date=signal_date,
        min_history_days=cfg.point_in_time_min_history_days,
        min_reference_price=cfg.point_in_time_min_reference_price,
        max_trailing_return_pct=cfg.point_in_time_max_trailing_return_pct,
        trailing_return_days=cfg.point_in_time_trailing_return_days,
    )
    decision_candles = (
        select_liquid_universe(
            point_in_time_candles,
            signal_date=signal_date,
            top_n=cfg.point_in_time_liquidity_top_n,
            window_days=cfg.point_in_time_liquidity_window_days,
        )
        if cfg.point_in_time_liquidity_top_n > 0
        else point_in_time_candles
    )
    train_start = cfg.train_start or _default_train_start(signal_date, cfg.train_years)
    train_candles = slice_asof_symbol_candles(
        decision_candles,
        start=train_start,
        end=signal_date,
        min_rows=cfg.min_rows_per_window,
        start_grace_days=cfg.start_grace_days,
    )
    train_rows = _train_candidate_rows(
        decision_candles,
        train_candles=train_candles,
        train_start=train_start,
        train_end=signal_date,
        preset_configs=selected_configs,
        min_rows_per_window=cfg.min_rows_per_window,
        start_grace_days=cfg.start_grace_days,
        train_stability_years=cfg.train_stability_years,
    )
    selected = select_best_train_candidate(
        train_rows,
        min_train_trades=cfg.min_train_trades,
        min_train_positive_ratio=cfg.min_train_positive_ratio,
    )
    prior_breadth = market_breadth_before_date(
        decision_candles,
        before_date=as_of_date,
        trend_days=cfg.fallback_breadth_days,
    )

    trend_scale = market_trend_exposure_scale(
        decision_candles,
        before_date=as_of_date,
        lookback_days=cfg.market_trend_filter_days,
        min_return_pct=cfg.market_trend_min_return_pct,
        risk_scale=cfg.market_trend_risk_scale,
    )
    volatility_scale = market_volatility_exposure_scale(
        decision_candles,
        before_date=as_of_date,
        lookback_days=cfg.market_volatility_filter_days,
        target_volatility_pct=cfg.market_volatility_target_pct,
        min_scale=cfg.market_volatility_min_scale,
    )
    liquidity_scale = liquidity_universe_exposure_scale(
        top_n=cfg.point_in_time_liquidity_top_n,
        reference_top_n=cfg.liquidity_risk_reference_top_n,
        min_scale=cfg.liquidity_risk_min_scale,
        min_top_n=cfg.liquidity_risk_min_top_n,
    )
    exposure_scale = trend_scale * volatility_scale * liquidity_scale
    reason_suffix = _risk_scale_reason_suffix(
        trend_scale=trend_scale,
        volatility_scale=volatility_scale,
        liquidity_scale=liquidity_scale,
    )
    target_budget = max(0.0, 1.0 - cfg.cash_buffer_weight) * exposure_scale
    proxy_max_exposure, proxy_cap_reason = _market_beta_proxy_effective_cap(
        cfg,
        prior_breadth,
        symbol_candles=decision_candles,
        signal_date=signal_date,
    )
    if selected is None:
        if prior_breadth is not None and prior_breadth >= cfg.market_beta_breadth_threshold:
            return _market_beta_or_cash_decision(
                decision_candles,
                as_of_date=as_of_date,
                signal_date=signal_date,
                target_budget=target_budget,
                config=cfg,
                proxy_max_exposure=proxy_max_exposure,
                proxy_cap_reason=proxy_cap_reason,
                reference_prices=reference_prices,
                portfolio_value=portfolio_value,
                proxy_reason=("no_train_candidate_neutral_breadth_proxy" + reason_suffix)
                if prior_breadth < cfg.fallback_breadth_threshold
                else ("no_train_candidate_strong_breadth_proxy" + reason_suffix),
                direct_reason=("no_train_candidate_neutral_breadth" + reason_suffix)
                if prior_breadth < cfg.fallback_breadth_threshold
                else ("no_train_candidate_strong_breadth" + reason_suffix),
                empty_reason="no_market_beta_proxy",
            )
        return MonthlyDecision(
            as_of_date=as_of_date,
            signal_date=signal_date,
            mode="cash",
            selected_preset="cash",
            target_weights={},
            reason="no_train_candidate_weak_breadth",
        )

    selected_preset = str(selected["preset"])
    if (
        prior_breadth is None or prior_breadth < cfg.fallback_breadth_threshold
    ) and float(selected.get("train_avg_subwindow_excess_pct", 0.0)) < cfg.weak_breadth_min_train_avg_excess_pct:
        if prior_breadth is not None and prior_breadth >= cfg.market_beta_breadth_threshold:
            return _market_beta_or_cash_decision(
                decision_candles,
                as_of_date=as_of_date,
                signal_date=signal_date,
                target_budget=target_budget,
                config=cfg,
                proxy_max_exposure=proxy_max_exposure,
                proxy_cap_reason=proxy_cap_reason,
                reference_prices=reference_prices,
                portfolio_value=portfolio_value,
                proxy_reason="weak_train_neutral_breadth_proxy" + reason_suffix,
                direct_reason="weak_train_neutral_breadth" + reason_suffix,
                empty_reason="weak_train_no_market_beta_proxy",
            )
        return MonthlyDecision(
            as_of_date=as_of_date,
            signal_date=signal_date,
            mode="cash",
            selected_preset="cash",
            target_weights={},
            reason="weak_breadth_and_weak_train_average",
        )

    target_candles = slice_asof_symbol_candles(
        decision_candles,
        start=train_start,
        end=signal_date,
        min_rows=cfg.min_rows_per_window,
        start_grace_days=cfg.start_grace_days,
    )
    selected_config = selected_configs[selected_preset]
    ranking_config = (
        replace(
            selected_config,
            top_n=max(selected_config.top_n, cfg.candidate_pool_size),
            bull_top_n=max(selected_config.bull_top_n, cfg.candidate_pool_size),
            max_lookback_return_pct=cfg.max_candidate_lookback_return_pct,
        )
        if reference_prices is not None and portfolio_value is not None
        else selected_config
    )
    ranked_targets = rank_momentum_targets(
        target_candles,
        signal_date=signal_date,
        config=ranking_config,
    )
    event_filtered_targets = filter_symbols_by_event_score(
        ranked_targets,
        event_scores=cfg.event_scores,
        signal_date=signal_date,
        lookback_days=cfg.event_lookback_days,
        min_entry_event_score=cfg.min_entry_event_score,
    )
    event_reason_suffix = "_event_filtered" if len(event_filtered_targets) < len(ranked_targets) else ""
    event_multipliers = event_score_multipliers(
        event_filtered_targets,
        event_scores=cfg.event_scores,
        signal_date=signal_date,
        lookback_days=cfg.event_lookback_days,
        event_weight=cfg.event_weight,
        min_multiplier=cfg.min_event_weight_multiplier,
        max_multiplier=cfg.max_event_weight_multiplier,
    )
    targets = (
        select_buyable_targets(
            event_filtered_targets,
            reference_prices=reference_prices,
            portfolio_value=portfolio_value,
            target_budget=target_budget,
            max_position_weight=cfg.max_position_weight,
            min_target_value=cfg.min_target_value,
        )
        if reference_prices is not None and portfolio_value is not None
        else event_filtered_targets
    )
    if not targets:
        return MonthlyDecision(
            as_of_date=as_of_date,
            signal_date=signal_date,
            mode="cash",
            selected_preset="cash",
            target_weights={},
            reason="no_ranked_targets",
        )
    return MonthlyDecision(
        as_of_date=as_of_date,
        signal_date=signal_date,
        mode="alpha",
        selected_preset=selected_preset,
        target_weights=target_weights_for_symbols(
            targets,
            target_budget=target_budget,
            max_position_weight=cfg.max_position_weight,
            symbol_multipliers=event_multipliers,
        ),
        reason="selected_monthly_alpha" + reason_suffix + event_reason_suffix,
    )


def build_order_plan(
    decision: MonthlyDecision,
    *,
    positions: list[Position],
    cash: float,
    reference_prices: dict[str, float],
    min_trade_value: float = 10_000.0,
    symbol_candles: dict[str, list[Candle]] | None = None,
    adv_window_days: int = 20,
    base_slippage_rate: float = 0.0005,
    impact_slippage_multiplier: float = 0.05,
    warn_adv_participation_rate: float = 0.05,
    max_adv_participation_rate: float = 0.10,
    liquidity_missing_adv_status: str = "BLOCK",
) -> list[PlannedOrder]:
    current_positions = {position.symbol: position for position in positions}
    current_values = {
        symbol: position.quantity * reference_prices.get(symbol, 0.0)
        for symbol, position in current_positions.items()
    }
    portfolio_value = cash + sum(current_values.values())
    symbols = sorted(set(current_positions) | set(decision.target_weights))
    orders: list[PlannedOrder] = []
    for symbol in symbols:
        price = reference_prices.get(symbol, 0.0)
        current_quantity = current_positions.get(symbol, Position(symbol, 0)).quantity
        target_weight = decision.target_weights.get(symbol, 0.0)
        target_value = portfolio_value * target_weight
        current_value = current_values.get(symbol, 0.0)
        delta_value = target_value - current_value
        if price <= 0:
            orders.append(
                PlannedOrder(
                    as_of_date=decision.as_of_date,
                    symbol=symbol,
                    action="SKIP",
                    quantity=0,
                    reference_price=0.0,
                    estimated_value=0.0,
                    target_weight=target_weight,
                    current_quantity=current_quantity,
                    reason="missing_reference_price",
                )
            )
            continue
        if abs(delta_value) < min_trade_value:
            continue
        if delta_value < 0:
            quantity = min(current_quantity, int(abs(delta_value) / price))
            action = "SELL"
        else:
            quantity = int(delta_value / price)
            action = "BUY"
        if quantity <= 0:
            if action == "BUY" and target_weight > 0 and delta_value >= min_trade_value:
                orders.append(
                    PlannedOrder(
                        as_of_date=decision.as_of_date,
                        symbol=symbol,
                        action="SKIP",
                        quantity=0,
                        reference_price=price,
                        estimated_value=0.0,
                        target_weight=target_weight,
                        current_quantity=current_quantity,
                        reason="target_value_below_one_share",
                    )
                )
            continue
        order = PlannedOrder(
            as_of_date=decision.as_of_date,
            symbol=symbol,
            action=action,
            quantity=quantity,
            reference_price=price,
            estimated_value=quantity * price,
            target_weight=target_weight,
            current_quantity=current_quantity,
            reason=decision.reason,
        )
        if symbol_candles is not None:
            order = _annotate_order_liquidity(
                order,
                symbol_candles.get(symbol, []),
                as_of_date=decision.signal_date,
                adv_window_days=adv_window_days,
                base_slippage_rate=base_slippage_rate,
                impact_slippage_multiplier=impact_slippage_multiplier,
                warn_adv_participation_rate=warn_adv_participation_rate,
                max_adv_participation_rate=max_adv_participation_rate,
                liquidity_missing_adv_status=liquidity_missing_adv_status,
            )
        orders.append(order)
    return sorted(orders, key=lambda order: 0 if order.action == "SELL" else 1)


def average_daily_trading_value(
    candles: list[Candle],
    *,
    as_of_date: str,
    window_days: int = 20,
) -> float:
    if window_days <= 0:
        return 0.0
    history = [
        candle
        for candle in sorted(candles, key=lambda candle: candle.date)
        if candle.date <= as_of_date and candle.close > 0 and candle.volume > 0
    ]
    if len(history) < window_days:
        return 0.0
    window = history[-window_days:]
    return sum(candle.close * candle.volume for candle in window) / len(window)


def _annotate_order_liquidity(
    order: PlannedOrder,
    candles: list[Candle],
    *,
    as_of_date: str,
    adv_window_days: int,
    base_slippage_rate: float,
    impact_slippage_multiplier: float,
    warn_adv_participation_rate: float,
    max_adv_participation_rate: float,
    liquidity_missing_adv_status: str,
) -> PlannedOrder:
    adv = average_daily_trading_value(candles, as_of_date=as_of_date, window_days=adv_window_days)
    participation = abs(order.estimated_value) / adv if adv > 0 else 0.0
    estimated_slippage_rate = max(0.0, base_slippage_rate) + participation * max(0.0, impact_slippage_multiplier)
    estimated_total_cost = abs(order.estimated_value) * estimated_slippage_rate
    if adv <= 0:
        status = _normalize_liquidity_status(liquidity_missing_adv_status)
        reason = f"adv_unavailable: need {adv_window_days} rows before {as_of_date}"
    elif participation > max_adv_participation_rate + 1e-12:
        status = "BLOCK"
        reason = f"adv_participation_rate {participation:.4f} > max {max_adv_participation_rate:.4f}"
    elif participation > warn_adv_participation_rate + 1e-12:
        status = "WARN"
        reason = f"adv_participation_rate {participation:.4f} > warn {warn_adv_participation_rate:.4f}"
    else:
        status = "PASS"
        reason = f"adv_participation_rate {participation:.4f}"
    return replace(
        order,
        adv_20d=adv,
        adv_participation_rate=participation,
        liquidity_status=status,
        liquidity_reason=reason,
        estimated_slippage_rate=estimated_slippage_rate,
        estimated_total_cost=estimated_total_cost,
    )


def _normalize_liquidity_status(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized in {"WARN", "PASS", "NOT_CHECKED"}:
        return normalized
    return "BLOCK"


def mark_order_plan_execution(
    orders: list[PlannedOrder],
    *,
    risk_status_value: str,
    production_trading_enabled: bool = False,
) -> list[PlannedOrder]:
    normalized = str(risk_status_value).strip().upper()
    marked: list[PlannedOrder] = []
    for order in orders:
        if normalized == "PASS" and order.action in {"BUY", "SELL"} and production_trading_enabled:
            marked.append(
                replace(
                    order,
                    execution_allowed=True,
                    execution_mode="live_ready",
                    execution_block_reason="",
                    risk_status="PASS",
                    risk_reasons="",
                )
            )
        else:
            if normalized == "PASS" and order.action in {"BUY", "SELL"}:
                reason = "production_trading_disabled"
            else:
                reason = f"risk_status_{normalized}" if normalized != "PASS" else f"action_{order.action}"
            marked.append(
                replace(
                    order,
                    execution_allowed=False,
                    execution_mode="blocked",
                    execution_block_reason=reason,
                    risk_status="BLOCKED",
                    risk_reasons=reason,
                )
            )
    return marked


def validate_pre_trade_risk(
    decision: MonthlyDecision,
    orders: list[PlannedOrder],
    *,
    limits: RiskLimits | None = None,
    kill_switch_path: Path | str | None = None,
    deployment_gate: DeploymentGate | None = None,
    require_deployment_gate: bool = False,
    performance_guard: PerformanceGuard | None = None,
    require_performance_guard: bool = False,
    day_start_equity: float | None = None,
    current_equity: float | None = None,
) -> list[RiskCheck]:
    cfg = limits or RiskLimits()
    checks: list[RiskCheck] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append(RiskCheck(name=name, status=status, detail=detail))

    if kill_switch_path is not None and Path(kill_switch_path).exists():
        add("kill_switch", "BLOCK", f"kill switch exists: {kill_switch_path}")
    else:
        add("kill_switch", "PASS", "not present")

    if day_start_equity is not None and current_equity is not None and day_start_equity > 0:
        daily_loss_pct = (current_equity / day_start_equity - 1) * 100
        if daily_loss_pct <= -abs(cfg.max_daily_loss_pct):
            add(
                "daily_loss",
                "BLOCK",
                f"daily loss {daily_loss_pct:.2f}% breaches -{abs(cfg.max_daily_loss_pct):.2f}%",
            )
        else:
            add("daily_loss", "PASS", f"daily loss {daily_loss_pct:.2f}%")
    else:
        add("daily_loss", "WARN", "day_start_equity/current_equity not provided")

    if deployment_gate is None:
        if require_deployment_gate:
            add("deployment_gate", "BLOCK", "deployment gate file is required but missing")
    elif deployment_gate.deployable:
        add("deployment_gate", "PASS", f"{deployment_gate.source}:{deployment_gate.reason}")
    else:
        add("deployment_gate", "BLOCK", f"{deployment_gate.source}:{deployment_gate.reason}")

    if performance_guard is None:
        if require_performance_guard:
            add("performance_guard", "BLOCK", "performance report is required but missing")
    else:
        status = performance_guard.status.upper()
        if status == "PASS":
            add("performance_guard", "PASS", performance_guard.detail)
        elif status == "WARN":
            add(
                "performance_guard",
                "WARN",
                f"{performance_guard.detail}; target_scale={performance_guard.scale:.4f}",
            )
        else:
            add(
                "performance_guard",
                "BLOCK",
                f"{performance_guard.detail}; target_scale={performance_guard.scale:.4f}",
            )

    try:
        age_days = (date.fromisoformat(decision.as_of_date) - date.fromisoformat(decision.signal_date)).days
    except ValueError:
        age_days = cfg.max_signal_age_days + 1
        add("signal_age", "BLOCK", "invalid decision or signal date")
    else:
        if age_days < 0:
            add("signal_age", "BLOCK", f"signal date is in the future: {decision.signal_date}")
        elif age_days > cfg.max_signal_age_days:
            add("signal_age", "BLOCK", f"signal age {age_days}d exceeds {cfg.max_signal_age_days}d")
        else:
            add("signal_age", "PASS", f"signal age {age_days}d")

    total_target_weight = sum(decision.target_weights.values())
    if total_target_weight > cfg.max_total_target_weight + 1e-9:
        add(
            "total_target_weight",
            "BLOCK",
            f"target weight {total_target_weight:.4f} exceeds {cfg.max_total_target_weight:.4f}",
        )
    elif total_target_weight < -1e-9:
        add("total_target_weight", "BLOCK", f"target weight is negative: {total_target_weight:.4f}")
    else:
        add("total_target_weight", "PASS", f"target weight {total_target_weight:.4f}")

    negative_targets = [symbol for symbol, weight in decision.target_weights.items() if weight < -1e-9]
    if negative_targets:
        add("negative_target_weight", "BLOCK", ",".join(negative_targets))
    else:
        add("negative_target_weight", "PASS", "none")

    executable_orders = [order for order in orders if order.action in {"BUY", "SELL"}]
    skipped_orders = [order for order in orders if order.action == "SKIP"]
    if skipped_orders and cfg.block_skip_orders:
        add(
            "skip_orders",
            "BLOCK",
            ",".join(f"{order.symbol}:{order.reason}" for order in skipped_orders),
        )
    elif skipped_orders:
        add("skip_orders", "WARN", ",".join(order.symbol for order in skipped_orders))
    else:
        add("skip_orders", "PASS", "none")

    if decision.target_weights and not executable_orders:
        add("orders", "WARN", "target weights exist but no executable orders were created")
    else:
        add("orders", "PASS", f"executable orders {len(executable_orders)}")

    if len(executable_orders) > cfg.max_order_count:
        add("order_count", "BLOCK", f"{len(executable_orders)} exceeds {cfg.max_order_count}")
    else:
        add("order_count", "PASS", f"{len(executable_orders)}")

    oversized = [
        order
        for order in executable_orders
        if order.estimated_value > cfg.max_single_order_value + 1e-9
    ]
    if oversized:
        detail = ",".join(f"{order.symbol}:{order.estimated_value:.0f}" for order in oversized)
        add("single_order_value", "BLOCK", detail)
    else:
        add("single_order_value", "PASS", f"limit {cfg.max_single_order_value:.0f}")

    total_buy_value = sum(order.estimated_value for order in executable_orders if order.action == "BUY")
    if total_buy_value > cfg.max_total_buy_value + 1e-9:
        add("total_buy_value", "BLOCK", f"{total_buy_value:.0f} exceeds {cfg.max_total_buy_value:.0f}")
    else:
        add("total_buy_value", "PASS", f"{total_buy_value:.0f}")

    total_sell_value = sum(order.estimated_value for order in executable_orders if order.action == "SELL")
    if total_sell_value > cfg.max_total_sell_value + 1e-9:
        add("total_sell_value", "BLOCK", f"{total_sell_value:.0f} exceeds {cfg.max_total_sell_value:.0f}")
    else:
        add("total_sell_value", "PASS", f"{total_sell_value:.0f}")

    invalid_sells = [
        order
        for order in executable_orders
        if order.action == "SELL" and order.quantity > order.current_quantity
    ]
    if invalid_sells:
        detail = ",".join(
            f"{order.symbol}:{order.quantity}>{order.current_quantity}" for order in invalid_sells
        )
        add("sell_quantity", "BLOCK", detail)
    else:
        add("sell_quantity", "PASS", "within current positions")

    invalid_orders = [
        order
        for order in executable_orders
        if order.quantity <= 0 or order.reference_price <= 0 or order.estimated_value <= 0
    ]
    if invalid_orders:
        add("order_shape", "BLOCK", ",".join(order.symbol for order in invalid_orders))
    else:
        add("order_shape", "PASS", "valid")

    liquidity_blocked = [
        order
        for order in executable_orders
        if str(order.liquidity_status).strip().upper() == "BLOCK"
    ]
    liquidity_warned = [
        order
        for order in executable_orders
        if str(order.liquidity_status).strip().upper() == "WARN"
    ]
    liquidity_checked = [
        order
        for order in executable_orders
        if str(order.liquidity_status).strip().upper() not in {"", "NOT_CHECKED"}
    ]
    if liquidity_blocked:
        detail = ";".join(f"{order.symbol}:{order.liquidity_reason}" for order in liquidity_blocked[:10])
        add("liquidity", "BLOCK", detail)
    elif liquidity_warned:
        detail = ";".join(f"{order.symbol}:{order.liquidity_reason}" for order in liquidity_warned[:10])
        add("liquidity", "WARN", detail)
    elif liquidity_checked:
        max_participation = max(order.adv_participation_rate for order in liquidity_checked)
        add("liquidity", "PASS", f"max_adv_participation_rate={max_participation:.4f}")

    return checks


def risk_status(checks: list[RiskCheck]) -> str:
    statuses = {check.status for check in checks}
    if "BLOCK" in statuses:
        return "BLOCK"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def risk_exit_code(status: str) -> int:
    return 2 if status == "BLOCK" else 0


def validate_report_freshness(
    report_paths: dict[str, Path | str | None],
    *,
    as_of_date: str,
    max_age_days: int,
) -> list[RiskCheck]:
    if max_age_days < 0:
        return []
    checks: list[RiskCheck] = []
    try:
        as_of = date.fromisoformat(as_of_date)
    except ValueError:
        as_of = date.today()
        checks.append(RiskCheck("report_freshness_as_of", "BLOCK", f"invalid as_of_date: {as_of_date}"))
    for name, raw_path in report_paths.items():
        if raw_path is None:
            continue
        path = Path(raw_path)
        check_name = f"{name}_freshness"
        if not path.exists():
            checks.append(RiskCheck(check_name, "BLOCK", f"missing report: {path}"))
            continue
        modified_date = datetime.fromtimestamp(path.stat().st_mtime).date()
        age_days = max(0, (as_of - modified_date).days)
        if age_days > max_age_days:
            checks.append(
                RiskCheck(
                    check_name,
                    "BLOCK",
                    f"age {age_days}d exceeds {max_age_days}d; modified={modified_date.isoformat()}",
                )
            )
        else:
            checks.append(
                RiskCheck(
                    check_name,
                    "PASS",
                    f"age {age_days}d within {max_age_days}d; modified={modified_date.isoformat()}",
                )
            )
    return checks


def save_risk_report(rows: list[RiskCheck], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RISK_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in RISK_COLUMNS})
    return len(rows)


def build_monthly_performance_audit(
    rows: list[dict[str, Any]],
    *,
    min_required_excess_pct: float = 0.0,
    min_walk_forward_warn_excess_pct: float = 5.0,
    max_drawdown_warn_pct: float = -20.0,
    max_drawdown_block_pct: float = -25.0,
    max_full_to_walk_median_excess_ratio: float = 20.0,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    required_rows = [row for row in rows if _parse_bool(row.get("required", True))]
    failed_required = [row for row in required_rows if not _parse_bool(row.get("deployable", False))]
    checks.append(
        {
            "name": "required_scenarios",
            "status": "BLOCK" if failed_required else "PASS",
            "detail": f"{len(failed_required)} failed of {len(required_rows)} required",
        }
    )

    numeric_required = [row for row in required_rows if _float_or_none(row.get("excess_return_pct")) is not None]
    excess_values = [float(row["excess_return_pct"]) for row in numeric_required]
    if excess_values:
        min_excess = min(excess_values)
        checks.append(
            {
                "name": "required_excess",
                "status": "BLOCK" if min_excess <= min_required_excess_pct else "PASS",
                "detail": f"min_required_excess_pct={min_excess:.4f}",
            }
        )
    else:
        checks.append({"name": "required_excess", "status": "BLOCK", "detail": "no numeric required excess"})

    walk_rows = [row for row in required_rows if str(row.get("category", "")).strip() == "walk_forward"]
    walk_excess = [float(row["excess_return_pct"]) for row in walk_rows if _float_or_none(row.get("excess_return_pct")) is not None]
    if not walk_excess:
        checks.append({"name": "walk_forward_margin", "status": "BLOCK", "detail": "no walk-forward excess values"})
    else:
        min_walk = min(walk_excess)
        status = "PASS"
        if min_walk <= min_required_excess_pct:
            status = "BLOCK"
        elif min_walk < min_walk_forward_warn_excess_pct:
            status = "WARN"
        checks.append(
            {
                "name": "walk_forward_margin",
                "status": status,
                "detail": f"min_walk_forward_excess_pct={min_walk:.4f}; warn_below={min_walk_forward_warn_excess_pct:.4f}",
            }
        )

    drawdown_values = [float(row["max_drawdown_pct"]) for row in numeric_required if _float_or_none(row.get("max_drawdown_pct")) is not None]
    if drawdown_values:
        worst_drawdown = min(drawdown_values)
        status = "PASS"
        if worst_drawdown < max_drawdown_block_pct:
            status = "BLOCK"
        elif worst_drawdown <= max_drawdown_warn_pct:
            status = "WARN"
        checks.append(
            {
                "name": "drawdown_buffer",
                "status": status,
                "detail": (
                    f"worst_max_drawdown_pct={worst_drawdown:.4f}; "
                    f"warn_at_or_below={max_drawdown_warn_pct:.4f}; block_below={max_drawdown_block_pct:.4f}"
                ),
            }
        )
    else:
        checks.append({"name": "drawdown_buffer", "status": "BLOCK", "detail": "no numeric drawdown values"})

    full_excess = next(
        (
            float(row["excess_return_pct"])
            for row in rows
            if str(row.get("name", "")).strip() == "full_period"
            and _float_or_none(row.get("excess_return_pct")) is not None
        ),
        None,
    )
    positive_walk_excess = [value for value in walk_excess if value > 0]
    if full_excess is None or not positive_walk_excess:
        checks.append({"name": "return_concentration", "status": "WARN", "detail": "insufficient full/walk-forward excess values"})
    else:
        walk_median = median(positive_walk_excess)
        ratio = full_excess / walk_median if walk_median > 0 else float("inf")
        checks.append(
            {
                "name": "return_concentration",
                "status": "WARN" if ratio > max_full_to_walk_median_excess_ratio else "PASS",
                "detail": (
                    f"full_excess_pct={full_excess:.4f}; median_walk_forward_excess_pct={walk_median:.4f}; "
                    f"ratio={ratio:.4f}; warn_above={max_full_to_walk_median_excess_ratio:.4f}"
                ),
            }
        )

    zero_trade_rows = [
        str(row.get("name", "unknown"))
        for row in required_rows
        if _float_or_none(row.get("trade_count")) is not None and float(row.get("trade_count", 0) or 0) <= 0
    ]
    checks.append(
        {
            "name": "trade_activity",
            "status": "BLOCK" if zero_trade_rows else "PASS",
            "detail": "zero_trade_scenarios=" + ",".join(zero_trade_rows[:10]) if zero_trade_rows else f"{len(required_rows)} required scenarios traded",
        }
    )
    return checks


def analyze_monthly_performance_concentration(
    result: MonthlyBacktestResult,
    *,
    symbol_candles: dict[str, list[Candle]] | None = None,
    source: str = "monthly-backtest",
    top_1_month_warn_threshold: float = 0.60,
    top_1_month_block_threshold: float = 0.80,
    top_3_month_warn_threshold: float = 0.85,
    top_3_month_block_threshold: float = 0.95,
    top_5_symbol_warn_threshold: float = 0.75,
    top_5_symbol_block_threshold: float = 0.90,
    min_positive_month_ratio: float = 0.45,
) -> dict[str, Any]:
    monthly_rows = _monthly_return_rows(result)
    monthly_returns = [row["return"] for row in monthly_rows]
    positive_month_returns = [value for value in monthly_returns if value > 0]
    positive_month_sum = sum(positive_month_returns)
    top_months = sorted(positive_month_returns, reverse=True)
    top_1_month = (top_months[0] / positive_month_sum) if positive_month_sum > 0 and top_months else 0.0
    top_3_month = (sum(top_months[:3]) / positive_month_sum) if positive_month_sum > 0 else 0.0
    best = max(monthly_rows, key=lambda row: row["return"], default={"month": "", "return": 0.0})
    worst = min(monthly_rows, key=lambda row: row["return"], default={"month": "", "return": 0.0})
    positive_month_ratio = (len(positive_month_returns) / len(monthly_returns)) if monthly_returns else 0.0
    rolling_3m_min = _rolling_compound_return_min(monthly_returns, 3)
    rolling_6m_min = _rolling_compound_return_min(monthly_returns, 6)
    recovery_months = _max_recovery_months(monthly_rows, result.initial_cash)

    symbol_contributions = _symbol_profit_contributions(result, symbol_candles or {})
    positive_symbol_contributions = [value for value in symbol_contributions.values() if value > 0]
    positive_symbol_sum = sum(positive_symbol_contributions)
    top_5_symbol = (
        sum(sorted(positive_symbol_contributions, reverse=True)[:5]) / positive_symbol_sum
        if positive_symbol_sum > 0
        else 0.0
    )

    status = "PASS"
    reasons: list[str] = []

    def flag(name: str, level: str, detail: str) -> None:
        nonlocal status
        reasons.append(f"{name}:{detail}")
        if level == "BLOCK":
            status = "BLOCK"
        elif status == "PASS":
            status = "WARN"

    if top_1_month >= top_1_month_block_threshold:
        flag("top_1_month_contribution", "BLOCK", f"{top_1_month:.4f}")
    elif top_1_month >= top_1_month_warn_threshold:
        flag("top_1_month_contribution", "WARN", f"{top_1_month:.4f}")
    if len(monthly_returns) >= 6:
        if top_3_month >= top_3_month_block_threshold:
            flag("top_3_month_contribution", "BLOCK", f"{top_3_month:.4f}")
        elif top_3_month >= top_3_month_warn_threshold:
            flag("top_3_month_contribution", "WARN", f"{top_3_month:.4f}")
    if len(positive_symbol_contributions) > 5:
        if top_5_symbol >= top_5_symbol_block_threshold:
            flag("top_5_symbol_contribution", "BLOCK", f"{top_5_symbol:.4f}")
        elif top_5_symbol >= top_5_symbol_warn_threshold:
            flag("top_5_symbol_contribution", "WARN", f"{top_5_symbol:.4f}")
    if monthly_returns and positive_month_ratio < min_positive_month_ratio:
        flag("positive_month_ratio", "WARN", f"{positive_month_ratio:.4f}")

    return {
        "source": source,
        "start": result.dates[0] if result.dates else "",
        "end": result.dates[-1] if result.dates else "",
        "top_1_month_contribution": round(top_1_month, 6),
        "top_3_month_contribution": round(top_3_month, 6),
        "top_5_symbol_contribution": round(top_5_symbol, 6),
        "best_month": str(best["month"]),
        "worst_month": str(worst["month"]),
        "positive_month_ratio": round(positive_month_ratio, 6),
        "rolling_3m_return_min": round(rolling_3m_min, 6),
        "rolling_6m_return_min": round(rolling_6m_min, 6),
        "max_recovery_months_if_possible": recovery_months,
        "concentration_status": status,
        "concentration_reasons": ";".join(reasons),
    }


def save_monthly_performance_concentration(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_CONCENTRATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in PERFORMANCE_CONCENTRATION_COLUMNS})
    return len(rows)


def analyze_monthly_drawdown_attribution(result: MonthlyBacktestResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not result.dates or not result.equity_curve:
        return rows

    running_peak = float(result.initial_cash)
    previous_month_end_equity = float(result.initial_cash)
    current: dict[str, Any] | None = None
    last_equity = float(result.initial_cash)

    def finish(row: dict[str, Any] | None) -> None:
        if row is None:
            return
        equity_change = float(row["end_equity"]) - float(row["start_equity"])
        return_pct = (equity_change / float(row["start_equity"]) * 100.0) if float(row["start_equity"]) > 0 else 0.0
        status = "LOSS" if equity_change < 0 else "GAIN" if equity_change > 0 else "FLAT"
        rows.append(
            {
                "month": str(row["month"]),
                "start_date": str(row["start_date"]),
                "end_date": str(row["end_date"]),
                "start_equity": _format_optional_float(float(row["start_equity"])),
                "end_equity": _format_optional_float(float(row["end_equity"])),
                "equity_change": _format_optional_float(equity_change),
                "return_pct": _format_optional_float(return_pct),
                "worst_equity": _format_optional_float(float(row["worst_equity"])),
                "worst_drawdown_pct": _format_optional_float(float(row["worst_drawdown_pct"])),
                "status": status,
            }
        )

    for raw_day, raw_equity in zip(result.dates, result.equity_curve):
        day = str(raw_day)
        month = day[:7]
        equity = float(raw_equity)
        if current is None or current["month"] != month:
            finish(current)
            previous_month_end_equity = last_equity
            current = {
                "month": month,
                "start_date": day,
                "end_date": day,
                "start_equity": previous_month_end_equity,
                "end_equity": equity,
                "worst_equity": equity,
                "worst_drawdown_pct": 0.0,
            }
        running_peak = max(running_peak, equity)
        drawdown_pct = (equity / running_peak - 1.0) * 100.0 if running_peak > 0 else 0.0
        current["end_date"] = day
        current["end_equity"] = equity
        current["worst_equity"] = min(float(current["worst_equity"]), equity)
        current["worst_drawdown_pct"] = min(float(current["worst_drawdown_pct"]), drawdown_pct)
        last_equity = equity
    finish(current)
    return rows


def analyze_monthly_benchmark_excess(
    monthly_rows: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
    *,
    scenario: str = "",
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for monthly_row in monthly_rows:
        start_date = str(monthly_row.get("start_date", "")).strip()
        end_date = str(monthly_row.get("end_date", "")).strip()
        strategy_return = _float_or_none(monthly_row.get("return_pct"))
        if not start_date or not end_date or strategy_return is None:
            continue
        benchmark_return = equal_weight_buy_hold_period_return(
            symbol_candles,
            start=start_date,
            end=end_date,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate,
        )
        monthly_excess = strategy_return - benchmark_return
        diagnostics: list[str] = []
        if monthly_excess < 0:
            diagnostics.append("benchmark_outperformed")
        if strategy_return < 0:
            diagnostics.append("strategy_loss")
        if benchmark_return > 0:
            diagnostics.append("benchmark_gain")
        if not diagnostics:
            diagnostics.append("strategy_matched_or_outperformed")
        rows.append(
            {
                "scenario": scenario,
                "month": str(monthly_row.get("month", "")),
                "start_date": start_date,
                "end_date": end_date,
                "strategy_return_pct": _format_optional_float(strategy_return),
                "benchmark_return_pct": _format_optional_float(benchmark_return),
                "monthly_excess_return_pct": _format_optional_float(monthly_excess),
                "strategy_equity_change": str(monthly_row.get("equity_change", "")),
                "strategy_worst_drawdown_pct": str(monthly_row.get("worst_drawdown_pct", "")),
                "excess_status": "NEGATIVE_EXCESS" if monthly_excess < 0 else "POSITIVE_EXCESS",
                "diagnostic": ";".join(diagnostics),
            }
        )
    return rows


def analyze_monthly_benchmark_contributions(
    monthly_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
    *,
    scenario: str = "",
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for monthly_row in monthly_rows:
        month = str(monthly_row.get("month", "")).strip()
        start_date = str(monthly_row.get("start_date", "")).strip()
        end_date = str(monthly_row.get("end_date", "")).strip()
        if not month or not start_date or not end_date:
            continue
        decision_row = _decision_row_for_month(decision_rows, month)
        strategy_weights = _parse_decision_target_weights(decision_row)
        symbol_returns = _net_period_symbol_returns(
            symbol_candles,
            start=start_date,
            end=end_date,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate,
        )
        benchmark_weight = 1 / len(symbol_returns) if symbol_returns else 0.0
        symbols = sorted(set(strategy_weights) | set(symbol_returns))
        for symbol in symbols:
            strategy_weight = strategy_weights.get(symbol, 0.0)
            symbol_return = symbol_returns.get(symbol)
            symbol_benchmark_weight = benchmark_weight if symbol in symbol_returns else 0.0
            strategy_contribution = (
                strategy_weight * symbol_return if symbol_return is not None else None
            )
            benchmark_contribution = (
                symbol_benchmark_weight * symbol_return if symbol_return is not None else None
            )
            contribution_delta = (
                strategy_contribution - benchmark_contribution
                if strategy_contribution is not None and benchmark_contribution is not None
                else None
            )
            rows.append(
                {
                    "scenario": scenario,
                    "month": month,
                    "start_date": start_date,
                    "end_date": end_date,
                    "decision_as_of_date": str(decision_row.get("as_of_date", "")),
                    "decision_reason": str(decision_row.get("reason", "")),
                    "symbol": symbol,
                    "contribution_role": _monthly_benchmark_contribution_role(
                        strategy_weight,
                        symbol_benchmark_weight,
                    ),
                    "strategy_weight": _format_optional_float(strategy_weight),
                    "benchmark_weight": _format_optional_float(symbol_benchmark_weight),
                    "symbol_return_pct": _format_optional_float(symbol_return),
                    "strategy_contribution_pct": _format_optional_float(strategy_contribution),
                    "benchmark_contribution_pct": _format_optional_float(benchmark_contribution),
                    "contribution_delta_pct": _format_optional_float(contribution_delta),
                    "diagnostic": _monthly_benchmark_contribution_diagnostic(
                        strategy_weight=strategy_weight,
                        benchmark_weight=symbol_benchmark_weight,
                        symbol_return=symbol_return,
                        contribution_delta=contribution_delta,
                    ),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            row.get("month", ""),
            _float_or_none(row.get("contribution_delta_pct")) or 0.0,
            row.get("symbol", ""),
        ),
    )


def analyze_monthly_benchmark_selection(
    monthly_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
    *,
    config: MonthlyRebalanceConfig | None = None,
    scenario: str = "",
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
) -> list[dict[str, str]]:
    cfg = config or MonthlyRebalanceConfig()
    contribution_rows = analyze_monthly_benchmark_contributions(
        monthly_rows,
        decision_rows,
        symbol_candles,
        scenario=scenario,
        fee_rate=fee_rate,
        tax_rate=tax_rate,
        slippage_rate=slippage_rate,
    )
    decision_by_month = {
        str(row.get("month", "")): _decision_row_for_month(decision_rows, str(row.get("month", "")))
        for row in monthly_rows
        if str(row.get("month", ""))
    }
    rank_cache: dict[str, dict[str, tuple[int, float]]] = {}
    rows: list[dict[str, str]] = []
    for row in contribution_rows:
        month = str(row.get("month", "")).strip()
        decision_row = decision_by_month.get(month, {})
        signal_date = str(decision_row.get("signal_date", "")).strip()
        if signal_date and signal_date not in rank_cache:
            rank_cache[signal_date] = _average_trading_value_rank_map(
                symbol_candles,
                signal_date=signal_date,
                window_days=cfg.point_in_time_liquidity_window_days,
            )
        rank_data = rank_cache.get(signal_date, {})
        symbol = str(row.get("symbol", "")).strip()
        rank, average_trading_value = rank_data.get(symbol, (None, None))
        rank_gap = (
            rank - cfg.market_beta_proxy_size
            if rank is not None and cfg.market_beta_proxy_size > 0
            else None
        )
        rows.append(
            {
                "scenario": str(row.get("scenario", "")),
                "month": month,
                "start_date": str(row.get("start_date", "")),
                "end_date": str(row.get("end_date", "")),
                "decision_as_of_date": str(decision_row.get("as_of_date", "")),
                "decision_signal_date": signal_date,
                "decision_reason": str(decision_row.get("reason", "")),
                "symbol": symbol,
                "contribution_role": str(row.get("contribution_role", "")),
                "strategy_weight": str(row.get("strategy_weight", "")),
                "benchmark_weight": str(row.get("benchmark_weight", "")),
                "symbol_return_pct": str(row.get("symbol_return_pct", "")),
                "contribution_delta_pct": str(row.get("contribution_delta_pct", "")),
                "contribution_diagnostic": str(row.get("diagnostic", "")),
                "liquidity_rank": "" if rank is None else str(rank),
                "average_trading_value": _format_optional_float(average_trading_value),
                "proxy_cutoff_rank": str(cfg.market_beta_proxy_size),
                "rank_gap_to_proxy_cutoff": "" if rank_gap is None else str(rank_gap),
                "selection_diagnostic": _monthly_benchmark_selection_diagnostic(
                    contribution_diagnostic=str(row.get("diagnostic", "")),
                    strategy_weight=_float_or_none(row.get("strategy_weight")) or 0.0,
                    liquidity_rank=rank,
                    proxy_cutoff_rank=cfg.market_beta_proxy_size,
                ),
            }
        )
    return rows


def analyze_monthly_benchmark_selection_summary(
    selection_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in selection_rows:
        key = (
            str(row.get("scenario", "")),
            str(row.get("month", "")),
            str(row.get("start_date", "")),
            str(row.get("end_date", "")),
        )
        grouped.setdefault(key, []).append(row)

    rows: list[dict[str, str]] = []
    for (scenario, month, start_date, end_date), month_rows in sorted(grouped.items()):
        selected_rows = [
            row
            for row in month_rows
            if (_float_or_none(row.get("strategy_weight")) or 0.0) > 0
        ]
        missed_rows = [
            row
            for row in month_rows
            if str(row.get("contribution_diagnostic", "")) == "missed_benchmark_winner"
        ]
        avoided_rows = [
            row
            for row in month_rows
            if str(row.get("contribution_diagnostic", "")) == "avoided_benchmark_loser"
        ]
        bucket_stats: dict[str, list[float]] = {
            "inside_proxy_cutoff": [],
            "13_50": [],
            "51_100": [],
            "101_200": [],
            "201_500": [],
            "501_plus": [],
            "missing": [],
        }
        for row in missed_rows:
            bucket = _benchmark_selection_missed_rank_bucket(row)
            bucket_stats[bucket].append(_float_or_none(row.get("contribution_delta_pct")) or 0.0)

        missed_delta = _sum_selection_delta(missed_rows)
        selected_delta = _sum_selection_delta(selected_rows)
        low_liquidity_delta = sum(bucket_stats["501_plus"])
        low_liquidity_share = (
            abs(low_liquidity_delta) / abs(missed_delta)
            if missed_delta
            else 0.0
        )
        selected_winner_count = sum(
            1 for row in selected_rows if str(row.get("selection_diagnostic", "")) == "selected_proxy_winner"
        )
        selected_loser_count = sum(
            1 for row in selected_rows if str(row.get("selection_diagnostic", "")) == "selected_proxy_loser"
        )
        rows.append(
            {
                "scenario": scenario,
                "month": month,
                "start_date": start_date,
                "end_date": end_date,
                "row_count": str(len(month_rows)),
                "selected_proxy_count": str(len(selected_rows)),
                "selected_proxy_winner_count": str(selected_winner_count),
                "selected_proxy_loser_count": str(selected_loser_count),
                "selected_proxy_delta_pct": _format_optional_float(selected_delta),
                "missed_benchmark_winner_count": str(len(missed_rows)),
                "missed_benchmark_winner_delta_pct": _format_optional_float(missed_delta),
                "missed_inside_proxy_cutoff_count": str(len(bucket_stats["inside_proxy_cutoff"])),
                "missed_inside_proxy_cutoff_delta_pct": _format_optional_float(
                    sum(bucket_stats["inside_proxy_cutoff"])
                ),
                "missed_rank_13_50_count": str(len(bucket_stats["13_50"])),
                "missed_rank_13_50_delta_pct": _format_optional_float(sum(bucket_stats["13_50"])),
                "missed_rank_51_100_count": str(len(bucket_stats["51_100"])),
                "missed_rank_51_100_delta_pct": _format_optional_float(sum(bucket_stats["51_100"])),
                "missed_rank_101_200_count": str(len(bucket_stats["101_200"])),
                "missed_rank_101_200_delta_pct": _format_optional_float(sum(bucket_stats["101_200"])),
                "missed_rank_201_500_count": str(len(bucket_stats["201_500"])),
                "missed_rank_201_500_delta_pct": _format_optional_float(sum(bucket_stats["201_500"])),
                "missed_rank_501_plus_count": str(len(bucket_stats["501_plus"])),
                "missed_rank_501_plus_delta_pct": _format_optional_float(low_liquidity_delta),
                "missed_rank_missing_count": str(len(bucket_stats["missing"])),
                "missed_rank_missing_delta_pct": _format_optional_float(sum(bucket_stats["missing"])),
                "low_liquidity_missed_winner_delta_share": _format_optional_float(low_liquidity_share),
                "avoided_benchmark_loser_count": str(len(avoided_rows)),
                "avoided_benchmark_loser_delta_pct": _format_optional_float(_sum_selection_delta(avoided_rows)),
                "diagnostic": _monthly_benchmark_selection_summary_diagnostic(
                    missed_winner_count=len(missed_rows),
                    low_liquidity_share=low_liquidity_share,
                    selected_delta=selected_delta,
                    selected_proxy_loser_count=selected_loser_count,
                    selected_proxy_winner_count=selected_winner_count,
                ),
            }
        )
    return rows


def _decision_row_for_month(decision_rows: list[dict[str, Any]], month: str) -> dict[str, Any]:
    for row in decision_rows:
        if str(row.get("as_of_date", "")).startswith(month):
            return row
    return {}


def _parse_decision_target_weights(decision_row: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for token in _split_semicolon_values(str(decision_row.get("target_weights", ""))):
        symbol, _, raw_weight = token.partition(":")
        symbol = symbol.strip()
        weight = _float_or_none(raw_weight)
        if symbol and weight is not None and weight > 0:
            weights[symbol] = weight
    if weights:
        return weights
    selected_symbols = _split_semicolon_values(str(decision_row.get("selected_symbols", "")))
    target_exposure = _float_or_none(decision_row.get("target_exposure"))
    if selected_symbols and target_exposure is not None and target_exposure > 0:
        equal_weight = target_exposure / len(selected_symbols)
        return {symbol: equal_weight for symbol in selected_symbols}
    return {}


def _net_period_symbol_returns(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
) -> dict[str, float]:
    returns: dict[str, float] = {}
    for symbol, candles in symbol_candles.items():
        symbol_return = _net_period_symbol_return_pct(
            candles,
            start=start,
            end=end,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate,
        )
        if symbol_return is not None:
            returns[symbol] = symbol_return
    return returns


def _net_period_symbol_return_pct(
    candles: list[Candle],
    *,
    start: str,
    end: str,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
) -> float | None:
    first = next((candle for candle in candles if start <= candle.date <= end and candle.open > 0), None)
    last = next((candle for candle in reversed(candles) if start <= candle.date <= end and candle.close > 0), None)
    if first is None or last is None or first.date > last.date:
        return None
    fill_price = first.open * (1 + slippage_rate)
    quantity = 1 / (fill_price * (1 + fee_rate))
    exit_price = last.close * (1 - slippage_rate)
    gross = quantity * exit_price
    final_value = gross - gross * fee_rate - gross * tax_rate
    return (final_value - 1) * 100


def _monthly_benchmark_contribution_role(strategy_weight: float, benchmark_weight: float) -> str:
    if strategy_weight <= 0 and benchmark_weight > 0:
        return "benchmark_only"
    if strategy_weight > 0 and benchmark_weight <= 0:
        return "strategy_only"
    if abs(strategy_weight - benchmark_weight) <= 1e-9:
        return "matched_weight"
    return "strategy_overweight" if strategy_weight > benchmark_weight else "strategy_underweight"


def _monthly_benchmark_contribution_diagnostic(
    *,
    strategy_weight: float,
    benchmark_weight: float,
    symbol_return: float | None,
    contribution_delta: float | None,
) -> str:
    if symbol_return is None or contribution_delta is None:
        return "missing_symbol_return"
    if strategy_weight <= 0 and benchmark_weight > 0 and symbol_return > 0:
        return "missed_benchmark_winner"
    if strategy_weight < benchmark_weight and symbol_return > 0 and contribution_delta < 0:
        return "underweighted_benchmark_winner"
    if strategy_weight > benchmark_weight and symbol_return < 0 and contribution_delta < 0:
        return "overweighted_loser"
    if strategy_weight <= 0 and benchmark_weight > 0 and symbol_return < 0:
        return "avoided_benchmark_loser"
    if contribution_delta > 0:
        return "positive_contribution_delta"
    if contribution_delta < 0:
        return "negative_contribution_delta"
    return "neutral_contribution_delta"


def _monthly_benchmark_selection_diagnostic(
    *,
    contribution_diagnostic: str,
    strategy_weight: float,
    liquidity_rank: int | None,
    proxy_cutoff_rank: int,
) -> str:
    if contribution_diagnostic == "missed_benchmark_winner":
        if liquidity_rank is None:
            return "missed_no_liquidity_rank"
        if proxy_cutoff_rank > 0 and liquidity_rank > proxy_cutoff_rank:
            return "missed_outside_proxy_liquidity_cutoff"
        return "missed_inside_proxy_liquidity_cutoff"
    if strategy_weight > 0 and contribution_diagnostic == "overweighted_loser":
        return "selected_proxy_loser"
    if strategy_weight > 0 and contribution_diagnostic == "positive_contribution_delta":
        return "selected_proxy_winner"
    if contribution_diagnostic == "avoided_benchmark_loser":
        return "avoided_benchmark_loser"
    if strategy_weight > 0:
        return "selected_proxy_other"
    return contribution_diagnostic


def _sum_selection_delta(rows: list[dict[str, Any]]) -> float:
    return sum(_float_or_none(row.get("contribution_delta_pct")) or 0.0 for row in rows)


def _benchmark_selection_missed_rank_bucket(row: dict[str, Any]) -> str:
    rank = _int_or_none(row.get("liquidity_rank"))
    if rank is None:
        return "missing"
    cutoff = _int_or_none(row.get("proxy_cutoff_rank")) or 0
    if cutoff > 0 and rank <= cutoff:
        return "inside_proxy_cutoff"
    if 13 <= rank <= 50:
        return "13_50"
    if 51 <= rank <= 100:
        return "51_100"
    if 101 <= rank <= 200:
        return "101_200"
    if 201 <= rank <= 500:
        return "201_500"
    return "501_plus"


def _monthly_benchmark_selection_summary_diagnostic(
    *,
    missed_winner_count: int,
    low_liquidity_share: float,
    selected_delta: float,
    selected_proxy_loser_count: int,
    selected_proxy_winner_count: int,
) -> str:
    if missed_winner_count <= 0:
        return "no_missed_winner_drag"
    if low_liquidity_share >= 0.5:
        return "low_liquidity_recovery_drag"
    if selected_delta < 0 and selected_proxy_loser_count > selected_proxy_winner_count:
        return "selected_proxy_loser_drag"
    return "mixed_recovery_selection_drag"


def compare_monthly_benchmark_selection_summary_reports(
    selection_summary_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    validation_by_name = {
        str(row.get("name", "")).strip(): row
        for row in validation_rows
        if str(row.get("name", "")).strip()
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in selection_summary_rows:
        scenario = str(row.get("scenario", "")).strip()
        grouped.setdefault(scenario, []).append(row)

    comparison_rows: list[dict[str, str]] = []
    for scenario, rows in sorted(grouped.items()):
        validation = validation_by_name.get(scenario, {})
        deployable = _parse_bool(validation.get("deployable", False)) if validation else None
        missed_delta = _sum_benchmark_selection_summary_values(
            rows,
            "missed_benchmark_winner_delta_pct",
        )
        missed_rank_501_plus_delta = _sum_benchmark_selection_summary_values(
            rows,
            "missed_rank_501_plus_delta_pct",
        )
        low_liquidity_share = (
            abs(missed_rank_501_plus_delta) / abs(missed_delta)
            if missed_delta
            else 0.0
        )
        low_liquidity_rows = [
            row
            for row in rows
            if str(row.get("diagnostic", "")).strip() == "low_liquidity_recovery_drag"
        ]
        selected_proxy_count = int(
            _sum_benchmark_selection_summary_values(rows, "selected_proxy_count")
        )
        selected_proxy_winner_count = int(
            _sum_benchmark_selection_summary_values(rows, "selected_proxy_winner_count")
        )
        selected_proxy_loser_count = int(
            _sum_benchmark_selection_summary_values(rows, "selected_proxy_loser_count")
        )
        selected_proxy_delta = _sum_benchmark_selection_summary_values(
            rows,
            "selected_proxy_delta_pct",
        )
        selected_proxy_loser_share = (
            selected_proxy_loser_count / selected_proxy_count
            if selected_proxy_count
            else 0.0
        )
        selected_proxy_delta_per_selected = (
            selected_proxy_delta / selected_proxy_count
            if selected_proxy_count
            else 0.0
        )
        negative_selected_proxy_rows = [
            row
            for row in rows
            if (_float_or_none(row.get("selected_proxy_delta_pct")) or 0.0) < 0
        ]
        worst_selected_proxy_row = min(
            rows,
            key=lambda row: _float_or_none(row.get("selected_proxy_delta_pct")) or 0.0,
            default={},
        )
        worst_selected_proxy_delta = _float_or_none(
            worst_selected_proxy_row.get("selected_proxy_delta_pct")
        )
        worst_row = min(
            rows,
            key=lambda row: _float_or_none(row.get("missed_benchmark_winner_delta_pct")) or 0.0,
            default={},
        )
        worst_delta = _float_or_none(worst_row.get("missed_benchmark_winner_delta_pct"))
        comparison_rows.append(
            {
                "scenario": scenario,
                "deployable": "" if deployable is None else str(deployable),
                "reason": str(validation.get("reason", "")),
                "excess_return_pct": _format_optional_float(
                    _float_or_none(validation.get("excess_return_pct"))
                ),
                "max_drawdown_pct": _format_optional_float(
                    _float_or_none(validation.get("max_drawdown_pct"))
                ),
                "month_count": str(len(rows)),
                "low_liquidity_drag_month_count": str(len(low_liquidity_rows)),
                "selected_proxy_count": str(selected_proxy_count),
                "selected_proxy_winner_count": str(selected_proxy_winner_count),
                "selected_proxy_loser_count": str(selected_proxy_loser_count),
                "selected_proxy_loser_share": _format_optional_float(
                    selected_proxy_loser_share
                ),
                "selected_proxy_delta_pct": _format_optional_float(selected_proxy_delta),
                "selected_proxy_delta_per_selected_pct": _format_optional_float(
                    selected_proxy_delta_per_selected
                ),
                "negative_selected_proxy_month_count": str(len(negative_selected_proxy_rows)),
                "worst_selected_proxy_month": str(worst_selected_proxy_row.get("month", "")),
                "worst_selected_proxy_delta_pct": _format_optional_float(
                    worst_selected_proxy_delta
                ),
                "missed_benchmark_winner_delta_pct": _format_optional_float(missed_delta),
                "missed_rank_501_plus_delta_pct": _format_optional_float(
                    missed_rank_501_plus_delta
                ),
                "low_liquidity_missed_winner_delta_share": _format_optional_float(
                    low_liquidity_share
                ),
                "worst_missed_month": str(worst_row.get("month", "")),
                "worst_missed_month_delta_pct": _format_optional_float(worst_delta),
                "diagnostic": _monthly_benchmark_selection_summary_comparison_diagnostic(
                    deployable=deployable,
                    low_liquidity_drag_month_count=len(low_liquidity_rows),
                ),
            }
        )
    return comparison_rows


def _sum_benchmark_selection_summary_values(rows: list[dict[str, Any]], column: str) -> float:
    return sum(_float_or_none(row.get(column)) or 0.0 for row in rows)


def _monthly_benchmark_selection_summary_comparison_diagnostic(
    *,
    deployable: bool | None,
    low_liquidity_drag_month_count: int,
) -> str:
    has_low_liquidity_drag = low_liquidity_drag_month_count > 0
    if deployable is False and has_low_liquidity_drag:
        return "failed_with_shared_low_liquidity_recovery_drag"
    if deployable is True and has_low_liquidity_drag:
        return "passed_despite_low_liquidity_recovery_drag"
    if deployable is False:
        return "failed_selection_review"
    if deployable is True:
        return "passed_selection_review"
    if has_low_liquidity_drag:
        return "shared_low_liquidity_recovery_drag"
    return "selection_review"


def compare_monthly_benchmark_selection_window_reports(
    selection_summary_rows: list[dict[str, Any]],
    benchmark_excess_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    *,
    window_start_month: str,
    window_end_month: str,
) -> list[dict[str, str]]:
    validation_by_name = {
        str(row.get("name", "")).strip(): row
        for row in validation_rows
        if str(row.get("name", "")).strip()
    }
    benchmark_by_key = {
        (str(row.get("scenario", "")).strip(), str(row.get("month", "")).strip()): row
        for row in benchmark_excess_rows
    }
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in selection_summary_rows:
        scenario = str(row.get("scenario", "")).strip()
        month = str(row.get("month", "")).strip()
        window = _month_window_label(
            month,
            window_start_month=window_start_month,
            window_end_month=window_end_month,
        )
        if scenario and month and window:
            grouped.setdefault((scenario, window), []).append(row)

    rows: list[dict[str, str]] = []
    window_order = {"pre_window": 0, "window": 1, "post_window": 2}
    for (scenario, window), window_rows in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], window_order.get(item[0][1], 99)),
    ):
        validation = validation_by_name.get(scenario, {})
        deployable = _parse_bool(validation.get("deployable", False)) if validation else None
        benchmark_rows = [
            benchmark_by_key.get((scenario, str(row.get("month", "")).strip()), {})
            for row in window_rows
        ]
        start_dates = [
            str(benchmark_row.get("start_date") or selection_row.get("start_date", "")).strip()
            for selection_row, benchmark_row in zip(window_rows, benchmark_rows)
            if str(benchmark_row.get("start_date") or selection_row.get("start_date", "")).strip()
        ]
        end_dates = [
            str(benchmark_row.get("end_date") or selection_row.get("end_date", "")).strip()
            for selection_row, benchmark_row in zip(window_rows, benchmark_rows)
            if str(benchmark_row.get("end_date") or selection_row.get("end_date", "")).strip()
        ]
        strategy_return = _compound_return_pct(
            _float_or_none(row.get("strategy_return_pct")) for row in benchmark_rows
        )
        benchmark_return = _compound_return_pct(
            _float_or_none(row.get("benchmark_return_pct")) for row in benchmark_rows
        )
        selected_proxy_count = int(
            _sum_benchmark_selection_summary_values(window_rows, "selected_proxy_count")
        )
        selected_proxy_delta = _sum_benchmark_selection_summary_values(
            window_rows,
            "selected_proxy_delta_pct",
        )
        selected_proxy_delta_per_selected = (
            selected_proxy_delta / selected_proxy_count
            if selected_proxy_count
            else 0.0
        )
        negative_selected_proxy_rows = [
            row
            for row in window_rows
            if (_float_or_none(row.get("selected_proxy_delta_pct")) or 0.0) < 0
        ]
        window_excess = (
            strategy_return - benchmark_return
            if strategy_return is not None and benchmark_return is not None
            else None
        )
        rows.append(
            {
                "scenario": scenario,
                "window": window,
                "deployable": "" if deployable is None else str(deployable),
                "reason": str(validation.get("reason", "")),
                "window_start_month": min(str(row.get("month", "")) for row in window_rows),
                "window_end_month": max(str(row.get("month", "")) for row in window_rows),
                "window_start_date": min(start_dates) if start_dates else "",
                "window_end_date": max(end_dates) if end_dates else "",
                "month_count": str(len(window_rows)),
                "strategy_return_pct": _format_optional_float(strategy_return),
                "benchmark_return_pct": _format_optional_float(benchmark_return),
                "window_excess_return_pct": _format_optional_float(window_excess),
                "selected_proxy_count": str(selected_proxy_count),
                "selected_proxy_delta_pct": _format_optional_float(selected_proxy_delta),
                "selected_proxy_delta_per_selected_pct": _format_optional_float(
                    selected_proxy_delta_per_selected
                ),
                "negative_selected_proxy_month_count": str(len(negative_selected_proxy_rows)),
                "missed_benchmark_winner_delta_pct": _format_optional_float(
                    _sum_benchmark_selection_summary_values(
                        window_rows,
                        "missed_benchmark_winner_delta_pct",
                    )
                ),
                "diagnostic": _monthly_benchmark_selection_window_diagnostic(
                    deployable=deployable,
                    window=window,
                    window_excess=window_excess,
                ),
            }
        )
    return rows


def _month_window_label(
    month: str,
    *,
    window_start_month: str,
    window_end_month: str,
) -> str:
    if not month:
        return ""
    if month < window_start_month:
        return "pre_window"
    if month > window_end_month:
        return "post_window"
    return "window"


def _compound_return_pct(values: Any) -> float | None:
    product = 1.0
    count = 0
    for value in values:
        if value is None:
            continue
        product *= 1.0 + value / 100.0
        count += 1
    if count <= 0:
        return None
    return (product - 1.0) * 100.0


def _monthly_benchmark_selection_window_diagnostic(
    *,
    deployable: bool | None,
    window: str,
    window_excess: float | None,
) -> str:
    if deployable is False and window == "pre_window" and (window_excess or 0.0) < 0:
        return "failed_pre_window_excess_drag"
    if deployable is False and window == "window" and (window_excess or 0.0) < 0:
        return "failed_window_excess_drag"
    if deployable is False and window == "window" and (window_excess or 0.0) >= 0:
        return "failed_window_not_primary_drag"
    if deployable is True and (window_excess or 0.0) >= 0:
        return "passed_window_excess_positive"
    if window_excess is not None and window_excess < 0:
        return "window_excess_drag"
    return "window_review"


def _int_or_none(value: Any) -> int | None:
    number = _float_or_none(value)
    if number is None:
        return None
    return int(number)


def compare_monthly_attribution_reports(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    scenario: str = "",
    candidate_label: str = "candidate",
    drawdown_threshold_pct: float = -25.0,
) -> list[dict[str, str]]:
    baseline_by_month = {str(row.get("month", "")): row for row in baseline_rows if str(row.get("month", ""))}
    candidate_by_month = {str(row.get("month", "")): row for row in candidate_rows if str(row.get("month", ""))}
    rows: list[dict[str, str]] = []
    for month in sorted(set(baseline_by_month) | set(candidate_by_month)):
        baseline = baseline_by_month.get(month, {})
        candidate = candidate_by_month.get(month, {})
        baseline_return = _float_or_none(baseline.get("return_pct"))
        candidate_return = _float_or_none(candidate.get("return_pct"))
        baseline_change = _float_or_none(baseline.get("equity_change"))
        candidate_change = _float_or_none(candidate.get("equity_change"))
        baseline_drawdown = _float_or_none(baseline.get("worst_drawdown_pct"))
        candidate_drawdown = _float_or_none(candidate.get("worst_drawdown_pct"))
        baseline_breached = baseline_drawdown is not None and baseline_drawdown <= drawdown_threshold_pct
        candidate_breached = candidate_drawdown is not None and candidate_drawdown <= drawdown_threshold_pct
        crossed_threshold = candidate_breached and not baseline_breached
        rows.append(
            {
                "scenario": scenario,
                "candidate_label": candidate_label,
                "month": month,
                "baseline_start_date": str(baseline.get("start_date", "")),
                "baseline_end_date": str(baseline.get("end_date", "")),
                "candidate_start_date": str(candidate.get("start_date", "")),
                "candidate_end_date": str(candidate.get("end_date", "")),
                "baseline_return_pct": _format_optional_float(baseline_return),
                "candidate_return_pct": _format_optional_float(candidate_return),
                "return_delta_pct": _format_optional_float(_optional_delta(candidate_return, baseline_return)),
                "baseline_equity_change": _format_optional_float(baseline_change),
                "candidate_equity_change": _format_optional_float(candidate_change),
                "equity_change_delta": _format_optional_float(_optional_delta(candidate_change, baseline_change)),
                "baseline_worst_equity": str(baseline.get("worst_equity", "")),
                "candidate_worst_equity": str(candidate.get("worst_equity", "")),
                "baseline_worst_drawdown_pct": _format_optional_float(baseline_drawdown),
                "candidate_worst_drawdown_pct": _format_optional_float(candidate_drawdown),
                "drawdown_delta_pct": _format_optional_float(_optional_delta(candidate_drawdown, baseline_drawdown)),
                "baseline_status": str(baseline.get("status", "")),
                "candidate_status": str(candidate.get("status", "")),
                "drawdown_threshold_pct": _format_optional_float(drawdown_threshold_pct),
                "baseline_breached_drawdown_threshold": str(baseline_breached),
                "candidate_breached_drawdown_threshold": str(candidate_breached),
                "candidate_crossed_drawdown_threshold": str(crossed_threshold),
                "diagnostic": _monthly_attribution_comparison_diagnostic(
                    baseline,
                    candidate,
                    return_delta=_optional_delta(candidate_return, baseline_return),
                    drawdown_delta=_optional_delta(candidate_drawdown, baseline_drawdown),
                    crossed_threshold=crossed_threshold,
                ),
            }
        )
    return rows


def _optional_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return value - baseline


def _monthly_attribution_comparison_diagnostic(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    return_delta: float | None,
    drawdown_delta: float | None,
    crossed_threshold: bool,
) -> str:
    if not baseline or not candidate:
        return "missing_month"
    if crossed_threshold:
        return "new_drawdown_breach"
    if drawdown_delta is not None and drawdown_delta < 0:
        return "drawdown_regression"
    if return_delta is not None and return_delta < 0:
        return "return_drag"
    if drawdown_delta is not None and drawdown_delta > 0:
        return "drawdown_improved"
    if return_delta is not None and return_delta > 0:
        return "return_improved"
    return "unchanged"


def compare_monthly_decision_attribution_reports(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    scenario: str = "",
    candidate_label: str = "candidate",
) -> list[dict[str, str]]:
    baseline_by_date = {
        str(row.get("as_of_date", "")): row
        for row in baseline_rows
        if str(row.get("as_of_date", ""))
    }
    candidate_by_date = {
        str(row.get("as_of_date", "")): row
        for row in candidate_rows
        if str(row.get("as_of_date", ""))
    }
    rows: list[dict[str, str]] = []
    for as_of_date in sorted(set(baseline_by_date) | set(candidate_by_date)):
        baseline = baseline_by_date.get(as_of_date, {})
        candidate = candidate_by_date.get(as_of_date, {})
        baseline_exposure = _float_or_none(baseline.get("target_exposure"))
        candidate_exposure = _float_or_none(candidate.get("target_exposure"))
        baseline_cash = _float_or_none(baseline.get("cash_weight"))
        candidate_cash = _float_or_none(candidate.get("cash_weight"))
        baseline_count = _float_or_none(baseline.get("position_count"))
        candidate_count = _float_or_none(candidate.get("position_count"))
        baseline_symbols = _decision_symbol_list(baseline)
        candidate_symbols = _decision_symbol_list(candidate)
        baseline_symbol_set = set(baseline_symbols)
        candidate_symbol_set = set(candidate_symbols)
        baseline_only = [symbol for symbol in baseline_symbols if symbol not in candidate_symbol_set]
        candidate_only = [symbol for symbol in candidate_symbols if symbol not in baseline_symbol_set]
        shared_count = len(baseline_symbol_set & candidate_symbol_set)
        exposure_delta = _optional_delta(candidate_exposure, baseline_exposure)
        cash_delta = _optional_delta(candidate_cash, baseline_cash)
        position_delta = _optional_delta(candidate_count, baseline_count)
        diagnostics = _monthly_decision_comparison_diagnostics(
            baseline,
            candidate,
            exposure_delta=exposure_delta,
            cash_delta=cash_delta,
            position_delta=position_delta,
            baseline_only=baseline_only,
            candidate_only=candidate_only,
        )
        rows.append(
            {
                "scenario": scenario,
                "candidate_label": candidate_label,
                "as_of_date": as_of_date,
                "month": as_of_date[:7],
                "baseline_signal_date": str(baseline.get("signal_date", "")),
                "candidate_signal_date": str(candidate.get("signal_date", "")),
                "baseline_mode": str(baseline.get("mode", "")),
                "candidate_mode": str(candidate.get("mode", "")),
                "baseline_selected_preset": str(baseline.get("selected_preset", "")),
                "candidate_selected_preset": str(candidate.get("selected_preset", "")),
                "baseline_reason": str(baseline.get("reason", "")),
                "candidate_reason": str(candidate.get("reason", "")),
                "baseline_target_exposure": _format_optional_float(baseline_exposure),
                "candidate_target_exposure": _format_optional_float(candidate_exposure),
                "target_exposure_delta": _format_optional_float(exposure_delta),
                "baseline_cash_weight": _format_optional_float(baseline_cash),
                "candidate_cash_weight": _format_optional_float(candidate_cash),
                "cash_weight_delta": _format_optional_float(cash_delta),
                "baseline_position_count": _format_optional_float(baseline_count),
                "candidate_position_count": _format_optional_float(candidate_count),
                "position_count_delta": _format_optional_float(position_delta),
                "shared_symbol_count": str(shared_count),
                "baseline_only_symbol_count": str(len(baseline_only)),
                "candidate_only_symbol_count": str(len(candidate_only)),
                "baseline_only_symbols": ";".join(baseline_only),
                "candidate_only_symbols": ";".join(candidate_only),
                "baseline_selected_symbols": ";".join(baseline_symbols),
                "candidate_selected_symbols": ";".join(candidate_symbols),
                "diagnostic": ";".join(diagnostics) if diagnostics else "same_decision",
            }
        )
    return rows


def compare_monthly_entry_month_reports(
    failed_benchmark_rows: list[dict[str, Any]],
    reference_benchmark_rows: list[dict[str, Any]],
    failed_selection_rows: list[dict[str, Any]],
    reference_selection_rows: list[dict[str, Any]],
    failed_decision_rows: list[dict[str, Any]],
    reference_decision_rows: list[dict[str, Any]],
    *,
    failed_label: str,
    reference_label: str,
    month: str,
) -> list[dict[str, str]]:
    failed_benchmark = _row_for_month(failed_benchmark_rows, month)
    reference_benchmark = _row_for_month(reference_benchmark_rows, month)
    failed_selection = _row_for_month(failed_selection_rows, month)
    reference_selection = _row_for_month(reference_selection_rows, month)
    failed_decision = _decision_for_month(failed_decision_rows, month)
    reference_decision = _decision_for_month(reference_decision_rows, month)
    if not failed_benchmark and not reference_benchmark:
        return []

    failed_strategy = _float_or_none(failed_benchmark.get("strategy_return_pct"))
    reference_strategy = _float_or_none(reference_benchmark.get("strategy_return_pct"))
    failed_benchmark_return = _float_or_none(failed_benchmark.get("benchmark_return_pct"))
    reference_benchmark_return = _float_or_none(reference_benchmark.get("benchmark_return_pct"))
    failed_excess = _monthly_excess_from_row(failed_benchmark)
    reference_excess = _monthly_excess_from_row(reference_benchmark)
    failed_selected_delta = _float_or_none(failed_selection.get("selected_proxy_delta_pct"))
    reference_selected_delta = _float_or_none(reference_selection.get("selected_proxy_delta_pct"))
    failed_missed_delta = _float_or_none(failed_selection.get("missed_benchmark_winner_delta_pct"))
    reference_missed_delta = _float_or_none(reference_selection.get("missed_benchmark_winner_delta_pct"))
    failed_exposure = _float_or_none(failed_decision.get("target_exposure"))
    reference_exposure = _float_or_none(reference_decision.get("target_exposure"))
    failed_cash = _float_or_none(failed_decision.get("cash_weight"))
    reference_cash = _float_or_none(reference_decision.get("cash_weight"))
    failed_symbols = _decision_symbol_list(failed_decision)
    reference_symbols = _decision_symbol_list(reference_decision)
    failed_symbol_set = set(failed_symbols)
    reference_symbol_set = set(reference_symbols)
    failed_only = [symbol for symbol in failed_symbols if symbol not in reference_symbol_set]
    reference_only = [symbol for symbol in reference_symbols if symbol not in failed_symbol_set]
    start_delta = _date_delta_days(
        str(failed_benchmark.get("start_date", "")),
        str(reference_benchmark.get("start_date", "")),
    )
    excess_delta = _optional_delta(reference_excess, failed_excess)
    exposure_delta = _optional_delta(reference_exposure, failed_exposure)
    cash_delta = _optional_delta(reference_cash, failed_cash)
    selected_delta_delta = _optional_delta(reference_selected_delta, failed_selected_delta)
    missed_delta_delta = _optional_delta(reference_missed_delta, failed_missed_delta)
    diagnostics = _monthly_entry_month_diagnostics(
        start_delta=start_delta,
        excess_delta=excess_delta,
        exposure_delta=exposure_delta,
        failed_only=failed_only,
        reference_only=reference_only,
    )
    return [
        {
            "month": month,
            "failed_label": failed_label,
            "reference_label": reference_label,
            "failed_start_date": str(failed_benchmark.get("start_date", "")),
            "reference_start_date": str(reference_benchmark.get("start_date", "")),
            "start_date_delta_days": "" if start_delta is None else str(start_delta),
            "failed_end_date": str(failed_benchmark.get("end_date", "")),
            "reference_end_date": str(reference_benchmark.get("end_date", "")),
            "failed_strategy_return_pct": _format_optional_float(failed_strategy),
            "reference_strategy_return_pct": _format_optional_float(reference_strategy),
            "strategy_return_delta": _format_optional_float(_optional_delta(reference_strategy, failed_strategy)),
            "failed_benchmark_return_pct": _format_optional_float(failed_benchmark_return),
            "reference_benchmark_return_pct": _format_optional_float(reference_benchmark_return),
            "benchmark_return_delta": _format_optional_float(
                _optional_delta(reference_benchmark_return, failed_benchmark_return)
            ),
            "failed_monthly_excess_return_pct": _format_optional_float(failed_excess),
            "reference_monthly_excess_return_pct": _format_optional_float(reference_excess),
            "monthly_excess_delta": _format_optional_float(excess_delta),
            "failed_selected_proxy_delta_pct": _format_optional_float(failed_selected_delta),
            "reference_selected_proxy_delta_pct": _format_optional_float(reference_selected_delta),
            "selected_proxy_delta_delta": _format_optional_float(selected_delta_delta),
            "failed_missed_benchmark_winner_delta_pct": _format_optional_float(failed_missed_delta),
            "reference_missed_benchmark_winner_delta_pct": _format_optional_float(reference_missed_delta),
            "missed_benchmark_winner_delta_delta": _format_optional_float(missed_delta_delta),
            "failed_decision_as_of_date": str(failed_decision.get("as_of_date", "")),
            "reference_decision_as_of_date": str(reference_decision.get("as_of_date", "")),
            "failed_signal_date": str(failed_decision.get("signal_date", "")),
            "reference_signal_date": str(reference_decision.get("signal_date", "")),
            "failed_reason": str(failed_decision.get("reason", "")),
            "reference_reason": str(reference_decision.get("reason", "")),
            "failed_target_exposure": _format_optional_float(failed_exposure),
            "reference_target_exposure": _format_optional_float(reference_exposure),
            "target_exposure_delta": _format_optional_float(exposure_delta),
            "failed_cash_weight": _format_optional_float(failed_cash),
            "reference_cash_weight": _format_optional_float(reference_cash),
            "cash_weight_delta": _format_optional_float(cash_delta),
            "shared_symbol_count": str(len(failed_symbol_set & reference_symbol_set)),
            "failed_only_symbols": ";".join(failed_only),
            "reference_only_symbols": ";".join(reference_only),
            "failed_selected_symbols": ";".join(failed_symbols),
            "reference_selected_symbols": ";".join(reference_symbols),
            "diagnostic": ";".join(diagnostics) if diagnostics else "same_entry_month",
        }
    ]


def _row_for_month(rows: list[dict[str, Any]], month: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("month", "")).strip() == month:
            return row
    return {}


def _decision_for_month(rows: list[dict[str, Any]], month: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("as_of_date", "")).startswith(month):
            return row
    return {}


def _monthly_excess_from_row(row: dict[str, Any]) -> float | None:
    excess = _float_or_none(row.get("monthly_excess_return_pct"))
    if excess is not None:
        return excess
    strategy = _float_or_none(row.get("strategy_return_pct"))
    benchmark = _float_or_none(row.get("benchmark_return_pct"))
    return _optional_delta(strategy, benchmark)


def _date_delta_days(start: str, reference: str) -> int | None:
    try:
        return (date.fromisoformat(reference) - date.fromisoformat(start)).days
    except ValueError:
        return None


def _monthly_entry_month_diagnostics(
    *,
    start_delta: int | None,
    excess_delta: float | None,
    exposure_delta: float | None,
    failed_only: list[str],
    reference_only: list[str],
) -> list[str]:
    diagnostics: list[str] = []
    if start_delta:
        diagnostics.append("entry_date_mismatch")
    if excess_delta is not None and excess_delta > 0:
        diagnostics.append("reference_excess_better")
    elif excess_delta is not None and excess_delta < 0:
        diagnostics.append("failed_excess_better")
    if exposure_delta is not None and exposure_delta > 0:
        diagnostics.append("reference_exposure_higher")
    elif exposure_delta is not None and exposure_delta < 0:
        diagnostics.append("failed_exposure_higher")
    if failed_only or reference_only:
        diagnostics.append("symbol_rotation")
    return diagnostics


def compare_monthly_entry_path_subperiod_reports(
    failed_path_rows: list[dict[str, Any]],
    reference_path_rows: list[dict[str, Any]],
    *,
    failed_label: str,
    reference_label: str,
    month_start: str,
    month_end: str,
    split_date: str,
) -> list[dict[str, str]]:
    segments = [
        (
            "failed_pre_split",
            failed_label,
            _path_rows_between(failed_path_rows, start=month_start, end=_previous_iso_date(split_date)),
        ),
        (
            "failed_post_split",
            failed_label,
            _path_rows_between(failed_path_rows, start=split_date, end=month_end),
        ),
        (
            "reference_post_split",
            reference_label,
            _path_rows_between(reference_path_rows, start=split_date, end=month_end),
        ),
    ]
    reference_summary = _summarize_path_subperiod(segments[2][2])
    reference_symbols = set(reference_summary["end_symbols"])

    rows: list[dict[str, str]] = []
    for subperiod, label, path_rows in segments:
        summary = _summarize_path_subperiod(path_rows)
        end_symbols = summary["end_symbols"]
        end_symbol_set = set(end_symbols)
        only_symbols = [
            symbol for symbol in end_symbols if symbol not in reference_symbols
        ]
        reference_only = [
            symbol for symbol in reference_summary["end_symbols"] if symbol not in end_symbol_set
        ]
        return_delta = _optional_delta(summary["return_pct"], reference_summary["return_pct"])
        exposure_delta = _optional_delta(
            summary["average_exposure"],
            reference_summary["average_exposure"],
        )
        diagnostics = _entry_path_subperiod_diagnostics(
            subperiod=subperiod,
            return_delta=return_delta,
            exposure_delta=exposure_delta,
            only_symbols=only_symbols,
            reference_only=reference_only,
        )
        rows.append(
            {
                "subperiod": subperiod,
                "failed_label": failed_label,
                "reference_label": reference_label,
                "start_date": summary["start_date"],
                "end_date": summary["end_date"],
                "trading_days": str(summary["trading_days"]),
                "return_pct": _format_optional_float(summary["return_pct"]),
                "average_exposure": _format_optional_float(summary["average_exposure"]),
                "end_position_symbols": ";".join(end_symbols),
                "return_delta_vs_reference_post": _format_optional_float(return_delta),
                "average_exposure_delta_vs_reference_post": _format_optional_float(exposure_delta),
                "shared_with_reference_post_symbol_count": str(len(end_symbol_set & reference_symbols)),
                "only_symbols_vs_reference_post": ";".join(only_symbols),
                "reference_only_symbols": ";".join(reference_only),
                "diagnostic": ";".join(diagnostics) if diagnostics else "same_as_reference_post",
            }
        )
    return rows


def _path_rows_between(rows: list[dict[str, Any]], *, start: str, end: str) -> list[dict[str, Any]]:
    return sorted(
        [
            row
            for row in rows
            if start <= str(row.get("date", "")) <= end
        ],
        key=lambda row: str(row.get("date", "")),
    )


def _previous_iso_date(day: str) -> str:
    try:
        return (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    except ValueError:
        return day


def _summarize_path_subperiod(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "start_date": "",
            "end_date": "",
            "trading_days": 0,
            "return_pct": None,
            "average_exposure": None,
            "end_symbols": [],
        }
    first_equity = _float_or_none(rows[0].get("equity"))
    last_equity = _float_or_none(rows[-1].get("equity"))
    return_pct = (
        (last_equity / first_equity - 1.0) * 100.0
        if first_equity and last_equity is not None
        else None
    )
    average_exposure = _average_numeric(row.get("exposure") for row in rows)
    return {
        "start_date": str(rows[0].get("date", "")),
        "end_date": str(rows[-1].get("date", "")),
        "trading_days": len(rows),
        "return_pct": return_pct,
        "average_exposure": average_exposure,
        "end_symbols": _split_semicolon_values(str(rows[-1].get("position_symbols", ""))),
    }


def _entry_path_subperiod_diagnostics(
    *,
    subperiod: str,
    return_delta: float | None,
    exposure_delta: float | None,
    only_symbols: list[str],
    reference_only: list[str],
) -> list[str]:
    if subperiod == "reference_post_split":
        return ["reference_post"]
    diagnostics: list[str] = []
    if return_delta is not None and return_delta < 0:
        diagnostics.append("reference_post_outperformed")
    elif return_delta is not None and return_delta > 0:
        diagnostics.append("subperiod_outperformed_reference")
    if exposure_delta is not None and exposure_delta < 0:
        diagnostics.append("reference_exposure_higher")
    elif exposure_delta is not None and exposure_delta > 0:
        diagnostics.append("subperiod_exposure_higher")
    if only_symbols or reference_only:
        diagnostics.append("symbol_rotation")
    return diagnostics


def compare_monthly_entry_contribution_overlap_reports(
    failed_contribution_rows: list[dict[str, Any]],
    reference_contribution_rows: list[dict[str, Any]],
    *,
    failed_label: str,
    reference_label: str,
    month: str,
) -> list[dict[str, str]]:
    failed_selected = _selected_contribution_rows_for_month(failed_contribution_rows, month)
    reference_selected = _selected_contribution_rows_for_month(reference_contribution_rows, month)
    failed_symbols = set(failed_selected)
    reference_symbols = set(reference_selected)
    shared_symbols = failed_symbols & reference_symbols
    failed_only_symbols = failed_symbols - reference_symbols
    reference_only_symbols = reference_symbols - failed_symbols
    total_gap = _contribution_delta(failed_selected.values(), reference_selected.values())
    shared_gap = _contribution_delta(
        (failed_selected[symbol] for symbol in shared_symbols),
        (reference_selected[symbol] for symbol in shared_symbols),
    )
    rotation_gap = _contribution_delta(
        (failed_selected[symbol] for symbol in failed_only_symbols),
        (reference_selected[symbol] for symbol in reference_only_symbols),
    )
    return [
        _entry_contribution_overlap_row(
            bucket="selected_total",
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
            failed_rows=failed_selected.values(),
            reference_rows=reference_selected.values(),
            total_gap=total_gap,
            shared_gap=shared_gap,
            rotation_gap=rotation_gap,
        ),
        _entry_contribution_overlap_row(
            bucket="shared_symbols",
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
            failed_rows=(failed_selected[symbol] for symbol in shared_symbols),
            reference_rows=(reference_selected[symbol] for symbol in shared_symbols),
            total_gap=total_gap,
            shared_gap=shared_gap,
            rotation_gap=rotation_gap,
        ),
        _entry_contribution_overlap_row(
            bucket="rotation_symbols",
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
            failed_rows=(failed_selected[symbol] for symbol in failed_only_symbols),
            reference_rows=(reference_selected[symbol] for symbol in reference_only_symbols),
            total_gap=total_gap,
            shared_gap=shared_gap,
            rotation_gap=rotation_gap,
        ),
        _entry_contribution_overlap_row(
            bucket="failed_only_symbols",
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
            failed_rows=(failed_selected[symbol] for symbol in failed_only_symbols),
            reference_rows=(),
            total_gap=total_gap,
            shared_gap=shared_gap,
            rotation_gap=rotation_gap,
        ),
        _entry_contribution_overlap_row(
            bucket="reference_only_symbols",
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
            failed_rows=(),
            reference_rows=(reference_selected[symbol] for symbol in reference_only_symbols),
            total_gap=total_gap,
            shared_gap=shared_gap,
            rotation_gap=rotation_gap,
        ),
    ]


def _selected_contribution_rows_for_month(
    rows: list[dict[str, Any]],
    month: str,
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if str(row.get("month", "")).strip() != month:
            continue
        symbol = str(row.get("symbol", "")).strip()
        if not symbol:
            continue
        strategy_weight = _float_or_none(row.get("strategy_weight")) or 0.0
        if strategy_weight <= 0:
            continue
        selected[symbol] = row
    return selected


def _entry_contribution_overlap_row(
    *,
    bucket: str,
    failed_label: str,
    reference_label: str,
    month: str,
    failed_rows: Any,
    reference_rows: Any,
    total_gap: float | None,
    shared_gap: float | None,
    rotation_gap: float | None,
) -> dict[str, str]:
    failed_list = sorted(list(failed_rows), key=lambda row: str(row.get("symbol", "")))
    reference_list = sorted(list(reference_rows), key=lambda row: str(row.get("symbol", "")))
    failed_symbols = [str(row.get("symbol", "")).strip() for row in failed_list]
    reference_symbols = [str(row.get("symbol", "")).strip() for row in reference_list]
    failed_weight = _sum_optional_values(row.get("strategy_weight") for row in failed_list)
    reference_weight = _sum_optional_values(row.get("strategy_weight") for row in reference_list)
    failed_contribution = _sum_optional_values(row.get("strategy_contribution_pct") for row in failed_list)
    reference_contribution = _sum_optional_values(row.get("strategy_contribution_pct") for row in reference_list)
    weight_delta = _optional_delta(reference_weight, failed_weight)
    contribution_delta = _optional_delta(reference_contribution, failed_contribution)
    gap_share = (
        contribution_delta / total_gap * 100.0
        if contribution_delta is not None and total_gap not in (None, 0)
        else None
    )
    diagnostics = _entry_contribution_overlap_diagnostics(
        bucket=bucket,
        weight_delta=weight_delta,
        contribution_delta=contribution_delta,
        shared_gap=shared_gap,
        rotation_gap=rotation_gap,
        failed_symbols=failed_symbols,
        reference_symbols=reference_symbols,
    )
    return {
        "bucket": bucket,
        "failed_label": failed_label,
        "reference_label": reference_label,
        "month": month,
        "failed_start_date": _first_nonempty_value(failed_list, "start_date"),
        "reference_start_date": _first_nonempty_value(reference_list, "start_date"),
        "failed_end_date": _first_nonempty_value(failed_list, "end_date"),
        "reference_end_date": _first_nonempty_value(reference_list, "end_date"),
        "failed_symbol_count": str(len(failed_symbols)),
        "reference_symbol_count": str(len(reference_symbols)),
        "shared_symbol_count": str(len(set(failed_symbols) & set(reference_symbols))),
        "failed_symbols": ";".join(failed_symbols),
        "reference_symbols": ";".join(reference_symbols),
        "failed_strategy_weight": _format_optional_float(failed_weight),
        "reference_strategy_weight": _format_optional_float(reference_weight),
        "strategy_weight_delta": _format_optional_float(weight_delta),
        "failed_strategy_contribution_pct": _format_optional_float(failed_contribution),
        "reference_strategy_contribution_pct": _format_optional_float(reference_contribution),
        "contribution_delta_pct": _format_optional_float(contribution_delta),
        "contribution_gap_share_pct": _format_optional_float(gap_share),
        "diagnostic": ";".join(diagnostics) if diagnostics else "balanced",
    }


def _sum_optional_values(values: Any) -> float:
    numbers = [
        value
        for value in (_float_or_none(raw_value) for raw_value in values)
        if value is not None
    ]
    return sum(numbers)


def _contribution_delta(failed_rows: Any, reference_rows: Any) -> float | None:
    failed = _sum_optional_values(row.get("strategy_contribution_pct") for row in failed_rows)
    reference = _sum_optional_values(row.get("strategy_contribution_pct") for row in reference_rows)
    return _optional_delta(reference, failed)


def _first_nonempty_value(rows: list[dict[str, Any]], key: str) -> str:
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def _entry_contribution_overlap_diagnostics(
    *,
    bucket: str,
    weight_delta: float | None,
    contribution_delta: float | None,
    shared_gap: float | None,
    rotation_gap: float | None,
    failed_symbols: list[str],
    reference_symbols: list[str],
) -> list[str]:
    diagnostics: list[str] = []
    if contribution_delta is not None and contribution_delta > 0:
        diagnostics.append("reference_contribution_higher")
    elif contribution_delta is not None and contribution_delta < 0:
        diagnostics.append("failed_contribution_higher")
    if weight_delta is not None and weight_delta > 0:
        diagnostics.append("reference_exposure_higher")
    elif weight_delta is not None and weight_delta < 0:
        diagnostics.append("failed_exposure_higher")
    if bucket == "selected_total" and set(failed_symbols) != set(reference_symbols):
        diagnostics.append("symbol_rotation")
        if abs(rotation_gap or 0.0) > abs(shared_gap or 0.0):
            diagnostics.append("rotation_gap_dominant")
        elif abs(shared_gap or 0.0) > abs(rotation_gap or 0.0):
            diagnostics.append("shared_gap_dominant")
    elif bucket == "shared_symbols":
        diagnostics.append("shared_symbol_exposure_gap")
    elif bucket == "rotation_symbols":
        diagnostics.append("rotation_symbol_gap")
    elif bucket == "failed_only_symbols":
        diagnostics.append("failed_only_rotation")
    elif bucket == "reference_only_symbols":
        diagnostics.append("reference_only_rotation")
    return diagnostics


def compare_monthly_entry_selection_rotation_reports(
    failed_selection_rows: list[dict[str, Any]],
    reference_selection_rows: list[dict[str, Any]],
    *,
    failed_label: str,
    reference_label: str,
    month: str,
) -> list[dict[str, str]]:
    failed_by_symbol = _selection_rows_by_symbol_for_month(failed_selection_rows, month)
    reference_by_symbol = _selection_rows_by_symbol_for_month(reference_selection_rows, month)
    selected_symbols = {
        symbol
        for symbol, row in failed_by_symbol.items()
        if _selection_row_is_selected(row)
    } | {
        symbol
        for symbol, row in reference_by_symbol.items()
        if _selection_row_is_selected(row)
    }
    rows = [
        _entry_selection_rotation_row(
            symbol=symbol,
            failed_row=failed_by_symbol.get(symbol, {}),
            reference_row=reference_by_symbol.get(symbol, {}),
            failed_label=failed_label,
            reference_label=reference_label,
            month=month,
        )
        for symbol in selected_symbols
    ]
    return sorted(
        rows,
        key=lambda row: (
            _selection_rotation_role_sort_key(row.get("rotation_role", "")),
            row.get("symbol", ""),
        ),
    )


def _selection_rows_by_symbol_for_month(
    rows: list[dict[str, Any]],
    month: str,
) -> dict[str, dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in rows:
        if str(row.get("month", "")).strip() != month:
            continue
        symbol = str(row.get("symbol", "")).strip()
        if symbol:
            by_symbol[symbol] = row
    return by_symbol


def _selection_row_is_selected(row: dict[str, Any]) -> bool:
    return (_float_or_none(row.get("strategy_weight")) or 0.0) > 0


def _entry_selection_rotation_row(
    *,
    symbol: str,
    failed_row: dict[str, Any],
    reference_row: dict[str, Any],
    failed_label: str,
    reference_label: str,
    month: str,
) -> dict[str, str]:
    failed_selected = _selection_row_is_selected(failed_row)
    reference_selected = _selection_row_is_selected(reference_row)
    rotation_role = _entry_selection_rotation_role(
        failed_selected=failed_selected,
        reference_selected=reference_selected,
    )
    failed_weight = _float_or_none(failed_row.get("strategy_weight")) or 0.0
    reference_weight = _float_or_none(reference_row.get("strategy_weight")) or 0.0
    failed_return = _float_or_none(failed_row.get("symbol_return_pct"))
    reference_return = _float_or_none(reference_row.get("symbol_return_pct"))
    failed_contribution = _float_or_none(failed_row.get("contribution_delta_pct")) or 0.0
    reference_contribution = _float_or_none(reference_row.get("contribution_delta_pct")) or 0.0
    failed_rank = _float_or_none(failed_row.get("liquidity_rank"))
    reference_rank = _float_or_none(reference_row.get("liquidity_rank"))
    weight_delta = reference_weight - failed_weight
    return_delta = _optional_delta(reference_return, failed_return)
    contribution_gap = reference_contribution - failed_contribution
    rank_delta = _optional_delta(reference_rank, failed_rank)
    diagnostics = _entry_selection_rotation_diagnostics(
        rotation_role=rotation_role,
        weight_delta=weight_delta,
        return_delta=return_delta,
        contribution_gap=contribution_gap,
        rank_delta=rank_delta,
        failed_selection_diagnostic=str(failed_row.get("selection_diagnostic", "")),
        reference_selection_diagnostic=str(reference_row.get("selection_diagnostic", "")),
    )
    return {
        "symbol": symbol,
        "rotation_role": rotation_role,
        "failed_label": failed_label,
        "reference_label": reference_label,
        "month": month,
        "failed_selected": str(failed_selected).lower(),
        "reference_selected": str(reference_selected).lower(),
        "failed_start_date": str(failed_row.get("start_date", "")),
        "reference_start_date": str(reference_row.get("start_date", "")),
        "failed_decision_as_of_date": str(failed_row.get("decision_as_of_date", "")),
        "reference_decision_as_of_date": str(reference_row.get("decision_as_of_date", "")),
        "failed_signal_date": str(failed_row.get("decision_signal_date", "")),
        "reference_signal_date": str(reference_row.get("decision_signal_date", "")),
        "failed_decision_reason": str(failed_row.get("decision_reason", "")),
        "reference_decision_reason": str(reference_row.get("decision_reason", "")),
        "failed_strategy_weight": _format_optional_float(failed_weight),
        "reference_strategy_weight": _format_optional_float(reference_weight),
        "strategy_weight_delta": _format_optional_float(weight_delta),
        "failed_symbol_return_pct": _format_optional_float(failed_return),
        "reference_symbol_return_pct": _format_optional_float(reference_return),
        "symbol_return_delta": _format_optional_float(return_delta),
        "failed_contribution_delta_pct": _format_optional_float(failed_contribution),
        "reference_contribution_delta_pct": _format_optional_float(reference_contribution),
        "contribution_delta_gap_pct": _format_optional_float(contribution_gap),
        "failed_liquidity_rank": _format_optional_float(failed_rank),
        "reference_liquidity_rank": _format_optional_float(reference_rank),
        "liquidity_rank_delta": _format_optional_float(rank_delta),
        "failed_selection_diagnostic": str(failed_row.get("selection_diagnostic", "")),
        "reference_selection_diagnostic": str(reference_row.get("selection_diagnostic", "")),
        "diagnostic": ";".join(diagnostics) if diagnostics else "balanced",
    }


def _entry_selection_rotation_role(
    *,
    failed_selected: bool,
    reference_selected: bool,
) -> str:
    if failed_selected and reference_selected:
        return "shared_symbols"
    if failed_selected:
        return "failed_only_symbols"
    if reference_selected:
        return "reference_only_symbols"
    return "unselected"


def _selection_rotation_role_sort_key(role: str) -> int:
    order = {
        "reference_only_symbols": 0,
        "failed_only_symbols": 1,
        "shared_symbols": 2,
    }
    return order.get(role, 99)


def _entry_selection_rotation_diagnostics(
    *,
    rotation_role: str,
    weight_delta: float | None,
    return_delta: float | None,
    contribution_gap: float | None,
    rank_delta: float | None,
    failed_selection_diagnostic: str,
    reference_selection_diagnostic: str,
) -> list[str]:
    diagnostics: list[str] = []
    if rotation_role == "reference_only_symbols":
        diagnostics.append("reference_selected_only")
    elif rotation_role == "failed_only_symbols":
        diagnostics.append("failed_selected_only")
    elif rotation_role == "shared_symbols":
        diagnostics.append("shared_selection")
    if contribution_gap is not None and contribution_gap > 0:
        diagnostics.append("reference_contribution_higher")
    elif contribution_gap is not None and contribution_gap < 0:
        diagnostics.append("failed_contribution_higher")
    if return_delta is not None and return_delta > 0:
        diagnostics.append("reference_return_higher")
    elif return_delta is not None and return_delta < 0:
        diagnostics.append("failed_return_higher")
    if weight_delta is not None and weight_delta > 0:
        diagnostics.append("reference_exposure_higher")
    elif weight_delta is not None and weight_delta < 0:
        diagnostics.append("failed_exposure_higher")
    if rank_delta is not None and rank_delta < 0:
        diagnostics.append("reference_liquidity_rank_better")
    elif rank_delta is not None and rank_delta > 0:
        diagnostics.append("failed_liquidity_rank_better")
    if reference_selection_diagnostic == "selected_proxy_winner":
        diagnostics.append("reference_selected_winner")
    if failed_selection_diagnostic == "selected_proxy_loser":
        diagnostics.append("failed_selected_loser")
    return diagnostics


def compare_monthly_entry_selection_eligibility_reports(
    selection_rotation_rows: list[dict[str, Any]],
    universe_filter_rows: list[dict[str, Any]],
    *,
    failed_label: str,
    reference_label: str,
) -> list[dict[str, str]]:
    exclusions = {
        (
            str(row.get("as_of_date", "")).strip(),
            str(row.get("symbol", "")).strip(),
        ): row
        for row in universe_filter_rows
        if str(row.get("symbol", "")).strip()
    }
    rows = [
        _entry_selection_eligibility_row(
            rotation_row,
            exclusions=exclusions,
            failed_label=failed_label,
            reference_label=reference_label,
        )
        for rotation_row in selection_rotation_rows
    ]
    return sorted(
        rows,
        key=lambda row: (
            _selection_rotation_role_sort_key(row.get("rotation_role", "")),
            row.get("symbol", ""),
        ),
    )


def _entry_selection_eligibility_row(
    rotation_row: dict[str, Any],
    *,
    exclusions: dict[tuple[str, str], dict[str, Any]],
    failed_label: str,
    reference_label: str,
) -> dict[str, str]:
    symbol = str(rotation_row.get("symbol", "")).strip()
    failed_signal_date = str(rotation_row.get("failed_signal_date", "")).strip()
    reference_signal_date = str(rotation_row.get("reference_signal_date", "")).strip()
    failed_exclusion = exclusions.get((failed_signal_date, symbol), {})
    reference_exclusion = exclusions.get((reference_signal_date, symbol), {})
    failed_status, failed_reason, failed_detail = _selection_eligibility_status(failed_exclusion)
    reference_status, reference_reason, reference_detail = _selection_eligibility_status(reference_exclusion)
    diagnostics = _entry_selection_eligibility_diagnostics(
        rotation_role=str(rotation_row.get("rotation_role", "")),
        failed_status=failed_status,
        failed_reason=failed_reason,
        reference_status=reference_status,
        reference_reason=reference_reason,
    )
    return {
        "symbol": symbol,
        "rotation_role": str(rotation_row.get("rotation_role", "")),
        "failed_label": failed_label,
        "reference_label": reference_label,
        "failed_selected": str(rotation_row.get("failed_selected", "")),
        "reference_selected": str(rotation_row.get("reference_selected", "")),
        "failed_signal_date": failed_signal_date,
        "reference_signal_date": reference_signal_date,
        "failed_universe_status": failed_status,
        "failed_universe_reason": failed_reason,
        "failed_universe_detail": failed_detail,
        "reference_universe_status": reference_status,
        "reference_universe_reason": reference_reason,
        "reference_universe_detail": reference_detail,
        "failed_selection_diagnostic": str(rotation_row.get("failed_selection_diagnostic", "")),
        "reference_selection_diagnostic": str(rotation_row.get("reference_selection_diagnostic", "")),
        "contribution_delta_gap_pct": str(rotation_row.get("contribution_delta_gap_pct", "")),
        "diagnostic": ";".join(diagnostics) if diagnostics else "eligible_both_sides",
    }


def _selection_eligibility_status(row: dict[str, Any]) -> tuple[str, str, str]:
    if not row:
        return "INCLUDED", "", ""
    return (
        str(row.get("status", "") or "EXCLUDED"),
        str(row.get("reason", "")),
        str(row.get("detail", "")),
    )


def _entry_selection_eligibility_diagnostics(
    *,
    rotation_role: str,
    failed_status: str,
    failed_reason: str,
    reference_status: str,
    reference_reason: str,
) -> list[str]:
    diagnostics: list[str] = []
    if failed_status == "EXCLUDED" and failed_reason:
        diagnostics.append(f"failed_universe_{failed_reason}")
    if reference_status == "EXCLUDED" and reference_reason:
        diagnostics.append(f"reference_universe_{reference_reason}")
    if (
        rotation_role == "reference_only_symbols"
        and failed_status == "EXCLUDED"
        and reference_status != "EXCLUDED"
    ):
        diagnostics.append("reference_selected_after_failed_exclusion")
    if (
        rotation_role == "failed_only_symbols"
        and reference_status == "EXCLUDED"
        and failed_status != "EXCLUDED"
    ):
        diagnostics.append("failed_selected_after_reference_exclusion")
    return diagnostics


def _decision_symbol_list(row: dict[str, Any]) -> list[str]:
    symbols = [
        symbol.strip()
        for symbol in str(row.get("selected_symbols", "")).split(";")
        if symbol.strip()
    ]
    if symbols:
        return symbols
    target_weights = str(row.get("target_weights", ""))
    return [
        token.split(":", 1)[0].strip()
        for token in target_weights.split(";")
        if token.split(":", 1)[0].strip()
    ]


def _monthly_decision_comparison_diagnostics(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    exposure_delta: float | None,
    cash_delta: float | None,
    position_delta: float | None,
    baseline_only: list[str],
    candidate_only: list[str],
) -> list[str]:
    if not baseline or not candidate:
        return ["missing_decision"]
    diagnostics: list[str] = []
    if str(baseline.get("mode", "")) != str(candidate.get("mode", "")):
        diagnostics.append("mode_changed")
    if str(baseline.get("selected_preset", "")) != str(candidate.get("selected_preset", "")):
        diagnostics.append("preset_changed")
    if str(baseline.get("reason", "")) != str(candidate.get("reason", "")):
        diagnostics.append("reason_changed")
    if exposure_delta is not None:
        if exposure_delta < 0:
            diagnostics.append("exposure_reduced")
        elif exposure_delta > 0:
            diagnostics.append("exposure_increased")
    if cash_delta is not None:
        if cash_delta > 0:
            diagnostics.append("cash_increased")
        elif cash_delta < 0:
            diagnostics.append("cash_reduced")
    if position_delta is not None and position_delta != 0:
        diagnostics.append("position_count_changed")
    if baseline_only or candidate_only:
        diagnostics.append("symbol_rotation")
    return diagnostics


def analyze_monthly_path_attribution(
    result: MonthlyBacktestResult,
    *,
    start: str = "",
    end: str = "",
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
) -> list[dict[str, str]]:
    trades_by_date: dict[str, list[MonthlyBacktestTrade]] = {}
    for trade in result.trades:
        trades_by_date.setdefault(trade.date, []).append(trade)

    cash = float(result.initial_cash)
    positions: dict[str, int] = {}
    rows: list[dict[str, str]] = []
    peak = float(result.initial_cash)
    previous_equity: float | None = None
    for day, raw_equity in zip(result.dates, result.equity_curve):
        buy_value = 0.0
        sell_value = 0.0
        estimated_trade_cost = 0.0
        trade_count = 0
        for trade in trades_by_date.get(day, []):
            gross = float(trade.price) * int(trade.quantity)
            trade_count += 1
            if trade.action.upper() == "BUY":
                positions[trade.symbol] = positions.get(trade.symbol, 0) + int(trade.quantity)
                buy_value += gross
                estimated_trade_cost += gross * fee_rate
            elif trade.action.upper() == "SELL":
                remaining = positions.get(trade.symbol, 0) - int(trade.quantity)
                if remaining > 0:
                    positions[trade.symbol] = remaining
                else:
                    positions.pop(trade.symbol, None)
                sell_value += gross
                estimated_trade_cost += gross * (fee_rate + tax_rate)
            cash = float(trade.cash_after)

        equity = float(raw_equity)
        peak = max(peak, equity)
        drawdown_pct = (equity / peak - 1.0) * 100.0 if peak > 0 else 0.0
        daily_return_pct = (
            (equity / previous_equity - 1.0) * 100.0
            if previous_equity and previous_equity > 0
            else 0.0
        )
        previous_equity = equity
        if start and day < start:
            continue
        if end and day > end:
            continue

        active_positions = {symbol: quantity for symbol, quantity in positions.items() if quantity > 0}
        position_symbols = sorted(active_positions)
        total_quantity = sum(active_positions.values())
        position_market_value = equity - cash
        exposure = position_market_value / equity if equity > 0 else 0.0
        turnover_value = buy_value + sell_value
        rows.append(
            {
                "date": day,
                "equity": _format_optional_float(equity),
                "rolling_peak": _format_optional_float(peak),
                "cash": _format_optional_float(cash),
                "position_market_value": _format_optional_float(position_market_value),
                "exposure": _format_optional_float(exposure),
                "position_count": str(len(position_symbols)),
                "total_position_quantity": str(total_quantity),
                "position_symbols": ";".join(position_symbols),
                "position_quantities": ";".join(
                    f"{symbol}:{active_positions[symbol]}" for symbol in position_symbols
                ),
                "buy_value": _format_optional_float(buy_value),
                "sell_value": _format_optional_float(sell_value),
                "turnover_value": _format_optional_float(turnover_value),
                "trade_count": str(trade_count),
                "estimated_trade_cost": _format_optional_float(estimated_trade_cost),
                "drawdown_pct": _format_optional_float(drawdown_pct),
                "daily_return_pct": _format_optional_float(daily_return_pct),
            }
        )
    return rows


def analyze_monthly_execution_gap(
    result: MonthlyBacktestResult,
    symbol_candles: dict[str, list[Candle]],
    *,
    scenario: str = "",
    min_trade_value: float = 10_000.0,
    gap_tolerance: float = 0.001,
) -> list[dict[str, str]]:
    candles_by_symbol_date = {
        symbol: {candle.date: candle for candle in candles}
        for symbol, candles in symbol_candles.items()
    }
    decisions_by_date: dict[str, list[MonthlyDecision]] = {}
    for decision in result.decisions:
        decisions_by_date.setdefault(decision.as_of_date, []).append(decision)
    trades_by_date: dict[str, list[MonthlyBacktestTrade]] = {}
    for trade in result.trades:
        trades_by_date.setdefault(trade.date, []).append(trade)

    cash = float(result.initial_cash)
    positions: dict[str, int] = {}
    last_prices: dict[str, float] = {}
    rows: list[dict[str, str]] = []

    for day in result.dates:
        day_candles = {
            symbol: by_date[day]
            for symbol, by_date in candles_by_symbol_date.items()
            if day in by_date
        }
        day_trades = trades_by_date.get(day, [])
        day_decisions = decisions_by_date.get(day, [])
        if day_decisions:
            decision = day_decisions[-1]
            for trade in day_trades:
                if trade.reason != decision.reason:
                    cash = _apply_monthly_trade_to_positions(cash, positions, trade)
            valuation_prices = _decision_valuation_prices(day_candles, last_prices)
            portfolio_value = _portfolio_value(cash, positions, valuation_prices)
            for trade in day_trades:
                if trade.reason == decision.reason:
                    cash = _apply_monthly_trade_to_positions(cash, positions, trade)
            rows.extend(
                _monthly_execution_gap_rows_for_decision(
                    decision,
                    positions=positions,
                    valuation_prices=valuation_prices,
                    portfolio_value=portfolio_value,
                    scenario=scenario,
                    min_trade_value=min_trade_value,
                    gap_tolerance=gap_tolerance,
                )
            )
        else:
            for trade in day_trades:
                cash = _apply_monthly_trade_to_positions(cash, positions, trade)

        for symbol, candle in day_candles.items():
            if candle.close > 0:
                last_prices[symbol] = candle.close
    return rows


def _apply_monthly_trade_to_positions(
    cash: float,
    positions: dict[str, int],
    trade: MonthlyBacktestTrade,
) -> float:
    quantity = int(trade.quantity)
    if trade.action.upper() == "BUY":
        positions[trade.symbol] = positions.get(trade.symbol, 0) + quantity
    elif trade.action.upper() == "SELL":
        remaining = positions.get(trade.symbol, 0) - quantity
        if remaining > 0:
            positions[trade.symbol] = remaining
        else:
            positions.pop(trade.symbol, None)
    return float(trade.cash_after)


def _decision_valuation_prices(
    day_candles: dict[str, Candle],
    last_prices: dict[str, float],
) -> dict[str, float]:
    valuation_prices = {
        symbol: candle.open
        for symbol, candle in day_candles.items()
        if candle.open > 0
    }
    for symbol, price in last_prices.items():
        valuation_prices.setdefault(symbol, price)
    return valuation_prices


def _monthly_execution_gap_rows_for_decision(
    decision: MonthlyDecision,
    *,
    positions: dict[str, int],
    valuation_prices: dict[str, float],
    portfolio_value: float,
    scenario: str,
    min_trade_value: float,
    gap_tolerance: float,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if portfolio_value <= 0:
        return rows
    for symbol, raw_weight in decision.target_weights.items():
        target_weight = float(raw_weight)
        if target_weight <= 0:
            continue
        reference_price = valuation_prices.get(symbol, 0.0)
        target_value = portfolio_value * target_weight
        actual_quantity = int(positions.get(symbol, 0))
        actual_market_value = actual_quantity * reference_price if reference_price > 0 else 0.0
        actual_weight = actual_market_value / portfolio_value if portfolio_value > 0 else 0.0
        if actual_quantity > 0 and actual_weight + gap_tolerance >= target_weight:
            continue
        execution_gap = "missed_target_symbol" if actual_quantity <= 0 else "underfilled_target_symbol"
        rows.append(
            {
                "scenario": scenario,
                "as_of_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "mode": decision.mode,
                "selected_preset": decision.selected_preset,
                "reason": decision.reason,
                "symbol": symbol,
                "target_weight": _format_optional_float(target_weight),
                "target_value": _format_optional_float(target_value),
                "reference_price": _format_optional_float(reference_price),
                "min_trade_value": _format_optional_float(min_trade_value),
                "actual_quantity": str(actual_quantity),
                "actual_market_value": _format_optional_float(actual_market_value),
                "actual_weight": _format_optional_float(actual_weight),
                "execution_gap": execution_gap,
                "diagnostic": _monthly_execution_gap_diagnostic(
                    target_value=target_value,
                    reference_price=reference_price,
                    actual_quantity=actual_quantity,
                    actual_weight=actual_weight,
                    target_weight=target_weight,
                    min_trade_value=min_trade_value,
                ),
                "paper_only": "true",
                "risk_note": "Diagnostic only; do not create or transmit live orders from this report.",
            }
        )
    return rows


def _monthly_execution_gap_diagnostic(
    *,
    target_value: float,
    reference_price: float,
    actual_quantity: int,
    actual_weight: float,
    target_weight: float,
    min_trade_value: float,
) -> str:
    if reference_price <= 0:
        return "missing_reference_price"
    if target_value < min_trade_value:
        return "target_value_below_min_trade"
    if target_value < reference_price:
        return "target_value_below_one_share"
    if actual_quantity <= 0:
        return "no_post_rebalance_position"
    if actual_weight < target_weight:
        return "target_underfilled_after_rebalance"
    return "target_aligned"


def compare_monthly_path_attribution_reports(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    scenario: str = "",
    candidate_label: str = "candidate",
    start: str = "",
    end: str = "",
) -> list[dict[str, str]]:
    baseline_by_date = {
        str(row.get("date", "")): row
        for row in baseline_rows
        if str(row.get("date", ""))
    }
    candidate_by_date = {
        str(row.get("date", "")): row
        for row in candidate_rows
        if str(row.get("date", ""))
    }
    rows: list[dict[str, str]] = []
    for day in sorted(set(baseline_by_date) | set(candidate_by_date)):
        if start and day < start:
            continue
        if end and day > end:
            continue
        baseline = baseline_by_date.get(day, {})
        candidate = candidate_by_date.get(day, {})
        baseline_equity = _float_or_none(baseline.get("equity"))
        candidate_equity = _float_or_none(candidate.get("equity"))
        baseline_peak = _float_or_none(baseline.get("rolling_peak"))
        candidate_peak = _float_or_none(candidate.get("rolling_peak"))
        baseline_drawdown = _float_or_none(baseline.get("drawdown_pct"))
        candidate_drawdown = _float_or_none(candidate.get("drawdown_pct"))
        baseline_daily_return = _float_or_none(baseline.get("daily_return_pct"))
        candidate_daily_return = _float_or_none(candidate.get("daily_return_pct"))
        baseline_cash = _float_or_none(baseline.get("cash"))
        candidate_cash = _float_or_none(candidate.get("cash"))
        baseline_exposure = _float_or_none(baseline.get("exposure"))
        candidate_exposure = _float_or_none(candidate.get("exposure"))
        baseline_count = _float_or_none(baseline.get("position_count"))
        candidate_count = _float_or_none(candidate.get("position_count"))
        baseline_quantity = _float_or_none(baseline.get("total_position_quantity"))
        candidate_quantity = _float_or_none(candidate.get("total_position_quantity"))
        baseline_turnover = _float_or_none(baseline.get("turnover_value"))
        candidate_turnover = _float_or_none(candidate.get("turnover_value"))
        baseline_cost = _float_or_none(baseline.get("estimated_trade_cost"))
        candidate_cost = _float_or_none(candidate.get("estimated_trade_cost"))
        baseline_symbols = _path_symbol_list(baseline)
        candidate_symbols = _path_symbol_list(candidate)
        baseline_symbol_set = set(baseline_symbols)
        candidate_symbol_set = set(candidate_symbols)
        baseline_only = [symbol for symbol in baseline_symbols if symbol not in candidate_symbol_set]
        candidate_only = [symbol for symbol in candidate_symbols if symbol not in baseline_symbol_set]
        equity_delta = _optional_delta(candidate_equity, baseline_equity)
        peak_delta = _optional_delta(candidate_peak, baseline_peak)
        drawdown_delta = _optional_delta(candidate_drawdown, baseline_drawdown)
        daily_return_delta = _optional_delta(candidate_daily_return, baseline_daily_return)
        cash_delta = _optional_delta(candidate_cash, baseline_cash)
        exposure_delta = _optional_delta(candidate_exposure, baseline_exposure)
        count_delta = _optional_delta(candidate_count, baseline_count)
        quantity_delta = _optional_delta(candidate_quantity, baseline_quantity)
        turnover_delta = _optional_delta(candidate_turnover, baseline_turnover)
        cost_delta = _optional_delta(candidate_cost, baseline_cost)
        diagnostics = _monthly_path_comparison_diagnostics(
            baseline,
            candidate,
            equity_delta=equity_delta,
            drawdown_delta=drawdown_delta,
            exposure_delta=exposure_delta,
            quantity_delta=quantity_delta,
            turnover_delta=turnover_delta,
            cost_delta=cost_delta,
            baseline_only=baseline_only,
            candidate_only=candidate_only,
        )
        rows.append(
            {
                "scenario": scenario,
                "candidate_label": candidate_label,
                "date": day,
                "baseline_equity": _format_optional_float(baseline_equity),
                "candidate_equity": _format_optional_float(candidate_equity),
                "equity_delta": _format_optional_float(equity_delta),
                "baseline_rolling_peak": _format_optional_float(baseline_peak),
                "candidate_rolling_peak": _format_optional_float(candidate_peak),
                "rolling_peak_delta": _format_optional_float(peak_delta),
                "baseline_drawdown_pct": _format_optional_float(baseline_drawdown),
                "candidate_drawdown_pct": _format_optional_float(candidate_drawdown),
                "drawdown_delta_pct": _format_optional_float(drawdown_delta),
                "baseline_daily_return_pct": _format_optional_float(baseline_daily_return),
                "candidate_daily_return_pct": _format_optional_float(candidate_daily_return),
                "daily_return_delta_pct": _format_optional_float(daily_return_delta),
                "baseline_cash": _format_optional_float(baseline_cash),
                "candidate_cash": _format_optional_float(candidate_cash),
                "cash_delta": _format_optional_float(cash_delta),
                "baseline_exposure": _format_optional_float(baseline_exposure),
                "candidate_exposure": _format_optional_float(candidate_exposure),
                "exposure_delta": _format_optional_float(exposure_delta),
                "baseline_position_count": _format_optional_float(baseline_count),
                "candidate_position_count": _format_optional_float(candidate_count),
                "position_count_delta": _format_optional_float(count_delta),
                "baseline_total_position_quantity": _format_optional_float(baseline_quantity),
                "candidate_total_position_quantity": _format_optional_float(candidate_quantity),
                "total_position_quantity_delta": _format_optional_float(quantity_delta),
                "shared_symbol_count": str(len(baseline_symbol_set & candidate_symbol_set)),
                "baseline_only_symbols": ";".join(baseline_only),
                "candidate_only_symbols": ";".join(candidate_only),
                "baseline_turnover_value": _format_optional_float(baseline_turnover),
                "candidate_turnover_value": _format_optional_float(candidate_turnover),
                "turnover_delta": _format_optional_float(turnover_delta),
                "baseline_estimated_trade_cost": _format_optional_float(baseline_cost),
                "candidate_estimated_trade_cost": _format_optional_float(candidate_cost),
                "estimated_trade_cost_delta": _format_optional_float(cost_delta),
                "diagnostic": ";".join(diagnostics) if diagnostics else "same_path",
            }
        )
    return rows


def summarize_monthly_path_attribution_comparison(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        day = str(row.get("date", "")).strip()
        month = day[:7]
        if not month:
            continue
        key = (
            str(row.get("scenario", "")).strip(),
            str(row.get("candidate_label", "")).strip(),
            month,
        )
        groups.setdefault(key, []).append(row)

    summary_rows: list[dict[str, str]] = []
    for key in sorted(groups):
        scenario, candidate_label, month = key
        month_rows = groups[key]
        diagnostic_counts: Counter[str] = Counter()
        for row in month_rows:
            for token in _split_semicolon_values(str(row.get("diagnostic", ""))):
                if token and token != "same_path":
                    diagnostic_counts[token] += 1

        worst_equity_row = _min_numeric_row(month_rows, "equity_delta")
        worst_drawdown_row = _min_numeric_row(month_rows, "drawdown_delta_pct")
        dominant_diagnostic = ""
        if diagnostic_counts:
            dominant_diagnostic = sorted(
                diagnostic_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]
        diagnostics = sorted(diagnostic_counts)
        summary_rows.append(
            {
                "scenario": scenario,
                "candidate_label": candidate_label,
                "month": month,
                "day_count": str(len(month_rows)),
                "equity_regression_day_count": str(_count_diagnostic(month_rows, "equity_regression")),
                "equity_improved_day_count": str(_count_diagnostic(month_rows, "equity_improved")),
                "drawdown_regression_day_count": str(_count_diagnostic(month_rows, "drawdown_regression")),
                "drawdown_improved_day_count": str(_count_diagnostic(month_rows, "drawdown_improved")),
                "exposure_reduced_day_count": str(_count_diagnostic(month_rows, "exposure_reduced")),
                "exposure_increased_day_count": str(_count_diagnostic(month_rows, "exposure_increased")),
                "symbol_rotation_day_count": str(_count_diagnostic(month_rows, "symbol_rotation")),
                "avg_equity_delta": _format_optional_float(_average_numeric(row.get("equity_delta") for row in month_rows)),
                "worst_equity_delta": _format_optional_float(_float_or_none(worst_equity_row.get("equity_delta"))),
                "worst_equity_delta_date": str(worst_equity_row.get("date", "")),
                "avg_drawdown_delta_pct": _format_optional_float(
                    _average_numeric(row.get("drawdown_delta_pct") for row in month_rows)
                ),
                "worst_drawdown_delta_pct": _format_optional_float(
                    _float_or_none(worst_drawdown_row.get("drawdown_delta_pct"))
                ),
                "worst_drawdown_delta_date": str(worst_drawdown_row.get("date", "")),
                "avg_exposure_delta": _format_optional_float(_average_numeric(row.get("exposure_delta") for row in month_rows)),
                "avg_cash_delta": _format_optional_float(_average_numeric(row.get("cash_delta") for row in month_rows)),
                "total_turnover_delta": _format_optional_float(_sum_numeric(row.get("turnover_delta") for row in month_rows)),
                "total_estimated_trade_cost_delta": _format_optional_float(
                    _sum_numeric(row.get("estimated_trade_cost_delta") for row in month_rows)
                ),
                "dominant_diagnostic": dominant_diagnostic,
                "diagnostic": ";".join(diagnostics) if diagnostics else "same_path",
                "paper_only": "true",
                "risk_note": "Diagnostic only; do not change live allocation from this summary without full validation.",
            }
        )
    return summary_rows


def _count_diagnostic(rows: list[dict[str, Any]], token: str) -> int:
    return sum(1 for row in rows if token in _split_semicolon_values(str(row.get("diagnostic", ""))))


def _min_numeric_row(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    numeric_rows = [(value, row) for row in rows if (value := _float_or_none(row.get(column))) is not None]
    if not numeric_rows:
        return {}
    return min(numeric_rows, key=lambda item: item[0])[1]


def _sum_numeric(values: Any) -> float | None:
    numeric = [value for value in (_float_or_none(value) for value in values) if value is not None]
    return sum(numeric) if numeric else None


def _path_symbol_list(row: dict[str, Any]) -> list[str]:
    return [
        symbol.strip()
        for symbol in str(row.get("position_symbols", "")).split(";")
        if symbol.strip()
    ]


def _monthly_path_comparison_diagnostics(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    equity_delta: float | None,
    drawdown_delta: float | None,
    exposure_delta: float | None,
    quantity_delta: float | None,
    turnover_delta: float | None,
    cost_delta: float | None,
    baseline_only: list[str],
    candidate_only: list[str],
) -> list[str]:
    if not baseline or not candidate:
        return ["missing_date"]
    diagnostics: list[str] = []
    if equity_delta is not None and equity_delta < 0:
        diagnostics.append("equity_regression")
    elif equity_delta is not None and equity_delta > 0:
        diagnostics.append("equity_improved")
    if drawdown_delta is not None and drawdown_delta < 0:
        diagnostics.append("drawdown_regression")
    elif drawdown_delta is not None and drawdown_delta > 0:
        diagnostics.append("drawdown_improved")
    if exposure_delta is not None and exposure_delta < 0:
        diagnostics.append("exposure_reduced")
    elif exposure_delta is not None and exposure_delta > 0:
        diagnostics.append("exposure_increased")
    if quantity_delta is not None and quantity_delta != 0:
        diagnostics.append("position_quantity_changed")
    if baseline_only or candidate_only:
        diagnostics.append("symbol_rotation")
    if turnover_delta is not None and turnover_delta > 0:
        diagnostics.append("higher_turnover")
    if cost_delta is not None and cost_delta > 0:
        diagnostics.append("higher_trade_cost")
    return diagnostics


def analyze_symbol_realized_pnl_attribution(result: MonthlyBacktestResult) -> list[dict[str, str]]:
    lots: dict[str, list[dict[str, float]]] = {}
    stats: dict[str, dict[str, Any]] = {}

    def symbol_stats(symbol: str, trade_date: str) -> dict[str, Any]:
        row = stats.setdefault(
            symbol,
            {
                "symbol": symbol,
                "realized_pnl": 0.0,
                "realized_cost": 0.0,
                "buy_value": 0.0,
                "sell_value": 0.0,
                "quantity_bought": 0.0,
                "quantity_sold": 0.0,
                "unmatched_sell_quantity": 0.0,
                "trade_count": 0,
                "first_trade_date": trade_date,
                "last_trade_date": trade_date,
            },
        )
        row["first_trade_date"] = min(str(row["first_trade_date"]), trade_date)
        row["last_trade_date"] = max(str(row["last_trade_date"]), trade_date)
        row["trade_count"] = int(row["trade_count"]) + 1
        return row

    for trade in result.trades:
        symbol = str(trade.symbol)
        action = str(trade.action).upper()
        price = float(trade.price)
        quantity = float(trade.quantity)
        row = symbol_stats(symbol, str(trade.date))
        lots.setdefault(symbol, [])
        if action == "BUY":
            row["buy_value"] += price * quantity
            row["quantity_bought"] += quantity
            lots[symbol].append({"quantity": quantity, "price": price})
        elif action == "SELL":
            row["sell_value"] += price * quantity
            row["quantity_sold"] += quantity
            remaining = quantity
            while remaining > 0 and lots[symbol]:
                lot = lots[symbol][0]
                matched = min(remaining, float(lot["quantity"]))
                row["realized_pnl"] += matched * (price - float(lot["price"]))
                row["realized_cost"] += matched * float(lot["price"])
                lot["quantity"] = float(lot["quantity"]) - matched
                remaining -= matched
                if float(lot["quantity"]) <= 0:
                    lots[symbol].pop(0)
            if remaining > 0:
                row["unmatched_sell_quantity"] += remaining

    output: list[dict[str, str]] = []
    for symbol, row in stats.items():
        open_quantity = sum(float(lot["quantity"]) for lot in lots.get(symbol, []))
        realized_cost = float(row.get("realized_cost", 0.0))
        realized_pnl = float(row.get("realized_pnl", 0.0))
        realized_return_pct = (realized_pnl / realized_cost * 100.0) if realized_cost > 0 else 0.0
        status = "LOSS" if realized_pnl < 0 else "GAIN" if realized_pnl > 0 else "FLAT"
        output.append(
            {
                "symbol": symbol,
                "realized_pnl": _format_optional_float(realized_pnl),
                "realized_return_pct": _format_optional_float(realized_return_pct),
                "buy_value": _format_optional_float(float(row.get("buy_value", 0.0))),
                "sell_value": _format_optional_float(float(row.get("sell_value", 0.0))),
                "quantity_bought": _format_optional_float(float(row.get("quantity_bought", 0.0))),
                "quantity_sold": _format_optional_float(float(row.get("quantity_sold", 0.0))),
                "open_quantity": _format_optional_float(open_quantity),
                "unmatched_sell_quantity": _format_optional_float(float(row.get("unmatched_sell_quantity", 0.0))),
                "trade_count": str(int(row.get("trade_count", 0))),
                "first_trade_date": str(row.get("first_trade_date", "")),
                "last_trade_date": str(row.get("last_trade_date", "")),
                "status": status,
            }
        )
    return sorted(output, key=lambda item: (float(item["realized_pnl"] or 0.0), item["symbol"]))


def analyze_monthly_decision_attribution(result: MonthlyBacktestResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for decision in result.decisions:
        weights = {
            str(symbol): float(weight)
            for symbol, weight in decision.target_weights.items()
            if float(weight) > 0
        }
        selected_symbols = list(weights.keys())
        target_exposure = sum(weights.values())
        cash_weight = max(0.0, 1.0 - target_exposure)
        weight_values = list(weights.values())
        rows.append(
            {
                "as_of_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "mode": decision.mode,
                "selected_preset": decision.selected_preset,
                "position_count": str(len(selected_symbols)),
                "selected_symbols": ";".join(selected_symbols),
                "target_exposure": _format_optional_float(target_exposure),
                "cash_weight": _format_optional_float(cash_weight),
                "max_position_weight": _format_optional_float(max(weight_values) if weight_values else 0.0),
                "min_position_weight": _format_optional_float(min(weight_values) if weight_values else 0.0),
                "target_weights": ";".join(
                    f"{symbol}:{_format_optional_float(weight)}" for symbol, weight in weights.items()
                ),
                "reason": decision.reason,
            }
        )
    return rows


def analyze_monthly_proxy_decision_diagnostics(
    result: MonthlyBacktestResult,
    *,
    symbol_candles: dict[str, list[Candle]],
    config: MonthlyRebalanceConfig,
    scenario: str = "",
    evidence_provider: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    monthly_rows = analyze_monthly_drawdown_attribution(result)
    decision_rows = analyze_monthly_decision_attribution(result)
    provider = evidence_provider or _monthly_train_decision_evidence
    rows: list[dict[str, str]] = []
    for decision, decision_row in zip(result.decisions, decision_rows):
        monthly_row = _monthly_attribution_for_decision(monthly_rows, decision.as_of_date)
        evidence = provider(symbol_candles, as_of_date=decision.as_of_date, config=config)
        diagnostics = _monthly_proxy_decision_diagnostic_tokens(decision, decision_row, monthly_row, evidence)
        if decision.mode == "market_beta_proxy":
            guard_evidence = _market_beta_proxy_reversal_guard_diagnostics(
                symbol_candles,
                signal_date=decision.signal_date,
                config=config,
                prior_breadth=_float_or_none(evidence.get("prior_breadth")),
            )
        else:
            guard_evidence = {
                "triggered": "false",
                "cap": "",
                "medium_return_pct": "",
                "short_return_pct": "",
                "medium_drawdown_pct": "",
                "reason": "not_market_beta_proxy",
            }
        rows.append(
            {
                "scenario": scenario,
                "as_of_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "month": str(monthly_row.get("month", "")),
                "month_return_pct": str(monthly_row.get("return_pct", "")),
                "month_status": str(monthly_row.get("status", "")),
                "month_equity_change": str(monthly_row.get("equity_change", "")),
                "mode": decision.mode,
                "reason": decision.reason,
                "target_exposure": str(decision_row.get("target_exposure", "")),
                "cash_weight": str(decision_row.get("cash_weight", "")),
                "position_count": str(decision_row.get("position_count", "")),
                "selected_symbols": str(decision_row.get("selected_symbols", "")),
                "prior_breadth": str(evidence.get("prior_breadth", "")),
                "fallback_breadth_threshold": str(evidence.get("fallback_breadth_threshold", "")),
                "market_beta_breadth_threshold": str(evidence.get("market_beta_breadth_threshold", "")),
                "trend_scale": str(evidence.get("trend_scale", "")),
                "volatility_scale": str(evidence.get("volatility_scale", "")),
                "liquidity_scale": str(evidence.get("liquidity_scale", "")),
                "exposure_scale": str(evidence.get("exposure_scale", "")),
                "direct_candidate_count": str(evidence.get("direct_candidate_count", "")),
                "eligible_direct_candidate_count": str(evidence.get("eligible_direct_candidate_count", "")),
                "best_direct_excess_return_pct": str(evidence.get("best_direct_excess_return_pct", "")),
                "best_direct_train_positive_ratio": str(evidence.get("best_direct_train_positive_ratio", "")),
                "direct_candidate_rejection_reasons": str(evidence.get("direct_candidate_rejection_reasons", "")),
                "proxy_reversal_guard_triggered": guard_evidence["triggered"],
                "proxy_reversal_guard_cap": guard_evidence["cap"],
                "proxy_reversal_guard_medium_return_pct": guard_evidence["medium_return_pct"],
                "proxy_reversal_guard_short_return_pct": guard_evidence["short_return_pct"],
                "proxy_reversal_guard_medium_drawdown_pct": guard_evidence["medium_drawdown_pct"],
                "proxy_reversal_guard_reason": guard_evidence["reason"],
                "diagnostic": ";".join(diagnostics) if diagnostics else "no_proxy_issue_detected",
                "recommended_next_action": _monthly_proxy_decision_recommended_action(diagnostics),
            }
        )
    return rows


def _monthly_attribution_for_decision(
    monthly_rows: list[dict[str, str]],
    as_of_date: str,
) -> dict[str, str]:
    month = str(as_of_date)[:7]
    same_month = [row for row in monthly_rows if str(row.get("month", "")) == month]
    if same_month:
        return same_month[-1]
    prior = [row for row in monthly_rows if str(row.get("end_date", "")) <= str(as_of_date)]
    return prior[-1] if prior else {}


def _monthly_proxy_decision_diagnostic_tokens(
    decision: MonthlyDecision,
    decision_row: dict[str, str],
    monthly_row: dict[str, str],
    evidence: dict[str, Any],
) -> list[str]:
    diagnostics: list[str] = []
    target_exposure = _float_or_none(decision_row.get("target_exposure")) or 0.0
    month_return = _float_or_none(monthly_row.get("return_pct"))
    prior_breadth = _float_or_none(evidence.get("prior_breadth"))
    fallback_threshold = _float_or_none(evidence.get("fallback_breadth_threshold"))
    beta_threshold = _float_or_none(evidence.get("market_beta_breadth_threshold"))
    eligible_count = _safe_int(evidence.get("eligible_direct_candidate_count"), default=0)

    if decision.mode == "market_beta_proxy":
        diagnostics.append("market_beta_proxy")
        if target_exposure >= 0.75:
            diagnostics.append("high_exposure_proxy")
        if target_exposure >= 0.75 and month_return is not None and month_return < 0:
            diagnostics.append("high_exposure_proxy_loss")
        if month_return is not None and month_return > 0:
            diagnostics.append("proxy_gain_participation")
    if "drawdown_guard" in decision.reason:
        diagnostics.append("already_scaled_by_drawdown_guard")
        if month_return is not None and month_return > 0 and target_exposure < 0.8:
            if decision.mode == "alpha":
                diagnostics.append("scaled_alpha_recovery")
            elif decision.mode == "market_beta_proxy":
                diagnostics.append("scaled_proxy_recovery")
    if prior_breadth is not None and fallback_threshold is not None and prior_breadth >= fallback_threshold:
        diagnostics.append("strong_breadth")
    elif prior_breadth is not None and beta_threshold is not None and prior_breadth >= beta_threshold:
        diagnostics.append("neutral_breadth")
    elif prior_breadth is not None:
        diagnostics.append("weak_breadth")
    if eligible_count <= 0:
        diagnostics.append("no_eligible_direct_candidate")
    return diagnostics


def _monthly_proxy_decision_recommended_action(diagnostics: list[str]) -> str:
    diagnostic_set = set(diagnostics)
    if "high_exposure_proxy_loss" in diagnostic_set:
        return "test_conditional_proxy_entry_guard"
    if (
        "scaled_alpha_recovery" in diagnostic_set
        or "scaled_proxy_recovery" in diagnostic_set
        or (
            "proxy_gain_participation" in diagnostic_set
            and "already_scaled_by_drawdown_guard" in diagnostic_set
        )
    ):
        return "preserve_scaled_recovery_participation"
    if "no_eligible_direct_candidate" in diagnostic_set:
        return "preserve_train_gate_and_improve_alpha_candidates"
    return "review_proxy_context"


def _market_beta_proxy_reversal_guard_diagnostics(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    config: MonthlyRebalanceConfig,
    prior_breadth: float | None,
) -> dict[str, str]:
    current_cap = max(0.0, config.market_beta_proxy_max_exposure)
    if prior_breadth is not None and prior_breadth < config.fallback_breadth_threshold:
        current_cap = min(current_cap, max(0.0, config.market_beta_proxy_neutral_breadth_max_exposure))

    guard_cap = max(0.0, config.market_beta_proxy_reversal_guard_max_exposure)
    medium_days = int(config.market_beta_proxy_reversal_guard_medium_lookback_days)
    if medium_days <= 0 or guard_cap >= current_cap:
        return {
            "triggered": "false",
            "cap": _format_optional_float(current_cap),
            "medium_return_pct": "",
            "short_return_pct": "",
            "medium_drawdown_pct": "",
            "reason": "proxy_exposure_capped",
        }

    universe_candles = filter_symbol_candles_by_universe(
        symbol_candles,
        config.point_in_time_universe,
        signal_date=signal_date,
        min_history_days=config.point_in_time_min_history_days,
    )
    point_in_time_candles = select_point_in_time_universe(
        universe_candles,
        signal_date=signal_date,
        min_history_days=config.point_in_time_min_history_days,
        min_reference_price=config.point_in_time_min_reference_price,
        max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
        trailing_return_days=config.point_in_time_trailing_return_days,
    )
    decision_candles = (
        select_liquid_universe(
            point_in_time_candles,
            signal_date=signal_date,
            top_n=config.point_in_time_liquidity_top_n,
            window_days=config.point_in_time_liquidity_window_days,
        )
        if config.point_in_time_liquidity_top_n > 0
        else point_in_time_candles
    )
    proxy_symbols = rank_symbols_by_average_trading_value(
        decision_candles,
        signal_date=signal_date,
        window_days=max(1, config.point_in_time_liquidity_window_days),
    )[: max(0, config.market_beta_proxy_size)]
    medium_return = _average_symbol_return_pct(
        decision_candles,
        proxy_symbols,
        signal_date=signal_date,
        lookback_days=medium_days,
    )
    medium_drawdown = _proxy_basket_max_drawdown_pct(
        decision_candles,
        proxy_symbols,
        signal_date=signal_date,
        lookback_days=medium_days,
    )
    short_return: float | None = None
    short_days = int(config.market_beta_proxy_reversal_guard_short_lookback_days)
    if short_days > 0:
        short_return = _average_symbol_return_pct(
            decision_candles,
            proxy_symbols,
            signal_date=signal_date,
            lookback_days=short_days,
        )

    reason = "proxy_exposure_capped"
    triggered = False
    if medium_return is not None and medium_return >= config.market_beta_proxy_reversal_guard_medium_return_pct:
        extreme_trigger = config.market_beta_proxy_reversal_guard_extreme_return_pct
        extreme_overheat = extreme_trigger > 0 and medium_return >= extreme_trigger
        short_allows_cap = short_days <= 0 or (
            short_return is not None and short_return <= config.market_beta_proxy_reversal_guard_short_max_return_pct
        )
        drawdown_trigger = config.market_beta_proxy_reversal_guard_medium_drawdown_pct
        drawdown_allows_cap = (
            drawdown_trigger < 0
            and medium_drawdown is not None
            and medium_drawdown <= drawdown_trigger
        )
        recovery_exit_trigger = config.market_beta_proxy_reversal_guard_recovery_exit_short_return_pct
        recovery_exit = (
            not extreme_overheat
            and drawdown_allows_cap
            and recovery_exit_trigger < 0
            and short_return is not None
            and short_return <= recovery_exit_trigger
        )
        if recovery_exit:
            reason = "proxy_reversal_guard_recovery_exit"
        elif extreme_overheat or short_allows_cap or drawdown_allows_cap:
            triggered = True
            current_cap = min(current_cap, guard_cap)
            reason = "proxy_reversal_guard_capped"

    return {
        "triggered": "true" if triggered else "false",
        "cap": _format_optional_float(current_cap),
        "medium_return_pct": _format_optional_float(medium_return),
        "short_return_pct": _format_optional_float(short_return),
        "medium_drawdown_pct": _format_optional_float(medium_drawdown),
        "reason": reason,
    }


def analyze_monthly_recovery_attribution(
    result: MonthlyBacktestResult,
    *,
    scenario: str = "",
) -> list[dict[str, str]]:
    monthly_rows = analyze_monthly_drawdown_attribution(result)
    if not monthly_rows:
        return []
    decision_rows = analyze_monthly_decision_attribution(result)
    symbol_rows = analyze_symbol_realized_pnl_attribution(result)

    worst_month = min(monthly_rows, key=lambda row: _float_or_none(row.get("return_pct")) or 0.0)
    best_month = max(monthly_rows, key=lambda row: _float_or_none(row.get("return_pct")) or 0.0)
    worst_decision = _decision_attribution_for_month(decision_rows, worst_month)
    best_decision = _decision_attribution_for_month(decision_rows, best_month)
    loss_symbols = [
        row for row in symbol_rows
        if (_float_or_none(row.get("realized_pnl")) or 0.0) < 0
    ]
    gain_symbols = [
        row for row in symbol_rows
        if (_float_or_none(row.get("realized_pnl")) or 0.0) > 0
    ]
    top_loss_rows = sorted(loss_symbols, key=lambda row: _float_or_none(row.get("realized_pnl")) or 0.0)[:3]
    top_loss_symbol = top_loss_rows[0] if top_loss_rows else {}

    exposures = [
        value for value in (_float_or_none(row.get("target_exposure")) for row in decision_rows)
        if value is not None
    ]
    cash_weights = [
        value for value in (_float_or_none(row.get("cash_weight")) for row in decision_rows)
        if value is not None
    ]
    loss_month_count = sum(1 for row in monthly_rows if str(row.get("status", "")) == "LOSS")
    gain_month_count = sum(1 for row in monthly_rows if str(row.get("status", "")) == "GAIN")
    positive_month_ratio = gain_month_count / len(monthly_rows) if monthly_rows else 0.0
    worst_index = monthly_rows.index(worst_month)
    post_worst_rows = monthly_rows[worst_index + 1 :]
    post_worst_total_return = None
    if post_worst_rows:
        base_equity = _float_or_none(worst_month.get("end_equity"))
        final_equity = _float_or_none(monthly_rows[-1].get("end_equity"))
        if base_equity and final_equity is not None:
            post_worst_total_return = (final_equity / base_equity - 1.0) * 100.0

    worst_return = _float_or_none(worst_month.get("return_pct"))
    best_cash = _float_or_none(best_decision.get("cash_weight"))
    worst_exposure = _float_or_none(worst_decision.get("target_exposure"))
    diagnostics: list[str] = []
    if result.excess_return_pct < 0 and result.total_return_pct > 0:
        diagnostics.append("benchmark_recovered_more")
    elif result.excess_return_pct < 0:
        diagnostics.append("negative_excess")
    if worst_exposure is not None and worst_exposure >= 0.75 and (worst_return or 0.0) < 0:
        diagnostics.append("high_exposure_worst_month")
    if best_cash is not None and best_cash >= 0.25:
        diagnostics.append("cash_drag_best_month")
    if (
        post_worst_total_return is not None
        and worst_return is not None
        and worst_return < 0
        and post_worst_total_return < abs(worst_return)
    ):
        diagnostics.append("insufficient_post_worst_recovery")
    if loss_month_count >= gain_month_count:
        diagnostics.append("loss_month_pressure")
    if top_loss_rows:
        diagnostics.append("symbol_loss_concentration")

    failure_mode = "benchmark_outpaced_recovery" if result.total_return_pct > 0 and result.excess_return_pct < 0 else ""
    if not failure_mode and result.excess_return_pct < 0:
        failure_mode = "absolute_loss_and_benchmark_drag" if result.total_return_pct < 0 else "negative_excess"

    row = {
        "scenario": scenario,
        "start": result.dates[0] if result.dates else "",
        "end": result.dates[-1] if result.dates else "",
        "total_return_pct": _format_optional_float(result.total_return_pct),
        "buy_hold_return_pct": _format_optional_float(result.buy_hold_return_pct),
        "excess_return_pct": _format_optional_float(result.excess_return_pct),
        "max_drawdown_pct": _format_optional_float(result.max_drawdown_pct),
        "month_count": str(len(monthly_rows)),
        "loss_month_count": str(loss_month_count),
        "gain_month_count": str(gain_month_count),
        "positive_month_ratio": _format_optional_float(positive_month_ratio),
        "average_target_exposure": _format_optional_float(sum(exposures) / len(exposures) if exposures else 0.0),
        "average_cash_weight": _format_optional_float(sum(cash_weights) / len(cash_weights) if cash_weights else 0.0),
        "worst_month": str(worst_month.get("month", "")),
        "worst_month_return_pct": str(worst_month.get("return_pct", "")),
        "worst_month_equity_change": str(worst_month.get("equity_change", "")),
        "worst_month_target_exposure": str(worst_decision.get("target_exposure", "")),
        "worst_month_cash_weight": str(worst_decision.get("cash_weight", "")),
        "worst_month_mode": str(worst_decision.get("mode", "")),
        "worst_month_reason": str(worst_decision.get("reason", "")),
        "best_month": str(best_month.get("month", "")),
        "best_month_return_pct": str(best_month.get("return_pct", "")),
        "best_month_target_exposure": str(best_decision.get("target_exposure", "")),
        "best_month_cash_weight": str(best_decision.get("cash_weight", "")),
        "post_worst_month_count": str(len(post_worst_rows)),
        "post_worst_total_return_pct": _format_optional_float(post_worst_total_return),
        "top_loss_symbol": str(top_loss_symbol.get("symbol", "")),
        "top_loss_symbol_realized_pnl": str(top_loss_symbol.get("realized_pnl", "")),
        "top_loss_symbols": ";".join(
            f"{row.get('symbol', '')}:{row.get('realized_pnl', '')}" for row in top_loss_rows
        ),
        "loss_symbol_count": str(len(loss_symbols)),
        "gain_symbol_count": str(len(gain_symbols)),
        "failure_mode": failure_mode,
        "diagnostic": ";".join(diagnostics) if diagnostics else "no_recovery_issue_detected",
    }
    return [row]


def _decision_attribution_for_month(
    decision_rows: list[dict[str, str]],
    monthly_row: dict[str, str],
) -> dict[str, str]:
    month = str(monthly_row.get("month", ""))
    end_date = str(monthly_row.get("end_date", ""))
    same_month = [row for row in decision_rows if str(row.get("as_of_date", ""))[:7] == month]
    if same_month:
        return sorted(same_month, key=lambda row: str(row.get("as_of_date", "")))[-1]
    prior = [row for row in decision_rows if str(row.get("as_of_date", "")) <= end_date]
    if prior:
        return sorted(prior, key=lambda row: str(row.get("as_of_date", "")))[-1]
    return {}


def save_monthly_decision_attribution(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_DECISION_ATTRIBUTION_COLUMNS)


def save_monthly_proxy_decision_diagnostics(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_PROXY_DECISION_DIAGNOSTIC_COLUMNS)


def save_monthly_proxy_decision_context_summary(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_PROXY_DECISION_CONTEXT_SUMMARY_COLUMNS)


def save_monthly_guarded_loss_position_pressure(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_GUARDED_LOSS_POSITION_PRESSURE_COLUMNS)


def save_monthly_position_loss_control_diagnostics(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_POSITION_LOSS_CONTROL_COLUMNS)


def analyze_monthly_guarded_loss_position_pressure(
    *,
    proxy_rows: list[dict[str, Any]],
    symbol_rows: list[dict[str, Any]],
    path_rows: list[dict[str, Any]],
    scenario: str = "",
    top_symbol_count: int = 5,
) -> list[dict[str, Any]]:
    loss_symbol_rows = [
        row
        for row in sorted(symbol_rows, key=lambda row: _float_or_none(row.get("realized_pnl")) or 0.0)
        if (_float_or_none(row.get("realized_pnl")) or 0.0) < 0
    ]
    rows: list[dict[str, Any]] = []
    for proxy in proxy_rows:
        if scenario and str(proxy.get("scenario", "")).strip() not in {"", scenario}:
            continue
        if str(proxy.get("mode", "")).strip() != "market_beta_proxy":
            continue
        if not _parse_bool(proxy.get("proxy_reversal_guard_triggered", False)):
            continue
        month_return = _float_or_none(proxy.get("month_return_pct"))
        if month_return is None or month_return >= 0:
            continue

        month = str(proxy.get("month", "")).strip()
        selected_symbols = _split_semicolon_values(str(proxy.get("selected_symbols", "")))
        selected_symbol_set = set(selected_symbols)
        selected_loss_candidates = [
            row for row in loss_symbol_rows if str(row.get("symbol", "")).strip() in selected_symbol_set
        ]
        selected_loss_rows = selected_loss_candidates[: max(1, top_symbol_count)]
        month_exit_loss_candidates = [
            row for row in loss_symbol_rows if str(row.get("last_trade_date", "")).startswith(month)
        ]
        month_exit_loss_rows = month_exit_loss_candidates[: max(1, top_symbol_count)]
        carryover_exit_rows = [
            row for row in month_exit_loss_rows if str(row.get("symbol", "")).strip() not in selected_symbol_set
        ]
        month_path_rows = [
            row for row in path_rows if str(row.get("date", "")).startswith(month)
        ]
        worst_path = min(
            month_path_rows,
            key=lambda row: _float_or_none(row.get("drawdown_pct")) or 0.0,
            default={},
        )
        diagnostics = ["guarded_loss_month"]
        if selected_loss_candidates:
            diagnostics.append("selected_symbol_losses")
        if month_exit_loss_candidates:
            diagnostics.append("month_exit_losses")
        if carryover_exit_rows:
            diagnostics.append("carryover_exit_losses")
        if month_path_rows:
            diagnostics.append("month_path_pressure")
        focus = "review_guarded_loss_position_pressure"
        if selected_loss_candidates and carryover_exit_rows:
            focus = "analyze_position_level_loss_controls_without_broad_stop"
        elif carryover_exit_rows:
            focus = "analyze_carryover_exit_loss_pressure"
        elif selected_loss_candidates:
            focus = "analyze_selected_basket_loss_pressure"

        rows.append(
            {
                "scenario": scenario or str(proxy.get("scenario", "")).strip(),
                "month": month,
                "as_of_date": proxy.get("as_of_date", ""),
                "signal_date": proxy.get("signal_date", ""),
                "month_return_pct": proxy.get("month_return_pct", ""),
                "target_exposure": proxy.get("target_exposure", ""),
                "cash_weight": proxy.get("cash_weight", ""),
                "guard_reason": proxy.get("proxy_reversal_guard_reason", ""),
                "guard_medium_return_pct": proxy.get("proxy_reversal_guard_medium_return_pct", ""),
                "guard_short_return_pct": proxy.get("proxy_reversal_guard_short_return_pct", ""),
                "guard_medium_drawdown_pct": proxy.get("proxy_reversal_guard_medium_drawdown_pct", ""),
                "selected_symbol_count": str(len(selected_symbols)),
                "selected_loss_symbol_count": str(len(selected_loss_candidates)),
                "selected_loss_symbols": _format_loss_symbol_list(selected_loss_rows),
                "selected_loss_windows": _format_loss_symbol_windows(selected_loss_rows),
                "selected_loss_realized_pnl": _format_optional_float(
                    _sum_numeric(row.get("realized_pnl") for row in selected_loss_rows)
                ),
                "month_exit_loss_symbol_count": str(len(month_exit_loss_candidates)),
                "month_exit_loss_symbols": _format_loss_symbol_list(month_exit_loss_rows),
                "month_exit_loss_windows": _format_loss_symbol_windows(month_exit_loss_rows),
                "month_exit_loss_realized_pnl": _format_optional_float(
                    _sum_numeric(row.get("realized_pnl") for row in month_exit_loss_rows)
                ),
                "carryover_exit_loss_symbols": _format_loss_symbol_list(carryover_exit_rows),
                "carryover_exit_loss_windows": _format_loss_symbol_windows(carryover_exit_rows),
                "worst_drawdown_date": worst_path.get("date", ""),
                "worst_drawdown_pct": _format_optional_float(_float_or_none(worst_path.get("drawdown_pct"))),
                "average_month_path_exposure": _format_optional_float(
                    _average_numeric(row.get("exposure") for row in month_path_rows)
                ),
                "max_month_path_exposure": _format_optional_float(
                    _max_numeric(row.get("exposure") for row in month_path_rows)
                ),
                "diagnostic": ";".join(diagnostics),
                "recommended_candidate_focus": focus,
                "paper_only": "true",
                "risk_note": "Diagnostic summary only; do not create or transmit live orders from this report.",
            }
        )
    return rows


def analyze_monthly_position_loss_control_diagnostics(
    *,
    pressure_rows: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
    loss_threshold_pct: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pressure in pressure_rows:
        selected_losses = _parse_symbol_loss_values(str(pressure.get("selected_loss_symbols", "")))
        carryover_losses = _parse_symbol_loss_values(str(pressure.get("carryover_exit_loss_symbols", "")))
        selected_windows = _parse_symbol_windows(str(pressure.get("selected_loss_windows", "")))
        carryover_windows = _parse_symbol_windows(str(pressure.get("carryover_exit_loss_windows", "")))
        symbols = list(selected_losses)
        symbols.extend(symbol for symbol in carryover_losses if symbol not in selected_losses)
        for symbol in symbols:
            selected = symbol in selected_losses
            carryover = symbol in carryover_losses
            if selected and carryover:
                pressure_source = "selected_and_carryover_exit_loss"
            elif selected:
                pressure_source = "selected_loss"
            else:
                pressure_source = "carryover_exit_loss"
            loss_value = selected_losses.get(symbol) if selected else carryover_losses.get(symbol)
            window = selected_windows.get(symbol) if selected else carryover_windows.get(symbol)
            rows.append(
                _position_loss_control_row(
                    pressure,
                    symbol=symbol,
                    pressure_source=pressure_source,
                    loss_realized_pnl=loss_value,
                    candles=symbol_candles.get(symbol, []),
                    loss_threshold_pct=loss_threshold_pct,
                    holding_window=window,
                )
            )
    return rows


def _parse_symbol_loss_values(value: str) -> dict[str, float | None]:
    parsed: dict[str, float | None] = {}
    for part in _split_semicolon_values(value):
        symbol, _, raw_value = part.partition(":")
        symbol = symbol.strip()
        if symbol:
            parsed[symbol] = _float_or_none(raw_value) if raw_value else None
    return parsed


def _format_loss_symbol_windows(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows:
        symbol = str(row.get("symbol", "")).strip()
        first_trade_date = str(row.get("first_trade_date", "")).strip()
        last_trade_date = str(row.get("last_trade_date", "")).strip()
        if symbol and (first_trade_date or last_trade_date):
            parts.append(f"{symbol}:{first_trade_date}..{last_trade_date}")
    return ";".join(parts)


def _parse_symbol_windows(value: str) -> dict[str, tuple[str, str]]:
    windows: dict[str, tuple[str, str]] = {}
    for part in _split_semicolon_values(value):
        symbol, _, raw_window = part.partition(":")
        start, _, end = raw_window.partition("..")
        symbol = symbol.strip()
        if symbol:
            windows[symbol] = (start.strip(), end.strip())
    return windows


def _position_loss_control_row(
    pressure: dict[str, Any],
    *,
    symbol: str,
    pressure_source: str,
    loss_realized_pnl: float | None,
    candles: list[Candle],
    loss_threshold_pct: float,
    holding_window: tuple[str, str] | None = None,
) -> dict[str, str]:
    month = str(pressure.get("month", "")).strip()
    pressure_as_of_date = str(pressure.get("as_of_date", "")).strip()
    worst_drawdown_date = str(pressure.get("worst_drawdown_date", "")).strip()
    window_start, window_end = holding_window or ("", "")
    as_of_date = window_start or pressure_as_of_date
    end_date = window_end or worst_drawdown_date
    explicit_window = bool(window_start or window_end)
    window = [
        candle
        for candle in sorted(candles, key=lambda candle: candle.date)
        if (not as_of_date or candle.date >= as_of_date)
        and (not end_date or candle.date <= end_date)
        and (explicit_window or not month or candle.date.startswith(month))
    ]
    diagnostics: list[str] = []
    if explicit_window:
        diagnostics.append("explicit_holding_window")
    if not window:
        diagnostics.append("missing_price_window")
        return {
            "scenario": str(pressure.get("scenario", "")).strip(),
            "month": month,
            "symbol": symbol,
            "pressure_source": pressure_source,
            "loss_realized_pnl": _format_optional_float(loss_realized_pnl),
            "as_of_date": as_of_date,
            "worst_drawdown_date": worst_drawdown_date,
            "loss_threshold_pct": _format_optional_float(loss_threshold_pct),
            "would_trigger": "false",
            "triggered_before_worst_drawdown": "false",
            "recommended_candidate_focus": "insufficient_price_history_for_position_control",
            "diagnostic": ";".join(diagnostics),
            "paper_only": "true",
            "risk_note": "Diagnostic summary only; do not create or transmit live orders from this report.",
        }

    entry = window[0]
    entry_close = entry.close
    min_low_candle = min(window, key=lambda candle: candle.low)
    max_adverse_return_pct = ((min_low_candle.low / entry_close) - 1.0) * 100 if entry_close else None
    stop_price = entry_close * (1.0 - max(0.0, loss_threshold_pct) / 100.0)
    trigger = next((candle for candle in window if candle.low <= stop_price), None)
    close_candle = window[-1]
    close_return_pct = ((close_candle.close / entry_close) - 1.0) * 100 if entry_close else None
    if trigger:
        diagnostics.append("position_threshold_hit")
    else:
        diagnostics.append("position_threshold_not_hit")
    if trigger and worst_drawdown_date and trigger.date <= worst_drawdown_date:
        diagnostics.append("trigger_before_worst_drawdown")
    recommended_focus = (
        "paper_position_stop_candidate_before_worst_drawdown"
        if trigger and (not worst_drawdown_date or trigger.date <= worst_drawdown_date)
        else "review_position_loss_without_stop_trigger"
    )
    return {
        "scenario": str(pressure.get("scenario", "")).strip(),
        "month": month,
        "symbol": symbol,
        "pressure_source": pressure_source,
        "loss_realized_pnl": _format_optional_float(loss_realized_pnl),
        "as_of_date": as_of_date,
        "worst_drawdown_date": worst_drawdown_date,
        "entry_date": entry.date,
        "entry_close": _format_optional_float(entry_close),
        "min_low_date": min_low_candle.date,
        "min_low": _format_optional_float(min_low_candle.low),
        "max_adverse_return_pct": _format_optional_float(max_adverse_return_pct),
        "loss_threshold_pct": _format_optional_float(loss_threshold_pct),
        "would_trigger": "true" if trigger else "false",
        "stop_trigger_date": trigger.date if trigger else "",
        "triggered_before_worst_drawdown": (
            "true" if trigger and (not worst_drawdown_date or trigger.date <= worst_drawdown_date) else "false"
        ),
        "close_return_to_worst_drawdown_pct": _format_optional_float(close_return_pct),
        "recommended_candidate_focus": recommended_focus,
        "diagnostic": ";".join(diagnostics),
        "paper_only": "true",
        "risk_note": "Diagnostic summary only; do not create or transmit live orders from this report.",
    }


def analyze_monthly_proxy_decision_context_summary(proxy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for proxy in proxy_rows:
        if str(proxy.get("mode", "")).strip() != "market_beta_proxy":
            continue
        diagnostic_tokens = set(_split_semicolon_values(str(proxy.get("diagnostic", ""))))
        key = (
            str(proxy.get("scenario", "")).strip(),
            _proxy_breadth_context(diagnostic_tokens),
            _proxy_exposure_bucket(proxy, diagnostic_tokens),
        )
        groups.setdefault(key, []).append(proxy)

    rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        scenario, breadth_context, exposure_bucket = key
        context_rows = groups[key]
        month_returns = [_float_or_none(row.get("month_return_pct")) for row in context_rows]
        target_exposures = [_float_or_none(row.get("target_exposure")) for row in context_rows]
        cash_weights = [_float_or_none(row.get("cash_weight")) for row in context_rows]
        prior_breadths = [
            value for value in (_float_or_none(row.get("prior_breadth")) for row in context_rows)
            if value is not None
        ]
        loss_count = sum(1 for value in month_returns if value is not None and value < 0)
        gain_count = sum(1 for value in month_returns if value is not None and value > 0)
        high_exposure_loss_count = sum(
            1
            for row in context_rows
            if "high_exposure_proxy_loss" in _split_semicolon_values(str(row.get("diagnostic", "")))
        )
        gain_participation_count = sum(
            1
            for row in context_rows
            if "proxy_gain_participation" in _split_semicolon_values(str(row.get("diagnostic", "")))
        )
        guard_triggered_count = sum(
            1 for row in context_rows if _parse_bool(row.get("proxy_reversal_guard_triggered", False))
        )
        months = sorted({str(row.get("month", "")).strip() for row in context_rows if str(row.get("month", "")).strip()})
        rows.append(
            {
                "scenario": scenario,
                "breadth_context": breadth_context,
                "exposure_bucket": exposure_bucket,
                "proxy_month_count": str(len(context_rows)),
                "loss_month_count": str(loss_count),
                "gain_month_count": str(gain_count),
                "high_exposure_loss_count": str(high_exposure_loss_count),
                "gain_participation_count": str(gain_participation_count),
                "guard_triggered_count": str(guard_triggered_count),
                "avg_month_return_pct": _format_optional_float(_average_numeric(month_returns)),
                "total_month_return_pct": _format_optional_float(_sum_numeric(month_returns)),
                "avg_target_exposure": _format_optional_float(_average_numeric(target_exposures)),
                "avg_cash_weight": _format_optional_float(_average_numeric(cash_weights)),
                "min_prior_breadth": _format_optional_float(min(prior_breadths) if prior_breadths else None),
                "max_prior_breadth": _format_optional_float(max(prior_breadths) if prior_breadths else None),
                "months": ";".join(months),
                "recommended_candidate_focus": _proxy_context_recommended_focus(
                    breadth_context=breadth_context,
                    high_exposure_loss_count=high_exposure_loss_count,
                    gain_participation_count=gain_participation_count,
                    guard_triggered_count=guard_triggered_count,
                    loss_count=loss_count,
                ),
                "diagnostic": _proxy_context_diagnostic(
                    high_exposure_loss_count=high_exposure_loss_count,
                    gain_participation_count=gain_participation_count,
                    guard_triggered_count=guard_triggered_count,
                    loss_count=loss_count,
                    gain_count=gain_count,
                ),
                "paper_only": "true",
                "risk_note": "Diagnostic only; use for paper candidate design and never for live order transmission.",
            }
        )
    return rows


def _proxy_breadth_context(diagnostic_tokens: set[str]) -> str:
    if "neutral_breadth" in diagnostic_tokens:
        return "neutral_breadth"
    if "strong_breadth" in diagnostic_tokens:
        return "strong_breadth"
    if "weak_breadth" in diagnostic_tokens:
        return "weak_breadth"
    return "unknown_breadth"


def _proxy_exposure_bucket(proxy: dict[str, Any], diagnostic_tokens: set[str]) -> str:
    target_exposure = _float_or_none(proxy.get("target_exposure"))
    if "high_exposure_proxy" in diagnostic_tokens or (target_exposure is not None and target_exposure >= 0.75):
        return "high_exposure"
    if _parse_bool(proxy.get("proxy_reversal_guard_triggered", False)):
        return "guarded_exposure"
    if target_exposure is not None and target_exposure < 0.75:
        return "scaled_exposure"
    return "uncategorized_exposure"


def _proxy_context_recommended_focus(
    *,
    breadth_context: str,
    high_exposure_loss_count: int,
    gain_participation_count: int,
    guard_triggered_count: int,
    loss_count: int,
) -> str:
    if breadth_context == "neutral_breadth" and high_exposure_loss_count > 0:
        return "test_neutral_breadth_loss_discriminator"
    if breadth_context == "strong_breadth" and gain_participation_count > 0 and loss_count == 0:
        return "preserve_strong_breadth_recovery"
    if breadth_context == "strong_breadth" and guard_triggered_count > 0 and loss_count > 0:
        return "analyze_guarded_loss_position_pressure"
    if guard_triggered_count > 0 and gain_participation_count > 0:
        return "inspect_guard_recovery_drag"
    if high_exposure_loss_count > 0:
        return "tighten_loss_discriminator_without_broad_cash_drag"
    return "review_proxy_context"


def _proxy_context_diagnostic(
    *,
    high_exposure_loss_count: int,
    gain_participation_count: int,
    guard_triggered_count: int,
    loss_count: int,
    gain_count: int,
) -> str:
    diagnostics: list[str] = []
    if high_exposure_loss_count:
        diagnostics.append("high_exposure_loss_context")
    if gain_participation_count:
        diagnostics.append("gain_participation_context")
    if guard_triggered_count:
        diagnostics.append("guard_triggered_context")
    if guard_triggered_count and loss_count:
        diagnostics.append("guarded_loss_residual")
    if loss_count and gain_count:
        diagnostics.append("mixed_return_context")
    elif loss_count:
        diagnostics.append("loss_only_context")
    elif gain_count:
        diagnostics.append("gain_only_context")
    return ";".join(diagnostics) if diagnostics else "review_proxy_context"


def analyze_monthly_proxy_guard_outcomes(proxy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for proxy in proxy_rows:
        if str(proxy.get("mode", "")).strip() != "market_beta_proxy":
            continue
        diagnostic = str(proxy.get("diagnostic", ""))
        month_return = _float_or_none(proxy.get("month_return_pct"))
        guard_triggered = _parse_bool(proxy.get("proxy_reversal_guard_triggered", False))
        loss_month = month_return is not None and month_return < 0
        gain_month = month_return is not None and month_return > 0
        high_exposure_loss = "high_exposure_proxy_loss" in diagnostic
        gain_participation = "proxy_gain_participation" in diagnostic
        guard_outcome, design_hint = _monthly_proxy_guard_outcome_label(
            guard_triggered=guard_triggered,
            loss_month=loss_month,
            gain_month=gain_month,
            high_exposure_loss=high_exposure_loss,
            gain_participation=gain_participation,
        )
        rows.append(
            {
                "scenario": proxy.get("scenario", ""),
                "as_of_date": proxy.get("as_of_date", ""),
                "signal_date": proxy.get("signal_date", ""),
                "month": proxy.get("month", ""),
                "mode": proxy.get("mode", ""),
                "reason": proxy.get("reason", ""),
                "target_exposure": proxy.get("target_exposure", ""),
                "cash_weight": proxy.get("cash_weight", ""),
                "month_return_pct": proxy.get("month_return_pct", ""),
                "month_status": proxy.get("month_status", ""),
                "guard_triggered": str(guard_triggered).lower(),
                "guard_cap": proxy.get("proxy_reversal_guard_cap", ""),
                "guard_medium_return_pct": proxy.get("proxy_reversal_guard_medium_return_pct", ""),
                "guard_short_return_pct": proxy.get("proxy_reversal_guard_short_return_pct", ""),
                "guard_medium_drawdown_pct": proxy.get("proxy_reversal_guard_medium_drawdown_pct", ""),
                "guard_reason": proxy.get("proxy_reversal_guard_reason", ""),
                "loss_month": str(loss_month).lower(),
                "gain_month": str(gain_month).lower(),
                "high_exposure_proxy_loss": str(high_exposure_loss).lower(),
                "proxy_gain_participation": str(gain_participation).lower(),
                "guard_outcome": guard_outcome,
                "candidate_design_hint": design_hint,
                "original_diagnostic": diagnostic,
                "original_recommended_next_action": proxy.get("recommended_next_action", ""),
                "paper_only": "true",
                "risk_note": "Diagnostic only; use for paper candidate design and never for live order transmission.",
            }
        )
    return rows


def _monthly_proxy_guard_outcome_label(
    *,
    guard_triggered: bool,
    loss_month: bool,
    gain_month: bool,
    high_exposure_loss: bool,
    gain_participation: bool,
) -> tuple[str, str]:
    if guard_triggered and gain_month:
        return "profitable_continuation_capped", "add_continuation_discriminator_before_capping"
    if guard_triggered and loss_month:
        return "loss_cap_aligned", "preserve_loss_cap_condition"
    if not guard_triggered and high_exposure_loss:
        return "missed_high_exposure_loss", "tighten_loss_discriminator_without_broad_cash_drag"
    if not guard_triggered and gain_participation:
        return "gain_preserved", "preserve_uncapped_gain_months"
    if loss_month:
        return "uncapped_loss", "inspect_loss_context_before_tuning_guard"
    return "review_proxy_context", "review_before_candidate_change"


def analyze_monthly_proxy_guard_recovery_exits(
    proxy_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    *,
    scenario: str = "",
    candidate_label: str = "candidate",
) -> list[dict[str, Any]]:
    comparisons_by_month = {
        str(row.get("month", "")): row for row in comparison_rows if str(row.get("month", ""))
    }
    market_proxy_rows = [
        row
        for row in proxy_rows
        if str(row.get("mode", "")).strip() == "market_beta_proxy" and str(row.get("month", ""))
    ]
    market_proxy_rows.sort(key=lambda row: str(row.get("month", "")))

    rows: list[dict[str, Any]] = []
    for index, loss_proxy in enumerate(market_proxy_rows[:-1]):
        loss_month_return = _float_or_none(loss_proxy.get("month_return_pct"))
        loss_guard_triggered = _parse_bool(loss_proxy.get("proxy_reversal_guard_triggered", False))
        if not loss_guard_triggered or loss_month_return is None or loss_month_return >= 0:
            continue

        recovery_proxy = market_proxy_rows[index + 1]
        recovery_month_return = _float_or_none(recovery_proxy.get("month_return_pct"))
        loss_comparison = comparisons_by_month.get(str(loss_proxy.get("month", "")), {})
        recovery_comparison = comparisons_by_month.get(str(recovery_proxy.get("month", "")), {})
        recovery_return_delta = _float_or_none(recovery_comparison.get("return_delta_pct"))
        recovery_guard_triggered = _parse_bool(recovery_proxy.get("proxy_reversal_guard_triggered", False))

        recovery_exit_outcome, design_hint = _monthly_proxy_guard_recovery_exit_label(
            recovery_guard_triggered=recovery_guard_triggered,
            recovery_month_return=recovery_month_return,
            recovery_return_delta=recovery_return_delta,
        )
        rows.append(
            {
                "scenario": scenario or loss_proxy.get("scenario", ""),
                "candidate_label": candidate_label,
                "loss_month": loss_proxy.get("month", ""),
                "recovery_month": recovery_proxy.get("month", ""),
                "loss_month_return_pct": loss_proxy.get("month_return_pct", ""),
                "loss_return_delta_pct": loss_comparison.get("return_delta_pct", ""),
                "loss_drawdown_delta_pct": loss_comparison.get("drawdown_delta_pct", ""),
                "loss_target_exposure": loss_proxy.get("target_exposure", ""),
                "loss_cash_weight": loss_proxy.get("cash_weight", ""),
                "loss_guard_triggered": str(loss_guard_triggered).lower(),
                "loss_guard_reason": loss_proxy.get("proxy_reversal_guard_reason", ""),
                "loss_guard_medium_return_pct": loss_proxy.get("proxy_reversal_guard_medium_return_pct", ""),
                "loss_guard_short_return_pct": loss_proxy.get("proxy_reversal_guard_short_return_pct", ""),
                "loss_guard_medium_drawdown_pct": loss_proxy.get("proxy_reversal_guard_medium_drawdown_pct", ""),
                "recovery_month_return_pct": recovery_proxy.get("month_return_pct", ""),
                "recovery_baseline_return_pct": recovery_comparison.get("baseline_return_pct", ""),
                "recovery_candidate_return_pct": recovery_comparison.get("candidate_return_pct", ""),
                "recovery_return_delta_pct": recovery_comparison.get("return_delta_pct", ""),
                "recovery_drawdown_delta_pct": recovery_comparison.get("drawdown_delta_pct", ""),
                "recovery_target_exposure": recovery_proxy.get("target_exposure", ""),
                "recovery_cash_weight": recovery_proxy.get("cash_weight", ""),
                "recovery_guard_triggered": str(recovery_guard_triggered).lower(),
                "recovery_guard_reason": recovery_proxy.get("proxy_reversal_guard_reason", ""),
                "recovery_guard_medium_return_pct": recovery_proxy.get("proxy_reversal_guard_medium_return_pct", ""),
                "recovery_guard_short_return_pct": recovery_proxy.get("proxy_reversal_guard_short_return_pct", ""),
                "recovery_guard_medium_drawdown_pct": recovery_proxy.get("proxy_reversal_guard_medium_drawdown_pct", ""),
                "recovery_exit_outcome": recovery_exit_outcome,
                "candidate_design_hint": design_hint,
                "risk_note": (
                    "Diagnostic only; do_not_broaden_loss_cap or promote live trading without full "
                    "walk-forward validation and regression checks."
                ),
                "paper_only": "true",
            }
        )
    return rows


def _monthly_proxy_guard_recovery_exit_label(
    *,
    recovery_guard_triggered: bool,
    recovery_month_return: float | None,
    recovery_return_delta: float | None,
) -> tuple[str, str]:
    if recovery_month_return is not None and recovery_month_return > 0:
        if recovery_guard_triggered and recovery_return_delta is not None and recovery_return_delta < 0:
            return "recovery_drag_after_loss_cap", "test_guard_exit_after_loss_cap_confirmation"
        if recovery_guard_triggered:
            return "recovery_still_capped_without_drag", "review_guard_exit_before_tuning"
        return "recovery_uncapped_after_loss_cap", "preserve_recovery_participation"
    if recovery_month_return is not None and recovery_month_return < 0:
        return "continued_loss_after_loss_cap", "keep_loss_cap_and_review_loss_cluster"
    return "no_clear_recovery_after_loss_cap", "inspect_next_month_context"


def save_monthly_proxy_guard_outcomes(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_PROXY_GUARD_OUTCOME_COLUMNS)


def save_monthly_proxy_guard_recovery_exits(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_PROXY_GUARD_RECOVERY_EXIT_COLUMNS)


def save_monthly_recovery_attribution(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_RECOVERY_ATTRIBUTION_COLUMNS)


def analyze_monthly_stress_drawdown_pressure(
    *,
    scenario: str,
    monthly_rows: list[dict[str, Any]],
    symbol_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    path_rows: list[dict[str, Any]],
    recovery_rows: list[dict[str, Any]] | None = None,
    drawdown_threshold_pct: float = -25.0,
    top_symbol_count: int = 5,
) -> list[dict[str, Any]]:
    recovery = (recovery_rows or [{}])[0] if recovery_rows else {}
    worst_path = min(
        path_rows,
        key=lambda row: _float_or_none(row.get("drawdown_pct")) or 0.0,
        default={},
    )
    breach_rows = [
        row
        for row in path_rows
        if (_float_or_none(row.get("drawdown_pct")) is not None)
        and (_float_or_none(row.get("drawdown_pct")) or 0.0) <= drawdown_threshold_pct
    ]
    worst_month_row = min(
        monthly_rows,
        key=lambda row: _float_or_none(row.get("equity_change")) or 0.0,
        default={},
    )
    top_loss_rows = [
        row
        for row in sorted(
            symbol_rows,
            key=lambda row: _float_or_none(row.get("realized_pnl")) or 0.0,
        )
        if (_float_or_none(row.get("realized_pnl")) or 0.0) < 0
    ][: max(1, top_symbol_count)]
    top_loss_symbol = str(recovery.get("top_loss_symbol") or (top_loss_rows[0].get("symbol") if top_loss_rows else ""))
    top_loss_symbol_realized_pnl = str(
        recovery.get("top_loss_symbol_realized_pnl")
        or (top_loss_rows[0].get("realized_pnl") if top_loss_rows else "")
    )
    top_loss_symbols = str(recovery.get("top_loss_symbols") or _format_loss_symbol_list(top_loss_rows))
    top_loss_names = _loss_symbol_names(top_loss_symbols)
    breach_position_symbols = sorted(
        {
            symbol
            for row in breach_rows
            for symbol in _split_semicolon_values(str(row.get("position_symbols", "")))
        }
    )
    overlap_symbols = [symbol for symbol in top_loss_names if symbol in set(breach_position_symbols)]
    high_exposure_loss_decisions = [
        row
        for row in decision_rows
        if "high_exposure_proxy_loss" in str(row.get("diagnostic", ""))
        or (
            str(row.get("mode", "")) == "market_beta_proxy"
            and (_float_or_none(row.get("target_exposure")) or 0.0) >= 0.90
            and (_float_or_none(row.get("month_equity_change")) or 0.0) < 0
        )
    ]
    decision_mode_counts = Counter(str(row.get("mode", "")) for row in decision_rows if row.get("mode"))
    diagnostics: list[str] = []
    if breach_rows:
        diagnostics.append("drawdown_threshold_breach")
    if high_exposure_loss_decisions:
        diagnostics.append("high_exposure_proxy_loss_months")
    if overlap_symbols:
        diagnostics.append("loss_symbols_active_during_breach")
    recovery_diagnostic = str(recovery.get("diagnostic", ""))
    if "symbol_loss_concentration" in recovery_diagnostic:
        diagnostics.append("symbol_loss_concentration")
    if "insufficient_post_worst_recovery" in recovery_diagnostic:
        diagnostics.append("insufficient_post_worst_recovery")

    recommended_focus = "review_stress_drawdown_path"
    if overlap_symbols and high_exposure_loss_decisions:
        recommended_focus = "test_conditional_proxy_or_position_loss_guard"
    elif high_exposure_loss_decisions:
        recommended_focus = "test_conditional_proxy_entry_guard"
    elif breach_rows:
        recommended_focus = "test_drawdown_guard_overlay"

    avg_breach_exposure = _average_numeric(row.get("exposure") for row in breach_rows)
    max_breach_exposure = _max_numeric(row.get("exposure") for row in breach_rows)
    avg_breach_cash = _average_numeric(row.get("cash") for row in breach_rows)
    breach_months = sorted({str(row.get("date", ""))[:7] for row in breach_rows if row.get("date")})
    row = {
        "scenario": scenario,
        "worst_drawdown_date": worst_path.get("date", ""),
        "max_drawdown_pct": _format_optional_float(_float_or_none(worst_path.get("drawdown_pct"))),
        "drawdown_threshold_pct": _format_optional_float(drawdown_threshold_pct),
        "breach_day_count": str(len(breach_rows)),
        "breach_start": breach_rows[0].get("date", "") if breach_rows else "",
        "breach_end": breach_rows[-1].get("date", "") if breach_rows else "",
        "breach_months": ";".join(breach_months),
        "average_breach_exposure": _format_optional_float(avg_breach_exposure),
        "max_breach_exposure": _format_optional_float(max_breach_exposure),
        "average_breach_cash": _format_optional_float(avg_breach_cash),
        "worst_loss_month": recovery.get("worst_month") or worst_month_row.get("month", ""),
        "worst_month_return_pct": recovery.get("worst_month_return_pct") or worst_month_row.get("return_pct", ""),
        "worst_month_equity_change": (
            recovery.get("worst_month_equity_change") or worst_month_row.get("equity_change", "")
        ),
        "worst_month_mode": recovery.get("worst_month_mode") or _mode_for_month(decision_rows, str(worst_month_row.get("month", ""))),
        "worst_month_target_exposure": recovery.get("worst_month_target_exposure", ""),
        "worst_month_cash_weight": recovery.get("worst_month_cash_weight", ""),
        "top_loss_symbol": top_loss_symbol,
        "top_loss_symbol_realized_pnl": top_loss_symbol_realized_pnl,
        "top_loss_symbols": top_loss_symbols,
        "breach_position_symbols": ";".join(breach_position_symbols),
        "top_loss_symbols_in_breach_positions": ";".join(overlap_symbols),
        "top_loss_symbol_overlap_count": str(len(overlap_symbols)),
        "high_exposure_loss_month_count": str(len(high_exposure_loss_decisions)),
        "decision_mode_counts": ";".join(f"{mode}={count}" for mode, count in sorted(decision_mode_counts.items())),
        "diagnostic": ";".join(diagnostics) if diagnostics else "no_drawdown_pressure_detected",
        "recommended_candidate_focus": recommended_focus,
        "paper_only": "true",
        "risk_note": "Diagnostic summary only; do not create or transmit live orders from this report.",
    }
    return [row]


def save_monthly_stress_drawdown_pressure(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_STRESS_DRAWDOWN_PRESSURE_COLUMNS)


def save_monthly_attribution_comparison(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_ATTRIBUTION_COMPARISON_COLUMNS)


def save_monthly_benchmark_excess(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_BENCHMARK_EXCESS_COLUMNS)


def save_monthly_benchmark_contributions(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_BENCHMARK_CONTRIBUTION_COLUMNS)


def save_monthly_benchmark_selection(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_BENCHMARK_SELECTION_COLUMNS)


def save_monthly_benchmark_selection_summary(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_BENCHMARK_SELECTION_SUMMARY_COLUMNS,
    )


def save_monthly_benchmark_selection_summary_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_BENCHMARK_SELECTION_SUMMARY_COMPARISON_COLUMNS,
    )


def save_monthly_benchmark_selection_window_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_BENCHMARK_SELECTION_WINDOW_COMPARISON_COLUMNS,
    )


def save_monthly_entry_month_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_ENTRY_MONTH_COMPARISON_COLUMNS,
    )


def save_monthly_entry_path_subperiod_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_ENTRY_PATH_SUBPERIOD_COMPARISON_COLUMNS,
    )


def save_monthly_entry_contribution_overlap_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_ENTRY_CONTRIBUTION_OVERLAP_COMPARISON_COLUMNS,
    )


def save_monthly_entry_selection_rotation_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_ENTRY_SELECTION_ROTATION_COMPARISON_COLUMNS,
    )


def save_monthly_entry_selection_eligibility_comparison(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_ENTRY_SELECTION_ELIGIBILITY_COMPARISON_COLUMNS,
    )


def save_monthly_decision_attribution_comparison(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_DECISION_ATTRIBUTION_COMPARISON_COLUMNS,
    )


def save_monthly_path_attribution(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_PATH_ATTRIBUTION_COLUMNS)


def save_monthly_execution_gap(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_EXECUTION_GAP_COLUMNS)


def save_monthly_path_attribution_comparison(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_PATH_ATTRIBUTION_COMPARISON_COLUMNS,
    )


def save_monthly_path_attribution_comparison_summary(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(
        rows,
        output_path,
        columns=MONTHLY_PATH_ATTRIBUTION_COMPARISON_SUMMARY_COLUMNS,
    )


def save_monthly_attribution_rows(
    rows: list[dict[str, Any]],
    output_path: Path | str,
    columns: list[str] | None = None,
) -> int:
    fieldnames = columns or MONTHLY_DRAWDOWN_ATTRIBUTION_COLUMNS
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})
    return len(rows)


def _average_numeric(values: Any) -> float | None:
    parsed = [_float_or_none(value) for value in values]
    numeric = [value for value in parsed if value is not None]
    return sum(numeric) / len(numeric) if numeric else None


def _format_loss_symbol_list(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows:
        symbol = str(row.get("symbol", "")).strip()
        pnl = _format_optional_float(_float_or_none(row.get("realized_pnl")))
        if symbol:
            parts.append(f"{symbol}:{pnl}")
    return ";".join(parts)


def _loss_symbol_names(value: str) -> list[str]:
    names: list[str] = []
    for part in _split_semicolon_values(value):
        symbol = part.split(":", 1)[0].strip()
        if symbol:
            names.append(symbol)
    return names


def _mode_for_month(decision_rows: list[dict[str, Any]], month: str) -> str:
    for row in decision_rows:
        if str(row.get("month", "")).strip() == month:
            return str(row.get("mode", "")).strip()
    return ""


def _monthly_return_rows(result: MonthlyBacktestResult) -> list[dict[str, Any]]:
    month_ends: list[tuple[str, str, float]] = []
    for day, equity in zip(result.dates, result.equity_curve):
        month = str(day)[:7]
        if month_ends and month_ends[-1][0] == month:
            month_ends[-1] = (month, day, float(equity))
        else:
            month_ends.append((month, day, float(equity)))
    rows: list[dict[str, Any]] = []
    previous_equity = float(result.initial_cash)
    for month, day, equity in month_ends:
        monthly_return = (equity / previous_equity - 1.0) if previous_equity > 0 else 0.0
        rows.append({"month": month, "date": day, "equity": equity, "return": monthly_return})
        previous_equity = equity
    return rows


def _rolling_compound_return_min(returns: list[float], window: int) -> float:
    if window <= 0 or len(returns) < window:
        return 0.0
    values: list[float] = []
    for index in range(0, len(returns) - window + 1):
        compound = 1.0
        for value in returns[index : index + window]:
            compound *= 1.0 + value
        values.append(compound - 1.0)
    return min(values) if values else 0.0


def _max_recovery_months(monthly_rows: list[dict[str, Any]], initial_cash: float) -> int:
    peak = float(initial_cash)
    underwater_start: int | None = None
    max_months = 0
    for index, row in enumerate(monthly_rows, start=1):
        equity = float(row["equity"])
        if equity >= peak:
            if underwater_start is not None:
                max_months = max(max_months, index - underwater_start)
                underwater_start = None
            peak = equity
        elif underwater_start is None:
            underwater_start = index
    if underwater_start is not None:
        max_months = max(max_months, len(monthly_rows) + 1 - underwater_start)
    return max_months


def _symbol_profit_contributions(
    result: MonthlyBacktestResult,
    symbol_candles: dict[str, list[Candle]],
) -> dict[str, float]:
    cashflows: dict[str, float] = {}
    quantities: dict[str, int] = {}
    for trade in result.trades:
        amount = float(trade.price) * int(trade.quantity)
        cashflows.setdefault(trade.symbol, 0.0)
        quantities.setdefault(trade.symbol, 0)
        if trade.action == "BUY":
            cashflows[trade.symbol] -= amount
            quantities[trade.symbol] += int(trade.quantity)
        elif trade.action == "SELL":
            cashflows[trade.symbol] += amount
            quantities[trade.symbol] -= int(trade.quantity)
    final_date = result.dates[-1] if result.dates else ""
    contributions: dict[str, float] = {}
    for symbol, cashflow in cashflows.items():
        final_value = 0.0
        quantity = quantities.get(symbol, 0)
        if quantity > 0:
            final_price = _last_close_on_or_before(symbol_candles.get(symbol, []), final_date)
            final_value = quantity * final_price
        contributions[symbol] = cashflow + final_value
    return contributions


def _last_close_on_or_before(candles: list[Candle], day: str) -> float:
    prior = [candle for candle in candles if not day or candle.date <= day]
    if not prior:
        return 0.0
    return sorted(prior, key=lambda candle: candle.date)[-1].close


def save_monthly_performance_audit_rows(rows: list[dict[str, str]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in PERFORMANCE_AUDIT_COLUMNS} for row in rows)
    return len(rows)


def load_performance_guard(
    path: Path | str | None,
    *,
    warn_scale: float = 0.1,
    block_scale: float = 0.0,
) -> PerformanceGuard | None:
    if path is None:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return PerformanceGuard(
            status="BLOCK",
            detail=f"empty performance report: {csv_path}",
            scale=min(1.0, max(0.0, block_scale)),
            source=str(csv_path),
        )
    blocked = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "BLOCK"
    ]
    if blocked:
        return PerformanceGuard(
            status="BLOCK",
            detail="; ".join(blocked[:5]),
            scale=min(1.0, max(0.0, block_scale)),
            source=str(csv_path),
        )
    warned = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "WARN"
    ]
    if warned:
        return PerformanceGuard(
            status="WARN",
            detail="; ".join(warned[:5]),
            scale=min(1.0, max(0.0, warn_scale)),
            source=str(csv_path),
        )
    return PerformanceGuard(
        status="PASS",
        detail=f"{len(rows)} performance checks passed",
        scale=1.0,
        source=str(csv_path),
    )


def apply_performance_guard(decision: MonthlyDecision, guard: PerformanceGuard | None) -> MonthlyDecision:
    if guard is None or guard.scale >= 1.0:
        return decision
    status = guard.status.lower()
    return scale_monthly_decision_targets(
        decision,
        scale=guard.scale,
        reason_suffix=f"_performance_{status}_scale_{guard.scale:.4f}",
    )


def compress_decision_to_buyable_targets(
    decision: MonthlyDecision,
    *,
    reference_prices: dict[str, float],
    portfolio_value: float,
    max_position_weight: float,
    min_target_value: float,
) -> MonthlyDecision:
    if not decision.target_weights or portfolio_value <= 0:
        return decision
    target_budget = sum(weight for weight in decision.target_weights.values() if weight > 0)
    if target_budget <= 0:
        return decision
    ranked_symbols = list(decision.target_weights.keys())
    selected = select_buyable_targets(
        ranked_symbols,
        reference_prices=reference_prices,
        portfolio_value=portfolio_value,
        target_budget=target_budget,
        max_position_weight=max_position_weight,
        min_target_value=min_target_value,
    )
    if selected == ranked_symbols:
        return decision
    if selected:
        target_weights = target_weights_for_symbols(
            selected,
            target_budget=target_budget,
            max_position_weight=max_position_weight,
        )
    else:
        target_weights = {}
    return MonthlyDecision(
        as_of_date=decision.as_of_date,
        signal_date=decision.signal_date,
        mode=decision.mode,
        selected_preset=decision.selected_preset,
        target_weights=target_weights,
        reason=f"{decision.reason}_buyable_targets_{len(selected)}of{len(ranked_symbols)}",
    )


def reserve_unbuyable_targets_as_cash(
    decision: MonthlyDecision,
    *,
    reference_prices: dict[str, float],
    portfolio_value: float,
    min_target_value: float,
) -> MonthlyDecision:
    if not decision.target_weights or portfolio_value <= 0:
        return decision
    ranked_symbols = list(decision.target_weights.keys())
    selected = [
        symbol
        for symbol in ranked_symbols
        if _target_is_buyable(symbol, decision.target_weights, reference_prices, portfolio_value, min_target_value)
    ]
    if selected == ranked_symbols:
        return decision
    target_weights = {symbol: decision.target_weights[symbol] for symbol in selected}
    return MonthlyDecision(
        as_of_date=decision.as_of_date,
        signal_date=decision.signal_date,
        mode=decision.mode,
        selected_preset=decision.selected_preset,
        target_weights=target_weights,
        reason=f"{decision.reason}_unbuyable_cash_reserve_{len(selected)}of{len(ranked_symbols)}",
    )


def build_deployment_gate(
    result: MonthlyBacktestResult,
    *,
    universe_bias: dict[str, Any],
    min_excess_return_pct: float = 0.0,
    max_drawdown_pct: float = -25.0,
    allow_universe_bias_warning: bool = False,
    source: str = "monthly-backtest",
) -> DeploymentGate:
    reason = "passed"
    deployable = True
    if result.trade_count <= 0:
        deployable = False
        reason = "no_trades"
    elif result.excess_return_pct <= min_excess_return_pct:
        deployable = False
        reason = "negative_excess_return"
    elif result.max_drawdown_pct < max_drawdown_pct:
        deployable = False
        reason = "max_drawdown_breach"
    elif bool(universe_bias.get("warning")) and not allow_universe_bias_warning:
        deployable = False
        reason = "universe_bias_warning"
    return DeploymentGate(
        deployable=deployable,
        reason=reason,
        source=source,
        total_return_pct=round(result.total_return_pct, 4),
        buy_hold_return_pct=round(result.buy_hold_return_pct, 4),
        excess_return_pct=round(result.excess_return_pct, 4),
        max_drawdown_pct=round(result.max_drawdown_pct, 4),
        trade_count=result.trade_count,
        universe_bias_warning=bool(universe_bias.get("warning")),
    )


def build_monthly_validation_gate(rows: list[dict[str, Any]], *, source: str = "monthly-validate") -> DeploymentGate:
    if not rows:
        return DeploymentGate(deployable=False, reason="no_validation_scenarios", source=source)
    failed = [
        str(row.get("name", "unknown"))
        for row in rows
        if _parse_bool(row.get("required", True)) and not _parse_bool(row.get("deployable", False))
    ]
    if failed:
        return DeploymentGate(
            deployable=False,
            reason=f"failed_required_scenarios:{','.join(failed[:5])}",
            source=source,
        )
    excess_values = [float(row.get("excess_return_pct", 0) or 0) for row in rows]
    drawdown_values = [float(row.get("max_drawdown_pct", 0) or 0) for row in rows]
    return DeploymentGate(
        deployable=True,
        reason="passed",
        source=source,
        excess_return_pct=round(min(excess_values), 4) if excess_values else 0.0,
        max_drawdown_pct=round(min(drawdown_values), 4) if drawdown_values else 0.0,
        trade_count=sum(int(float(row.get("trade_count", 0) or 0)) for row in rows),
        universe_bias_warning=any(_parse_bool(row.get("universe_bias_warning", False)) for row in rows),
    )


def run_monthly_validation_suite(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
    min_excess_return_pct: float = 0.0,
    max_drawdown_pct: float = -25.0,
    allow_universe_bias_warning: bool = False,
    backtest_runner: Callable[..., MonthlyBacktestResult] | None = None,
) -> list[dict[str, Any]]:
    runner = backtest_runner or run_monthly_rebalance_backtest
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_candles = symbol_candles
        stress_parts: list[str] = []
        if case.stress_exclude_return_above is not None:
            case_candles = exclude_extreme_period_return_symbols(
                case_candles,
                start=case.start,
                end=case.end,
                max_period_return_pct=case.stress_exclude_return_above,
            )
            stress_parts.append(f"exclude_return_above_{case.stress_exclude_return_above:g}")
        if case.stress_exclude_top_return_symbols > 0:
            case_candles = exclude_top_period_return_symbols(
                case_candles,
                start=case.start,
                end=case.end,
                top_n=case.stress_exclude_top_return_symbols,
            )
            stress_parts.append(f"exclude_top_{case.stress_exclude_top_return_symbols}")

        case_config = (
            replace(config, point_in_time_liquidity_top_n=case.liquidity_top_n)
            if case.liquidity_top_n is not None
            else config
        )
        result = runner(
            case_candles,
            start=case.start,
            end=case.end,
            config=case_config,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate * case.slippage_multiplier,
            min_trade_value=min_trade_value,
        )
        bias = diagnose_universe_bias(case_candles, start=case.start, end=case.end)
        gate = build_deployment_gate(
            result,
            universe_bias=bias,
            min_excess_return_pct=min_excess_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            allow_universe_bias_warning=allow_universe_bias_warning,
            source=case.name,
        )
        rows.append(
            {
                "name": case.name,
                "category": case.category,
                "required": case.required,
                "train_start": case.train_start,
                "train_end": case.train_end,
                "selected_preset": "",
                "train_excess_return_pct": "",
                "start": case.start,
                "end": case.end,
                "slippage_multiplier": case.slippage_multiplier,
                "stress": case.stress or ";".join(stress_parts),
                "final_equity": round(result.final_equity, 4),
                "total_return_pct": round(result.total_return_pct, 4),
                "buy_hold_return_pct": round(result.buy_hold_return_pct, 4),
                "excess_return_pct": round(result.excess_return_pct, 4),
                "max_drawdown_pct": round(result.max_drawdown_pct, 4),
                "trade_count": result.trade_count,
                "universe_bias_warning": bool(bias.get("warning")),
                "universe_bias_reasons": _format_universe_bias_reasons(bias),
                "universe_symbol_count": bias.get("symbol_count", 0),
                "universe_avg_symbol_return_pct": bias.get("average_symbol_return_pct", 0.0),
                "universe_median_symbol_return_pct": bias.get("median_symbol_return_pct", 0.0),
                "universe_extreme_return_symbols": bias.get("extreme_return_symbols", 0),
                "universe_extreme_return_share": bias.get("extreme_return_share", 0.0),
                "deployable": gate.deployable,
                "reason": gate.reason,
            }
        )
    return rows


def run_monthly_walk_forward_validation(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
    min_excess_return_pct: float = 0.0,
    max_drawdown_pct: float = -25.0,
    allow_universe_bias_warning: bool = False,
    backtest_runner: Callable[..., MonthlyBacktestResult] | None = None,
) -> list[dict[str, Any]]:
    runner = backtest_runner or run_monthly_rebalance_backtest
    rows: list[dict[str, Any]] = []
    for case in cases:
        direct_train_rows = _monthly_walk_forward_direct_train_rows(symbol_candles, case, config)
        direct_train_diagnostics = _monthly_walk_forward_direct_train_diagnostics(
            symbol_candles,
            case,
            config,
            direct_train_rows=direct_train_rows,
        )
        train_rows: list[dict[str, Any]] = []
        train_results: dict[str, MonthlyBacktestResult] = {}
        for preset in config.presets:
            train_result = runner(
                symbol_candles,
                start=case.train_start,
                end=case.train_end,
                config=replace(config, presets=(preset,)),
                initial_cash=initial_cash,
                fee_rate=fee_rate,
                tax_rate=tax_rate,
                slippage_rate=slippage_rate,
                min_trade_value=min_trade_value,
            )
            train_results[preset] = train_result
            train_rows.append(_monthly_validation_train_row(preset, train_result))
        selected = select_best_train_candidate(
            train_rows,
            min_train_trades=config.min_train_trades,
            min_train_positive_ratio=config.min_train_positive_ratio,
        )
        train_rejected = selected is None
        if selected is None:
            selected = max(train_rows, key=_monthly_validation_train_score)

        selected_preset = str(selected["preset"])
        train_result = train_results[selected_preset]
        test_config = replace(config, presets=(selected_preset,), train_start=case.train_start)
        test_result = runner(
            symbol_candles,
            start=case.start,
            end=case.end,
            config=test_config,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate * case.slippage_multiplier,
            min_trade_value=min_trade_value,
        )
        bias = diagnose_universe_bias(symbol_candles, start=case.start, end=case.end)
        gate = build_deployment_gate(
            test_result,
            universe_bias=bias,
            min_excess_return_pct=min_excess_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            allow_universe_bias_warning=allow_universe_bias_warning,
            source=case.name,
        )
        if train_rejected or train_result.excess_return_pct <= min_excess_return_pct:
            gate = DeploymentGate(
                deployable=False,
                reason="train_window_rejected",
                source=case.name,
                total_return_pct=gate.total_return_pct,
                buy_hold_return_pct=gate.buy_hold_return_pct,
                excess_return_pct=gate.excess_return_pct,
                max_drawdown_pct=gate.max_drawdown_pct,
                trade_count=gate.trade_count,
                universe_bias_warning=gate.universe_bias_warning,
            )
        rows.append(
            {
                "name": case.name,
                "category": "walk_forward",
                "required": case.required,
                "train_start": case.train_start,
                "train_end": case.train_end,
                "selected_preset": selected_preset,
                "train_excess_return_pct": round(train_result.excess_return_pct, 4),
                "train_candidate_scores": _format_monthly_validation_train_scores(train_rows),
                "train_candidate_decision_profiles": _format_monthly_validation_train_decision_profiles(train_rows),
                "train_candidate_direct_scores": _format_monthly_validation_train_scores(direct_train_rows),
                "train_direct_diagnostics": direct_train_diagnostics,
                "start": case.start,
                "end": case.end,
                "slippage_multiplier": case.slippage_multiplier,
                "stress": case.stress,
                "final_equity": round(test_result.final_equity, 4),
                "total_return_pct": round(test_result.total_return_pct, 4),
                "buy_hold_return_pct": round(test_result.buy_hold_return_pct, 4),
                "excess_return_pct": round(test_result.excess_return_pct, 4),
                "max_drawdown_pct": round(test_result.max_drawdown_pct, 4),
                "trade_count": test_result.trade_count,
                "universe_bias_warning": bool(bias.get("warning")),
                "universe_bias_reasons": _format_universe_bias_reasons(bias),
                "universe_symbol_count": bias.get("symbol_count", 0),
                "universe_avg_symbol_return_pct": bias.get("average_symbol_return_pct", 0.0),
                "universe_median_symbol_return_pct": bias.get("median_symbol_return_pct", 0.0),
                "universe_extreme_return_symbols": bias.get("extreme_return_symbols", 0),
                "universe_extreme_return_share": bias.get("extreme_return_share", 0.0),
                "deployable": gate.deployable,
                "reason": gate.reason,
            }
        )
    return rows


def _monthly_walk_forward_direct_train_rows(
    symbol_candles: dict[str, list[Candle]],
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    if not case.train_start or not case.train_end:
        return []
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []
    preset_configs = _monthly_preset_configs(config)
    return _train_candidate_rows(
        decision_candles,
        train_candles=train_candles,
        train_start=case.train_start,
        train_end=case.train_end,
        preset_configs=preset_configs,
        min_rows_per_window=config.min_rows_per_window,
        start_grace_days=config.start_grace_days,
        train_stability_years=config.train_stability_years,
    )


def _monthly_walk_forward_direct_train_diagnostics(
    symbol_candles: dict[str, list[Candle]],
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
    *,
    direct_train_rows: list[dict[str, Any]],
) -> str:
    if not case.train_start or not case.train_end:
        return ""
    period_days = _inclusive_date_days(case.train_start, case.train_end)
    raw_symbol_count = len(symbol_candles)
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError as exc:
        return "; ".join(
            [
                f"period_days={period_days}",
                f"raw_symbols={raw_symbol_count}",
                f"filter_error={_diagnostic_token(str(exc))}",
            ]
        )

    universe_count = len(universe_candles)
    pit_count = len(point_in_time_candles)
    liquid_count = len(decision_candles)
    train_count = len(train_candles)
    returns = [value for _, value in _period_symbol_returns(train_candles, start=case.train_start, end=case.train_end)]
    average_return = mean(returns) if returns else None
    median_return = median(returns) if returns else None
    direct_excess_values = [
        value
        for value in (_float_or_none(row.get("excess_return_pct")) for row in direct_train_rows)
        if value is not None
    ]
    best_direct_excess = max(direct_excess_values) if direct_excess_values else None
    best_direct_row = max(direct_train_rows, key=_direct_train_row_excess_sort_value, default={})
    all_direct_nonpositive = bool(direct_excess_values) and all(value <= 0.0 for value in direct_excess_values)

    parts = [
        f"period_days={period_days}",
        f"raw_symbols={raw_symbol_count}",
        f"universe_symbols={universe_count}",
        f"pit_symbols={pit_count}",
        f"liquid_symbols={liquid_count}",
        f"train_symbols={train_count}",
        f"liquidity_top_n={config.point_in_time_liquidity_top_n}",
        f"liquidity_window_days={config.point_in_time_liquidity_window_days}",
        f"universe_removed={max(0, raw_symbol_count - universe_count)}",
        f"pit_filter_removed={max(0, universe_count - pit_count)}",
        f"liquidity_removed={max(0, pit_count - liquid_count)}",
        f"train_coverage_removed={max(0, liquid_count - train_count)}",
        f"train_avg_symbol_return_pct={_format_optional_float(average_return)}",
        f"train_median_symbol_return_pct={_format_optional_float(median_return)}",
        f"market_regime={_classify_train_market_regime(average_return, median_return)}",
        f"direct_candidate_count={len(direct_train_rows)}",
        f"best_direct_total_return_pct={_format_optional_float(_float_or_none(best_direct_row.get('total_return_pct')))}",
        f"best_direct_buy_hold_return_pct={_format_optional_float(_float_or_none(best_direct_row.get('buy_hold_return_pct')))}",
        f"best_direct_excess_pct={_format_optional_float(best_direct_excess)}",
        f"all_direct_excess_nonpositive={str(all_direct_nonpositive).lower()}",
    ]
    return "; ".join(parts)


def _inclusive_date_days(start: str, end: str) -> int:
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except ValueError:
        return 0


def _classify_train_market_regime(average_return: float | None, median_return: float | None) -> str:
    if average_return is None or median_return is None:
        return "unknown"
    if median_return <= -5.0 or average_return <= -10.0:
        return "weak"
    if median_return < 5.0:
        return "sideways"
    return "risk_on"


def _direct_train_row_excess_sort_value(row: dict[str, Any]) -> float:
    value = _float_or_none(row.get("excess_return_pct"))
    return value if value is not None else float("-inf")


def _diagnostic_token(value: str) -> str:
    token = "_".join(part for part in value.lower().replace(":", " ").replace(";", " ").split() if part)
    return token or "unknown"


def _monthly_validation_train_row(preset: str, result: MonthlyBacktestResult) -> dict[str, Any]:
    return {
        "preset": preset,
        "excess_return_pct": result.excess_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "trades": result.trade_count,
        "decision_profile": _format_monthly_validation_train_decision_profile(result),
    }


def _monthly_validation_train_score(row: dict[str, Any]) -> float:
    return float(row["excess_return_pct"]) + float(row["max_drawdown_pct"])


def _format_monthly_validation_train_scores(rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        preset = str(row.get("preset", "")).strip()
        if not preset:
            continue
        excess = _format_optional_float(_float_or_none(row.get("excess_return_pct")))
        drawdown = _format_optional_float(_float_or_none(row.get("max_drawdown_pct")))
        trades = str(row.get("trades", "")).strip()
        score = _format_optional_float(_monthly_validation_train_score(row))
        parts.append(f"{preset}:excess={excess},drawdown={drawdown},trades={trades},score={score}")
    return "; ".join(parts)


def _format_monthly_validation_train_decision_profiles(rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        preset = str(row.get("preset", "")).strip()
        profile = str(row.get("decision_profile", "")).strip()
        if preset and profile:
            parts.append(f"{preset}:{profile}")
    return "; ".join(parts)


def _format_monthly_validation_train_decision_profile(result: MonthlyBacktestResult) -> str:
    decision_count = len(result.decisions)
    if not decision_count:
        return "modes=none,selected=none,alpha_ratio=0"
    mode_counts = Counter(decision.mode for decision in result.decisions)
    selected_counts = Counter(decision.selected_preset for decision in result.decisions)
    alpha_ratio = mode_counts.get("alpha", 0) / decision_count
    modes = "|".join(f"{key}:{mode_counts[key]}" for key in sorted(mode_counts))
    selected = "|".join(f"{key}:{selected_counts[key]}" for key in sorted(selected_counts))
    return (
        f"modes={modes},selected={selected},"
        f"alpha_ratio={_format_optional_float(alpha_ratio)}"
    )


def generate_monthly_validation_cases(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
) -> list[MonthlyValidationCase]:
    dates = _available_dates(symbol_candles, start=start, end=end)
    if not dates:
        return []

    first_date = dates[0]
    last_date = dates[-1]
    cases: list[MonthlyValidationCase] = [
        MonthlyValidationCase(name="full_period", category="duration", start=first_date, end=last_date),
    ]

    for name, rows in [
        ("duration_3m", 63),
        ("duration_6m", 126),
        ("duration_1y", 252),
        ("duration_2y", 504),
    ]:
        case_start = _date_n_rows_before(dates, rows)
        if case_start != first_date or name == "duration_3m":
            cases.append(MonthlyValidationCase(name=name, category="duration", start=case_start, end=last_date))

    cases.extend(
        [
            MonthlyValidationCase(
                name="stress_exclude_500pct_winners",
                category="stress",
                start=first_date,
                end=last_date,
                stress_exclude_return_above=500.0,
                stress="exclude_return_above_500",
            ),
            MonthlyValidationCase(
                name="stress_exclude_top_5_winners",
                category="stress",
                start=first_date,
                end=last_date,
                stress_exclude_top_return_symbols=5,
                stress="exclude_top_5_winners",
            ),
            MonthlyValidationCase(
                name="stress_slippage_x2",
                category="stress",
                start=first_date,
                end=last_date,
                slippage_multiplier=2.0,
                stress="slippage_x2",
            ),
            MonthlyValidationCase(
                name="stress_slippage_x3",
                category="stress",
                start=first_date,
                end=last_date,
                slippage_multiplier=3.0,
                stress="slippage_x3",
            ),
            MonthlyValidationCase(
                name="stress_liquidity_top_50",
                category="stress",
                start=first_date,
                end=last_date,
                liquidity_top_n=50,
                stress="liquidity_top_50",
            ),
        ]
    )

    cases.extend(_generate_regime_validation_cases(symbol_candles, dates))
    cases.extend(_generate_walk_forward_validation_cases(dates))
    return cases


def audit_monthly_validation_data(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    min_rows: int = 252,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, candles in sorted(symbol_candles.items()):
        period = [candle for candle in sorted(candles, key=lambda candle: candle.date) if start <= candle.date <= end]
        dates = [candle.date for candle in period]
        duplicate_dates = len(dates) - len(set(dates))
        nonpositive_price_rows = sum(
            1
            for candle in period
            if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0
        )
        reasons: list[str] = []
        if len(period) < min_rows:
            reasons.append("short_history")
        if duplicate_dates:
            reasons.append("duplicate_dates")
        if nonpositive_price_rows:
            reasons.append("nonpositive_price")
        rows.append(
            {
                "symbol": symbol,
                "status": "BLOCK" if reasons else "PASS",
                "first_date": period[0].date if period else "",
                "last_date": period[-1].date if period else "",
                "rows": len(period),
                "duplicate_dates": duplicate_dates,
                "nonpositive_price_rows": nonpositive_price_rows,
                "reason": ";".join(reasons) if reasons else "passed",
            }
        )
    return rows


def save_validation_data_quality_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_DATA_QUALITY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_DATA_QUALITY_COLUMNS})
    return len(rows)


def audit_point_in_time_price_coverage(
    symbol_candles: dict[str, list[Candle]],
    point_in_time_universe: dict[str, set[str]],
    *,
    min_coverage_pct: float = 80.0,
    missing_preview_size: int = 10,
    excluded_symbols: set[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    excluded = {_normalize_symbol_code(symbol) for symbol in (excluded_symbols or set())}
    sorted_candles = {
        symbol: sorted(candles, key=lambda candle: candle.date)
        for symbol, candles in symbol_candles.items()
        if candles
    }
    for snapshot_date, universe_symbols in sorted(point_in_time_universe.items()):
        eligible_symbols, _ = _eligible_universe_symbols(
            sorted_candles,
            point_in_time_universe,
            snapshot_date=snapshot_date,
            as_of_date=snapshot_date,
            min_history_days=0,
        )
        excluded_in_snapshot = sorted(eligible_symbols & excluded)
        normalized_universe = eligible_symbols - excluded
        price_symbols = {
            symbol
            for symbol, candles in sorted_candles.items()
            if any(candle.date <= snapshot_date for candle in candles)
        }
        covered = normalized_universe & price_symbols
        missing = sorted(normalized_universe - covered)
        universe_count = len(normalized_universe)
        coverage_pct = (len(covered) / universe_count * 100) if universe_count else 100.0
        rows.append(
            {
                "date": snapshot_date,
                "universe_symbols": universe_count,
                "price_symbols": len(price_symbols),
                "covered_symbols": len(covered),
                "excluded_symbols": len(excluded_in_snapshot),
                "missing_symbols": len(missing),
                "coverage_pct": round(coverage_pct, 4),
                "status": "PASS" if coverage_pct >= min_coverage_pct else "BLOCK",
                "missing_preview": ";".join(missing[:missing_preview_size]),
                "excluded_preview": ";".join(excluded_in_snapshot[:missing_preview_size]),
            }
        )
    return rows


def save_universe_price_coverage_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIVERSE_PRICE_COVERAGE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in UNIVERSE_PRICE_COVERAGE_COLUMNS})
    return len(rows)


def save_universe_filter_report(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIVERSE_FILTER_REPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in UNIVERSE_FILTER_REPORT_COLUMNS})
    return len(rows)


def save_monthly_validation_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_VALIDATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MONTHLY_VALIDATION_COLUMNS})
    return len(rows)


def analyze_monthly_direct_alpha_selection(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(_monthly_direct_alpha_selection_for_case(symbol_candles, case=case, config=config))
    return rows


def save_monthly_direct_alpha_selection(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_ALPHA_SELECTION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DIRECT_ALPHA_SELECTION_COLUMNS})
    return len(rows)


def analyze_monthly_direct_alpha_holding_path(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(_monthly_direct_alpha_holding_path_for_case(symbol_candles, case=case, config=config))
    return rows


def save_monthly_direct_alpha_holding_path(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_ALPHA_HOLDING_PATH_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DIRECT_ALPHA_HOLDING_PATH_COLUMNS})
    return len(rows)


def analyze_monthly_direct_alpha_path_drift(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(_monthly_direct_alpha_path_drift_for_case(symbol_candles, case=case, config=config))
    return rows


def save_monthly_direct_alpha_path_drift(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_ALPHA_PATH_DRIFT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DIRECT_ALPHA_PATH_DRIFT_COLUMNS})
    return len(rows)


def analyze_monthly_direct_alpha_timing(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(_monthly_direct_alpha_timing_for_case(symbol_candles, case=case, config=config))
    return rows


def save_monthly_direct_alpha_timing(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_ALPHA_TIMING_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DIRECT_ALPHA_TIMING_COLUMNS})
    return len(rows)


def analyze_monthly_direct_alpha_rank_drift(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(_monthly_direct_alpha_rank_drift_for_case(symbol_candles, case=case, config=config))
    return rows


def save_monthly_direct_alpha_rank_drift(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIRECT_ALPHA_RANK_DRIFT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DIRECT_ALPHA_RANK_DRIFT_COLUMNS})
    return len(rows)


def analyze_monthly_train_decision_path(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(
            _monthly_train_decision_path_for_case(
                symbol_candles,
                case=case,
                config=config,
                initial_cash=initial_cash,
                fee_rate=fee_rate,
                tax_rate=tax_rate,
                slippage_rate=slippage_rate,
                min_trade_value=min_trade_value,
            )
        )
    return rows


def save_monthly_train_decision_path(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_TRAIN_DECISION_PATH_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MONTHLY_TRAIN_DECISION_PATH_COLUMNS})
    return len(rows)


def analyze_monthly_train_stability_windows(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    config: MonthlyRebalanceConfig,
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not case.train_start or not case.train_end:
            continue
        rows.extend(
            _monthly_train_stability_windows_for_case(
                symbol_candles,
                case=case,
                config=config,
                initial_cash=initial_cash,
                fee_rate=fee_rate,
                tax_rate=tax_rate,
                slippage_rate=slippage_rate,
                min_trade_value=min_trade_value,
            )
        )
    return rows


def save_monthly_train_stability_windows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_TRAIN_STABILITY_WINDOW_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MONTHLY_TRAIN_STABILITY_WINDOW_COLUMNS})
    return len(rows)


def analyze_monthly_train_stability_summary(stability_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in stability_rows:
        candidate_name = str(row.get("candidate_name", "") or row.get("preset", "")).strip()
        if not candidate_name:
            candidate_name = "no_direct_candidate"
        key = (
            str(row.get("scenario", "")).strip(),
            str(row.get("walk_forward_preset", "")).strip(),
            str(row.get("category", "")).strip(),
            candidate_name,
            str(row.get("candidate_rank", "")).strip(),
        )
        if key[0]:
            groups.setdefault(key, []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        scenario, walk_forward_preset, category, candidate_name, candidate_rank = key
        rows = groups[key]
        decision_dates = {
            str(row.get("as_of_date", "")).strip()
            for row in rows
            if str(row.get("as_of_date", "")).strip()
        }
        eligible_decisions = {
            str(row.get("as_of_date", "")).strip()
            for row in rows
            if str(row.get("as_of_date", "")).strip()
            and str(row.get("candidate_eligible", "")).strip().lower() == "true"
        }
        low_positive_ratio_decisions = {
            str(row.get("as_of_date", "")).strip()
            for row in rows
            if str(row.get("as_of_date", "")).strip()
            and "low_positive_ratio" in _split_semicolon_values(str(row.get("candidate_rejection_reasons", "")))
        }
        counted_rows = [
            row
            for row in rows
            if str(row.get("subwindow_counted_flag", "")).strip().lower() == "true"
        ]
        positive_rows = [
            row
            for row in counted_rows
            if str(row.get("stability_positive", row.get("subwindow_positive_flag", ""))).strip().lower()
            == "true"
        ]
        negative_rows = [row for row in counted_rows if row not in positive_rows]
        excess_values = [
            value
            for value in (_float_or_none(row.get("stability_excess_return_pct")) for row in counted_rows)
            if value is not None
        ]
        positive_ratios = [
            value
            for value in (_float_or_none(row.get("candidate_positive_ratio")) for row in rows)
            if value is not None
        ]
        no_trade_rows = [
            row
            for row in counted_rows
            if "no_trades" in _split_semicolon_values(str(row.get("stability_failed_reason", "")))
            or "no_trades" in _split_semicolon_values(str(row.get("stability_underperformance_driver", "")))
        ]
        no_trade_benchmark_returns = [
            value
            for value in (_float_or_none(row.get("stability_buy_hold_return_pct")) for row in no_trade_rows)
            if value is not None and value > 0
        ]
        failed_reason_counts: Counter[str] = Counter()
        driver_counts: Counter[str] = Counter()
        negative_window_tokens: list[str] = []
        counter_source_rows = negative_rows if counted_rows else rows
        for row in counter_source_rows:
            failed_reasons = _split_semicolon_values(str(row.get("stability_failed_reason", "")))
            if not failed_reasons and counted_rows:
                failed_reasons = ["negative_or_unclassified"]
            failed_reason_counts.update(failed_reasons)
            driver = str(row.get("stability_underperformance_driver", "")).strip()
            if driver:
                driver_counts.update(_split_semicolon_values(driver))
            if row not in negative_rows:
                continue
            as_of_date = str(row.get("as_of_date", "")).strip()
            window_name = str(row.get("stability_window", "")).strip()
            window_start = str(row.get("stability_window_start", "")).strip()
            window_end = str(row.get("stability_window_end", "")).strip()
            window_token = ":".join(value for value in [as_of_date, window_name] if value)
            if window_start or window_end:
                window_token = f"{window_token}({window_start}..{window_end})"
            if window_token:
                negative_window_tokens.append(window_token)

        counted_count = len(counted_rows)
        negative_count = len(negative_rows)
        negative_ratio = negative_count / counted_count if counted_count else None
        dominant_failed_reason = failed_reason_counts.most_common(1)[0][0] if failed_reason_counts else ""
        if counted_count == 0:
            diagnostic = "no_counted_stability_windows"
            next_action = "Regenerate stability diagnostics with enough train history before changing gates."
        elif low_positive_ratio_decisions and negative_count > 0:
            diagnostic = "low_positive_ratio_due_to_negative_stability_windows"
            next_action = (
                "Inspect negative stability windows and symbol/path-drift reports before loosening gates."
            )
        elif low_positive_ratio_decisions:
            diagnostic = "low_positive_ratio_without_negative_window_evidence"
            next_action = "Check candidate scoring inputs and train-decision path diagnostics."
        elif len(eligible_decisions) == len(decision_dates) and decision_dates:
            diagnostic = "eligible_direct_alpha_candidate"
            next_action = "Preserve gate behavior; no direct-alpha ineligibility action needed."
        else:
            diagnostic = "direct_alpha_stability_summary"
            next_action = "Review rejection and stability counters before candidate design."

        summary_rows.append(
            {
                "scenario": scenario,
                "walk_forward_preset": walk_forward_preset,
                "category": category,
                "candidate_name": candidate_name,
                "candidate_rank": candidate_rank,
                "train_decision_count": str(len(decision_dates)),
                "eligible_decision_count": str(len(eligible_decisions)),
                "low_positive_ratio_decision_count": str(len(low_positive_ratio_decisions)),
                "counted_subwindow_count": str(counted_count),
                "positive_subwindow_count": str(len(positive_rows)),
                "negative_subwindow_count": str(negative_count),
                "negative_subwindow_ratio": _format_optional_float(negative_ratio),
                "no_trade_subwindow_count": str(len(no_trade_rows)),
                "no_trade_benchmark_positive_count": str(len(no_trade_benchmark_returns)),
                "no_trade_total_benchmark_return_pct": _format_optional_float(
                    sum(no_trade_benchmark_returns) if no_trade_benchmark_returns else None
                ),
                "no_trade_avg_benchmark_return_pct": _format_optional_float(
                    mean(no_trade_benchmark_returns) if no_trade_benchmark_returns else None
                ),
                "candidate_positive_ratio_min": _format_optional_float(min(positive_ratios) if positive_ratios else None),
                "candidate_positive_ratio_max": _format_optional_float(max(positive_ratios) if positive_ratios else None),
                "candidate_positive_ratio_median": _format_optional_float(median(positive_ratios) if positive_ratios else None),
                "avg_stability_excess_return_pct": _format_optional_float(mean(excess_values) if excess_values else None),
                "worst_stability_excess_return_pct": _format_optional_float(min(excess_values) if excess_values else None),
                "dominant_failed_reason": dominant_failed_reason,
                "failed_reason_counts": _format_counter_counts(failed_reason_counts),
                "underperformance_driver_counts": _format_counter_counts(driver_counts),
                "negative_stability_windows": ";".join(negative_window_tokens),
                "diagnostic": diagnostic,
                "next_action": next_action,
            }
        )
    return summary_rows


def save_monthly_train_stability_summary(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_TRAIN_STABILITY_SUMMARY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MONTHLY_TRAIN_STABILITY_SUMMARY_COLUMNS})
    return len(rows)


def analyze_monthly_train_stability_symbol_attribution(
    stability_rows: list[dict[str, Any]],
    symbol_candles: dict[str, list[Candle]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stability in stability_rows:
        if str(stability.get("subwindow_counted_flag", "")).strip().lower() != "true":
            continue
        selected_symbols = _split_semicolon_values(str(stability.get("stability_selected_symbols", "")))
        traded_symbols = _split_semicolon_values(str(stability.get("stability_traded_symbols", "")))
        selected_set = set(selected_symbols)
        traded_set = set(traded_symbols)
        symbols = sorted(selected_set | traded_set)
        if not symbols:
            continue
        start = str(stability.get("stability_window_start", "")).strip()
        end = str(stability.get("stability_window_end", "")).strip()
        symbol_returns = dict(_period_symbol_returns(symbol_candles, start=start, end=end))
        selected_weight = 1 / len(selected_symbols) if selected_symbols else 0.0
        traded_weight = 1 / len(traded_symbols) if traded_symbols else 0.0
        train_symbol_count = _safe_int(stability.get("train_symbols"), default=0)
        benchmark_weight = 1 / train_symbol_count if train_symbol_count > 0 else 0.0
        for symbol in symbols:
            in_selected = symbol in selected_set
            in_traded = symbol in traded_set
            symbol_return = symbol_returns.get(symbol)
            selected_contribution = symbol_return * selected_weight if symbol_return is not None and in_selected else 0.0
            traded_contribution = symbol_return * traded_weight if symbol_return is not None and in_traded else 0.0
            benchmark_contribution = symbol_return * benchmark_weight if symbol_return is not None else None
            selected_vs_benchmark = (
                selected_contribution - benchmark_contribution
                if benchmark_contribution is not None
                else None
            )
            traded_vs_selected = traded_contribution - selected_contribution
            rows.append(
                {
                    "scenario": stability.get("scenario", ""),
                    "walk_forward_preset": stability.get("walk_forward_preset", ""),
                    "as_of_date": stability.get("as_of_date", ""),
                    "signal_date": stability.get("signal_date", ""),
                    "category": stability.get("category", ""),
                    "decision_mode": stability.get("decision_mode", ""),
                    "alpha_block_reason": stability.get("alpha_block_reason", ""),
                    "candidate_rejection_reasons": stability.get("candidate_rejection_reasons", ""),
                    "candidate_positive_ratio": stability.get("candidate_positive_ratio", ""),
                    "stability_window_start": start,
                    "stability_window_end": end,
                    "stability_excess_return_pct": stability.get("stability_excess_return_pct", ""),
                    "stability_trade_count": stability.get("stability_trade_count", ""),
                    "stability_failed_reason": stability.get("stability_failed_reason", ""),
                    "stability_underperformance_driver": stability.get("stability_underperformance_driver", ""),
                    "symbol": symbol,
                    "stability_symbol_role": _stability_symbol_role(
                        in_selected=in_selected,
                        in_traded=in_traded,
                    ),
                    "in_stability_selected": str(in_selected).lower(),
                    "in_stability_traded": str(in_traded).lower(),
                    "symbol_return_pct": _format_optional_float(symbol_return),
                    "selected_weight": _format_optional_float(selected_weight if in_selected else 0.0),
                    "traded_weight": _format_optional_float(traded_weight if in_traded else 0.0),
                    "benchmark_weight": _format_optional_float(benchmark_weight),
                    "selected_contribution_pct": _format_optional_float(selected_contribution),
                    "traded_contribution_pct": _format_optional_float(traded_contribution),
                    "benchmark_contribution_pct": _format_optional_float(benchmark_contribution),
                    "selected_vs_benchmark_contribution_delta_pct": _format_optional_float(selected_vs_benchmark),
                    "traded_vs_selected_contribution_delta_pct": _format_optional_float(traded_vs_selected),
                    "selected_symbol_count": len(selected_symbols),
                    "traded_symbol_count": len(traded_symbols),
                    "train_symbols": stability.get("train_symbols", ""),
                    "raw_symbols": stability.get("raw_symbols", ""),
                    "universe_symbols": stability.get("universe_symbols", ""),
                    "pit_symbols": stability.get("pit_symbols", ""),
                    "liquid_symbols": stability.get("liquid_symbols", ""),
                    "liquidity_removed": stability.get("liquidity_removed", ""),
                    "train_coverage_removed": stability.get("train_coverage_removed", ""),
                }
            )
    return rows


def save_monthly_train_stability_symbol_attribution(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_TRAIN_STABILITY_SYMBOL_ATTRIBUTION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: row.get(column, "")
                    for column in MONTHLY_TRAIN_STABILITY_SYMBOL_ATTRIBUTION_COLUMNS
                }
            )
    return len(rows)


def analyze_monthly_train_stability_path_drift_experiments(
    stability_rows: list[dict[str, Any]],
    symbol_attribution_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    symbol_rows_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in symbol_attribution_rows:
        key = (
            str(row.get("scenario", "")).strip(),
            str(row.get("as_of_date", "")).strip(),
            str(row.get("stability_window_start", "")).strip(),
            str(row.get("stability_window_end", "")).strip(),
        )
        if all(key):
            symbol_rows_by_key.setdefault(key, []).append(row)

    rows: list[dict[str, Any]] = []
    for stability in stability_rows:
        if str(stability.get("subwindow_counted_flag", "")).strip().lower() != "true":
            continue
        key = (
            str(stability.get("scenario", "")).strip(),
            str(stability.get("as_of_date", "")).strip(),
            str(stability.get("stability_window_start", "")).strip(),
            str(stability.get("stability_window_end", "")).strip(),
        )
        symbol_rows = symbol_rows_by_key.get(key, [])
        if not symbol_rows:
            continue

        actual_traded = _sum_numeric_column(symbol_rows, "traded_contribution_pct")
        selected_snapshot = _sum_numeric_column(symbol_rows, "selected_contribution_pct")
        benchmark = _sum_numeric_column(symbol_rows, "benchmark_contribution_pct")
        selected_not_traded = [
            row
            for row in symbol_rows
            if str(row.get("stability_symbol_role", "")).strip() == "selected_not_traded"
        ]
        traded_not_selected = [
            row
            for row in symbol_rows
            if str(row.get("stability_symbol_role", "")).strip() == "traded_not_selected"
        ]
        selected_and_traded = [
            row
            for row in symbol_rows
            if str(row.get("stability_symbol_role", "")).strip() == "selected_and_traded"
        ]
        selected_not_traded_contribution = _sum_numeric_column(selected_not_traded, "selected_contribution_pct")
        traded_not_selected_contribution = _sum_numeric_column(traded_not_selected, "traded_contribution_pct")
        path_drift_delta = actual_traded - selected_snapshot
        target_persistence_delta = selected_snapshot - actual_traded
        target_persistence_candidate = target_persistence_delta > 0 and bool(selected_not_traded)
        slower_rebalance_candidate = (
            target_persistence_candidate
            and bool(traded_not_selected)
            and str(stability.get("stability_underperformance_driver", "")).strip()
            == "holding_path_differs_from_selection_snapshot"
        )
        delayed_entry_candidate = bool(traded_not_selected) and traded_not_selected_contribution < 0
        recommendation = _path_drift_experiment_recommendation(
            target_persistence_candidate=target_persistence_candidate,
            slower_rebalance_candidate=slower_rebalance_candidate,
            delayed_entry_candidate=delayed_entry_candidate,
            selected_not_traded_contribution=selected_not_traded_contribution,
            traded_not_selected_contribution=traded_not_selected_contribution,
        )
        rows.append(
            {
                "scenario": stability.get("scenario", ""),
                "walk_forward_preset": stability.get("walk_forward_preset", ""),
                "as_of_date": stability.get("as_of_date", ""),
                "signal_date": stability.get("signal_date", ""),
                "category": stability.get("category", ""),
                "decision_mode": stability.get("decision_mode", ""),
                "alpha_block_reason": stability.get("alpha_block_reason", ""),
                "candidate_rejection_reasons": stability.get("candidate_rejection_reasons", ""),
                "candidate_positive_ratio": stability.get("candidate_positive_ratio", ""),
                "stability_window_start": stability.get("stability_window_start", ""),
                "stability_window_end": stability.get("stability_window_end", ""),
                "stability_excess_return_pct": stability.get("stability_excess_return_pct", ""),
                "stability_trade_count": stability.get("stability_trade_count", ""),
                "stability_failed_reason": stability.get("stability_failed_reason", ""),
                "stability_underperformance_driver": stability.get("stability_underperformance_driver", ""),
                "experiment_family": "path_drift_reduction",
                "paper_only": "true",
                "actual_traded_contribution_pct": _format_optional_float(actual_traded),
                "selected_snapshot_contribution_pct": _format_optional_float(selected_snapshot),
                "benchmark_contribution_pct": _format_optional_float(benchmark),
                "path_drift_delta_pct": _format_optional_float(path_drift_delta),
                "estimated_target_persistence_delta_pct": _format_optional_float(target_persistence_delta),
                "selected_not_traded_count": len(selected_not_traded),
                "traded_not_selected_count": len(traded_not_selected),
                "selected_and_traded_count": len(selected_and_traded),
                "selected_not_traded_contribution_pct": _format_optional_float(selected_not_traded_contribution),
                "traded_not_selected_contribution_pct": _format_optional_float(traded_not_selected_contribution),
                "target_persistence_candidate": str(target_persistence_candidate).lower(),
                "slower_rebalance_candidate": str(slower_rebalance_candidate).lower(),
                "delayed_entry_candidate": str(delayed_entry_candidate).lower(),
                "experiment_recommendation": recommendation,
                "candidate_status": "paper_only_needs_full_validation",
                "risk_note": (
                    "Diagnostic estimate only; do not change live behavior or loosen train gates "
                    "without full walk-forward validation."
                ),
            }
        )
    return rows


def save_monthly_train_stability_path_drift_experiments(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_TRAIN_STABILITY_PATH_DRIFT_EXPERIMENT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: row.get(column, "")
                    for column in MONTHLY_TRAIN_STABILITY_PATH_DRIFT_EXPERIMENT_COLUMNS
                }
            )
    return len(rows)


def _monthly_train_decision_path_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
    initial_cash: float,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
    min_trade_value: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = replace(config, presets=(preset,), train_start=case.train_start)
        result = run_monthly_rebalance_backtest(
            symbol_candles,
            start=case.train_start,
            end=case.train_end,
            config=preset_config,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate,
            min_trade_value=min_trade_value,
        )
        decision_count = len(result.decisions)
        alpha_ratio = (
            sum(1 for decision in result.decisions if decision.mode == "alpha") / decision_count
            if decision_count
            else 0.0
        )
        outer_summary = {
            "outer_train_total_return_pct": _format_optional_float(result.total_return_pct),
            "outer_train_buy_hold_return_pct": _format_optional_float(result.buy_hold_return_pct),
            "outer_train_excess_return_pct": _format_optional_float(result.excess_return_pct),
            "outer_train_max_drawdown_pct": _format_optional_float(result.max_drawdown_pct),
            "outer_train_trade_count": result.trade_count,
            "outer_train_decision_count": decision_count,
            "outer_train_alpha_ratio": _format_optional_float(alpha_ratio),
        }
        for decision in result.decisions:
            evidence = _monthly_train_decision_evidence(
                symbol_candles,
                as_of_date=decision.as_of_date,
                config=preset_config,
            )
            decision_reason = decision.reason
            if (
                str(evidence.get("filter_error", "")).strip() == "no_train_symbols"
                and decision_reason.startswith("decision_error:")
            ):
                decision_reason = "no_train_symbols"
            target_exposure = sum(weight for weight in decision.target_weights.values() if weight > 0)
            row = {
                "scenario": case.name,
                "category": case.category,
                "walk_forward_preset": preset,
                "as_of_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "decision_mode": decision.mode,
                "decision_selected_preset": decision.selected_preset,
                "decision_reason": decision_reason,
                "alpha_block_reason": _monthly_alpha_block_reason(decision, evidence),
                "decision_family": _monthly_decision_family(decision.mode),
                "target_symbol_count": len(decision.target_weights),
                "target_symbols": ";".join(sorted(decision.target_weights)),
                "target_exposure": _format_optional_float(target_exposure),
                "cash_weight": _format_optional_float(max(0.0, 1.0 - target_exposure)),
                **evidence,
                **outer_summary,
            }
            rows.append(row)
    return rows


def _monthly_train_stability_windows_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
    initial_cash: float,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
    min_trade_value: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = replace(config, presets=(preset,), train_start=case.train_start)
        result = run_monthly_rebalance_backtest(
            symbol_candles,
            start=case.train_start,
            end=case.train_end,
            config=preset_config,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            tax_rate=tax_rate,
            slippage_rate=slippage_rate,
            min_trade_value=min_trade_value,
        )
        for decision in result.decisions:
            decision_evidence = _monthly_train_decision_evidence(
                symbol_candles,
                as_of_date=decision.as_of_date,
                config=preset_config,
            )
            for stability in _monthly_train_stability_window_evidence(
                symbol_candles,
                as_of_date=decision.as_of_date,
                config=preset_config,
            ):
                rows.append(
                    {
                        "scenario": case.name,
                        "category": case.category,
                        "walk_forward_preset": preset,
                        "as_of_date": decision.as_of_date,
                        "signal_date": decision.signal_date,
                        "decision_mode": decision.mode,
                        "decision_selected_preset": decision.selected_preset,
                        "decision_reason": decision.reason,
                        "alpha_block_reason": _monthly_alpha_block_reason(decision, decision_evidence),
                        "prior_breadth": decision_evidence.get("prior_breadth", ""),
                        "fallback_breadth_threshold": decision_evidence.get("fallback_breadth_threshold", ""),
                        "market_beta_breadth_threshold": decision_evidence.get("market_beta_breadth_threshold", ""),
                        "trend_scale": decision_evidence.get("trend_scale", ""),
                        "volatility_scale": decision_evidence.get("volatility_scale", ""),
                        "liquidity_scale": decision_evidence.get("liquidity_scale", ""),
                        "exposure_scale": decision_evidence.get("exposure_scale", ""),
                        "direct_candidate_count": decision_evidence.get("direct_candidate_count", ""),
                        "eligible_direct_candidate_count": decision_evidence.get("eligible_direct_candidate_count", ""),
                        "best_direct_preset": decision_evidence.get("best_direct_preset", ""),
                        "best_direct_excess_return_pct": decision_evidence.get("best_direct_excess_return_pct", ""),
                        "best_direct_train_positive_ratio": decision_evidence.get(
                            "best_direct_train_positive_ratio",
                            "",
                        ),
                        **stability,
                    }
                )
    return rows


def _monthly_train_stability_window_evidence(
    symbol_candles: dict[str, list[Candle]],
    *,
    as_of_date: str,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    raw_symbol_count = len(symbol_candles)
    try:
        signal_date = latest_signal_date(symbol_candles, as_of_date=as_of_date)
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=signal_date,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=signal_date,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=signal_date,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        inner_train_start = config.train_start or _default_train_start(signal_date, config.train_years)
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=inner_train_start,
            end=signal_date,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
        counts = {
            "raw_symbols": raw_symbol_count,
            "universe_symbols": len(universe_candles),
            "pit_symbols": len(point_in_time_candles),
            "liquid_symbols": len(decision_candles),
            "train_symbols": len(train_candles),
            "universe_removed": max(0, raw_symbol_count - len(universe_candles)),
            "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
            "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
            "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
            "filter_error": "",
        }
        if not train_candles:
            return [
                _empty_monthly_train_stability_window_row(
                    as_of_date=as_of_date,
                    inner_train_start=inner_train_start,
                    inner_train_end=signal_date,
                    reason="no_train_symbols",
                    counts=counts,
                )
            ]
        preset_configs = _monthly_preset_configs(config)
        candidate_rows = _train_candidate_rows(
            decision_candles,
            train_candles=train_candles,
            train_start=inner_train_start,
            train_end=signal_date,
            preset_configs=preset_configs,
            min_rows_per_window=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
            train_stability_years=config.train_stability_years,
        )
        rows: list[dict[str, Any]] = []
        for candidate_rank, candidate in enumerate(candidate_rows, start=1):
            preset = str(candidate.get("preset", ""))
            preset_config = preset_configs[preset]
            candidate_reasons = _monthly_train_candidate_rejection_reasons(candidate, config)
            candidate_positive_ratio = candidate.get("train_positive_ratio", "")
            candidate_summary = {
                "inner_train_start": inner_train_start,
                "inner_train_end": signal_date,
                "preset": preset,
                "train_decision_as_of": as_of_date,
                "candidate_name": preset,
                "candidate_rank": str(candidate_rank),
                "candidate_total_return_pct": candidate.get("total_return_pct", ""),
                "candidate_buy_hold_return_pct": candidate.get("buy_hold_return_pct", ""),
                "candidate_excess_return_pct": candidate.get("excess_return_pct", ""),
                "candidate_max_drawdown_pct": candidate.get("max_drawdown_pct", ""),
                "candidate_trade_count": candidate.get("trades", ""),
                "candidate_train_subwindows": candidate.get("train_subwindows", ""),
                "candidate_train_positive_subwindows": candidate.get("train_positive_subwindows", ""),
                "candidate_train_positive_ratio": candidate_positive_ratio,
                "candidate_positive_ratio": candidate_positive_ratio,
                "candidate_train_avg_subwindow_excess_pct": candidate.get("train_avg_subwindow_excess_pct", ""),
                "candidate_train_worst_subwindow_excess_pct": candidate.get("train_worst_subwindow_excess_pct", ""),
                "candidate_rejection_reasons": ";".join(candidate_reasons) if candidate_reasons else "eligible",
                "candidate_eligible": "false" if candidate_reasons else "true",
            }
            stability_windows = list(generate_train_stability_windows(
                inner_train_start,
                signal_date,
                stability_years=config.train_stability_years,
            ))
            for window_index, window in enumerate(stability_windows, start=1):
                sub_candles = slice_asof_symbol_candles(
                    decision_candles,
                    start=window.train_start,
                    end=window.train_end,
                    min_rows=config.min_rows_per_window,
                    start_grace_days=config.start_grace_days,
                )
                row = {
                    **candidate_summary,
                    "stability_window": window.name,
                    "stability_start": window.train_start,
                    "stability_end": window.train_end,
                    "stability_window_index": window_index,
                    "stability_window_start": window.train_start,
                    "stability_window_end": window.train_end,
                    "stability_window_days": _date_span_days(window.train_start, window.train_end),
                    **counts,
                }
                if not sub_candles:
                    rows.append(
                        {
                            **row,
                            "subwindow_counted_flag": "false",
                            "subwindow_symbol_count": 0,
                            "subwindow_total_return_pct": "",
                            "subwindow_buy_hold_return_pct": "",
                            "subwindow_excess_return_pct": "",
                            "subwindow_max_drawdown_pct": "",
                            "subwindow_trade_count": "",
                            "subwindow_positive_flag": "false",
                            "subwindow_rejection_reasons": "no_subwindow_symbols",
                            "stability_total_return_pct": "",
                            "stability_buy_hold_return_pct": "",
                            "stability_excess_return_pct": "",
                            "stability_max_drawdown_pct": "",
                            "stability_trade_count": "",
                            "stability_positive": "false",
                            "stability_failed_reason": "no_subwindow_symbols",
                            "stability_selected_symbol_count": 0,
                            "stability_selected_symbols": "",
                            "stability_benchmark_avg_return_pct": "",
                            "stability_benchmark_median_return_pct": "",
                            "stability_selected_avg_return_pct": "",
                            "stability_selected_median_return_pct": "",
                            "stability_selected_vs_benchmark_avg_return_delta_pct": "",
                            "stability_selected_underperformed_benchmark": "",
                            "stability_traded_symbol_count": 0,
                            "stability_traded_symbols": "",
                            "stability_selected_not_traded_symbols": "",
                            "stability_traded_not_selected_symbols": "",
                            "stability_underperformance_driver": "no_subwindow_symbols",
                        }
                    )
                    continue
                sub_result = run_momentum_rotation_backtest(sub_candles, preset_config)
                sub_reasons: list[str] = []
                if sub_result.excess_return_pct <= 0:
                    sub_reasons.append("nonpositive_excess")
                if sub_result.trade_count <= 0:
                    sub_reasons.append("no_trades")
                positive = sub_result.excess_return_pct > 0 and sub_result.trade_count > 0
                subwindow_total_return = round(sub_result.total_return_pct, 4)
                subwindow_buy_hold_return = round(sub_result.buy_hold_return_pct, 4)
                subwindow_excess_return = round(sub_result.excess_return_pct, 4)
                subwindow_max_drawdown = round(sub_result.max_drawdown_pct, 4)
                failed_reason = ";".join(sub_reasons) if sub_reasons else ""
                selection_context = _stability_selection_path_context(
                    sub_candles,
                    train_start=window.train_start,
                    train_end=window.train_end,
                    preset_config=preset_config,
                    sub_result=sub_result,
                )
                rows.append(
                    {
                        **row,
                        "subwindow_counted_flag": "true",
                        "subwindow_symbol_count": len(sub_candles),
                        "subwindow_total_return_pct": subwindow_total_return,
                        "subwindow_buy_hold_return_pct": subwindow_buy_hold_return,
                        "subwindow_excess_return_pct": subwindow_excess_return,
                        "subwindow_max_drawdown_pct": subwindow_max_drawdown,
                        "subwindow_trade_count": sub_result.trade_count,
                        "subwindow_positive_flag": "true" if positive else "false",
                        "subwindow_rejection_reasons": failed_reason,
                        "stability_total_return_pct": subwindow_total_return,
                        "stability_buy_hold_return_pct": subwindow_buy_hold_return,
                        "stability_excess_return_pct": subwindow_excess_return,
                        "stability_max_drawdown_pct": subwindow_max_drawdown,
                        "stability_trade_count": sub_result.trade_count,
                        "stability_positive": "true" if positive else "false",
                        "stability_failed_reason": failed_reason,
                        **selection_context,
                    }
                )
        return rows
    except ValueError as exc:
        return [
            {
                "inner_train_start": "",
                "inner_train_end": "",
                "stability_window": "",
                "stability_start": "",
                "stability_end": "",
                "preset": "",
                "subwindow_counted_flag": "false",
                "subwindow_symbol_count": "",
                "subwindow_total_return_pct": "",
                "subwindow_buy_hold_return_pct": "",
                "subwindow_excess_return_pct": "",
                "subwindow_max_drawdown_pct": "",
                "subwindow_trade_count": "",
                "subwindow_positive_flag": "false",
                "subwindow_rejection_reasons": "",
                "candidate_total_return_pct": "",
                "candidate_buy_hold_return_pct": "",
                "candidate_excess_return_pct": "",
                "candidate_max_drawdown_pct": "",
                "candidate_trade_count": "",
                "candidate_train_subwindows": "",
                "candidate_train_positive_subwindows": "",
                "candidate_train_positive_ratio": "",
                "candidate_train_avg_subwindow_excess_pct": "",
                "candidate_train_worst_subwindow_excess_pct": "",
                "candidate_rejection_reasons": "",
                "raw_symbols": raw_symbol_count,
                "universe_symbols": "",
                "pit_symbols": "",
                "liquid_symbols": "",
                "train_symbols": "",
                "universe_removed": "",
                "pit_filter_removed": "",
                "liquidity_removed": "",
                "train_coverage_removed": "",
                "filter_error": _diagnostic_token(str(exc)),
                "train_decision_as_of": as_of_date,
                "candidate_name": "",
                "candidate_rank": "",
                "candidate_positive_ratio": "",
                "candidate_eligible": "false",
                "stability_window_index": "",
                "stability_window_start": "",
                "stability_window_end": "",
                "stability_window_days": "",
                "stability_total_return_pct": "",
                "stability_buy_hold_return_pct": "",
                "stability_excess_return_pct": "",
                "stability_max_drawdown_pct": "",
                "stability_trade_count": "",
                "stability_positive": "false",
                "stability_failed_reason": _diagnostic_token(str(exc)),
                "stability_selected_symbol_count": 0,
                "stability_selected_symbols": "",
                "stability_benchmark_avg_return_pct": "",
                "stability_benchmark_median_return_pct": "",
                "stability_selected_avg_return_pct": "",
                "stability_selected_median_return_pct": "",
                "stability_selected_vs_benchmark_avg_return_delta_pct": "",
                "stability_selected_underperformed_benchmark": "",
                "stability_traded_symbol_count": 0,
                "stability_traded_symbols": "",
                "stability_selected_not_traded_symbols": "",
                "stability_traded_not_selected_symbols": "",
                "stability_underperformance_driver": _diagnostic_token(str(exc)),
            }
        ]


def _stability_selection_path_context(
    symbol_candles: dict[str, list[Candle]],
    *,
    train_start: str,
    train_end: str,
    preset_config: MomentumRotationConfig,
    sub_result: Any,
) -> dict[str, Any]:
    symbol_returns = dict(_period_symbol_returns(symbol_candles, start=train_start, end=train_end))
    benchmark_returns = list(symbol_returns.values())
    benchmark_avg = mean(benchmark_returns) if benchmark_returns else None
    benchmark_median = median(benchmark_returns) if benchmark_returns else None
    try:
        selected_symbols = rank_momentum_targets(symbol_candles, signal_date=train_end, config=preset_config)
    except ValueError:
        selected_symbols = []
    selected_returns = [
        symbol_returns[symbol]
        for symbol in selected_symbols
        if symbol in symbol_returns
    ]
    selected_avg = mean(selected_returns) if selected_returns else None
    selected_median = median(selected_returns) if selected_returns else None
    selected_delta = (
        selected_avg - benchmark_avg
        if selected_avg is not None and benchmark_avg is not None
        else None
    )
    selected_underperformed = (
        selected_delta < 0
        if selected_delta is not None
        else None
    )
    traded_symbols = sorted({str(trade.symbol) for trade in getattr(sub_result, "trades", [])})
    selected_set = set(selected_symbols)
    traded_set = set(traded_symbols)
    selected_not_traded = sorted(selected_set - traded_set)
    traded_not_selected = sorted(traded_set - selected_set)
    drivers: list[str] = []
    if getattr(sub_result, "trade_count", 0) <= 0:
        drivers.append("no_trades")
    if selected_underperformed:
        drivers.append("selected_underperformed_benchmark")
    if benchmark_avg is not None and benchmark_avg > 0 and (selected_avg is None or selected_avg <= 0):
        drivers.append("benchmark_positive_selection_nonpositive")
    if selected_not_traded or traded_not_selected:
        drivers.append("holding_path_differs_from_selection_snapshot")
    if not drivers and getattr(sub_result, "excess_return_pct", 0) <= 0:
        drivers.append("candidate_path_underperformed_benchmark")
    return {
        "stability_selected_symbol_count": len(selected_symbols),
        "stability_selected_symbols": ";".join(selected_symbols),
        "stability_benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
        "stability_benchmark_median_return_pct": _format_optional_float(benchmark_median),
        "stability_selected_avg_return_pct": _format_optional_float(selected_avg),
        "stability_selected_median_return_pct": _format_optional_float(selected_median),
        "stability_selected_vs_benchmark_avg_return_delta_pct": _format_optional_float(selected_delta),
        "stability_selected_underperformed_benchmark": (
            ""
            if selected_underperformed is None
            else "true"
            if selected_underperformed
            else "false"
        ),
        "stability_traded_symbol_count": len(traded_symbols),
        "stability_traded_symbols": ";".join(traded_symbols),
        "stability_selected_not_traded_symbols": ";".join(selected_not_traded),
        "stability_traded_not_selected_symbols": ";".join(traded_not_selected),
        "stability_underperformance_driver": ";".join(drivers) if drivers else "positive_or_no_issue",
    }


def _empty_monthly_train_stability_window_row(
    *,
    as_of_date: str,
    inner_train_start: str,
    inner_train_end: str,
    reason: str,
    counts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "inner_train_start": inner_train_start,
        "inner_train_end": inner_train_end,
        "stability_window": "",
        "stability_start": "",
        "stability_end": "",
        "preset": "",
        "subwindow_counted_flag": "false",
        "subwindow_symbol_count": "",
        "subwindow_total_return_pct": "",
        "subwindow_buy_hold_return_pct": "",
        "subwindow_excess_return_pct": "",
        "subwindow_max_drawdown_pct": "",
        "subwindow_trade_count": "",
        "subwindow_positive_flag": "false",
        "subwindow_rejection_reasons": reason,
        "candidate_total_return_pct": "",
        "candidate_buy_hold_return_pct": "",
        "candidate_excess_return_pct": "",
        "candidate_max_drawdown_pct": "",
        "candidate_trade_count": "",
        "candidate_train_subwindows": "",
        "candidate_train_positive_subwindows": "",
        "candidate_train_positive_ratio": "",
        "candidate_train_avg_subwindow_excess_pct": "",
        "candidate_train_worst_subwindow_excess_pct": "",
        "candidate_rejection_reasons": reason,
        "train_decision_as_of": as_of_date,
        "candidate_name": "",
        "candidate_rank": "",
        "candidate_positive_ratio": "",
        "candidate_eligible": "false",
        "stability_window_index": "",
        "stability_window_start": "",
        "stability_window_end": "",
        "stability_window_days": "",
        "stability_total_return_pct": "",
        "stability_buy_hold_return_pct": "",
        "stability_excess_return_pct": "",
        "stability_max_drawdown_pct": "",
        "stability_trade_count": "",
        "stability_positive": "false",
        "stability_failed_reason": reason,
        "stability_selected_symbol_count": 0,
        "stability_selected_symbols": "",
        "stability_benchmark_avg_return_pct": "",
        "stability_benchmark_median_return_pct": "",
        "stability_selected_avg_return_pct": "",
        "stability_selected_median_return_pct": "",
        "stability_selected_vs_benchmark_avg_return_delta_pct": "",
        "stability_selected_underperformed_benchmark": "",
        "stability_traded_symbol_count": 0,
        "stability_traded_symbols": "",
        "stability_selected_not_traded_symbols": "",
        "stability_traded_not_selected_symbols": "",
        "stability_underperformance_driver": reason,
        **counts,
    }


def _stability_symbol_role(*, in_selected: bool, in_traded: bool) -> str:
    if in_selected and in_traded:
        return "selected_and_traded"
    if in_selected:
        return "selected_not_traded"
    if in_traded:
        return "traded_not_selected"
    return "context_only"


def _sum_numeric_column(rows: list[dict[str, Any]], column: str) -> float:
    values = [
        _float_or_none(row.get(column))
        for row in rows
    ]
    return sum(value for value in values if value is not None)


def _path_drift_experiment_recommendation(
    *,
    target_persistence_candidate: bool,
    slower_rebalance_candidate: bool,
    delayed_entry_candidate: bool,
    selected_not_traded_contribution: float,
    traded_not_selected_contribution: float,
) -> str:
    if (
        target_persistence_candidate
        and selected_not_traded_contribution > max(traded_not_selected_contribution, 0.0)
    ):
        return "test_stricter_target_persistence"
    if delayed_entry_candidate:
        return "test_delayed_entry_filter"
    if slower_rebalance_candidate:
        return "test_slower_rebalance_cadence"
    return "monitor_path_drift"


def _monthly_train_decision_evidence(
    symbol_candles: dict[str, list[Candle]],
    *,
    as_of_date: str,
    config: MonthlyRebalanceConfig,
) -> dict[str, Any]:
    raw_symbol_count = len(symbol_candles)
    try:
        signal_date = latest_signal_date(symbol_candles, as_of_date=as_of_date)
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=signal_date,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=signal_date,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=signal_date,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        inner_train_start = config.train_start or _default_train_start(signal_date, config.train_years)
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=inner_train_start,
            end=signal_date,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
        if not train_candles:
            return {
                "inner_train_start": inner_train_start,
                "inner_train_end": signal_date,
                "prior_breadth": "",
                "fallback_breadth_threshold": _format_optional_float(config.fallback_breadth_threshold),
                "market_beta_breadth_threshold": _format_optional_float(config.market_beta_breadth_threshold),
                "trend_scale": "",
                "volatility_scale": "",
                "liquidity_scale": "",
                "exposure_scale": "",
                "direct_candidate_count": 0,
                "eligible_direct_candidate_count": 0,
                "direct_candidate_scores": "",
                "direct_candidate_rejection_reasons": "no_train_symbols=1",
                "best_direct_preset": "",
                "best_direct_score": "",
                "best_direct_excess_return_pct": "",
                "best_direct_trade_count": "",
                "best_direct_train_positive_ratio": "",
                "raw_symbols": raw_symbol_count,
                "universe_symbols": len(universe_candles),
                "pit_symbols": len(point_in_time_candles),
                "liquid_symbols": len(decision_candles),
                "train_symbols": 0,
                "universe_removed": max(0, raw_symbol_count - len(universe_candles)),
                "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
                "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
                "train_coverage_removed": len(decision_candles),
                "filter_error": "no_train_symbols",
            }
        preset_configs = _monthly_preset_configs(config)
        direct_rows = _train_candidate_rows(
            decision_candles,
            train_candles=train_candles,
            train_start=inner_train_start,
            train_end=signal_date,
            preset_configs=preset_configs,
            min_rows_per_window=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
            train_stability_years=config.train_stability_years,
        )
        prior_breadth = market_breadth_before_date(
            decision_candles,
            before_date=as_of_date,
            trend_days=config.fallback_breadth_days,
        )
        trend_scale = market_trend_exposure_scale(
            decision_candles,
            before_date=as_of_date,
            lookback_days=config.market_trend_filter_days,
            min_return_pct=config.market_trend_min_return_pct,
            risk_scale=config.market_trend_risk_scale,
        )
        volatility_scale = market_volatility_exposure_scale(
            decision_candles,
            before_date=as_of_date,
            lookback_days=config.market_volatility_filter_days,
            target_volatility_pct=config.market_volatility_target_pct,
            min_scale=config.market_volatility_min_scale,
        )
        liquidity_scale = liquidity_universe_exposure_scale(
            top_n=config.point_in_time_liquidity_top_n,
            reference_top_n=config.liquidity_risk_reference_top_n,
            min_scale=config.liquidity_risk_min_scale,
            min_top_n=config.liquidity_risk_min_top_n,
        )
        eligible_rows = [
            row for row in direct_rows
            if not _monthly_train_candidate_rejection_reasons(row, config)
        ]
        best_row = max(direct_rows, key=_monthly_validation_train_score, default={})
        return {
            "inner_train_start": inner_train_start,
            "inner_train_end": signal_date,
            "prior_breadth": _format_optional_float(prior_breadth),
            "fallback_breadth_threshold": _format_optional_float(config.fallback_breadth_threshold),
            "market_beta_breadth_threshold": _format_optional_float(config.market_beta_breadth_threshold),
            "trend_scale": _format_optional_float(trend_scale),
            "volatility_scale": _format_optional_float(volatility_scale),
            "liquidity_scale": _format_optional_float(liquidity_scale),
            "exposure_scale": _format_optional_float(trend_scale * volatility_scale * liquidity_scale),
            "direct_candidate_count": len(direct_rows),
            "eligible_direct_candidate_count": len(eligible_rows),
            "direct_candidate_scores": _format_monthly_validation_train_scores(direct_rows),
            "direct_candidate_rejection_reasons": _format_train_candidate_rejection_summary(direct_rows, config),
            "best_direct_preset": best_row.get("preset", ""),
            "best_direct_score": _format_optional_float(
                _monthly_validation_train_score(best_row) if best_row else None
            ),
            "best_direct_excess_return_pct": _format_optional_float(
                _float_or_none(best_row.get("excess_return_pct")) if best_row else None
            ),
            "best_direct_trade_count": best_row.get("trades", ""),
            "best_direct_train_positive_ratio": _format_optional_float(
                _float_or_none(best_row.get("train_positive_ratio")) if best_row else None
            ),
            "raw_symbols": raw_symbol_count,
            "universe_symbols": len(universe_candles),
            "pit_symbols": len(point_in_time_candles),
            "liquid_symbols": len(decision_candles),
            "train_symbols": len(train_candles),
            "universe_removed": max(0, raw_symbol_count - len(universe_candles)),
            "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
            "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
            "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
            "filter_error": "",
        }
    except ValueError as exc:
        return {
            "inner_train_start": "",
            "inner_train_end": "",
            "prior_breadth": "",
            "fallback_breadth_threshold": _format_optional_float(config.fallback_breadth_threshold),
            "market_beta_breadth_threshold": _format_optional_float(config.market_beta_breadth_threshold),
            "trend_scale": "",
            "volatility_scale": "",
            "liquidity_scale": "",
            "exposure_scale": "",
            "direct_candidate_count": 0,
            "eligible_direct_candidate_count": 0,
            "direct_candidate_scores": "",
            "direct_candidate_rejection_reasons": "",
            "best_direct_preset": "",
            "best_direct_score": "",
            "best_direct_excess_return_pct": "",
            "best_direct_trade_count": "",
            "best_direct_train_positive_ratio": "",
            "raw_symbols": raw_symbol_count,
            "universe_symbols": "",
            "pit_symbols": "",
            "liquid_symbols": "",
            "train_symbols": "",
            "universe_removed": "",
            "pit_filter_removed": "",
            "liquidity_removed": "",
            "train_coverage_removed": "",
            "filter_error": _diagnostic_token(str(exc)),
        }


def _monthly_train_candidate_rejection_reasons(
    row: dict[str, Any],
    config: MonthlyRebalanceConfig,
) -> list[str]:
    reasons: list[str] = []
    excess = _float_or_none(row.get("excess_return_pct"))
    trades = int(float(row.get("trades", 0) or 0))
    positive_ratio = _float_or_none(row.get("train_positive_ratio"))
    if excess is None or excess <= 0:
        reasons.append("nonpositive_excess")
    if trades < config.min_train_trades:
        reasons.append("insufficient_trades")
    if positive_ratio is not None and positive_ratio < config.min_train_positive_ratio:
        reasons.append("low_positive_ratio")
    return reasons


def _format_train_candidate_rejection_summary(
    rows: list[dict[str, Any]],
    config: MonthlyRebalanceConfig,
) -> str:
    counts: Counter[str] = Counter()
    for row in rows:
        reasons = _monthly_train_candidate_rejection_reasons(row, config)
        if not reasons:
            counts["eligible"] += 1
        for reason in reasons:
            counts[reason] += 1
    return ";".join(f"{reason}={counts[reason]}" for reason in sorted(counts))


def _monthly_decision_family(mode: str) -> str:
    if mode == "alpha":
        return "alpha"
    if mode in {"market_beta", "market_beta_proxy"}:
        return "market_beta"
    if mode == "cash":
        return "cash"
    return "other"


def _monthly_alpha_block_reason(decision: MonthlyDecision, evidence: dict[str, Any]) -> str:
    if decision.mode == "alpha":
        return "selected_alpha"
    filter_error = str(evidence.get("filter_error", "")).strip()
    if filter_error == "no_train_symbols":
        return "no_train_symbols"
    if filter_error:
        return "candidate_filter_error"
    eligible_count = int(float(evidence.get("eligible_direct_candidate_count", 0) or 0))
    if eligible_count <= 0:
        return "no_eligible_direct_candidate"
    if "weak_train" in decision.reason:
        return "weak_breadth_and_weak_train_average"
    if "no_ranked_targets" in decision.reason:
        return "no_ranked_targets"
    if "drawdown" in decision.reason:
        return "risk_overlay_scaled_or_blocked_alpha"
    return "fallback_after_candidate_selection"


def _monthly_direct_alpha_selection_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []

    counts = {
        "raw_symbols": len(symbol_candles),
        "universe_symbols": len(universe_candles),
        "pit_symbols": len(point_in_time_candles),
        "liquid_symbols": len(decision_candles),
        "train_symbols": len(train_candles),
        "universe_removed": max(0, len(symbol_candles) - len(universe_candles)),
        "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
        "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
        "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
    }
    symbol_returns = dict(_period_symbol_returns(train_candles, start=case.train_start, end=case.train_end))
    return_values = list(symbol_returns.values())
    benchmark_avg = mean(return_values) if return_values else None
    benchmark_median = median(return_values) if return_values else None
    benchmark_weight = 1 / len(train_candles) if train_candles else 0.0

    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = _monthly_preset_config_for_name(config, preset)
        candidate_result = run_momentum_rotation_backtest(train_candles, preset_config)
        candidate_buy_count = sum(1 for trade in candidate_result.trades if trade.action == "BUY")
        candidate_sell_count = sum(1 for trade in candidate_result.trades if trade.action == "SELL")
        candidate_unique_symbols = len({trade.symbol for trade in candidate_result.trades})
        selected_symbols = rank_momentum_targets(train_candles, signal_date=case.train_end, config=preset_config)
        selected_set = set(selected_symbols)
        selected_weights = {
            symbol: 1 / len(selected_symbols)
            for symbol in selected_symbols
        } if selected_symbols else {}
        rank_info = _direct_alpha_rank_info(train_candles, signal_date=case.train_end, config=preset_config)
        for symbol in sorted(train_candles):
            info = rank_info.get(symbol, {})
            selected = symbol in selected_set
            rejection_reason = "" if selected else str(info.get("rejection_reason", "") or "below_selected_rank")
            rows.append(
                {
                    "scenario": case.name,
                    "category": case.category,
                    "train_start": case.train_start,
                    "train_end": case.train_end,
                    "preset": preset,
                    "symbol": symbol,
                    "selection_status": "selected" if selected else "rejected",
                    "selection_rank": selected_symbols.index(symbol) + 1 if selected else "",
                    "selection_weight": _format_optional_float(selected_weights.get(symbol)),
                    "rejection_reason": rejection_reason,
                    "momentum_score_pct": _format_optional_float(info.get("momentum_score_pct")),
                    "average_trading_value": _format_optional_float(info.get("average_trading_value")),
                    "symbol_train_return_pct": _format_optional_float(symbol_returns.get(symbol)),
                    "benchmark_weight": _format_optional_float(benchmark_weight),
                    "benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
                    "benchmark_median_return_pct": _format_optional_float(benchmark_median),
                    "candidate_total_return_pct": _format_optional_float(candidate_result.total_return_pct),
                    "candidate_buy_hold_return_pct": _format_optional_float(candidate_result.buy_hold_return_pct),
                    "candidate_excess_return_pct": _format_optional_float(candidate_result.excess_return_pct),
                    "candidate_max_drawdown_pct": _format_optional_float(candidate_result.max_drawdown_pct),
                    "candidate_trade_count": candidate_result.trade_count,
                    "candidate_buy_count": candidate_buy_count,
                    "candidate_sell_count": candidate_sell_count,
                    "candidate_unique_traded_symbols": candidate_unique_symbols,
                    **counts,
                }
            )
    return rows


def _monthly_direct_alpha_holding_path_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []

    counts = {
        "raw_symbols": len(symbol_candles),
        "universe_symbols": len(universe_candles),
        "pit_symbols": len(point_in_time_candles),
        "liquid_symbols": len(decision_candles),
        "train_symbols": len(train_candles),
        "universe_removed": max(0, len(symbol_candles) - len(universe_candles)),
        "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
        "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
        "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
    }
    benchmark_symbols = sorted(train_candles)
    symbol_returns = dict(_period_symbol_returns(train_candles, start=case.train_start, end=case.train_end))
    return_values = list(symbol_returns.values())
    benchmark_avg = mean(return_values) if return_values else None
    benchmark_median = median(return_values) if return_values else None

    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = _monthly_preset_config_for_name(config, preset)
        candidate_result = run_momentum_rotation_backtest(train_candles, preset_config)
        candidate_buy_count = sum(1 for trade in candidate_result.trades if trade.action == "BUY")
        candidate_sell_count = sum(1 for trade in candidate_result.trades if trade.action == "SELL")
        candidate_unique_symbols = len({trade.symbol for trade in candidate_result.trades})
        train_end_selected = rank_momentum_targets(train_candles, signal_date=case.train_end, config=preset_config)
        train_end_selected_set = set(train_end_selected)
        holdings: set[str] = set()
        trades_by_date: dict[str, list[Any]] = {}
        for trade in candidate_result.trades:
            trades_by_date.setdefault(trade.date, []).append(trade)
        scheduled_rebalance_dates = set(_direct_alpha_scheduled_rebalance_dates(train_candles, preset_config))
        snapshot_dates = sorted(scheduled_rebalance_dates | set(trades_by_date))

        for rebalance_date in snapshot_dates:
            day_trades = trades_by_date.get(rebalance_date, [])
            entered: list[str] = []
            exited: list[str] = []
            for trade in day_trades:
                if trade.action == "SELL":
                    holdings.discard(trade.symbol)
                    exited.append(trade.symbol)
                elif trade.action == "BUY":
                    holdings.add(trade.symbol)
                    entered.append(trade.symbol)
            held_symbols = sorted(holdings)
            overlap = sorted(set(held_symbols) & train_end_selected_set)
            holding_not_in_snapshot = sorted(set(held_symbols) - train_end_selected_set)
            missing_from_holdings = sorted(train_end_selected_set - set(held_symbols))
            is_final_liquidation = (
                bool(day_trades)
                and not entered
                and any(str(trade.reason) == "final_close" for trade in day_trades)
                and not held_symbols
            )
            row = {
                "scenario": case.name,
                "preset": preset,
                "rebalance_date": rebalance_date,
                "category": case.category,
                "train_start": case.train_start,
                "train_end": case.train_end,
                "event_type": (
                    "liquidation"
                    if is_final_liquidation
                    else "rebalance_no_trade"
                    if not day_trades
                    else "rebalance"
                ),
                "holding_count": len(held_symbols),
                "held_symbols": ";".join(held_symbols),
                "held_weights": _format_equal_symbol_weights(held_symbols),
                "entered_symbols": ";".join(sorted(entered)),
                "exited_symbols": ";".join(sorted(exited)),
                "train_end_selected_symbols": ";".join(train_end_selected),
                "snapshot_overlap_count": len(overlap),
                "snapshot_overlap_symbols": ";".join(overlap),
                "holding_not_in_train_end_snapshot": ";".join(holding_not_in_snapshot),
                "train_end_selected_missing_from_holdings": ";".join(missing_from_holdings),
                "benchmark_symbol_count": len(benchmark_symbols),
                "benchmark_symbols": ";".join(benchmark_symbols),
                "benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
                "benchmark_median_return_pct": _format_optional_float(benchmark_median),
                "candidate_total_return_pct": _format_optional_float(candidate_result.total_return_pct),
                "candidate_buy_hold_return_pct": _format_optional_float(candidate_result.buy_hold_return_pct),
                "candidate_excess_return_pct": _format_optional_float(candidate_result.excess_return_pct),
                "candidate_max_drawdown_pct": _format_optional_float(candidate_result.max_drawdown_pct),
                "candidate_trade_count": candidate_result.trade_count,
                "candidate_buy_count": candidate_buy_count,
                "candidate_sell_count": candidate_sell_count,
                "candidate_unique_traded_symbols": candidate_unique_symbols,
                "rebalance_trade_count": len(day_trades),
                "rebalance_buy_count": len(entered),
                "rebalance_sell_count": len(exited),
                **counts,
            }
            rows.append(row)
    return rows


def _monthly_direct_alpha_path_drift_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []

    counts = {
        "raw_symbols": len(symbol_candles),
        "universe_symbols": len(universe_candles),
        "pit_symbols": len(point_in_time_candles),
        "liquid_symbols": len(decision_candles),
        "train_symbols": len(train_candles),
        "universe_removed": max(0, len(symbol_candles) - len(universe_candles)),
        "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
        "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
        "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
    }
    benchmark_symbols = sorted(train_candles)
    benchmark_weight = 1 / len(benchmark_symbols) if benchmark_symbols else 0.0
    symbol_returns = dict(_period_symbol_returns(train_candles, start=case.train_start, end=case.train_end))
    return_values = list(symbol_returns.values())
    benchmark_avg = mean(return_values) if return_values else None
    benchmark_median = median(return_values) if return_values else None

    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = _monthly_preset_config_for_name(config, preset)
        candidate_result = run_momentum_rotation_backtest(train_candles, preset_config)
        train_end_selected = rank_momentum_targets(train_candles, signal_date=case.train_end, config=preset_config)
        train_end_selected_set = set(train_end_selected)
        snapshot_weight = 1 / len(train_end_selected) if train_end_selected else 0.0
        holdings: set[str] = set()
        trades_by_date: dict[str, list[Any]] = {}
        first_trade_date = ""
        for trade in candidate_result.trades:
            trades_by_date.setdefault(trade.date, []).append(trade)
            if trade.action == "BUY" and not first_trade_date:
                first_trade_date = trade.date
        first_trade_delay_days = (
            _date_span_days(case.train_start, first_trade_date) - 1
            if first_trade_date
            else ""
        )
        scheduled_rebalance_dates = set(_direct_alpha_scheduled_rebalance_dates(train_candles, preset_config))
        snapshot_dates = sorted(scheduled_rebalance_dates | set(trades_by_date))
        previous_active_rebalance_date = ""
        active_rebalance_index = 0

        for rebalance_date in snapshot_dates:
            day_trades = trades_by_date.get(rebalance_date, [])
            entered: list[str] = []
            for trade in day_trades:
                if trade.action == "SELL":
                    holdings.discard(trade.symbol)
                elif trade.action == "BUY":
                    holdings.add(trade.symbol)
                    entered.append(trade.symbol)
            held_symbols = sorted(holdings)
            if not held_symbols:
                continue
            event_type = "rebalance" if day_trades else "rebalance_no_trade"
            active_rebalance_index += 1
            days_since_previous = (
                _date_span_days(previous_active_rebalance_date, rebalance_date) - 1
                if previous_active_rebalance_date
                else ""
            )
            held_set = set(held_symbols)
            actual_weight = 1 / len(held_symbols) if held_symbols else 0.0
            overlap = sorted(held_set & train_end_selected_set)
            row_base = {
                "scenario": case.name,
                "preset": preset,
                "rebalance_date": rebalance_date,
                "category": case.category,
                "train_start": case.train_start,
                "train_end": case.train_end,
                "event_type": event_type,
                "active_rebalance_index": active_rebalance_index,
                "previous_active_rebalance_date": previous_active_rebalance_date,
                "days_since_previous_active_rebalance": days_since_previous,
                "first_trade_date": first_trade_date,
                "first_trade_delay_days": first_trade_delay_days,
                "holding_count": len(held_symbols),
                "held_symbols": ";".join(held_symbols),
                "train_end_selected_symbols": ";".join(train_end_selected),
                "snapshot_overlap_count": len(overlap),
                "candidate_excess_return_pct": _format_optional_float(candidate_result.excess_return_pct),
                "benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
                "benchmark_median_return_pct": _format_optional_float(benchmark_median),
                **counts,
            }
            for symbol in benchmark_symbols:
                in_actual = symbol in held_set
                in_snapshot = symbol in train_end_selected_set
                symbol_return = symbol_returns.get(symbol)
                actual_symbol_weight = actual_weight if in_actual else 0.0
                snapshot_symbol_weight = snapshot_weight if in_snapshot else 0.0
                actual_contribution = (
                    actual_symbol_weight * symbol_return
                    if symbol_return is not None
                    else None
                )
                snapshot_contribution = (
                    snapshot_symbol_weight * symbol_return
                    if symbol_return is not None
                    else None
                )
                benchmark_contribution = (
                    benchmark_weight * symbol_return
                    if symbol_return is not None
                    else None
                )
                contribution_delta = (
                    actual_contribution - benchmark_contribution
                    if actual_contribution is not None and benchmark_contribution is not None
                    else None
                )
                actual_vs_snapshot_delta = (
                    actual_contribution - snapshot_contribution
                    if actual_contribution is not None and snapshot_contribution is not None
                    else None
                )
                role, gap_reason = _direct_alpha_path_drift_role(
                    in_actual_holdings=in_actual,
                    in_train_end_selected_snapshot=in_snapshot,
                )
                rows.append(
                    {
                        **row_base,
                        "symbol": symbol,
                        "path_role": role,
                        "path_gap_reason": gap_reason,
                        "in_actual_holdings": "true" if in_actual else "false",
                        "in_train_end_selected_snapshot": "true" if in_snapshot else "false",
                        "actual_weight": _format_optional_float(actual_symbol_weight),
                        "snapshot_weight": _format_optional_float(snapshot_symbol_weight),
                        "benchmark_weight": _format_optional_float(benchmark_weight),
                        "symbol_train_return_pct": _format_optional_float(symbol_return),
                        "actual_contribution_pct": _format_optional_float(actual_contribution),
                        "snapshot_contribution_pct": _format_optional_float(snapshot_contribution),
                        "benchmark_contribution_pct": _format_optional_float(benchmark_contribution),
                        "contribution_delta_pct": _format_optional_float(contribution_delta),
                        "actual_vs_snapshot_contribution_delta_pct": _format_optional_float(actual_vs_snapshot_delta),
                    }
                )
            previous_active_rebalance_date = rebalance_date
    return rows


def _monthly_direct_alpha_timing_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []

    counts = {
        "raw_symbols": len(symbol_candles),
        "universe_symbols": len(universe_candles),
        "pit_symbols": len(point_in_time_candles),
        "liquid_symbols": len(decision_candles),
        "train_symbols": len(train_candles),
        "universe_removed": max(0, len(symbol_candles) - len(universe_candles)),
        "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
        "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
        "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
    }
    return_values = list(dict(_period_symbol_returns(train_candles, start=case.train_start, end=case.train_end)).values())
    benchmark_avg = mean(return_values) if return_values else None
    benchmark_median = median(return_values) if return_values else None
    all_dates = sorted({candle.date for candles in train_candles.values() for candle in candles})
    date_index = {value: index for index, value in enumerate(all_dates)}
    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = _monthly_preset_config_for_name(config, preset)
        candidate_result = run_momentum_rotation_backtest(train_candles, preset_config)
        train_end_selected = rank_momentum_targets(train_candles, signal_date=case.train_end, config=preset_config)
        train_end_selected_set = set(train_end_selected)
        scheduled_dates = _direct_alpha_scheduled_rebalance_dates(train_candles, preset_config)
        target_by_rebalance_date: dict[str, list[str]] = {}
        signal_by_rebalance_date: dict[str, str] = {}
        for rebalance_date in scheduled_dates:
            signal_date = _direct_alpha_signal_date_for_rebalance(all_dates, rebalance_date)
            signal_by_rebalance_date[rebalance_date] = signal_date
            target_by_rebalance_date[rebalance_date] = (
                rank_momentum_targets(train_candles, signal_date=signal_date, config=preset_config)
                if signal_date
                else []
            )

        trades_by_date: dict[str, list[Any]] = {}
        first_trade_date = ""
        for trade in candidate_result.trades:
            trades_by_date.setdefault(trade.date, []).append(trade)
            if trade.action == "BUY" and not first_trade_date:
                first_trade_date = trade.date
        first_trade_delay_days = (
            _date_span_days(case.train_start, first_trade_date) - 1
            if first_trade_date
            else ""
        )

        holdings: set[str] = set()
        previous_scheduled_date = ""
        for scheduled_index, rebalance_date in enumerate(scheduled_dates, start=1):
            for trade in trades_by_date.get(rebalance_date, []):
                if trade.action == "SELL":
                    holdings.discard(trade.symbol)
                elif trade.action == "BUY":
                    holdings.add(trade.symbol)
            scheduled_targets = target_by_rebalance_date.get(rebalance_date, [])
            scheduled_target_set = set(scheduled_targets)
            held_set = set(holdings)
            available_snapshot = sorted(
                symbol for symbol in train_end_selected
                if symbol in train_candles and date_index.get(rebalance_date) is not None
                and any(candle.date == rebalance_date for candle in train_candles[symbol])
            )
            unavailable_snapshot = sorted(train_end_selected_set - set(available_snapshot))
            snapshot_target_overlap = sorted(train_end_selected_set & scheduled_target_set)
            snapshot_actual_overlap = sorted(train_end_selected_set & held_set)
            snapshot_missing_targets = sorted(train_end_selected_set - scheduled_target_set)
            snapshot_missing_holdings = sorted(train_end_selected_set - held_set)
            scheduled_not_snapshot = sorted(scheduled_target_set - train_end_selected_set)
            previous_targets = (
                target_by_rebalance_date.get(scheduled_dates[scheduled_index - 2], [])
                if scheduled_index > 1
                else []
            )
            next_targets = (
                target_by_rebalance_date.get(scheduled_dates[scheduled_index], [])
                if scheduled_index < len(scheduled_dates)
                else []
            )
            previous_overlap = len(train_end_selected_set & set(previous_targets))
            current_overlap = len(snapshot_target_overlap)
            next_overlap = len(train_end_selected_set & set(next_targets))
            best_offset, best_overlap = _direct_alpha_best_timing_overlap(
                previous_overlap=previous_overlap,
                current_overlap=current_overlap,
                next_overlap=next_overlap,
            )
            timing_diagnostic = _direct_alpha_timing_diagnostic(
                best_offset=best_offset,
                current_overlap=current_overlap,
                best_overlap=best_overlap,
                scheduled_targets=scheduled_targets,
                snapshot_missing_holdings=snapshot_missing_holdings,
            )
            missed_reason = _direct_alpha_missed_snapshot_reason(
                train_end_selected=train_end_selected,
                available_snapshot=set(available_snapshot),
                scheduled_targets=scheduled_target_set,
                held_symbols=held_set,
            )
            rows.append(
                {
                    "scenario": case.name,
                    "preset": preset,
                    "scheduled_rebalance_date": rebalance_date,
                    "category": case.category,
                    "train_start": case.train_start,
                    "train_end": case.train_end,
                    "scheduled_rebalance_index": scheduled_index,
                    "signal_date": signal_by_rebalance_date.get(rebalance_date, ""),
                    "previous_scheduled_rebalance_date": previous_scheduled_date,
                    "days_since_previous_scheduled_rebalance": (
                        _date_span_days(previous_scheduled_date, rebalance_date) - 1
                        if previous_scheduled_date
                        else ""
                    ),
                    "first_trade_date": first_trade_date,
                    "first_trade_delay_days": first_trade_delay_days,
                    "train_end_selected_count": len(train_end_selected),
                    "train_end_selected_symbols": ";".join(train_end_selected),
                    "scheduled_target_count": len(scheduled_targets),
                    "scheduled_target_symbols": ";".join(scheduled_targets),
                    "actual_held_count": len(holdings),
                    "actual_held_symbols": ";".join(sorted(holdings)),
                    "snapshot_target_overlap_count": current_overlap,
                    "snapshot_target_overlap_symbols": ";".join(snapshot_target_overlap),
                    "snapshot_actual_overlap_count": len(snapshot_actual_overlap),
                    "snapshot_actual_overlap_symbols": ";".join(snapshot_actual_overlap),
                    "snapshot_missing_from_scheduled_targets": ";".join(snapshot_missing_targets),
                    "snapshot_missing_from_actual_holdings": ";".join(snapshot_missing_holdings),
                    "scheduled_targets_not_in_snapshot": ";".join(scheduled_not_snapshot),
                    "available_snapshot_symbols": ";".join(available_snapshot),
                    "unavailable_snapshot_symbols": ";".join(unavailable_snapshot),
                    "missed_snapshot_reason": missed_reason,
                    "previous_target_overlap_count": previous_overlap,
                    "current_target_overlap_count": current_overlap,
                    "next_target_overlap_count": next_overlap,
                    "best_timing_offset": best_offset,
                    "best_timing_overlap_count": best_overlap,
                    "timing_diagnostic": timing_diagnostic,
                    "candidate_excess_return_pct": _format_optional_float(candidate_result.excess_return_pct),
                    "benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
                    "benchmark_median_return_pct": _format_optional_float(benchmark_median),
                    **counts,
                }
            )
            previous_scheduled_date = rebalance_date
    return rows


def _monthly_direct_alpha_rank_drift_for_case(
    symbol_candles: dict[str, list[Candle]],
    *,
    case: MonthlyValidationCase,
    config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    try:
        universe_candles = filter_symbol_candles_by_universe(
            symbol_candles,
            config.point_in_time_universe,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
        )
        point_in_time_candles = select_point_in_time_universe(
            universe_candles,
            signal_date=case.train_end,
            min_history_days=config.point_in_time_min_history_days,
            min_reference_price=config.point_in_time_min_reference_price,
            max_trailing_return_pct=config.point_in_time_max_trailing_return_pct,
            trailing_return_days=config.point_in_time_trailing_return_days,
        )
        decision_candles = (
            select_liquid_universe(
                point_in_time_candles,
                signal_date=case.train_end,
                top_n=config.point_in_time_liquidity_top_n,
                window_days=config.point_in_time_liquidity_window_days,
            )
            if config.point_in_time_liquidity_top_n > 0
            else point_in_time_candles
        )
        train_candles = slice_asof_symbol_candles(
            decision_candles,
            start=case.train_start,
            end=case.train_end,
            min_rows=config.min_rows_per_window,
            start_grace_days=config.start_grace_days,
        )
    except ValueError:
        return []
    if not train_candles:
        return []

    counts = {
        "raw_symbols": len(symbol_candles),
        "universe_symbols": len(universe_candles),
        "pit_symbols": len(point_in_time_candles),
        "liquid_symbols": len(decision_candles),
        "train_symbols": len(train_candles),
        "universe_removed": max(0, len(symbol_candles) - len(universe_candles)),
        "pit_filter_removed": max(0, len(universe_candles) - len(point_in_time_candles)),
        "liquidity_removed": max(0, len(point_in_time_candles) - len(decision_candles)),
        "train_coverage_removed": max(0, len(decision_candles) - len(train_candles)),
    }
    return_values = list(dict(_period_symbol_returns(train_candles, start=case.train_start, end=case.train_end)).values())
    benchmark_avg = mean(return_values) if return_values else None
    benchmark_median = median(return_values) if return_values else None
    all_dates = sorted({candle.date for candles in train_candles.values() for candle in candles})
    rows: list[dict[str, Any]] = []
    for preset in config.presets:
        preset_config = _monthly_preset_config_for_name(config, preset)
        candidate_result = run_momentum_rotation_backtest(train_candles, preset_config)
        train_end_selected = rank_momentum_targets(train_candles, signal_date=case.train_end, config=preset_config)
        train_end_selected_set = set(train_end_selected)
        train_end_target_rank = {symbol: index for index, symbol in enumerate(train_end_selected, start=1)}
        _, _, _, train_end_trend_days = _direct_alpha_market_breadth_profile(
            train_candles,
            signal_date=case.train_end,
            config=preset_config,
        )
        train_end_rank_info = _direct_alpha_rank_info(
            train_candles,
            signal_date=case.train_end,
            config=preset_config,
            trend_filter_days=train_end_trend_days,
        )
        scheduled_dates = _direct_alpha_scheduled_rebalance_dates(train_candles, preset_config)

        trades_by_date: dict[str, list[Any]] = {}
        for trade in candidate_result.trades:
            trades_by_date.setdefault(trade.date, []).append(trade)

        holdings: set[str] = set()
        for scheduled_index, rebalance_date in enumerate(scheduled_dates, start=1):
            for trade in trades_by_date.get(rebalance_date, []):
                if trade.action == "SELL":
                    holdings.discard(trade.symbol)
                elif trade.action == "BUY":
                    holdings.add(trade.symbol)

            signal_date = _direct_alpha_signal_date_for_rebalance(all_dates, rebalance_date)
            scheduled_targets = (
                rank_momentum_targets(train_candles, signal_date=signal_date, config=preset_config)
                if signal_date
                else []
            )
            scheduled_target_set = set(scheduled_targets)
            scheduled_target_rank = {symbol: index for index, symbol in enumerate(scheduled_targets, start=1)}
            market_breadth, market_allows_entry, ranking_top_n, ranking_trend_days = (
                _direct_alpha_market_breadth_profile(train_candles, signal_date=signal_date, config=preset_config)
            )
            scheduled_rank_info = _direct_alpha_rank_info(
                train_candles,
                signal_date=signal_date,
                config=preset_config,
                trend_filter_days=ranking_trend_days,
            )
            held_set = set(holdings)
            row_symbols = sorted(train_end_selected_set | scheduled_target_set | held_set)
            snapshot_target_overlap = train_end_selected_set & scheduled_target_set
            snapshot_missing_targets = sorted(train_end_selected_set - scheduled_target_set)
            timing_diagnostic = _direct_alpha_timing_diagnostic(
                best_offset="current",
                current_overlap=len(snapshot_target_overlap),
                best_overlap=len(snapshot_target_overlap),
                scheduled_targets=scheduled_targets,
                snapshot_missing_holdings=snapshot_missing_targets,
            )

            for symbol in row_symbols:
                in_train_end = symbol in train_end_selected_set
                in_scheduled = symbol in scheduled_target_set
                in_actual = symbol in held_set
                train_info = train_end_rank_info.get(symbol, {})
                scheduled_info = scheduled_rank_info.get(symbol, {})
                train_rank = train_info.get("candidate_rank")
                scheduled_rank = scheduled_info.get("candidate_rank")
                train_momentum = _float_or_none(train_info.get("momentum_score_pct"))
                scheduled_momentum = _float_or_none(scheduled_info.get("momentum_score_pct"))
                rank_delta = (
                    int(scheduled_rank) - int(train_rank)
                    if train_rank is not None and scheduled_rank is not None
                    else ""
                )
                momentum_delta = (
                    scheduled_momentum - train_momentum
                    if train_momentum is not None and scheduled_momentum is not None
                    else None
                )
                scheduled_rejection_reason = (
                    ""
                    if in_scheduled
                    else str(scheduled_info.get("rejection_reason", "") or "not_ranked")
                )
                train_end_rejection_reason = (
                    ""
                    if in_train_end
                    else str(train_info.get("rejection_reason", "") or "not_ranked")
                )
                rows.append(
                    {
                        "scenario": case.name,
                        "preset": preset,
                        "scheduled_rebalance_date": rebalance_date,
                        "signal_date": signal_date,
                        "category": case.category,
                        "train_start": case.train_start,
                        "train_end": case.train_end,
                        "scheduled_rebalance_index": scheduled_index,
                        "symbol": symbol,
                        "symbol_role": _direct_alpha_rank_drift_symbol_role(
                            in_train_end_selected_snapshot=in_train_end,
                            in_scheduled_targets=in_scheduled,
                            in_actual_holdings=in_actual,
                        ),
                        "in_train_end_selected_snapshot": str(in_train_end).lower(),
                        "in_scheduled_targets": str(in_scheduled).lower(),
                        "in_actual_holdings": str(in_actual).lower(),
                        "train_end_rank": train_rank if train_rank is not None else "",
                        "scheduled_rank": scheduled_rank if scheduled_rank is not None else "",
                        "rank_delta": rank_delta,
                        "train_end_target_rank": train_end_target_rank.get(symbol, ""),
                        "scheduled_target_rank": scheduled_target_rank.get(symbol, ""),
                        "train_end_momentum_score_pct": _format_optional_float(train_momentum),
                        "scheduled_momentum_score_pct": _format_optional_float(scheduled_momentum),
                        "momentum_delta_pct": _format_optional_float(momentum_delta),
                        "train_end_rejection_reason": train_end_rejection_reason,
                        "scheduled_rejection_reason": scheduled_rejection_reason,
                        "train_end_average_trading_value": _format_optional_float(
                            train_info.get("average_trading_value")
                        ),
                        "scheduled_average_trading_value": _format_optional_float(
                            scheduled_info.get("average_trading_value")
                        ),
                        "market_breadth_at_signal": _format_optional_float(market_breadth),
                        "market_breadth_allows_entry": str(market_allows_entry).lower(),
                        "ranking_top_n_at_signal": ranking_top_n,
                        "ranking_trend_filter_days_at_signal": ranking_trend_days,
                        "train_end_selected_count": len(train_end_selected),
                        "scheduled_target_count": len(scheduled_targets),
                        "actual_held_count": len(holdings),
                        "train_end_selected_symbols": ";".join(train_end_selected),
                        "scheduled_target_symbols": ";".join(scheduled_targets),
                        "actual_held_symbols": ";".join(sorted(holdings)),
                        "snapshot_target_overlap_count": len(snapshot_target_overlap),
                        "drop_reason": _direct_alpha_rank_drift_drop_reason(
                            in_train_end_selected_snapshot=in_train_end,
                            in_scheduled_targets=in_scheduled,
                            scheduled_targets=scheduled_targets,
                            scheduled_rank=scheduled_rank,
                            scheduled_rejection_reason=scheduled_rejection_reason,
                        ),
                        "timing_diagnostic": timing_diagnostic,
                        "candidate_excess_return_pct": _format_optional_float(candidate_result.excess_return_pct),
                        "benchmark_avg_return_pct": _format_optional_float(benchmark_avg),
                        "benchmark_median_return_pct": _format_optional_float(benchmark_median),
                        **counts,
                    }
                )
    return rows


def _direct_alpha_signal_date_for_rebalance(dates: list[str], rebalance_date: str) -> str:
    try:
        index = dates.index(rebalance_date)
    except ValueError:
        return ""
    if index <= 0:
        return ""
    return dates[index - 1]


def _direct_alpha_best_timing_overlap(
    *,
    previous_overlap: int,
    current_overlap: int,
    next_overlap: int,
) -> tuple[str, int]:
    candidates = [
        ("current", current_overlap),
        ("previous", previous_overlap),
        ("next", next_overlap),
    ]
    return max(candidates, key=lambda item: (item[1], 1 if item[0] == "current" else 0))


def _direct_alpha_timing_diagnostic(
    *,
    best_offset: str,
    current_overlap: int,
    best_overlap: int,
    scheduled_targets: list[str],
    snapshot_missing_holdings: list[str],
) -> str:
    if not scheduled_targets:
        return "no_scheduled_targets"
    if best_offset != "current" and best_overlap > current_overlap:
        return f"{best_offset}_rebalance_has_better_snapshot_overlap"
    if snapshot_missing_holdings:
        return "current_timing_targets_differ_from_train_end_snapshot"
    return "current_timing_best"


def _direct_alpha_missed_snapshot_reason(
    *,
    train_end_selected: list[str],
    available_snapshot: set[str],
    scheduled_targets: set[str],
    held_symbols: set[str],
) -> str:
    counts: Counter[str] = Counter()
    for symbol in train_end_selected:
        if symbol in held_symbols:
            continue
        if symbol not in available_snapshot:
            counts["unavailable_on_rebalance"] += 1
        elif symbol not in scheduled_targets:
            counts["not_selected_on_rebalance_signal"] += 1
        else:
            counts["scheduled_target_not_held"] += 1
    if not counts:
        return "no_snapshot_miss"
    return ";".join(f"{reason}={counts[reason]}" for reason in sorted(counts))


def _direct_alpha_rank_drift_symbol_role(
    *,
    in_train_end_selected_snapshot: bool,
    in_scheduled_targets: bool,
    in_actual_holdings: bool,
) -> str:
    if in_train_end_selected_snapshot and in_scheduled_targets:
        return "both"
    if in_train_end_selected_snapshot:
        return "train_end_snapshot_only"
    if in_scheduled_targets:
        return "scheduled_target_only"
    if in_actual_holdings:
        return "actual_holding_only"
    return "context_only"


def _direct_alpha_rank_drift_drop_reason(
    *,
    in_train_end_selected_snapshot: bool,
    in_scheduled_targets: bool,
    scheduled_targets: list[str],
    scheduled_rank: Any,
    scheduled_rejection_reason: str,
) -> str:
    if in_train_end_selected_snapshot and in_scheduled_targets:
        return "still_selected"
    if in_scheduled_targets:
        return "entered_scheduled_targets"
    if not in_train_end_selected_snapshot:
        return "not_in_train_end_snapshot"
    if not scheduled_targets:
        return "no_scheduled_targets"
    if scheduled_rejection_reason == "below_selected_rank":
        return "rank_dropped_below_top_n"
    if scheduled_rejection_reason:
        return scheduled_rejection_reason
    if scheduled_rank not in (None, ""):
        return "rank_dropped_below_top_n"
    return "unranked_on_rebalance_signal"


def _direct_alpha_market_breadth_profile(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    config: MomentumRotationConfig,
) -> tuple[float | None, bool, int, int]:
    market_breadth = _direct_alpha_market_breadth_value(
        symbol_candles,
        signal_date=signal_date,
        trend_days=config.market_trend_filter_days,
    )
    if config.market_trend_filter_days <= 0 or config.market_breadth_threshold <= 0:
        allows_entry = True
    else:
        allows_entry = market_breadth is not None and market_breadth >= config.market_breadth_threshold
    if market_breadth is not None and market_breadth >= config.bull_breadth_threshold:
        return market_breadth, allows_entry, config.bull_top_n, config.bull_trend_filter_days
    return market_breadth, allows_entry, config.top_n, config.trend_filter_days


def _direct_alpha_market_breadth_value(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    trend_days: int,
) -> float | None:
    if not signal_date or trend_days <= 0:
        return None
    checks: list[bool] = []
    for candles in symbol_candles.values():
        sorted_candles = sorted(candles, key=lambda candle: candle.date)
        signal_index = next((index for index, candle in enumerate(sorted_candles) if candle.date == signal_date), None)
        if signal_index is None or signal_index + 1 < trend_days:
            continue
        trend_values = sorted_candles[signal_index - trend_days + 1 : signal_index + 1]
        trend_average = sum(candle.close for candle in trend_values) / len(trend_values)
        checks.append(sorted_candles[signal_index].close >= trend_average)
    if not checks:
        return None
    return sum(checks) / len(checks)


def _direct_alpha_path_drift_role(
    *,
    in_actual_holdings: bool,
    in_train_end_selected_snapshot: bool,
) -> tuple[str, str]:
    if in_actual_holdings and in_train_end_selected_snapshot:
        return "held_and_snapshot", "aligned"
    if in_actual_holdings:
        return "held_not_snapshot", "traded_outside_train_end_snapshot"
    if in_train_end_selected_snapshot:
        return "snapshot_missing_from_holdings", "selected_snapshot_missed"
    return "benchmark_only", "benchmark_symbol_not_held"


def _direct_alpha_scheduled_rebalance_dates(
    symbol_candles: dict[str, list[Candle]],
    config: MomentumRotationConfig,
) -> list[str]:
    dates = sorted({candle.date for candles in symbol_candles.values() for candle in candles})
    first_rebalance_index = config.lookback_days + 1
    if first_rebalance_index >= len(dates):
        return []
    return [
        dates[index]
        for index in range(first_rebalance_index, len(dates), config.rebalance_days)
    ]


def _direct_alpha_rank_info(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    config: MomentumRotationConfig,
    trend_filter_days: int | None = None,
) -> dict[str, dict[str, Any]]:
    rows: list[tuple[str, float]] = []
    info: dict[str, dict[str, Any]] = {}
    selected_trend_filter_days = config.trend_filter_days if trend_filter_days is None else trend_filter_days
    for symbol, candles in symbol_candles.items():
        sorted_candles = sorted(candles, key=lambda candle: candle.date)
        signal_index = next((index for index, candle in enumerate(sorted_candles) if candle.date == signal_date), None)
        if signal_index is None:
            info[symbol] = {"rejection_reason": "missing_signal_date"}
            continue
        lookback_index = signal_index - config.lookback_days
        if lookback_index < 0:
            info[symbol] = {"rejection_reason": "insufficient_lookback"}
            continue
        signal_close = sorted_candles[signal_index].close
        base_close = sorted_candles[lookback_index].close
        if base_close <= 0:
            info[symbol] = {"rejection_reason": "nonpositive_lookback_price"}
            continue
        momentum_pct = (signal_close / base_close - 1) * 100
        average_trading_value = _average_trading_value_for_signal(
            sorted_candles,
            signal_index=signal_index,
            window_days=config.liquidity_window_days,
        )
        symbol_info: dict[str, Any] = {
            "momentum_score_pct": momentum_pct,
            "average_trading_value": average_trading_value,
        }
        if config.require_positive_momentum and momentum_pct <= 0:
            symbol_info["rejection_reason"] = "nonpositive_momentum"
        elif config.max_lookback_return_pct > 0 and momentum_pct > config.max_lookback_return_pct:
            symbol_info["rejection_reason"] = "max_lookback_return"
        elif config.min_average_trading_value > 0 and (
            average_trading_value is None or average_trading_value < config.min_average_trading_value
        ):
            symbol_info["rejection_reason"] = "liquidity_threshold"
        elif selected_trend_filter_days > 0:
            if signal_index + 1 < selected_trend_filter_days:
                symbol_info["rejection_reason"] = "insufficient_trend_history"
            else:
                trend_values = sorted_candles[signal_index - selected_trend_filter_days + 1 : signal_index + 1]
                trend_average = sum(candle.close for candle in trend_values) / len(trend_values)
                if signal_close < trend_average:
                    symbol_info["rejection_reason"] = "trend_filter_failed"
        info[symbol] = symbol_info
        if not symbol_info.get("rejection_reason"):
            rows.append((symbol, momentum_pct))
    rows.sort(key=lambda row: row[1], reverse=True)
    for rank, (symbol, _) in enumerate(rows, start=1):
        info[symbol]["candidate_rank"] = rank
        info[symbol].setdefault("rejection_reason", "below_selected_rank")
    return info


def _average_trading_value_for_signal(
    candles: list[Candle],
    *,
    signal_index: int,
    window_days: int,
) -> float | None:
    if window_days <= 0 or signal_index + 1 < window_days:
        return None
    values = [candle.close * candle.volume for candle in candles[signal_index - window_days + 1 : signal_index + 1]]
    return sum(values) / len(values)


def analyze_monthly_validation_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for row in rows:
        required = _parse_bool(row.get("required", True))
        deployable = _parse_bool(row.get("deployable", False))
        if not required or deployable:
            continue
        diagnostics.append(_validation_failure_diagnostic(row))
    return diagnostics


def save_monthly_validation_failures(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_FAILURE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_FAILURE_COLUMNS})
    return len(rows)


def analyze_monthly_validation_remediation(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in failures:
        action = str(row.get("suggested_action", "")).strip() or "REVIEW_SCENARIO"
        grouped.setdefault(action, []).append(row)

    rows: list[dict[str, Any]] = []
    for action, action_rows in grouped.items():
        categories = _unique_join(str(row.get("category", "")).strip() for row in action_rows)
        scenarios = _unique_join(str(row.get("name", "")).strip() for row in action_rows)
        metrics = _unique_join(str(row.get("failed_metric", "")).strip() for row in action_rows)
        hints = _unique_join(
            part.strip()
            for row in action_rows
            for part in str(row.get("parameter_hints", "")).split(";")
        )
        worst_value = _worst_failure_metric_value(action_rows)
        blocked_count = sum(1 for row in action_rows if str(row.get("severity", "")).strip().upper() == "BLOCK")
        rows.append(
            {
                "priority": _remediation_priority(action, blocked_count),
                "suggested_action": action,
                "failure_count": len(action_rows),
                "blocked_count": blocked_count,
                "affected_categories": categories,
                "affected_scenarios": scenarios,
                "failed_metrics": metrics,
                "worst_metric_value": worst_value,
                "parameter_hints": hints,
                "next_experiment": _remediation_next_experiment(action),
            }
        )

    rows.sort(
        key=lambda row: (
            {"P0": 0, "P1": 1, "P2": 2}.get(str(row.get("priority", "P2")), 3),
            -int(row.get("failure_count", 0) or 0),
            str(row.get("suggested_action", "")),
        )
    )
    return rows


def save_monthly_validation_remediation(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_REMEDIATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_REMEDIATION_COLUMNS})
    return len(rows)


def build_monthly_validation_sweep_plan(
    remediation_rows: list[dict[str, Any]],
    *,
    base_config: MonthlyRebalanceConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_actions = {
        str(row.get("suggested_action", "")).strip(): row
        for row in remediation_rows
        if str(row.get("suggested_action", "")).strip()
    }

    weak_row = seen_actions.get("IMPROVE_WEAK_WINDOW_DEFENSE")
    if weak_row is not None:
        target_scenarios = str(weak_row.get("affected_scenarios", "")).strip()
        rows.extend(
            [
                _sweep_plan_row(
                    weak_row,
                    experiment_id="weak_defense_cash_05",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    cash_buffer_weight=0.05,
                    min_train_positive_ratio=max(base_config.min_train_positive_ratio, 0.55),
                    candidate_pool_size=min(base_config.candidate_pool_size, 5),
                    expected_effect="Reduce weak-window exposure while keeping enough breadth for rotation.",
                ),
                _sweep_plan_row(
                    weak_row,
                    experiment_id="weak_defense_cash_10",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    cash_buffer_weight=0.10,
                    min_train_positive_ratio=max(base_config.min_train_positive_ratio, 0.60),
                    candidate_pool_size=min(base_config.candidate_pool_size, 5),
                    expected_effect="Test a larger cash buffer for sideways and weak walk-forward windows.",
                ),
                _sweep_plan_row(
                    weak_row,
                    experiment_id="weak_defense_pool_03",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    cash_buffer_weight=0.05,
                    min_train_positive_ratio=max(base_config.min_train_positive_ratio, 0.60),
                    candidate_pool_size=min(base_config.candidate_pool_size, 3),
                    expected_effect="Test whether fewer candidates reduce churn in weak regimes.",
                ),
                _sweep_plan_row(
                    weak_row,
                    experiment_id="market_beta_proxy_cap_75",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    market_beta_proxy_max_exposure=0.75,
                    expected_effect=(
                        "Cap all fallback market-beta-proxy exposure to test broad beta de-risking."
                    ),
                ),
                _sweep_plan_row(
                    weak_row,
                    experiment_id="neutral_breadth_proxy_cap_50",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    market_beta_proxy_neutral_breadth_max_exposure=0.50,
                    expected_effect=(
                        "Cap fallback proxy only when breadth is neutral, preserving strong-breadth "
                        "proxy participation that prevented prior regressions."
                    ),
                ),
                _sweep_plan_row(
                    weak_row,
                    experiment_id="neutral_proxy_deep_guard_35",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    market_beta_proxy_neutral_breadth_max_exposure=0.50,
                    drawdown_guard_deep_trigger_pct=-20.0,
                    drawdown_guard_deep_scale=0.35,
                    expected_effect=(
                        "Retest the neutral-breadth proxy cap with an explicit deep drawdown guard "
                        "to preserve March-April drawdown buffer before full validation."
                    ),
                ),
            ]
        )

    drawdown_row = seen_actions.get("REDUCE_DRAWDOWN")
    if drawdown_row is not None:
        target_scenarios = str(drawdown_row.get("affected_scenarios", "")).strip()
        rows.extend(
            [
                _sweep_plan_row(
                    drawdown_row,
                    experiment_id="drawdown_guard_stronger",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    max_position_weight=min(base_config.max_position_weight, 0.10),
                    drawdown_guard_scale=min(base_config.drawdown_guard_scale, 0.50),
                    market_volatility_min_scale=max(base_config.market_volatility_min_scale, 0.50),
                    expected_effect="Reduce stress drawdown by capping single-name exposure and risk-off scaling.",
                ),
                _sweep_plan_row(
                    drawdown_row,
                    experiment_id="drawdown_guard_very_strict",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    max_position_weight=min(base_config.max_position_weight, 0.08),
                    drawdown_guard_scale=min(base_config.drawdown_guard_scale, 0.35),
                    market_volatility_min_scale=max(base_config.market_volatility_min_scale, 0.65),
                    expected_effect="Test a stricter drawdown overlay for stress scenarios that remain just beyond the hard block threshold.",
                ),
                _sweep_plan_row(
                    drawdown_row,
                    experiment_id="drawdown_cash_buffer_05",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    cash_buffer_weight=max(base_config.cash_buffer_weight, 0.05),
                    max_position_weight=min(base_config.max_position_weight, 0.10),
                    drawdown_guard_scale=min(base_config.drawdown_guard_scale, 0.50),
                    market_volatility_min_scale=max(base_config.market_volatility_min_scale, 0.50),
                    expected_effect="Test whether adding cash buffer to the drawdown overlay clears the stress drawdown gate.",
                ),
                _sweep_plan_row(
                    drawdown_row,
                    experiment_id="position_stop_12",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    position_trailing_stop_pct=-12.0,
                    expected_effect="Test a next-open per-position trailing stop to cap single-name drawdowns without selling at same-day closes.",
                ),
                _sweep_plan_row(
                    drawdown_row,
                    experiment_id="guarded_loss_position_stop_12",
                    target_scenarios=target_scenarios,
                    base_config=base_config,
                    position_trailing_stop_pct=-12.0,
                    position_trailing_stop_reason_contains="proxy_neutral_loss_guard_capped",
                    expected_effect=(
                        "Scope the next-open per-position stop to neutral loss-guard proxy "
                        "decisions so broad recovery-month proxy exposure is not stopped."
                    ),
                ),
            ]
        )

    if weak_row is not None and drawdown_row is not None:
        combo_targets = _unique_join(
            [
                *_split_semicolon_values(str(weak_row.get("affected_scenarios", ""))),
                *_split_semicolon_values(str(drawdown_row.get("affected_scenarios", ""))),
            ]
        )
        combo_row = {
            "priority": "P1",
            "suggested_action": "COMBINE_WEAK_DEFENSE_AND_DRAWDOWN",
        }
        rows.append(
            _sweep_plan_row(
                combo_row,
                experiment_id="weak_cash_10_position_stop_12",
                target_scenarios=combo_targets,
                base_config=base_config,
                cash_buffer_weight=0.10,
                min_train_positive_ratio=max(base_config.min_train_positive_ratio, 0.60),
                candidate_pool_size=min(base_config.candidate_pool_size, 5),
                position_trailing_stop_pct=-12.0,
                expected_effect="Combine the best weak-window cash buffer candidate with the per-position stop candidate and test whether failures improve without adding new target failures.",
            )
        )

    rejected_row = seen_actions.get("KEEP_TRAIN_WINDOW_REJECTED")
    if rejected_row is not None:
        rows.append(
            _sweep_plan_row(
                rejected_row,
                experiment_id="train_gate_keep_blocked",
                target_scenarios=str(rejected_row.get("affected_scenarios", "")).strip(),
                base_config=base_config,
                expected_effect="Keep this as a no-trade gate unless independent validation improves.",
                risk_note="Do not relax train-window rejection only to make deployment pass.",
            )
        )
    return rows


def save_monthly_validation_sweep_plan(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_SWEEP_PLAN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_SWEEP_PLAN_COLUMNS})
    return len(rows)


def filter_monthly_validation_sweep_plan(
    rows: list[dict[str, Any]],
    *,
    experiment_ids: list[str] | tuple[str, ...] | set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    selected = list(rows)
    if experiment_ids:
        allowed = {str(value).strip() for value in experiment_ids if str(value).strip()}
        if allowed:
            selected = [row for row in selected if str(row.get("experiment_id", "")).strip() in allowed]
    if limit is not None:
        selected = selected[:limit]
    return selected


def run_monthly_validation_sweep_results(
    symbol_candles: dict[str, list[Candle]],
    *,
    cases: list[MonthlyValidationCase],
    sweep_plan_rows: list[dict[str, Any]],
    base_config: MonthlyRebalanceConfig,
    baseline_rows: list[dict[str, Any]],
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
    min_excess_return_pct: float = 0.0,
    max_drawdown_pct: float = -25.0,
    allow_universe_bias_warning: bool = False,
    backtest_runner: Callable[..., MonthlyBacktestResult] | None = None,
) -> list[dict[str, Any]]:
    case_by_name = {case.name: case for case in cases}
    results: list[dict[str, Any]] = []
    for plan_row in sweep_plan_rows:
        target_names = _split_semicolon_values(str(plan_row.get("target_scenarios", "")))
        target_cases = [case_by_name[name] for name in target_names if name in case_by_name]
        experiment_id = str(plan_row.get("experiment_id", "")).strip()
        if not target_cases:
            results.append(
                _sweep_result_row(
                    plan_row,
                    status="SKIPPED",
                    scenario_count=0,
                    failed_required=0,
                    baseline_failed_required=0,
                    failed_delta=0,
                    min_excess_return_pct="",
                    worst_drawdown_pct="",
                    trade_count=0,
                    config_changes=_sweep_config_changes(plan_row),
                    result_summary="No matching target scenarios found.",
                )
            )
            continue

        experiment_config = _apply_sweep_plan_config(base_config, plan_row)
        regular_cases = [case for case in target_cases if case.category != "walk_forward"]
        walk_forward_cases = [case for case in target_cases if case.category == "walk_forward"]
        rows: list[dict[str, Any]] = []
        if regular_cases:
            rows.extend(
                run_monthly_validation_suite(
                    symbol_candles,
                    cases=regular_cases,
                    config=experiment_config,
                    initial_cash=initial_cash,
                    fee_rate=fee_rate,
                    tax_rate=tax_rate,
                    slippage_rate=slippage_rate,
                    min_trade_value=min_trade_value,
                    min_excess_return_pct=min_excess_return_pct,
                    max_drawdown_pct=max_drawdown_pct,
                    allow_universe_bias_warning=allow_universe_bias_warning,
                    backtest_runner=backtest_runner,
                )
            )
        if walk_forward_cases:
            rows.extend(
                run_monthly_walk_forward_validation(
                    symbol_candles,
                    cases=walk_forward_cases,
                    config=experiment_config,
                    initial_cash=initial_cash,
                    fee_rate=fee_rate,
                    tax_rate=tax_rate,
                    slippage_rate=slippage_rate,
                    min_trade_value=min_trade_value,
                    min_excess_return_pct=min_excess_return_pct,
                    max_drawdown_pct=max_drawdown_pct,
                    allow_universe_bias_warning=allow_universe_bias_warning,
                    backtest_runner=backtest_runner,
                )
            )

        failed_required = _count_failed_required(rows)
        baseline_failed = _count_failed_required(
            [row for row in baseline_rows if str(row.get("name", "")).strip() in set(target_names)]
        )
        failed_delta = failed_required - baseline_failed
        status = "IMPROVED" if failed_delta < 0 else "REGRESSED" if failed_delta > 0 else "UNCHANGED"
        min_excess = _min_numeric(row.get("excess_return_pct") for row in rows)
        worst_drawdown = _min_numeric(row.get("max_drawdown_pct") for row in rows)
        trade_count = sum(int(float(row.get("trade_count", 0) or 0)) for row in rows)
        results.append(
            _sweep_result_row(
                plan_row,
                status=status,
                scenario_count=len(rows),
                failed_required=failed_required,
                baseline_failed_required=baseline_failed,
                failed_delta=failed_delta,
                min_excess_return_pct=_format_optional_float(min_excess),
                worst_drawdown_pct=_format_optional_float(worst_drawdown),
                trade_count=trade_count,
                config_changes=_sweep_config_changes(plan_row),
                result_summary=(
                    f"failed_required {baseline_failed} -> {failed_required}; "
                    f"experiment={experiment_id or 'unknown'}"
                ),
            )
        )
    return results


def save_monthly_validation_sweep_results(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_SWEEP_RESULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            normalized = _normalize_sweep_result_row(row)
            writer.writerow({column: normalized.get(column, "") for column in VALIDATION_SWEEP_RESULT_COLUMNS})
    return len(rows)


def build_monthly_validation_candidate_followup_rows(
    sweep_result_rows: list[dict[str, Any]],
    *,
    data_dir: Path | str,
    start: str,
    end: str,
    baseline_scenarios: Path | str,
    reports_dir: Path | str = "data/reports",
    point_in_time_universe: Path | str | None = None,
    max_candidates: int | None = None,
) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in sweep_result_rows
        if str(row.get("status", "")).strip().upper() == "IMPROVED"
        and str(row.get("adoption_status", "")).strip().upper() == "FULL_VALIDATION_REQUIRED"
    ]
    candidates.sort(
        key=lambda row: (
            _safe_int(row.get("failed_delta"), default=9999),
            _safe_int(row.get("failed_required"), default=9999),
            str(row.get("experiment_id", "")),
        )
    )
    if max_candidates is not None:
        candidates = candidates[: max(0, max_candidates)]
    rows: list[dict[str, Any]] = []
    report_root = Path(reports_dir)
    for rank, row in enumerate(candidates, start=1):
        experiment_id = _sanitize_report_token(str(row.get("experiment_id", "")).strip() or f"candidate_{rank}")
        candidate_scenario_output = report_root / f"monthly_validation_candidate_{experiment_id}.csv"
        candidate_gate_output = report_root / f"monthly_deployment_gate_candidate_{experiment_id}.csv"
        candidate_data_quality_output = report_root / f"monthly_validation_data_quality_candidate_{experiment_id}.csv"
        candidate_coverage_output = report_root / f"monthly_universe_price_coverage_candidate_{experiment_id}.csv"
        candidate_performance_output = report_root / f"monthly_performance_audit_candidate_{experiment_id}.csv"
        candidate_concentration_output = report_root / f"monthly_performance_concentration_candidate_{experiment_id}.csv"
        candidate_failure_output = report_root / f"monthly_validation_failures_candidate_{experiment_id}.csv"
        candidate_remediation_output = report_root / f"monthly_validation_remediation_candidate_{experiment_id}.csv"
        candidate_sweep_plan_output = report_root / f"monthly_validation_sweep_plan_candidate_{experiment_id}.csv"
        candidate_sweep_result_output = report_root / f"monthly_validation_sweep_results_candidate_{experiment_id}.csv"
        candidate_universe_filter_output = report_root / f"universe_filter_report_candidate_{experiment_id}.csv"
        comparison_output = report_root / f"monthly_validation_comparison_{experiment_id}.csv"
        delta_output = report_root / f"monthly_validation_comparison_deltas_{experiment_id}.csv"
        decision_output = report_root / f"monthly_validation_candidate_decision_{experiment_id}.csv"
        candidate_args = str(row.get("candidate_validation_args", "")).strip()
        validate_argv = [
            "python",
            "-m",
            "backtester",
            "monthly-validate",
            "--data-dir",
            str(data_dir),
            "--start",
            start,
            "--end",
            end,
        ]
        if point_in_time_universe is not None:
            validate_argv.extend(["--point-in-time-universe", str(point_in_time_universe)])
        validate_argv.extend(_split_cli_args(candidate_args))
        validate_argv.extend(
            [
                "--scenario-output",
                str(candidate_scenario_output),
                "--data-quality-output",
                str(candidate_data_quality_output),
                "--coverage-output",
                str(candidate_coverage_output),
                "--performance-output",
                str(candidate_performance_output),
                "--concentration-output",
                str(candidate_concentration_output),
                "--failure-output",
                str(candidate_failure_output),
                "--remediation-output",
                str(candidate_remediation_output),
                "--sweep-plan-output",
                str(candidate_sweep_plan_output),
                "--sweep-result-output",
                str(candidate_sweep_result_output),
                "--universe-filter-report",
                str(candidate_universe_filter_output),
                "--deployment-gate-output",
                str(candidate_gate_output),
            ]
        )
        compare_argv = [
            "python",
            "-m",
            "backtester",
            "monthly-compare-validation",
            "--baseline",
            str(baseline_scenarios),
            "--candidate",
            str(candidate_scenario_output),
            "--candidate-label",
            experiment_id,
            "--output",
            str(comparison_output),
            "--delta-output",
            str(delta_output),
            "--decision-output",
            str(decision_output),
        ]
        rows.append(
            {
                "priority_rank": rank,
                "experiment_id": experiment_id,
                "status": row.get("status", ""),
                "adoption_status": row.get("adoption_status", ""),
                "failed_delta": row.get("failed_delta", ""),
                "candidate_validation_args": candidate_args,
                "candidate_scenario_output": str(candidate_scenario_output),
                "candidate_gate_output": str(candidate_gate_output),
                "comparison_output": str(comparison_output),
                "delta_output": str(delta_output),
                "decision_output": str(decision_output),
                "validation_command": _format_cli_command(validate_argv),
                "comparison_command": _format_cli_command(compare_argv),
                "risk_note": row.get("risk_note", ""),
            }
        )
    return rows


def save_monthly_validation_candidate_followup_rows(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_CANDIDATE_FOLLOWUP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_CANDIDATE_FOLLOWUP_COLUMNS})
    return len(rows)


def _normalize_sweep_result_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    status = str(normalized.get("status", "")).strip().upper()
    if not str(normalized.get("candidate_validation_args", "")).strip():
        normalized["candidate_validation_args"] = _sweep_candidate_validation_args_from_config_changes(
            str(normalized.get("config_changes", ""))
        )
    normalized.setdefault("validation_scope", "TARGET_ONLY")
    if not str(normalized.get("validation_scope", "")).strip():
        normalized["validation_scope"] = "TARGET_ONLY"
    if not str(normalized.get("adoption_status", "")).strip():
        normalized["adoption_status"] = (
            "FULL_VALIDATION_REQUIRED" if status == "IMPROVED" else "PAPER_DIAGNOSTIC_ONLY"
        )
    if not str(normalized.get("adoption_requirements", "")).strip():
        normalized["adoption_requirements"] = (
            "Run full monthly-validate for the candidate config, compare with baseline, "
            "and require candidate_decision != REJECT before any paper-operation promotion."
        )
    return normalized


def compare_monthly_validation_reports(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> dict[str, Any]:
    baseline_failed = _failed_required_names(baseline_rows)
    candidate_failed = _failed_required_names(candidate_rows)
    resolved = sorted(baseline_failed - candidate_failed)
    new = sorted(candidate_failed - baseline_failed)
    unchanged = sorted(baseline_failed & candidate_failed)
    failed_delta = len(candidate_failed) - len(baseline_failed)
    if failed_delta < 0 and not new:
        status = "IMPROVED"
    elif failed_delta > 0 or new:
        status = "REJECT"
    else:
        status = "UNCHANGED"
    summary = (
        f"failed_required {len(baseline_failed)} -> {len(candidate_failed)}; "
        f"resolved={len(resolved)}; new failures={len(new)}; unchanged={len(unchanged)}"
    )
    return {
        "baseline_label": baseline_label,
        "candidate_label": candidate_label,
        "status": status,
        "baseline_failed_required": len(baseline_failed),
        "candidate_failed_required": len(candidate_failed),
        "failed_delta": failed_delta,
        "resolved_failures": "; ".join(resolved),
        "new_failures": "; ".join(new),
        "unchanged_failures": "; ".join(unchanged),
        "summary": summary,
    }


def compare_monthly_validation_scenario_deltas(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> list[dict[str, Any]]:
    baseline_by_name = {
        str(row.get("name", "")).strip(): row
        for row in baseline_rows
        if str(row.get("name", "")).strip()
    }
    candidate_by_name = {
        str(row.get("name", "")).strip(): row
        for row in candidate_rows
        if str(row.get("name", "")).strip()
    }
    rows: list[dict[str, Any]] = []
    for name in sorted(set(baseline_by_name) | set(candidate_by_name)):
        baseline = baseline_by_name.get(name, {})
        candidate = candidate_by_name.get(name, {})
        baseline_deployable = _parse_bool(baseline.get("deployable", False))
        candidate_deployable = _parse_bool(candidate.get("deployable", False))
        baseline_failed = _parse_bool(baseline.get("required", True)) and not baseline_deployable
        candidate_failed = _parse_bool(candidate.get("required", True)) and not candidate_deployable
        classification = _scenario_delta_classification(baseline_failed, candidate_failed)
        baseline_excess = _float_or_none(baseline.get("excess_return_pct"))
        candidate_excess = _float_or_none(candidate.get("excess_return_pct"))
        baseline_drawdown = _float_or_none(baseline.get("max_drawdown_pct"))
        candidate_drawdown = _float_or_none(candidate.get("max_drawdown_pct"))
        baseline_trades = _float_or_none(baseline.get("trade_count"))
        candidate_trades = _float_or_none(candidate.get("trade_count"))
        excess_delta = _numeric_delta(candidate_excess, baseline_excess)
        drawdown_delta = _numeric_delta(candidate_drawdown, baseline_drawdown)
        trade_delta = _numeric_delta(candidate_trades, baseline_trades)
        rows.append(
            {
                "name": name,
                "classification": classification,
                "baseline_label": baseline_label,
                "candidate_label": candidate_label,
                "baseline_deployable": str(baseline_deployable),
                "candidate_deployable": str(candidate_deployable),
                "baseline_reason": baseline.get("reason", ""),
                "candidate_reason": candidate.get("reason", ""),
                "baseline_excess_return_pct": _format_optional_float(baseline_excess),
                "candidate_excess_return_pct": _format_optional_float(candidate_excess),
                "excess_return_delta": _format_optional_float(excess_delta),
                "baseline_max_drawdown_pct": _format_optional_float(baseline_drawdown),
                "candidate_max_drawdown_pct": _format_optional_float(candidate_drawdown),
                "max_drawdown_delta": _format_optional_float(drawdown_delta),
                "baseline_trade_count": _format_optional_float(baseline_trades),
                "candidate_trade_count": _format_optional_float(candidate_trades),
                "trade_count_delta": _format_optional_float(trade_delta),
                "diagnostic": _scenario_delta_diagnostic(
                    classification,
                    baseline_reason=str(baseline.get("reason", "")),
                    candidate_reason=str(candidate.get("reason", "")),
                    excess_delta=excess_delta,
                    drawdown_delta=drawdown_delta,
                    trade_delta=trade_delta,
                ),
            }
        )
    return rows


def save_monthly_validation_scenario_deltas(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_SCENARIO_DELTA_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_SCENARIO_DELTA_COLUMNS})
    return len(rows)


def save_monthly_validation_comparison(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_COMPARISON_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_COMPARISON_COLUMNS})
    return len(rows)


def build_monthly_validation_candidate_decision(
    comparison: dict[str, Any],
    delta_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    classifications = Counter(str(row.get("classification", "")).strip() for row in delta_rows)
    diagnostics = Counter(
        str(row.get("diagnostic", "")).strip()
        for row in delta_rows
        if str(row.get("classification", "")).strip() == "NEW_FAILURE"
    )
    new_count = classifications.get("NEW_FAILURE", 0)
    resolved_count = classifications.get("RESOLVED", 0)
    unchanged_count = classifications.get("UNCHANGED_FAILURE", 0)
    resolved_names = _scenario_names_by_classification(delta_rows, "RESOLVED")
    new_failure_names = _scenario_names_by_classification(delta_rows, "NEW_FAILURE")
    unchanged_names = _scenario_names_by_classification(delta_rows, "UNCHANGED_FAILURE")
    comparison_status = str(comparison.get("status", "")).strip().upper() or "UNKNOWN"
    try:
        failed_delta = int(float(comparison.get("failed_delta", 0) or 0))
    except (TypeError, ValueError):
        failed_delta = 0

    reasons: list[str] = []
    if comparison_status in {"REJECT", "REJECTED"}:
        reasons.append("comparison_rejected")
    if new_count:
        reasons.append(f"new_failures={new_count}")
    if failed_delta > 0:
        reasons.append(f"failed_delta={failed_delta}")
    if unchanged_count:
        reasons.append(f"unchanged_failures={unchanged_count}")
    drawdown_buffer_regression_count = sum(
        diagnostics.get(name, 0)
        for name in (
            "equity_improved_but_drawdown_buffer_worse",
            "drawdown_buffer_regression",
            "candidate_introduced_drawdown_breach",
        )
    )
    if drawdown_buffer_regression_count:
        reasons.append(f"drawdown_buffer_regressions={drawdown_buffer_regression_count}")

    if comparison_status in {"REJECT", "REJECTED"} or new_count or failed_delta > 0:
        decision = "REJECT"
        if drawdown_buffer_regression_count:
            recommendation = (
                "Do not adopt this candidate; it reduces hard-gate drawdown buffer. "
                "Inspect path-level drawdown-buffer diagnostics and run narrower paper-only experiments."
            )
        else:
            recommendation = (
                "Do not adopt this candidate; inspect new failure diagnostics and run narrower paper-only experiments."
            )
    elif failed_delta < 0 and not new_count:
        decision = "PAPER_REVIEW"
        recommendation = (
            "Candidate improved required failures without introducing new failures; keep paper-only, rerun full validation, "
            "complete OOS/post-cutoff review, and require explicit production readiness changes before promotion."
        )
    else:
        decision = "HOLD"
        recommendation = "No deployable improvement; keep baseline controls and continue diagnostics."

    diagnostic_summary = ", ".join(
        f"{name}={count}" for name, count in sorted(diagnostics.items()) if name
    )
    decision_reasons = "; ".join(reasons) if reasons else "no_required_failure_regression"
    return [
        {
            "candidate_label": comparison.get("candidate_label", ""),
            "comparison_status": comparison_status,
            "decision": decision,
            "decision_reasons": decision_reasons,
            "baseline_failed_required": comparison.get("baseline_failed_required", ""),
            "candidate_failed_required": comparison.get("candidate_failed_required", ""),
            "failed_delta": comparison.get("failed_delta", ""),
            "resolved_count": resolved_count,
            "new_failure_count": new_count,
            "unchanged_failure_count": unchanged_count,
            "resolved_failure_names": "; ".join(resolved_names),
            "new_failure_names": "; ".join(new_failure_names),
            "unchanged_failure_names": "; ".join(unchanged_names),
            "new_failure_diagnostics": diagnostic_summary,
            "recommendation": recommendation,
        }
    ]


def save_monthly_validation_candidate_decision(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_CANDIDATE_DECISION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_CANDIDATE_DECISION_COLUMNS})
    return len(rows)


def build_monthly_validation_candidate_summary(
    decision_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    path_comparison_rows: list[dict[str, Any]] | None = None,
    *,
    drawdown_threshold_pct: float = -25.0,
) -> list[dict[str, Any]]:
    path_rows = path_comparison_rows or []
    labels = _candidate_summary_labels(decision_rows, delta_rows, path_rows)
    rows: list[dict[str, Any]] = []
    for label in labels:
        decision = _first_candidate_summary_row(decision_rows, label)
        candidate_deltas = _candidate_summary_rows(delta_rows, label, labels)
        candidate_paths = _candidate_summary_rows(path_rows, label, labels)
        classifications = Counter(str(row.get("classification", "")).strip() for row in candidate_deltas)
        diagnostics = Counter(str(row.get("diagnostic", "")).strip() for row in candidate_deltas)

        resolved_count = _candidate_summary_int(decision, "resolved_count", classifications.get("RESOLVED", 0))
        new_failure_count = _candidate_summary_int(
            decision,
            "new_failure_count",
            classifications.get("NEW_FAILURE", 0),
        )
        unchanged_failure_count = _candidate_summary_int(
            decision,
            "unchanged_failure_count",
            classifications.get("UNCHANGED_FAILURE", 0),
        )
        drawdown_buffer_count = sum(
            diagnostics.get(name, 0)
            for name in (
                "equity_improved_but_drawdown_buffer_worse",
                "drawdown_buffer_regression",
                "candidate_introduced_drawdown_breach",
            )
        )
        drawdown_buffer_count = max(
            drawdown_buffer_count,
            _candidate_summary_counter_value(
                str(decision.get("decision_reasons", "")),
                "drawdown_buffer_regressions",
            ),
        )
        equity_improved_new_failure_count = diagnostics.get(
            "equity_improved_but_drawdown_buffer_worse",
            0,
        )

        path_diagnostics = [str(row.get("diagnostic", "")) for row in candidate_paths]
        path_equity_regression_days = _count_diagnostics(path_diagnostics, "equity_regression")
        path_equity_improved_days = _count_diagnostics(path_diagnostics, "equity_improved")
        path_drawdown_regression_days = _count_diagnostics(path_diagnostics, "drawdown_regression")
        path_symbol_rotation_days = _count_diagnostics(path_diagnostics, "symbol_rotation")
        path_higher_turnover_days = _count_diagnostics(path_diagnostics, "higher_turnover")
        path_higher_trade_cost_days = _count_diagnostics(path_diagnostics, "higher_trade_cost")
        path_min_equity_delta = _min_numeric(row.get("equity_delta") for row in candidate_paths)
        path_worst_drawdown_delta = _min_numeric(row.get("drawdown_delta_pct") for row in candidate_paths)
        path_max_rolling_peak_delta = _max_numeric(row.get("rolling_peak_delta") for row in candidate_paths)
        path_candidate_drawdown_breach_days = 0
        path_equity_improved_drawdown_breach_days = 0
        path_peak_buffer_loss_days = 0
        for row in candidate_paths:
            candidate_drawdown = _float_or_none(row.get("candidate_drawdown_pct"))
            equity_delta = _float_or_none(row.get("equity_delta"))
            rolling_peak_delta = _float_or_none(row.get("rolling_peak_delta"))
            drawdown_delta = _float_or_none(row.get("drawdown_delta_pct"))
            if candidate_drawdown is not None and candidate_drawdown <= drawdown_threshold_pct:
                path_candidate_drawdown_breach_days += 1
                if equity_delta is not None and equity_delta > 0:
                    path_equity_improved_drawdown_breach_days += 1
                    if (
                        rolling_peak_delta is not None
                        and rolling_peak_delta > 0
                        and drawdown_delta is not None
                        and drawdown_delta < 0
                    ):
                        path_peak_buffer_loss_days += 1
        path_rejection_reasons: list[str] = []
        if path_peak_buffer_loss_days:
            path_acceptance_decision = "REJECT"
            path_rejection_reasons.append("higher_rolling_peak_drawdown_buffer_loss")
        elif path_equity_improved_drawdown_breach_days:
            path_acceptance_decision = "REJECT"
            path_rejection_reasons.append("equity_improved_candidate_crossed_drawdown_threshold")
        elif path_candidate_drawdown_breach_days:
            path_acceptance_decision = "REVIEW"
            path_rejection_reasons.append("candidate_crossed_drawdown_threshold")
        elif candidate_paths:
            path_acceptance_decision = "PASS"
        else:
            path_acceptance_decision = "NO_PATH_DATA"
        evaluation_score = (
            resolved_count * 100
            - new_failure_count * 200
            - drawdown_buffer_count * 50
            - path_equity_regression_days * 5
            - path_drawdown_regression_days
            - path_symbol_rotation_days * 5
            - path_higher_turnover_days
            - path_peak_buffer_loss_days * 5
        )
        rows.append(
            {
                "candidate_rank": "",
                "candidate_label": label,
                "decision": decision.get("decision", ""),
                "comparison_status": decision.get("comparison_status", ""),
                "baseline_failed_required": decision.get("baseline_failed_required", ""),
                "candidate_failed_required": decision.get("candidate_failed_required", ""),
                "failed_delta": decision.get("failed_delta", ""),
                "resolved_count": str(resolved_count),
                "new_failure_count": str(new_failure_count),
                "unchanged_failure_count": str(unchanged_failure_count),
                "drawdown_buffer_regression_count": str(drawdown_buffer_count),
                "equity_improved_new_failure_count": str(equity_improved_new_failure_count),
                "path_scenario_count": str(
                    len({str(row.get("scenario", "")).strip() for row in candidate_paths if row.get("scenario", "")})
                ),
                "path_days_compared": str(len(candidate_paths)),
                "path_equity_regression_days": str(path_equity_regression_days),
                "path_equity_improved_days": str(path_equity_improved_days),
                "path_drawdown_regression_days": str(path_drawdown_regression_days),
                "path_symbol_rotation_days": str(path_symbol_rotation_days),
                "path_higher_turnover_days": str(path_higher_turnover_days),
                "path_higher_trade_cost_days": str(path_higher_trade_cost_days),
                "path_min_equity_delta": _format_optional_float(path_min_equity_delta),
                "path_worst_drawdown_delta_pct": _format_optional_float(path_worst_drawdown_delta),
                "path_max_rolling_peak_delta": _format_optional_float(path_max_rolling_peak_delta),
                "path_drawdown_threshold_pct": _format_optional_float(drawdown_threshold_pct),
                "path_acceptance_decision": path_acceptance_decision,
                "path_rejection_reasons": "; ".join(path_rejection_reasons),
                "path_candidate_drawdown_breach_days": str(path_candidate_drawdown_breach_days),
                "path_equity_improved_drawdown_breach_days": str(path_equity_improved_drawdown_breach_days),
                "path_peak_buffer_loss_days": str(path_peak_buffer_loss_days),
                "evaluation_score": str(evaluation_score),
                "resolved_failure_names": str(
                    decision.get("resolved_failure_names", "")
                    or "; ".join(_scenario_names_by_classification(candidate_deltas, "RESOLVED"))
                ),
                "new_failure_names": str(
                    decision.get("new_failure_names", "")
                    or "; ".join(_scenario_names_by_classification(candidate_deltas, "NEW_FAILURE"))
                ),
                "new_failure_diagnostics": str(
                    decision.get("new_failure_diagnostics", "")
                    or _candidate_summary_diagnostic_summary(candidate_deltas, "NEW_FAILURE")
                ),
                "summary": (
                    f"resolved={resolved_count}; new_failures={new_failure_count}; "
                    f"drawdown_buffer_regressions={drawdown_buffer_count}; "
                    f"path_acceptance={path_acceptance_decision}; "
                    f"path_equity_regression_days={path_equity_regression_days}; "
                    f"path_drawdown_regression_days={path_drawdown_regression_days}; "
                    f"path_higher_turnover_days={path_higher_turnover_days}"
                ),
                "recommendation": decision.get("recommendation", ""),
            }
        )
    rows.sort(
        key=lambda row: (
            -_safe_int(row.get("evaluation_score")),
            _safe_int(row.get("new_failure_count")),
            _safe_int(row.get("drawdown_buffer_regression_count")),
            str(row.get("candidate_label", "")),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["candidate_rank"] = str(index)
    return rows


def save_monthly_validation_candidate_summary(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_CANDIDATE_SUMMARY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_CANDIDATE_SUMMARY_COLUMNS})
    return len(rows)


def analyze_monthly_validation_failure_patterns(
    baseline_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_name = {
        str(row.get("name", "")).strip(): row
        for row in baseline_rows
        if str(row.get("name", "")).strip()
    }
    scenarios: set[str] = {
        name
        for name, row in baseline_by_name.items()
        if _parse_bool(row.get("required", True)) and not _parse_bool(row.get("deployable", False))
    }
    stats: dict[str, dict[str, Any]] = {}

    def scenario_stats(name: str) -> dict[str, Any]:
        if name not in stats:
            stats[name] = {
                "failed": set(),
                "new": set(),
                "resolved": set(),
                "unchanged": set(),
                "diagnostics": Counter(),
            }
        return stats[name]

    for row in delta_rows:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        classification = str(row.get("classification", "")).strip().upper()
        if classification not in {"NEW_FAILURE", "RESOLVED", "UNCHANGED_FAILURE"}:
            continue
        scenarios.add(name)
        stat = scenario_stats(name)
        candidate = str(row.get("candidate_label", "")).strip() or "candidate"
        diagnostic = str(row.get("diagnostic", "")).strip()
        if diagnostic:
            stat["diagnostics"][diagnostic] += 1
        if classification == "NEW_FAILURE":
            stat["new"].add(candidate)
            stat["failed"].add(candidate)
        elif classification == "UNCHANGED_FAILURE":
            stat["unchanged"].add(candidate)
            stat["failed"].add(candidate)
        elif classification == "RESOLVED":
            stat["resolved"].add(candidate)

    rows: list[dict[str, Any]] = []
    for scenario in sorted(scenarios):
        baseline = baseline_by_name.get(scenario, {})
        baseline_failed = _parse_bool(baseline.get("required", True)) and not _parse_bool(
            baseline.get("deployable", False)
        )
        stat = scenario_stats(scenario)
        failed = sorted(stat["failed"])
        new = sorted(stat["new"])
        resolved = sorted(stat["resolved"])
        unchanged = sorted(stat["unchanged"])
        diagnostic_counts: Counter[str] = stat["diagnostics"]
        dominant_diagnostic = ""
        if diagnostic_counts:
            dominant_diagnostic = "; ".join(
                f"{name}={count}" for name, count in diagnostic_counts.most_common(3)
            )
        pattern_status, suggested_action, notes = _validation_failure_pattern_status(
            baseline_failed=baseline_failed,
            failed_count=len(failed),
            new_count=len(new),
            resolved_count=len(resolved),
            unchanged_count=len(unchanged),
        )
        rows.append(
            {
                "scenario": scenario,
                "baseline_failed": str(baseline_failed),
                "baseline_reason": baseline.get("reason", ""),
                "failed_candidate_count": len(failed),
                "new_failure_candidate_count": len(new),
                "resolved_candidate_count": len(resolved),
                "unchanged_failure_candidate_count": len(unchanged),
                "candidate_labels_failed": "; ".join(failed),
                "candidate_labels_new_failure": "; ".join(new),
                "candidate_labels_resolved": "; ".join(resolved),
                "candidate_labels_unchanged": "; ".join(unchanged),
                "dominant_diagnostic": dominant_diagnostic,
                "pattern_status": pattern_status,
                "suggested_action": suggested_action,
                "notes": notes,
            }
        )
    rows.sort(
        key=lambda row: (
            _failure_pattern_rank(str(row.get("pattern_status", ""))),
            -int(row.get("failed_candidate_count", 0) or 0),
            str(row.get("scenario", "")),
        )
    )
    return rows


def save_monthly_validation_failure_patterns(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_FAILURE_PATTERN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_FAILURE_PATTERN_COLUMNS})
    return len(rows)


def analyze_monthly_validation_failure_drilldown(
    baseline_rows: list[dict[str, Any]],
    pattern_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    *,
    decision_attribution_rows: list[dict[str, Any]] | None = None,
    symbol_attribution_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    baseline_by_name = {
        str(row.get("name", "")).strip(): row
        for row in baseline_rows
        if str(row.get("name", "")).strip()
    }
    delta_by_name: dict[str, list[dict[str, Any]]] = {}
    for row in delta_rows:
        name = str(row.get("name", "")).strip()
        if name:
            delta_by_name.setdefault(name, []).append(row)
    attribution_evidence = _validation_attribution_evidence(
        decision_attribution_rows=decision_attribution_rows or [],
        symbol_attribution_rows=symbol_attribution_rows or [],
    )

    rows: list[dict[str, Any]] = []
    for pattern in pattern_rows:
        scenario = str(pattern.get("scenario", "")).strip()
        if not scenario:
            continue
        baseline = baseline_by_name.get(scenario, {})
        deltas = delta_by_name.get(scenario, [])
        candidate_labels = sorted(
            {
                str(row.get("candidate_label", "")).strip()
                for row in deltas
                if str(row.get("candidate_label", "")).strip()
            }
        )
        excess_deltas = [_float_or_none(row.get("excess_return_delta")) for row in deltas]
        drawdown_deltas = [_float_or_none(row.get("max_drawdown_delta")) for row in deltas]
        trade_deltas = [_float_or_none(row.get("trade_count_delta")) for row in deltas]
        median_excess_delta = _median_numeric(excess_deltas)
        likely_root_cause = _validation_failure_likely_root_cause(
            baseline,
            pattern,
            median_excess_delta=median_excess_delta,
        )
        evidence_gaps = _validation_failure_evidence_gaps(
            pattern_status=str(pattern.get("pattern_status", "")),
            likely_root_cause=likely_root_cause,
            available_evidence=_validation_failure_available_evidence(
                baseline,
                attribution_evidence.get(scenario, set()),
            ),
        )
        rows.append(
            {
                "scenario": scenario,
                "category": baseline.get("category", ""),
                "pattern_status": pattern.get("pattern_status", ""),
                "suggested_action": pattern.get("suggested_action", ""),
                "baseline_reason": baseline.get("reason", pattern.get("baseline_reason", "")),
                "likely_root_cause": likely_root_cause,
                "train_start": baseline.get("train_start", ""),
                "train_end": baseline.get("train_end", ""),
                "selected_preset": baseline.get("selected_preset", ""),
                "train_excess_return_pct": baseline.get("train_excess_return_pct", ""),
                "train_candidate_scores": baseline.get("train_candidate_scores", ""),
                "train_candidate_decision_profiles": baseline.get("train_candidate_decision_profiles", ""),
                "train_candidate_direct_scores": baseline.get("train_candidate_direct_scores", ""),
                "train_direct_diagnostics": baseline.get("train_direct_diagnostics", ""),
                "start": baseline.get("start", ""),
                "end": baseline.get("end", ""),
                "baseline_excess_return_pct": baseline.get("excess_return_pct", ""),
                "baseline_max_drawdown_pct": baseline.get("max_drawdown_pct", ""),
                "baseline_trade_count": baseline.get("trade_count", ""),
                "candidate_count": len(candidate_labels),
                "candidate_labels": "; ".join(candidate_labels),
                "candidate_excess_delta_min": _format_optional_float(_min_numeric(excess_deltas)),
                "candidate_excess_delta_median": _format_optional_float(median_excess_delta),
                "candidate_drawdown_delta_median": _format_optional_float(_median_numeric(drawdown_deltas)),
                "candidate_trade_delta_median": _format_optional_float(_median_numeric(trade_deltas)),
                "dominant_diagnostic": pattern.get("dominant_diagnostic", ""),
                "evidence_gaps": evidence_gaps,
                "next_action": _validation_failure_next_action(likely_root_cause, evidence_gaps),
            }
        )
    rows.sort(
        key=lambda row: (
            _failure_pattern_rank(str(row.get("pattern_status", ""))),
            str(row.get("scenario", "")),
        )
    )
    return rows


def save_monthly_validation_failure_drilldown(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_FAILURE_DRILLDOWN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in VALIDATION_FAILURE_DRILLDOWN_COLUMNS})
    return len(rows)


def _scenario_names_by_classification(rows: list[dict[str, Any]], classification: str) -> list[str]:
    wanted = classification.strip()
    names = [
        str(row.get("name", "")).strip()
        for row in rows
        if str(row.get("classification", "")).strip() == wanted
        and str(row.get("name", "")).strip()
    ]
    return sorted(set(names))


def _validation_failure_pattern_status(
    *,
    baseline_failed: bool,
    failed_count: int,
    new_count: int,
    resolved_count: int,
    unchanged_count: int,
) -> tuple[str, str, str]:
    if baseline_failed and unchanged_count and not resolved_count:
        return (
            "PERSISTENT_BLOCK",
            "REVIEW_PERSISTENT_FAILURE",
            "Baseline failure persisted in every candidate that touched this scenario.",
        )
    if new_count and not baseline_failed:
        return (
            "REGRESSION_RISK",
            "AVOID_REGRESSION_CONFIGS",
            "Previously passing scenario became a candidate failure.",
        )
    if baseline_failed and unchanged_count and resolved_count:
        return (
            "MIXED_RESPONSE",
            "ISOLATE_FIXING_FEATURES",
            "Some candidates fixed this baseline failure while others left it failed.",
        )
    if baseline_failed and resolved_count and not failed_count:
        return (
            "CANDIDATE_FIXED",
            "RETEST_FIXING_CANDIDATES",
            "Candidates resolved this baseline failure without introducing a scenario failure.",
        )
    if baseline_failed:
        return (
            "BASELINE_BLOCK",
            "RUN_CANDIDATE_DIAGNOSTICS",
            "Baseline remains blocked and no candidate delta evidence is available.",
        )
    return ("REVIEW", "REVIEW_SCENARIO", "Scenario appeared in candidate deltas and needs review.")


def _failure_pattern_rank(status: str) -> int:
    ranks = {
        "PERSISTENT_BLOCK": 0,
        "REGRESSION_RISK": 1,
        "MIXED_RESPONSE": 2,
        "BASELINE_BLOCK": 3,
        "CANDIDATE_FIXED": 4,
        "REVIEW": 5,
    }
    return ranks.get(status, 99)


def _validation_failure_likely_root_cause(
    baseline: dict[str, Any],
    pattern: dict[str, Any],
    *,
    median_excess_delta: float | None = None,
) -> str:
    reason = str(baseline.get("reason", pattern.get("baseline_reason", ""))).strip()
    pattern_status = str(pattern.get("pattern_status", "")).strip().upper()
    diagnostic = str(pattern.get("dominant_diagnostic", "")).strip()
    if reason == "train_window_rejected" or "train_gate_regression" in diagnostic:
        if _direct_train_candidates_are_ineligible(str(baseline.get("train_candidate_direct_scores", ""))):
            return "direct_alpha_ineligible"
        return "train_window_selection"
    if reason == "max_drawdown_breach":
        return "drawdown_pressure"
    if pattern_status == "REGRESSION_RISK":
        if "over_defense_or_filter_drag" in diagnostic:
            return "over_defense_or_filter_drag"
        return "selection_or_exposure_regression"
    if pattern_status == "CANDIDATE_FIXED":
        return "candidate_fixed_failure"
    if reason == "negative_excess_return" and pattern_status == "PERSISTENT_BLOCK":
        if median_excess_delta is not None and median_excess_delta > 0:
            return "insufficient_recovery"
        return "weak_window_return_drag"
    return "scenario_review"


def _validation_attribution_evidence(
    *,
    decision_attribution_rows: list[dict[str, Any]],
    symbol_attribution_rows: list[dict[str, Any]],
) -> dict[str, set[str]]:
    evidence: dict[str, set[str]] = {}
    for row in decision_attribution_rows:
        scenario = str(row.get("scenario", "")).strip()
        if not scenario:
            continue
        scenario_evidence = evidence.setdefault(scenario, set())
        if str(row.get("selected_symbols", "")).strip():
            scenario_evidence.add("selected_symbols")
        if _float_or_none(row.get("target_exposure")) is not None:
            scenario_evidence.add("exposure")
        if _float_or_none(row.get("cash_weight")) is not None:
            scenario_evidence.add("cash_weight")
    for row in symbol_attribution_rows:
        scenario = str(row.get("scenario", "")).strip()
        if not scenario:
            continue
        if str(row.get("symbol", "")).strip() and str(row.get("realized_pnl", "")).strip():
            evidence.setdefault(scenario, set()).add("symbol_pnl_attribution")
    return evidence


def _validation_failure_available_evidence(
    baseline: dict[str, Any],
    attribution_evidence: set[str],
) -> set[str]:
    available = set(attribution_evidence)
    if str(baseline.get("train_candidate_scores", "")).strip():
        available.add("train_window_candidate_scores")
    if str(baseline.get("train_candidate_direct_scores", "")).strip():
        available.add("direct_train_candidate_scores")
    return available


def _validation_failure_evidence_gaps(
    *,
    pattern_status: str,
    likely_root_cause: str,
    available_evidence: set[str] | None = None,
) -> str:
    status = pattern_status.strip().upper()
    available = available_evidence or set()
    gaps: list[str] = []
    if status in {"PERSISTENT_BLOCK", "REGRESSION_RISK", "MIXED_RESPONSE"}:
        gaps.extend(["selected_symbols", "exposure", "cash_weight"])
    if likely_root_cause == "train_window_selection":
        gaps.append("train_window_candidate_scores")
    if likely_root_cause == "direct_alpha_ineligible":
        gaps.append("direct_train_candidate_scores")
    if likely_root_cause in {"weak_window_return_drag", "selection_or_exposure_regression", "insufficient_recovery"}:
        gaps.append("symbol_pnl_attribution")
    gaps = [gap for gap in gaps if gap not in available]
    return "; ".join(dict.fromkeys(gaps))


def _validation_failure_next_action(likely_root_cause: str, evidence_gaps: str) -> str:
    if likely_root_cause == "direct_alpha_ineligible":
        return (
            "Diagnose why direct alpha train candidates have non-positive excess returns before loosening gates."
        )
    if likely_root_cause == "train_window_selection":
        return "Review training window rejection and no-trade gate before tuning parameters."
    if likely_root_cause == "drawdown_pressure":
        return "Run drawdown attribution and reduce exposure only after identifying loss months and symbols."
    if likely_root_cause in {"selection_or_exposure_regression", "over_defense_or_filter_drag"}:
        return "Avoid regression configs; compare selected symbols, exposure, and cash weight against baseline."
    if likely_root_cause == "insufficient_recovery":
        if not evidence_gaps:
            return "Use attribution evidence to isolate the partial fix before changing risk parameters."
        return "Isolate the partial fix, then run scenario attribution before increasing risk or adding filters."
    if likely_root_cause == "candidate_fixed_failure":
        return "Retest the fixing behavior in isolation and verify it does not introduce new failures."
    if evidence_gaps:
        return "Run scenario attribution with selected symbols, exposure, cash weight, and symbol PnL before tuning more parameters."
    return "Review scenario metrics before adding another parameter experiment."


def _direct_train_candidates_are_ineligible(value: str) -> bool:
    scores = [part.strip() for part in value.split(";") if part.strip()]
    if not scores:
        return False
    excess_values: list[float] = []
    for score in scores:
        marker = "excess="
        if marker not in score:
            return False
        raw_value = score.split(marker, 1)[-1].split(",", 1)[0].strip()
        try:
            excess_values.append(float(raw_value))
        except ValueError:
            return False
    return bool(excess_values) and all(value <= 0.0 for value in excess_values)


def _median_numeric(values: Any) -> float | None:
    numeric_values = [_float_or_none(value) for value in values]
    numeric_values = [value for value in numeric_values if value is not None]
    return median(numeric_values) if numeric_values else None


def _validation_failure_diagnostic(row: dict[str, Any]) -> dict[str, Any]:
    reason = str(row.get("reason", "") or "unknown").strip()
    failed_metric = "reason"
    metric_value = reason
    threshold = ""
    suggested_action = "REVIEW_SCENARIO"
    parameter_hints = "Inspect validation row and keep production-check blocked until the cause is understood."

    if reason == "max_drawdown_breach":
        failed_metric = "max_drawdown_pct"
        metric_value = str(row.get("max_drawdown_pct", ""))
        threshold = "configured max deployment drawdown"
        suggested_action = "REDUCE_DRAWDOWN"
        parameter_hints = (
            "lower max_position_weight; increase cash_buffer_weight; strengthen drawdown_guard_scale; "
            "test higher market_volatility_min_scale and stricter risk-off fallback"
        )
    elif reason == "negative_excess_return":
        failed_metric = "excess_return_pct"
        metric_value = str(row.get("excess_return_pct", ""))
        threshold = "0.0"
        suggested_action = "IMPROVE_WEAK_WINDOW_DEFENSE"
        parameter_hints = (
            "increase cash_buffer_weight in weak regimes; tighten min_train_positive_ratio; "
            "test lower candidate_pool_size and stronger market_beta/cash fallback"
        )
    elif reason == "train_window_rejected":
        failed_metric = "train_excess_return_pct"
        metric_value = str(row.get("train_excess_return_pct", ""))
        threshold = "training gate"
        suggested_action = "KEEP_TRAIN_WINDOW_REJECTED"
        parameter_hints = (
            "Do not override rejected train windows; inspect preset stability and require robust train windows."
        )
    elif reason.startswith("data_quality"):
        failed_metric = "data_quality"
        metric_value = reason
        threshold = "PASS"
        suggested_action = "REFRESH_OR_EXCLUDE_DATA"
        parameter_hints = "Refresh KRX candles and rerun data-check exclusions before validation."

    return {
        "name": row.get("name", ""),
        "category": row.get("category", ""),
        "reason": reason,
        "severity": "BLOCK",
        "failed_metric": failed_metric,
        "metric_value": metric_value,
        "threshold": threshold,
        "suggested_action": suggested_action,
        "parameter_hints": parameter_hints,
        "start": row.get("start", ""),
        "end": row.get("end", ""),
        "selected_preset": row.get("selected_preset", ""),
        "train_excess_return_pct": row.get("train_excess_return_pct", ""),
        "excess_return_pct": row.get("excess_return_pct", ""),
        "max_drawdown_pct": row.get("max_drawdown_pct", ""),
        "trade_count": row.get("trade_count", ""),
        "stress": row.get("stress", ""),
        "source": row.get("source", ""),
    }


def _sweep_plan_row(
    remediation_row: dict[str, Any],
    *,
    experiment_id: str,
    target_scenarios: str,
    base_config: MonthlyRebalanceConfig,
    cash_buffer_weight: float | None = None,
    min_train_positive_ratio: float | None = None,
    candidate_pool_size: int | None = None,
    market_beta_proxy_max_exposure: float | None = None,
    market_beta_proxy_neutral_breadth_max_exposure: float | None = None,
    max_position_weight: float | None = None,
    drawdown_guard_scale: float | None = None,
    drawdown_guard_deep_trigger_pct: float | None = None,
    drawdown_guard_deep_scale: float | None = None,
    market_volatility_min_scale: float | None = None,
    position_trailing_stop_pct: float | None = None,
    position_trailing_stop_reason_contains: str | None = None,
    expected_effect: str,
    risk_note: str = "Plan only; run monthly validation before adopting any parameter change.",
) -> dict[str, Any]:
    return {
        "priority": remediation_row.get("priority", "P1"),
        "suggested_action": remediation_row.get("suggested_action", ""),
        "experiment_id": experiment_id,
        "target_scenarios": target_scenarios,
        "cash_buffer_weight": _sweep_value(cash_buffer_weight, base_config.cash_buffer_weight),
        "min_train_positive_ratio": _sweep_value(min_train_positive_ratio, base_config.min_train_positive_ratio),
        "candidate_pool_size": "" if candidate_pool_size is None else str(candidate_pool_size),
        "market_beta_proxy_max_exposure": _sweep_value(
            market_beta_proxy_max_exposure,
            base_config.market_beta_proxy_max_exposure,
        ),
        "market_beta_proxy_neutral_breadth_max_exposure": _sweep_value(
            market_beta_proxy_neutral_breadth_max_exposure,
            base_config.market_beta_proxy_neutral_breadth_max_exposure,
        ),
        "max_position_weight": _sweep_value(max_position_weight, base_config.max_position_weight),
        "drawdown_guard_scale": _sweep_value(drawdown_guard_scale, base_config.drawdown_guard_scale),
        "drawdown_guard_deep_trigger_pct": _sweep_value(
            drawdown_guard_deep_trigger_pct,
            base_config.drawdown_guard_deep_trigger_pct,
        ),
        "drawdown_guard_deep_scale": _sweep_value(
            drawdown_guard_deep_scale,
            base_config.drawdown_guard_deep_scale,
        ),
        "market_volatility_min_scale": _sweep_value(
            market_volatility_min_scale,
            base_config.market_volatility_min_scale,
        ),
        "position_trailing_stop_pct": _sweep_value(
            position_trailing_stop_pct,
            base_config.position_trailing_stop_pct,
        ),
        "position_trailing_stop_reason_contains": (
            ""
            if position_trailing_stop_reason_contains is None
            or position_trailing_stop_reason_contains == base_config.position_trailing_stop_reason_contains
            else position_trailing_stop_reason_contains
        ),
        "expected_effect": expected_effect,
        "risk_note": risk_note,
    }


def _sweep_value(value: float | None, base_value: float) -> str:
    if value is None or abs(value - base_value) < 1e-12:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _sweep_result_row(
    plan_row: dict[str, Any],
    *,
    status: str,
    scenario_count: int,
    failed_required: int,
    baseline_failed_required: int,
    failed_delta: int,
    min_excess_return_pct: str,
    worst_drawdown_pct: str,
    trade_count: int,
    config_changes: str,
    result_summary: str,
) -> dict[str, Any]:
    return {
        "experiment_id": plan_row.get("experiment_id", ""),
        "suggested_action": plan_row.get("suggested_action", ""),
        "status": status,
        "target_scenarios": plan_row.get("target_scenarios", ""),
        "scenario_count": scenario_count,
        "failed_required": failed_required,
        "baseline_failed_required": baseline_failed_required,
        "failed_delta": failed_delta,
        "min_excess_return_pct": min_excess_return_pct,
        "worst_drawdown_pct": worst_drawdown_pct,
        "trade_count": trade_count,
        "config_changes": config_changes,
        "candidate_validation_args": _sweep_candidate_validation_args(plan_row),
        "validation_scope": "TARGET_ONLY",
        "adoption_status": "FULL_VALIDATION_REQUIRED" if status == "IMPROVED" else "PAPER_DIAGNOSTIC_ONLY",
        "adoption_requirements": (
            "Run full monthly-validate for the candidate config, compare with baseline, "
            "and require candidate_decision != REJECT before any paper-operation promotion."
        ),
        "result_summary": result_summary,
        "risk_note": plan_row.get("risk_note", ""),
    }


def _apply_sweep_plan_config(
    base_config: MonthlyRebalanceConfig,
    plan_row: dict[str, Any],
) -> MonthlyRebalanceConfig:
    updates: dict[str, Any] = {}
    for field_name, converter in {
        "cash_buffer_weight": float,
        "min_train_positive_ratio": float,
        "candidate_pool_size": int,
        "market_beta_proxy_max_exposure": float,
        "market_beta_proxy_neutral_breadth_max_exposure": float,
        "max_position_weight": float,
        "drawdown_guard_scale": float,
        "drawdown_guard_deep_trigger_pct": float,
        "drawdown_guard_deep_scale": float,
        "market_volatility_min_scale": float,
        "position_trailing_stop_pct": float,
    }.items():
        raw_value = str(plan_row.get(field_name, "")).strip()
        if raw_value == "":
            continue
        try:
            updates[field_name] = converter(float(raw_value)) if converter is int else converter(raw_value)
        except ValueError:
            continue
    reason_filter = str(plan_row.get("position_trailing_stop_reason_contains", "")).strip()
    if reason_filter:
        updates["position_trailing_stop_reason_contains"] = reason_filter
    return replace(base_config, **updates) if updates else base_config


def _sweep_config_changes(plan_row: dict[str, Any]) -> str:
    parts: list[str] = []
    for field_name in (
        "cash_buffer_weight",
        "min_train_positive_ratio",
        "candidate_pool_size",
        "market_beta_proxy_max_exposure",
        "market_beta_proxy_neutral_breadth_max_exposure",
        "max_position_weight",
        "drawdown_guard_scale",
        "drawdown_guard_deep_trigger_pct",
        "drawdown_guard_deep_scale",
        "market_volatility_min_scale",
        "position_trailing_stop_pct",
        "position_trailing_stop_reason_contains",
    ):
        value = str(plan_row.get(field_name, "")).strip()
        if value:
            parts.append(f"{field_name}={value}")
    return "; ".join(parts)


def _sweep_candidate_validation_args(plan_row: dict[str, Any]) -> str:
    parts: list[str] = []
    for field_name, flag in _SWEEP_CONFIG_CLI_FLAGS.items():
        value = str(plan_row.get(field_name, "")).strip()
        if value:
            parts.append(f"{flag} {value}")
    return " ".join(parts)


def _sweep_candidate_validation_args_from_config_changes(config_changes: str) -> str:
    plan_row: dict[str, str] = {}
    for part in str(config_changes or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            plan_row[key] = value
    return _sweep_candidate_validation_args(plan_row)


_SWEEP_CONFIG_CLI_FLAGS = {
    "cash_buffer_weight": "--cash-buffer-weight",
    "min_train_positive_ratio": "--min-train-positive-ratio",
    "candidate_pool_size": "--candidate-pool-size",
    "market_beta_proxy_max_exposure": "--market-beta-proxy-max-exposure",
    "market_beta_proxy_neutral_breadth_max_exposure": "--market-beta-proxy-neutral-breadth-max-exposure",
    "max_position_weight": "--max-position-weight",
    "drawdown_guard_scale": "--drawdown-guard-scale",
    "drawdown_guard_deep_trigger_pct": "--drawdown-guard-deep-trigger-pct",
    "drawdown_guard_deep_scale": "--drawdown-guard-deep-scale",
    "market_volatility_min_scale": "--market-volatility-min-scale",
    "position_trailing_stop_pct": "--position-trailing-stop-pct",
    "position_trailing_stop_reason_contains": "--position-trailing-stop-reason-contains",
}


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _sanitize_report_token(value: str) -> str:
    token = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(value).strip())
    return token.strip("_") or "candidate"


def _split_cli_args(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return shlex.split(text)


def _format_cli_command(argv: list[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in argv])


def _split_semicolon_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _date_span_days(start: str, end: str) -> int:
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except ValueError:
        return 0


def _candidate_summary_labels(
    decision_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    path_rows: list[dict[str, Any]],
) -> list[str]:
    labels: list[str] = []
    for rows in (decision_rows, delta_rows, path_rows):
        for row in rows:
            label = str(row.get("candidate_label", "")).strip()
            if label and label not in labels:
                labels.append(label)
    if labels:
        return labels
    return ["candidate"] if decision_rows or delta_rows or path_rows else []


def _candidate_summary_rows(
    rows: list[dict[str, Any]],
    label: str,
    all_labels: list[str],
) -> list[dict[str, Any]]:
    if len(all_labels) == 1:
        return [
            row
            for row in rows
            if str(row.get("candidate_label", "")).strip() in {"", label}
        ]
    return [row for row in rows if str(row.get("candidate_label", "")).strip() == label]


def _first_candidate_summary_row(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    matches = _candidate_summary_rows(rows, label, [label])
    return matches[0] if matches else {}


def _candidate_summary_int(row: dict[str, Any], field_name: str, default: int) -> int:
    value = str(row.get(field_name, "")).strip()
    if not value:
        return default
    return _safe_int(value, default=default)


def _candidate_summary_counter_value(value: str, key: str) -> int:
    for part in str(value or "").replace(",", ";").split(";"):
        if "=" not in part:
            continue
        name, raw_count = part.split("=", 1)
        if name.strip() == key:
            return _safe_int(raw_count)
    return 0


def _candidate_summary_diagnostic_summary(rows: list[dict[str, Any]], classification: str) -> str:
    counts = Counter(
        str(row.get("diagnostic", "")).strip()
        for row in rows
        if str(row.get("classification", "")).strip() == classification
        and str(row.get("diagnostic", "")).strip()
    )
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


def _count_diagnostics(values: list[str], token: str) -> int:
    return sum(1 for value in values if token in value)


def _format_counter_counts(counter: Counter[str]) -> str:
    return ";".join(
        f"{name}={count}"
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        if name
    )


def _count_failed_required(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if _parse_bool(row.get("required", True)) and not _parse_bool(row.get("deployable", False))
    )


def _failed_required_names(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("name", "")).strip()
        for row in rows
        if str(row.get("name", "")).strip()
        and _parse_bool(row.get("required", True))
        and not _parse_bool(row.get("deployable", False))
    }


def _min_numeric(values: Any) -> float | None:
    numeric_values = [_float_or_none(value) for value in values]
    numeric_values = [value for value in numeric_values if value is not None]
    return min(numeric_values) if numeric_values else None


def _max_numeric(values: Any) -> float | None:
    numeric_values = [_float_or_none(value) for value in values]
    numeric_values = [value for value in numeric_values if value is not None]
    return max(numeric_values) if numeric_values else None


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _format_equal_symbol_weights(symbols: list[str]) -> str:
    if not symbols:
        return ""
    weight = 1 / len(symbols)
    return ";".join(f"{symbol}:{_format_optional_float(weight)}" for symbol in symbols)


def _numeric_delta(candidate_value: float | None, baseline_value: float | None) -> float | None:
    if candidate_value is None or baseline_value is None:
        return None
    return candidate_value - baseline_value


def _scenario_delta_classification(baseline_failed: bool, candidate_failed: bool) -> str:
    if baseline_failed and not candidate_failed:
        return "RESOLVED"
    if not baseline_failed and candidate_failed:
        return "NEW_FAILURE"
    if baseline_failed and candidate_failed:
        return "UNCHANGED_FAILURE"
    return "UNCHANGED_PASS"


def _scenario_delta_diagnostic(
    classification: str,
    *,
    baseline_reason: str,
    candidate_reason: str,
    excess_delta: float | None,
    drawdown_delta: float | None,
    trade_delta: float | None,
) -> str:
    if classification == "RESOLVED":
        return "candidate_fixed_required_failure"
    if classification == "NEW_FAILURE":
        if candidate_reason == "max_drawdown_breach":
            if drawdown_delta is not None and drawdown_delta < 0:
                if excess_delta is not None and excess_delta >= 0:
                    return "equity_improved_but_drawdown_buffer_worse"
                return "drawdown_buffer_regression"
            return "candidate_introduced_drawdown_breach"
        if candidate_reason == "train_window_rejected":
            return "train_gate_regression"
        if (
            candidate_reason == "negative_excess_return"
            and excess_delta is not None
            and excess_delta < 0
            and (trade_delta is None or trade_delta <= 0)
            and (drawdown_delta is None or drawdown_delta >= 0)
        ):
            return "over_defense_or_filter_drag"
        if (
            candidate_reason == "negative_excess_return"
            and excess_delta is not None
            and excess_delta < 0
            and trade_delta is not None
            and trade_delta > 0
        ):
            return "selection_or_exposure_drag"
        return "candidate_introduced_failure"
    if classification == "UNCHANGED_FAILURE":
        if candidate_reason == baseline_reason:
            return "same_failure_persists"
        return "failure_shifted_reason"
    return "no_required_failure_change"


def _unique_join(values: Any) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return "; ".join(ordered)


def _worst_failure_metric_value(rows: list[dict[str, Any]]) -> str:
    values: list[float] = []
    for row in rows:
        value = _float_or_none(row.get("metric_value"))
        if value is not None:
            values.append(value)
    if not values:
        return ""
    return f"{min(values):.4f}".rstrip("0").rstrip(".")


def _remediation_priority(action: str, blocked_count: int) -> str:
    if action == "REFRESH_OR_EXCLUDE_DATA":
        return "P0"
    if blocked_count > 0:
        return "P1"
    return "P2"


def _remediation_next_experiment(action: str) -> str:
    if action == "IMPROVE_WEAK_WINDOW_DEFENSE":
        return (
            "Run a parameter sweep with higher cash_buffer_weight, stricter min_train_positive_ratio, "
            "and lower candidate_pool_size on only failed weak windows."
        )
    if action == "REDUCE_DRAWDOWN":
        return (
            "Run a drawdown-control sweep with lower max_position_weight, stronger drawdown_guard_scale, "
            "and higher market_volatility_min_scale."
        )
    if action == "KEEP_TRAIN_WINDOW_REJECTED":
        return "Keep the train-window gate blocking this scenario; inspect preset stability before relaxing gates."
    if action == "REFRESH_OR_EXCLUDE_DATA":
        return "Refresh KRX candles, rerun data-check exclusions, then regenerate monthly validation reports."
    return "Review failed scenarios manually before changing deployment gates."


def save_deployment_gate(gate: DeploymentGate, output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DEPLOYMENT_GATE_COLUMNS)
        writer.writeheader()
        writer.writerow({column: getattr(gate, column) for column in DEPLOYMENT_GATE_COLUMNS})
    return 1


def load_deployment_gate(path: Path | str | None) -> DeploymentGate | None:
    if path is None or str(path).strip() == "":
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    row = rows[-1]
    return DeploymentGate(
        deployable=_parse_bool(row.get("deployable", "")),
        reason=str(row.get("reason", "")).strip(),
        source=str(row.get("source", "")).strip(),
        total_return_pct=float(row.get("total_return_pct", 0) or 0),
        buy_hold_return_pct=float(row.get("buy_hold_return_pct", 0) or 0),
        excess_return_pct=float(row.get("excess_return_pct", 0) or 0),
        max_drawdown_pct=float(row.get("max_drawdown_pct", 0) or 0),
        trade_count=int(float(row.get("trade_count", 0) or 0)),
        universe_bias_warning=_parse_bool(row.get("universe_bias_warning", "")),
    )


def target_weights_for_symbols(
    symbols: list[str],
    *,
    target_budget: float,
    max_position_weight: float,
    symbol_multipliers: dict[str, float] | None = None,
) -> dict[str, float]:
    if not symbols or target_budget <= 0:
        return {}
    if not symbol_multipliers:
        equal_weight = target_budget / len(symbols)
        position_weight = min(equal_weight, max_position_weight) if max_position_weight > 0 else equal_weight
        return {symbol: position_weight for symbol in symbols}

    multipliers = {symbol: max(float(symbol_multipliers.get(symbol, 1.0)), 0.0) for symbol in symbols}
    if sum(multipliers.values()) <= 0:
        return {}

    remaining_symbols = list(symbols)
    remaining_budget = target_budget
    weights: dict[str, float] = {}
    while remaining_symbols and remaining_budget > 0:
        total_multiplier = sum(multipliers[symbol] for symbol in remaining_symbols)
        if total_multiplier <= 0:
            break
        uncapped: list[str] = []
        capped_this_round = False
        for symbol in remaining_symbols:
            weight = remaining_budget * multipliers[symbol] / total_multiplier
            if max_position_weight > 0 and weight > max_position_weight:
                weights[symbol] = max_position_weight
                remaining_budget -= max_position_weight
                capped_this_round = True
            else:
                uncapped.append(symbol)
        if not capped_this_round:
            for symbol in remaining_symbols:
                weights[symbol] = remaining_budget * multipliers[symbol] / total_multiplier
            break
        remaining_symbols = uncapped
    return weights


def filter_symbols_by_event_score(
    symbols: list[str],
    *,
    event_scores: EventScoreStore | None,
    signal_date: str,
    lookback_days: int,
    min_entry_event_score: float,
) -> list[str]:
    if event_scores is None:
        return symbols
    return [
        symbol
        for symbol in symbols
        if event_scores.score_window(symbol, signal_date, lookback_days) >= min_entry_event_score
    ]


def event_score_multipliers(
    symbols: list[str],
    *,
    event_scores: EventScoreStore | None,
    signal_date: str,
    lookback_days: int,
    event_weight: float,
    min_multiplier: float = 0.5,
    max_multiplier: float = 1.5,
) -> dict[str, float]:
    if event_scores is None or event_weight <= 0:
        return {symbol: 1.0 for symbol in symbols}
    lower = max(min_multiplier, 0.0)
    upper = max(max_multiplier, lower)
    multipliers: dict[str, float] = {}
    for symbol in symbols:
        score = event_scores.score_window(symbol, signal_date, lookback_days)
        raw_multiplier = 1.0 + score * event_weight
        multipliers[symbol] = min(upper, max(lower, raw_multiplier))
    return multipliers


def scale_monthly_decision_targets(
    decision: MonthlyDecision,
    *,
    scale: float,
    reason_suffix: str,
) -> MonthlyDecision:
    clipped_scale = min(1.0, max(0.0, scale))
    if clipped_scale >= 1.0 or not decision.target_weights:
        return decision
    return MonthlyDecision(
        as_of_date=decision.as_of_date,
        signal_date=decision.signal_date,
        mode=decision.mode,
        selected_preset=decision.selected_preset,
        target_weights={symbol: weight * clipped_scale for symbol, weight in decision.target_weights.items()},
        reason=decision.reason + reason_suffix,
    )


def market_trend_exposure_scale(
    symbol_candles: dict[str, list[Candle]],
    *,
    before_date: str,
    lookback_days: int,
    min_return_pct: float,
    risk_scale: float,
) -> float:
    if lookback_days <= 0:
        return 1.0
    returns: list[float] = []
    for candles in symbol_candles.values():
        prior = [candle for candle in candles if candle.date < before_date and candle.close > 0]
        if len(prior) <= lookback_days:
            continue
        base_price = prior[-lookback_days].close
        if base_price > 0:
            returns.append((prior[-1].close / base_price - 1) * 100)
    if not returns:
        return 1.0
    if median(returns) >= min_return_pct:
        return 1.0
    return min(1.0, max(0.0, risk_scale))


def market_volatility_exposure_scale(
    symbol_candles: dict[str, list[Candle]],
    *,
    before_date: str,
    lookback_days: int,
    target_volatility_pct: float,
    min_scale: float,
) -> float:
    if lookback_days <= 1 or target_volatility_pct <= 0:
        return 1.0
    volatilities: list[float] = []
    for candles in symbol_candles.values():
        prior = [candle for candle in candles if candle.date < before_date and candle.close > 0]
        if len(prior) <= lookback_days:
            continue
        window = prior[-lookback_days:]
        returns = [
            (window[index].close / window[index - 1].close - 1) * 100
            for index in range(1, len(window))
            if window[index - 1].close > 0
        ]
        if len(returns) < 2:
            continue
        avg = sum(returns) / len(returns)
        variance = sum((value - avg) ** 2 for value in returns) / (len(returns) - 1)
        volatilities.append((variance ** 0.5) * (252 ** 0.5))
    if not volatilities:
        return 1.0
    realized_volatility = median(volatilities)
    if realized_volatility <= target_volatility_pct:
        return 1.0
    return min(1.0, max(min_scale, target_volatility_pct / realized_volatility))


def liquidity_universe_exposure_scale(
    *,
    top_n: int,
    reference_top_n: int,
    min_scale: float,
    min_top_n: int,
) -> float:
    if top_n <= 0 or reference_top_n <= 0 or top_n >= reference_top_n:
        return 1.0
    if top_n < max(1, min_top_n):
        return 1.0
    raw_scale = top_n / reference_top_n
    return min(1.0, max(0.0, max(min_scale, raw_scale)))


def _risk_scale_reason_suffix(*, trend_scale: float, volatility_scale: float, liquidity_scale: float) -> str:
    reasons: list[str] = []
    if trend_scale < 1.0:
        reasons.append("trend")
    if volatility_scale < 1.0:
        reasons.append("vol")
    if liquidity_scale < 1.0:
        reasons.append("liquidity")
    if reasons:
        return "_" + "_".join(reasons) + "_scaled"
    return ""


def _monthly_preset_configs(config: MonthlyRebalanceConfig) -> dict[str, MomentumRotationConfig]:
    return {
        preset: _monthly_preset_config_for_name(config, preset)
        for preset in config.presets
    }


def _monthly_preset_config_for_name(config: MonthlyRebalanceConfig, preset: str) -> MomentumRotationConfig:
    preset_config = momentum_rotation_config_for_preset(preset)
    if config.direct_alpha_target_persistence_signals == preset_config.target_persistence_signals:
        return preset_config
    return replace(
        preset_config,
        target_persistence_signals=config.direct_alpha_target_persistence_signals,
    )


def select_buyable_targets(
    ranked_symbols: list[str],
    *,
    reference_prices: dict[str, float],
    portfolio_value: float,
    target_budget: float,
    max_position_weight: float,
    min_target_value: float,
) -> list[str]:
    selected: list[str] = []
    for symbol in ranked_symbols:
        if reference_prices.get(symbol, 0.0) <= 0:
            continue
        trial = selected + [symbol]
        weights = target_weights_for_symbols(
            trial,
            target_budget=target_budget,
            max_position_weight=max_position_weight,
        )
        if all(_target_is_buyable(candidate, weights, reference_prices, portfolio_value, min_target_value) for candidate in trial):
            selected = trial
    return selected


def select_liquid_universe(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    top_n: int,
    window_days: int,
) -> dict[str, list[Candle]]:
    if top_n <= 0:
        return symbol_candles
    selected = set(rank_symbols_by_average_trading_value(symbol_candles, signal_date=signal_date, window_days=window_days)[:top_n])
    return {symbol: candles for symbol, candles in symbol_candles.items() if symbol in selected}


def rank_symbols_by_average_trading_value(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    window_days: int,
) -> list[str]:
    return [
        symbol
        for symbol, _ in rank_symbol_average_trading_values(
            symbol_candles,
            signal_date=signal_date,
            window_days=window_days,
        )
    ]


def rank_symbol_average_trading_values(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    window_days: int,
) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for symbol, candles in symbol_candles.items():
        history = [candle for candle in candles if candle.date <= signal_date]
        if len(history) < window_days:
            continue
        window = history[-window_days:]
        average_trading_value = sum(candle.close * candle.volume for candle in window) / len(window)
        rows.append((symbol, average_trading_value))
    rows.sort(key=lambda row: row[1], reverse=True)
    return rows


def _average_trading_value_rank_map(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    window_days: int,
) -> dict[str, tuple[int, float]]:
    return {
        symbol: (index + 1, average_trading_value)
        for index, (symbol, average_trading_value) in enumerate(
            rank_symbol_average_trading_values(
                symbol_candles,
                signal_date=signal_date,
                window_days=window_days,
            )
        )
    }


def _market_beta_target_weights(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    target_budget: float,
    config: MonthlyRebalanceConfig,
    proxy_max_exposure: float | None = None,
) -> dict[str, float]:
    if target_budget <= 0:
        return {}
    if config.market_beta_symbol in symbol_candles:
        return {config.market_beta_symbol: target_budget}
    if config.market_beta_proxy_size <= 0:
        return {}
    max_proxy_budget = config.market_beta_proxy_max_exposure if proxy_max_exposure is None else proxy_max_exposure
    proxy_target_budget = min(target_budget, max(0.0, max_proxy_budget))
    if proxy_target_budget <= 0:
        return {}
    proxy_symbols = rank_symbols_by_average_trading_value(
        symbol_candles,
        signal_date=signal_date,
        window_days=config.point_in_time_liquidity_window_days,
    )[: config.market_beta_proxy_size]
    return target_weights_for_symbols(
        proxy_symbols,
        target_budget=proxy_target_budget,
        max_position_weight=config.max_position_weight,
    )


def _market_beta_or_cash_decision(
    symbol_candles: dict[str, list[Candle]],
    *,
    as_of_date: str,
    signal_date: str,
    target_budget: float,
    config: MonthlyRebalanceConfig,
    proxy_reason: str,
    direct_reason: str,
    empty_reason: str,
    proxy_max_exposure: float | None = None,
    proxy_cap_reason: str = "proxy_exposure_capped",
    reference_prices: dict[str, float] | None = None,
    portfolio_value: float | None = None,
) -> MonthlyDecision:
    beta_weights = _market_beta_target_weights(
        symbol_candles,
        signal_date=signal_date,
        target_budget=target_budget,
        config=config,
        proxy_max_exposure=proxy_max_exposure,
    )
    if beta_weights:
        is_proxy = config.market_beta_symbol not in beta_weights
        max_proxy_budget = config.market_beta_proxy_max_exposure if proxy_max_exposure is None else proxy_max_exposure
        proxy_capped = (
            is_proxy
            and max(0.0, max_proxy_budget) < target_budget - 1e-12
        )
        decision = MonthlyDecision(
            as_of_date=as_of_date,
            signal_date=signal_date,
            mode="market_beta_proxy" if is_proxy else "market_beta",
            selected_preset="market_beta_proxy" if is_proxy else "market_beta",
            target_weights=beta_weights,
            reason=(
                (proxy_reason + "_" + proxy_cap_reason)
                if proxy_capped
                else (proxy_reason if is_proxy else direct_reason)
            ),
        )
        if is_proxy and reference_prices is not None and portfolio_value is not None:
            if config.market_beta_proxy_unbuyable_cash_reserve:
                return reserve_unbuyable_targets_as_cash(
                    decision,
                    reference_prices=reference_prices,
                    portfolio_value=portfolio_value,
                    min_target_value=config.min_target_value,
                )
            if config.market_beta_proxy_buyable_only:
                return compress_decision_to_buyable_targets(
                    decision,
                    reference_prices=reference_prices,
                    portfolio_value=portfolio_value,
                    max_position_weight=config.max_position_weight,
                    min_target_value=config.min_target_value,
                )
        return decision
    return MonthlyDecision(
        as_of_date=as_of_date,
        signal_date=signal_date,
        mode="cash",
        selected_preset="cash",
        target_weights={},
        reason=empty_reason,
    )


def _market_beta_proxy_effective_cap(
    config: MonthlyRebalanceConfig,
    prior_breadth: float | None,
    *,
    symbol_candles: dict[str, list[Candle]] | None = None,
    signal_date: str | None = None,
) -> tuple[float, str]:
    broad_cap = max(0.0, config.market_beta_proxy_max_exposure)
    effective_cap = broad_cap
    reason = "proxy_exposure_capped"
    if prior_breadth is not None and prior_breadth < config.fallback_breadth_threshold:
        neutral_cap = max(0.0, config.market_beta_proxy_neutral_breadth_max_exposure)
        if neutral_cap < effective_cap:
            effective_cap = neutral_cap
            reason = "proxy_neutral_breadth_capped"
        if symbol_candles is not None and signal_date:
            neutral_loss_cap, neutral_loss_reason = market_beta_proxy_neutral_loss_guard_cap(
                symbol_candles,
                signal_date=signal_date,
                current_cap=effective_cap,
                prior_breadth=prior_breadth,
                config=config,
            )
            if neutral_loss_cap < effective_cap:
                effective_cap = neutral_loss_cap
                reason = neutral_loss_reason
    if symbol_candles is not None and signal_date:
        reversal_cap, reversal_reason = market_beta_proxy_reversal_guard_cap(
            symbol_candles,
            signal_date=signal_date,
            current_cap=effective_cap,
            config=config,
        )
        if reversal_cap < effective_cap:
            return reversal_cap, reversal_reason
    return effective_cap, reason


def market_beta_proxy_neutral_loss_guard_cap(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    current_cap: float,
    prior_breadth: float | None,
    config: MonthlyRebalanceConfig,
) -> tuple[float, str]:
    effective_cap = max(0.0, current_cap)
    if prior_breadth is None or prior_breadth >= config.fallback_breadth_threshold:
        return effective_cap, "proxy_exposure_capped"
    guard_cap = max(0.0, config.market_beta_proxy_neutral_loss_guard_max_exposure)
    medium_days = int(config.market_beta_proxy_neutral_loss_guard_medium_lookback_days)
    if medium_days <= 0 or guard_cap >= effective_cap:
        return effective_cap, "proxy_exposure_capped"

    proxy_symbols = rank_symbols_by_average_trading_value(
        symbol_candles,
        signal_date=signal_date,
        window_days=max(1, config.point_in_time_liquidity_window_days),
    )[: max(0, config.market_beta_proxy_size)]
    medium_return = _average_symbol_return_pct(
        symbol_candles,
        proxy_symbols,
        signal_date=signal_date,
        lookback_days=medium_days,
    )
    if (
        medium_return is None
        or medium_return > config.market_beta_proxy_neutral_loss_guard_medium_max_return_pct
    ):
        return effective_cap, "proxy_exposure_capped"

    short_days = int(config.market_beta_proxy_neutral_loss_guard_short_lookback_days)
    if short_days > 0:
        short_return = _average_symbol_return_pct(
            symbol_candles,
            proxy_symbols,
            signal_date=signal_date,
            lookback_days=short_days,
        )
        if (
            short_return is None
            or short_return > config.market_beta_proxy_neutral_loss_guard_short_max_return_pct
        ):
            return effective_cap, "proxy_exposure_capped"
    return min(effective_cap, guard_cap), "proxy_neutral_loss_guard_capped"


def market_beta_proxy_reversal_guard_cap(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    current_cap: float,
    config: MonthlyRebalanceConfig,
) -> tuple[float, str]:
    effective_cap = max(0.0, current_cap)
    guard_cap = max(0.0, config.market_beta_proxy_reversal_guard_max_exposure)
    medium_days = int(config.market_beta_proxy_reversal_guard_medium_lookback_days)
    if medium_days <= 0 or guard_cap >= effective_cap:
        return effective_cap, "proxy_exposure_capped"

    proxy_symbols = rank_symbols_by_average_trading_value(
        symbol_candles,
        signal_date=signal_date,
        window_days=max(1, config.point_in_time_liquidity_window_days),
    )[: max(0, config.market_beta_proxy_size)]
    medium_return = _average_symbol_return_pct(
        symbol_candles,
        proxy_symbols,
        signal_date=signal_date,
        lookback_days=medium_days,
    )
    if medium_return is None or medium_return < config.market_beta_proxy_reversal_guard_medium_return_pct:
        return effective_cap, "proxy_exposure_capped"

    extreme_trigger = config.market_beta_proxy_reversal_guard_extreme_return_pct
    extreme_overheat = extreme_trigger > 0 and medium_return >= extreme_trigger
    medium_drawdown = _proxy_basket_max_drawdown_pct(
        symbol_candles,
        proxy_symbols,
        signal_date=signal_date,
        lookback_days=medium_days,
    )
    drawdown_trigger = config.market_beta_proxy_reversal_guard_medium_drawdown_pct
    drawdown_allows_cap = (
        drawdown_trigger < 0
        and medium_drawdown is not None
        and medium_drawdown <= drawdown_trigger
    )
    short_days = int(config.market_beta_proxy_reversal_guard_short_lookback_days)
    short_return: float | None = None
    if short_days > 0:
        short_return = _average_symbol_return_pct(
            symbol_candles,
            proxy_symbols,
            signal_date=signal_date,
            lookback_days=short_days,
        )
    if short_days > 0 and not extreme_overheat and not drawdown_allows_cap:
        if (
            short_return is None
            or short_return > config.market_beta_proxy_reversal_guard_short_max_return_pct
        ):
            return effective_cap, "proxy_exposure_capped"
    recovery_exit_trigger = config.market_beta_proxy_reversal_guard_recovery_exit_short_return_pct
    if (
        not extreme_overheat
        and drawdown_allows_cap
        and recovery_exit_trigger < 0
        and short_return is not None
        and short_return <= recovery_exit_trigger
    ):
        return effective_cap, "proxy_reversal_guard_recovery_exit"
    return min(effective_cap, guard_cap), "proxy_reversal_guard_capped"


def _proxy_basket_max_drawdown_pct(
    symbol_candles: dict[str, list[Candle]],
    symbols: list[str],
    *,
    signal_date: str,
    lookback_days: int,
) -> float | None:
    if lookback_days <= 0 or not symbols:
        return None
    normalized_series: list[dict[str, float]] = []
    all_dates: set[str] = set()
    for symbol in symbols:
        history = [
            candle
            for candle in sorted(symbol_candles.get(symbol, []), key=lambda candle: candle.date)
            if candle.date <= signal_date and candle.close > 0
        ]
        if len(history) <= lookback_days:
            continue
        window = history[-lookback_days - 1:]
        base_price = window[0].close
        if base_price <= 0:
            continue
        series = {candle.date: candle.close / base_price for candle in window}
        normalized_series.append(series)
        all_dates.update(series)
    if not normalized_series:
        return None
    min_observations = max(1, len(normalized_series) // 2)
    basket_values: list[float] = []
    for day in sorted(all_dates):
        day_values = [series[day] for series in normalized_series if day in series]
        if len(day_values) >= min_observations:
            basket_values.append(sum(day_values) / len(day_values))
    if not basket_values:
        return None
    peak = basket_values[0]
    worst_drawdown = 0.0
    for value in basket_values:
        if value > peak:
            peak = value
        if peak > 0:
            worst_drawdown = min(worst_drawdown, (value / peak - 1.0) * 100.0)
    return worst_drawdown


def _average_symbol_return_pct(
    symbol_candles: dict[str, list[Candle]],
    symbols: list[str],
    *,
    signal_date: str,
    lookback_days: int,
) -> float | None:
    returns: list[float] = []
    if lookback_days <= 0:
        return None
    for symbol in symbols:
        history = [
            candle
            for candle in sorted(symbol_candles.get(symbol, []), key=lambda candle: candle.date)
            if candle.date <= signal_date and candle.close > 0
        ]
        if len(history) <= lookback_days:
            continue
        start_price = history[-lookback_days - 1].close
        end_price = history[-1].close
        if start_price > 0:
            returns.append((end_price / start_price - 1.0) * 100.0)
    return sum(returns) / len(returns) if returns else None


def select_point_in_time_universe(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    min_history_days: int,
    min_reference_price: float,
    max_trailing_return_pct: float,
    trailing_return_days: int,
) -> dict[str, list[Candle]]:
    selected: dict[str, list[Candle]] = {}
    for symbol, candles in symbol_candles.items():
        history = [candle for candle in sorted(candles, key=lambda candle: candle.date) if candle.date <= signal_date]
        if len(history) < min_history_days:
            continue
        if any(_has_nonpositive_price(candle) for candle in history):
            continue
        reference_price = history[-1].close
        if reference_price < min_reference_price:
            continue
        if trailing_return_days > 1 and len(history) >= trailing_return_days:
            base_price = history[-trailing_return_days].close
            if base_price > 0:
                trailing_return_pct = (reference_price / base_price - 1) * 100
                if trailing_return_pct > max_trailing_return_pct:
                    continue
        selected[symbol] = candles
    return selected


def load_point_in_time_universe(path: Path | str) -> PointInTimeUniverse:
    snapshots: dict[str, set[str]] = {}
    members_by_date: dict[str, list[UniverseMember]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        if not fieldnames or "symbol" not in fieldnames or not ({"date", "snapshot_date"} & fieldnames):
            raise RuntimeError("point-in-time universe CSV must include date/snapshot_date and symbol columns")
        for row in reader:
            snapshot_date = _normalize_date_value(row.get("snapshot_date") or row.get("date", ""))
            symbol = _normalize_symbol_code(row.get("symbol", ""))
            name = str(row.get("name", "") or "").strip()
            if not snapshot_date or not symbol:
                continue
            snapshots.setdefault(snapshot_date, set()).add(symbol)
            members_by_date.setdefault(snapshot_date, []).append(
                UniverseMember(
                    snapshot_date=snapshot_date,
                    symbol=symbol,
                    name=name,
                    market=str(row.get("market", "") or "").strip(),
                    listed_date=_normalize_date_value(row.get("listed_date", "")),
                    delisted_date=_normalize_date_value(row.get("delisted_date", "")),
                    is_active=str(row.get("is_active", "") or "").strip(),
                    is_suspended=str(row.get("is_suspended", "") or "").strip(),
                    is_managed=str(row.get("is_managed", "") or "").strip(),
                    is_spac=str(row.get("is_spac", "") or "").strip() or ("true" if _looks_like_spac(name) else ""),
                    is_preferred=str(row.get("is_preferred", "") or "").strip() or ("true" if _looks_like_preferred_stock(name) else ""),
                    tradable=str(row.get("tradable", "") or "").strip(),
                )
            )
    return PointInTimeUniverse(snapshots, members_by_date=members_by_date)


def filter_symbol_candles_by_universe(
    symbol_candles: dict[str, list[Candle]],
    universe_by_date: dict[str, set[str]] | None,
    *,
    signal_date: str,
    min_history_days: int = 0,
) -> dict[str, list[Candle]]:
    if not universe_by_date:
        return symbol_candles
    eligible_date = max((date for date in universe_by_date if date <= signal_date), default="")
    if not eligible_date:
        return {}
    eligible_symbols, _ = _eligible_universe_symbols(
        symbol_candles,
        universe_by_date,
        snapshot_date=eligible_date,
        as_of_date=signal_date,
        min_history_days=min_history_days,
    )
    return {symbol: candles for symbol, candles in symbol_candles.items() if symbol in eligible_symbols}


def build_universe_filter_report(
    symbol_candles: dict[str, list[Candle]],
    universe_by_date: dict[str, set[str]] | None,
    *,
    as_of_dates: list[str],
    min_history_days: int = 0,
) -> list[dict[str, Any]]:
    if not universe_by_date:
        return []
    rows: list[dict[str, Any]] = []
    for as_of_date in sorted({date for date in as_of_dates if date}):
        snapshot_date = max((date for date in universe_by_date if date <= as_of_date), default="")
        if not snapshot_date:
            continue
        _, excluded = _eligible_universe_symbols(
            symbol_candles,
            universe_by_date,
            snapshot_date=snapshot_date,
            as_of_date=as_of_date,
            min_history_days=min_history_days,
        )
        rows.extend(excluded)
    rows.sort(key=lambda row: (str(row.get("as_of_date", "")), str(row.get("symbol", "")), str(row.get("reason", ""))))
    return rows


def monthly_rebalance_signal_dates(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
) -> list[str]:
    candles_by_symbol = {
        symbol: sorted(candles, key=lambda candle: candle.date)
        for symbol, candles in symbol_candles.items()
        if candles
    }
    dates = sorted(
        {
            candle.date
            for candles in candles_by_symbol.values()
            for candle in candles
            if start <= candle.date <= end
        }
    )
    signal_dates: list[str] = []
    for current_date in _first_trading_dates_by_month(dates):
        asof_candles = _candles_before_date(candles_by_symbol, current_date)
        if asof_candles:
            signal_dates.append(latest_signal_date(asof_candles, as_of_date=current_date))
    return sorted(set(signal_dates))


def _eligible_universe_symbols(
    symbol_candles: dict[str, list[Candle]],
    universe_by_date: dict[str, set[str]],
    *,
    snapshot_date: str,
    as_of_date: str,
    min_history_days: int,
) -> tuple[set[str], list[dict[str, Any]]]:
    selected: set[str] = set()
    excluded: list[dict[str, Any]] = []
    members = _universe_members_for_snapshot(universe_by_date, snapshot_date)
    for member in members:
        reason, detail = _universe_member_exclusion_reason(
            member,
            symbol_candles.get(member.symbol, []),
            as_of_date=as_of_date,
            min_history_days=min_history_days,
        )
        if reason:
            excluded.append(
                {
                    "as_of_date": as_of_date,
                    "snapshot_date": member.snapshot_date,
                    "symbol": member.symbol,
                    "name": member.name,
                    "market": member.market,
                    "status": "EXCLUDED",
                    "reason": reason,
                    "detail": detail,
                }
            )
            continue
        selected.add(member.symbol)
    return selected, excluded


def _universe_members_for_snapshot(
    universe_by_date: dict[str, set[str]],
    snapshot_date: str,
) -> list[UniverseMember]:
    if isinstance(universe_by_date, PointInTimeUniverse):
        members = universe_by_date.members_by_date.get(snapshot_date)
        if members is not None:
            return members
    return [
        UniverseMember(snapshot_date=snapshot_date, symbol=symbol)
        for symbol in sorted(universe_by_date.get(snapshot_date, set()))
    ]


def _universe_member_exclusion_reason(
    member: UniverseMember,
    candles: list[Candle],
    *,
    as_of_date: str,
    min_history_days: int,
) -> tuple[str, str]:
    if member.snapshot_date > as_of_date:
        return "future_snapshot", f"snapshot_date={member.snapshot_date}; as_of_date={as_of_date}"
    if member.listed_date and member.listed_date > as_of_date:
        return "not_listed", f"listed_date={member.listed_date}; as_of_date={as_of_date}"
    if member.delisted_date and member.delisted_date <= as_of_date:
        return "delisted", f"delisted_date={member.delisted_date}; as_of_date={as_of_date}"
    if member.is_active and _metadata_is_false(member.is_active):
        return "inactive", f"is_active={member.is_active}"
    if member.tradable and _metadata_is_false(member.tradable):
        return "not_tradable", f"tradable={member.tradable}"
    if _parse_bool(member.is_suspended):
        return "suspended", f"is_suspended={member.is_suspended}"
    if _parse_bool(member.is_managed):
        return "managed", f"is_managed={member.is_managed}"
    if _parse_bool(member.is_spac):
        return "spac", f"is_spac={member.is_spac}"
    if _parse_bool(member.is_preferred):
        return "preferred", f"is_preferred={member.is_preferred}"
    if min_history_days > 0:
        history = [candle for candle in sorted(candles, key=lambda candle: candle.date) if candle.date <= as_of_date]
        if len(history) < min_history_days:
            return "insufficient_history", f"history_rows={len(history)}; required={min_history_days}"
    return "", ""


def _normalize_symbol_code(value: Any) -> str:
    text = str(value).strip().strip("'").strip('"')
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text.upper()


def _looks_like_spac(name: str) -> bool:
    normalized = str(name or "").replace(" ", "").upper()
    return "스팩" in normalized or normalized.endswith("SPAC") or " SPAC" in normalized


def _looks_like_preferred_stock(name: str) -> bool:
    normalized = str(name or "").replace(" ", "").upper()
    if not normalized:
        return False
    return (
        normalized.endswith("우")
        or normalized.endswith("우B")
        or normalized.endswith("1우")
        or normalized.endswith("2우")
        or normalized.endswith("3우")
    )


def _normalize_date_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ""


def _metadata_is_false(value: Any) -> bool:
    return str(value).strip().lower() in {"0", "false", "no", "n", "f"}


def exclude_invalid_price_symbols(symbol_candles: dict[str, list[Candle]]) -> dict[str, list[Candle]]:
    return {
        symbol: candles
        for symbol, candles in symbol_candles.items()
        if candles and not any(_has_nonpositive_price(candle) for candle in candles)
    }


def _has_nonpositive_price(candle: Candle) -> bool:
    return candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0


def _position_trailing_stop_decision_matches(
    decision: MonthlyDecision,
    config: MonthlyRebalanceConfig,
) -> bool:
    reason_filter = config.position_trailing_stop_reason_contains.strip()
    return not reason_filter or reason_filter in decision.reason


def run_monthly_rebalance_backtest(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    config: MonthlyRebalanceConfig | None = None,
    initial_cash: float = 10_000_000.0,
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
    min_trade_value: float = 10_000.0,
    decision_provider: Callable[..., MonthlyDecision] | None = None,
) -> MonthlyBacktestResult:
    cfg = config or MonthlyRebalanceConfig()
    candles_by_symbol = {
        symbol: sorted(candles, key=lambda candle: candle.date)
        for symbol, candles in symbol_candles.items()
        if candles
    }
    dates = sorted(
        {
            candle.date
            for candles in candles_by_symbol.values()
            for candle in candles
            if start <= candle.date <= end
        }
    )
    if not dates:
        raise ValueError("no candle data in requested backtest period")

    provider = decision_provider or decide_monthly_allocation
    rebalance_dates = set(_first_trading_dates_by_month(dates))
    candles_by_symbol_date = {
        symbol: {candle.date: candle for candle in candles}
        for symbol, candles in candles_by_symbol.items()
    }
    cash = initial_cash
    positions: dict[str, int] = {}
    last_prices: dict[str, float] = {}
    decisions: list[MonthlyDecision] = []
    trades: list[MonthlyBacktestTrade] = []
    equity_curve: list[float] = []
    curve_dates: list[str] = []
    drawdown_stop_pending = False
    drawdown_stop_cooldown_remaining = 0
    position_peak_prices: dict[str, float] = {}
    position_stop_pending: set[str] = set()
    position_stop_eligible_symbols: set[str] = set()

    for current_date in dates:
        day_candles = {
            symbol: by_date[current_date]
            for symbol, by_date in candles_by_symbol_date.items()
            if current_date in by_date
        }
        if position_stop_pending:
            cash, position_stop_trades, stopped_symbols = _execute_symbol_liquidation(
                current_date,
                position_stop_pending,
                positions,
                cash,
                day_candles,
                fee_rate=fee_rate,
                tax_rate=tax_rate,
                slippage_rate=slippage_rate,
                reason="position_trailing_stop",
            )
            trades.extend(position_stop_trades)
            position_stop_pending.difference_update(stopped_symbols)
            for symbol in stopped_symbols:
                position_peak_prices.pop(symbol, None)
                position_stop_eligible_symbols.discard(symbol)

        if drawdown_stop_pending:
            cash, stop_trades = _execute_full_liquidation(
                current_date,
                positions,
                cash,
                day_candles,
                fee_rate=fee_rate,
                tax_rate=tax_rate,
                slippage_rate=slippage_rate,
                reason="daily_drawdown_stop",
            )
            trades.extend(stop_trades)
            if not positions:
                drawdown_stop_pending = False
                drawdown_stop_cooldown_remaining = max(0, cfg.daily_drawdown_cooldown_days)
                position_stop_pending.clear()
                position_peak_prices.clear()

        if current_date in rebalance_dates:
            asof_candles = _candles_before_date(candles_by_symbol, current_date)
            if asof_candles:
                try:
                    if drawdown_stop_cooldown_remaining > 0:
                        decision = MonthlyDecision(
                            as_of_date=current_date,
                            signal_date=latest_signal_date(asof_candles, as_of_date=current_date),
                            mode="cash",
                            selected_preset="cash",
                            target_weights={},
                            reason="drawdown_stop_cooldown",
                        )
                    elif decision_provider is None:
                        reference_prices = latest_reference_prices(asof_candles, as_of_date=current_date)
                        portfolio_value = _portfolio_value(cash, positions, reference_prices)
                        decision = provider(
                            asof_candles,
                            as_of_date=current_date,
                            config=cfg,
                            portfolio_value=portfolio_value,
                            reference_prices=reference_prices,
                        )
                    else:
                        decision = provider(asof_candles, as_of_date=current_date, config=cfg)
                    current_peak = max([initial_cash, *equity_curve]) if equity_curve else initial_cash
                    current_equity = _portfolio_value(cash, positions, last_prices) if last_prices else cash
                    current_drawdown_pct = (current_equity / current_peak - 1) * 100 if current_peak > 0 else 0.0
                    if (
                        cfg.drawdown_guard_trigger_pct < 0
                        and current_drawdown_pct <= cfg.drawdown_guard_trigger_pct
                    ):
                        drawdown_guard_scale = cfg.drawdown_guard_scale
                        drawdown_guard_suffix = "_drawdown_guard"
                        if (
                            cfg.drawdown_guard_deep_trigger_pct < 0
                            and current_drawdown_pct <= cfg.drawdown_guard_deep_trigger_pct
                        ):
                            drawdown_guard_scale = min(
                                drawdown_guard_scale,
                                cfg.drawdown_guard_deep_scale,
                            )
                            drawdown_guard_suffix = "_deep_drawdown_guard"
                        decision = scale_monthly_decision_targets(
                            decision,
                            scale=drawdown_guard_scale,
                            reason_suffix=drawdown_guard_suffix,
                        )
                except ValueError as exc:
                    decision = MonthlyDecision(
                        as_of_date=current_date,
                        signal_date=latest_signal_date(asof_candles, as_of_date=current_date),
                        mode="cash",
                        selected_preset="cash",
                        target_weights={},
                        reason=f"decision_error:{exc}",
                    )
                cash, executed = _execute_monthly_rebalance(
                    current_date,
                    decision,
                    positions,
                    cash,
                    day_candles,
                    last_prices,
                    fee_rate=fee_rate,
                    tax_rate=tax_rate,
                    slippage_rate=slippage_rate,
                    min_trade_value=min_trade_value,
                )
                decisions.append(decision)
                trades.extend(executed)
                if cfg.position_trailing_stop_pct < 0:
                    target_symbols = set(decision.target_weights)
                    if _position_trailing_stop_decision_matches(decision, cfg):
                        position_stop_eligible_symbols.update(
                            symbol for symbol in target_symbols if positions.get(symbol, 0) > 0
                        )
                    elif cfg.position_trailing_stop_reason_contains.strip():
                        position_stop_eligible_symbols.difference_update(target_symbols)
                    position_stop_eligible_symbols = {
                        symbol for symbol in position_stop_eligible_symbols if positions.get(symbol, 0) > 0
                    }

        for symbol, candle in day_candles.items():
            if candle.close > 0:
                last_prices[symbol] = candle.close
        position_peak_prices = {
            symbol: peak
            for symbol, peak in position_peak_prices.items()
            if positions.get(symbol, 0) > 0
        }
        if cfg.position_trailing_stop_pct < 0:
            for symbol, quantity in positions.items():
                if quantity <= 0:
                    continue
                if (
                    cfg.position_trailing_stop_reason_contains.strip()
                    and symbol not in position_stop_eligible_symbols
                ):
                    continue
                candle = day_candles.get(symbol)
                close_price = candle.close if candle and candle.close > 0 else last_prices.get(symbol, 0.0)
                if close_price <= 0:
                    continue
                peak_price = max(position_peak_prices.get(symbol, close_price), close_price)
                position_peak_prices[symbol] = peak_price
                position_drawdown_pct = (close_price / peak_price - 1.0) * 100.0 if peak_price > 0 else 0.0
                if position_drawdown_pct <= cfg.position_trailing_stop_pct:
                    position_stop_pending.add(symbol)
        else:
            for symbol, quantity in positions.items():
                candle = day_candles.get(symbol)
                close_price = candle.close if candle and candle.close > 0 else last_prices.get(symbol, 0.0)
                if quantity > 0 and close_price > 0:
                    position_peak_prices[symbol] = max(position_peak_prices.get(symbol, close_price), close_price)
        end_of_day_equity = _portfolio_value(cash, positions, last_prices)
        equity_curve.append(end_of_day_equity)
        curve_dates.append(current_date)
        current_peak = max([initial_cash, *equity_curve])
        current_drawdown_pct = (end_of_day_equity / current_peak - 1) * 100 if current_peak > 0 else 0.0
        if (
            positions
            and cfg.daily_drawdown_stop_pct < 0
            and current_drawdown_pct <= cfg.daily_drawdown_stop_pct
        ):
            drawdown_stop_pending = True
        if drawdown_stop_cooldown_remaining > 0:
            drawdown_stop_cooldown_remaining -= 1

    final_equity = equity_curve[-1]
    total_return_pct = (final_equity / initial_cash - 1) * 100
    buy_hold_return_pct = equal_weight_buy_hold_period_return(
        candles_by_symbol,
        start=start,
        end=end,
        initial_cash=initial_cash,
        fee_rate=fee_rate,
        tax_rate=tax_rate,
        slippage_rate=slippage_rate,
    )
    return MonthlyBacktestResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        excess_return_pct=total_return_pct - buy_hold_return_pct,
        max_drawdown_pct=_max_drawdown_pct(equity_curve),
        trade_count=len(trades),
        decisions=decisions,
        trades=trades,
        dates=curve_dates,
        equity_curve=equity_curve,
    )


def latest_signal_date(symbol_candles: dict[str, list[Candle]], *, as_of_date: str) -> str:
    dates = sorted({candle.date for candles in symbol_candles.values() for candle in candles if candle.date < as_of_date})
    if not dates:
        raise ValueError("no candle data before as_of_date")
    return dates[-1]


def latest_reference_prices(symbol_candles: dict[str, list[Candle]], *, as_of_date: str) -> dict[str, float]:
    signal_date = latest_signal_date(symbol_candles, as_of_date=as_of_date)
    prices: dict[str, float] = {}
    for symbol, candles in symbol_candles.items():
        prior = [candle for candle in candles if candle.date <= signal_date and candle.close > 0]
        if prior:
            prices[symbol] = prior[-1].close
    return prices


def load_positions(path: Path | str | None) -> list[Position]:
    if path is None:
        return []
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [
            Position(
                symbol=str(row.get("symbol", "")).strip(),
                quantity=int(float(row.get("quantity", 0) or 0)),
                average_price=float(row.get("average_price", 0) or 0),
            )
            for row in reader
            if str(row.get("symbol", "")).strip()
        ]


def save_order_plan(rows: list[PlannedOrder], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in ORDER_COLUMNS})
    return len(rows)


def save_order_plan_summary(
    *,
    decision: MonthlyDecision,
    orders: list[PlannedOrder],
    risk_checks: list[RiskCheck],
    risk_status_value: str,
    output_path: Path | str,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = str(risk_status_value).strip().upper()
    execution_ready = normalized == "PASS" and all(order.execution_allowed for order in orders)
    status_text = "LIVE_READY" if execution_ready else "BLOCKED"
    buy_orders = [order for order in orders if order.action == "BUY"]
    sell_orders = [order for order in orders if order.action == "SELL"]
    blocked_orders = [order for order in orders if not order.execution_allowed]
    lines = [
        "# Monthly Order Plan Summary",
        "",
        f"Execution status: {status_text}",
        f"Risk status: {normalized}",
        f"As of: {decision.as_of_date}",
        f"Signal date: {decision.signal_date}",
        f"Mode: {decision.mode}",
        f"Selected preset: {decision.selected_preset}",
        f"Decision reason: {decision.reason}",
        "",
        "## Order Totals",
        "",
        f"Orders: {len(orders)}",
        f"BUY orders: {len(buy_orders)}",
        f"SELL orders: {len(sell_orders)}",
        f"Blocked orders: {len(blocked_orders)}",
        f"Total buy value: {sum(order.estimated_value for order in buy_orders):.0f}",
        f"Total sell value: {sum(order.estimated_value for order in sell_orders):.0f}",
        "",
        "## Risk Checks",
        "",
    ]
    if risk_checks:
        for check in risk_checks:
            lines.append(f"- {check.name}: {check.status} - {check.detail}")
    else:
        lines.append("- none")
    lines.extend(["", "## Block Reasons", ""])
    risk_block_reasons = [
        f"{check.name}: {check.detail}"
        for check in risk_checks
        if str(check.status).strip().upper() in {"BLOCK", "WARN"}
    ]
    if blocked_orders:
        for order in blocked_orders:
            lines.append(
                f"- {order.symbol} {order.action} {order.quantity}: {order.execution_block_reason}"
            )
    if risk_block_reasons:
        for reason in risk_block_reasons:
            lines.append(f"- {reason}")
    if not blocked_orders and not risk_block_reasons:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_monthly_decision(decision: MonthlyDecision, output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "as_of_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "mode": decision.mode,
                "selected_preset": decision.selected_preset,
                "reason": decision.reason,
                "target_weights": ";".join(
                    f"{symbol}:{weight:.6f}" for symbol, weight in decision.target_weights.items()
                ),
            }
        )
    return 1


def load_last_rebalance_date(path: Path | str | None) -> str | None:
    if path is None:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    return str(rows[-1].get("last_rebalance_date", "")).strip() or None


def save_rebalance_state(decision: MonthlyDecision, output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STATE_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "last_rebalance_date": decision.as_of_date,
                "signal_date": decision.signal_date,
                "mode": decision.mode,
                "selected_preset": decision.selected_preset,
                "reason": decision.reason,
            }
        )
    return 1


def _train_candidate_rows(
    symbol_candles: dict[str, list[Candle]],
    *,
    train_candles: dict[str, list[Candle]],
    train_start: str,
    train_end: str,
    preset_configs: dict[str, MomentumRotationConfig],
    min_rows_per_window: int,
    start_grace_days: int,
    train_stability_years: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset, preset_config in preset_configs.items():
        result = run_momentum_rotation_backtest(train_candles, preset_config)
        row = {
            "preset": preset,
            "total_return_pct": round(result.total_return_pct, 4),
            "buy_hold_return_pct": round(result.buy_hold_return_pct, 4),
            "excess_return_pct": round(result.excess_return_pct, 4),
            "max_drawdown_pct": round(result.max_drawdown_pct, 4),
            "trades": result.trade_count,
        }
        _add_stability_metrics(
            row,
            symbol_candles,
            train_start=train_start,
            train_end=train_end,
            preset_config=preset_config,
            min_rows_per_window=min_rows_per_window,
            start_grace_days=start_grace_days,
            train_stability_years=train_stability_years,
        )
        rows.append(row)
    return rows


def _add_stability_metrics(
    row: dict[str, Any],
    symbol_candles: dict[str, list[Candle]],
    *,
    train_start: str,
    train_end: str,
    preset_config: MomentumRotationConfig,
    min_rows_per_window: int,
    start_grace_days: int,
    train_stability_years: int,
) -> None:
    excess_values: list[float] = []
    positive_count = 0
    for window in generate_train_stability_windows(train_start, train_end, stability_years=train_stability_years):
        sub_candles = slice_asof_symbol_candles(
            symbol_candles,
            start=window.train_start,
            end=window.train_end,
            min_rows=min_rows_per_window,
            start_grace_days=start_grace_days,
        )
        if not sub_candles:
            continue
        result = run_momentum_rotation_backtest(sub_candles, preset_config)
        excess_values.append(result.excess_return_pct)
        if result.excess_return_pct > 0 and result.trade_count > 0:
            positive_count += 1
    count = len(excess_values)
    row["train_subwindows"] = count
    row["train_positive_subwindows"] = positive_count
    row["train_positive_ratio"] = round(positive_count / count, 4) if count else 0.0
    row["train_avg_subwindow_excess_pct"] = round(sum(excess_values) / count, 4) if count else 0.0
    row["train_worst_subwindow_excess_pct"] = round(min(excess_values), 4) if count else 0.0


def _default_train_start(signal_date: str, train_years: int) -> str:
    signal_year = date.fromisoformat(signal_date).year
    return f"{signal_year - train_years + 1:04d}-01-01"


def _first_trading_dates_by_month(dates: list[str]) -> list[str]:
    first_dates: dict[str, str] = {}
    for value in dates:
        first_dates.setdefault(value[:7], value)
    return list(first_dates.values())


def _target_is_buyable(
    symbol: str,
    weights: dict[str, float],
    reference_prices: dict[str, float],
    portfolio_value: float,
    min_target_value: float,
) -> bool:
    target_value = portfolio_value * weights.get(symbol, 0.0)
    return target_value >= min_target_value and target_value >= reference_prices.get(symbol, 0.0)


def _candles_before_date(symbol_candles: dict[str, list[Candle]], before_date: str) -> dict[str, list[Candle]]:
    result: dict[str, list[Candle]] = {}
    for symbol, candles in symbol_candles.items():
        prior = [candle for candle in candles if candle.date < before_date]
        if prior:
            result[symbol] = prior
    return result


def _execute_monthly_rebalance(
    trade_date: str,
    decision: MonthlyDecision,
    positions: dict[str, int],
    cash: float,
    day_candles: dict[str, Candle],
    last_prices: dict[str, float],
    *,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
    min_trade_value: float,
) -> tuple[float, list[MonthlyBacktestTrade]]:
    valuation_prices = {
        symbol: candle.open
        for symbol, candle in day_candles.items()
        if candle.open > 0
    }
    for symbol, price in last_prices.items():
        valuation_prices.setdefault(symbol, price)
    portfolio_value = _portfolio_value(cash, positions, valuation_prices)
    symbols = sorted(set(positions) | set(decision.target_weights))
    trades: list[MonthlyBacktestTrade] = []

    for symbol in symbols:
        quantity = positions.get(symbol, 0)
        if quantity <= 0:
            continue
        open_price = day_candles.get(symbol).open if symbol in day_candles else 0.0
        if open_price <= 0:
            continue
        target_value = portfolio_value * decision.target_weights.get(symbol, 0.0)
        current_value = quantity * open_price
        delta_value = target_value - current_value
        if delta_value >= -min_trade_value:
            continue
        sell_quantity = min(quantity, int(abs(delta_value) / open_price))
        if sell_quantity <= 0:
            continue
        fill_price = open_price * (1 - slippage_rate)
        gross = sell_quantity * fill_price
        cash += gross - gross * fee_rate - gross * tax_rate
        remaining = quantity - sell_quantity
        if remaining:
            positions[symbol] = remaining
        else:
            positions.pop(symbol, None)
        trades.append(
            MonthlyBacktestTrade(
                date=trade_date,
                symbol=symbol,
                action="SELL",
                price=fill_price,
                quantity=sell_quantity,
                cash_after=cash,
                reason=decision.reason,
            )
        )

    for symbol in symbols:
        open_price = day_candles.get(symbol).open if symbol in day_candles else 0.0
        if open_price <= 0:
            continue
        target_value = portfolio_value * decision.target_weights.get(symbol, 0.0)
        current_value = positions.get(symbol, 0) * open_price
        delta_value = target_value - current_value
        if delta_value < min_trade_value:
            continue
        fill_price = open_price * (1 + slippage_rate)
        cost_per_share = fill_price * (1 + fee_rate)
        buy_quantity = min(int(delta_value / cost_per_share), int(cash / cost_per_share))
        if buy_quantity <= 0:
            continue
        cash -= buy_quantity * cost_per_share
        positions[symbol] = positions.get(symbol, 0) + buy_quantity
        trades.append(
            MonthlyBacktestTrade(
                date=trade_date,
                symbol=symbol,
                action="BUY",
                price=fill_price,
                quantity=buy_quantity,
                cash_after=cash,
                reason=decision.reason,
            )
        )

    return cash, trades


def _execute_full_liquidation(
    trade_date: str,
    positions: dict[str, int],
    cash: float,
    day_candles: dict[str, Candle],
    *,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
    reason: str,
) -> tuple[float, list[MonthlyBacktestTrade]]:
    trades: list[MonthlyBacktestTrade] = []
    for symbol in sorted(list(positions)):
        quantity = positions.get(symbol, 0)
        candle = day_candles.get(symbol)
        if quantity <= 0 or candle is None or candle.open <= 0:
            continue
        fill_price = candle.open * (1 - slippage_rate)
        gross = quantity * fill_price
        cash += gross - gross * fee_rate - gross * tax_rate
        positions.pop(symbol, None)
        trades.append(
            MonthlyBacktestTrade(
                date=trade_date,
                symbol=symbol,
                action="SELL",
                price=fill_price,
                quantity=quantity,
                cash_after=cash,
                reason=reason,
            )
        )
    return cash, trades


def _execute_symbol_liquidation(
    trade_date: str,
    symbols: set[str],
    positions: dict[str, int],
    cash: float,
    day_candles: dict[str, Candle],
    *,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
    reason: str,
) -> tuple[float, list[MonthlyBacktestTrade], set[str]]:
    trades: list[MonthlyBacktestTrade] = []
    sold_symbols: set[str] = set()
    for symbol in sorted(symbols):
        quantity = positions.get(symbol, 0)
        candle = day_candles.get(symbol)
        if quantity <= 0:
            sold_symbols.add(symbol)
            continue
        if candle is None or candle.open <= 0:
            continue
        fill_price = candle.open * (1 - slippage_rate)
        gross = quantity * fill_price
        cash += gross - gross * fee_rate - gross * tax_rate
        positions.pop(symbol, None)
        sold_symbols.add(symbol)
        trades.append(
            MonthlyBacktestTrade(
                date=trade_date,
                symbol=symbol,
                action="SELL",
                price=fill_price,
                quantity=quantity,
                cash_after=cash,
                reason=reason,
            )
        )
    return cash, trades, sold_symbols


def _portfolio_value(cash: float, positions: dict[str, int], prices: dict[str, float]) -> float:
    return cash + sum(quantity * prices.get(symbol, 0.0) for symbol, quantity in positions.items())


def equal_weight_buy_hold_period_return(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    initial_cash: float,
    fee_rate: float,
    tax_rate: float,
    slippage_rate: float,
) -> float:
    tradeable_pairs: list[tuple[Candle, Candle]] = []
    for candles in symbol_candles.values():
        first = next((candle for candle in candles if start <= candle.date <= end and candle.open > 0), None)
        last = next((candle for candle in reversed(candles) if start <= candle.date <= end and candle.close > 0), None)
        if first is not None and last is not None and first.date <= last.date:
            tradeable_pairs.append((first, last))
    if not tradeable_pairs:
        return 0.0
    per_symbol_cash = initial_cash / len(tradeable_pairs)
    final_equity = 0.0
    for first, last in tradeable_pairs:
        fill_price = first.open * (1 + slippage_rate)
        quantity = per_symbol_cash / (fill_price * (1 + fee_rate))
        exit_price = last.close * (1 - slippage_rate)
        gross = quantity * exit_price
        final_equity += gross - gross * fee_rate - gross * tax_rate
    return (final_equity / initial_cash - 1) * 100


def diagnose_universe_bias(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    extreme_return_threshold_pct: float = 500.0,
) -> dict[str, Any]:
    rows = _period_symbol_returns(symbol_candles, start=start, end=end)
    if not rows:
        return {
            "symbol_count": 0,
            "average_symbol_return_pct": 0.0,
            "median_symbol_return_pct": 0.0,
            "extreme_return_symbols": 0,
            "extreme_return_share": 0.0,
            "warning_reasons": [],
            "warning": False,
        }
    returns = [row[1] for row in rows]
    extreme_count = sum(1 for _, value in rows if value >= extreme_return_threshold_pct)
    extreme_share = extreme_count / len(rows)
    average_return = mean(returns)
    median_return = median(returns)
    warning_reasons: list[str] = []
    if average_return >= 100.0:
        warning_reasons.append("high_average_symbol_return")
    if median_return >= 50.0:
        warning_reasons.append("high_median_symbol_return")
    if extreme_share >= 0.05:
        warning_reasons.append("extreme_return_share")
    return {
        "symbol_count": len(rows),
        "average_symbol_return_pct": round(average_return, 4),
        "median_symbol_return_pct": round(median_return, 4),
        "extreme_return_symbols": extreme_count,
        "extreme_return_share": round(extreme_share, 4),
        "warning_reasons": warning_reasons,
        "warning": bool(warning_reasons),
    }


def _format_universe_bias_reasons(bias: dict[str, Any]) -> str:
    reasons = bias.get("warning_reasons", [])
    if isinstance(reasons, str):
        return reasons
    return ";".join(str(reason) for reason in reasons)


def exclude_extreme_period_return_symbols(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    max_period_return_pct: float,
) -> dict[str, list[Candle]]:
    excluded = {
        symbol
        for symbol, period_return in _period_symbol_returns(symbol_candles, start=start, end=end)
        if period_return > max_period_return_pct
    }
    return {symbol: candles for symbol, candles in symbol_candles.items() if symbol not in excluded}


def exclude_top_period_return_symbols(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
    top_n: int,
) -> dict[str, list[Candle]]:
    if top_n <= 0:
        return symbol_candles
    rows = sorted(_period_symbol_returns(symbol_candles, start=start, end=end), key=lambda row: row[1], reverse=True)
    excluded = {symbol for symbol, _ in rows[:top_n]}
    return {symbol: candles for symbol, candles in symbol_candles.items() if symbol not in excluded}


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1) * 100)
    return worst


def _period_symbol_returns(
    symbol_candles: dict[str, list[Candle]],
    *,
    start: str,
    end: str,
) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for symbol, candles in symbol_candles.items():
        first = next((candle for candle in candles if start <= candle.date <= end and candle.open > 0), None)
        last = next((candle for candle in reversed(candles) if start <= candle.date <= end and candle.close > 0), None)
        if first is not None and last is not None and first.date <= last.date:
            rows.append((symbol, (last.close / first.open - 1) * 100))
    return rows


def _available_dates(symbol_candles: dict[str, list[Candle]], *, start: str, end: str) -> list[str]:
    return sorted(
        {
            candle.date
            for candles in symbol_candles.values()
            for candle in candles
            if start <= candle.date <= end
        }
    )


def _date_n_rows_before(dates: list[str], rows: int) -> str:
    if not dates:
        raise ValueError("dates is empty")
    if rows <= 1:
        return dates[-1]
    return dates[max(0, len(dates) - rows)]


def _generate_regime_validation_cases(
    symbol_candles: dict[str, list[Candle]],
    dates: list[str],
    *,
    window_rows: int = 126,
) -> list[MonthlyValidationCase]:
    if len(dates) < max(20, window_rows):
        return []
    step = max(21, window_rows // 2)
    windows: list[tuple[str, str, float]] = []
    for start_index in range(0, len(dates) - window_rows + 1, step):
        case_start = dates[start_index]
        case_end = dates[start_index + window_rows - 1]
        period_return = equal_weight_buy_hold_period_return(
            symbol_candles,
            start=case_start,
            end=case_end,
            initial_cash=1_000_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )
        windows.append((case_start, case_end, period_return))
    if not windows:
        return []

    selected = {
        "regime_bull": max(windows, key=lambda row: row[2]),
        "regime_bear": min(windows, key=lambda row: row[2]),
        "regime_sideways": min(windows, key=lambda row: abs(row[2])),
    }
    cases: list[MonthlyValidationCase] = []
    seen_periods: set[tuple[str, str]] = set()
    for name, (case_start, case_end, period_return) in selected.items():
        period = (case_start, case_end)
        if period in seen_periods:
            continue
        seen_periods.add(period)
        cases.append(
            MonthlyValidationCase(
                name=name,
                category="regime",
                start=case_start,
                end=case_end,
                stress=f"market_return_pct={period_return:.2f}",
            )
        )
    return cases


def _generate_walk_forward_validation_cases(
    dates: list[str],
    *,
    train_rows: int = 252,
    test_rows: int = 63,
    step_rows: int = 63,
) -> list[MonthlyValidationCase]:
    if len(dates) < train_rows + test_rows:
        return []
    cases: list[MonthlyValidationCase] = []
    index = 0
    case_number = 1
    while index + train_rows + test_rows <= len(dates):
        train_start = dates[index]
        train_end = dates[index + train_rows - 1]
        test_start = dates[index + train_rows]
        test_end = dates[index + train_rows + test_rows - 1]
        cases.append(
            MonthlyValidationCase(
                name=f"walk_forward_{case_number:03d}",
                category="walk_forward",
                train_start=train_start,
                train_end=train_end,
                start=test_start,
                end=test_end,
                stress=f"train_rows={train_rows};test_rows={test_rows}",
            )
        )
        index += step_rows
        case_number += 1
    return cases


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float_or_none(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None
