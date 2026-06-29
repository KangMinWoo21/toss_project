import csv
import calendar
import subprocess
import sys
import time
from datetime import date as Date
from pathlib import Path
from typing import Any, Callable


FLOW_COLUMNS = [
    "date",
    "symbol",
    "foreign_net_value",
    "institution_net_value",
    "individual_net_value",
    "insider_buy_value",
    "insider_sell_value",
]
OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
UNIVERSE_SNAPSHOT_COLUMNS = ["date", "symbol", "name", "market"]
MARKET_SNAPSHOT_COLUMNS = [
    "date",
    "symbol",
    "name",
    "market",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trading_value",
    "market_cap",
    "shares",
]
UNIVERSE_REPORT_COLUMNS = ["symbol", "name", "market", "output", "rows", "status", "error"]
MISSING_OHLCV_TARGET_COLUMNS = [
    "symbol",
    "name",
    "market",
    "missing_snapshots",
    "first_missing_date",
    "last_missing_date",
]
MISSING_OHLCV_FETCH_PLAN_COLUMNS = [
    "plan_id",
    "status",
    "target_count",
    "batch_size",
    "max_batches",
    "planned_batches",
    "planned_symbols",
    "remaining_after_plan",
    "batch_timeout_seconds",
    "batch_pause_seconds",
    "top_symbols",
    "start",
    "end",
    "universe_file",
    "data_dir",
    "targets_output",
    "report_dir",
    "recommended_command",
    "risk_note",
]
MISSING_OHLCV_LOOP_SUMMARY_COLUMNS = [
    "status",
    "attempted_batches",
    "completed_batches",
    "timed_out_batches",
    "failed_batches",
    "saved",
    "remaining_targets",
    "command_count",
    "last_stdout_tail",
    "last_stderr_tail",
]

DATE_KEY = "\ub0a0\uc9dc"
TICKER_KEY = "\ud2f0\ucee4"
OPEN_KEY = "\uc2dc\uac00"
HIGH_KEY = "\uace0\uac00"
LOW_KEY = "\uc800\uac00"
CLOSE_KEY = "\uc885\uac00"
VOLUME_KEY = "\uac70\ub798\ub7c9"
TRADING_VALUE_KEY = "\uac70\ub798\ub300\uae08"
MARKET_CAP_KEY = "\uc2dc\uac00\ucd1d\uc561"
SHARES_KEY = "\uc0c1\uc7a5\uc8fc\uc2dd\uc218"
FOREIGN_KEY = "\uc678\uad6d\uc778"
FOREIGN_TOTAL_KEY = "\uc678\uad6d\uc778\ud569\uacc4"
INSTITUTION_TOTAL_KEY = "\uae30\uad00\ud569\uacc4"
INSTITUTION_KEY = "\uae30\uad00"
INDIVIDUAL_KEY = "\uac1c\uc778"


def fetch_pykrx_flow_csv(start: str, end: str, symbol: str, output_path: Path | str) -> int:
    try:
        from pykrx import stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Install it with: pip install pykrx") from exc

    frame = stock.get_market_trading_value_by_date(
        start.replace("-", ""),
        end.replace("-", ""),
        symbol,
        detail=False,
    )
    if frame.empty:
        raise RuntimeError(
            "pykrx returned no flow rows. Check KRX_ID/KRX_PW in .env and the requested date range."
        )
    frame = frame.reset_index()
    rows = normalize_pykrx_trading_value_frame(symbol=symbol, rows=frame.to_dict("records"))
    return save_flow_rows(rows, output_path)


def fetch_pykrx_ohlcv_csv(start: str, end: str, symbol: str, output_path: Path | str) -> int:
    try:
        from pykrx import stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Install it with: pip install pykrx") from exc

    frame = stock.get_market_ohlcv_by_date(start.replace("-", ""), end.replace("-", ""), symbol)
    if frame.empty:
        raise RuntimeError("pykrx returned no OHLCV rows. Check the symbol and date range.")
    frame = frame.reset_index()
    rows = normalize_pykrx_ohlcv_frame(frame.to_dict("records"))
    return save_ohlcv_rows(rows, output_path)


