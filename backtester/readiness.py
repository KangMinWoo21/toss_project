import csv
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .candidate_safety import candidate_promotion_proof_status
from .data_quality import validate_dataset_freshness


READINESS_COLUMNS = ["name", "status", "detail"]
REQUIRED_DEPLOYMENT_GATE_COLUMNS = {
    "deployable",
    "reason",
    "source",
    "total_return_pct",
    "buy_hold_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "trade_count",
    "universe_bias_warning",
}
REQUIRED_VALIDATION_SCENARIO_COLUMNS = {
    "name",
    "category",
    "required",
    "train_start",
    "train_end",
    "selected_preset",
    "train_excess_return_pct",
    "train_candidate_scores",
    "train_candidate_decision_profiles",
    "train_candidate_direct_scores",
    "train_direct_diagnostics",
    "start",
    "end",
    "slippage_multiplier",
    "stress",
    "final_equity",
    "total_return_pct",
    "buy_hold_return_pct",
    "excess_return_pct",
    "max_drawdown_pct",
    "trade_count",
    "universe_bias_warning",
    "universe_bias_reasons",
    "universe_symbol_count",
    "universe_avg_symbol_return_pct",
    "universe_median_symbol_return_pct",
    "universe_extreme_return_symbols",
    "universe_extreme_return_share",
    "deployable",
    "reason",
    "source",
}
REQUIRED_RISK_REPORT_CHECKS = {
    "point_in_time_universe",
    "market_data_freshness",
    "universe_freshness",
    "universe_price_coverage",
}
REQUIRED_PERFORMANCE_REPORT_CHECKS = {
    "required_scenarios",
    "required_excess",
    "walk_forward_margin",
    "drawdown_buffer",
    "return_concentration",
    "trade_activity",
}
REQUIRED_PERFORMANCE_CONCENTRATION_COLUMNS = {
    "source",
    "start",
    "end",
    "top_1_month_contribution",
    "top_3_month_contribution",
    "top_5_symbol_contribution",
    "positive_month_ratio",
    "rolling_3m_return_min",
    "rolling_6m_return_min",
    "max_recovery_months_if_possible",
    "concentration_status",
    "concentration_reasons",
}
REQUIRED_DRAWDOWN_ATTRIBUTION_MONTHLY_COLUMNS = {
    "month",
    "start_date",
    "end_date",
    "equity_change",
    "worst_drawdown_pct",
}
REQUIRED_DRAWDOWN_ATTRIBUTION_SYMBOL_COLUMNS = {
    "symbol",
    "realized_pnl",
    "trade_count",
    "status",
}
REQUIRED_VALIDATION_FAILURE_COLUMNS = {
    "name",
    "category",
    "reason",
    "severity",
    "failed_metric",
    "metric_value",
    "threshold",
    "suggested_action",
    "parameter_hints",
}
REQUIRED_VALIDATION_FAILURE_VALUE_COLUMNS = {
    "name",
    "category",
    "reason",
    "severity",
    "failed_metric",
    "metric_value",
    "suggested_action",
}
REQUIRED_VALIDATION_REMEDIATION_COLUMNS = {
    "priority",
    "suggested_action",
    "failure_count",
    "blocked_count",
    "affected_categories",
    "affected_scenarios",
    "failed_metrics",
    "worst_metric_value",
    "parameter_hints",
    "next_experiment",
}
REQUIRED_VALIDATION_REMEDIATION_VALUE_COLUMNS = {
    "priority",
    "suggested_action",
    "failure_count",
    "blocked_count",
    "affected_categories",
    "affected_scenarios",
    "failed_metrics",
    "worst_metric_value",
    "parameter_hints",
    "next_experiment",
}
REQUIRED_VALIDATION_SWEEP_PLAN_COLUMNS = {
    "priority",
    "suggested_action",
    "experiment_id",
    "target_scenarios",
    "expected_effect",
    "risk_note",
}
REQUIRED_VALIDATION_SWEEP_PLAN_VALUE_COLUMNS = {
    "priority",
    "suggested_action",
    "experiment_id",
    "target_scenarios",
    "expected_effect",
    "risk_note",
}
REQUIRED_VALIDATION_SWEEP_RESULTS_COLUMNS = {
    "experiment_id",
    "suggested_action",
    "status",
    "target_scenarios",
    "scenario_count",
    "failed_required",
    "baseline_failed_required",
    "failed_delta",
    "candidate_validation_args",
    "validation_scope",
    "adoption_status",
    "adoption_requirements",
    "result_summary",
    "risk_note",
}
REQUIRED_VALIDATION_SWEEP_RESULTS_VALUE_COLUMNS = set(REQUIRED_VALIDATION_SWEEP_RESULTS_COLUMNS)
REQUIRED_VALIDATION_COMPARISON_COLUMNS = {
    "baseline_label",
    "candidate_label",
    "status",
    "baseline_failed_required",
    "candidate_failed_required",
    "failed_delta",
    "resolved_failures",
    "new_failures",
    "unchanged_failures",
    "summary",
}
REQUIRED_VALIDATION_COMPARISON_DELTA_COLUMNS = {
    "name",
    "classification",
    "baseline_label",
    "candidate_label",
    "baseline_deployable",
    "candidate_deployable",
    "baseline_reason",
    "candidate_reason",
    "excess_return_delta",
    "max_drawdown_delta",
    "trade_count_delta",
    "diagnostic",
}
REQUIRED_VALIDATION_CANDIDATE_FOLLOWUP_COLUMNS = {
    "priority_rank",
    "experiment_id",
    "status",
    "adoption_status",
    "failed_delta",
    "candidate_validation_args",
    "candidate_scenario_output",
    "candidate_gate_output",
    "comparison_output",
    "delta_output",
    "decision_output",
    "validation_command",
    "comparison_command",
    "risk_note",
}
REQUIRED_VALIDATION_CANDIDATE_DECISION_COLUMNS = {
    "candidate_label",
    "comparison_status",
    "decision",
    "decision_reasons",
    "baseline_failed_required",
    "candidate_failed_required",
    "failed_delta",
    "resolved_count",
    "new_failure_count",
    "unchanged_failure_count",
    "resolved_failure_names",
    "new_failure_names",
    "unchanged_failure_names",
    "new_failure_diagnostics",
    "recommendation",
}
REQUIRED_VALIDATION_FAILURE_PATTERN_COLUMNS = {
    "scenario",
    "baseline_failed",
    "baseline_reason",
    "failed_candidate_count",
    "new_failure_candidate_count",
    "resolved_candidate_count",
    "unchanged_failure_candidate_count",
    "candidate_labels_failed",
    "candidate_labels_new_failure",
    "candidate_labels_resolved",
    "candidate_labels_unchanged",
    "dominant_diagnostic",
    "pattern_status",
    "suggested_action",
    "notes",
}
REQUIRED_VALIDATION_FAILURE_PATTERN_VALUE_COLUMNS = {
    "scenario",
    "baseline_failed",
    "baseline_reason",
    "failed_candidate_count",
    "new_failure_candidate_count",
    "resolved_candidate_count",
    "unchanged_failure_candidate_count",
    "dominant_diagnostic",
    "pattern_status",
    "suggested_action",
    "notes",
}
REQUIRED_VALIDATION_FAILURE_DRILLDOWN_COLUMNS = {
    "scenario",
    "category",
    "pattern_status",
    "suggested_action",
    "baseline_reason",
    "likely_root_cause",
    "train_start",
    "train_end",
    "selected_preset",
    "train_excess_return_pct",
    "train_candidate_scores",
    "train_candidate_decision_profiles",
    "train_candidate_direct_scores",
    "train_direct_diagnostics",
    "start",
    "end",
    "baseline_excess_return_pct",
    "baseline_max_drawdown_pct",
    "baseline_trade_count",
    "candidate_count",
    "candidate_labels",
    "candidate_excess_delta_min",
    "candidate_excess_delta_median",
    "candidate_drawdown_delta_median",
    "candidate_trade_delta_median",
    "dominant_diagnostic",
    "evidence_gaps",
    "next_action",
}


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ReadinessAction:
    priority: str
    action: str
    detail: str


