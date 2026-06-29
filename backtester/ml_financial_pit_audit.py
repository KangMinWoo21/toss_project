from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

from .dart import DartDisclosureRow


FINANCIAL_OBSERVATION_COLUMNS = [
    "symbol",
    "corp_code",
    "business_year",
    "report_code",
    "fs_div",
    "statement_name",
    "account_name",
    "current_amount",
    "previous_amount",
    "currency",
    "ord",
    "receipt_no",
    "receipt_date",
    "receipt_time",
    "collected_at",
    "usable_from",
    "report_period_end",
    "correction_filing_flag",
    "original_receipt_no",
    "source_revision",
    "quality_status",
    "excluded_reason",
    "training_allowed_now",
    "trading_allowed",
    "production_effect",
]

FINANCIAL_PIT_AUDIT_COLUMNS = [
    "check_name",
    "check_status",
    "evidence",
    "train_cutoff",
    "post_cutoff_data_used_for_train",
    "training_allowed_now",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]


def build_ml_financial_pit_audit_reports(
    financial_rows: list[dict[str, Any]],
    disclosure_rows: list[DartDisclosureRow],
    *,
    collected_at: str,
    train_cutoff: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    observations = _build_observations(financial_rows, disclosure_rows, collected_at)
    audit_rows = _build_audit_rows(observations, disclosure_rows, train_cutoff)
    markdown = _build_markdown(observations, audit_rows)
    return observations, audit_rows, markdown


def save_ml_financial_pit_audit_reports(
    observations: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    readiness_markdown: str,
    sample_output: Path | str,
    audit_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_observations(observations)
    _validate_audit_rows(audit_rows)
    sample_path = Path(sample_output)
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    with sample_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINANCIAL_OBSERVATION_COLUMNS)
        writer.writeheader()
        writer.writerows(observations)

    audit_path = Path(audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINANCIAL_PIT_AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(audit_rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(readiness_markdown, encoding="utf-8")


def _build_observations(
    financial_rows: list[dict[str, Any]],
    disclosure_rows: list[DartDisclosureRow],
    collected_at: str,
) -> list[dict[str, str]]:
    disclosures_by_symbol: dict[str, list[DartDisclosureRow]] = {}
    for disclosure in disclosure_rows:
        disclosures_by_symbol.setdefault(disclosure.symbol, []).append(disclosure)

    observations: list[dict[str, str]] = []
    for index, row in enumerate(financial_rows, start=1):
        symbol = str(row.get("symbol", "")).strip()
        symbol_disclosures = sorted(disclosures_by_symbol.get(symbol, []), key=lambda item: item.date)
        latest_disclosure = symbol_disclosures[-1] if symbol_disclosures else None
        original_disclosure = next((item for item in symbol_disclosures if not _is_correction(item.report_name)), None)
        correction_seen = any(_is_correction(item.report_name) for item in symbol_disclosures)
        receipt_date = latest_disclosure.date if latest_disclosure else ""
        usable_from = _conservative_usable_from(receipt_date, collected_at)
        quality_status = "PASS" if receipt_date else "WARN"
        excluded_reason = "" if receipt_date else "missing_receipt_date_using_collected_at"
        observations.append(
            {
                "symbol": symbol,
                "corp_code": str(row.get("corp_code", "")).strip(),
                "business_year": str(row.get("business_year", "")).strip(),
                "report_code": str(row.get("report_code", "")).strip(),
                "fs_div": str(row.get("fs_div", "")).strip(),
                "statement_name": str(row.get("statement_name", "")).strip(),
                "account_name": str(row.get("account_name", "")).strip(),
                "current_amount": str(row.get("current_amount", "")).strip(),
                "previous_amount": str(row.get("previous_amount", "")).strip(),
                "currency": str(row.get("currency", "")).strip(),
                "ord": str(row.get("ord", index)).strip(),
                "receipt_no": latest_disclosure.receipt_no if latest_disclosure else "",
                "receipt_date": receipt_date,
                "receipt_time": "00:00:00" if receipt_date else "",
                "collected_at": collected_at,
                "usable_from": usable_from,
                "report_period_end": _report_period_end(str(row.get("business_year", "")).strip(), str(row.get("report_code", "")).strip()),
                "correction_filing_flag": str(correction_seen),
                "original_receipt_no": original_disclosure.receipt_no if original_disclosure else "",
                "source_revision": f"dart:{symbol}:{row.get('business_year', '')}:{row.get('report_code', '')}",
                "quality_status": quality_status,
                "excluded_reason": excluded_reason,
                "training_allowed_now": "False",
                "trading_allowed": "False",
                "production_effect": "none",
            }
        )
    return observations


def _build_audit_rows(
    observations: list[dict[str, str]],
    disclosure_rows: list[DartDisclosureRow],
    train_cutoff: str,
) -> list[dict[str, str]]:
    usable_from_count = sum(1 for row in observations if row.get("usable_from"))
    post_cutoff_rows = sum(1 for row in observations if row.get("usable_from", "") > train_cutoff)
    correction_disclosures = [row for row in disclosure_rows if _is_correction(row.report_name)]
    correction_observations = [row for row in observations if row["correction_filing_flag"] == "True"]
    correction_has_original = all(row["original_receipt_no"] for row in correction_observations)
    correction_status = "PASS" if not correction_disclosures or correction_has_original else "WARN"
    return [
        _audit_row(
            "usable_from_presence",
            "PASS" if usable_from_count == len(observations) and observations else "BLOCK",
            f"{usable_from_count}/{len(observations)} observations include usable_from",
            train_cutoff,
        ),
        _audit_row(
            "post_cutoff_train_leakage",
            "PASS",
            f"{post_cutoff_rows} observations are post-cutoff, all remain training_allowed_now=False",
            train_cutoff,
        ),
        _audit_row(
            "correction_lineage",
            correction_status,
            f"{len(correction_disclosures)} correction disclosures observed; original receipt linked={correction_has_original}",
            train_cutoff,
        ),
        _audit_row(
            "readiness_status",
            "BLOCK",
            "limited sample is PIT-audited only; training_allowed_now remains False",
            train_cutoff,
        ),
    ]


def _audit_row(check_name: str, check_status: str, evidence: str, train_cutoff: str) -> dict[str, str]:
    return {
        "check_name": check_name,
        "check_status": check_status,
        "evidence": evidence,
        "train_cutoff": train_cutoff,
        "post_cutoff_data_used_for_train": "False",
        "training_allowed_now": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _build_markdown(observations: list[dict[str, str]], audit_rows: list[dict[str, str]]) -> str:
    audit_by_name = {row["check_name"]: row for row in audit_rows}
    lines = [
        "# ML Financial Feature Readiness Report",
        "",
        "## Do Not Trade / PIT Audit Only",
        "",
        "This report records a limited OpenDART sample for paper-only ML feature readiness. It does not train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        "- `training_allowed_now=False`.",
        "- `trading_allowed=False`.",
        "- `production_effect=none`.",
        "- `post_cutoff_data_used_for_train=False`.",
        "- Protected candidate unchanged.",
        "",
        "## PIT Summary",
        "",
        f"- observation_rows={len(observations)}",
        f"- usable_from_check={audit_by_name['usable_from_presence']['check_status']}",
        f"- correction_lineage={audit_by_name['correction_lineage']['check_status']}",
        f"- readiness_status={audit_by_name['readiness_status']['check_status']}",
        "",
        "## Next Safe Action",
        "",
        "Use this sample only for Phase 7 financial feature merge audit. Keep `training_allowed_now=False` until merge coverage, missingness, and leakage checks pass under a separately approved paper-only experiment.",
        "",
    ]
    return "\n".join(lines)


def _validate_observations(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("financial observation sample is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in FINANCIAL_OBSERVATION_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"financial observation row {index} missing columns: {','.join(missing)}")
        for column, expected in (
            ("training_allowed_now", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
        ):
            if row[column] != expected:
                raise ValueError(f"financial observation row {index} {column}={row[column]} expected {expected}")
        if not row["usable_from"]:
            raise ValueError(f"financial observation row {index} missing usable_from")


def _validate_audit_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("financial PIT audit is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in FINANCIAL_PIT_AUDIT_COLUMNS if not row.get(column)]
        if missing:
            raise ValueError(f"financial PIT audit row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("post_cutoff_data_used_for_train", "False"),
            ("training_allowed_now", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("protected_candidate_unchanged", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"financial PIT audit row {index} {column}={row[column]} expected {expected}")


def _is_correction(report_name: str) -> bool:
    normalized = report_name.casefold()
    return "correction" in normalized or "정정" in normalized


def _conservative_usable_from(receipt_date: str, collected_at: str) -> str:
    collected_date = collected_at[:10]
    candidates = [value for value in (receipt_date, collected_date) if value]
    return max(candidates) if candidates else date.today().isoformat()


def _report_period_end(business_year: str, report_code: str) -> str:
    if not business_year:
        return ""
    report_month_day = {
        "11013": "03-31",
        "11012": "06-30",
        "11014": "09-30",
        "11011": "12-31",
    }.get(report_code, "12-31")
    return f"{business_year}-{report_month_day}"
