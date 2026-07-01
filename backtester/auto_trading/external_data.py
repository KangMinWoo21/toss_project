from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


SAFETY_FLAGS = {
    "paper_only": True,
    "dry_run": True,
    "execution_allowed": False,
    "production_effect": "none",
}
READINESS_FIELDNAMES = [
    "adapter",
    "filename",
    "status",
    "reasons",
    "symbols_requested",
    "symbols_covered",
    "missing_symbols",
    "row_count",
    "freshness_field",
    "latest_observation",
    "source_values",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]
READINESS_FLAGS = {
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


@dataclass(frozen=True)
class ExternalDataPolicy:
    free_data_sources: tuple[str, ...] = (
        "SEC EDGAR",
        "FINRA Daily Short Sale Volume",
        "GDELT",
        "Alpha Vantage",
        "Nasdaq Trader Symbol Directory",
        "Yahoo/Alpaca daily volume",
    )
    live_execution_policy: str = "paper_execution_simulator_only"
    network_policy: str = "fetch_scripts_only_auto_paper_run_local_csv_only"


@dataclass(frozen=True)
class ExternalDataAdapterSpec:
    adapter: str
    filename: str
    required_columns: tuple[str, ...]
    freshness_field: str


EXTERNAL_DATA_ADAPTERS = (
    ExternalDataAdapterSpec(
        adapter="factors",
        filename="factors.csv",
        required_columns=(
            "symbol",
            "sector",
            "beta",
            "size_score",
            "value_score",
            "quality_score",
            "momentum_score",
            "source",
            "as_of",
        ),
        freshness_field="as_of",
    ),
    ExternalDataAdapterSpec(
        adapter="short_sale_volume",
        filename="short_sale_volume.csv",
        required_columns=("symbol", "date", "short_volume", "total_volume", "source"),
        freshness_field="date",
    ),
    ExternalDataAdapterSpec(
        adapter="news_sentiment",
        filename="news_sentiment.csv",
        required_columns=("symbol", "date", "article_count", "sentiment_score", "source"),
        freshness_field="date",
    ),
    ExternalDataAdapterSpec(
        adapter="listing_status",
        filename="listing_status.csv",
        required_columns=("symbol", "name", "exchange", "asset_type", "ipo_date", "delisting_date", "status", "source"),
        freshness_field="",
    ),
)


@dataclass(frozen=True)
class ExternalSymbolRow:
    symbol: str
    sector: str
    beta: float
    size_score: float
    value_score: float
    quality_score: float
    momentum_score: float
    factor_source: str
    factor_as_of: str
    short_volume_ratio: float
    short_source: str
    news_article_count: int
    news_sentiment_score: float
    news_source: str
    listing_status: str
    delisted: bool
    listing_source: str
    paper_only: bool = True
    dry_run: bool = True
    execution_allowed: bool = False
    production_effect: str = "none"


@dataclass(frozen=True)
class LiquidityImpactEstimate:
    symbol: str
    order_value_usd: float
    average_daily_dollar_volume: float
    participation_rate: float
    annualized_volatility: float
    estimated_impact_rate: float
    estimated_impact_usd: float
    liquidity_source: str
    paper_only: bool = True
    dry_run: bool = True
    execution_allowed: bool = False
    production_effect: str = "none"


@dataclass(frozen=True)
class ExternalDataBundle:
    symbol_rows: dict[str, ExternalSymbolRow]
    policy: ExternalDataPolicy

    @classmethod
    def empty(cls) -> "ExternalDataBundle":
        return cls(symbol_rows={}, policy=ExternalDataPolicy())


def load_external_data_bundle(root: Path | str, symbols: list[str]) -> ExternalDataBundle:
    csv_root = Path(root)
    normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    factor_rows = _load_required_rows(csv_root / "factors.csv", "factor")
    short_rows = _load_optional_rows(csv_root / "short_sale_volume.csv")
    news_rows = _load_optional_rows(csv_root / "news_sentiment.csv")
    listing_rows = _load_optional_rows(csv_root / "listing_status.csv")

    by_symbol: dict[str, ExternalSymbolRow] = {}
    for symbol in normalized_symbols:
        factor = _latest_by_symbol(factor_rows, symbol, "as_of")
        if factor is None:
            raise ValueError(f"external factor row missing for {symbol}")
        _require_source(factor, "factors.csv", symbol)
        short = _latest_by_symbol(short_rows, symbol, "date") or {}
        news = _latest_by_symbol(news_rows, symbol, "date") or {}
        listing = _latest_by_symbol(listing_rows, symbol, "delisting_date") or {}
        _require_optional_source(short, "short_sale_volume.csv", symbol)
        _require_optional_source(news, "news_sentiment.csv", symbol)
        _require_optional_source(listing, "listing_status.csv", symbol)

        total_volume = _float(short.get("total_volume", "0"))
        short_ratio = 0.0
        if total_volume > 0:
            short_ratio = _float(short.get("short_volume", "0")) / total_volume
        listing_status = str(listing.get("status", "") or "unknown").strip()
        delisted = bool(str(listing.get("delisting_date", "")).strip()) or listing_status.lower() == "delisted"
        by_symbol[symbol] = ExternalSymbolRow(
            symbol=symbol,
            sector=str(factor.get("sector", "")).strip(),
            beta=_float(factor.get("beta", "0")),
            size_score=_float(factor.get("size_score", "0")),
            value_score=_float(factor.get("value_score", "0")),
            quality_score=_float(factor.get("quality_score", "0")),
            momentum_score=_float(factor.get("momentum_score", "0")),
            factor_source=str(factor.get("source", "")).strip(),
            factor_as_of=str(factor.get("as_of", "")).strip(),
            short_volume_ratio=short_ratio,
            short_source=str(short.get("source", "")).strip(),
            news_article_count=int(_float(news.get("article_count", "0"))),
            news_sentiment_score=_float(news.get("sentiment_score", "0")),
            news_source=str(news.get("source", "")).strip(),
            listing_status=listing_status,
            delisted=delisted,
            listing_source=str(listing.get("source", "")).strip(),
        )
    return ExternalDataBundle(symbol_rows=by_symbol, policy=ExternalDataPolicy())


def build_external_data_readiness_rows(root: Path | str, symbols: list[str]) -> list[dict[str, str]]:
    csv_root = Path(root)
    normalized_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
    if not normalized_symbols:
        raise ValueError("external data readiness requires at least one symbol")
    return [_readiness_row(csv_root, spec, normalized_symbols) for spec in EXTERNAL_DATA_ADAPTERS]


def save_external_data_readiness_reports(
    rows: list[dict[str, str]],
    csv_path: Path | str,
    markdown_path: Path | str,
) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=READINESS_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_readiness_markdown(rows), encoding="utf-8")


