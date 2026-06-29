import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


CANDLE_COLUMNS = {"date", "open", "high", "low", "close", "volume"}
UNIVERSE_COLUMNS = {"date", "symbol"}
DIAGNOSTIC_COLUMNS = [
    "symbol",
    "file_path",
    "status",
    "reason_code",
    "issue_count",
    "warning_count",
    "latest_date",
    "stale_days",
    "first_issue",
    "suggested_action",
]
REASON_PRIORITY = [
    "missing_columns",
    "symbol_mapping_error_if_detectable",
    "missing_close",
    "duplicate_dates",
    "zero_or_negative_price",
    "invalid_ohlc",
    "volume_anomaly",
    "stale_data",
    "suspected_split_or_adjustment_issue",
    "unknown",
]


@dataclass(frozen=True)
class DataQualityResult:
    status: str
    issues: list[str]
    warnings: list[str]
    latest_date: str | None
    stale_days: int | None
    rows_checked: int
    blocked_symbols: tuple[str, ...] = ()
    symbol_issues: tuple["DataQualitySymbolIssue", ...] = ()


@dataclass(frozen=True)
class DataQualitySymbolIssue:
    symbol: str
    status: str
    reason: str


@dataclass(frozen=True)
class CandleCsvDiagnosis:
    symbol: str
    file_path: str
    status: str
    reason_code: str
    issue_count: int
    warning_count: int
    latest_date: str | None
    stale_days: int | None
    first_issue: str
    suggested_action: str


def validate_candle_dataframe(
    rows: Any,
    *,
    as_of_date: str | None = None,
    max_stale_days: int | None = None,
) -> DataQualityResult:
    records = _records_from_input(rows)
    issues: list[str] = []
    warnings: list[str] = []
    if not records:
        return DataQualityResult("BLOCK", ["no candle rows"], [], None, None, 0)

    fieldnames = set().union(*(record.keys() for record in records))
    missing = CANDLE_COLUMNS.difference(fieldnames)
    if missing:
        return DataQualityResult(
            "BLOCK",
            [f"missing columns: {', '.join(sorted(missing))}"],
            [],
            None,
            None,
            len(records),
        )

    parsed_dates: list[date] = []
    seen_dates: set[str] = set()
    previous_date: date | None = None
    for index, record in enumerate(records, start=1):
        raw_date = str(record.get("date", "")).strip()
        try:
            row_date = date.fromisoformat(raw_date)
            parsed_dates.append(row_date)
        except ValueError:
            issues.append(f"row {index} invalid date: {raw_date}")
            row_date = None
        if raw_date in seen_dates:
            issues.append(f"row {index} duplicate date: {raw_date}")
        seen_dates.add(raw_date)
        if row_date is not None and previous_date is not None and row_date < previous_date:
            warnings.append(f"row {index} date out of order: {raw_date}")
        if row_date is not None:
            previous_date = row_date
        _validate_ohlcv(record, index, issues)

    latest = max(parsed_dates).isoformat() if parsed_dates else None
    stale_days = _stale_days(latest, as_of_date)
    if stale_days is not None and max_stale_days is not None and stale_days > max_stale_days:
        issues.append(f"stale by {stale_days}d exceeds {max_stale_days}d")

    return DataQualityResult(
        _status(issues, warnings),
        issues,
        warnings,
        latest,
        stale_days,
        len(records),
    )


def validate_candle_csv(
    path: Path | str,
    *,
    as_of_date: str | None = None,
    max_stale_days: int | None = None,
) -> DataQualityResult:
    csv_path = Path(path)
    if not csv_path.exists():
        return DataQualityResult("BLOCK", [f"missing file: {csv_path}"], [], None, None, 0)
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return DataQualityResult("BLOCK", [f"{csv_path} has no header"], [], None, None, 0)
        return validate_candle_dataframe(
            list(reader),
            as_of_date=as_of_date,
            max_stale_days=max_stale_days,
        )


