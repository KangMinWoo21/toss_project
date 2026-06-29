from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


REQUIRED_BLOCKED_SYMBOLS = ("000270", "016360", "028050", "088350", "161390")

AUDIT_COLUMNS = [
    "check",
    "status",
    "expected",
    "observed",
    "reason",
    "source",
]


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    source = Path(path)
    if not source.exists():
        return [], f"missing source file: {source}"
    try:
        with source.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f)), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return [], f"failed to parse {source}: {exc}"


def _read_text(path: Path | str) -> tuple[str, str | None]:
    source = Path(path)
    if not source.exists():
        return "", f"missing source file: {source}"
    try:
        return source.read_text(encoding="utf-8-sig"), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return "", f"failed to read {source}: {exc}"


def _row(check: str, status: str, expected: str, observed: str, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "expected": expected,
        "observed": observed,
        "reason": reason,
        "source": str(source),
    }


def _bool_text(value: object) -> str:
    return str(value).strip().lower()


def _all_false(rows: Iterable[dict[str, str]], field: str) -> bool:
    return all(_bool_text(row.get(field, "")) == "false" for row in rows)


def _key_value_blob(rows: Iterable[dict[str, str]]) -> str:
    return ";".join(str(row.get("key_value", "")) for row in rows)


def _key_values(rows: Iterable[dict[str, str]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in rows:
        for part in str(row.get("key_value", "")).split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _has_required_columns(rows: list[dict[str, str]], columns: Iterable[str]) -> tuple[bool, str]:
    if not rows:
        return False, "no rows"
    missing = sorted(column for column in columns if column not in rows[0])
    if missing:
        return False, "missing columns: " + ",".join(missing)
    return True, "present"


def build_monthly_paper_operation_consistency_audit(
    *,
    review_packet_csv: Path | str,
    markdown_blocked_audit_csv: Path | str,
    order_plan_csv: Path | str,
    review_packet_md: Path | str,
    markdown_blocked_audit_md: Path | str,
    blocked_summary_md: Path | str,
    order_plan_md: Path | str,
) -> list[dict[str, str]]:
    packet_rows, packet_error = _read_csv(review_packet_csv)
    markdown_audit_rows, markdown_audit_error = _read_csv(markdown_blocked_audit_csv)
    order_rows, order_error = _read_csv(order_plan_csv)
    packet_text, packet_md_error = _read_text(review_packet_md)
    markdown_audit_text, markdown_audit_md_error = _read_text(markdown_blocked_audit_md)
    blocked_summary_text, blocked_summary_error = _read_text(blocked_summary_md)
    order_plan_text, order_plan_md_error = _read_text(order_plan_md)

    source_errors = [
        error
        for error in (
            packet_error,
            markdown_audit_error,
            order_error,
            packet_md_error,
            markdown_audit_md_error,
            blocked_summary_error,
            order_plan_md_error,
        )
        if error
    ]
    rows: list[dict[str, str]] = [
        _row(
            "source_files_present",
            "BLOCK" if source_errors else "PASS",
            "all source files readable",
            "; ".join(source_errors) if source_errors else "all source files readable",
            "Fail closed when any source file is missing or unreadable.",
            "multiple",
        )
    ]

    packet_columns_ok, packet_columns_observed = _has_required_columns(
        packet_rows,
        ["section", "status", "key_value", "manual_action_required", "trading_allowed"],
    )
    order_columns_ok, order_columns_observed = _has_required_columns(
        order_rows,
        ["symbol", "execution_allowed", "execution_mode", "risk_status", "risk_reasons"],
    )
    markdown_audit_columns_ok, markdown_audit_columns_observed = _has_required_columns(
        markdown_audit_rows,
        [
            "csv_order_rows",
            "markdown_blocked_rows_visible",
            "all_blocked_rows_explained",
            "missing_blocked_row_count",
            "risk_status_visible",
        ],
    )
    rows.extend(
        [
            _row(
                "review_packet_required_fields",
                "PASS" if packet_columns_ok else "BLOCK",
                "required review packet columns present",
                packet_columns_observed,
                "Review packet must expose safety fields.",
                review_packet_csv,
            ),
            _row(
                "order_plan_required_fields",
                "PASS" if order_columns_ok else "BLOCK",
                "required order-plan columns present",
                order_columns_observed,
                "Order plan must expose execution and risk fields.",
                order_plan_csv,
            ),
            _row(
                "markdown_audit_required_fields",
                "PASS" if markdown_audit_columns_ok else "BLOCK",
                "required Markdown audit columns present",
                markdown_audit_columns_observed,
                "Blocked-row audit must expose row coverage fields.",
                markdown_blocked_audit_csv,
            ),
        ]
    )

    packet_blob = _key_value_blob(packet_rows)
    packet_values = _key_values(packet_rows)
    packet_statuses = {str(row.get("section", "")): str(row.get("status", "")) for row in packet_rows}
    packet_manual_flags = [str(row.get("manual_action_required", "")) for row in packet_rows]
    order_symbols = {str(row.get("symbol", "")).strip() for row in order_rows}
    combined_markdown = "\n".join([packet_text, markdown_audit_text, blocked_summary_text, order_plan_text])

    rows.extend(
        [
            _row(
                "trading_allowed_false",
                "PASS" if packet_rows and _all_false(packet_rows, "trading_allowed") and "trading_allowed=True" not in packet_blob else "BLOCK",
                "trading_allowed=False for every packet row",
                f"rows={len(packet_rows)}; true_present={not _all_false(packet_rows, 'trading_allowed') or 'trading_allowed=True' in packet_blob}",
                "Any trading_allowed=True signal is a hard stop.",
                review_packet_csv,
            ),
            _row(
                "actionable_rows_zero",
                "PASS" if packet_values.get("actionable_rows") == "0" else "BLOCK",
                "actionable_rows=0",
                f"actionable_rows={packet_values.get('actionable_rows', 'missing')}",
                "Monthly paper operation must remain zero-actionable.",
                review_packet_csv,
            ),
            _row(
                "broker_submission_forbidden",
                "PASS"
                if packet_values.get("broker_submission") == "forbidden"
                or "broker submission: forbidden" in blocked_summary_text.lower()
                else "BLOCK",
                "broker_submission=forbidden",
                f"broker_submission={packet_values.get('broker_submission', 'summary_text')}",
                "Audit must not authorize broker submission.",
                review_packet_csv,
            ),
            _row(
                "manual_review_required",
                "PASS" if packet_manual_flags and all(_bool_text(flag) == "true" for flag in packet_manual_flags) else "BLOCK",
                "manual_review_required=True",
                ";".join(packet_manual_flags),
                "Every packet row must require manual review.",
                review_packet_csv,
            ),
            _row(
                "production_status_block",
                "PASS" if packet_statuses.get("production_readiness") == "BLOCK" and "Production readiness remains `BLOCK`" in packet_text else "BLOCK",
                "production_status=BLOCK",
                f"status={packet_statuses.get('production_readiness', '')}",
                "Production BLOCK must remain visible.",
                review_packet_csv,
            ),
            _row(
                "production_effect_none",
                "PASS" if packet_values.get("production_effect") == "none" and "Production effect: `none`" in packet_text else "BLOCK",
                "production_effect=none",
                f"production_effect={packet_values.get('production_effect', 'missing')}",
                "Report-only audit must have no production effect.",
                review_packet_csv,
            ),
            _row(
                "protected_candidate_paper_review",
                "PASS" if packet_statuses.get("protected_candidate") == "PAPER_REVIEW" and "PAPER_REVIEW" in packet_text else "BLOCK",
                "protected candidate status PAPER_REVIEW",
                f"status={packet_statuses.get('protected_candidate', '')}",
                "Protected candidate must remain paper review only.",
                review_packet_csv,
            ),
            _row(
                "oos_review_not_allowed",
                "PASS" if packet_values.get("review_allowed") == "False" and "review_allowed=False" in packet_text else "BLOCK",
                "OOS review_allowed=False",
                f"review_allowed={packet_values.get('review_allowed', 'missing')}",
                "OOS observation review must not be allowed yet.",
                review_packet_csv,
            ),
            _row(
                "all_order_rows_blocked",
                "PASS" if order_rows and all(str(row.get("risk_status", "")) == "BLOCKED" for row in order_rows) else "BLOCK",
                "all order-plan rows risk_status=BLOCKED",
                f"rows={len(order_rows)}; blocked={sum(1 for row in order_rows if str(row.get('risk_status', '')) == 'BLOCKED')}",
                "Every order-plan row must remain blocked.",
                order_plan_csv,
            ),
            _row(
                "no_execution_allowed_true",
                "PASS" if order_rows and all(_bool_text(row.get("execution_allowed", "")) == "false" for row in order_rows) else "BLOCK",
                "no execution_allowed=True",
                ";".join(f"{row.get('symbol')}={row.get('execution_allowed')}" for row in order_rows),
                "Any execution_allowed=True value is a hard stop.",
                order_plan_csv,
            ),
            _row(
                "execution_mode_blocked_only",
                "PASS" if order_rows and all(str(row.get("execution_mode", "")).strip().lower() == "blocked" for row in order_rows) else "BLOCK",
                "execution_mode=blocked for every row",
                ";".join(f"{row.get('symbol')}={row.get('execution_mode')}" for row in order_rows),
                "Any executable mode is a hard stop.",
                order_plan_csv,
            ),
            _row(
                "blocked_rows_visible",
                "PASS"
                if len(order_rows) == 5
                and all(symbol in blocked_summary_text for symbol in REQUIRED_BLOCKED_SYMBOLS)
                and all(symbol in markdown_audit_text for symbol in REQUIRED_BLOCKED_SYMBOLS)
                and all(symbol in order_plan_text for symbol in REQUIRED_BLOCKED_SYMBOLS)
                else "BLOCK",
                "five blocked rows visible in Markdown and summary",
                f"csv_rows={len(order_rows)}; symbols={','.join(sorted(order_symbols))}",
                "Markdown summaries must show every blocked review row.",
                blocked_summary_md,
            ),
            _row(
                "required_symbols_present",
                "PASS" if set(REQUIRED_BLOCKED_SYMBOLS).issubset(order_symbols) else "BLOCK",
                ",".join(REQUIRED_BLOCKED_SYMBOLS),
                ",".join(sorted(order_symbols)),
                "Required blocked-review symbols must all be present.",
                order_plan_csv,
            ),
            _row(
                "hard_stop_reason_risk_status_block",
                "PASS"
                if order_rows
                and all("risk_status_BLOCK" in str(row.get("risk_reasons", "")) for row in order_rows)
                and "risk_status_BLOCK" in combined_markdown
                else "BLOCK",
                "risk_status_BLOCK visible in CSV and Markdown",
                ";".join(f"{row.get('symbol')}={row.get('risk_reasons')}" for row in order_rows),
                "Hard-stop reason must remain explicit.",
                order_plan_csv,
            ),
            _row(
                "markdown_audit_row_coverage",
                "PASS"
                if markdown_audit_rows
                and str(markdown_audit_rows[0].get("csv_blocked_rows", "")) == "5"
                and str(markdown_audit_rows[0].get("markdown_blocked_rows_visible", "")) == "5"
                and _bool_text(markdown_audit_rows[0].get("all_blocked_rows_explained", "")) == "true"
                and str(markdown_audit_rows[0].get("missing_blocked_row_count", "")) == "0"
                and _bool_text(markdown_audit_rows[0].get("risk_status_visible", "")) == "true"
                else "BLOCK",
                "blocked-row audit confirms 5/5 rows and risk_status_BLOCK",
                str(markdown_audit_rows[0]) if markdown_audit_rows else "no rows",
                "Existing blocked-row audit must agree with source Markdown.",
                markdown_blocked_audit_csv,
            ),
            _row(
                "do_not_trade_banner",
                "PASS",
                "Markdown output starts with Do Not Trade / Review Only",
                "enforced by save_monthly_paper_operation_consistency_audit",
                "Generated audit is not trading authorization.",
                "generated_markdown",
            ),
        ]
    )
    return rows


def save_monthly_paper_operation_consistency_audit(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    block_count = sum(1 for row in rows if row.get("status") == "BLOCK")
    warn_count = sum(1 for row in rows if row.get("status") == "WARN")
    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    overall = "BLOCK" if block_count else "WARN" if warn_count else "PASS"
    lines = [
        "# Monthly Paper Operation Consistency Audit",
        "",
        "## Do Not Trade / Review Only",
        "",
        "This report is review-only. It does not authorize trading, broker submission, or order execution.",
        "",
        "- Production BLOCK is retained.",
        "- Protected candidate remains `PAPER_REVIEW`.",
        "- OOS observation remains `review_allowed=False`.",
        "- The actionable row count remains `0`.",
        "- Broker submission remains forbidden.",
        "",
        "## Summary",
        "",
        f"- Overall status: `{overall}`.",
        f"- PASS rows: `{pass_count}`.",
        f"- WARN rows: `{warn_count}`.",
        f"- BLOCK rows: `{block_count}`.",
        "",
        "## Checks",
        "",
        "| Check | Status | Expected | Observed | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {check} | {status} | {expected} | {observed} | {source} |".format(
                check=row.get("check", ""),
                status=row.get("status", ""),
                expected=str(row.get("expected", "")).replace("|", "/"),
                observed=str(row.get("observed", "")).replace("|", "/"),
                source=row.get("source", ""),
            )
        )
    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
