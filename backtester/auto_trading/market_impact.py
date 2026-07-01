from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


SCENARIO_MULTIPLIERS = {
    "base": 1.0,
    "conservative": 1.5,
    "stress": 2.5,
}
FIELDNAMES = [
    "symbol",
    "scenario",
    "order_value_usd",
    "average_daily_dollar_volume",
    "participation_rate",
    "annualized_volatility",
    "spread_rate",
    "estimated_impact_rate",
    "estimated_impact_usd",
    "risk_bucket",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]


@dataclass(frozen=True)
class MarketImpactInput:
    symbol: str
    order_value_usd: float
    average_daily_dollar_volume: float
    annualized_volatility: float
    spread_rate: float
    scenario: str = "base"


@dataclass(frozen=True)
class MarketImpactEstimate:
    symbol: str
    scenario: str
    order_value_usd: float
    average_daily_dollar_volume: float
    participation_rate: float
    annualized_volatility: float
    spread_rate: float
    estimated_impact_rate: float
    estimated_impact_usd: float
    risk_bucket: str
    paper_only: bool = True
    dry_run: bool = True
    execution_allowed: bool = False
    production_effect: str = "none"


def estimate_market_impact(value: MarketImpactInput) -> MarketImpactEstimate:
    if value.average_daily_dollar_volume <= 0:
        raise ValueError(f"average_daily_dollar_volume must be positive for {value.symbol}")
    scenario = value.scenario.strip().lower() or "base"
    if scenario not in SCENARIO_MULTIPLIERS:
        raise ValueError(f"unknown market impact scenario: {value.scenario}")
    participation = max(0.0, value.order_value_usd) / value.average_daily_dollar_volume
    volatility_component = max(0.0, value.annualized_volatility) * math.sqrt(participation) * 0.10
    spread_component = max(0.0, value.spread_rate) * (0.5 + participation)
    impact_rate = (volatility_component + spread_component) * SCENARIO_MULTIPLIERS[scenario]
    return MarketImpactEstimate(
        symbol=value.symbol.strip().upper(),
        scenario=scenario,
        order_value_usd=float(value.order_value_usd),
        average_daily_dollar_volume=float(value.average_daily_dollar_volume),
        participation_rate=participation,
        annualized_volatility=float(value.annualized_volatility),
        spread_rate=float(value.spread_rate),
        estimated_impact_rate=impact_rate,
        estimated_impact_usd=float(value.order_value_usd) * impact_rate,
        risk_bucket=_risk_bucket(participation, impact_rate),
    )


def estimate_market_impact_rows(values: list[MarketImpactInput]) -> list[dict[str, str]]:
    return [_estimate_row(estimate_market_impact(value)) for value in values]


def write_market_impact_report(rows: list[dict[str, str]], output_path: Path | str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _estimate_row(estimate: MarketImpactEstimate) -> dict[str, str]:
    return {
        "symbol": estimate.symbol,
        "scenario": estimate.scenario,
        "order_value_usd": _fmt(estimate.order_value_usd),
        "average_daily_dollar_volume": _fmt(estimate.average_daily_dollar_volume),
        "participation_rate": _fmt(estimate.participation_rate),
        "annualized_volatility": _fmt(estimate.annualized_volatility),
        "spread_rate": _fmt(estimate.spread_rate),
        "estimated_impact_rate": _fmt(estimate.estimated_impact_rate),
        "estimated_impact_usd": _fmt(estimate.estimated_impact_usd),
        "risk_bucket": estimate.risk_bucket,
        "paper_only": str(estimate.paper_only),
        "dry_run": str(estimate.dry_run),
        "execution_allowed": str(estimate.execution_allowed),
        "production_effect": estimate.production_effect,
    }


def _risk_bucket(participation: float, impact_rate: float) -> str:
    if participation >= 0.10 or impact_rate >= 0.01:
        return "HIGH"
    if participation >= 0.03 or impact_rate >= 0.005:
        return "MEDIUM"
    return "LOW"


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"
