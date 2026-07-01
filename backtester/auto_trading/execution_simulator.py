from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .prices import PriceRow, load_price_history


FIELDNAMES = [
    "as_of",
    "symbol",
    "side",
    "requested_quantity",
    "filled_quantity",
    "fill_status",
    "fill_reasons",
    "reference_price_basis",
    "reference_price",
    "simulated_fill_price",
    "estimated_spread_cost_usd",
    "estimated_slippage_cost_usd",
    "simulated",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]
PAPER_FLAGS = {
    "simulated": "True",
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


@dataclass(frozen=True)
class ExecutionSimulationConfig:
    fill_policy: str = "close"
    max_adv_participation: float = 0.05
    spread_rate: float = 0.001
    slippage_rate: float = 0.001
    execution_time_kst: str = ""


def simulate_paper_execution(
    *,
    orders_path: Path | str,
    prices_dir: Path | str,
    config: ExecutionSimulationConfig,
) -> list[dict[str, str]]:
    orders = _load_orders(Path(orders_path))
    histories = load_price_history(prices_dir, sorted({order["symbol"] for order in orders}))
    execution_time = datetime.fromisoformat(config.execution_time_kst) if config.execution_time_kst else None
    rows: list[dict[str, str]] = []
    for order in orders:
        rows.append(_simulate_order(order, histories[order["symbol"]], config, execution_time))
    return rows


def write_execution_simulation_report(rows: list[dict[str, str]], output_path: Path | str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _simulate_order(
    order: dict[str, str],
    history: list[PriceRow],
    config: ExecutionSimulationConfig,
    execution_time: datetime | None,
) -> dict[str, str]:
    bar = _select_bar(history, order["as_of"], config.fill_policy)
    if bar is None:
        return _row(order, 0, "NO_FILL", "missing_price_bar", config.fill_policy, 0.0, 0.0, 0.0, 0.0)
    if execution_time is not None and datetime.fromisoformat(bar.usable_from_kst) > execution_time:
        raise ValueError(
            f"lookahead detected for {order['symbol']} {bar.bar_date}: usable_from_kst={bar.usable_from_kst}"
        )
    reference_price = _reference_price(bar, config.fill_policy)
    max_quantity = int(max(0, bar.volume) * max(0.0, config.max_adv_participation))
    requested_quantity = int(order["quantity"])
    if requested_quantity <= 0:
        return _row(order, 0, "NO_FILL", "zero_quantity", config.fill_policy, reference_price, 0.0, 0.0, 0.0)
    if max_quantity <= 0:
        return _row(
            order,
            0,
            "NO_FILL",
            "insufficient_liquidity",
            config.fill_policy,
            reference_price,
            0.0,
            0.0,
            0.0,
        )
    filled_quantity = min(requested_quantity, max_quantity)
    status = "FILLED" if filled_quantity == requested_quantity else "PARTIAL"
    reasons = "filled" if status == "FILLED" else "liquidity_cap"
    fill_price = _fill_price(order["side"], reference_price, config.spread_rate, config.slippage_rate)
    spread_cost = abs(reference_price * filled_quantity * config.spread_rate / 2.0)
    slippage_cost = abs(reference_price * filled_quantity * config.slippage_rate)
    return _row(
        order,
        filled_quantity,
        status,
        reasons,
        config.fill_policy,
        reference_price,
        fill_price,
        spread_cost,
        slippage_cost,
    )


def _load_orders(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows: list[dict[str, str]] = []
        for row in reader:
            symbol = str(row.get("symbol", "")).strip().upper()
            side = str(row.get("side", "")).strip().upper()
            if not symbol or side == "SKIP":
                continue
            if str(row.get("execution_allowed", "")).strip() != "False":
                raise ValueError(f"unsafe order row for {symbol}: execution_allowed={row.get('execution_allowed', '')}")
            rows.append(
                {
                    "as_of": str(row.get("as_of", "")).strip(),
                    "symbol": symbol,
                    "side": side,
                    "quantity": str(int(float(row.get("quantity", 0) or 0))),
                }
            )
    if not rows:
        raise ValueError(f"{path} has no executable paper order rows")
    return rows


def _select_bar(history: list[PriceRow], as_of: str, fill_policy: str) -> PriceRow | None:
    if fill_policy == "next_bar":
        return next((row for row in history if row.bar_date > as_of), None)
    eligible = [row for row in history if row.bar_date <= as_of]
    return eligible[-1] if eligible else None


def _reference_price(bar: PriceRow, fill_policy: str) -> float:
    if fill_policy == "open":
        return bar.open
    if fill_policy == "vwap_proxy":
        return (bar.high + bar.low + bar.close) / 3.0
    return bar.close


def _fill_price(side: str, reference_price: float, spread_rate: float, slippage_rate: float) -> float:
    adjustment = spread_rate / 2.0 + slippage_rate
    if side == "SELL":
        return reference_price * (1.0 - adjustment)
    return reference_price * (1.0 + adjustment)


def _row(
    order: dict[str, str],
    filled_quantity: int,
    status: str,
    reasons: str,
    price_basis: str,
    reference_price: float,
    fill_price: float,
    spread_cost: float,
    slippage_cost: float,
) -> dict[str, str]:
    return {
        "as_of": order["as_of"],
        "symbol": order["symbol"],
        "side": order["side"],
        "requested_quantity": order["quantity"],
        "filled_quantity": str(filled_quantity),
        "fill_status": status,
        "fill_reasons": reasons,
        "reference_price_basis": price_basis,
        "reference_price": f"{reference_price:.6f}",
        "simulated_fill_price": f"{fill_price:.6f}",
        "estimated_spread_cost_usd": f"{spread_cost:.6f}",
        "estimated_slippage_cost_usd": f"{slippage_cost:.6f}",
        **PAPER_FLAGS,
    }