def validate_dataset_freshness(
    path: Path | str,
    *,
    as_of_date: str | None = None,
    max_stale_days: int = 7,
) -> DataQualityResult:
    root = Path(path)
    if root.is_file():
        return validate_candle_csv(root, as_of_date=as_of_date, max_stale_days=max_stale_days)
    if not root.exists():
        return DataQualityResult("BLOCK", [f"missing path: {root}"], [], None, None, 0)

    csv_files = sorted(item for item in root.glob("*.csv") if item.is_file())
    if not csv_files:
        return DataQualityResult("BLOCK", [f"no csv files in: {root}"], [], None, None, 0)

    issues: list[str] = []
    warnings: list[str] = []
    symbol_issues: list[DataQualitySymbolIssue] = []
    latest_dates: list[str] = []
    stale_values: list[int] = []
    rows_checked = 0
    for csv_file in csv_files:
        result = validate_candle_csv(
            csv_file,
            as_of_date=as_of_date,
            max_stale_days=max_stale_days,
        )
        rows_checked += result.rows_checked
        if result.latest_date:
            latest_dates.append(result.latest_date)
        if result.stale_days is not None:
            stale_values.append(result.stale_days)
        if result.status == "BLOCK":
            symbol_issues.append(
                DataQualitySymbolIssue(
                    symbol=csv_file.stem,
                    status="BLOCK",
                    reason="; ".join(result.issues[:5]) or "blocked data quality",
                )
            )
        issues.extend(f"{csv_file.name} {issue}" for issue in result.issues)
        warnings.extend(f"{csv_file.name} {warning}" for warning in result.warnings)

    latest = max(latest_dates) if latest_dates else None
    stale_days = max(stale_values) if stale_values else None
    blocked_symbols = tuple(issue.symbol for issue in symbol_issues if issue.status == "BLOCK")
    return DataQualityResult(
        _status(issues, warnings),
        issues,
        warnings,
        latest,
        stale_days,
        rows_checked,
        blocked_symbols,
        tuple(symbol_issues),
    )


def validate_universe_metadata(path: Path | str) -> DataQualityResult:
    csv_path = Path(path)
    if not csv_path.exists():
        return DataQualityResult("BLOCK", [f"missing file: {csv_path}"], [], None, None, 0)
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return DataQualityResult("BLOCK", [f"{csv_path} has no header"], [], None, None, 0)
        missing = UNIVERSE_COLUMNS.difference(reader.fieldnames)
        rows = list(reader)
    issues: list[str] = []
    if missing:
        issues.append(f"missing columns: {', '.join(sorted(missing))}")
    if not rows:
        issues.append("no universe rows")
    latest = _latest_date(row.get("date", "") for row in rows)
    return DataQualityResult(_status(issues, []), issues, [], latest, None, len(rows))


def diagnose_candle_csv(
    path: Path | str,
    *,
    as_of_date: str | None = None,
    max_stale_days: int | None = None,
) -> CandleCsvDiagnosis:
    csv_path = Path(path)
    symbol = _symbol_from_path(csv_path)
    issues_by_code: dict[str, list[str]] = {code: [] for code in REASON_PRIORITY}
    warnings_by_code: dict[str, list[str]] = {code: [] for code in REASON_PRIORITY}
    rows_checked = 0
    latest_date: str | None = None
    stale_days: int | None = None

    _diagnose_symbol_mapping(csv_path, symbol, warnings_by_code)

    if not csv_path.exists():
        issues_by_code["unknown"].append(f"missing file: {csv_path}")
        return _diagnosis_from_codes(symbol, csv_path, issues_by_code, warnings_by_code, None, None)

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            issues_by_code["missing_columns"].append(f"{csv_path} has no header")
            return _diagnosis_from_codes(symbol, csv_path, issues_by_code, warnings_by_code, None, None)
        missing = CANDLE_COLUMNS.difference(reader.fieldnames)
        if missing:
            issues_by_code["missing_columns"].append(f"missing columns: {', '.join(sorted(missing))}")
            return _diagnosis_from_codes(symbol, csv_path, issues_by_code, warnings_by_code, None, None)
        rows = list(reader)

    rows_checked = len(rows)
    if not rows:
        issues_by_code["unknown"].append("no candle rows")
        return _diagnosis_from_codes(symbol, csv_path, issues_by_code, warnings_by_code, None, None)

    seen_dates: set[str] = set()
    parsed_dates: list[date] = []
    previous_close: float | None = None
    for index, row in enumerate(rows, start=1):
        raw_date = str(row.get("date", "")).strip()
        try:
            parsed_dates.append(date.fromisoformat(raw_date))
        except ValueError:
            issues_by_code["unknown"].append(f"row {index} invalid date: {raw_date}")
        if raw_date in seen_dates:
            issues_by_code["duplicate_dates"].append(f"row {index} duplicate date: {raw_date}")
        seen_dates.add(raw_date)
        _diagnose_ohlcv_row(row, index, issues_by_code, warnings_by_code)
        close_value = _optional_float(row.get("close"))
        if close_value is not None and previous_close is not None and previous_close > 0 and close_value > 0:
            ratio = max(close_value / previous_close, previous_close / close_value)
            if ratio >= 5.0:
                warnings_by_code["suspected_split_or_adjustment_issue"].append(
                    f"row {index} close jump ratio {ratio:.2f}"
                )
        if close_value is not None and close_value > 0:
            previous_close = close_value

    latest_date = max(parsed_dates).isoformat() if parsed_dates else None
    stale_days = _stale_days(latest_date, as_of_date)
    if stale_days is not None and max_stale_days is not None and stale_days > max_stale_days:
        issues_by_code["stale_data"].append(f"stale by {stale_days}d exceeds {max_stale_days}d")

    return _diagnosis_from_codes(symbol, csv_path, issues_by_code, warnings_by_code, latest_date, stale_days)