def fetch_pykrx_universe_snapshot_csv(
    date: str,
    output_path: Path | str,
    *,
    markets: tuple[str, ...] = ("KOSPI", "KOSDAQ"),
) -> int:
    try:
        from pykrx import stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Install it with: pip install pykrx") from exc

    compact_date = date.replace("-", "")
    rows: list[dict[str, Any]] = []
    for market in markets:
        tickers = stock.get_market_ticker_list(compact_date, market=market)
        rows.extend(
            normalize_pykrx_universe_snapshot(
                date=date,
                market=market,
                tickers=tickers,
                name_lookup=stock.get_market_ticker_name,
            )
        )
    return save_universe_snapshot_rows(rows, output_path)


def fetch_pykrx_universe_snapshots_csv(
    start: str,
    end: str,
    output_path: Path | str,
    *,
    markets: tuple[str, ...] = ("KOSPI", "KOSDAQ"),
) -> int:
    rows: list[dict[str, Any]] = []
    for snapshot_date in monthly_snapshot_dates(start, end):
        rows.extend(_fetch_pykrx_universe_snapshot_rows(snapshot_date, markets=markets))
    return save_universe_snapshot_rows(rows, output_path)


def fetch_pykrx_market_snapshot_csv(
    date: str,
    output_path: Path | str,
    *,
    markets: tuple[str, ...] = ("KOSPI", "KOSDAQ"),
) -> int:
    try:
        from pykrx import stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Install it with: pip install pykrx") from exc

    compact_date = date.replace("-", "")
    rows: list[dict[str, Any]] = []
    for market in markets:
        ohlcv_frame = stock.get_market_ohlcv_by_ticker(compact_date, market=market).reset_index()
        market_cap_frame = stock.get_market_cap_by_ticker(compact_date, market=market).reset_index()
        rows.extend(
            normalize_pykrx_market_snapshot_frames(
                date=date,
                market=market,
                ohlcv_rows=ohlcv_frame.to_dict("records"),
                market_cap_rows=market_cap_frame.to_dict("records"),
                name_lookup=stock.get_market_ticker_name,
            )
        )
    return save_market_snapshot_rows(rows, output_path)


def monthly_snapshot_dates(start: str, end: str) -> list[str]:
    start_date = Date.fromisoformat(start)
    end_date = Date.fromisoformat(end)
    if end_date < start_date:
        return []
    rows: list[str] = []
    year = start_date.year
    month = start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        last_day = calendar.monthrange(year, month)[1]
        candidate = Date(year, month, last_day)
        if candidate < start_date:
            candidate = start_date
        if candidate > end_date:
            candidate = end_date
        value = candidate.isoformat()
        if not rows or rows[-1] != value:
            rows.append(value)
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return rows


def _fetch_pykrx_universe_snapshot_rows(date: str, *, markets: tuple[str, ...]) -> list[dict[str, Any]]:
    try:
        from pykrx import stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Install it with: pip install pykrx") from exc

    compact_date = date.replace("-", "")
    rows: list[dict[str, Any]] = []
    for market in markets:
        tickers = stock.get_market_ticker_list(compact_date, market=market)
        rows.extend(
            normalize_pykrx_universe_snapshot(
                date=date,
                market=market,
                tickers=tickers,
                name_lookup=stock.get_market_ticker_name,
            )
        )
    return rows


