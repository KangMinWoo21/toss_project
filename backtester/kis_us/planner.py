import csv
from pathlib import Path

from .models import KisUsPlannedOrder, KisUsPosition, KisUsQuote, KisUsTarget, ProtectedPosition


ALLOWED_TARGET_EXCHANGES = {"NAS", "NYS", "AMS"}


def load_targets(path: Path | str) -> list[KisUsTarget]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = {"symbol", "exchange", "target_weight"}.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        targets: list[KisUsTarget] = []
        seen: set[str] = set()
        for row in reader:
            symbol = _normalize_symbol(row.get("symbol", ""))
            exchange = str(row.get("exchange", "")).strip().upper()
            if not symbol:
                continue
            if symbol in seen:
                raise ValueError(f"duplicate target symbol: {symbol}")
            if exchange not in ALLOWED_TARGET_EXCHANGES:
                raise ValueError(f"unknown exchange for {symbol}: {exchange}")
            target_weight = float(row.get("target_weight", 0) or 0)
            if target_weight < 0:
                raise ValueError(f"negative target_weight for {symbol}")
            seen.add(symbol)
            targets.append(KisUsTarget(symbol=symbol, exchange=exchange, target_weight=target_weight))
    total_weight = sum(target.target_weight for target in targets)
    if total_weight > 1.0 + 1e-12:
        raise ValueError(f"target_weight total exceeds 1.0: {total_weight:.6f}")
    return targets


def build_kis_us_order_plan(
    *,
    targets: list[KisUsTarget],
    positions: list[KisUsPosition],
    quotes: dict[str, KisUsQuote],
    protected_positions: dict[str, ProtectedPosition],
    cash_usd: float,
    as_of: str,
    created_at: str,
) -> list[KisUsPlannedOrder]:
    target_by_symbol = {target.symbol: target for target in targets}
    position_by_symbol = {_normalize_symbol(position.symbol): position for position in positions}
    protected_symbols = {_normalize_symbol(symbol) for symbol in protected_positions}
    symbols = sorted(set(target_by_symbol) | set(position_by_symbol))
    rebalance_value = max(float(cash_usd), 0.0) + sum(
        max(position.market_value, 0.0)
        for symbol, position in position_by_symbol.items()
        if symbol not in protected_symbols
    )
    if rebalance_value <= 0:
        rebalance_value = sum(max(position.market_value, 0.0) for position in position_by_symbol.values())
    plan_id = f"kis-us-{as_of.replace('-', '')}"
    rows: list[KisUsPlannedOrder] = []
    for symbol in symbols:
        target = target_by_symbol.get(symbol)
        position = position_by_symbol.get(symbol)
        quote = quotes.get(symbol)
        exchange = (target.exchange if target else (position.exchange if position else "")).upper()
        current_quantity = max(position.quantity, 0) if position else 0
        current_value = max(position.market_value, 0.0) if position else 0.0
        target_weight = target.target_weight if target else 0.0
        current_weight = current_value / rebalance_value if rebalance_value > 0 else 0.0
        if quote is None:
            rows.append(
                _row(
                    plan_id,
                    as_of,
                    symbol,
                    exchange,
                    "SKIP",
                    0,
                    current_quantity,
                    target_weight,
                    current_weight,
                    0.0,
                    0.0,
                    "BLOCKED",
                    "missing_quote",
                    created_at,
                )
            )
            continue
        price = max(float(quote.price), 0.0)
        if price <= 0:
            rows.append(
                _row(
                    plan_id,
                    as_of,
                    symbol,
                    exchange,
                    "SKIP",
                    0,
                    current_quantity,
                    target_weight,
                    current_weight,
                    price,
                    0.0,
                    "BLOCKED",
                    "invalid_reference_price",
                    created_at,
                )
            )
            continue
        target_value = target_weight * rebalance_value
        delta_value = target_value - current_value
        if abs(delta_value) < price:
            rows.append(
                _row(
                    plan_id,
                    as_of,
                    symbol,
                    exchange,
                    "SKIP",
                    0,
                    current_quantity,
                    target_weight,
                    current_weight,
                    price,
                    0.0,
                    "BLOCKED",
                    "quantity_below_one_share",
                    created_at,
                )
            )
            continue
        if delta_value < 0:
            quantity = min(current_quantity, int(abs(delta_value) / price))
            if symbol in protected_symbols:
                reason = protected_positions[symbol].reason
                rows.append(
                    _row(
                        plan_id,
                        as_of,
                        symbol,
                        exchange,
                        "SKIP",
                        0,
                        current_quantity,
                        target_weight,
                        current_weight,
                        price,
                        0.0,
                        "BLOCKED",
                        f"protected_position:{reason}",
                        created_at,
                    )
                )
                continue
            side = "SELL"
        else:
            quantity = int(delta_value / price)
            side = "BUY"
        if quantity <= 0:
            rows.append(
                _row(
                    plan_id,
                    as_of,
                    symbol,
                    exchange,
                    "SKIP",
                    0,
                    current_quantity,
                    target_weight,
                    current_weight,
                    price,
                    0.0,
                    "BLOCKED",
                    "quantity_below_one_share",
                    created_at,
                )
            )
            continue
        rows.append(
            _row(
                plan_id,
                as_of,
                symbol,
                exchange,
                side,
                quantity,
                current_quantity,
                target_weight,
                current_weight,
                price,
                quantity * price,
                "PASS",
                "dry_run_only",
                created_at,
            )
        )
    return sorted(rows, key=lambda row: (0 if row.side == "SELL" else 1 if row.side == "BUY" else 2, row.symbol))


def _row(
    plan_id: str,
    as_of: str,
    symbol: str,
    exchange: str,
    side: str,
    quantity: int,
    current_quantity: int,
    target_weight: float,
    current_weight: float,
    reference_price: float,
    estimated_value: float,
    risk_status: str,
    risk_reasons: str,
    created_at: str,
) -> KisUsPlannedOrder:
    return KisUsPlannedOrder(
        plan_id=plan_id,
        as_of=as_of,
        symbol=symbol,
        exchange=exchange,
        side=side,
        quantity=quantity,
        current_quantity=current_quantity,
        target_weight=target_weight,
        current_weight=current_weight,
        reference_price=reference_price,
        estimated_value=estimated_value,
        risk_status=risk_status,
        risk_reasons=risk_reasons,
        execution_allowed=False,
        created_at=created_at,
    )


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()
