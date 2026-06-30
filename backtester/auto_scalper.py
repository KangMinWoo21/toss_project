import time
from datetime import datetime
from pathlib import Path
import re
from typing import Callable
from zoneinfo import ZoneInfo

from .scalper import ScalperConfig, ScalperState, run_paper_scalper
from .toss import fetch_tick_snapshot


KR_SESSIONS = ["regularMarket"]
US_SESSIONS = ["dayMarket", "preMarket", "regularMarket", "afterMarket"]
KST = ZoneInfo("Asia/Seoul")
_SAFE_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_symbol_list(value: str) -> list[str]:
    return [_validate_symbol(part.strip()) for part in value.split(",") if part.strip()]


def is_market_open(calendar: dict[str, object], now: datetime, session_names: list[str]) -> bool:
    for day in _calendar_days(calendar):
        for session_name in session_names:
            session = _session_from_day(day, session_name)
            if not isinstance(session, dict):
                continue
            start = session.get("startTime") or session.get("startDateTime")
            end = session.get("endTime") or session.get("endDateTime")
            if not start or not end:
                continue
            if datetime.fromisoformat(str(start)) <= now <= datetime.fromisoformat(str(end)):
                return True
    return False


def choose_symbols_for_now(
    kr_calendar: dict[str, object],
    us_calendar: dict[str, object],
    now: datetime,
    kr_symbols: list[str],
    us_symbols: list[str],
) -> tuple[str | None, list[str]]:
    if kr_symbols and is_market_open(kr_calendar, now, KR_SESSIONS):
        return "KR", kr_symbols
    if us_symbols and is_market_open(us_calendar, now, US_SESSIONS):
        return "US", us_symbols
    return None, []


def run_auto_scalper_once(
    now: datetime,
    kr_calendar: dict[str, object],
    us_calendar: dict[str, object],
    kr_symbols: list[str],
    us_symbols: list[str],
    output_dir: Path | str,
    runner: Callable[[str, Path, str], int],
) -> list[tuple[str, str, int]]:
    market, symbols = choose_symbols_for_now(
        kr_calendar=kr_calendar,
        us_calendar=us_calendar,
        now=now,
        kr_symbols=kr_symbols,
        us_symbols=us_symbols,
    )
    if market is None:
        return []

    required_date = now.date().isoformat()
    rows: list[tuple[str, str, int]] = []
    for symbol in symbols:
        symbol = _validate_symbol(symbol)
        output_path = Path(output_dir) / f"{symbol}_{required_date}_paper_scalp.csv"
        saved = runner(symbol, output_path, required_date)
        rows.append((market, symbol, saved))
    return rows


def auto_scalper_sleep_seconds(
    rows: list[tuple[str, str, int]],
    *,
    interval_seconds: float,
    idle_seconds: float,
) -> float:
    return interval_seconds if rows else idle_seconds


def run_auto_scalper_loop(
    access_token: str,
    kr_calendar_fetcher: Callable[[], dict[str, object]],
    us_calendar_fetcher: Callable[[], dict[str, object]],
    kr_symbols: list[str],
    us_symbols: list[str],
    output_dir: Path | str,
    interval_seconds: float,
    iterations_per_symbol: int,
    idle_seconds: float,
    config: ScalperConfig,
) -> None:
    states: dict[str, ScalperState] = {}
    while True:
        now = datetime.now(KST)
        kr_calendar = kr_calendar_fetcher()
        us_calendar = us_calendar_fetcher()

        def runner(symbol: str, output_path: Path, required_date: str) -> int:
            rows = run_paper_scalper(
                snapshot_fetcher=lambda: fetch_tick_snapshot(access_token, symbol),
                iterations=iterations_per_symbol,
                interval_seconds=interval_seconds,
                output_path=output_path,
                config=config,
                append=True,
                required_date=required_date,
                state=states.setdefault(symbol, ScalperState()),
            )
            return len(rows)

        rows = run_auto_scalper_once(
            now=now,
            kr_calendar=kr_calendar,
            us_calendar=us_calendar,
            kr_symbols=kr_symbols,
            us_symbols=us_symbols,
            output_dir=output_dir,
            runner=runner,
        )
        if rows:
            for market, symbol, saved in rows:
                print(f"{now.isoformat()} market={market} symbol={symbol} saved={saved}", flush=True)
        else:
            print(f"{now.isoformat()} market=closed sleeping={idle_seconds}", flush=True)
        sleep_seconds = auto_scalper_sleep_seconds(
            rows,
            interval_seconds=interval_seconds,
            idle_seconds=idle_seconds,
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


def _calendar_days(calendar: dict[str, object]) -> list[dict[str, object]]:
    result = calendar.get("result", [])
    if isinstance(result, dict):
        values = result.get("markets") or result.get("days") or result.get("items")
        if values is None:
            values = [
                result.get("previousBusinessDay"),
                result.get("today"),
                result.get("nextBusinessDay"),
            ]
        return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _session_from_day(day: dict[str, object], session_name: str) -> object:
    session = day.get(session_name)
    if session is not None:
        return session
    integrated = day.get("integrated")
    if isinstance(integrated, dict):
        return integrated.get(session_name)
    return None


def _validate_symbol(symbol: str) -> str:
    if not _SAFE_SYMBOL_RE.fullmatch(symbol) or symbol in {".", ".."}:
        raise ValueError(f"unsafe symbol for output path: {symbol}")
    return symbol
