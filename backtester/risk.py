from dataclasses import dataclass


@dataclass(frozen=True)
class RiskCheck:
    name: str
    status: str
    detail: str


def validate_portfolio_risk(
    *,
    target_weights: dict[str, float],
    prices: dict[str, float],
    max_position_weight: float,
    max_positions: int,
    blocked_symbols: set[str] | None = None,
    stale_symbols: set[str] | None = None,
    target_amounts: dict[str, float] | None = None,
    average_daily_values: dict[str, float] | None = None,
    max_adv_participation: float = 0.1,
    max_adv_participation_rate: float | None = None,
    warn_adv_participation_rate: float = 0.05,
    missing_adv_status: str = "BLOCK",
) -> list[RiskCheck]:
    checks: list[RiskCheck] = []
    active = {symbol: weight for symbol, weight in target_weights.items() if weight > 0}

    missing_prices = [
        symbol
        for symbol in active
        if float(prices.get(symbol, 0.0) or 0.0) <= 0
    ]
    if missing_prices:
        checks.append(RiskCheck("missing_prices", "BLOCK", ",".join(sorted(missing_prices))))
    else:
        checks.append(RiskCheck("missing_prices", "PASS", "none"))

    oversized = [
        f"{symbol}:{weight:.4f}"
        for symbol, weight in active.items()
        if weight > max_position_weight + 1e-12
    ]
    if oversized:
        checks.append(RiskCheck("max_position_weight", "BLOCK", ",".join(sorted(oversized))))
    else:
        checks.append(RiskCheck("max_position_weight", "PASS", f"limit {max_position_weight:.4f}"))

    if len(active) > max_positions:
        checks.append(RiskCheck("max_positions", "BLOCK", f"{len(active)} exceeds {max_positions}"))
    else:
        checks.append(RiskCheck("max_positions", "PASS", str(len(active))))

    blocked = sorted(set(active).intersection(blocked_symbols or set()))
    if blocked:
        checks.append(RiskCheck("blocked_symbols", "BLOCK", ",".join(blocked)))
    else:
        checks.append(RiskCheck("blocked_symbols", "PASS", "none"))

    stale = sorted(set(active).intersection(stale_symbols or set()))
    if stale:
        checks.append(RiskCheck("stale_symbols", "BLOCK", ",".join(stale)))
    else:
        checks.append(RiskCheck("stale_symbols", "PASS", "none"))

    liquidity = _liquidity_check(
        target_amounts or {},
        average_daily_values or {},
        max_adv_participation=(
            max_adv_participation if max_adv_participation_rate is None else max_adv_participation_rate
        ),
        warn_adv_participation_rate=warn_adv_participation_rate,
        missing_adv_status=missing_adv_status,
    )
    if liquidity is not None:
        checks.append(liquidity)

    return checks


def risk_status(checks: list[RiskCheck]) -> str:
    statuses = {check.status for check in checks}
    if "BLOCK" in statuses:
        return "BLOCK"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def _liquidity_check(
    target_amounts: dict[str, float],
    average_daily_values: dict[str, float],
    *,
    max_adv_participation: float,
    warn_adv_participation_rate: float,
    missing_adv_status: str,
) -> RiskCheck | None:
    if not target_amounts:
        return None
    blocked: list[str] = []
    warned: list[str] = []
    normalized_missing_status = str(missing_adv_status).strip().upper()
    for symbol, amount in target_amounts.items():
        adv = float(average_daily_values.get(symbol, 0.0) or 0.0)
        if adv <= 0:
            detail = f"{symbol}:adv_unavailable"
            if normalized_missing_status == "WARN":
                warned.append(detail)
            else:
                blocked.append(detail)
            continue
        participation = abs(float(amount)) / adv
        if participation > max_adv_participation + 1e-12:
            blocked.append(f"{symbol}:{participation:.4f}>{max_adv_participation:.4f}")
        elif participation > warn_adv_participation_rate + 1e-12:
            warned.append(f"{symbol}:{participation:.4f}>{warn_adv_participation_rate:.4f}")
    if blocked:
        return RiskCheck("liquidity", "BLOCK", ",".join(sorted(blocked)))
    if warned:
        return RiskCheck("liquidity", "WARN", ",".join(sorted(warned)))
    return RiskCheck(
        "liquidity",
        "PASS",
        (
            f"max_adv_participation {max_adv_participation:.4f}; "
            f"warn_adv_participation {warn_adv_participation_rate:.4f}"
        ),
    )
