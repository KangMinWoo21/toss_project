import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .scalper import OrderbookLevel, TickSnapshot


BASE_URL = "https://openapi.tossinvest.com"


def issue_token(client_id: str, client_secret: str, base_url: str = BASE_URL) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    response = _request_json(request)
    return str(response["access_token"])


def fetch_candles_page(
    access_token: str,
    symbol: str,
    interval: str = "1d",
    count: int = 200,
    before: str | None = None,
    adjusted: bool = True,
    base_url: str = BASE_URL,
) -> dict[str, Any]:
    query = {
        "symbol": symbol,
        "interval": interval,
        "count": str(count),
        "adjusted": str(adjusted).lower(),
    }
    if before:
        query["before"] = before
    url = f"{base_url}/api/v1/candles?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _request_json(request)


def fetch_price(access_token: str, symbol: str, base_url: str = BASE_URL) -> dict[str, Any]:
    query = urllib.parse.urlencode({"symbols": symbol})
    request = urllib.request.Request(
        f"{base_url}/api/v1/prices?{query}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _request_json(request)


def fetch_orderbook(access_token: str, symbol: str, base_url: str = BASE_URL) -> dict[str, Any]:
    query = urllib.parse.urlencode({"symbol": symbol})
    request = urllib.request.Request(
        f"{base_url}/api/v1/orderbook?{query}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _request_json(request)


def fetch_trades(access_token: str, symbol: str, count: int = 20, base_url: str = BASE_URL) -> dict[str, Any]:
    query = urllib.parse.urlencode({"symbol": symbol, "count": str(count)})
    request = urllib.request.Request(
        f"{base_url}/api/v1/trades?{query}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _request_json(request)


def fetch_market_calendar(access_token: str, market: str, base_url: str = BASE_URL) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}/api/v1/market-calendar/{market}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _request_json(request)


def fetch_tick_snapshot(access_token: str, symbol: str, base_url: str = BASE_URL) -> TickSnapshot:
    return market_payloads_to_snapshot(
        price_payload=fetch_price(access_token, symbol, base_url=base_url),
        orderbook_payload=fetch_orderbook(access_token, symbol, base_url=base_url),
        trades_payload=fetch_trades(access_token, symbol, base_url=base_url),
    )


def download_daily_candles_csv(
    client_id: str,
    client_secret: str,
    symbol: str,
    output_path: Path | str,
    pages: int = 5,
    interval: str = "1d",
    base_url: str = BASE_URL,
) -> int:
    access_token = issue_token(client_id, client_secret, base_url=base_url)
    before = None
    rows: list[list[object]] = []
    for _ in range(pages):
        page = fetch_candles_page(
            access_token=access_token,
            symbol=symbol,
            interval=interval,
            count=200,
            before=before,
            adjusted=True,
            base_url=base_url,
        )
        rows.extend(candle_page_to_rows(page, keep_timestamp=interval == "1m"))
        before = page.get("result", {}).get("nextBefore")
        if not before:
            break

    rows.sort(key=lambda row: str(row[0]))
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
    return len(rows)


def candle_page_to_rows(page: dict[str, Any], keep_timestamp: bool = False) -> list[list[object]]:
    candles = page.get("result", {}).get("candles", [])
    rows: list[list[object]] = []
    for candle in candles:
        timestamp = str(candle["timestamp"])
        rows.append(
            [
                timestamp if keep_timestamp else timestamp[:10],
                float(candle["openPrice"]),
                float(candle["highPrice"]),
                float(candle["lowPrice"]),
                float(candle["closePrice"]),
                int(candle["volume"]),
            ]
        )
    return rows


def market_payloads_to_snapshot(
    price_payload: dict[str, Any],
    orderbook_payload: dict[str, Any],
    trades_payload: dict[str, Any],
) -> TickSnapshot:
    price_result = price_payload.get("result", [])
    price_row = price_result[0] if isinstance(price_result, list) and price_result else {}
    orderbook = orderbook_payload.get("result", {})
    trades = trades_payload.get("result", [])
    return TickSnapshot(
        timestamp=str(price_row.get("timestamp", orderbook.get("timestamp", ""))),
        last_price=float(price_row["lastPrice"]),
        recent_trade_volume=sum(float(trade.get("volume", 0)) for trade in trades),
        bids=[
            OrderbookLevel(price=float(level["price"]), volume=float(level["volume"]))
            for level in orderbook.get("bids", [])
        ],
        asks=[
            OrderbookLevel(price=float(level["price"]), volume=float(level["volume"]))
            for level in orderbook.get("asks", [])
        ],
    )


def _request_json(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