def evaluate_readiness(
    *,
    required_artifacts: list[Path | str] | None = None,
    deployment_gate_path: Path | str | None = None,
    validation_scenarios_path: Path | str | None = None,
    validation_failures_path: Path | str | None = None,
    validation_remediation_path: Path | str | None = None,
    validation_sweep_plan_path: Path | str | None = None,
    validation_sweep_results_path: Path | str | None = None,
    validation_comparison_path: Path | str | None = None,
    validation_comparison_delta_path: Path | str | None = None,
    validation_candidate_decision_path: Path | str | None = None,
    validation_candidate_followup_path: Path | str | None = None,
    validation_failure_patterns_path: Path | str | None = None,
    validation_failure_drilldown_path: Path | str | None = None,
    risk_report_path: Path | str | None = None,
    coverage_report_path: Path | str | None = None,
    missing_ohlcv_targets_path: Path | str | None = None,
    missing_ohlcv_fetch_plan_path: Path | str | None = None,
    missing_ohlcv_fetch_summary_path: Path | str | None = None,
    performance_report_path: Path | str | None = None,
    performance_concentration_path: Path | str | None = None,
    drawdown_attribution_path: Path | str | None = None,
    symbol_attribution_path: Path | str | None = None,
    data_quality_path: Path | str | None = None,
    data_quality_exclusions_path: Path | str | None = None,
    coverage_warning_min_pct: float = 90.0,
    max_data_stale_days: int = 7,
    max_report_age_days: int | None = None,
    as_of_date: str | None = None,
) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    checks.extend(_artifact_checks(required_artifacts or []))
    if deployment_gate_path is not None:
        checks.append(_deployment_gate_check(Path(deployment_gate_path)))
    if validation_scenarios_path is not None:
        validation_path = Path(validation_scenarios_path)
        checks.append(_validation_scenario_check(validation_path))
        checks.append(_walk_forward_train_candidate_coverage_check(validation_path))
    if validation_failures_path is not None:
        checks.append(_validation_failure_actions_check(Path(validation_failures_path)))
    if validation_remediation_path is not None:
        checks.append(_validation_remediation_check(Path(validation_remediation_path)))
    if validation_sweep_plan_path is not None:
        checks.append(_validation_sweep_plan_check(Path(validation_sweep_plan_path)))
    if validation_sweep_results_path is not None:
        checks.append(_validation_sweep_results_check(Path(validation_sweep_results_path)))
    if validation_comparison_path is not None:
        checks.append(_validation_comparison_check(Path(validation_comparison_path)))
    if validation_comparison_delta_path is not None:
        checks.append(_validation_comparison_delta_check(Path(validation_comparison_delta_path)))
    if validation_candidate_decision_path is not None:
        checks.append(_validation_candidate_decision_check(Path(validation_candidate_decision_path)))
    if validation_candidate_followup_path is not None:
        checks.append(_validation_candidate_followup_check(Path(validation_candidate_followup_path)))
    if validation_failure_patterns_path is not None:
        checks.append(_validation_failure_patterns_check(Path(validation_failure_patterns_path)))
    if validation_failure_drilldown_path is not None:
        checks.append(_validation_failure_drilldown_check(Path(validation_failure_drilldown_path)))
    if risk_report_path is not None:
        checks.append(_risk_report_check(Path(risk_report_path)))
    coverage_check: ReadinessCheck | None = None
    if coverage_report_path is not None:
        coverage_check = _coverage_report_check(
            Path(coverage_report_path),
            warning_min_coverage_pct=coverage_warning_min_pct,
        )
        checks.append(coverage_check)
    if missing_ohlcv_targets_path is not None:
        target_check = _missing_ohlcv_targets_check(Path(missing_ohlcv_targets_path), coverage_check)
        if target_check is not None:
            checks.append(target_check)
    if missing_ohlcv_fetch_plan_path is not None:
        fetch_plan_check = _missing_ohlcv_fetch_plan_check(
            Path(missing_ohlcv_fetch_plan_path),
            Path(missing_ohlcv_targets_path) if missing_ohlcv_targets_path is not None else None,
        )
        if fetch_plan_check is not None:
            checks.append(fetch_plan_check)
    if missing_ohlcv_fetch_summary_path is not None:
        fetch_summary_check = _missing_ohlcv_fetch_summary_check(Path(missing_ohlcv_fetch_summary_path))
        if fetch_summary_check is not None:
            checks.append(fetch_summary_check)
    if performance_report_path is not None:
        checks.append(_performance_report_check(Path(performance_report_path)))
    if performance_concentration_path is not None:
        checks.append(_performance_concentration_check(Path(performance_concentration_path)))
    if drawdown_attribution_path is not None or symbol_attribution_path is not None:
        checks.append(
            _drawdown_attribution_check(
                Path(drawdown_attribution_path) if drawdown_attribution_path is not None else None,
                Path(symbol_attribution_path) if symbol_attribution_path is not None else None,
                Path(validation_failures_path) if validation_failures_path is not None else None,
            )
        )
    if data_quality_path is not None:
        checks.append(_data_quality_check(Path(data_quality_path), max_stale_days=max_data_stale_days, as_of_date=as_of_date))
    if data_quality_exclusions_path is not None:
        checks.append(
            _data_quality_exclusions_check(
                Path(data_quality_exclusions_path),
                {
                    "deployment_gate": deployment_gate_path,
                    "validation_scenarios": validation_scenarios_path,
                    "risk_report": risk_report_path,
                },
            )
        )
    if max_report_age_days is not None:
        checks.extend(
            _report_freshness_checks(
                {
                    "deployment_gate": deployment_gate_path,
                    "validation_scenarios": validation_scenarios_path,
                    "validation_failures": validation_failures_path,
                    "validation_remediation": validation_remediation_path,
                    "validation_sweep_plan": validation_sweep_plan_path,
                    "validation_sweep_results": validation_sweep_results_path,
                    "validation_comparison": validation_comparison_path,
                    "validation_comparison_deltas": validation_comparison_delta_path,
                    "validation_candidate_decision": validation_candidate_decision_path,
                    "risk_report": risk_report_path,
                    "universe_price_coverage": coverage_report_path,
                    "krx_missing_ohlcv_targets": missing_ohlcv_targets_path,
                    "krx_missing_ohlcv_fetch_plan": missing_ohlcv_fetch_plan_path,
                    "krx_missing_ohlcv_fetch_summary": missing_ohlcv_fetch_summary_path,
                    "performance_report": performance_report_path,
                    "performance_concentration": performance_concentration_path,
                    "drawdown_attribution": drawdown_attribution_path,
                    "symbol_attribution": symbol_attribution_path,
                },
                max_age_days=max_report_age_days,
                as_of_date=as_of_date,
            )
        )
    if not checks:
        checks.append(ReadinessCheck("overall", "PASS", "no readiness inputs requested"))
    return checks


def readiness_status(checks: list[ReadinessCheck]) -> str:
    statuses = {check.status for check in checks}
    if "BLOCK" in statuses:
        return "BLOCK"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def readiness_exit_code(status: str, *, strict: bool = False) -> int:
    normalized = str(status).strip().upper()
    if normalized == "BLOCK":
        return 2
    if strict and normalized == "WARN":
        return 2
    return 0


