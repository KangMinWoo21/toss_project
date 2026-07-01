from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceMetrics:
    net_total_return_pct: float
    net_cagr_pct: float
    max_drawdown_abs_pct: float
    risk_adjusted_return: float
    sharpe_ratio: float = 0.0


@dataclass(frozen=True)
class ObjectiveEvaluation:
    engine_status: str
    objective_status: str
    core_conditions_passed: bool
    risk_adjusted_passed: bool
    reasons: str


def max_drawdown_abs_pct(value: float) -> float:
    return abs(float(value))


def evaluate_objective_status(
    base: PerformanceMetrics,
    conservative: PerformanceMetrics,
    benchmark: PerformanceMetrics,
) -> ObjectiveEvaluation:
    reasons: list[str] = []
    if base.net_cagr_pct <= benchmark.net_cagr_pct:
        reasons.append("net_cagr_not_above_benchmark")
    if base.max_drawdown_abs_pct > benchmark.max_drawdown_abs_pct:
        reasons.append("max_drawdown_abs_pct_worse_than_benchmark")
    if conservative.net_total_return_pct <= benchmark.net_total_return_pct:
        reasons.append("conservative_net_total_return_not_above_benchmark")
    core_passed = not reasons
    risk_passed = base.risk_adjusted_return >= benchmark.risk_adjusted_return
    if not risk_passed:
        reasons.append("risk_adjusted_return_below_benchmark")
    if core_passed and risk_passed:
        status = "COMPLETE"
    elif core_passed:
        status = "REVIEW"
    else:
        status = "NOT_COMPLETE"
    return ObjectiveEvaluation(
        engine_status="SUCCESS",
        objective_status=status,
        core_conditions_passed=core_passed,
        risk_adjusted_passed=risk_passed,
        reasons=";".join(reasons) if reasons else "beats_benchmark_after_costs_and_tax",
    )
