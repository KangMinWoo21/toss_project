from dataclasses import replace
from typing import Any


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
