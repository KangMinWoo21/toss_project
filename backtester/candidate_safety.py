from __future__ import annotations

import re
from datetime import date
from typing import Any


POST_CUTOFF_BASELINE_END_DATE = "2026-06-18"


def candidate_promotion_proof_status(
    row: dict[str, Any],
    *,
    baseline_end_date: str = POST_CUTOFF_BASELINE_END_DATE,
) -> tuple[bool, str]:
    reasons = str(row.get("decision_reasons", "")).strip().lower()
    if "oos_review_passed" not in reasons or "production_readiness_approved" not in reasons:
        return False, "promotion_proof_missing"
    if "PENDING_POST_CUTOFF_OOS" in {
        str(row.get("post_cutoff_oos_start_date", "")).strip(),
        str(row.get("post_cutoff_oos_end_date", "")).strip(),
        str(row.get("oos_review_end_date", "")).strip(),
    }:
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
    return True, "not_blocked_by_decision"


def _post_cutoff_oos_end_date(row: dict[str, Any], reasons: str) -> str:
    for field_name in ("post_cutoff_oos_end_date", "oos_review_end_date"):
        value = str(row.get(field_name, "")).strip()
        if value:
            return value
    match = re.search(r"(?:post_cutoff_oos_end_date|oos_review_end_date)=([0-9]{4}-[0-9]{2}-[0-9]{2})", reasons)
    return match.group(1) if match else ""