def diagnose_candle_dataset(
    path: Path | str,
    *,
    as_of_date: str | None = None,
    max_stale_days: int | None = None,
) -> list[CandleCsvDiagnosis]:
    root = Path(path)
    if root.is_file():
        return [diagnose_candle_csv(root, as_of_date=as_of_date, max_stale_days=max_stale_days)]
    if not root.exists():
        return [
            CandleCsvDiagnosis(
                symbol="",
                file_path=str(root),
                status="BLOCK",
                reason_code="unknown",
                issue_count=1,
                warning_count=0,
                latest_date=None,
                stale_days=None,
                first_issue=f"missing path: {root}",
                suggested_action="REVIEW",
            )
        ]
    return [
        diagnose_candle_csv(csv_path, as_of_date=as_of_date, max_stale_days=max_stale_days)
        for csv_path in sorted(item for item in root.glob("*.csv") if item.is_file())
    ]


def save_data_quality_exclusions(result: DataQualityResult, output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [issue for issue in result.symbol_issues if issue.status == "BLOCK"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "status", "reason"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"symbol": row.symbol, "status": row.status, "reason": row.reason})
    return len(rows)


def save_data_quality_diagnostics(rows: list[CandleCsvDiagnosis], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DIAGNOSTIC_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "symbol": row.symbol,
                "file_path": row.file_path,
                "status": row.status,
                "reason_code": row.reason_code,
                "issue_count": row.issue_count,
                "warning_count": row.warning_count,
                "latest_date": row.latest_date or "",
                "stale_days": "" if row.stale_days is None else row.stale_days,
                "first_issue": row.first_issue,
                "suggested_action": row.suggested_action,
            })
    return len(rows)


def _records_from_input(rows: Any) -> list[dict[str, Any]]:
    if hasattr(rows, "to_dict"):
        return list(rows.to_dict("records"))
    return [dict(row) for row in rows]


def _validate_ohlcv(record: dict[str, Any], index: int, issues: list[str]) -> None:
    try:
        open_price = float(record.get("open", ""))
        high = float(record.get("high", ""))
        low = float(record.get("low", ""))
        close = float(record.get("close", ""))
        volume = float(record.get("volume", ""))
    except (TypeError, ValueError):
        issues.append(f"row {index} non-numeric ohlcv")
        return
    if min(open_price, high, low, close) <= 0:
        issues.append(f"row {index} non-positive price")
    if high < max(open_price, close):
        issues.append(f"row {index} high below open/close")
    if low > min(open_price, close):
        issues.append(f"row {index} low above open/close")
    if volume < 0:
        issues.append(f"row {index} negative volume")


