from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .external_data import ExternalDataBundle, load_external_data_bundle


ALLOWED_EXCHANGES = {"NAS", "NYS", "AMS"}
FIELDNAMES = [
    "symbol",
    "exchange",
    "target_weight",
    "alpha_score",
    "optimizer_status",
    "optimizer_reasons",
    "sector",
    "beta",
    "quality_score",
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
class PortfolioOptimizationConfig:
    max_total_weight: float = 0.98
    max_single_weight: float = 0.35
    max_sector_weight: float = 0.50
    max_weighted_beta: float = 1.50
    max_symbol_beta: float = 1.80
    min_quality_score: float = 0.50
    min_alpha_score: float = 0.0
    weight_step: float = 0.01


def build_optimized_portfolio_rows(
    *,
    candidates_path: Path | str,
    external_data_dir: Path | str,
    config: PortfolioOptimizationConfig | None = None,
) -> list[dict[str, str]]:
    active_config = config or PortfolioOptimizationConfig()
    candidates = _load_candidates(Path(candidates_path))
    symbols = [row["symbol"] for row in candidates]
    external = load_external_data_bundle(external_data_dir, symbols)
    return _optimize(candidates, external, active_config)


def save_optimized_portfolio_reports(
    rows: list[dict[str, str]],
    csv_path: Path | str,
    markdown_path: Path | str,
) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(rows), encoding="utf-8")


def _load_candidates(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        required = {"symbol", "exchange", "alpha_score"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path} missing required columns: {','.join(sorted(missing))}")
        for row in reader:
            _assert_safe_candidate_row(row)
            symbol = str(row.get("symbol", "")).strip().upper()
            exchange = str(row.get("exchange", "")).strip().upper()
            if not symbol:
                continue
            if symbol in seen:
                raise ValueError(f"duplicate optimizer candidate symbol: {symbol}")
            if exchange not in ALLOWED_EXCHANGES:
                raise ValueError(f"unsupported optimizer exchange for {symbol}: {exchange}")
            seen.add(symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "alpha_score": float(row.get("alpha_score", 0.0) or 0.0),
                }
            )
    if not rows:
        raise ValueError(f"{path} has no optimizer candidates")
    return rows


def _assert_safe_candidate_row(row: dict[str, str]) -> None:
    for key, expected in PAPER_FLAGS.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected:
            raise ValueError(f"unsafe optimizer candidate row for {row.get('symbol', '')}: {key}={actual}")


def _optimize(
    candidates: list[dict[str, float | str]],
    external: ExternalDataBundle,
    config: PortfolioOptimizationConfig,
) -> list[dict[str, str]]:
    ordered = sorted(candidates, key=lambda row: (-float(row["alpha_score"]), str(row["symbol"])))
    total_weight = 0.0
    weighted_beta = 0.0
    sector_weights: dict[str, float] = {}
    rows: list[dict[str, str]] = []

    for candidate in ordered:
        symbol = str(candidate["symbol"])
        factor = external.symbol_rows[symbol]
        sector = factor.sector or "unknown"
        reasons = _pre_block_reasons(candidate, factor, config)
        target_weight = 0.0
        if not reasons:
            while _can_add_step(
                step=config.weight_step,
                beta=factor.beta,
                sector=sector,
                target_weight=target_weight,
                total_weight=total_weight,
                weighted_beta=weighted_beta,
                sector_weights=sector_weights,
                config=config,
            ):
                target_weight = _round_weight(target_weight + config.weight_step)
                total_weight = _round_weight(total_weight + config.weight_step)
                weighted_beta += config.weight_step * factor.beta
                sector_weights[sector] = _round_weight(sector_weights.get(sector, 0.0) + config.weight_step)
        if target_weight <= 0 and not reasons:
            reasons.append("constraint_capacity")
        status = "SELECTED" if target_weight > 0 else "SKIP"
        if status == "SELECTED" and target_weight < config.max_single_weight:
            reasons.append("capped_by_constraints")
        rows.append(
            {
                "symbol": symbol,
                "exchange": str(candidate["exchange"]),
                "target_weight": f"{target_weight:.6f}",
                "alpha_score": f"{float(candidate['alpha_score']):.6f}",
                "optimizer_status": status,
                "optimizer_reasons": ",".join(reasons) or "selected",
                "sector": sector,
                "beta": f"{factor.beta:.6f}",
                "quality_score": f"{factor.quality_score:.6f}",
                **PAPER_FLAGS,
            }
        )
    if not any(float(row["target_weight"]) > 0 for row in rows):
        raise ValueError("portfolio optimizer selected no positive target weights")
    return rows


def _pre_block_reasons(candidate: dict[str, float | str], factor, config: PortfolioOptimizationConfig) -> list[str]:
    reasons: list[str] = []
    if float(candidate["alpha_score"]) < config.min_alpha_score:
        reasons.append("alpha_below_minimum")
    if factor.beta > config.max_symbol_beta:
        reasons.append("symbol_beta")
    if factor.quality_score < config.min_quality_score:
        reasons.append("quality_score")
    return reasons


def _can_add_step(
    *,
    step: float,
    beta: float,
    sector: str,
    target_weight: float,
    total_weight: float,
    weighted_beta: float,
    sector_weights: dict[str, float],
    config: PortfolioOptimizationConfig,
) -> bool:
    if step <= 0:
        raise ValueError("weight_step must be positive")
    epsilon = 1e-12
    if target_weight + step > config.max_single_weight + epsilon:
        return False
    if total_weight + step > config.max_total_weight + epsilon:
        return False
    if sector_weights.get(sector, 0.0) + step > config.max_sector_weight + epsilon:
        return False
    if weighted_beta + step * beta > config.max_weighted_beta + epsilon:
        return False
    return True


def _round_weight(value: float) -> float:
    return round(value + 1e-12, 10)


def _markdown(rows: list[dict[str, str]]) -> str:
    selected = [row for row in rows if float(row["target_weight"]) > 0]
    total_weight = sum(float(row["target_weight"]) for row in selected)
    lines = [
        "# Portfolio Optimizer",
        "",
        "paper-only / dry-run / execution_allowed=False / production_effect=none",
        "",
        f"- selected_count: `{len(selected)}`",
        f"- total_target_weight: `{total_weight:.6f}`",
        f"- estimated_cash_weight: `{max(0.0, 1.0 - total_weight):.6f}`",
        "",
        "| symbol | target_weight | alpha_score | status | reasons |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['target_weight']} | {row['alpha_score']} | "
            f"{row['optimizer_status']} | {row['optimizer_reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)
