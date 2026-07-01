from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .external_data import ExternalDataBundle, load_external_data_bundle
from .prices import PriceRow, load_price_history


FIELDNAMES = [
    "check",
    "status",
    "detail",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]
ADJUSTED_TARGET_FIELDNAMES = [
    "symbol",
    "exchange",
    "target_weight",
    "risk_adjustment",
    "risk_reasons",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]
PAPER_FLAGS = {
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


@dataclass(frozen=True)
class PortfolioRiskLimits:
    max_single_weight: float = 0.35
    max_sector_weight: float = 0.50
    min_beta: float = 0.0
    max_beta: float = 1.80
    max_short_volume_ratio: float = 0.35
    min_news_sentiment: float = -0.60
    max_adv_participation: float = 0.05


def build_portfolio_risk_rows(
    *,
    targets_path: Path | str,
    external_data_dir: Path | str,
    prices_dir: Path | str,
    portfolio_value_usd: float,
    limits: PortfolioRiskLimits | None = None,
) -> list[dict[str, str]]:
    active_limits = limits or PortfolioRiskLimits()
    targets = _load_targets(Path(targets_path))
    symbols = [row["symbol"] for row in targets]
    external = load_external_data_bundle(external_data_dir, symbols)
    prices = load_price_history(prices_dir, symbols)
    return [
        _single_name_weight_row(targets, active_limits),
        _sector_weight_row(targets, external, active_limits),
        _beta_band_row(targets, external, active_limits),
        _short_volume_row(targets, external, active_limits),
        _news_sentiment_row(targets, external, active_limits),
        _listing_status_row(targets, external),
        _adv_participation_row(targets, prices, portfolio_value_usd, active_limits),
    ]


def adjust_targets_for_portfolio_risk(
    *,
    targets_path: Path | str,
    external_data_dir: Path | str,
    prices_dir: Path | str,
    portfolio_value_usd: float,
    limits: PortfolioRiskLimits | None = None,
) -> list[dict[str, str]]:
    active_limits = limits or PortfolioRiskLimits()
    targets = _load_targets(Path(targets_path))
    raw_rows = _read_raw_targets(Path(targets_path))
    exchange_by_symbol = {str(row.get("symbol", "")).strip().upper(): str(row.get("exchange", "")).strip().upper() for row in raw_rows}
    symbols = [row["symbol"] for row in targets]
    external = load_external_data_bundle(external_data_dir, symbols)
    prices = load_price_history(prices_dir, symbols)
    adjusted: list[dict[str, str]] = []
    sector_weights: dict[str, float] = {}

    for target in targets:
        symbol = str(target["symbol"])
        original_weight = float(target["target_weight"])
        reasons = _symbol_block_reasons(symbol, original_weight, external, prices, portfolio_value_usd, active_limits)
        if reasons:
            continue
        sector = external.symbol_rows[symbol].sector or "unknown"
        sector_room = max(0.0, active_limits.max_sector_weight - sector_weights.get(sector, 0.0))
        capped_weight = min(original_weight, active_limits.max_single_weight, sector_room)
        if capped_weight <= 0:
            continue
        sector_weights[sector] = sector_weights.get(sector, 0.0) + capped_weight
        adjustment = "kept" if abs(capped_weight - original_weight) < 1e-12 else "capped"
        cap_reasons = []
        if capped_weight < original_weight and original_weight > active_limits.max_single_weight:
            cap_reasons.append("single_name_cap")
        if capped_weight < original_weight and sector_room < original_weight:
            cap_reasons.append("sector_cap")
        adjusted.append(
            {
                "symbol": symbol,
                "exchange": exchange_by_symbol.get(symbol, ""),
                "target_weight": f"{capped_weight:.6f}",
                "risk_adjustment": adjustment,
                "risk_reasons": ",".join(cap_reasons) or "none",
                **PAPER_FLAGS,
            }
        )
    if not adjusted:
        raise ValueError("portfolio risk adjustment removed all targets")
    return adjusted


def save_adjusted_targets(rows: list[dict[str, str]], output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=ADJUSTED_TARGET_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def save_portfolio_risk_reports(rows: list[dict[str, str]], csv_path: Path | str, markdown_path: Path | str) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(rows), encoding="utf-8")


def _single_name_weight_row(targets: list[dict[str, float | str]], limits: PortfolioRiskLimits) -> dict[str, str]:
    offenders = [
        f"{row['symbol']}={float(row['target_weight']):.6f}"
        for row in targets
        if float(row["target_weight"]) > limits.max_single_weight
    ]
    return _row(
        "single_name_weight",
        not offenders,
        f"max_single_weight={limits.max_single_weight:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _sector_weight_row(
    targets: list[dict[str, float | str]],
    external: ExternalDataBundle,
    limits: PortfolioRiskLimits,
) -> dict[str, str]:
    weights: dict[str, float] = {}
    for target in targets:
        symbol = str(target["symbol"])
        sector = external.symbol_rows[symbol].sector or "unknown"
        weights[sector] = weights.get(sector, 0.0) + float(target["target_weight"])
    offenders = [
        f"{sector}={weight:.6f}"
        for sector, weight in sorted(weights.items())
        if weight > limits.max_sector_weight
    ]
    return _row(
        "sector_weight",
        not offenders,
        f"max_sector_weight={limits.max_sector_weight:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _beta_band_row(
    targets: list[dict[str, float | str]],
    external: ExternalDataBundle,
    limits: PortfolioRiskLimits,
) -> dict[str, str]:
    offenders = []
    for target in targets:
        symbol = str(target["symbol"])
        beta = external.symbol_rows[symbol].beta
        if beta < limits.min_beta or beta > limits.max_beta:
            offenders.append(f"{symbol}={beta:.6f}")
    return _row(
        "beta_band",
        not offenders,
        f"min_beta={limits.min_beta:.6f}; max_beta={limits.max_beta:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _short_volume_row(
    targets: list[dict[str, float | str]],
    external: ExternalDataBundle,
    limits: PortfolioRiskLimits,
) -> dict[str, str]:
    offenders = []
    for target in targets:
        symbol = str(target["symbol"])
        ratio = external.symbol_rows[symbol].short_volume_ratio
        if ratio > limits.max_short_volume_ratio:
            offenders.append(f"{symbol}={ratio:.6f}")
    return _row(
        "short_volume_ratio",
        not offenders,
        f"max_short_volume_ratio={limits.max_short_volume_ratio:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _news_sentiment_row(
    targets: list[dict[str, float | str]],
    external: ExternalDataBundle,
    limits: PortfolioRiskLimits,
) -> dict[str, str]:
    offenders = []
    for target in targets:
        symbol = str(target["symbol"])
        score = external.symbol_rows[symbol].news_sentiment_score
        if score < limits.min_news_sentiment:
            offenders.append(f"{symbol}={score:.6f}")
    return _row(
        "news_sentiment",
        not offenders,
        f"min_news_sentiment={limits.min_news_sentiment:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _listing_status_row(targets: list[dict[str, float | str]], external: ExternalDataBundle) -> dict[str, str]:
    offenders = []
    for target in targets:
        symbol = str(target["symbol"])
        data = external.symbol_rows[symbol]
        if data.delisted or data.listing_status.lower() not in {"active", ""}:
            offenders.append(f"{symbol}={data.listing_status or 'delisted'}")
    return _row("listing_status", not offenders, f"offenders={','.join(offenders) or 'none'}")


def _adv_participation_row(
    targets: list[dict[str, float | str]],
    prices: dict[str, list[PriceRow]],
    portfolio_value_usd: float,
    limits: PortfolioRiskLimits,
) -> dict[str, str]:
    offenders = []
    for target in targets:
        symbol = str(target["symbol"])
        target_value = float(target["target_weight"]) * float(portfolio_value_usd)
        adv = _average_daily_dollar_volume(prices[symbol])
        participation = target_value / adv if adv > 0 else float("inf")
        if participation > limits.max_adv_participation:
            offenders.append(f"{symbol}={participation:.6f}")
    return _row(
        "adv_participation",
        not offenders,
        f"max_adv_participation={limits.max_adv_participation:.6f}; offenders={','.join(offenders) or 'none'}",
    )


def _load_targets(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for row in _read_raw_targets(path):
        _assert_safe_target_row(row)
        symbol = str(row.get("symbol", "")).strip().upper()
        weight = float(row.get("target_weight", 0.0) or 0.0)
        if symbol and weight > 0:
            rows.append({"symbol": symbol, "target_weight": weight})
    if not rows:
        raise ValueError(f"{path} has no positive target weights")
    return rows


def _read_raw_targets(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return [dict(row) for row in reader]


def _symbol_block_reasons(
    symbol: str,
    weight: float,
    external: ExternalDataBundle,
    prices: dict[str, list[PriceRow]],
    portfolio_value_usd: float,
    limits: PortfolioRiskLimits,
) -> list[str]:
    row = external.symbol_rows[symbol]
    reasons: list[str] = []
    if row.beta < limits.min_beta or row.beta > limits.max_beta:
        reasons.append("beta_band")
    if row.short_volume_ratio > limits.max_short_volume_ratio:
        reasons.append("short_volume_ratio")
    if row.news_sentiment_score < limits.min_news_sentiment:
        reasons.append("news_sentiment")
    if row.delisted or row.listing_status.lower() not in {"active", ""}:
        reasons.append("listing_status")
    adv = _average_daily_dollar_volume(prices[symbol])
    participation = (weight * portfolio_value_usd / adv) if adv > 0 else float("inf")
    if participation > limits.max_adv_participation:
        reasons.append("adv_participation")
    return reasons


def _assert_safe_target_row(row: dict[str, str]) -> None:
    expected = {
        "paper_only": "True",
        "dry_run": "True",
        "execution_allowed": "False",
        "production_effect": "none",
    }
    for key, expected_value in expected.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected_value:
            raise ValueError(f"unsafe target row for {row.get('symbol', '')}: {key}={actual}")


def _average_daily_dollar_volume(rows: list[PriceRow], lookback_days: int = 20) -> float:
    recent = rows[-lookback_days:] if len(rows) > lookback_days else rows
    values = [row.close * row.volume for row in recent if row.close > 0 and row.volume > 0]
    return sum(values) / len(values) if values else 0.0


def _row(check: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "PASS" if passed else "BLOCK", "detail": detail, **PAPER_FLAGS}


def _markdown(rows: list[dict[str, str]]) -> str:
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK"
    lines = [
        "# Portfolio Risk Gate",
        "",
        "paper-only / dry-run / execution_allowed=False",
        "",
        f"- overall_status: `{overall}`",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['detail']} |")
    lines.append("")
    return "\n".join(lines)