def load_symbol_universe(path: Path | str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "symbol" not in reader.fieldnames:
            raise RuntimeError("universe CSV must include a symbol column")
        for raw in reader:
            symbol = _normalize_symbol_code(raw.get("symbol", ""))
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            row = {key: (value or "").strip() for key, value in raw.items() if key is not None}
            row["symbol"] = symbol
            rows.append(row)
    return rows


def available_ohlcv_symbols(data_dir: Path | str) -> set[str]:
    root = Path(data_dir)
    symbols: set[str] = set()
    for path in root.glob("*.csv"):
        symbol = _normalize_symbol_code(path.stem.split("_")[0])
        if symbol:
            symbols.add(symbol)
    return symbols


def available_ohlcv_symbol_dates(data_dir: Path | str) -> dict[str, set[str]]:
    root = Path(data_dir)
    dates_by_symbol: dict[str, set[str]] = {}
    for path in root.glob("*.csv"):
        symbol = _normalize_symbol_code(path.stem.split("_")[0])
        if not symbol:
            continue
        dates: set[str] = set()
        try:
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_date = _normalize_date(row.get("date", ""))
                    if row_date:
                        dates.add(row_date)
        except (OSError, csv.Error, UnicodeDecodeError):
            dates = set()
        dates_by_symbol[symbol] = dates
    return dates_by_symbol


def load_universe_snapshot_rows(path: Path | str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        if not fieldnames or "symbol" not in fieldnames or not ({"date", "snapshot_date"} & fieldnames):
            raise RuntimeError("universe snapshot CSV must include date/snapshot_date and symbol columns")
        for raw in reader:
            symbol = _normalize_symbol_code(raw.get("symbol", ""))
            date = _normalize_date(raw.get("snapshot_date") or raw.get("date", ""))
            if not symbol or not date:
                continue
            row = {key: (value or "").strip() for key, value in raw.items() if key is not None}
            row["date"] = date
            row["symbol"] = symbol
            rows.append(row)
    return rows


def build_missing_ohlcv_targets(
    universe_rows: list[dict[str, Any]],
    *,
    available_symbols: set[str],
    available_symbol_dates: dict[str, set[str]] | None = None,
    exclude_untradable: bool = True,
) -> list[dict[str, Any]]:
    available = {_normalize_symbol_code(symbol) for symbol in available_symbols}
    coverage_dates = _normalize_available_symbol_dates(available_symbol_dates)
    grouped: dict[str, dict[str, Any]] = {}
    seen_symbol_dates: set[tuple[str, str]] = set()
    for raw in universe_rows:
        symbol = _normalize_symbol_code(raw.get("symbol", ""))
        snapshot_date = _normalize_date(raw.get("date", ""))
        if not symbol or not snapshot_date:
            continue
        if exclude_untradable and _missing_ohlcv_target_exclusion_reason(raw, snapshot_date):
            continue
        if _has_ohlcv_on_or_before_snapshot(symbol, snapshot_date, available, coverage_dates):
            continue
        key = (symbol, snapshot_date)
        if key in seen_symbol_dates:
            continue
        seen_symbol_dates.add(key)
        current = grouped.setdefault(
            symbol,
            {
                "symbol": symbol,
                "name": str(raw.get("name", "") or "").strip(),
                "market": str(raw.get("market", "") or "").strip(),
                "missing_snapshots": 0,
                "first_missing_date": snapshot_date,
                "last_missing_date": snapshot_date,
            },
        )
        current["missing_snapshots"] += 1
        current["first_missing_date"] = min(str(current["first_missing_date"]), snapshot_date)
        current["last_missing_date"] = max(str(current["last_missing_date"]), snapshot_date)
        if snapshot_date == current["last_missing_date"]:
            current["name"] = str(raw.get("name", current.get("name", "")) or "").strip()
            current["market"] = str(raw.get("market", current.get("market", "")) or "").strip()
    return sorted(
        grouped.values(),
        key=lambda row: (-int(row["missing_snapshots"]), str(row["last_missing_date"]), str(row["symbol"])),
    )


def _missing_ohlcv_target_exclusion_reason(row: dict[str, Any], snapshot_date: str) -> str:
    name = str(row.get("name", "") or "").strip()
    listed_date = _normalize_date(row.get("listed_date", ""))
    delisted_date = _normalize_date(row.get("delisted_date", ""))
    if listed_date and listed_date > snapshot_date:
        return "not_listed"
    if delisted_date and delisted_date <= snapshot_date:
        return "delisted"
    if _metadata_is_false(row.get("is_active", "")):
        return "inactive"
    if _metadata_is_false(row.get("tradable", "")):
        return "not_tradable"
    if _metadata_is_true(row.get("is_suspended", "")):
        return "suspended"
    if _metadata_is_true(row.get("is_managed", "")):
        return "managed"
    if _metadata_is_true(row.get("is_spac", "")) or _looks_like_spac(name):
        return "spac"
    if _metadata_is_true(row.get("is_preferred", "")) or _looks_like_preferred_stock(name):
        return "preferred"
    return ""


def _normalize_available_symbol_dates(
    available_symbol_dates: dict[str, set[str]] | None,
) -> dict[str, set[str]] | None:
    if available_symbol_dates is None:
        return None
    normalized: dict[str, set[str]] = {}
    for raw_symbol, raw_dates in available_symbol_dates.items():
        symbol = _normalize_symbol_code(raw_symbol)
        if not symbol:
            continue
        normalized[symbol] = {
            normalized_date
            for raw_date in raw_dates
            if (normalized_date := _normalize_date(raw_date))
        }
    return normalized


def _has_ohlcv_on_or_before_snapshot(
    symbol: str,
    snapshot_date: str,
    available_symbols: set[str],
    available_symbol_dates: dict[str, set[str]] | None,
) -> bool:
    if available_symbol_dates is None:
        return symbol in available_symbols
    return any(row_date <= snapshot_date for row_date in available_symbol_dates.get(symbol, set()))


def save_missing_ohlcv_targets(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MISSING_OHLCV_TARGET_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in MISSING_OHLCV_TARGET_COLUMNS} for row in rows)
    return len(rows)


def build_missing_ohlcv_fetch_plan(
    target_rows: list[dict[str, Any]],
    *,
    batch_size: int,
    max_batches: int,
    batch_timeout_seconds: float,
    batch_pause_seconds: float,
    universe_file: Path | str,
    data_dir: Path | str,
    targets_output: Path | str,
    report_dir: Path | str,
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if max_batches <= 0:
        raise ValueError("max_batches must be greater than zero")
    if batch_timeout_seconds <= 0:
        raise ValueError("batch_timeout_seconds must be greater than zero")

    sorted_targets = sorted(
        target_rows,
        key=lambda row: (-_safe_int(row.get("missing_snapshots", 0)), str(row.get("symbol", ""))),
    )
    target_count = len(sorted_targets)
    planned_symbols = min(target_count, batch_size * max_batches)
    planned_batches = 0
    if planned_symbols > 0:
        planned_batches = min(max_batches, (planned_symbols + batch_size - 1) // batch_size)
    remaining_after_plan = max(0, target_count - planned_symbols)
    top_symbols = "; ".join(
        f"{str(row.get('symbol', '')).strip()}:{_safe_int(row.get('missing_snapshots', 0))}"
        for row in sorted_targets[:5]
        if str(row.get("symbol", "")).strip()
    )
    status = "READY" if target_count else "COMPLETE"
    command = (
        "python -m backtester fetch-pykrx-missing-ohlcv-loop "
        f"--universe-file \"{universe_file}\" --start {start} --end {end} "
        f"--data-dir \"{data_dir}\" --targets-output \"{targets_output}\" "
        f"--report-dir \"{report_dir}\" --batch-size {batch_size} --max-batches {max_batches} "
        f"--batch-timeout-seconds {batch_timeout_seconds:g} --batch-pause-seconds {batch_pause_seconds:g}"
    )
    risk_note = (
        "Plan only; run during off-hours or with conservative batch/timeouts. "
        "Rerun production-check and monthly-validate after fetch completion."
    )
    return [
        {
            "plan_id": "missing_ohlcv_fetch",
            "status": status,
            "target_count": target_count,
            "batch_size": batch_size,
            "max_batches": max_batches,
            "planned_batches": planned_batches,
            "planned_symbols": planned_symbols,
            "remaining_after_plan": remaining_after_plan,
            "batch_timeout_seconds": batch_timeout_seconds,
            "batch_pause_seconds": batch_pause_seconds,
            "top_symbols": top_symbols,
            "start": start,
            "end": end,
            "universe_file": str(universe_file),
            "data_dir": str(data_dir),
            "targets_output": str(targets_output),
            "report_dir": str(report_dir),
            "recommended_command": command,
            "risk_note": risk_note,
        }
    ]


def save_missing_ohlcv_fetch_plan(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MISSING_OHLCV_FETCH_PLAN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MISSING_OHLCV_FETCH_PLAN_COLUMNS})
    return len(rows)


def save_missing_ohlcv_loop_summary(summary: dict[str, Any], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    outputs = list(summary.get("outputs", []) or [])
    last_output = outputs[-1] if outputs else {}
    row = {
        "status": summary.get("status", ""),
        "attempted_batches": summary.get("attempted_batches", 0),
        "completed_batches": summary.get("completed_batches", 0),
        "timed_out_batches": summary.get("timed_out_batches", 0),
        "failed_batches": summary.get("failed_batches", 0),
        "saved": summary.get("saved", 0),
        "remaining_targets": summary.get("remaining_targets", 0),
        "command_count": len(summary.get("commands", []) or []),
        "last_stdout_tail": _text_tail(last_output.get("stdout", "")),
        "last_stderr_tail": _text_tail(last_output.get("stderr", "")),
    }
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MISSING_OHLCV_LOOP_SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    return 1


def fetch_missing_ohlcv_batches(
    *,
    start: str,
    end: str,
    universe_file: Path | str,
    data_dir: Path | str,
    targets_output: Path | str,
    report_dir: Path | str,
    batch_size: int = 50,
    batches: int = 1,
    batch_pause_seconds: float = 0.0,
    report_prefix: str = "krx_missing_ohlcv_fetch",
    skip_existing: bool = True,
    fetcher: Callable[[str, str, str, Path | str], int] = fetch_pykrx_ohlcv_csv,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if batches <= 0:
        raise ValueError("batches must be greater than zero")

    report_root = Path(report_dir)
    report_root.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "batches_run": 0,
        "processed": 0,
        "saved": 0,
        "skipped": 0,
        "failed": 0,
        "rows": 0,
        "remaining_targets": 0,
        "reports": [],
    }

    for batch_index in range(1, batches + 1):
        targets = build_missing_ohlcv_targets(
            load_universe_snapshot_rows(universe_file),
            available_symbols=available_ohlcv_symbols(data_dir),
            available_symbol_dates=available_ohlcv_symbol_dates(data_dir),
        )
        save_missing_ohlcv_targets(targets, targets_output)
        if not targets:
            break

        batch_targets = targets[:batch_size]
        report_path = report_root / f"{report_prefix}_batch{batch_index:03d}.csv"
        report = fetch_pykrx_ohlcv_universe_csv(
            start=start,
            end=end,
            symbols=batch_targets,
            output_dir=data_dir,
            skip_existing=skip_existing,
            fetcher=fetcher,
            checkpoint_report_path=report_path,
        )
        save_universe_fetch_report(report, report_path)

        summary["batches_run"] += 1
        summary["processed"] += len(report)
        summary["saved"] += sum(1 for row in report if row["status"] == "saved")
        summary["skipped"] += sum(1 for row in report if row["status"] == "skipped")
        summary["failed"] += sum(1 for row in report if row["status"] == "failed")
        summary["rows"] += sum(int(row["rows"]) for row in report)
        summary["reports"].append(str(report_path))
        if batch_index < batches and batch_pause_seconds > 0:
            sleeper(batch_pause_seconds)

    remaining = build_missing_ohlcv_targets(
        load_universe_snapshot_rows(universe_file),
        available_symbols=available_ohlcv_symbols(data_dir),
        available_symbol_dates=available_ohlcv_symbol_dates(data_dir),
    )
    summary["remaining_targets"] = save_missing_ohlcv_targets(remaining, targets_output)
    return summary


def run_missing_ohlcv_batch_subprocess_loop(
    *,
    start: str,
    end: str,
    universe_file: Path | str,
    data_dir: Path | str,
    targets_output: Path | str,
    report_dir: Path | str,
    report_prefix: str = "krx_missing_ohlcv_fetch",
    batch_size: int = 50,
    max_batches: int = 1,
    batch_timeout_seconds: float = 300.0,
    batch_pause_seconds: float = 10.0,
    python_executable: str | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if max_batches <= 0:
        raise ValueError("max_batches must be greater than zero")
    if batch_timeout_seconds <= 0:
        raise ValueError("batch_timeout_seconds must be greater than zero")

    executable = python_executable or sys.executable
    summary: dict[str, Any] = {
        "status": "completed",
        "attempted_batches": 0,
        "completed_batches": 0,
        "timed_out_batches": 0,
        "failed_batches": 0,
        "saved": 0,
        "remaining_targets": None,
        "commands": [],
        "outputs": [],
    }

    for batch_index in range(1, max_batches + 1):
        command = [
            executable,
            "-m",
            "backtester",
            "fetch-pykrx-missing-ohlcv-batches",
            "--universe-file",
            str(universe_file),
            "--start",
            start,
            "--end",
            end,
            "--data-dir",
            str(data_dir),
            "--targets-output",
            str(targets_output),
            "--report-dir",
            str(report_dir),
            "--report-prefix",
            f"{report_prefix}_loop{batch_index:03d}",
            "--batch-size",
            str(batch_size),
            "--batches",
            "1",
            "--batch-pause-seconds",
            "0",
        ]
        summary["attempted_batches"] += 1
        summary["commands"].append(command)
        try:
            completed = command_runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=batch_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            summary["status"] = "timed_out"
            summary["timed_out_batches"] += 1
            summary["outputs"].append({"stdout": exc.stdout or "", "stderr": exc.stderr or ""})
            break

        summary["outputs"].append({"stdout": completed.stdout or "", "stderr": completed.stderr or ""})
        if completed.returncode != 0:
            summary["status"] = "failed"
            summary["failed_batches"] += 1
            break

        summary["completed_batches"] += 1
        stdout = completed.stdout or ""
        summary["saved"] += _extract_summary_int(stdout, "saved")
        remaining = _extract_summary_int(stdout, "remaining_targets")
        summary["remaining_targets"] = remaining
        if remaining == 0:
            break
        if batch_index < max_batches and batch_pause_seconds > 0:
            sleeper(batch_pause_seconds)

    if summary["remaining_targets"] is None and Path(targets_output).exists():
        summary["remaining_targets"] = len(load_symbol_universe(targets_output))
    if summary["remaining_targets"] is None:
        summary["remaining_targets"] = 0
    return summary


def fetch_pykrx_ohlcv_universe_csv(
    start: str,
    end: str,
    symbols: list[dict[str, str]] | list[str],
    output_dir: Path | str,
    *,
    skip_existing: bool = True,
    fetcher: Callable[[str, str, str, Path | str], int] = fetch_pykrx_ohlcv_csv,
    checkpoint_report_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, Any]] = []
    for entry in symbols:
        row = _symbol_entry_to_row(entry)
        symbol = row["symbol"]
        target = output_path / f"{symbol}.csv"
        if skip_existing and target.exists() and target.stat().st_size > 0:
            report.append(
                {
                    "symbol": symbol,
                    "name": row.get("name", ""),
                    "market": row.get("market", ""),
                    "output": str(target),
                    "rows": _count_csv_data_rows(target),
                    "status": "skipped",
                    "error": "",
                }
            )
            if checkpoint_report_path is not None:
                save_universe_fetch_report(report, checkpoint_report_path)
            continue
        try:
            saved = fetcher(start, end, symbol, target)
        except Exception as exc:  # Keep one broken ticker from stopping the universe fetch.
            report.append(
                {
                    "symbol": symbol,
                    "name": row.get("name", ""),
                    "market": row.get("market", ""),
                    "output": str(target),
                    "rows": 0,
                    "status": "failed",
                    "error": str(exc),
                }
            )
        else:
            report.append(
                {
                    "symbol": symbol,
                    "name": row.get("name", ""),
                    "market": row.get("market", ""),
                    "output": str(target),
                    "rows": saved,
                    "status": "saved",
                    "error": "",
                }
            )
        if checkpoint_report_path is not None:
            save_universe_fetch_report(report, checkpoint_report_path)
    return report


def save_universe_fetch_report(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIVERSE_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in UNIVERSE_REPORT_COLUMNS} for row in rows)
    return len(rows)


def normalize_pykrx_trading_value_frame(symbol: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "date": _normalize_date(row.get(DATE_KEY, row.get("date", ""))),
                "symbol": symbol,
                "foreign_net_value": _number(row.get(FOREIGN_KEY, row.get(FOREIGN_TOTAL_KEY, 0))),
                "institution_net_value": _number(row.get(INSTITUTION_TOTAL_KEY, row.get(INSTITUTION_KEY, 0))),
                "individual_net_value": _number(row.get(INDIVIDUAL_KEY, 0)),
                "insider_buy_value": 0,
                "insider_sell_value": 0,
            }
        )
    return normalized


def normalize_pykrx_ohlcv_frame(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "date": _normalize_date(row.get(DATE_KEY, row.get("date", ""))),
                "open": _number(row.get(OPEN_KEY, row.get("open", 0))),
                "high": _number(row.get(HIGH_KEY, row.get("high", 0))),
                "low": _number(row.get(LOW_KEY, row.get("low", 0))),
                "close": _number(row.get(CLOSE_KEY, row.get("close", 0))),
                "volume": int(_number(row.get(VOLUME_KEY, row.get("volume", 0)))),
            }
        )
    return normalized


