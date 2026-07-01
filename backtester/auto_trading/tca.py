from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


FIELDNAMES = [
    "as_of",
    "symbol",
    "side",
    "fill_status",
    "filled_quantity",
    "arrival_price",
    "simulated_fill_price",
    "arrival_notional_usd",
    "implementation_shortfall_usd",
    "implementation_shortfall_bps",
    "estimated_spread_cost_usd",
    "estimated_slippage_cost_usd",
    "expected_market_impact_usd",
    "expected_total_cost_usd",
    "cost_variance_usd",
    "tca_status",
    "tca_reasons",
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
class TcaConfig:
    max_shortfall_bps: float = 50.0
    max_cost_variance_usd: float = 5.0


def build_tca_rows(
    *,
    executions_path: Path | str,
    market_impact_path: Path | str | None = None,
    config: TcaConfig | None = None,
) -> list[dict[str, str]]:
    active_config = config or TcaConfig()
    impact_by_symbol = _load_market_impact(Path(market_impact_path)) if market_impact_path else {}
    rows = [_tca_row(row, impact_by_symbol, active_config) for row in _load_execution_rows(Path(executions_path))]
    if not rows:
        raise ValueError(f"{executions_path} has no paper execution rows")
    return rows


def save_tca_reports(rows: list[dict[str, str]], csv_path: Path | str, markdown_path: Path | str) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(rows), encoding="utf-8")


def _load_execution_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows = [dict(row) for row in reader]
    for row in rows:
        _assert_safe_execution_row(row)
    return rows


def _assert_safe_execution_row(row: dict[str, str]) -> None:
    expected = {**PAPER_FLAGS, "simulated": "True"}
    for key, expected_value in expected.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected_value:
            raise ValueError(f"unsafe TCA execution row for {row.get('symbol', '')}: {key}={actual}")


def _load_market_impact(path: Path) -> dict[str, float]:
    if not path.exists():
        raise ValueError(f"market impact file does not exist: {path}")
    values: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        for row in reader:
            _assert_safe_market_impact_row(row)
            symbol = str(row.get("symbol", "")).strip().upper()
            if symbol:
                values[symbol] = float(row.get("estimated_impact_usd", 0.0) or 0.0)
    return values


def _assert_safe_market_impact_row(row: dict[str, str]) -> None:
    for key, expected_value in PAPER_FLAGS.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected_value:
            raise ValueError(f"unsafe TCA market impact row for {row.get('symbol', '')}: {key}={actual}")


def _tca_row(row: dict[str, str], impact_by_symbol: dict[str, float], config: TcaConfig) -> dict[str, str]:
    symbol = str(row.get("symbol", "")).strip().upper()
    side = str(row.get("side", "")).strip().upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError(f"unsupported TCA side for {symbol}: {side}")
    filled_quantity = float(row.get("filled_quantity", 0.0) or 0.0)
    arrival_price = float(row.get("reference_price", 0.0) or 0.0)
    fill_price = float(row.get("simulated_fill_price", 0.0) or 0.0)
    spread_cost = float(row.get("estimated_spread_cost_usd", 0.0) or 0.0)
    slippage_cost = float(row.get("estimated_slippage_cost_usd", 0.0) or 0.0)
    fill_status = str(row.get("fill_status", "")).strip().upper()
    arrival_notional = abs(filled_quantity * arrival_price)

    if filled_quantity <= 0 or fill_status == "NO_FILL":
        return _row(
            row,
            arrival_price,
            fill_price,
            0.0,
            0.0,
            0.0,
            spread_cost,
            slippage_cost,
            impact_by_symbol.get(symbol, 0.0),
            "REVIEW",
            "no_fill",
        )

    shortfall = _implementation_shortfall(side, arrival_price, fill_price, filled_quantity)
    shortfall_bps = (shortfall / arrival_notional * 10_000.0) if arrival_notional > 0 else 0.0
    expected_impact = impact_by_symbol.get(symbol, 0.0)
    expected_total = spread_cost + slippage_cost + expected_impact
    variance = shortfall - expected_total
    reasons: list[str] = []
    if shortfall_bps > config.max_shortfall_bps:
        reasons.append("shortfall_bps")
    if variance > config.max_cost_variance_usd:
        reasons.append("cost_variance")
    return _row(
        row,
        arrival_price,
        fill_price,
        arrival_notional,
        shortfall,
        shortfall_bps,
        spread_cost,
        slippage_cost,
        expected_impact,
        "BLOCK" if reasons else "PASS",
        ",".join(reasons) or "within_limits",
    )


def _implementation_shortfall(side: str, arrival_price: float, fill_price: float, quantity: float) -> float:
    if side == "SELL":
        return (arrival_price - fill_price) * quantity
    return (fill_price - arrival_price) * quantity


def _row(
    source: dict[str, str],
    arrival_price: float,
    fill_price: float,
    arrival_notional: float,
    shortfall: float,
    shortfall_bps: float,
    spread_cost: float,
    slippage_cost: float,
    expected_impact: float,
    status: str,
    reasons: str,
) -> dict[str, str]:
    expected_total = spread_cost + slippage_cost + expected_impact
    return {
        "as_of": str(source.get("as_of", "")).strip(),
        "symbol": str(source.get("symbol", "")).strip().upper(),
        "side": str(source.get("side", "")).strip().upper(),
        "fill_status": str(source.get("fill_status", "")).strip().upper(),
        "filled_quantity": f"{float(source.get('filled_quantity', 0.0) or 0.0):.6f}",
        "arrival_price": f"{arrival_price:.6f}",
        "simulated_fill_price": f"{fill_price:.6f}",
        "arrival_notional_usd": f"{arrival_notional:.6f}",
        "implementation_shortfall_usd": f"{shortfall:.6f}",
        "implementation_shortfall_bps": f"{shortfall_bps:.6f}",
        "estimated_spread_cost_usd": f"{spread_cost:.6f}",
        "estimated_slippage_cost_usd": f"{slippage_cost:.6f}",
        "expected_market_impact_usd": f"{expected_impact:.6f}",
        "expected_total_cost_usd": f"{expected_total:.6f}",
        "cost_variance_usd": f"{shortfall - expected_total:.6f}",
        "tca_status": status,
        "tca_reasons": reasons,
        **PAPER_FLAGS,
    }


def _markdown(rows: list[dict[str, str]]) -> str:
    status_counts: dict[str, int] = {}
    total_shortfall = 0.0
    for row in rows:
        status_counts[row["tca_status"]] = status_counts.get(row["tca_status"], 0) + 1
        total_shortfall += float(row["implementation_shortfall_usd"])
    lines = [
        "# TCA Simulator",
        "",
        "paper-only / dry-run / execution_allowed=False / production_effect=none",
        "",
        f"- rows: `{len(rows)}`",
        f"- total_implementation_shortfall_usd: `{total_shortfall:.6f}`",
        "- status_counts: `"
        + ",".join(f"{status}={count}" for status, count in sorted(status_counts.items()))
        + "`",
        "",
        "| symbol | side | fill_status | shortfall_usd | shortfall_bps | status | reasons |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['side']} | {row['fill_status']} | "
            f"{row['implementation_shortfall_usd']} | {row['implementation_shortfall_bps']} | "
            f"{row['tca_status']} | {row['tca_reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)
