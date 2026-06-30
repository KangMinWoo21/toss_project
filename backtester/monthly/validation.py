from pathlib import Path
from typing import Any


def candidate_decision_required_for_report_paths(paths: list[str | Path | None]) -> bool:
    for raw_path in paths:
        if raw_path is None:
            continue
        name = Path(str(raw_path)).name.lower()
        if "candidate" in name:
            return True
    return False


def numeric_delta(candidate_value: float | None, baseline_value: float | None) -> float | None:
    if candidate_value is None or baseline_value is None:
        return None
    return candidate_value - baseline_value


def risk_status(checks: list[Any]) -> str:
    statuses = {check.status for check in checks}
    if "BLOCK" in statuses:
        return "BLOCK"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def risk_exit_code(status: str) -> int:
    return 2 if status == "BLOCK" else 0


def scenario_delta_classification(baseline_failed: bool, candidate_failed: bool) -> str:
    if baseline_failed and not candidate_failed:
        return "RESOLVED"
    if not baseline_failed and candidate_failed:
        return "NEW_FAILURE"
    if baseline_failed and candidate_failed:
        return "UNCHANGED_FAILURE"
    return "UNCHANGED_PASS"


def scenario_delta_diagnostic(
    classification: str,
    *,
    baseline_reason: str,
    candidate_reason: str,
    excess_delta: float | None,
    drawdown_delta: float | None,
    trade_delta: float | None,
) -> str:
    if classification == "RESOLVED":
        return "candidate_fixed_required_failure"
    if classification == "NEW_FAILURE":
        if candidate_reason == "max_drawdown_breach":
            if drawdown_delta is not None and drawdown_delta < 0:
                if excess_delta is not None and excess_delta >= 0:
                    return "equity_improved_but_drawdown_buffer_worse"
                return "drawdown_buffer_regression"
            return "candidate_introduced_drawdown_breach"
        if candidate_reason == "train_window_rejected":
            return "train_gate_regression"
        if (
            candidate_reason == "negative_excess_return"
            and excess_delta is not None
            and excess_delta < 0
            and (trade_delta is None or trade_delta <= 0)
            and (drawdown_delta is None or drawdown_delta >= 0)
        ):
            return "over_defense_or_filter_drag"
        if (
            candidate_reason == "negative_excess_return"
            and excess_delta is not None
            and excess_delta < 0
            and trade_delta is not None
            and trade_delta > 0
        ):
            return "selection_or_exposure_drag"
        return "candidate_introduced_failure"
    if classification == "UNCHANGED_FAILURE":
        if candidate_reason == baseline_reason:
            return "same_failure_persists"
        return "failure_shifted_reason"
    return "no_required_failure_change"
