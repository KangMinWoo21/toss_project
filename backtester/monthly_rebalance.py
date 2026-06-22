import csv
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from datetime import date, datetime
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
    weak_breadth_min_train_avg_excess_pct: float = 10.0
    cash_buffer_weight: float = 0.01
    max_position_weight: float = 0.15
    candidate_pool_size: int = 7
    min_target_value: float = 10_000.0
    max_candidate_lookback_return_pct: float = 90.0
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
    "max_position_weight",
    "drawdown_guard_scale",
    "market_volatility_min_scale",
    "position_trailing_stop_pct",
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
    selected_configs = preset_configs or {
        preset: momentum_rotation_config_for_preset(preset) for preset in cfg.presets
    }
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
    if selected is None:
        if prior_breadth is not None and prior_breadth >= cfg.market_beta_breadth_threshold:
            return _market_beta_or_cash_decision(
                decision_candles,
                as_of_date=as_of_date,
                signal_date=signal_date,
                target_budget=target_budget,
                config=cfg,
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


def save_monthly_decision_attribution(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    return save_monthly_attribution_rows(rows, output_path, columns=MONTHLY_DECISION_ATTRIBUTION_COLUMNS)


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

    if comparison_status in {"REJECT", "REJECTED"} or new_count or failed_delta > 0:
        decision = "REJECT"
        recommendation = (
            "Do not adopt this candidate; inspect new failure diagnostics and run narrower paper-only experiments."
        )
    elif failed_delta < 0 and not new_count:
        decision = "PAPER_REVIEW"
        recommendation = (
            "Candidate improved required failures without introducing new failures; keep paper-only and rerun full validation."
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
    if likely_root_cause in {"weak_window_return_drag", "selection_or_exposure_regression", "insufficient_recovery"}:
        gaps.append("symbol_pnl_attribution")
    gaps = [gap for gap in gaps if gap not in available]
    return "; ".join(dict.fromkeys(gaps))


def _validation_failure_next_action(likely_root_cause: str, evidence_gaps: str) -> str:
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
    max_position_weight: float | None = None,
    drawdown_guard_scale: float | None = None,
    market_volatility_min_scale: float | None = None,
    position_trailing_stop_pct: float | None = None,
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
        "max_position_weight": _sweep_value(max_position_weight, base_config.max_position_weight),
        "drawdown_guard_scale": _sweep_value(drawdown_guard_scale, base_config.drawdown_guard_scale),
        "market_volatility_min_scale": _sweep_value(
            market_volatility_min_scale,
            base_config.market_volatility_min_scale,
        ),
        "position_trailing_stop_pct": _sweep_value(
            position_trailing_stop_pct,
            base_config.position_trailing_stop_pct,
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
        "max_position_weight": float,
        "drawdown_guard_scale": float,
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
    return replace(base_config, **updates) if updates else base_config


def _sweep_config_changes(plan_row: dict[str, Any]) -> str:
    parts: list[str] = []
    for field_name in (
        "cash_buffer_weight",
        "min_train_positive_ratio",
        "candidate_pool_size",
        "max_position_weight",
        "drawdown_guard_scale",
        "market_volatility_min_scale",
        "position_trailing_stop_pct",
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
    "max_position_weight": "--max-position-weight",
    "drawdown_guard_scale": "--drawdown-guard-scale",
    "market_volatility_min_scale": "--market-volatility-min-scale",
    "position_trailing_stop_pct": "--position-trailing-stop-pct",
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


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


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
    rows: list[tuple[str, float]] = []
    for symbol, candles in symbol_candles.items():
        history = [candle for candle in candles if candle.date <= signal_date]
        if len(history) < window_days:
            continue
        window = history[-window_days:]
        average_trading_value = sum(candle.close * candle.volume for candle in window) / len(window)
        rows.append((symbol, average_trading_value))
    rows.sort(key=lambda row: row[1], reverse=True)
    return [symbol for symbol, _ in rows]


def _market_beta_target_weights(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    target_budget: float,
    config: MonthlyRebalanceConfig,
) -> dict[str, float]:
    if target_budget <= 0:
        return {}
    if config.market_beta_symbol in symbol_candles:
        return {config.market_beta_symbol: target_budget}
    if config.market_beta_proxy_size <= 0:
        return {}
    proxy_symbols = rank_symbols_by_average_trading_value(
        symbol_candles,
        signal_date=signal_date,
        window_days=config.point_in_time_liquidity_window_days,
    )[: config.market_beta_proxy_size]
    return target_weights_for_symbols(
        proxy_symbols,
        target_budget=target_budget,
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
) -> MonthlyDecision:
    beta_weights = _market_beta_target_weights(
        symbol_candles,
        signal_date=signal_date,
        target_budget=target_budget,
        config=config,
    )
    if beta_weights:
        is_proxy = config.market_beta_symbol not in beta_weights
        return MonthlyDecision(
            as_of_date=as_of_date,
            signal_date=signal_date,
            mode="market_beta_proxy" if is_proxy else "market_beta",
            selected_preset="market_beta_proxy" if is_proxy else "market_beta",
            target_weights=beta_weights,
            reason=proxy_reason if is_proxy else direct_reason,
        )
    return MonthlyDecision(
        as_of_date=as_of_date,
        signal_date=signal_date,
        mode="cash",
        selected_preset="cash",
        target_weights={},
        reason=empty_reason,
    )


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
