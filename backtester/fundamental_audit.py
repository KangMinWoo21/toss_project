import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NOT_AVAILABLE = "not_available"

FUNDAMENTAL_AUDIT_COLUMNS = [
    "symbol",
    "group",
    "fiscal_period",
    "usable_from",
    "revenue_growth_yoy",
    "operating_profit_growth_yoy",
    "net_income_growth_yoy",
    "operating_margin",
    "debt_ratio",
    "current_ratio",
    "roe",
    "operating_cashflow",
    "capital_impairment_flag",
    "capital_increase_or_cb_flag",
    "earnings_event_risk_status",
    "fundamental_quality_status",
    "explains_ranking_gap",
    "reason",
]

_FUNDAMENTAL_FIELDS = [
    "fiscal_period",
    "usable_from",
    "revenue_growth_yoy",
    "operating_profit_growth_yoy",
    "net_income_growth_yoy",
    "operating_margin",
    "debt_ratio",
    "current_ratio",
    "roe",
    "operating_cashflow",
    "capital_impairment_flag",
    "capital_increase_or_cb_flag",
    "earnings_event_risk_status",
    "fundamental_quality_status",
]

FUNDAMENTAL_SAMPLE_INPUT_COLUMNS = [
    "symbol",
    "group",
    "fiscal_period",
    "report_type",
    "receipt_date",
    "receipt_time",
    "available_date",
    "usable_from",
    "revenue_growth_yoy",
    "operating_profit_growth_yoy",
    "net_income_growth_yoy",
    "operating_margin",
    "debt_ratio",
    "current_ratio",
    "roe",
    "operating_cashflow",
    "free_cashflow_proxy",
    "capital_impairment_flag",
    "capital_increase_or_cb_flag",
    "earnings_event_risk_status",
    "source",
    "source_report_id",
]

_SAMPLE_REQUIRED_FIELDS = ["usable_from", "fiscal_period"]
_SAMPLE_PAYLOAD_FIELDS = [
    field for field in FUNDAMENTAL_SAMPLE_INPUT_COLUMNS if field not in {"symbol", "group"}
]


@dataclass(frozen=True)
class FundamentalSampleValidationIssue:
    row_number: int
    symbol: str
    field: str
    reason: str


@dataclass(frozen=True)
class FundamentalSampleLoadResult:
    valid_rows: list[dict[str, str]]
    issues: list[FundamentalSampleValidationIssue]


def build_regime_sideways_fundamental_audit(
    *,
    missed_recovery_rows: list[dict[str, Any]],
    min_history_rows: list[dict[str, Any]],
    candidate_comparison_rows: list[dict[str, Any]],
    fundamental_rows: list[dict[str, Any]] | None = None,
    local_sample_path: Path | str | None = None,
    as_of: str | None = None,
    sample_validation_issues: list[FundamentalSampleValidationIssue] | None = None,
) -> list[dict[str, str]]:
    usable_fundamental_rows = list(fundamental_rows or [])
    if local_sample_path and Path(local_sample_path).exists():
        sample_result = load_local_fundamental_sample_rows(local_sample_path, as_of=as_of)
        usable_fundamental_rows.extend(sample_result.valid_rows)
        if sample_validation_issues is not None:
            sample_validation_issues.extend(sample_result.issues)

    fundamentals_by_symbol = _latest_fundamental_rows(usable_fundamental_rows)
    rows: list[dict[str, str]] = []

    for symbol in _symbols_from_rows(missed_recovery_rows):
        rows.append(_audit_row(symbol, "missed_252safe_recovery", fundamentals_by_symbol.get(symbol)))

    for symbol in _symbols_from_rows(min_history_rows):
        rows.append(_audit_row(symbol, "min_history244_contribution", fundamentals_by_symbol.get(symbol)))

    existing_primary_symbols = {
        row["symbol"]
        for row in rows
        if row["group"] in {"missed_252safe_recovery", "min_history244_contribution"}
    }
    for symbol in _selected_loser_symbols(candidate_comparison_rows):
        if symbol in existing_primary_symbols:
            continue
        rows.append(_audit_row(symbol, "selected_loser", fundamentals_by_symbol.get(symbol)))

    return rows


def save_regime_sideways_fundamental_audit(rows: list[dict[str, str]], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FUNDAMENTAL_AUDIT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, NOT_AVAILABLE) for column in FUNDAMENTAL_AUDIT_COLUMNS})
    return len(rows)


def save_regime_sideways_fundamental_sample_template(
    audit_rows: list[dict[str, Any]], output_path: Path | str
) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    template_rows = _sample_template_rows(audit_rows)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FUNDAMENTAL_SAMPLE_INPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(template_rows)
    return len(template_rows)