def normalize_pykrx_universe_snapshot(
    *,
    date: str,
    market: str,
    tickers: list[Any],
    name_lookup: Callable[[str], str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_ticker in tickers:
        symbol = _normalize_symbol_code(raw_ticker)
        if not symbol:
            continue
        rows.append(
            {
                "date": _normalize_date(date),
                "symbol": symbol,
                "name": name_lookup(symbol),
                "market": market,
            }
        )
    return rows


def normalize_pykrx_market_snapshot_frames(
    *,
    date: str,
    market: str,
    ohlcv_rows: list[dict[str, Any]],
    market_cap_rows: list[dict[str, Any]],
    name_lookup: Callable[[str], str],
) -> list[dict[str, Any]]:
    cap_by_symbol = {_row_symbol(row): row for row in market_cap_rows if _row_symbol(row)}
    normalized: list[dict[str, Any]] = []
    for row in ohlcv_rows:
        symbol = _row_symbol(row)
        if not symbol:
            continue
        cap_row = cap_by_symbol.get(symbol, {})
        normalized.append(
            {
                "date": _normalize_date(date),
                "symbol": symbol,
                "name": name_lookup(symbol),
                "market": market,
                "open": _number(row.get(OPEN_KEY, row.get("open", 0))),
                "high": _number(row.get(HIGH_KEY, row.get("high", 0))),
                "low": _number(row.get(LOW_KEY, row.get("low", 0))),
                "close": _number(row.get(CLOSE_KEY, row.get("close", cap_row.get(CLOSE_KEY, 0)))),
                "volume": int(_number(row.get(VOLUME_KEY, row.get("volume", cap_row.get(VOLUME_KEY, 0))))),
                "trading_value": _number(
                    row.get(TRADING_VALUE_KEY, row.get("trading_value", cap_row.get(TRADING_VALUE_KEY, 0)))
                ),
                "market_cap": _number(cap_row.get(MARKET_CAP_KEY, cap_row.get("market_cap", 0))),
                "shares": _number(cap_row.get(SHARES_KEY, cap_row.get("shares", 0))),
            }
        )
    return normalized


def save_flow_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FLOW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def save_ohlcv_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OHLCV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def save_universe_snapshot_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIVERSE_SNAPSHOT_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in UNIVERSE_SNAPSHOT_COLUMNS} for row in rows)
    return len(rows)