def recommend_readiness_actions(checks: list[ReadinessCheck]) -> list[ReadinessAction]:
    actions: list[ReadinessAction] = []
    details = "\n".join(check.detail for check in checks)

    if any(check.name.startswith("artifact:") and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Regenerate missing readiness artifacts",
                "Live execution must not start until all required data, validation, and risk files exist.",
            )
        )

    if any(check.name == "deployment_gate" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Keep live executor disabled",
                "The monthly deployment gate is not deployable; paper review and data collection only.",
            )
        )

    if "universe_bias_warning" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce data bias",
                "Add stronger point-in-time and delisted-symbol coverage before accepting the excess return.",
            )
        )

    if "extreme_return_share" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce extreme-winner dependence",
                "Keep winner-exclusion stress tests required and add broader historical constituents before trusting high-return windows.",
            )
        )

    if any(check.name == "universe_price_coverage" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Expand KRX price coverage",
                "Fetch historical OHLCV for missing point-in-time universe members before trusting deployment validation.",
            )
        )

    if any(check.name == "krx_missing_ohlcv_targets" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Create KRX missing OHLCV target plan",
                "Run plan-pykrx-missing-ohlcv, then fetch the prioritized batches before rerunning monthly validation.",
            )
        )

    if any(check.name == "krx_missing_ohlcv_fetch_plan" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P1",
                "Review KRX missing OHLCV fetch plan",
                "Generate or refresh the fetch-loop plan before running network collection batches.",
            )
        )

    if any(check.name == "krx_missing_ohlcv_fetch_summary" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P1",
                "Inspect KRX missing OHLCV fetch result",
                "Review failed or timed-out collection batches before rerunning validation.",
            )
        )

    if "max_drawdown_breach" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce stress drawdown",
                "Tune exposure caps, stop rules, or risk-off overlays until required stress scenarios pass.",
            )
        )

    if any(check.name == "risk_report" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Keep risk report as an order hard stop",
                "A blocked risk report should prevent order generation even if signals look attractive.",
            )
        )

    if any(check.name == "performance_report" and check.status in {"BLOCK", "WARN"} for check in checks):
        if "walk_forward_margin" in details:
            actions.append(
                ReadinessAction(
                    "P1",
                    "Improve walk-forward margin",
                    "Raise the weakest required-window excess return before increasing size; test stricter entry filters, slower rebalance cadence, or lower exposure in marginal regimes.",
                )
            )
        if "drawdown_buffer" in details:
            actions.append(
                ReadinessAction(
                    "P1",
                    "Reduce drawdown pressure",
                    "Worst drawdown is too close to the hard block threshold; test stronger risk-off overlays, lower max position weight, and faster de-risking after equity-curve drawdowns.",
                )
            )
        if "return_concentration" in details:
            actions.append(
                ReadinessAction(
                    "P1",
                    "Reduce return concentration",
                    "Full-period returns are too dependent on a small set of favorable windows; require broader rolling-window contribution before treating the strategy as robust.",
                )
            )
        actions.append(
            ReadinessAction(
                "P1",
                "Treat performance fragility as a live-size limiter",
                "Thin walk-forward margins, high drawdown pressure, or full-period concentration should keep trading in paper/live dry-run or very small sizing until they improve.",
            )
        )

    if any(check.name == "performance_concentration" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce performance concentration risk",
                "Review whether returns depend on one month or a few symbols before increasing live size.",
            )
        )

    train_candidate_checks = [
        check
        for check in checks
        if check.name == "walk_forward_train_candidate_coverage" and check.status in {"BLOCK", "WARN"}
    ]
    if train_candidate_checks:
        detail = train_candidate_checks[0].detail
        if "direct_alpha_ineligible=" in detail and not "direct_alpha_ineligible=0" in detail:
            actions.append(
                ReadinessAction(
                    "P1",
                    "Diagnose walk-forward train alpha weakness",
                    detail,
                )
            )
        else:
            actions.append(
                ReadinessAction(
                    "P1",
                    "Expand walk-forward train candidates",
                    detail,
                )
            )

    drawdown_attribution_checks = [
        check for check in checks if check.name == "drawdown_attribution" and check.status in {"BLOCK", "WARN"}
    ]
    if drawdown_attribution_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Regenerate drawdown attribution reports",
                "Run monthly-attribution for failed drawdown scenarios so worst months and symbols are visible before tuning risk controls.",
            )
        )

    validation_action_checks = [
        check for check in checks if check.name == "validation_failure_actions" and check.status in {"BLOCK", "WARN"}
    ]
    if validation_action_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Apply validation failure playbook",
                validation_action_checks[0].detail,
            )
        )

    remediation_checks = [
        check for check in checks if check.name == "validation_remediation" and check.status in {"BLOCK", "WARN"}
    ]
    if remediation_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Run validation remediation experiments",
                remediation_checks[0].detail,
            )
        )

    sweep_plan_checks = [
        check for check in checks if check.name == "validation_sweep_plan" and check.status in {"BLOCK", "WARN"}
    ]
    if sweep_plan_checks:
        actions.append(
            ReadinessAction(
                "P2",
                "Review validation sweep plan",
                sweep_plan_checks[0].detail,
            )
        )

    sweep_result_checks = [
        check for check in checks if check.name == "validation_sweep_results" and check.status in {"BLOCK", "WARN"}
    ]
    if sweep_result_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Review validation sweep results",
                sweep_result_checks[0].detail,
            )
        )

    comparison_checks = [
        check for check in checks if check.name == "validation_comparison" and check.status in {"BLOCK", "WARN"}
    ]
    if comparison_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Do not adopt rejected validation candidate",
                comparison_checks[0].detail,
            )
        )

    comparison_delta_checks = [
        check
        for check in checks
        if check.name == "validation_comparison_deltas" and check.status in {"BLOCK", "WARN"}
    ]
    if comparison_delta_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Review validation scenario deltas",
                comparison_delta_checks[0].detail,
            )
        )

    candidate_decision_checks = [
        check
        for check in checks
        if check.name == "validation_candidate_decision" and check.status in {"BLOCK", "WARN"}
    ]
    if candidate_decision_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Do not adopt rejected validation candidate",
                candidate_decision_checks[0].detail,
            )
        )

    candidate_followup_checks = [
        check
        for check in checks
        if check.name == "validation_candidate_followup" and check.status in {"BLOCK", "WARN"}
    ]
    if candidate_followup_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Run candidate follow-up validation",
                candidate_followup_checks[0].detail,
            )
        )

    failure_pattern_checks = [
        check
        for check in checks
        if check.name == "validation_failure_patterns" and check.status in {"BLOCK", "WARN"}
    ]
    if failure_pattern_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Analyze persistent validation failures",
                failure_pattern_checks[0].detail,
            )
        )

    failure_drilldown_checks = [
        check
        for check in checks
        if check.name == "validation_failure_drilldown" and check.status in {"BLOCK", "WARN"}
    ]
    if failure_drilldown_checks:
        actions.append(
            ReadinessAction(
                "P1",
                "Fill validation drilldown evidence gaps",
                failure_drilldown_checks[0].detail,
            )
        )

    if any(check.name.endswith("_freshness") and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Regenerate stale validation reports",
                "Live execution must not rely on old deployment, risk, coverage, or performance reports.",
            )
        )

    if any(check.name == "data_quality" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Refresh or repair market data",
                "Data quality is blocked by stale, missing, duplicated, or invalid candle rows.",
            )
        )

    if any(check.name == "data_quality_exclusions" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P1",
                "Regenerate reports with data-quality exclusions",
                "Run data-check, then rerun monthly-backtest, monthly-validate, and monthly-plan so blocked symbols are excluded.",
            )
        )

    if not actions and readiness_status(checks) == "PASS":
        actions.append(
            ReadinessAction(
                "P2",
                "Continue paper/live dry-run",
                "Passing readiness checks confirms controls, not expected profit; keep monitoring drift and slippage.",
            )
        )
    return actions


def save_readiness_report(checks: list[ReadinessCheck], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [ReadinessCheck("overall", readiness_status(checks), f"{len(checks)} checks")] + checks
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in READINESS_COLUMNS})
    return len(rows)


