from dataclasses import replace
from typing import Any


def average_daily_trading_value(
    candles: list[Any],
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


def annotate_order_liquidity(
    order: Any,
    candles: list[Any],
    *,
    as_of_date: str,
    adv_window_days: int,
    base_slippage_rate: float,
    impact_slippage_multiplier: float,
    warn_adv_participation_rate: float,
    max_adv_participation_rate: float,
    liquidity_missing_adv_status: str,
) -> Any:
    adv = average_daily_trading_value(candles, as_of_date=as_of_date, window_days=adv_window_days)
    participation = abs(order.estimated_value) / adv if adv > 0 else 0.0
    estimated_slippage_rate = max(0.0, base_slippage_rate) + participation * max(0.0, impact_slippage_multiplier)
    estimated_total_cost = abs(order.estimated_value) * estimated_slippage_rate
    if adv <= 0:
        status = normalize_liquidity_status(liquidity_missing_adv_status)
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


def normalize_liquidity_status(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized in {"WARN", "PASS", "NOT_CHECKED"}:
        return normalized
    return "BLOCK"


def mark_order_plan_execution(
    orders: list[Any],
    *,
    risk_status_value: str,
    production_trading_enabled: bool = False,
) -> list[Any]:
    normalized = str(risk_status_value).strip().upper()
    marked: list[Any] = []
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