def load_csv_rows(path: Path | str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_local_fundamental_sample_rows(
    path: Path | str, *, as_of: str | None = None
) -> FundamentalSampleLoadResult:
    valid_rows: list[dict[str, str]] = []
    issues: list[FundamentalSampleValidationIssue] = []
    for index, row in enumerate(load_csv_rows(path), start=2):
        normalized = {column: _clean(row.get(column)) for column in FUNDAMENTAL_SAMPLE_INPUT_COLUMNS}
        if not _has_sample_payload(normalized):
            continue
        row_issues = _validate_sample_row(normalized, index, as_of=as_of)
        if row_issues:
            issues.extend(row_issues)
            continue
        normalized["fundamental_quality_status"] = "local_sample_available"
        valid_rows.append(normalized)
    return FundamentalSampleLoadResult(valid_rows=valid_rows, issues=issues)


def _audit_row(symbol: str, group: str, fundamental: dict[str, Any] | None) -> dict[str, str]:
    row = {column: NOT_AVAILABLE for column in FUNDAMENTAL_AUDIT_COLUMNS}
    row["symbol"] = symbol
    row["group"] = group
    if not fundamental:
        row["explains_ranking_gap"] = "insufficient_fundamental_data"
        row["reason"] = "no_local_pit_fundamental_or_earnings_rows"
        return row

    for field in _FUNDAMENTAL_FIELDS:
        row[field] = _clean(fundamental.get(field))
    row["explains_ranking_gap"] = _explanation_for(group, row)
    row["reason"] = "local_fixture_pit_fundamental_row_joined"
    return row


def _explanation_for(group: str, row: dict[str, str]) -> str:
    if row["fundamental_quality_status"] in {"not_available", "", "insufficient_data"}:
        return "insufficient_fundamental_data"
    if group == "missed_252safe_recovery":
        return "fundamental_data_available_review_only"
    return "not_applicable_to_ranking_gap"


def _latest_fundamental_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = _clean(row.get("symbol"))
        if not symbol:
            continue
        current_usable = _clean(row.get("usable_from"))
        previous_usable = _clean(latest.get(symbol, {}).get("usable_from"))
        if symbol not in latest or current_usable >= previous_usable:
            latest[symbol] = row
    return latest


def _sample_template_rows(audit_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for audit_row in audit_rows:
        symbol = _clean(audit_row.get("symbol"))
        group = _clean(audit_row.get("group"))
        if not symbol or not group:
            continue
        key = (symbol, group)
        if key in seen:
            continue
        row = {column: NOT_AVAILABLE for column in FUNDAMENTAL_SAMPLE_INPUT_COLUMNS}
        row["symbol"] = symbol
        row["group"] = group
        rows.append(row)
        seen.add(key)
    return rows


def _validate_sample_row(
    row: dict[str, str], row_number: int, *, as_of: str | None
) -> list[FundamentalSampleValidationIssue]:
    issues: list[FundamentalSampleValidationIssue] = []
    symbol = row.get("symbol", "")
    for field in _SAMPLE_REQUIRED_FIELDS:
        if not _is_available(row.get(field)):
            issues.append(
                FundamentalSampleValidationIssue(row_number, symbol, field, "missing_required_field")
            )
    if not (_is_available(row.get("receipt_date")) or _is_available(row.get("available_date"))):
        issues.append(
            FundamentalSampleValidationIssue(
                row_number, symbol, "receipt_date_or_available_date", "missing_required_field"
            )
        )
    if as_of and _is_available(row.get("usable_from")) and row["usable_from"] > as_of:
        issues.append(FundamentalSampleValidationIssue(row_number, symbol, "usable_from", "row_not_usable_as_of"))
    return issues


def _has_sample_payload(row: dict[str, str]) -> bool:
    return any(_is_available(row.get(field)) for field in _SAMPLE_PAYLOAD_FIELDS)


def _is_available(value: Any) -> bool:
    return _clean(value) not in {"", NOT_AVAILABLE}


def _symbols_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for row in rows:
        symbol = _clean(row.get("symbol"))
        if symbol and symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return symbols


def _selected_loser_symbols(rows: list[dict[str, Any]]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for item in _clean(row.get("top_loss_symbols")).split(";"):
            symbol = item.split(":", 1)[0].strip()
            if not symbol or symbol == NOT_AVAILABLE or symbol in seen:
                continue
            symbols.append(symbol)
            seen.add(symbol)
    return symbols


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return text
