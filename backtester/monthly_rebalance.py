import csv
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

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
    execution_allowed: bool = False
    execution_mode: str = "blocked"
    execution_block_reason: str = "unmarked_order_plan"


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
    daily_drawdown_stop_pct: float = 0.0
    daily_drawdown_cooldown_days: int = 20
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
    "execution_allowed",
    "execution_mode",
    "execution_block_reason",
]

DECISION_COLUMNS = ["as_of_date", "signal_date", "mode", "selected_preset", "reason", "target_weights"]

STATE_COLUMNS = ["last_rebalance_date", "signal_date", "mode", "selected_preset", "reason"]

RISK_COLUMNS = ["name", "status", "detail"]
PERFORMANCE_AUDIT_COLUMNS = ["name", "status", "detail"]

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
    "missing_symbols",
    "coverage_pct",
    "status",
    "missing_preview",
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
    targets = (
        select_buyable_targets(
            ranked_targets,
            reference_prices=reference_prices,
            portfolio_value=portfolio_value,
            target_budget=target_budget,
            max_position_weight=cfg.max_position_weight,
            min_target_value=cfg.min_target_value,
        )
        if reference_prices is not None and portfolio_value is not None
        else ranked_targets
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
        ),
        reason="selected_monthly_alpha" + reason_suffix,
    )


def build_order_plan(
    decision: MonthlyDecision,
    *,
    positions: list[Position],
    cash: float,
    reference_prices: dict[str, float],
    min_trade_value: float = 10_000.0,
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
        orders.append(
            PlannedOrder(
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
        )
    return sorted(orders, key=lambda order: 0 if order.action == "SELL" else 1)


def mark_order_plan_execution(
    orders: list[PlannedOrder],
    *,
    risk_status_value: str,
) -> list[PlannedOrder]:
    normalized = str(risk_status_value).strip().upper()
    marked: list[PlannedOrder] = []
    for order in orders:
        if normalized == "PASS" and order.action in {"BUY", "SELL"}:
            marked.append(
                replace(
                    order,
                    execution_allowed=True,
                    execution_mode="live_ready",
                    execution_block_reason="",
                )
            )
        else:
            reason = f"risk_status_{normalized}" if normalized != "PASS" else f"action_{order.action}"
            marked.append(
                replace(
                    order,
                    execution_allowed=False,
                    execution_mode="blocked",
                    execution_block_reason=reason,
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
    }


def _monthly_validation_train_score(row: dict[str, Any]) -> float:
    return float(row["excess_return_pct"]) + float(row["max_drawdown_pct"])


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
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sorted_candles = {
        symbol: sorted(candles, key=lambda candle: candle.date)
        for symbol, candles in symbol_candles.items()
        if candles
    }
    for snapshot_date, universe_symbols in sorted(point_in_time_universe.items()):
        normalized_universe = {_normalize_symbol_code(symbol) for symbol in universe_symbols if symbol}
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
                "missing_symbols": len(missing),
                "coverage_pct": round(coverage_pct, 4),
                "status": "PASS" if coverage_pct >= min_coverage_pct else "BLOCK",
                "missing_preview": ";".join(missing[:missing_preview_size]),
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


def save_monthly_validation_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MONTHLY_VALIDATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MONTHLY_VALIDATION_COLUMNS})
    return len(rows)


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
) -> dict[str, float]:
    if not symbols or target_budget <= 0:
        return {}
    equal_weight = target_budget / len(symbols)
    position_weight = min(equal_weight, max_position_weight) if max_position_weight > 0 else equal_weight
    return {symbol: position_weight for symbol in symbols}


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


def load_point_in_time_universe(path: Path | str) -> dict[str, set[str]]:
    snapshots: dict[str, set[str]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "date" not in reader.fieldnames or "symbol" not in reader.fieldnames:
            raise RuntimeError("point-in-time universe CSV must include date and symbol columns")
        for row in reader:
            snapshot_date = str(row.get("date", "")).strip()
            symbol = _normalize_symbol_code(row.get("symbol", ""))
            if not snapshot_date or not symbol:
                continue
            snapshots.setdefault(snapshot_date, set()).add(symbol)
    return snapshots


def filter_symbol_candles_by_universe(
    symbol_candles: dict[str, list[Candle]],
    universe_by_date: dict[str, set[str]] | None,
    *,
    signal_date: str,
) -> dict[str, list[Candle]]:
    if not universe_by_date:
        return symbol_candles
    eligible_date = max((date for date in universe_by_date if date <= signal_date), default="")
    if not eligible_date:
        return {}
    eligible_symbols = universe_by_date[eligible_date]
    return {symbol: candles for symbol, candles in symbol_candles.items() if symbol in eligible_symbols}


def _normalize_symbol_code(value: Any) -> str:
    text = str(value).strip().strip("'").strip('"')
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text.upper()


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

    for current_date in dates:
        day_candles = {
            symbol: by_date[current_date]
            for symbol, by_date in candles_by_symbol_date.items()
            if current_date in by_date
        }
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
                        decision = scale_monthly_decision_targets(
                            decision,
                            scale=cfg.drawdown_guard_scale,
                            reason_suffix="_drawdown_guard",
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
