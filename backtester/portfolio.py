from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    quantity: int


@dataclass(frozen=True)
class RebalanceOrder:
    symbol: str
    side: str
    current_weight: float
    target_weight: float
    target_amount: float
    delta_amount: float
    reference_price: float
    estimated_quantity: int
    reason: str


def calculate_current_weights(
    *,
    positions: list[PortfolioPosition],
    prices: dict[str, float],
    cash: float,
) -> dict[str, float]:
    values = {
        position.symbol: max(position.quantity, 0) * max(float(prices.get(position.symbol, 0.0)), 0.0)
        for position in positions
    }
    total_value = max(cash, 0.0) + sum(values.values())
    if total_value <= 0:
        return {"CASH": 1.0}
    weights = {symbol: value / total_value for symbol, value in values.items() if value > 0}
    weights["CASH"] = max(cash, 0.0) / total_value
    return weights


def cap_target_allocations(
    target_weights: dict[str, float],
    *,
    max_position_weight: float,
    cash_buffer_weight: float = 0.0,
) -> dict[str, float]:
    capped = {
        symbol: min(max(weight, 0.0), max_position_weight)
        for symbol, weight in target_weights.items()
    }
    budget = max(0.0, min(1.0, 1.0 - cash_buffer_weight))
    total = sum(capped.values())
    if total > budget and total > 0:
        scale = budget / total
        capped = {symbol: weight * scale for symbol, weight in capped.items()}
    return capped


def generate_rebalance_orders(
    *,
    positions: list[PortfolioPosition],
    prices: dict[str, float],
    cash: float,
    target_weights: dict[str, float],
    min_order_amount: float = 0.0,
    reason: str = "rebalance",
) -> list[RebalanceOrder]:
    position_map = {position.symbol: position for position in positions}
    current_weights = calculate_current_weights(positions=positions, prices=prices, cash=cash)
    portfolio_value = max(cash, 0.0) + sum(
        max(position.quantity, 0) * max(float(prices.get(position.symbol, 0.0)), 0.0)
        for position in positions
    )
    orders: list[RebalanceOrder] = []
    for symbol in sorted(set(position_map) | set(target_weights)):
        price = float(prices.get(symbol, 0.0) or 0.0)
        if price <= 0:
            continue
        target_weight = max(float(target_weights.get(symbol, 0.0)), 0.0)
        current_weight = float(current_weights.get(symbol, 0.0))
        target_amount = target_weight * portfolio_value
        current_amount = current_weight * portfolio_value
        delta_amount = target_amount - current_amount
        if abs(delta_amount) < min_order_amount:
            continue
        if delta_amount > 0:
            side = "BUY"
            quantity = int(delta_amount / price)
        else:
            side = "SELL"
            current_quantity = position_map.get(symbol, PortfolioPosition(symbol, 0)).quantity
            quantity = min(current_quantity, int(abs(delta_amount) / price))
        if quantity <= 0:
            continue
        orders.append(
            RebalanceOrder(
                symbol=symbol,
                side=side,
                current_weight=current_weight,
                target_weight=target_weight,
                target_amount=target_amount,
                delta_amount=delta_amount,
                reference_price=price,
                estimated_quantity=quantity,
                reason=reason,
            )
        )
    return sorted(orders, key=lambda order: (0 if order.side == "SELL" else 1, order.symbol))
