"""Fetch US daily OHLCV data from Yahoo Finance chart endpoints.

The output is normalized to simple CSV files for local research and paper-only
backtests. No brokerage credentials are used.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")
YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={period1}&period2={period2}&interval=1d&events=history"
)


def _unix_time(value: datetime) -> int:
    return int(value.replace(tzinfo=timezone.utc).timestamp())


def fetch_yahoo_daily(symbol: str, *, start: datetime, end: datetime, timeout: float) -> list[dict[str, str]]:
    url = YAHOO_CHART_URL.format(
        symbol=symbol.upper(),
        period1=_unix_time(start),
        period2=_unix_time(end),
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research-data-fetcher/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    chart = payload.get("chart", {})
    error = chart.get("error")
    if error:
        raise ValueError(f"Yahoo Finance error for {symbol}: {error}")
    results = chart.get("result") or []
    if not results:
        raise ValueError(f"empty Yahoo Finance payload for {symbol}")

    result: dict[str, Any] = results[0]
    timestamps = result.get("timestamp") or []
    quote_blocks = result.get("indicators", {}).get("quote") or []
    if not timestamps or not quote_blocks:
        raise ValueError(f"missing OHLCV arrays for {symbol}")
    quote = quote_blocks[0]
    adjclose_blocks = result.get("indicators", {}).get("adjclose") or []
    adjclose = adjclose_blocks[0].get("adjclose", []) if adjclose_blocks else []

    rows: list[dict[str, str]] = []
    for index, timestamp in enumerate(timestamps):
        close = _at(quote, "close", index)
        if close is None:
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                "symbol": symbol.upper(),
                "open": _format_number(_at(quote, "open", index)),
                "high": _format_number(_at(quote, "high", index)),
                "low": _format_number(_at(quote, "low", index)),
                "close": _format_number(close),
                "adj_close": _format_number(adjclose[index] if index < len(adjclose) else close),
                "volume": str(int(_at(quote, "volume", index) or 0)),
                "source": "yahoo_finance_chart",
            }
        )
    return rows


def _at(block: dict[str, list[Any]], key: str, index: int) -> Any:
    values = block.get(key) or []
    return values[index] if index < len(values) else None


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value):.6f}"


def write_symbol_csv(symbol: str, rows: list[dict[str, str]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.upper()}_daily.csv"
    fieldnames = ["date", "symbol", "open", "high", "low", "close", "adj_close", "volume", "source"]
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_manifest(outputs: list[Path], output_dir: Path, *, start: datetime, end: datetime) -> Path:
    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["symbol", "path", "start", "end", "source_url"])
        writer.writeheader()
        for path in outputs:
            symbol = path.stem.replace("_daily", "")
            writer.writerow(
                {
                    "symbol": symbol,
                    "path": path.as_posix(),
                    "start": start.date().isoformat(),
                    "end": end.date().isoformat(),
                    "source_url": YAHOO_CHART_URL.format(
                        symbol=symbol,
                        period1=_unix_time(start),
                        period2=_unix_time(end),
                    ),
                }
            )
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch US daily OHLCV data from Yahoo Finance")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--output-dir", default="data/external/yahoo/us_daily")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default=(datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat())
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
    if not symbols:
        raise ValueError("at least one symbol is required")

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    output_dir = Path(args.output_dir)
    outputs: list[Path] = []

    for symbol in symbols:
        try:
            rows = fetch_yahoo_daily(symbol, start=start, end=end, timeout=args.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"failed {symbol}: {exc}", file=sys.stderr)
            return 1
        outputs.append(write_symbol_csv(symbol, rows, output_dir))
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    manifest_path = write_manifest(outputs, output_dir, start=start, end=end)
    print(f"saved {len(outputs)} symbols to {output_dir}")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
