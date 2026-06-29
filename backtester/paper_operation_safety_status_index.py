from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


INDEX_COLUMNS = [
    "check",
    "status",
    "expected",
    "observed",
    "reason",
    "source",
    "overall_status",
    "trading_allowed",
    "review_allowed",
    "production_effect",
    "recommended_action",
]

RECOMMENDED_ACTION = "keep_observing_no_tuning_no_promotion"


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    source = Path(path)
    if not source.exists():
        return [], f"missing source file: {source}"
    try:
        with source.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f)), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return [], f"failed to parse {source}: {exc}"


def _has_required_columns(rows: list[dict[str, str]], columns: Iterable[str]) -> tuple[bool, str]:
    if not rows:
        return False, "no rows"
    missing = sorted(column for column in columns if column not in rows[0])
    if missing:
        return False, "missing columns: " + ",".join(missing)
    return True, "present"


def _bool_text(value: object) -> str:
    return str(value).strip().lower()


def _int_value(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _key_values(rows: Iterable[dict[str, str]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in rows:
        for part in str(row.get("key_value", "")).split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _row(check: str, status: str, expected: str, observed: str, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "expected": expected,
        "observed": observed,
        "reason": reason,
        "source": str(source),
        "overall_status": "",
        "trading_allowed": "False",
        "review_allowed": "False",
        "production_effect": "none",
        "recommended_action": RECOMMENDED_ACTION,
    }


def _status_by_check(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("check", "")): row for row in rows}


def _section_rows(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("section", "")): row for row in rows}


def build_paper_operation_safety_status_index(
    *,
    production_block_csv: Path | str,
    oos_review_guard_csv: Path | str,
    monthly_consistency_audit_csv: Path | str,
    order_plan_csv: Path | str,
    review_packet_csv: Path | str,
    trial_summary_csv: Path | str,
    health_warn_csv: Path | str,
) -> list[dict[str, str]]:
    production_rows, production_error = _read_csv(production_block_csv)
    guard_rows, guard_error = _read_csv(oos_review_guard_csv)
    consistency_rows, consistency_error = _read_csv(monthly_consistency_audit_csv)
    order_rows, order_error = _read_csv(order_plan_csv)
    packet_rows, packet_error = _read_csv(review_packet_csv)
    trial_rows, trial_error = _read_csv(trial_summary_csv)
    health_rows, health_error = _read_csv(health_warn_csv)
    source_errors = [
        error
        for error in (
            production_error,
            guard_error,
            consistency_error,
            order_error,
            packet_error,
            trial_error,
            health_error,
        )
        if error
    ]

    rows: list[dict[str, str]] = [
        _row(
            "source_files_present",
            "BLOCK" if source_errors else "PASS",
            "all source files readable",
            "; ".join(source_errors) if source_errors else "all source files readable",
            "Fail closed when any source is missing or unreadable.",
            "multiple",
        )
    ]

    production_ok, production_observed = _has_required_columns(production_rows, ["check_scope", "block_name", "block_status"])
    guard_ok, guard_observed = _has_required_columns(
        guard_rows,
        ["check", "status", "guard_status", "review_eligibility", "trading_allowed", "production_effect"],
    )
    consistency_ok, consistency_observed = _has_required_columns(consistency_rows, ["check", "status", "observed"])
    order_ok, order_observed = _has_required_columns(order_rows, ["execution_allowed", "execution_mode", "risk_status"])
    packet_ok, packet_observed = _has_required_columns(packet_rows, ["section", "status", "key_value", "trading_allowed"])
    trial_ok, trial_observed = _has_required_columns(trial_rows, ["row_type", "promoted_count"])
    health_ok, health_observed = _has_required_columns(
        health_rows,
        ["warn_name", "current_status", "affects_monthly_rebalance", "affects_protected_candidate_oos", "affects_scalper_only"],
    )
    rows.extend(
        [
            _row("production_required_fields", "PASS" if production_ok else "BLOCK", "production block columns present", production_observed, "Production report must expose BLOCK status.", production_block_csv),
            _row("oos_guard_required_fields", "PASS" if guard_ok else "BLOCK", "OOS guard columns present", guard_observed, "OOS guard must expose eligibility and safety fields.", oos_review_guard_csv),
            _row("monthly_consistency_required_fields", "PASS" if consistency_ok else "BLOCK", "monthly consistency columns present", consistency_observed, "Consistency audit must expose status fields.", monthly_consistency_audit_csv),
            _row("order_plan_required_fields", "PASS" if order_ok else "BLOCK", "order plan columns present", order_observed, "Order plan must expose execution and risk fields.", order_plan_csv),
            _row("review_packet_required_fields", "PASS" if packet_ok else "BLOCK", "review packet columns present", packet_observed, "Review packet must expose safety fields.", review_packet_csv),
            _row("trial_summary_required_fields", "PASS" if trial_ok else "BLOCK", "trial summary columns present", trial_observed, "Trial summary must expose promoted count.", trial_summary_csv),
            _row("health_warn_required_fields", "PASS" if health_ok else "BLOCK", "health warning columns present", health_observed, "Health warning classification must expose scope fields.", health_warn_csv),
        ]
    )

    guard_summary = guard_rows[0] if guard_rows else {}
    consistency_by_check = _status_by_check(consistency_rows)
    packet_by_section = _section_rows(packet_rows)
    packet_values = _key_values(packet_rows)
    production_block_count = sum(1 for row in production_rows if str(row.get("block_status", "")).strip() == "BLOCK")
    trial_summary = next((row for row in trial_rows if row.get("row_type") == "trial_count_summary"), {})
    promoted_count = _int_value(trial_summary.get("promoted_count", ""))
    if promoted_count is None:
        promoted_count = _int_value(packet_values.get("promoted", ""))
    observed_days = _int_value(packet_values.get("observed_days", ""))
    required_days = _int_value(packet_values.get("required_days", ""))
    remaining_days = _int_value(packet_values.get("remaining_days", ""))
    health_scalper = next((row for row in health_rows if row.get("warn_name") == "scalper_data"), {})

    rows.extend(
        [
            _row(
                "production_block_retained",
                "PASS" if production_block_count > 0 and packet_by_section.get("production_readiness", {}).get("status") == "BLOCK" else "BLOCK",
                "production remains BLOCK",
                f"block_rows={production_block_count}; packet_status={packet_by_section.get('production_readiness', {}).get('status', 'missing')}",
                "Production/readiness/risk BLOCK must remain active.",
                production_block_csv,
            ),
            _row(
                "protected_candidate_paper_review",
                "PASS" if packet_by_section.get("protected_candidate", {}).get("status") == "PAPER_REVIEW" else "BLOCK",
                "protected candidate PAPER_REVIEW",
                packet_by_section.get("protected_candidate", {}).get("status", "missing"),
                "Protected candidate must remain paper review only.",
                review_packet_csv,
            ),
            _row(
                "oos_review_eligibility_not_allowed",
                "PASS" if guard_summary.get("review_eligibility") == "REVIEW_NOT_ALLOWED" and guard_summary.get("guard_status") == "PASS" else "BLOCK",
                "review_eligibility=REVIEW_NOT_ALLOWED",
                f"guard_status={guard_summary.get('guard_status', 'missing')}; review_eligibility={guard_summary.get('review_eligibility', 'missing')}",
                "OOS review eligibility must remain closed.",
                oos_review_guard_csv,
            ),
            _row(
                "oos_review_allowed_false",
                "PASS" if packet_values.get("review_allowed") == "False" and guard_summary.get("review_eligibility") == "REVIEW_NOT_ALLOWED" else "BLOCK",
                "review_allowed=False",
                f"packet={packet_values.get('review_allowed', 'missing')}; guard={guard_summary.get('review_eligibility', 'missing')}",
                "OOS review must not be allowed even while production is blocked.",
                review_packet_csv,
            ),
            _row(
                "observed_days_below_required",
                "PASS" if observed_days is not None and required_days is not None and observed_days < required_days else "BLOCK",
                "observed days < required days",
                f"observed={observed_days}; required={required_days}",
                "Observation window remains incomplete.",
                review_packet_csv,
            ),
            _row(
                "remaining_days_positive",
                "PASS" if remaining_days is not None and remaining_days > 0 else "BLOCK",
                "remaining days > 0",
                f"remaining={remaining_days}",
                "Review remains unavailable while remaining days are positive.",
                review_packet_csv,
            ),
            _row(
                "monthly_consistency_pass_not_authorization",
                "PASS" if consistency_rows and all(row.get("status") == "PASS" for row in consistency_rows) else "BLOCK",
                "monthly consistency audit PASS but not authorization",
                f"rows={len(consistency_rows)}; non_pass={sum(1 for row in consistency_rows if row.get('status') != 'PASS')}",
                "PASS confirms review-only consistency, not trading authorization.",
                monthly_consistency_audit_csv,
            ),
            _row(
                "actionable_rows_zero",
                "PASS" if packet_values.get("actionable_rows") == "0" and consistency_by_check.get("actionable_rows_zero", {}).get("status") == "PASS" else "BLOCK",
                "actionable_rows=0",
                f"packet={packet_values.get('actionable_rows', 'missing')}; consistency={consistency_by_check.get('actionable_rows_zero', {}).get('status', 'missing')}",
                "Monthly order plan must remain non-actionable.",
                review_packet_csv,
            ),
            _row(
                "all_order_rows_blocked",
                "PASS"
                if order_rows
                and all(_bool_text(row.get("execution_allowed", "")) == "false" for row in order_rows)
                and all(str(row.get("execution_mode", "")).strip().lower() == "blocked" for row in order_rows)
                and all(str(row.get("risk_status", "")) == "BLOCKED" for row in order_rows)
                else "BLOCK",
                "all order rows blocked and execution_allowed=False",
                f"rows={len(order_rows)}; blocked={sum(1 for row in order_rows if row.get('risk_status') == 'BLOCKED')}",
                "No order row may be executable.",
                order_plan_csv,
            ),
            _row(
                "promoted_candidates_zero",
                "PASS" if promoted_count == 0 and packet_values.get("promoted") == "0" else "BLOCK",
                "promoted candidates count=0",
                f"trial={promoted_count}; packet={packet_values.get('promoted', 'missing')}",
                "No candidate may be promoted or adopted.",
                trial_summary_csv,
            ),
            _row(
                "trading_allowed_false",
                "PASS"
                if guard_summary.get("trading_allowed") == "False"
                and consistency_by_check.get("trading_allowed_false", {}).get("status") == "PASS"
                and all(_bool_text(row.get("trading_allowed", "")) == "false" for row in packet_rows)
                else "BLOCK",
                "trading_allowed=False",
                f"guard={guard_summary.get('trading_allowed', 'missing')}; packet_true={any(_bool_text(row.get('trading_allowed', '')) == 'true' for row in packet_rows)}",
                "Index must never authorize trading.",
                oos_review_guard_csv,
            ),
            _row(
                "production_effect_none",
                "PASS" if guard_summary.get("production_effect") == "none" and consistency_by_check.get("production_effect_none", {}).get("status") == "PASS" else "BLOCK",
                "production_effect=none",
                f"guard={guard_summary.get('production_effect', 'missing')}; consistency={consistency_by_check.get('production_effect_none', {}).get('status', 'missing')}",
                "Index must have no production effect.",
                oos_review_guard_csv,
            ),
            _row(
                "scalper_warn_separated",
                "PASS"
                if health_scalper.get("current_status") == "WARN"
                and _bool_text(health_scalper.get("affects_monthly_rebalance")) == "false"
                and _bool_text(health_scalper.get("affects_protected_candidate_oos")) == "false"
                and _bool_text(health_scalper.get("affects_scalper_only")) == "true"
                else "BLOCK",
                "scalper stale WARN separated from monthly paper review/OOS",
                str(health_scalper) if health_scalper else "missing",
                "Stale scalper data should be recorded separately from monthly paper review/OOS.",
                health_warn_csv,
            ),
        ]
    )

    overall_status = "BLOCK" if any(row["status"] == "BLOCK" for row in rows) else "OBSERVE"
    summary = _row(
        "summary",
        "PASS" if overall_status == "OBSERVE" else "BLOCK",
        "overall_status=OBSERVE;trading_allowed=False;review_allowed=False;production_effect=none",
        f"overall_status={overall_status};trading_allowed=False;review_allowed=False;production_effect=none",
        "Overall paper-operation safety status index.",
        "derived",
    )
    summary["overall_status"] = overall_status
    rows.insert(0, summary)
    for row in rows[1:]:
        row["overall_status"] = overall_status
    return rows


def save_paper_operation_safety_status_index(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    block_count = sum(1 for row in rows if row.get("status") == "BLOCK")
    lines = [
        "# Paper Operation Safety Status Index",
        "",
        "## Do Not Trade / Status Index Only",
        "",
        "This report is a status index only and does not authorize trading, broker submission, order execution, candidate promotion, or production readiness change.",
        "",
        f"- Overall status: `{summary.get('overall_status', 'BLOCK')}`.",
        "- Trading allowed: `False`.",
        "- Review allowed: `False`.",
        "- Production effect: `none`.",
        f"- Recommended action: `{summary.get('recommended_action', RECOMMENDED_ACTION)}`.",
        "",
        "## Safety Summary",
        "",
        f"- PASS rows: `{pass_count}`.",
        f"- BLOCK rows: `{block_count}`.",
        "- Scalper stale WARN is recorded separately from monthly paper review/OOS when present.",
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