def estimate_liquidity_impact(
    symbol: str,
    order_value_usd: float,
    average_daily_dollar_volume: float,
    annualized_volatility: float,
    bundle: ExternalDataBundle,
) -> LiquidityImpactEstimate:
    if average_daily_dollar_volume <= 0:
        raise ValueError(f"average_daily_dollar_volume must be positive for {symbol}")
    participation = max(0.0, float(order_value_usd)) / float(average_daily_dollar_volume)
    impact = max(0.0, float(annualized_volatility)) * math.sqrt(participation) * 0.10
    source = "daily_volume_adv_proxy"
    row = bundle.symbol_rows.get(symbol.strip().upper())
    if row and row.short_volume_ratio > 0.30:
        impact *= 1.25
        source += "+short_pressure_proxy"
    return LiquidityImpactEstimate(
        symbol=symbol.strip().upper(),
        order_value_usd=float(order_value_usd),
        average_daily_dollar_volume=float(average_daily_dollar_volume),
        participation_rate=participation,
        annualized_volatility=float(annualized_volatility),
        estimated_impact_rate=impact,
        estimated_impact_usd=float(order_value_usd) * impact,
        liquidity_source=source,
    )


def _readiness_row(csv_root: Path, spec: ExternalDataAdapterSpec, symbols: list[str]) -> dict[str, str]:
    path = csv_root / spec.filename
    reasons: list[str] = []
    row_count = 0
    covered_symbols: set[str] = set()
    source_values: set[str] = set()
    observations: list[str] = []
    if not path.exists():
        reasons.append("missing_file")
    else:
        with path.open(newline="", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            fieldnames = set(reader.fieldnames or [])
            missing_columns = set(spec.required_columns) - fieldnames
            if missing_columns:
                reasons.append("missing_columns=" + ",".join(sorted(missing_columns)))
            rows = [dict(row) for row in reader]
        row_count = len(rows)
        requested = set(symbols)
        relevant_rows = [row for row in rows if str(row.get("symbol", "")).strip().upper() in requested]
        covered_symbols = {str(row.get("symbol", "")).strip().upper() for row in relevant_rows}
        missing_symbols = requested - covered_symbols
        if missing_symbols:
            reasons.append("missing_symbols=" + ",".join(sorted(missing_symbols)))
        if any(not str(row.get("source", "")).strip() for row in relevant_rows):
            reasons.append("missing_source")
        if spec.freshness_field:
            observations = [str(row.get(spec.freshness_field, "")).strip() for row in relevant_rows if str(row.get(spec.freshness_field, "")).strip()]
            if len(observations) < len(relevant_rows):
                reasons.append("missing_observation_date")
        source_values = {str(row.get("source", "")).strip() for row in relevant_rows if str(row.get("source", "")).strip()}

    missing_symbols_text = ",".join(symbol for symbol in symbols if symbol not in covered_symbols)
    return {
        "adapter": spec.adapter,
        "filename": spec.filename,
        "status": "PASS" if not reasons else "BLOCK",
        "reasons": ";".join(reasons) or "none",
        "symbols_requested": str(len(symbols)),
        "symbols_covered": str(len(covered_symbols)),
        "missing_symbols": missing_symbols_text or "none",
        "row_count": str(row_count),
        "freshness_field": spec.freshness_field or "not_applicable",
        "latest_observation": max(observations) if observations else "",
        "source_values": ",".join(sorted(source_values)) or "none",
        **READINESS_FLAGS,
    }


def _readiness_markdown(rows: list[dict[str, str]]) -> str:
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK"
    lines = [
        "# External Data Readiness",
        "",
        "paper-only / dry-run / execution_allowed=False / production_effect=none",
        "",
        f"- overall_status: `{overall}`",
        "",
        "| adapter | status | covered | missing_symbols | latest_observation | reasons |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['adapter']} | {row['status']} | {row['symbols_covered']}/{row['symbols_requested']} | "
            f"{row['missing_symbols']} | {row['latest_observation']} | {row['reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_required_rows(path: Path, label: str) -> list[dict[str, str]]:
    rows = _load_optional_rows(path)
    if not rows:
        raise ValueError(f"missing required {label} CSV: {path}")
    return rows


def _load_optional_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return [dict(row) for row in reader]


def _latest_by_symbol(rows: list[dict[str, str]], symbol: str, date_field: str) -> dict[str, str] | None:
    matches = [row for row in rows if str(row.get("symbol", "")).strip().upper() == symbol]
    if not matches:
        return None
    return sorted(matches, key=lambda row: str(row.get(date_field, "")))[-1]


def _require_source(row: dict[str, str], filename: str, symbol: str) -> None:
    if not str(row.get("source", "")).strip():
        raise ValueError(f"{filename} missing source for {symbol}")


def _require_optional_source(row: dict[str, str], filename: str, symbol: str) -> None:
    if row:
        _require_source(row, filename, symbol)


def _float(value: object) -> float:
    text = str(value or "").strip()
    return float(text) if text else 0.0