def _diagnose_ohlcv_row(
    record: dict[str, Any],
    index: int,
    issues_by_code: dict[str, list[str]],
    warnings_by_code: dict[str, list[str]],
) -> None:
    raw_close = str(record.get("close", "")).strip()
    if raw_close == "":
        issues_by_code["missing_close"].append(f"row {index} missing close")
    values = {
        name: _optional_float(record.get(name))
        for name in ("open", "high", "low", "close", "volume")
    }
    if any(values[name] is None for name in ("open", "high", "low", "close", "volume")):
        issues_by_code["unknown"].append(f"row {index} non-numeric ohlcv")
        return
    open_price = values["open"]
    high = values["high"]
    low = values["low"]
    close = values["close"]
    volume = values["volume"]
    if open_price is None or high is None or low is None or close is None or volume is None:
        return
    if min(open_price, high, low, close) <= 0:
        issues_by_code["zero_or_negative_price"].append(f"row {index} zero or negative price")
    if high < max(open_price, close):
        issues_by_code["invalid_ohlc"].append(f"row {index} high below open/close")
    if low > min(open_price, close):
        issues_by_code["invalid_ohlc"].append(f"row {index} low above open/close")
    if volume < 0:
        issues_by_code["volume_anomaly"].append(f"row {index} negative volume")
    elif volume == 0:
        warnings_by_code["volume_anomaly"].append(f"row {index} zero volume")


def _diagnose_symbol_mapping(
    path: Path,
    symbol: str,
    warnings_by_code: dict[str, list[str]],
) -> None:
    if not symbol:
        warnings_by_code["symbol_mapping_error_if_detectable"].append("empty symbol from file name")
        return
    if symbol.isdigit() and len(symbol) != 6:
        warnings_by_code["symbol_mapping_error_if_detectable"].append(
            f"numeric symbol is not 6 digits: {path.stem}"
        )


def _diagnosis_from_codes(
    symbol: str,
    csv_path: Path,
    issues_by_code: dict[str, list[str]],
    warnings_by_code: dict[str, list[str]],
    latest_date: str | None,
    stale_days: int | None,
) -> CandleCsvDiagnosis:
    issue_count = sum(len(values) for values in issues_by_code.values())
    warning_count = sum(len(values) for values in warnings_by_code.values())
    reason_code = _primary_reason_code(issues_by_code, warnings_by_code)
    status = "BLOCK" if issue_count else "WARN" if warning_count else "PASS"
    first_issue = _first_reason_message(reason_code, issues_by_code, warnings_by_code)
    return CandleCsvDiagnosis(
        symbol=symbol,
        file_path=str(csv_path),
        status=status,
        reason_code=reason_code,
        issue_count=issue_count,
        warning_count=warning_count,
        latest_date=latest_date,
        stale_days=stale_days,
        first_issue=first_issue,
        suggested_action=_suggested_action(reason_code, status),
    )


def _primary_reason_code(
    issues_by_code: dict[str, list[str]],
    warnings_by_code: dict[str, list[str]],
) -> str:
    for code in REASON_PRIORITY:
        if issues_by_code.get(code):
            return code
    for code in REASON_PRIORITY:
        if warnings_by_code.get(code):
            return code
    return "unknown"


def _first_reason_message(
    reason_code: str,
    issues_by_code: dict[str, list[str]],
    warnings_by_code: dict[str, list[str]],
) -> str:
    if issues_by_code.get(reason_code):
        return issues_by_code[reason_code][0]
    if warnings_by_code.get(reason_code):
        return warnings_by_code[reason_code][0]
    return ""


def _suggested_action(reason_code: str, status: str) -> str:
    if status == "PASS":
        return "REVIEW"
    if reason_code in {"missing_columns", "missing_close", "duplicate_dates"}:
        return "FIXABLE"
    if reason_code == "stale_data":
        return "REFRESH"
    if reason_code in {"zero_or_negative_price", "invalid_ohlc", "symbol_mapping_error_if_detectable"}:
        return "EXCLUDE"
    return "REVIEW"


def _symbol_from_path(path: Path) -> str:
    text = path.stem.split("_", 1)[0].strip()
    if text.isdigit():
        return text.zfill(6)
    return text.upper()


def _optional_float(value: Any) -> float | None:
    text = str(value if value is not None else "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _latest_date(values: Iterable[Any]) -> str | None:
    parsed: list[date] = []
    for value in values:
        try:
            parsed.append(date.fromisoformat(str(value).strip()))
        except ValueError:
            continue
    return max(parsed).isoformat() if parsed else None


def _stale_days(latest: str | None, as_of_date: str | None) -> int | None:
    if latest is None or as_of_date is None:
        return None
    try:
        return max(0, (date.fromisoformat(as_of_date) - date.fromisoformat(latest)).days)
    except ValueError:
        return None


def _status(issues: list[str], warnings: list[str]) -> str:
    if issues:
        return "BLOCK"
    if warnings:
        return "WARN"
    return "PASS"