def save_market_snapshot_rows(rows: list[dict[str, Any]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MARKET_SNAPSHOT_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in MARKET_SNAPSHOT_COLUMNS} for row in rows)
    return len(rows)


def _normalize_date(value: Any) -> str:
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return text


def _normalize_symbol_code(value: Any) -> str:
    text = str(value).strip().strip("'").strip('"')
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text.upper()


def _metadata_is_true(value: Any) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "t", "active", "pass"}


def _metadata_is_false(value: Any) -> bool:
    return str(value).strip().casefold() in {"0", "false", "no", "n", "f", "inactive", "blocked"}


def _looks_like_spac(name: str) -> bool:
    normalized = str(name or "").replace(" ", "").upper()
    return "스팩" in normalized or "SPAC" in normalized


def _looks_like_preferred_stock(name: str) -> bool:
    normalized = str(name or "").replace(" ", "").upper()
    if not normalized:
        return False
    return (
        normalized.endswith("우")
        or normalized.endswith("우B")
        or normalized.endswith("1우")
        or normalized.endswith("2우")
        or normalized.endswith("3우")
        or normalized.endswith("1우B")
        or normalized.endswith("2우B")
        or normalized.endswith("3우B")
    )


def _symbol_entry_to_row(entry: dict[str, str] | str) -> dict[str, str]:
    if isinstance(entry, str):
        return {"symbol": _normalize_symbol_code(entry), "name": "", "market": ""}
    row = {key: str(value).strip() for key, value in entry.items()}
    row["symbol"] = _normalize_symbol_code(row.get("symbol", ""))
    return row


def _row_symbol(row: dict[str, Any]) -> str:
    for key in (TICKER_KEY, "ticker", "symbol", "index"):
        symbol = _normalize_symbol_code(row.get(key, ""))
        if symbol:
            return symbol
    return ""


def _count_csv_data_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)


def _extract_summary_int(text: str, key: str) -> int:
    for line in str(text).splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == key:
            try:
                return int(parts[1])
            except ValueError:
                return 0
    return 0


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _text_tail(value: Any, *, max_chars: int = 500) -> str:
    text = str(value or "").replace("\r\n", "\n").strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(str(value).replace(",", ""))
