"""Fetch free US equity auxiliary data into local paper-only CSV inputs.

This script is intentionally separate from ``python -m backtester auto-paper-run``.
The engine consumes only local CSV files; network access belongs here.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


FINRA_SHORT_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"
ALPHA_LISTING_URL = "https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={apikey}"
ALPHA_NEWS_URL = "https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbols}&apikey={apikey}"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
USER_AGENT = "paper-only-research-data-fetcher/1.0 contact=local"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
    if not symbols:
        raise ValueError("at least one symbol is required")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    short_rows = fetch_finra_short_sale_volume(args.finra_date, symbols, timeout=args.timeout)
    write_csv(output_dir / "short_sale_volume.csv", short_rows, SHORT_FIELDNAMES)

    if args.alpha_vantage_key:
        listing_rows = fetch_alpha_vantage_listing_status(args.alpha_vantage_key, symbols, timeout=args.timeout)
        news_rows = fetch_alpha_vantage_news_sentiment(args.alpha_vantage_key, symbols, timeout=args.timeout)
    else:
        listing_rows = [_empty_listing_row(symbol) for symbol in symbols]
        news_rows = [_empty_news_row(symbol) for symbol in symbols]
    write_csv(output_dir / "listing_status.csv", listing_rows, LISTING_FIELDNAMES)
    write_csv(output_dir / "news_sentiment.csv", news_rows, NEWS_FIELDNAMES)

    factor_rows = fetch_sec_factor_proxies(args.cik_map, symbols, timeout=args.timeout)
    write_csv(output_dir / "factors.csv", factor_rows, FACTOR_FIELDNAMES)

    if args.sleep_seconds > 0:
        time.sleep(args.sleep_seconds)
    print(f"saved free external data for {len(symbols)} symbols to {output_dir}")
    print("paper_only True")
    print("auto_paper_run_network False")
    return 0


SHORT_FIELDNAMES = ["symbol", "date", "short_volume", "total_volume", "source"]
LISTING_FIELDNAMES = ["symbol", "name", "exchange", "asset_type", "ipo_date", "delisting_date", "status", "source"]
NEWS_FIELDNAMES = ["symbol", "date", "article_count", "sentiment_score", "source"]
FACTOR_FIELDNAMES = [
    "symbol",
    "sector",
    "beta",
    "size_score",
    "value_score",
    "quality_score",
    "momentum_score",
    "source",
    "as_of",
]


def fetch_finra_short_sale_volume(finra_date: str, symbols: list[str], *, timeout: float) -> list[dict[str, str]]:
    url = FINRA_SHORT_URL.format(date=finra_date)
    text = _fetch_text(url, timeout=timeout)
    wanted = set(symbols)
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    for row in reader:
        symbol = str(row.get("Symbol", "")).strip().upper()
        if symbol not in wanted:
            continue
        rows.append(
            {
                "symbol": symbol,
                "date": _finra_date(row.get("Date", finra_date)),
                "short_volume": str(int(float(row.get("ShortVolume", "0") or 0))),
                "total_volume": str(int(float(row.get("TotalVolume", "0") or 0))),
                "source": "finra_daily_short_sale_volume",
            }
        )
    return rows or [_empty_short_row(symbol, finra_date) for symbol in symbols]


def fetch_alpha_vantage_listing_status(apikey: str, symbols: list[str], *, timeout: float) -> list[dict[str, str]]:
    text = _fetch_text(ALPHA_LISTING_URL.format(apikey=urllib.parse.quote(apikey)), timeout=timeout)
    wanted = set(symbols)
    rows: list[dict[str, str]] = []
    for row in csv.DictReader(io.StringIO(text)):
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol not in wanted:
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": str(row.get("name", "")).strip(),
                "exchange": str(row.get("exchange", "")).strip(),
                "asset_type": str(row.get("assetType", "") or row.get("asset_type", "")).strip(),
                "ipo_date": _blank_null(row.get("ipoDate", "")),
                "delisting_date": _blank_null(row.get("delistingDate", "")),
                "status": str(row.get("status", "")).strip(),
                "source": "alpha_vantage_listing_status",
            }
        )
    return rows or [_empty_listing_row(symbol) for symbol in symbols]


def fetch_alpha_vantage_news_sentiment(apikey: str, symbols: list[str], *, timeout: float) -> list[dict[str, str]]:
    joined_symbols = ",".join(symbols)
    url = ALPHA_NEWS_URL.format(
        symbols=urllib.parse.quote(joined_symbols),
        apikey=urllib.parse.quote(apikey),
    )
    payload = json.loads(_fetch_text(url, timeout=timeout))
    scores_by_symbol: dict[str, list[float]] = {symbol: [] for symbol in symbols}
    for item in payload.get("feed", []):
        for sentiment in item.get("ticker_sentiment", []):
            symbol = str(sentiment.get("ticker", "")).strip().upper()
            if symbol in scores_by_symbol:
                scores_by_symbol[symbol].append(float(sentiment.get("ticker_sentiment_score", 0.0) or 0.0))
    today = date.today().isoformat()
    rows: list[dict[str, str]] = []
    for symbol in symbols:
        scores = scores_by_symbol.get(symbol, [])
        average = sum(scores) / len(scores) if scores else 0.0
        rows.append(
            {
                "symbol": symbol,
                "date": today,
                "article_count": str(len(scores)),
                "sentiment_score": _fmt(average),
                "source": "alpha_vantage_news_sentiment",
            }
        )
    return rows


def fetch_sec_factor_proxies(cik_map_path: str | None, symbols: list[str], *, timeout: float) -> list[dict[str, str]]:
    cik_by_symbol = _load_cik_map(Path(cik_map_path)) if cik_map_path else {}
    rows: list[dict[str, str]] = []
    for symbol in symbols:
        cik = cik_by_symbol.get(symbol)
        if not cik:
            rows.append(_empty_factor_row(symbol, source="missing_cik_map"))
            continue
        payload = json.loads(_fetch_text(SEC_COMPANYFACTS_URL.format(cik=cik.zfill(10)), timeout=timeout))
        rows.append(_factor_row_from_companyfacts(symbol, payload))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _factor_row_from_companyfacts(symbol: str, payload: dict[str, Any]) -> dict[str, str]:
    facts = payload.get("facts", {}).get("us-gaap", {})
    assets = _latest_fact_value(facts, "Assets")
    liabilities = _latest_fact_value(facts, "Liabilities")
    net_income = _latest_fact_value(facts, "NetIncomeLoss")
    revenue = _latest_fact_value(facts, "Revenues")
    equity_ratio = max(0.0, min(1.0, (assets - liabilities) / assets)) if assets > 0 else 0.0
    margin = max(0.0, min(1.0, net_income / revenue)) if revenue > 0 else 0.0
    size_score = max(0.0, min(1.0, math.log10(max(assets, 1.0)) / 13.0))
    return {
        "symbol": symbol,
        "sector": "unknown",
        "beta": "0",
        "size_score": _fmt(size_score),
        "value_score": _fmt(equity_ratio),
        "quality_score": _fmt((equity_ratio + margin) / 2.0),
        "momentum_score": "0",
        "source": "sec_edgar_companyfacts_proxy",
        "as_of": date.today().isoformat(),
    }


def _latest_fact_value(facts: dict[str, Any], name: str) -> float:
    entries = facts.get(name, {}).get("units", {}).get("USD", [])
    if not entries:
        return 0.0
    sorted_entries = sorted(entries, key=lambda item: (int(item.get("fy", 0) or 0), str(item.get("end", ""))))
    return float(sorted_entries[-1].get("val", 0.0) or 0.0)


def _load_cik_map(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        return {
            str(row.get("symbol", "")).strip().upper(): str(row.get("cik", "")).strip()
            for row in csv.DictReader(fp)
            if str(row.get("symbol", "")).strip() and str(row.get("cik", "")).strip()
        }


def _fetch_text(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _empty_short_row(symbol: str, finra_date: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "date": _finra_date(finra_date),
        "short_volume": "0",
        "total_volume": "0",
        "source": "finra_daily_short_sale_volume_missing_symbol",
    }


def _empty_listing_row(symbol: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "name": "",
        "exchange": "",
        "asset_type": "",
        "ipo_date": "",
        "delisting_date": "",
        "status": "unknown",
        "source": "listing_status_not_fetched",
    }


def _empty_news_row(symbol: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "date": date.today().isoformat(),
        "article_count": "0",
        "sentiment_score": "0",
        "source": "news_sentiment_not_fetched",
    }


def _empty_factor_row(symbol: str, *, source: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "sector": "unknown",
        "beta": "0",
        "size_score": "0",
        "value_score": "0",
        "quality_score": "0",
        "momentum_score": "0",
        "source": source,
        "as_of": date.today().isoformat(),
    }


def _finra_date(value: object) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _blank_null(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"null", "none", "nan"} else text


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch free US equity external data into local CSV files")
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--output-dir", default="data/auto_trading/free_external_data")
    parser.add_argument("--alpha-vantage-key", default="")
    parser.add_argument("--cik-map", default=None)
    parser.add_argument("--finra-date", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