def save_readiness_markdown(
    checks: list[ReadinessCheck],
    output_path: Path | str,
    *,
    title: str = "Production Readiness Report",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    status = readiness_status(checks)
    lines = [
        f"# {title}",
        "",
        f"Overall status: {status}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {_escape_markdown_cell(check.detail)} |")
    actions = recommend_readiness_actions(checks)
    if actions:
        lines.extend(
            [
                "",
                "## Required Next Actions",
                "",
                "| Priority | Action | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for action in actions:
            lines.append(
                f"| {action.priority} | {action.action} | {_escape_markdown_cell(action.detail)} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _artifact_checks(paths: list[Path | str]) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    for raw_path in paths:
        path = Path(raw_path)
        name = f"artifact:{path.name}"
        if not path.exists():
            checks.append(ReadinessCheck(name, "BLOCK", f"missing: {path}"))
        elif path.is_file() and path.stat().st_size <= 0:
            checks.append(ReadinessCheck(name, "BLOCK", f"empty: {path}"))
        else:
            checks.append(ReadinessCheck(name, "PASS", f"present: {path}"))
    return checks


def _report_freshness_checks(
    paths: dict[str, Path | str | None],
    *,
    max_age_days: int,
    as_of_date: str | None,
) -> list[ReadinessCheck]:
    try:
        as_of = date.fromisoformat(as_of_date) if as_of_date else date.today()
    except ValueError:
        return [ReadinessCheck("report_freshness_as_of", "BLOCK", f"invalid as_of_date: {as_of_date}")]

    checks: list[ReadinessCheck] = []
    for name, raw_path in paths.items():
        if raw_path is None:
            continue
        path = Path(raw_path)
        if not path.exists():
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime).date()
        age_days = max((as_of - modified).days, 0)
        check_name = f"{name}_freshness"
        if age_days > max_age_days:
            checks.append(
                ReadinessCheck(
                    check_name,
                    "BLOCK",
                    f"age {age_days}d exceeds {max_age_days}d; modified={modified.isoformat()}",
                )
            )
        else:
            checks.append(
                ReadinessCheck(
                    check_name,
                    "PASS",
                    f"age {age_days}d within {max_age_days}d; modified={modified.isoformat()}",
                )
            )
    return checks


def _deployment_gate_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("deployment_gate", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("deployment_gate", "BLOCK", f"empty: {path}")
    row = rows[-1]
    missing_columns = sorted(REQUIRED_DEPLOYMENT_GATE_COLUMNS - set(row.keys()))
    if missing_columns:
        return ReadinessCheck(
            "deployment_gate",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    deployable = _parse_bool(row.get("deployable", ""))
    reason = str(row.get("reason", "")).strip() or "no reason"
    source = str(row.get("source", "")).strip() or str(path)
    if deployable:
        return ReadinessCheck("deployment_gate", "PASS", f"{source}:passed")
    return ReadinessCheck("deployment_gate", "BLOCK", f"{source}:{reason}")


def _validation_scenario_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_scenarios", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    failed_rows = [
        row
        for row in rows
        if _parse_bool(row.get("required", "False")) and not _parse_bool(row.get("deployable", "False"))
    ]
    failed = [str(row.get("name", "unknown")) for row in failed_rows]
    if failed:
        preview = ",".join(failed[:10])
        suffix = f" (+{len(failed) - 10} more)" if len(failed) > 10 else ""
        reasons = Counter(str(row.get("reason", "unknown")).strip() or "unknown" for row in failed_rows)
        reason_summary = ", ".join(f"{reason}={count}" for reason, count in sorted(reasons.items()))
        bias_reasons = Counter()
        for row in failed_rows:
            if str(row.get("reason", "")).strip() != "universe_bias_warning":
                continue
            for reason in _split_bias_reasons(str(row.get("universe_bias_reasons", ""))):
                bias_reasons[reason] += 1
        bias_summary = ""
        if bias_reasons:
            bias_summary = "; bias: " + ", ".join(
                f"{reason}={count}" for reason, count in sorted(bias_reasons.items())
            )
        return ReadinessCheck(
            "validation_scenarios",
            "BLOCK",
            f"{len(failed)} failed: {preview}{suffix}; reasons: {reason_summary}{bias_summary}",
        )
    missing_columns = sorted(REQUIRED_VALIDATION_SCENARIO_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_scenarios",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    return ReadinessCheck("validation_scenarios", "PASS", f"{len(rows)} scenarios passed")


def _walk_forward_train_candidate_coverage_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("walk_forward_train_candidate_coverage", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    walk_rows = [
        row
        for row in rows
        if str(row.get("category", "")).strip() == "walk_forward"
        or str(row.get("name", "")).strip().startswith("walk_forward")
    ]
    if not walk_rows:
        return ReadinessCheck("walk_forward_train_candidate_coverage", "PASS", "no walk-forward scenarios")
    counts = [
        (
            str(row.get("name", "unknown")).strip() or "unknown",
            _train_candidate_score_count(str(row.get("train_candidate_scores", ""))),
            _train_candidate_unique_score_count(str(row.get("train_candidate_scores", ""))),
            _train_candidate_profiles_are_fallback_only(str(row.get("train_candidate_decision_profiles", ""))),
            _train_candidate_direct_scores_are_ineligible(str(row.get("train_candidate_direct_scores", ""))),
        )
        for row in walk_rows
    ]
    under_covered = [(name, count, unique_count) for name, count, unique_count, _, _ in counts if count < 2]
    low_diversity = [
        (name, count, unique_count)
        for name, count, unique_count, _, _ in counts
        if count >= 2 and unique_count < 2
    ]
    fallback_only = [
        (name, count, unique_count)
        for name, count, unique_count, is_fallback_only, _ in counts
        if is_fallback_only
    ]
    direct_alpha_ineligible = [
        (name, count, unique_count)
        for name, count, unique_count, is_fallback_only, is_direct_ineligible in counts
        if is_fallback_only and is_direct_ineligible
    ]
    if under_covered or low_diversity or fallback_only:
        problem_rows = _dedupe_train_candidate_problem_rows(under_covered + low_diversity + fallback_only)
        preview = ", ".join(f"{name}:{count}/{unique_count}" for name, count, unique_count in problem_rows[:5])
        suffix = f" (+{len(problem_rows) - 5} more)" if len(problem_rows) > 5 else ""
        return ReadinessCheck(
            "walk_forward_train_candidate_coverage",
            "WARN",
            f"under_covered={len(under_covered)}; low_diversity={len(low_diversity)}; "
            f"fallback_only={len(fallback_only)}; "
            f"direct_alpha_ineligible={len(direct_alpha_ineligible)}; "
            f"min_candidates={min(count for _, count, _, _, _ in counts)}; "
            f"min_unique_scores={min(unique_count for _, _, unique_count, _, _ in counts)}; {preview}{suffix}",
        )
    return ReadinessCheck(
        "walk_forward_train_candidate_coverage",
        "PASS",
        f"{len(walk_rows)} walk-forward scenarios have at least 2 train candidates",
    )


def _train_candidate_score_count(value: str) -> int:
    return len([part for part in value.split(";") if part.strip()])


def _dedupe_train_candidate_problem_rows(rows: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    deduped: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for name, count, unique_count in rows:
        if name in seen:
            continue
        seen.add(name)
        deduped.append((name, count, unique_count))
    return deduped


def _train_candidate_unique_score_count(value: str) -> int:
    signatures: set[str] = set()
    for part in value.split(";"):
        text = part.strip()
        if not text:
            continue
        _, _, score_signature = text.partition(":")
        signatures.add(score_signature.strip() or text)
    return len(signatures)


def _train_candidate_profiles_are_fallback_only(value: str) -> bool:
    profiles = [part.strip() for part in value.split(";") if part.strip()]
    if not profiles:
        return False
    alpha_ratios: list[float] = []
    for profile in profiles:
        marker = "alpha_ratio="
        if marker not in profile:
            return False
        raw_ratio = profile.rsplit(marker, 1)[-1].split(",", 1)[0].strip()
        try:
            alpha_ratios.append(float(raw_ratio))
        except ValueError:
            return False
    return bool(alpha_ratios) and all(ratio <= 0.0 for ratio in alpha_ratios)


def _train_candidate_direct_scores_are_ineligible(value: str) -> bool:
    scores = [part.strip() for part in value.split(";") if part.strip()]
    if not scores:
        return False
    excess_values: list[float] = []
    for score in scores:
        marker = "excess="
        if marker not in score:
            return False
        raw_value = score.split(marker, 1)[-1].split(",", 1)[0].strip()
        try:
            excess_values.append(float(raw_value))
        except ValueError:
            return False
    return bool(excess_values) and all(value <= 0.0 for value in excess_values)


def _validation_failure_actions_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_failure_actions", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_failure_actions", "PASS", "no validation failures recorded")
    missing_columns = sorted(REQUIRED_VALIDATION_FAILURE_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_failure_actions",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    missing_values = sorted(
        {
            column
            for row in rows
            for column in REQUIRED_VALIDATION_FAILURE_VALUE_COLUMNS
            if not str(row.get(column, "")).strip()
        }
    )
    if missing_values:
        return ReadinessCheck(
            "validation_failure_actions",
            "BLOCK",
            f"missing_required_values={','.join(missing_values)}",
        )

    severities = Counter(str(row.get("severity", "")).strip().upper() or "WARN" for row in rows)
    action_counts = Counter(
        str(row.get("suggested_action", "")).strip() or "REVIEW_SCENARIO"
        for row in rows
    )
    status = "BLOCK" if severities.get("BLOCK", 0) else "WARN"
    action_summary = ", ".join(
        f"{action}={count}" for action, count in sorted(action_counts.items())
    )
    samples_by_action: dict[str, str] = {}
    for row in rows:
        action = str(row.get("suggested_action", "")).strip() or "REVIEW_SCENARIO"
        if action in samples_by_action:
            continue
        name = str(row.get("name", "unknown")).strip() or "unknown"
        reason = str(row.get("reason", "unknown")).strip() or "unknown"
        metric = str(row.get("failed_metric", "")).strip()
        value = str(row.get("metric_value", "")).strip()
        hints = str(row.get("parameter_hints", "")).strip()
        sample = f"{action}->{name}:{reason}"
        if metric:
            sample += f" {metric}={value}"
        if hints:
            sample += f"; hints={hints}"
        samples_by_action[action] = sample
    samples = " | ".join(samples_by_action[action] for action in sorted(samples_by_action))
    return ReadinessCheck(
        "validation_failure_actions",
        status,
        f"{len(rows)} failures; actions: {action_summary}; samples: {samples}",
    )


def _validation_remediation_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_remediation", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_remediation", "PASS", "no validation remediation experiments needed")
    missing_columns = sorted(REQUIRED_VALIDATION_REMEDIATION_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_remediation",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    missing_values = sorted(
        {
            column
            for row in rows
            for column in REQUIRED_VALIDATION_REMEDIATION_VALUE_COLUMNS
            if not str(row.get(column, "")).strip()
        }
    )
    if missing_values:
        return ReadinessCheck(
            "validation_remediation",
            "BLOCK",
            f"missing_required_values={','.join(missing_values)}",
        )
    priority_counts = Counter(str(row.get("priority", "")).strip() or "P2" for row in rows)
    status = "BLOCK" if priority_counts.get("P0", 0) or priority_counts.get("P1", 0) else "WARN"
    first = rows[0]
    detail = (
        f"{len(rows)} experiment groups; "
        f"priorities: {', '.join(f'{priority}={count}' for priority, count in sorted(priority_counts.items()))}; "
        f"top_action={first.get('suggested_action', '')}; "
        f"affected={first.get('affected_scenarios', '')}; "
        f"next={first.get('next_experiment', '')}"
    )
    return ReadinessCheck("validation_remediation", status, detail)


def _validation_sweep_plan_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_sweep_plan", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_sweep_plan", "PASS", "no sweep experiments planned")
    missing_columns = sorted(REQUIRED_VALIDATION_SWEEP_PLAN_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_sweep_plan",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    missing_values = sorted(
        {
            column
            for row in rows
            for column in REQUIRED_VALIDATION_SWEEP_PLAN_VALUE_COLUMNS
            if not str(row.get(column, "")).strip()
        }
    )
    if missing_values:
        return ReadinessCheck(
            "validation_sweep_plan",
            "BLOCK",
            f"missing_required_values={','.join(missing_values)}",
        )
    first = rows[0]
    actions = Counter(str(row.get("suggested_action", "")).strip() or "UNKNOWN" for row in rows)
    action_summary = ", ".join(f"{action}={count}" for action, count in sorted(actions.items()))
    detail = (
        f"{len(rows)} planned experiments; actions: {action_summary}; "
        f"first={first.get('experiment_id', '')}; "
        f"targets={first.get('target_scenarios', '')}; "
        f"risk_note={first.get('risk_note', '')}"
    )
    return ReadinessCheck("validation_sweep_plan", "WARN", detail)


def _validation_sweep_results_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_sweep_results", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_sweep_results", "WARN", "empty sweep result report")
    missing_columns = sorted(REQUIRED_VALIDATION_SWEEP_RESULTS_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_sweep_results",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    missing_values = sorted(
        {
            column
            for row in rows
            for column in REQUIRED_VALIDATION_SWEEP_RESULTS_VALUE_COLUMNS
            if not str(row.get(column, "")).strip()
        }
    )
    if missing_values:
        return ReadinessCheck(
            "validation_sweep_results",
            "BLOCK",
            f"missing_required_values={','.join(missing_values)}",
        )
    statuses = Counter(str(row.get("status", "")).strip().upper() or "UNKNOWN" for row in rows)
    adoption_statuses = Counter(
        str(row.get("adoption_status", "")).strip().upper()
        for row in rows
        if str(row.get("adoption_status", "")).strip()
    )
    status_summary = ", ".join(f"{status}={count}" for status, count in sorted(statuses.items()))
    adoption_summary = ", ".join(
        f"{status}={count}" for status, count in sorted(adoption_statuses.items())
    )
    status = "BLOCK" if statuses.get("REGRESSED", 0) else "WARN"
    best = _best_sweep_result_row(rows)
    improved = [
        str(row.get("experiment_id", "")).strip()
        for row in rows
        if str(row.get("status", "")).strip().upper() == "IMPROVED"
        and str(row.get("experiment_id", "")).strip()
    ]
    improved_summary = "; improved=" + ", ".join(improved[:5]) if improved else ""
    target_only_note = "; target_only_improvements_require_full_validation" if improved else ""
    candidate_args = str(best.get("candidate_validation_args", "")).strip()
    candidate_args_note = f"; candidate_validation_args={candidate_args}" if candidate_args else ""
    detail = (
        f"{len(rows)} sweep results; statuses: {status_summary}; "
        f"adoption_statuses: {adoption_summary or 'unspecified'}; "
        f"best={best.get('experiment_id', '')}; "
        f"delta={best.get('failed_delta', '')}; "
        f"summary={best.get('result_summary', '')}; "
        f"risk_note={best.get('risk_note', '')}"
        f"{candidate_args_note}"
        f"{improved_summary}"
        f"{target_only_note}"
    )
    return ReadinessCheck("validation_sweep_results", status, detail)


def _validation_comparison_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_comparison", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_comparison", "WARN", f"empty: {path}")
    row = rows[-1]
    missing_columns = sorted(REQUIRED_VALIDATION_COMPARISON_COLUMNS - set(row.keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_comparison",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    raw_status = str(row.get("status", "")).strip().upper()
    if raw_status in {"ACCEPT", "PASS", "APPROVE", "APPROVED"}:
        status = "PASS"
    elif raw_status in {"REJECT", "REJECTED"}:
        status = "WARN"
    else:
        status = "BLOCK"
    detail = (
        f"{row.get('candidate_label', path)}:{raw_status or 'UNKNOWN'}; "
        f"failed_delta={row.get('failed_delta', '')}; "
        f"new_failures={row.get('new_failures', '')}; "
        f"resolved_failures={row.get('resolved_failures', '')}; "
        f"summary={row.get('summary', '')}"
    )
    return ReadinessCheck("validation_comparison", status, detail)


def _validation_comparison_delta_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_comparison_deltas", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_comparison_deltas", "BLOCK", f"empty: {path}")
    missing_columns = sorted(REQUIRED_VALIDATION_COMPARISON_DELTA_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_comparison_deltas",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    classifications = Counter(str(row.get("classification", "")).strip() or "UNKNOWN" for row in rows)
    diagnostics = Counter(str(row.get("diagnostic", "")).strip() or "unknown" for row in rows)
    status = "WARN" if classifications.get("NEW_FAILURE", 0) else "PASS"
    class_summary = ", ".join(
        f"{name}={count}" for name, count in sorted(classifications.items())
    )
    diagnostic_summary = ", ".join(
        f"{name}={count}" for name, count in sorted(diagnostics.items()) if name != "no_required_failure_change"
    )
    new_failures = [
        str(row.get("name", "")).strip()
        for row in rows
        if str(row.get("classification", "")).strip() == "NEW_FAILURE"
        and str(row.get("name", "")).strip()
    ]
    detail = f"{len(rows)} scenario deltas; classes: {class_summary}"
    if diagnostic_summary:
        detail += f"; diagnostics: {diagnostic_summary}"
    if new_failures:
        detail += f"; new_failures={'; '.join(new_failures[:5])}"
    return ReadinessCheck("validation_comparison_deltas", status, detail)


def _validation_candidate_decision_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_candidate_decision", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_candidate_decision", "BLOCK", f"empty: {path}")

    row = rows[-1]
    missing_columns = sorted(REQUIRED_VALIDATION_CANDIDATE_DECISION_COLUMNS - set(row.keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_candidate_decision",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    decision = str(row.get("decision", "")).strip().upper() or "UNKNOWN"
    comparison_status = str(row.get("comparison_status", "")).strip().upper() or "UNKNOWN"
    promotion_proof_present, promotion_status = candidate_promotion_proof_status(row)
    acceptance_issue = _candidate_acceptance_consistency_issue(row, comparison_status)
    if decision in {"ACCEPT", "PASS", "APPROVE", "APPROVED"}:
        status = "PASS" if promotion_proof_present and not acceptance_issue else "BLOCK"
    elif decision == "PAPER_REVIEW":
        status = "BLOCK"
    elif decision in {"REJECT", "REJECTED", "HOLD"}:
        status = "WARN"
    else:
        status = "BLOCK"

    detail = (
        f"{row.get('candidate_label', path)}:{decision}; "
        f"comparison_status={comparison_status}; "
        f"failed_delta={row.get('failed_delta', '')}; "
        f"new_failures={row.get('new_failure_count', '')}; "
        f"resolved={row.get('resolved_count', '')}; "
        f"new_failure_names={row.get('new_failure_names', '')}; "
        f"resolved_failure_names={row.get('resolved_failure_names', '')}; "
        f"unchanged_failure_names={row.get('unchanged_failure_names', '')}; "
        f"diagnostics={row.get('new_failure_diagnostics', '')}; "
        f"reasons={row.get('decision_reasons', '')}; "
        f"promotion_status={_candidate_promotion_status(decision, promotion_proof_present, promotion_status)}; "
        f"acceptance_status={acceptance_issue or 'consistent'}; "
        f"recommendation={row.get('recommendation', '')}"
    )
    return ReadinessCheck("validation_candidate_decision", status, detail)


def _candidate_promotion_status(decision: str, promotion_proof_present: bool, proof_status: str) -> str:
    if decision == "PAPER_REVIEW":
        return "promotion_blocked"
    if decision in {"ACCEPT", "PASS", "APPROVE", "APPROVED"} and not promotion_proof_present:
        return proof_status
    return "not_blocked_by_decision"


def _candidate_acceptance_consistency_issue(row: dict[str, Any], comparison_status: str) -> str:
    allowed_statuses = {"PASS", "PASSED", "IMPROVED", "ACCEPT", "ACCEPTED", "APPROVE", "APPROVED"}
    issues: list[str] = []
    if comparison_status not in allowed_statuses:
        issues.append(f"comparison_status={comparison_status}")
    candidate_failed_required = _parse_int(row.get("candidate_failed_required", "0"))
    if candidate_failed_required > 0:
        issues.append(f"candidate_failed_required={candidate_failed_required}")
    new_failure_count = _parse_int(row.get("new_failure_count", "0"))
    if new_failure_count > 0:
        issues.append(f"new_failure_count={new_failure_count}")
    if not issues:
        return ""
    return f"acceptance_consistency_failed:{','.join(issues)}"


def _validation_candidate_followup_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_candidate_followup", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_candidate_followup", "WARN", f"empty: {path}")
    missing_columns = sorted(REQUIRED_VALIDATION_CANDIDATE_FOLLOWUP_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_candidate_followup",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    rows = sorted(rows, key=lambda row: _parse_float(row.get("priority_rank") or 9999.0))
    top = rows[0]
    decisions = _candidate_followup_decisions(rows, base_dir=path.parent)
    pending_rows = [
        row
        for row in rows
        if _candidate_followup_decision_for_row(row, base_dir=path.parent) is None
    ]
    decision_counts = Counter(str(decision.get("decision", "")).strip().upper() for decision in decisions)
    decision_summary = ", ".join(
        f"{decision}={count}" for decision, count in sorted(decision_counts.items()) if decision
    )
    promotion_blocked = []
    for decision_row in decisions:
        decision_value = str(decision_row.get("decision", "")).strip().upper()
        comparison_status = str(decision_row.get("comparison_status", "")).strip().upper() or "UNKNOWN"
        proof_present, proof_status = candidate_promotion_proof_status(decision_row)
        if decision_value == "PAPER_REVIEW":
            promotion_blocked.append(
                f"{decision_row.get('candidate_label', '')}:PAPER_REVIEW:promotion_blocked"
            )
        elif decision_value in {"ACCEPT", "PASS", "APPROVE", "APPROVED"} and not proof_present:
            promotion_blocked.append(
                f"{decision_row.get('candidate_label', '')}:{decision_value}:{proof_status}"
            )
        elif decision_value in {"ACCEPT", "PASS", "APPROVE", "APPROVED"}:
            acceptance_issue = _candidate_acceptance_consistency_issue(decision_row, comparison_status)
            if acceptance_issue:
                promotion_blocked.append(
                    f"{decision_row.get('candidate_label', '')}:{decision_value}:{acceptance_issue}"
                )
    top_decision = decisions[0] if decisions else {}
    decision_detail = ""
    if decision_summary:
        decision_detail = (
            f"; decisions: {decision_summary}; "
            f"top_decision={top_decision.get('decision', '')}; "
            f"candidate_failed_required={top_decision.get('candidate_failed_required', '')}; "
            f"new_failures={top_decision.get('new_failure_names', '')}"
        )
    if promotion_blocked:
        decision_detail += f"; promotion_blocked_decisions={'; '.join(promotion_blocked[:5])}"
    pending_detail = f"; completed={len(decisions)}; pending={len(pending_rows)}"
    if pending_rows:
        next_pending = pending_rows[0]
        pending_detail += (
            f"; next_pending={next_pending.get('experiment_id', '')}; "
            f"next_validation_command={next_pending.get('validation_command', '')}"
        )
    else:
        pending_detail += "; all_candidate_followups_completed"
    command_detail = ""
    if pending_rows:
        command_detail = (
            f"; validation_command={top.get('validation_command', '')}; "
            f"comparison_command={top.get('comparison_command', '')}"
        )
    detail = (
        f"{len(rows)} candidate follow-up command sets; "
        f"top={top.get('experiment_id', '')}; "
        f"failed_delta={top.get('failed_delta', '')}"
        f"{command_detail}"
        f"{decision_detail}"
        f"{pending_detail}"
    )
    status = "BLOCK" if promotion_blocked else "WARN"
    return ReadinessCheck("validation_candidate_followup", status, detail)


def _validation_failure_patterns_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_failure_patterns", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_failure_patterns", "PASS", f"empty: {path}")
    missing_columns = sorted(REQUIRED_VALIDATION_FAILURE_PATTERN_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_failure_patterns",
            "BLOCK",
            f"missing required columns: {','.join(missing_columns)}",
        )
    missing_values = sorted(
        {
            column
            for row in rows
            for column in REQUIRED_VALIDATION_FAILURE_PATTERN_VALUE_COLUMNS
            if not str(row.get(column, "")).strip()
        }
    )
    if missing_values:
        return ReadinessCheck(
            "validation_failure_patterns",
            "BLOCK",
            f"missing_required_values={','.join(missing_values)}",
        )

    statuses = Counter(str(row.get("pattern_status", "")).strip().upper() for row in rows)
    blocking_statuses = {"PERSISTENT_BLOCK", "REGRESSION_RISK"}
    warning_statuses = {"MIXED_RESPONSE", "BASELINE_BLOCK"}
    blocked_rows = [
        row
        for row in rows
        if str(row.get("pattern_status", "")).strip().upper() in blocking_statuses
    ]
    warned_rows = [
        row
        for row in rows
        if str(row.get("pattern_status", "")).strip().upper() in warning_statuses
    ]
    status = "PASS"
    if blocked_rows:
        status = "BLOCK"
    elif warned_rows:
        status = "WARN"

    status_summary = ", ".join(f"{name}={count}" for name, count in sorted(statuses.items()) if name)
    top_rows = blocked_rows or warned_rows or rows
    top_detail = "; ".join(
        f"{row.get('scenario', '')}:{row.get('pattern_status', '')}:{row.get('suggested_action', '')}"
        for row in top_rows[:5]
    )
    detail = f"{len(rows)} scenarios; statuses: {status_summary}; top={top_detail}"
    return ReadinessCheck("validation_failure_patterns", status, detail)


def _validation_failure_drilldown_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_failure_drilldown", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("validation_failure_drilldown", "WARN", f"empty: {path}")
    missing_columns = sorted(REQUIRED_VALIDATION_FAILURE_DRILLDOWN_COLUMNS - set(rows[-1].keys()))
    if missing_columns:
        return ReadinessCheck(
            "validation_failure_drilldown",
            "BLOCK",
            f"missing required columns: {','.join(missing_columns)}",
        )
    root_causes = Counter(str(row.get("likely_root_cause", "")).strip() for row in rows)
    evidence_gap_rows = [row for row in rows if str(row.get("evidence_gaps", "")).strip()]
    persistent_gap_rows = [
        row
        for row in evidence_gap_rows
        if str(row.get("pattern_status", "")).strip().upper() in {"PERSISTENT_BLOCK", "REGRESSION_RISK"}
    ]
    if persistent_gap_rows:
        status = "WARN"
    else:
        status = "PASS"
    root_summary = ", ".join(f"{name}={count}" for name, count in sorted(root_causes.items()) if name)
    top_rows = persistent_gap_rows or rows
    top_detail = "; ".join(
        f"{row.get('scenario', '')}:{row.get('likely_root_cause', '')}:{row.get('evidence_gaps', '')}"
        for row in top_rows[:5]
    )
    detail = (
        f"{len(rows)} scenarios; root_causes: {root_summary}; "
        f"evidence_gaps={len(evidence_gap_rows)}; top={top_detail}"
    )
    return ReadinessCheck("validation_failure_drilldown", status, detail)


def _candidate_followup_decisions(rows: list[dict[str, Any]], *, base_dir: Path) -> list[dict[str, str]]:
    decisions: list[dict[str, str]] = []
    for row in rows:
        decision = _candidate_followup_decision_for_row(row, base_dir=base_dir)
        if decision is not None:
            decisions.append(decision)
    return decisions


def _candidate_followup_decision_for_row(
    row: dict[str, Any],
    *,
    base_dir: Path,
) -> dict[str, str] | None:
    raw_path = str(row.get("decision_output", "")).strip()
    if not raw_path:
        return None
    decision_path = Path(raw_path)
    if not decision_path.exists() and not decision_path.is_absolute():
        candidate = base_dir / decision_path
        if candidate.exists():
            decision_path = candidate
    if not decision_path.exists():
        return None
    decision_rows = _read_csv_rows(decision_path)
    if not decision_rows:
        return None
    return decision_rows[-1]


def _risk_report_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("risk_report", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    blocked = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "BLOCK"
    ]
    if blocked:
        return ReadinessCheck("risk_report", "BLOCK", "; ".join(blocked[:5]))
    warned = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "WARN"
    ]
    if warned:
        return ReadinessCheck("risk_report", "WARN", "; ".join(warned[:5]))
    names = {str(row.get("name", "")).strip() for row in rows}
    missing = sorted(REQUIRED_RISK_REPORT_CHECKS - names)
    if missing:
        return ReadinessCheck(
            "risk_report",
            "BLOCK",
            f"missing_required_checks={','.join(missing)}",
        )
    missing_detail = sorted(
        str(row.get("name", "")).strip()
        for row in rows
        if str(row.get("name", "")).strip() in REQUIRED_RISK_REPORT_CHECKS
        and not str(row.get("detail", "")).strip()
    )
    if missing_detail:
        return ReadinessCheck(
            "risk_report",
            "BLOCK",
            f"missing_required_detail={','.join(missing_detail)}",
        )
    return ReadinessCheck("risk_report", "PASS", f"{len(rows)} risk checks passed")


def _performance_report_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("performance_report", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("performance_report", "BLOCK", f"empty: {path}")
    blocked = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "BLOCK"
    ]
    if blocked:
        return ReadinessCheck("performance_report", "BLOCK", "; ".join(blocked[:5]))
    warned = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "WARN"
    ]
    if warned:
        return ReadinessCheck("performance_report", "WARN", "; ".join(warned[:5]))
    names = {str(row.get("name", "")).strip() for row in rows}
    missing = sorted(REQUIRED_PERFORMANCE_REPORT_CHECKS - names)
    if missing:
        return ReadinessCheck(
            "performance_report",
            "BLOCK",
            f"missing_required_checks={','.join(missing)}",
        )
    missing_detail = sorted(
        str(row.get("name", "")).strip()
        for row in rows
        if str(row.get("name", "")).strip() in REQUIRED_PERFORMANCE_REPORT_CHECKS
        and not str(row.get("detail", "")).strip()
    )
    if missing_detail:
        return ReadinessCheck(
            "performance_report",
            "BLOCK",
            f"missing_required_detail={','.join(missing_detail)}",
        )
    return ReadinessCheck("performance_report", "PASS", f"{len(rows)} performance checks passed")


def _performance_concentration_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("performance_concentration", "WARN", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("performance_concentration", "BLOCK", f"empty: {path}")
    row = rows[-1]
    missing_columns = sorted(REQUIRED_PERFORMANCE_CONCENTRATION_COLUMNS - set(row.keys()))
    if missing_columns:
        return ReadinessCheck(
            "performance_concentration",
            "BLOCK",
            f"missing_required_columns={','.join(missing_columns)}",
        )
    source = str(row.get("source", path)).strip()
    status = str(row.get("concentration_status", "")).strip().upper() or "BLOCK"
    if status not in {"PASS", "WARN", "BLOCK"}:
        status = "BLOCK"
    reasons = str(row.get("concentration_reasons", "")).strip() or "no reasons"
    if source and not source.startswith("monthly-validate"):
        reasons = f"unexpected_source:{source}; {reasons}"
        if status == "PASS":
            status = "WARN"
    detail = (
        f"{source or path}:{reasons}; "
        f"top_1_month={row.get('top_1_month_contribution', '')}; "
        f"top_5_symbol={row.get('top_5_symbol_contribution', '')}"
    )
    return ReadinessCheck("performance_concentration", status, detail)


def _drawdown_attribution_check(
    monthly_path: Path | None,
    symbol_path: Path | None,
    validation_failures_path: Path | None,
) -> ReadinessCheck:
    needs_attribution = _validation_has_drawdown_failure(validation_failures_path)
    missing = [
        str(path)
        for path in (monthly_path, symbol_path)
        if path is not None and not path.exists()
    ]
    if missing:
        status = "WARN" if needs_attribution else "PASS"
        prefix = "missing" if needs_attribution else "not required; missing"
        return ReadinessCheck("drawdown_attribution", status, f"{prefix}: {', '.join(missing)}")
    if monthly_path is None or symbol_path is None:
        status = "WARN" if needs_attribution else "PASS"
        return ReadinessCheck("drawdown_attribution", status, "paths not configured")
    monthly_rows = _read_csv_rows(monthly_path)
    symbol_rows = _read_csv_rows(symbol_path)
    if not monthly_rows or not symbol_rows:
        status = "WARN" if needs_attribution else "PASS"
        return ReadinessCheck(
            "drawdown_attribution",
            status,
            f"empty attribution report: monthly_rows={len(monthly_rows)}; symbol_rows={len(symbol_rows)}",
        )
    monthly_missing = sorted(REQUIRED_DRAWDOWN_ATTRIBUTION_MONTHLY_COLUMNS - set(monthly_rows[-1].keys()))
    symbol_missing = sorted(REQUIRED_DRAWDOWN_ATTRIBUTION_SYMBOL_COLUMNS - set(symbol_rows[-1].keys()))
    if monthly_missing or symbol_missing:
        return ReadinessCheck(
            "drawdown_attribution",
            "BLOCK",
            (
                "missing_required_columns="
                f"monthly:{','.join(monthly_missing) or 'none'}; "
                f"symbol:{','.join(symbol_missing) or 'none'}"
            ),
        )

    worst_loss_month = min(monthly_rows, key=lambda row: _parse_float(row.get("equity_change")))
    worst_drawdown_month = min(monthly_rows, key=lambda row: _parse_float(row.get("worst_drawdown_pct")))
    worst_symbol = min(symbol_rows, key=lambda row: _parse_float(row.get("realized_pnl")))
    detail = (
        f"monthly_rows={len(monthly_rows)}; symbol_rows={len(symbol_rows)}; "
        f"worst_month={worst_loss_month.get('month', '')} "
        f"equity_change={worst_loss_month.get('equity_change', '')}; "
        f"worst_drawdown_month={worst_drawdown_month.get('month', '')} "
        f"worst_drawdown_pct={worst_drawdown_month.get('worst_drawdown_pct', '')}; "
        f"worst_symbol={worst_symbol.get('symbol', '')} "
        f"realized_pnl={worst_symbol.get('realized_pnl', '')}"
    )
    return ReadinessCheck("drawdown_attribution", "PASS", detail)


def _coverage_report_check(path: Path, *, warning_min_coverage_pct: float = 90.0) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("universe_price_coverage", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("universe_price_coverage", "BLOCK", f"empty: {path}")
    blocked = [row for row in rows if str(row.get("status", "")).upper() == "BLOCK"]
    coverage_values = [
        float(row.get("coverage_pct", 0) or 0)
        for row in rows
        if str(row.get("coverage_pct", "")).strip() != ""
    ]
    min_coverage = min(coverage_values) if coverage_values else 0.0
    if blocked:
        worst = min(blocked, key=lambda row: float(row.get("coverage_pct", 0) or 0))
        covered = _parse_int(worst.get("covered_symbols", 0))
        universe = _parse_int(worst.get("universe_symbols", 0))
        target_80 = math.ceil(universe * 0.8) if universe > 0 else 0
        need_to_80 = max(0, target_80 - covered)
        batches_of_50 = math.ceil(need_to_80 / 50) if need_to_80 > 0 else 0
        return ReadinessCheck(
            "universe_price_coverage",
            "BLOCK",
            (
                f"{len(blocked)} blocked snapshots; min_coverage_pct={min_coverage:.1f}; "
                f"worst_date={worst.get('date', 'unknown')}; missing={worst.get('missing_symbols', '')}; "
                f"need_to_80pct={need_to_80}; batches_of_50={batches_of_50}"
            ),
        )
    if coverage_values and min_coverage < warning_min_coverage_pct:
        worst = min(
            rows,
            key=lambda row: float(row.get("coverage_pct", 0) or 0),
        )
        covered = _parse_int(worst.get("covered_symbols", 0))
        universe = _parse_int(worst.get("universe_symbols", 0))
        target = math.ceil(universe * (warning_min_coverage_pct / 100.0)) if universe > 0 else 0
        need_to_warning = max(0, target - covered)
        batches_of_50 = math.ceil(need_to_warning / 50) if need_to_warning > 0 else 0
        target_label = int(warning_min_coverage_pct) if float(warning_min_coverage_pct).is_integer() else warning_min_coverage_pct
        return ReadinessCheck(
            "universe_price_coverage",
            "WARN",
            (
                f"{len(rows)} snapshots below coverage warning target; min_coverage_pct={min_coverage:.1f}; "
                f"warning_min_coverage_pct={warning_min_coverage_pct:.1f}; "
                f"worst_date={worst.get('date', 'unknown')}; missing={worst.get('missing_symbols', '')}; "
                f"need_to_{target_label}pct={need_to_warning}; batches_of_50={batches_of_50}"
            ),
        )
    return ReadinessCheck(
        "universe_price_coverage",
        "PASS",
        f"{len(rows)} snapshots covered; min_coverage_pct={min_coverage:.1f}",
    )


def _missing_ohlcv_targets_check(path: Path, coverage_check: ReadinessCheck | None) -> ReadinessCheck | None:
    coverage_needs_plan = coverage_check is not None and coverage_check.status in {"BLOCK", "WARN"}
    if not coverage_needs_plan and not path.exists():
        return None
    if not path.exists():
        return ReadinessCheck(
            "krx_missing_ohlcv_targets",
            "WARN",
            (
                f"missing target plan: {path}; "
                "run plan-pykrx-missing-ohlcv --universe-file data/krx_metadata/krx_universe_monthly.csv"
            ),
        )
    rows = _read_csv_rows(path)
    if not rows:
        status = "WARN" if coverage_needs_plan else "PASS"
        return ReadinessCheck("krx_missing_ohlcv_targets", status, f"empty target plan: {path}")
    sorted_rows = sorted(
        rows,
        key=lambda row: (-_parse_int(row.get("missing_snapshots", 0)), str(row.get("symbol", ""))),
    )
    top = "; ".join(
        f"{str(row.get('symbol', '')).strip()}:{_parse_int(row.get('missing_snapshots', 0))}"
        for row in sorted_rows[:5]
        if str(row.get("symbol", "")).strip()
    )
    first_missing = min(
        (str(row.get("first_missing_date", "")).strip() for row in rows if str(row.get("first_missing_date", "")).strip()),
        default="",
    )
    last_missing = max(
        (str(row.get("last_missing_date", "")).strip() for row in rows if str(row.get("last_missing_date", "")).strip()),
        default="",
    )
    detail = (
        f"targets={len(rows)}; top={top}; first_missing_date={first_missing}; "
        f"last_missing_date={last_missing}; next=python -m backtester fetch-pykrx-missing-ohlcv-loop "
        f"--universe-file data/krx_metadata/krx_universe_monthly.csv --start 2024-01-01 --end YYYY-MM-DD "
        f"--targets-output {path}"
    )
    return ReadinessCheck("krx_missing_ohlcv_targets", "PASS", detail)


def _missing_ohlcv_fetch_plan_check(path: Path, targets_path: Path | None) -> ReadinessCheck | None:
    target_plan_exists = targets_path is not None and targets_path.exists()
    if not target_plan_exists and not path.exists():
        return None
    if not path.exists():
        return ReadinessCheck(
            "krx_missing_ohlcv_fetch_plan",
            "WARN",
            f"missing fetch plan: {path}; rerun plan-pykrx-missing-ohlcv with --fetch-plan-output",
        )
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("krx_missing_ohlcv_fetch_plan", "WARN", f"empty fetch plan: {path}")
    row = rows[-1]
    status_raw = str(row.get("status", "")).strip().upper()
    status = "PASS" if status_raw in {"READY", "COMPLETE", "PASS"} else "WARN"
    command = str(row.get("recommended_command", "")).strip()
    detail = (
        f"status={status_raw or 'UNKNOWN'}; target_count={row.get('target_count', '')}; "
        f"planned_batches={row.get('planned_batches', '')}; planned_symbols={row.get('planned_symbols', '')}; "
        f"remaining_after_plan={row.get('remaining_after_plan', '')}; "
        f"batch_timeout_seconds={row.get('batch_timeout_seconds', '')}; "
        f"batch_pause_seconds={row.get('batch_pause_seconds', '')}; "
        f"top={row.get('top_symbols', '')}; command={command}"
    )
    return ReadinessCheck("krx_missing_ohlcv_fetch_plan", status, detail)


def _missing_ohlcv_fetch_summary_check(path: Path) -> ReadinessCheck | None:
    if not path.exists():
        return None
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("krx_missing_ohlcv_fetch_summary", "WARN", f"empty fetch summary: {path}")
    row = rows[-1]
    raw_status = str(row.get("status", "")).strip()
    status_key = raw_status.lower()
    timed_out = _parse_int(row.get("timed_out_batches", 0))
    failed = _parse_int(row.get("failed_batches", 0))
    status = "PASS" if status_key == "completed" and timed_out == 0 and failed == 0 else "WARN"
    detail = (
        f"status={raw_status or 'unknown'}; attempted_batches={row.get('attempted_batches', '')}; "
        f"completed_batches={row.get('completed_batches', '')}; timed_out_batches={row.get('timed_out_batches', '')}; "
        f"failed_batches={row.get('failed_batches', '')}; saved={row.get('saved', '')}; "
        f"remaining_targets={row.get('remaining_targets', '')}; stderr_tail={row.get('last_stderr_tail', '')}"
    )
    return ReadinessCheck("krx_missing_ohlcv_fetch_summary", status, detail)


def _data_quality_check(path: Path, *, max_stale_days: int, as_of_date: str | None) -> ReadinessCheck:
    result = validate_dataset_freshness(path, as_of_date=as_of_date, max_stale_days=max_stale_days)
    detail_parts = [
        f"latest_date={result.latest_date or ''}",
        f"stale_days={'' if result.stale_days is None else result.stale_days}",
        f"rows_checked={result.rows_checked}",
    ]
    if result.issues:
        detail_parts.append("issues=" + "; ".join(result.issues[:5]))
    if result.warnings:
        detail_parts.append("warnings=" + "; ".join(result.warnings[:5]))
    return ReadinessCheck("data_quality", result.status, "; ".join(detail_parts))


def _data_quality_exclusions_check(
    exclusions_path: Path,
    report_paths: dict[str, Path | str | None],
) -> ReadinessCheck:
    if not exclusions_path.exists():
        return ReadinessCheck(
            "data_quality_exclusions",
            "WARN",
            f"default exclusion report missing: {exclusions_path}",
        )

    existing_reports = {
        name: Path(path)
        for name, path in report_paths.items()
        if path is not None and Path(path).exists()
    }
    if not existing_reports:
        return ReadinessCheck(
            "data_quality_exclusions",
            "WARN",
            f"exclusion report exists but no monthly reports were available to verify: {exclusions_path}",
        )

    unapplied: list[str] = []
    applied: list[str] = []
    for name, path in existing_reports.items():
        if _report_has_applied_data_quality_exclusions(path):
            applied.append(name)
        else:
            unapplied.append(name)

    if unapplied:
        return ReadinessCheck(
            "data_quality_exclusions",
            "BLOCK",
            (
                f"exclusion report exists but reports lack applied marker: {','.join(unapplied)}; "
                f"applied={','.join(applied) if applied else 'none'}; exclusions={exclusions_path}"
            ),
        )
    return ReadinessCheck(
        "data_quality_exclusions",
        "PASS",
        f"applied in {','.join(applied)}; exclusions={exclusions_path}",
    )


def _report_has_applied_data_quality_exclusions(path: Path) -> bool:
    try:
        rows = _read_csv_rows(path)
    except (OSError, csv.Error, UnicodeDecodeError):
        return False
    for row in rows:
        source = str(row.get("source", ""))
        if "data_quality_exclusions=auto:" in source or "data_quality_exclusions=explicit:" in source:
            return True
        if str(row.get("name", "")) == "data_quality_exclusions" and str(row.get("status", "")).upper() == "PASS":
            return True
        detail = str(row.get("detail", ""))
        if detail.startswith("auto:") or detail.startswith("explicit:"):
            return True
    return False


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _parse_bool(value: Any) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "pass", "passed"}


def _parse_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _parse_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _validation_has_drawdown_failure(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    for row in _read_csv_rows(path):
        fields = " ".join(
            str(row.get(name, ""))
            for name in ("reason", "failed_metric", "suggested_action", "parameter_hints")
        ).lower()
        if "drawdown" in fields or "max_drawdown" in fields:
            return True
    return False


def _best_sweep_result_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def score(row: dict[str, Any]) -> tuple[int, int]:
        try:
            delta = int(float(str(row.get("failed_delta", "0")).strip()))
        except ValueError:
            delta = 0
        status_rank = {"IMPROVED": 0, "UNCHANGED": 1, "SKIPPED": 2, "REGRESSED": 3}.get(
            str(row.get("status", "")).strip().upper(),
            4,
        )
        return (delta, status_rank)

    return min(rows, key=score)


def _split_bias_reasons(value: str) -> list[str]:
    return [part.strip() for part in str(value).replace("|", ";").split(";") if part.strip()]


def _escape_markdown_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
