from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class CostScenario:
    name: str
    fee_rate: float
    slippage_rate: float
    fx_buffer_rate: float


@dataclass(frozen=True)
class TaxConfig:
    usd_krw_rate: float = 1400.0
    annual_deduction_krw: float = 2_500_000.0
    capital_gains_tax_rate: float = 0.22
    lot_method: str = "FIFO"
    tax_year_by: str = "settlement_date"
    settlement_lag_days: int = 1
    tax_proxy: str = "constant_fx"


@dataclass(frozen=True)
class TaxTrade:
    trade_date: str
    symbol: str
    side: str
    quantity: int
    price_usd: float


BASE_COST_SCENARIO = CostScenario("base", fee_rate=0.00015, slippage_rate=0.0005, fx_buffer_rate=0.0010)
CONSERVATIVE_COST_SCENARIO = CostScenario(
    "conservative",
    fee_rate=0.00030,
    slippage_rate=0.0015,
    fx_buffer_rate=0.0030,
)


def buy_fill_price(price: float, scenario: CostScenario) -> float:
    return float(price) * (1.0 + scenario.slippage_rate)


def sell_fill_price(price: float, scenario: CostScenario) -> float:
    return float(price) * (1.0 - scenario.slippage_rate)


def trade_cost_usd(value_usd: float, scenario: CostScenario) -> float:
    value = abs(float(value_usd))
    return value * (scenario.fee_rate + scenario.fx_buffer_rate)


def compute_capital_gains_tax_usd(trades: list[TaxTrade], config: TaxConfig) -> float:
    if config.lot_method != "FIFO":
        raise ValueError("v1 supports only lot_method=FIFO")
    if config.tax_year_by != "settlement_date":
        raise ValueError("v1 supports only tax_year_by=settlement_date")
    lots_by_symbol: dict[str, list[tuple[int, float]]] = {}
    gains_by_year_krw: dict[int, float] = {}
    for trade in sorted(trades, key=lambda item: item.trade_date):
        symbol = trade.symbol.strip().upper()
        side = trade.side.strip().upper()
        quantity = int(trade.quantity)
        price = float(trade.price_usd)
        if quantity <= 0:
            continue
        if side == "BUY":
            lots_by_symbol.setdefault(symbol, []).append((quantity, price))
            continue
        if side != "SELL":
            raise ValueError(f"unsupported tax trade side: {trade.side}")
        remaining = quantity
        realized_usd = 0.0
        lots = lots_by_symbol.setdefault(symbol, [])
        while remaining > 0:
            if not lots:
                raise ValueError(f"sell exceeds FIFO lots for {symbol}")
            lot_quantity, lot_price = lots[0]
            used = min(remaining, lot_quantity)
            realized_usd += (price - lot_price) * used
            remaining -= used
            if used == lot_quantity:
                lots.pop(0)
            else:
                lots[0] = (lot_quantity - used, lot_price)
        settlement = date.fromisoformat(trade.trade_date) + timedelta(days=int(config.settlement_lag_days))
        gains_by_year_krw[settlement.year] = gains_by_year_krw.get(settlement.year, 0.0) + (
            realized_usd * config.usd_krw_rate
        )
    tax_krw = 0.0
    for realized_gain_krw in gains_by_year_krw.values():
        taxable = max(0.0, realized_gain_krw - config.annual_deduction_krw)
        tax_krw += taxable * config.capital_gains_tax_rate
    return tax_krw / config.usd_krw_rate if config.usd_krw_rate else 0.0
