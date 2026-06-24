from __future__ import annotations

import re
from datetime import date
from typing import Any


POST_CUTOFF_BASELINE_END_DATE = "2026-06-18"
POST_CUTOFF_OOS_PENDING_MARKER = "PENDING_POST_CUTOFF_OOS"
POST_CUTOFF_OOS_DATE_FIELDS = (
    "post_cutoff_oos_start_date",
    "post_cutoff_oos_end_date",
    "oos_review_start_date",
    "oos_review_end_date",
)


def has_pending_post_cutoff_oos_marker(row: dict[str, Any]) -> bool:
    if POST_CUTOFF_OOS_PENDING_MARKER in {
        str(row.get(field_name, "")).strip().upper()
        for field_name in POST_CUTOFF_OOS_DATE_FIELDS
    }:
        return True
    reasons = str(row.get("decision_reasons", "")).strip().lower()
    return bool(
        re.search(
            r"(?:^|[,;\s])(?:post_cutoff_oos_start_date|post_cutoff_oos_end_date|oos_review_start_date|oos_review_end_date)\s*=\s*pending_post_cutoff_oos(?:[,;\s]|$)",
            reasons,
        )
    )


def candidate_promotion_proof_status(
    row: dict[str, Any],
    *,
    baseline_end_date: str = POST_CUTOFF_BASELINE_END_DATE,
) -> tuple[bool, str]:
    reasons = str(row.get("decision_reasons", "")).strip().lower()
    if "oos_review_passed" not in reasons or "production_readiness_approved" not in reasons:
        return False, "promotion_proof_missing"
    if has_pending_post_cutoff_oos_marker(row):
        return False, "post_cutoff_oos_pending"

    oos_end = _post_cutoff_oos_end_date(row, reasons)
    if not oos_end:
        return False, "post_cutoff_oos_missing"
    try:
        oos_end_date = date.fromisoformat(oos_end)
        baseline_date = date.fromisoformat(baseline_end_date)
    except ValueError:
        return False, "post_cutoff_oos_invalid"
    if oos_end_date <= baseline_date:
        return False, "post_cutoff_oos_missing"
    oos_start = _post_cutoff_oos_start_date(row, reasons)
    if not oos_start:
        return False, "post_cutoff_oos_start_missing"
    try:
        oos_start_date = date.fromisoformat(oos_start)
    except ValueError:
        return False, "post_cutoff_oos_start_invalid"
    if oos_start_date <= baseline_date:
        return False, "post_cutoff_oos_start_not_post_cutoff"
    if oos_start_date > oos_end_date:
        return False, "post_cutoff_oos_date_order_invalid"
    return True, "not_blocked_by_decision"


def _post_cutoff_oos_start_date(row: dict[str, Any], reasons: str) -> str:
    for field_name in ("post_cutoff_oos_start_date", "oos_review_start_date"):
        value = str(row.get(field_name, "")).strip()
        if value:
            return value
    match = re.search(r"(?:^|[,;\s])(?:post_cutoff_oos_start_date|oos_review_start_date)\s*=\s*([^,;\s]+)", reasons)
    return match.group(1) if match else ""


def _post_cutoff_oos_end_date(row: dict[str, Any], reasons: str) -> str:
    for field_name in ("post_cutoff_oos_end_date", "oos_review_end_date"):
        value = str(row.get(field_name, "")).strip()
        if value:
            return value
    match = re.search(r"(?:^|[,;\s])(?:post_cutoff_oos_end_date|oos_review_end_date)\s*=\s*([^,;\s]+)", reasons)
    return match.group(1) if match else ""
