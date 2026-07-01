from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class PriceRow:
    symbol: str
    bar_date: str
    usable_from_kst: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int
    source: str


def load_price_history(prices_dir: Path | str, symbols: list[str]) -> dict[str, list[PriceRow]]:
    root = Path(prices_dir)
    histories: dict[str, list[PriceRow]] = {}
    for symbol in symbols:
        normalized = symbol.strip().upper()
        path = root / f"{normalized}_daily.csv"
        if not path.exists():
            raise ValueError(f"missing price CSV for {normalized}: {path}")
        histories[normalized] = _load_symbol_prices(path, normalized)
    return histories


def assert_no_lookahead(rows: list[PriceRow], decision_time_kst: datetime) -> None:
    for row in rows:
        usable = datetime.fromisoformat(row.usable_from_kst)
        if usable > decision_time_kst:
            raise ValueError(
                f"lookahead detected for {row.symbol} {row.bar_date}: usable_from_kst={row.usable_from_kst}"
            )


def _load_symbol_prices(path: Path, expected_symbol: str) -> list[PriceRow]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows = [_price_row(path, row, expected_symbol) for row in reader]
    if not rows:
        raise ValueError(f"{path} has no rows")
    return sorted(rows, key=lambda row: row.bar_date)


def _price_row(path: Path, row: dict[str, str], expected_symbol: str) -> PriceRow:
    raw_date = str(row.get("bar_date") or row.get("date") or "").strip()
    if not raw_date:
        raise ValueError(f"{path} row missing date/bar_date")
    bar = date.fromisoformat(raw_date)
    usable_from = str(row.get("usable_from_kst", "")).strip() or _default_usable_from_kst(bar)
    symbol = str(row.get("symbol") or expected_symbol).strip().upper()
    if symbol != expected_symbol:
        raise ValueError(f"{path} contains symbol {symbol}, expected {expected_symbol}")
    return PriceRow(
        symbol=symbol,
        bar_date=bar.isoformat(),
        usable_from_kst=usable_from,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        adj_close=float(row["adj_close"]),
        volume=int(float(row.get("volume", 0) or 0)),
        source=str(row.get("source", "")).strip(),
    )


def _default_usable_from_kst(bar: date) -> str:
    usable = datetime.combine(bar + timedelta(days=1), time(hour=6), tzinfo=KST)
    return usable.isoformat()
