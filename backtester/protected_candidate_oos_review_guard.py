from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


PROTECTED_CANDIDATE_ID = "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244"

GUARD_COLUMNS = [
    "check",
    "status",
    "expected",
    "observed",
    "reason",
    "source",
    "guard_status",
    "review_eligibility",
    "trading_allowed",
    "production_effect",
]

PROMOTION_MARKERS = (
    "accept",
    "accepted",
    "adopt",
    "adopted",
    "approve",
    "approved",
    "promote",
    "promoted",
    "promotion_allowed=true",
)

SAFE_NEGATED_PROMOTION_MARKERS = (
    "not promoted",
    "not adopted",
    "not approved",
    "no promotion",
    "no candidate promotion",
    "promotion_allowed=false",
    "promotion_status=promotion_blocked",
)


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    source = Path(path)
    if not source.exists():
        return [], f"missing source file: {source}"
    try:
        with source.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f)), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return [], f"failed to parse {source}: {exc}"


def _bool_text(value: object) -> str:
    return str(value).strip().lower()


def _int_value(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _has_required_columns(rows: list[dict[str, str]], columns: Iterable[str]) -> tuple[bool, str]:
    if not rows:
        return False, "no rows"
    missing = sorted(column for column in columns if column not in rows[0])
    if missing:
        return False, "missing columns: " + ",".join(missing)
    return True, "present"


def _find_candidate(rows: Iterable[dict[str, str]], candidate_id: str = PROTECTED_CANDIDATE_ID) -> dict[str, str] | None:
    for row in rows:
        if str(row.get("candidate_id", "")).strip() == candidate_id:
            return row
    return None


def _row(check: str, status: str, expected: str, observed: str, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "expected": expected,
        "observed": observed,
        "reason": reason,
        "source": str(source),
        "guard_status": "",
        "review_eligibility": "",
        "trading_allowed": "False",
        "production_effect": "none",
    }


def _contains_promotion_marker(rows: Iterable[dict[str, str]]) -> tuple[bool, str]:
    unsafe_fields = ("status", "recommendation", "reason", "review_assessment", "promotion_allowed")
    observed: list[str] = []
    for row in rows:
        for field in unsafe_fields:
            value = str(row.get(field, "")).strip()
            if not value:
                continue
            lowered = value.lower()
            if any(marker in lowered for marker in SAFE_NEGATED_PROMOTION_MARKERS):
                continue
            if any(marker in lowered for marker in PROMOTION_MARKERS):
                observed.append(f"{row.get('candidate_id', row.get('row_type', 'row'))}:{field}={value}")
    return bool(observed), ";".join(observed)


def build_protected_candidate_oos_review_eligibility_guard(
    *,
    observation_status_csv: Path | str,
    candidate_ledger_csv: Path | str,
    trial_summary_csv: Path | str,
    production_block_csv: Path | str,
    monthly_consistency_audit_csv: Path | str,
) -> list[dict[str, str]]:
    observation_rows, observation_error = _read_csv(observation_status_csv)
    ledger_rows, ledger_error = _read_csv(candidate_ledger_csv)
    trial_rows, trial_error = _read_csv(trial_summary_csv)
    production_rows, production_error = _read_csv(production_block_csv)
    consistency_rows, consistency_error = _read_csv(monthly_consistency_audit_csv)
    source_errors = [
        error
        for error in (observation_error, ledger_error, trial_error, production_error, consistency_error)
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

    observation_columns_ok, observation_columns_observed = _has_required_columns(
        observation_rows,
        [
            "candidate_id",
            "observed_trading_days_after_plan",
            "required_additional_trading_days",
            "remaining_trading_days",
            "review_allowed",
            "status",
        ],
    )
    ledger_columns_ok, ledger_columns_observed = _has_required_columns(
        ledger_rows,
        ["candidate_id", "status", "protected_from_tuning"],
    )
    trial_columns_ok, trial_columns_observed = _has_required_columns(
        trial_rows,
        ["row_type", "candidate_id", "status", "promotion_allowed", "promoted_count"],
    )
    production_columns_ok, production_columns_observed = _has_required_columns(
        production_rows,
        ["check_scope", "block_name", "block_status"],
    )
    consistency_columns_ok, consistency_columns_observed = _has_required_columns(
        consistency_rows,
        ["check", "status", "expected", "observed"],
    )
    rows.extend(
        [
            _row(
                "observation_required_fields",
                "PASS" if observation_columns_ok else "BLOCK",
                "observation eligibility columns present",
                observation_columns_observed,
                "Observation status must expose review gating fields.",
                observation_status_csv,
            ),
            _row(
                "ledger_required_fields",
                "PASS" if ledger_columns_ok else "BLOCK",
                "candidate ledger columns present",
                ledger_columns_observed,
                "Ledger must expose protected candidate status and tuning lock.",
                candidate_ledger_csv,
            ),
            _row(
                "trial_summary_required_fields",
                "PASS" if trial_columns_ok else "BLOCK",
                "trial summary columns present",
                trial_columns_observed,
                "Trial summary must expose promotion counts and status fields.",
                trial_summary_csv,
            ),
            _row(
                "production_block_required_fields",
                "PASS" if production_columns_ok else "BLOCK",
                "production block columns present",
                production_columns_observed,
                "Production block report must expose block status.",
                production_block_csv,
            ),
            _row(
                "monthly_consistency_required_fields",
                "PASS" if consistency_columns_ok else "BLOCK",
                "monthly consistency audit columns present",
                consistency_columns_observed,
                "Consistency audit must expose PASS/BLOCK status fields.",
                monthly_consistency_audit_csv,
            ),
        ]
    )

    observation = _find_candidate(observation_rows)
    ledger = _find_candidate(ledger_rows)
    trial_candidate = _find_candidate(trial_rows)
    observed_days = _int_value(observation.get("observed_trading_days_after_plan")) if observation else None
    required_days = _int_value(observation.get("required_additional_trading_days")) if observation else None
    remaining_days = _int_value(observation.get("remaining_trading_days")) if observation else None
    review_allowed = observation.get("review_allowed") if observation else "missing"
    promoted_summary = next((row for row in trial_rows if row.get("row_type") == "trial_count_summary"), {})
    promoted_count = _int_value(promoted_summary.get("promoted_count", ""))
    consistency_by_check = {row.get("check", ""): row for row in consistency_rows}
    production_block_count = sum(1 for row in production_rows if str(row.get("block_status", "")).strip() == "BLOCK")
    promotion_marker_found, promotion_marker_observed = _contains_promotion_marker([*ledger_rows, *trial_rows])

    rows.extend(
        [
            _row(
                "protected_candidate_paper_review",
                "PASS" if ledger and ledger.get("status") == "PAPER_REVIEW" and trial_candidate and trial_candidate.get("status") == "PAPER_REVIEW" else "BLOCK",
                "protected candidate status PAPER_REVIEW",
                f"ledger={ledger.get('status') if ledger else 'missing'}; trial={trial_candidate.get('status') if trial_candidate else 'missing'}",
                "Protected candidate must remain PAPER_REVIEW.",
                candidate_ledger_csv,
            ),
            _row(
                "protected_from_tuning",
                "PASS" if ledger and _bool_text(ledger.get("protected_from_tuning")) == "true" else "BLOCK",
                "protected_from_tuning=True",
                f"protected_from_tuning={ledger.get('protected_from_tuning') if ledger else 'missing'}",
                "Protected candidate must remain locked from tuning.",
                candidate_ledger_csv,
            ),
            _row(
                "oos_review_not_allowed",
                "PASS" if observation and _bool_text(review_allowed) == "false" else "BLOCK",
                "review_allowed=False",
                f"review_allowed={review_allowed}",
                "OOS review eligibility must remain closed.",
                observation_status_csv,
            ),
            _row(
                "observed_days_below_required",
                "PASS" if observed_days is not None and required_days is not None and observed_days < required_days else "BLOCK",
                "observed trading days < required trading days",
                f"observed={observed_days}; required={required_days}",
                "Review remains unavailable until enough paper OOS days accrue.",
                observation_status_csv,
            ),
            _row(
                "remaining_days_positive",
                "PASS" if remaining_days is not None and remaining_days > 0 else "BLOCK",
                "remaining trading days > 0",
                f"remaining={remaining_days}",
                "Positive remaining days keep review eligibility closed.",
                observation_status_csv,
            ),
            _row(
                "no_promoted_candidates",
                "PASS" if promoted_count == 0 else "BLOCK",
                "promoted_count=0",
                f"promoted_count={promoted_count}",
                "No candidate may be promoted, adopted, or approved.",
                trial_summary_csv,
            ),
            _row(
                "no_promotion_markers",
                "PASS" if not promotion_marker_found else "BLOCK",
                "no promoted/adopted/approved markers",
                promotion_marker_observed if promotion_marker_found else "none",
                "Promotion-like markers are fail-closed.",
                trial_summary_csv,
            ),
            _row(
                "production_blocks_retained",
                "PASS" if production_block_count > 0 else "BLOCK",
                "production/readiness/risk BLOCK retained",
                f"block_rows={production_block_count}",
                "Production readiness and risk BLOCK must remain hard stops.",
                production_block_csv,
            ),
            _row(
                "monthly_consistency_pass_not_authorization",
                "PASS" if consistency_rows and all(row.get("status") == "PASS" for row in consistency_rows) else "BLOCK",
                "monthly consistency audit PASS but not authorization",
                f"rows={len(consistency_rows)}; non_pass={sum(1 for row in consistency_rows if row.get('status') != 'PASS')}",
                "PASS consistency only confirms review-only consistency.",
                monthly_consistency_audit_csv,
            ),
            _row(
                "trading_allowed_false",
                "PASS" if consistency_by_check.get("trading_allowed_false", {}).get("status") == "PASS" else "BLOCK",
                "trading_allowed=False",
                consistency_by_check.get("trading_allowed_false", {}).get("observed", "missing"),
                "Guard must never authorize trading.",
                monthly_consistency_audit_csv,
            ),
            _row(
                "production_effect_none",
                "PASS" if consistency_by_check.get("production_effect_none", {}).get("status") == "PASS" else "BLOCK",
                "production_effect=none",
                consistency_by_check.get("production_effect_none", {}).get("observed", "missing"),
                "Guard must have no production effect.",
                monthly_consistency_audit_csv,
            ),
        ]
    )
    guard_status = "BLOCK" if any(row["status"] == "BLOCK" for row in rows) else "PASS"
    review_eligibility = "REVIEW_NOT_ALLOWED" if guard_status == "PASS" else "BLOCKED_FAIL_CLOSED"
    summary = _row(
        "summary",
        guard_status,
        "guard_status=PASS;review_eligibility=REVIEW_NOT_ALLOWED;trading_allowed=False;production_effect=none",
        f"guard_status={guard_status};review_eligibility={review_eligibility};trading_allowed=False;production_effect=none",
        "Overall protected candidate OOS review eligibility guard.",
        "derived",
    )
    summary["guard_status"] = guard_status
    summary["review_eligibility"] = review_eligibility
    rows.insert(0, summary)
    for row in rows[1:]:
        row["guard_status"] = guard_status
        row["review_eligibility"] = review_eligibility
    return rows


def save_protected_candidate_oos_review_eligibility_guard(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GUARD_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    block_count = sum(1 for row in rows if row.get("status") == "BLOCK")
    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    lines = [
        "# Protected Candidate OOS Review Eligibility Guard",
        "",
        "## Do Not Trade / Review Not Allowed",
        "",
        "This report is review-only and does not authorize trading, broker submission, order execution, candidate promotion, or production readiness change.",
        "",
        f"- Guard status: `{summary.get('guard_status', 'BLOCK')}`.",
        f"- Review eligibility: `{summary.get('review_eligibility', 'BLOCKED_FAIL_CLOSED')}`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "- Protected candidate remains `PAPER_REVIEW` unless this report explicitly BLOCKs fail-closed.",
        "",
        "## Summary",
        "",
        f"- PASS rows: `{pass_count}`.",
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
