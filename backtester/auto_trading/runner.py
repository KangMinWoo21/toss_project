from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .benchmark import BenchmarkMetrics, load_benchmark_metrics
from .costs import (
    BASE_COST_SCENARIO,
    CONSERVATIVE_COST_SCENARIO,
    CostScenario,
    TaxConfig,
    TaxTrade,
    buy_fill_price,
    compute_capital_gains_tax_usd,
    sell_fill_price,
    trade_cost_usd,
)
from .external_data import ExternalDataBundle, estimate_liquidity_impact, load_external_data_bundle
from .gates import ObjectiveEvaluation, PerformanceMetrics, evaluate_objective_status
from .prices import KST, PriceRow, assert_no_lookahead, load_price_history
from .universe import (
    UniverseMember,
    load_point_in_time_universe,
    load_universe,
    universe_survivorship_warning_flag,
)


RETURN_PRICE_BASIS = "adj_close"
TRADE_PRICE_BASIS = "close"
TAX_PRICE_BASIS = "trade_fill_price"
DIVIDEND_TAX_POLICY = "excluded_v1"
TAX_CONSISTENCY_WARNING = True
RISK_METRIC_POLICY = "risk_adjusted_return=calmar_pct;sharpe_ratio=annualized_daily_equity_returns"
MOMENTUM_LOOKBACK_DAYS = 189
TREND_LOOKBACK_DAYS = 250
TOP_N = 1
TARGET_EXPOSURE = 0.35
REBALANCE_INTERVAL_DAYS = 42
PAPER_FLAGS = {
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


@dataclass(frozen=True)
class AutoPaperRunResult:
    engine_status: str
    objective_status: str
    output_dir: Path
    performance_path: Path
    comparison_path: Path
    order_plan_path: Path
    audit_log_path: Path
    model_config_path: Path
    cost_policy_path: Path
    candidate_sweep_path: Path
    validation_scenarios_path: Path
    validation_audit_path: Path


@dataclass(frozen=True)
class ScenarioResult:
    scenario: CostScenario
    performance: PerformanceMetrics
    tax_usd: float
    trade_cost_usd: float
    turnover_value_usd: float


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    momentum_lookback_days: int
    trend_lookback_days: int
    top_n: int
    target_exposure: float
    rebalance_interval_days: int
    volatility_target_symbol: str = ""
    volatility_lookback_days: int = 0
    target_annual_volatility: float = 0.0
    volatility_min_scale: float = 0.0
    volatility_max_scale: float = 1.0


@dataclass(frozen=True)
class CandidateEvaluation:
    strategy: StrategyConfig
    base_result: ScenarioResult
    conservative_result: ScenarioResult
    engine_status: str
    objective_status: str
    reasons: str
    best_model: bool = False


DEFAULT_STRATEGY = StrategyConfig(
    name="momentum_cash_guard_v1",
    momentum_lookback_days=MOMENTUM_LOOKBACK_DAYS,
    trend_lookback_days=TREND_LOOKBACK_DAYS,
    top_n=TOP_N,
    target_exposure=TARGET_EXPOSURE,
    rebalance_interval_days=REBALANCE_INTERVAL_DAYS,
)

DEFAULT_CANDIDATE_GRID = [
    DEFAULT_STRATEGY,
    StrategyConfig("momentum_cash_guard_m84_t70_top1_exp13_reb70", 84, 70, 1, 0.13, 70),
    StrategyConfig(
        "momentum_cash_guard_vol_spy42_tvol12_floor80_m84_t70_top1_exp18_reb70",
        84,
        70,
        1,
        0.18,
        70,
        volatility_target_symbol="SPY",
        volatility_lookback_days=42,
        target_annual_volatility=0.12,
        volatility_min_scale=0.80,
        volatility_max_scale=1.00,
    ),
    StrategyConfig(
        "momentum_cash_guard_vol_spy21_tvol10_floor75_cap105_m84_t70_top1_exp18_reb70",
        84,
        70,
        1,
        0.18,
        70,
        volatility_target_symbol="SPY",
        volatility_lookback_days=21,
        target_annual_volatility=0.10,
        volatility_min_scale=0.75,
        volatility_max_scale=1.05,
    ),
    StrategyConfig("momentum_cash_guard_m70_t84_top1_exp20_reb75", 70, 84, 1, 0.20, 75),
    StrategyConfig("momentum_cash_guard_m84_t70_top1_exp18_reb70", 84, 70, 1, 0.18, 70),
    StrategyConfig("momentum_cash_guard_m84_t84_top1_exp16_reb70", 84, 84, 1, 0.16, 70),
    StrategyConfig("momentum_cash_guard_m70_t84_top1_exp30_reb75", 70, 84, 1, 0.30, 75),
    StrategyConfig("momentum_cash_guard_m70_t84_top1_exp27_reb75", 70, 84, 1, 0.27, 75),
    StrategyConfig("momentum_cash_guard_m70_t84_top1_exp25_reb75", 70, 84, 1, 0.25, 75),
    StrategyConfig("momentum_cash_guard_m210_t200_top2_exp45_reb63", 210, 200, 2, 0.45, 63),
    StrategyConfig("momentum_cash_guard_m210_t210_top2_exp45_reb63", 210, 210, 2, 0.45, 63),
    StrategyConfig("momentum_cash_guard_m200_t175_top2_exp45_reb50", 200, 175, 2, 0.45, 50),
    StrategyConfig("momentum_cash_guard_m189_t225_top1_exp30_reb63", 189, 225, 1, 0.30, 63),
    StrategyConfig("momentum_cash_guard_m210_t200_top1_exp35_reb63", 210, 200, 1, 0.35, 63),
    StrategyConfig("momentum_cash_guard_m210_t225_top2_exp45_reb63", 210, 225, 2, 0.45, 63),
    StrategyConfig("momentum_cash_guard_m189_t250_top3_exp45_reb42", 189, 250, 3, 0.45, 42),
    StrategyConfig("momentum_cash_guard_m126_t250_top3_exp45_reb42", 126, 250, 3, 0.45, 42),
    StrategyConfig("momentum_cash_guard_m126_t250_top2_exp35_reb42", 126, 250, 2, 0.35, 42),
    StrategyConfig("momentum_cash_guard_m252_t150_top2_exp35_reb21", 252, 150, 2, 0.35, 21),
    StrategyConfig("momentum_cash_guard_m252_t150_top4_exp55_reb21", 252, 150, 4, 0.55, 21),
    StrategyConfig("momentum_cash_guard_m252_t250_top1_exp25_reb42", 252, 250, 1, 0.25, 42),
    StrategyConfig("momentum_cash_guard_m189_t200_top2_exp35_reb42", 189, 200, 2, 0.35, 42),
]


def run_auto_paper_run(
    *,
    prices_dir: Path | str,
    universe_path: Path | str,
    benchmark_report: Path | str,
    benchmark_row_selector: str,
    output_dir: Path | str,
    usd_krw_rate: float = 1400.0,
    initial_cash_usd: float = 100_000.0,
    decision_time_kst: datetime | None = None,
    external_data_dir: Path | str | None = None,
    universe_as_of: str | None = None,
) -> AutoPaperRunResult:
    universe_mode = "point_in_time" if universe_as_of else "current"
    members = (
        load_point_in_time_universe(universe_path, as_of=universe_as_of)
        if universe_as_of
        else load_universe(universe_path)
    )
    histories = load_price_history(Path(prices_dir), [member.symbol for member in members])
    external_data = (
        load_external_data_bundle(external_data_dir, [member.symbol for member in members])
        if external_data_dir
        else ExternalDataBundle.empty()
    )
    effective_decision_time = decision_time_kst or datetime.now(KST)
    for rows in histories.values():
        assert_no_lookahead(rows, effective_decision_time)
    benchmark = load_benchmark_metrics(benchmark_report, row_selector=benchmark_row_selector)
    tax_config = TaxConfig(usd_krw_rate=float(usd_krw_rate))

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    performance_path = output_root / "auto_paper_performance.csv"
    comparison_path = output_root / "auto_paper_comparison.md"
    order_plan_path = output_root / "auto_paper_order_plan.csv"
    audit_log_path = output_root / "auto_paper_audit_log.json"
    model_config_path = output_root / "auto_paper_model_config.json"
    cost_policy_path = output_root / "auto_paper_cost_policy.md"
    candidate_sweep_path = output_root / "auto_paper_candidate_sweep.csv"
    validation_scenarios_path = output_root / "auto_paper_validation_scenarios.csv"
    validation_audit_path = output_root / "auto_paper_validation_audit.csv"

    candidate_evaluations = _evaluate_candidate_grid(
        members,
        histories,
        tax_config,
        benchmark,
        initial_cash_usd,
    )
    validation_cache: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]] = {}
    validation_pass_by_strategy: dict[str, bool] = {}
    concentration_ratio_by_strategy: dict[str, float] = {}
    for candidate in candidate_evaluations:
        rows = _monthly_style_validation_rows(
            members,
            histories,
            tax_config,
            benchmark,
            initial_cash_usd,
            candidate.strategy,
        )
        audit_rows = _monthly_style_validation_audit(rows)
        validation_cache[candidate.strategy.name] = (rows, audit_rows)
        validation_pass_by_strategy[candidate.strategy.name] = _validation_hard_gates_pass(audit_rows)
        concentration_ratio_by_strategy[candidate.strategy.name] = _validation_concentration_ratio(audit_rows)

    best_evaluation = _select_best_candidate(
        candidate_evaluations,
        validation_pass_by_strategy=validation_pass_by_strategy,
        concentration_ratio_by_strategy=concentration_ratio_by_strategy,
    )
    base_result = best_evaluation.base_result
    conservative_result = best_evaluation.conservative_result
    evaluation = evaluate_objective_status(
        base_result.performance,
        conservative_result.performance,
        benchmark.performance,
    )
    validation_rows, validation_audit_rows = validation_cache[best_evaluation.strategy.name]
    evaluation = _apply_validation_audit_to_objective(evaluation, validation_audit_rows)

    performance_rows = _performance_rows(
        [base_result, conservative_result],
        benchmark,
        evaluation.engine_status,
        evaluation.objective_status,
        members,
        best_evaluation.strategy,
        universe_mode,
        universe_as_of or "",
    )
    _write_csv(performance_path, performance_rows)
    _write_csv(
        candidate_sweep_path,
        _candidate_sweep_rows(
            candidate_evaluations,
            best_evaluation.strategy.name,
            benchmark,
            validation_pass_by_strategy=validation_pass_by_strategy,
            concentration_ratio_by_strategy=concentration_ratio_by_strategy,
            validation_cache=validation_cache,
        ),
    )
    _write_csv(validation_scenarios_path, validation_rows)
    _write_csv(validation_audit_path, validation_audit_rows)
    order_rows = _order_plan_rows(members, histories, initial_cash_usd, benchmark.report_sha256, external_data)
    _write_csv(order_plan_path, order_rows)
    audit = _audit_log(
        prices_dir=Path(prices_dir),
        universe_path=Path(universe_path),
        benchmark_report=Path(benchmark_report),
        benchmark=benchmark,
        tax_config=tax_config,
        members=members,
        evaluation=evaluation,
        best_strategy=best_evaluation.strategy,
        validation_scenarios_path=validation_scenarios_path,
        validation_audit_path=validation_audit_path,
        validation_audit_rows=validation_audit_rows,
        external_data_dir=Path(external_data_dir) if external_data_dir else None,
        external_data=external_data,
        universe_mode=universe_mode,
        universe_as_of=universe_as_of or "",
    )
    audit_log_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    model_config_path.write_text(
        json.dumps(
            _model_config(
                benchmark=benchmark,
                tax_config=tax_config,
                best_strategy=best_evaluation.strategy,
                evaluation=evaluation,
            ),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    cost_policy_path.write_text(_cost_policy_markdown(tax_config), encoding="utf-8")
    comparison_path.write_text(
        _comparison_markdown(benchmark, base_result, conservative_result, evaluation.objective_status, evaluation.reasons),
        encoding="utf-8",
    )
    return AutoPaperRunResult(
        engine_status=evaluation.engine_status,
        objective_status=evaluation.objective_status,
        output_dir=output_root,
        performance_path=performance_path,
        comparison_path=comparison_path,
        order_plan_path=order_plan_path,
        audit_log_path=audit_log_path,
        model_config_path=model_config_path,
        cost_policy_path=cost_policy_path,
        candidate_sweep_path=candidate_sweep_path,
        validation_scenarios_path=validation_scenarios_path,
        validation_audit_path=validation_audit_path,
    )


def _evaluate_candidate_grid(
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    tax_config: TaxConfig,
    benchmark: BenchmarkMetrics,
    initial_cash_usd: float,
) -> list[CandidateEvaluation]:
    evaluations: list[CandidateEvaluation] = []
    for strategy in DEFAULT_CANDIDATE_GRID:
        base_result = _simulate_momentum_cash_guard(
            members,
            histories,
            BASE_COST_SCENARIO,
            tax_config,
            initial_cash_usd,
            strategy,
        )
        conservative_result = _simulate_momentum_cash_guard(
            members,
            histories,
            CONSERVATIVE_COST_SCENARIO,
            tax_config,
            initial_cash_usd,
            strategy,
        )
        objective = evaluate_objective_status(base_result.performance, conservative_result.performance, benchmark.performance)
        evaluations.append(
            CandidateEvaluation(
                strategy=strategy,
                base_result=base_result,
                conservative_result=conservative_result,
                engine_status=objective.engine_status,
                objective_status=objective.objective_status,
                reasons=objective.reasons,
            )
        )
    return evaluations


def _select_best_candidate(
    evaluations: list[CandidateEvaluation],
    *,
    validation_pass_by_strategy: dict[str, bool] | None = None,
    concentration_ratio_by_strategy: dict[str, float] | None = None,
) -> CandidateEvaluation:
    if not evaluations:
        raise ValueError("candidate grid produced no evaluations")

    def score(evaluation: CandidateEvaluation) -> tuple[int, float, float, float]:
        validation_rank = 1 if (validation_pass_by_strategy or {}).get(evaluation.strategy.name, False) else 0
        status_rank = {"COMPLETE": 2, "REVIEW": 1, "NOT_COMPLETE": 0}.get(evaluation.objective_status, -1)
        performance = evaluation.conservative_result.performance
        ratio = (concentration_ratio_by_strategy or {}).get(evaluation.strategy.name, float("inf"))
        return (
            validation_rank,
            status_rank,
            -ratio,
            performance.risk_adjusted_return,
            performance.net_total_return_pct,
            -performance.max_drawdown_abs_pct,
        )

    best = max(evaluations, key=score)
    return CandidateEvaluation(
        strategy=best.strategy,
        base_result=best.base_result,
        conservative_result=best.conservative_result,
        engine_status=best.engine_status,
        objective_status=best.objective_status,
        reasons=best.reasons,
        best_model=True,
    )


def _apply_validation_audit_to_objective(
    evaluation: ObjectiveEvaluation,
    validation_audit_rows: list[dict[str, str]],
) -> ObjectiveEvaluation:
    blocking = [row for row in validation_audit_rows if row.get("status") == "BLOCK"]
    concentration_warn = [
        row for row in validation_audit_rows
        if row.get("name") == "return_concentration" and row.get("status") == "WARN"
    ]
    review_reasons = []
    if blocking:
        review_reasons.append("monthly_style_validation_block=" + ";".join(row.get("name", "unknown") for row in blocking))
    if concentration_warn:
        review_reasons.append("monthly_style_validation_warn=return_concentration")
    if not review_reasons or evaluation.objective_status != "COMPLETE":
        return evaluation
    if blocking:
        return ObjectiveEvaluation(
            engine_status=evaluation.engine_status,
            objective_status="NOT_COMPLETE",
            core_conditions_passed=False,
            risk_adjusted_passed=evaluation.risk_adjusted_passed,
            reasons=f"{evaluation.reasons};" + ";".join(review_reasons),
        )
    return ObjectiveEvaluation(
        engine_status=evaluation.engine_status,
        objective_status="REVIEW",
        core_conditions_passed=evaluation.core_conditions_passed,
        risk_adjusted_passed=evaluation.risk_adjusted_passed,
        reasons=f"{evaluation.reasons};" + ";".join(review_reasons),
    )


def _validation_hard_gates_pass(validation_audit_rows: list[dict[str, str]]) -> bool:
    required = {
        "required_scenarios": "PASS",
        "required_net_total": "PASS",
        "walk_forward_margin": "PASS",
        "trade_activity": "PASS",
    }
    status_by_name = {row.get("name", ""): row.get("status", "") for row in validation_audit_rows}
    return all(status_by_name.get(name) == status for name, status in required.items())


def _validation_concentration_ratio(validation_audit_rows: list[dict[str, str]]) -> float:
    row = next((item for item in validation_audit_rows if item.get("name") == "return_concentration"), None)
    if row is None:
        return float("inf")
    detail = row.get("detail", "")
    marker = "ratio="
    if marker not in detail:
        return float("inf")
    try:
        return float(detail.split(marker, 1)[1].split(";", 1)[0])
    except ValueError:
        return float("inf")


def _monthly_style_validation_rows(
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    tax_config: TaxConfig,
    benchmark: BenchmarkMetrics,
    initial_cash_usd: float,
    strategy: StrategyConfig,
) -> list[dict[str, str]]:
    common_dates = _common_dates(histories)
    rows: list[dict[str, str]] = []
    rows.append(
        _validation_result_row(
            name="full_period",
            category="duration",
            required=True,
            histories=histories,
            members=members,
            strategy=strategy,
            scenario=CONSERVATIVE_COST_SCENARIO,
            tax_config=tax_config,
            benchmark=benchmark,
            initial_cash_usd=initial_cash_usd,
        )
    )
    for name, fraction in (("latest_30pct", 0.70), ("latest_20pct", 0.80)):
        start_index = min(int(len(common_dates) * fraction), max(len(common_dates) - 1, 0))
        sliced = _slice_histories(histories, start=common_dates[start_index], end=None)
        rows.append(
            _validation_result_row(
                name=name,
                category="duration",
                required=True,
                histories=sliced,
                members=members,
                strategy=strategy,
                scenario=CONSERVATIVE_COST_SCENARIO,
                tax_config=tax_config,
                benchmark=benchmark,
                initial_cash_usd=initial_cash_usd,
            )
        )
    for multiplier in (2.0, 3.0):
        scenario = CostScenario(
            name=f"conservative_slippage_x{int(multiplier)}",
            fee_rate=CONSERVATIVE_COST_SCENARIO.fee_rate,
            slippage_rate=CONSERVATIVE_COST_SCENARIO.slippage_rate * multiplier,
            fx_buffer_rate=CONSERVATIVE_COST_SCENARIO.fx_buffer_rate,
        )
        rows.append(
            _validation_result_row(
                name=f"stress_slippage_x{int(multiplier)}",
                category="stress",
                required=True,
                histories=histories,
                members=members,
                strategy=strategy,
                scenario=scenario,
                tax_config=tax_config,
                benchmark=benchmark,
                initial_cash_usd=initial_cash_usd,
                stress=f"slippage_x{int(multiplier)}",
                slippage_multiplier=multiplier,
            )
        )
    rows.extend(
        _walk_forward_validation_rows(
            members,
            histories,
            tax_config,
            benchmark,
            initial_cash_usd,
            strategy,
        )
    )
    return rows


def _walk_forward_validation_rows(
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    tax_config: TaxConfig,
    benchmark: BenchmarkMetrics,
    initial_cash_usd: float,
    strategy: StrategyConfig,
) -> list[dict[str, str]]:
    common_dates = _common_dates(histories)
    train_size = 756
    test_size = 252
    if len(common_dates) < train_size + test_size:
        return []
    rows: list[dict[str, str]] = []
    last_start = len(common_dates) - test_size
    starts = [last_start - test_size * offset for offset in range(4, -1, -1)]
    for index, test_start_index in enumerate(starts, start=1):
        if test_start_index < train_size:
            continue
        train_start = common_dates[test_start_index - train_size]
        train_end = common_dates[test_start_index - 1]
        test_start = common_dates[test_start_index]
        test_end = common_dates[min(test_start_index + test_size - 1, len(common_dates) - 1)]
        train_histories = _slice_histories(histories, start=train_start, end=train_end)
        test_histories = _slice_histories(histories, start=test_start, end=test_end)
        train_evaluations = [
            _evaluate_strategy_for_validation(strategy, members, train_histories, tax_config, benchmark, initial_cash_usd)
        ]
        selected = train_evaluations[0]
        row = _validation_result_row(
            name=f"walk_forward_{index:03d}",
            category="walk_forward",
            required=True,
            histories=test_histories,
            members=members,
            strategy=strategy,
            scenario=CONSERVATIVE_COST_SCENARIO,
            tax_config=tax_config,
            benchmark=benchmark,
            initial_cash_usd=initial_cash_usd,
        )
        row["train_start"] = train_start
        row["train_end"] = train_end
        row["selected_preset"] = strategy.name
        row["train_net_total_return_pct"] = selected["net_total_return_pct"]
        row["train_candidate_scores"] = _format_validation_train_scores(train_evaluations)
        if selected["deployable"] != "True":
            row["deployable"] = "False"
            row["reason"] = "train_window_rejected"
        rows.append(row)
    return rows


def _evaluate_strategy_for_validation(
    strategy: StrategyConfig,
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    tax_config: TaxConfig,
    benchmark: BenchmarkMetrics,
    initial_cash_usd: float,
) -> dict[str, str]:
    return _validation_result_row(
        name="train",
        category="train",
        required=False,
        histories=histories,
        members=members,
        strategy=strategy,
        scenario=CONSERVATIVE_COST_SCENARIO,
        tax_config=tax_config,
        benchmark=benchmark,
        initial_cash_usd=initial_cash_usd,
    )


def _validation_result_row(
    *,
    name: str,
    category: str,
    required: bool,
    histories: dict[str, list[PriceRow]],
    members: list[UniverseMember],
    strategy: StrategyConfig,
    scenario: CostScenario,
    tax_config: TaxConfig,
    benchmark: BenchmarkMetrics,
    initial_cash_usd: float,
    stress: str = "",
    slippage_multiplier: float = 1.0,
) -> dict[str, str]:
    result = _simulate_momentum_cash_guard(members, histories, scenario, tax_config, initial_cash_usd, strategy)
    performance = result.performance
    dates = _common_dates(histories)
    if len(dates) <= max(strategy.momentum_lookback_days, strategy.trend_lookback_days):
        deployable, reason = True, "observation_only_insufficient_history"
    else:
        deployable, reason = _validation_deployable(performance, benchmark, result.turnover_value_usd)
    return {
        "name": name,
        "category": category,
        "required": str(required),
        "train_start": "",
        "train_end": "",
        "selected_preset": strategy.name,
        "train_net_total_return_pct": "",
        "train_candidate_scores": "",
        "start": dates[0],
        "end": dates[-1],
        "slippage_multiplier": _fmt(slippage_multiplier),
        "stress": stress,
        "strategy_name": strategy.name,
        "net_total_return_pct": _fmt(performance.net_total_return_pct),
        "net_cagr_pct": _fmt(performance.net_cagr_pct),
        "max_drawdown_abs_pct": _fmt(performance.max_drawdown_abs_pct),
        "risk_adjusted_return": _fmt(performance.risk_adjusted_return),
        "sharpe_ratio": _fmt(performance.sharpe_ratio),
        "risk_metric_policy": RISK_METRIC_POLICY,
        **_strategy_volatility_fields(strategy),
        "trade_activity_usd": _fmt(result.turnover_value_usd),
        "deployable": str(deployable),
        "reason": reason,
        "benchmark_report_sha256": benchmark.report_sha256,
        "return_price_basis": RETURN_PRICE_BASIS,
        "trade_price_basis": TRADE_PRICE_BASIS,
        "tax_price_basis": TAX_PRICE_BASIS,
        "dividend_tax_policy": DIVIDEND_TAX_POLICY,
        "tax_consistency_warning": str(TAX_CONSISTENCY_WARNING),
        **PAPER_FLAGS,
    }


def _validation_deployable(
    performance: PerformanceMetrics,
    benchmark: BenchmarkMetrics,
    turnover_value_usd: float,
) -> tuple[bool, str]:
    if performance.net_total_return_pct <= 0:
        return False, "negative_or_zero_net_total_return"
    if performance.max_drawdown_abs_pct > benchmark.performance.max_drawdown_abs_pct:
        return False, "max_drawdown_abs_pct_worse_than_benchmark"
    if turnover_value_usd <= 0:
        return False, "zero_trade_activity"
    return True, "passed"


def _monthly_style_validation_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    required = [row for row in rows if row.get("required") == "True"]
    failed = [row for row in required if row.get("deployable") != "True"]
    audit = [
        {
            "name": "required_scenarios",
            "status": "BLOCK" if failed else "PASS",
            "detail": f"{len(failed)} failed of {len(required)} required",
        }
    ]
    scorable_required = [row for row in required if row.get("reason") != "observation_only_insufficient_history"]
    net_returns = [_float(row.get("net_total_return_pct")) for row in scorable_required]
    net_returns = [value for value in net_returns if value is not None]
    if net_returns:
        minimum = min(net_returns)
        audit.append(
            {
                "name": "required_net_total",
                "status": "BLOCK" if minimum <= 0 else "PASS",
                "detail": f"min_required_net_total_return_pct={minimum:.4f}",
            }
        )
    else:
        audit.append({"name": "required_net_total", "status": "BLOCK", "detail": "no numeric required net total return"})
    walk_returns = [
        _float(row.get("net_total_return_pct"))
        for row in scorable_required
        if row.get("category") == "walk_forward"
    ]
    walk_returns = [value for value in walk_returns if value is not None]
    if not walk_returns:
        audit.append({"name": "walk_forward_margin", "status": "WARN", "detail": "no walk-forward net return values"})
    else:
        minimum = min(walk_returns)
        audit.append(
            {
                "name": "walk_forward_margin",
                "status": "BLOCK" if minimum <= 0 else "PASS",
                "detail": f"min_walk_forward_net_total_return_pct={minimum:.4f}",
            }
        )
    drawdowns = [_float(row.get("max_drawdown_abs_pct")) for row in scorable_required]
    drawdowns = [value for value in drawdowns if value is not None]
    if drawdowns:
        worst = max(drawdowns)
        audit.append(
            {
                "name": "drawdown_buffer",
                "status": "BLOCK" if worst > 25.0 else "WARN" if worst >= 20.0 else "PASS",
                "detail": f"worst_max_drawdown_abs_pct={worst:.4f}; warn_at_or_above=20.0000; block_above=25.0000",
            }
        )
    else:
        audit.append({"name": "drawdown_buffer", "status": "BLOCK", "detail": "no numeric drawdown values"})
    full = next((_float(row.get("net_total_return_pct")) for row in rows if row.get("name") == "full_period"), None)
    positive_walk = [value for value in walk_returns if value > 0]
    if full is None or not positive_walk:
        audit.append({"name": "return_concentration", "status": "WARN", "detail": "insufficient full/walk-forward net return values"})
    else:
        walk_median = sorted(positive_walk)[len(positive_walk) // 2]
        ratio = full / walk_median if walk_median > 0 else float("inf")
        audit.append(
            {
                "name": "return_concentration",
                "status": "WARN" if ratio > 20.0 else "PASS",
                "detail": f"full_net_total_return_pct={full:.4f}; median_walk_forward_net_total_return_pct={walk_median:.4f}; ratio={ratio:.4f}; warn_above=20.0000",
            }
        )
    zero_trade = [
        row.get("name", "unknown")
        for row in required
        if (_float(row.get("trade_activity_usd")) or 0.0) <= 0
        and row.get("reason") != "observation_only_insufficient_history"
    ]
    audit.append(
        {
            "name": "trade_activity",
            "status": "BLOCK" if zero_trade else "PASS",
            "detail": "zero_trade_scenarios=" + ",".join(zero_trade[:10]) if zero_trade else f"{len(required)} required scenarios traded",
        }
    )
    return audit


def _common_dates(histories: dict[str, list[PriceRow]]) -> list[str]:
    return sorted(set.intersection(*(set(row.bar_date for row in rows) for rows in histories.values())))


def _slice_histories(
    histories: dict[str, list[PriceRow]],
    *,
    start: str | None,
    end: str | None,
) -> dict[str, list[PriceRow]]:
    sliced = {
        symbol: [
            row for row in rows
            if (start is None or row.bar_date >= start) and (end is None or row.bar_date <= end)
        ]
        for symbol, rows in histories.items()
    }
    if any(not rows for rows in sliced.values()):
        raise ValueError("validation slice produced empty price history")
    return sliced


def _format_validation_train_scores(rows: list[dict[str, str]]) -> str:
    parts = []
    for row in rows:
        parts.append(
            f"{row['strategy_name']}:net={row['net_total_return_pct']},"
            f"mdd={row['max_drawdown_abs_pct']},risk={row['risk_adjusted_return']},"
            f"deployable={row['deployable']}"
        )
    return " | ".join(parts)


def _float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _simulate_momentum_cash_guard(
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    scenario: CostScenario,
    tax_config: TaxConfig,
    initial_cash_usd: float,
    strategy: StrategyConfig,
) -> ScenarioResult:
    cash = float(initial_cash_usd)
    positions: dict[str, int] = {}
    tax_trades: list[TaxTrade] = []
    total_trade_cost = 0.0
    turnover = 0.0
    symbols = [member.symbol for member in members]
    positions = {symbol: 0 for symbol in symbols}
    common_dates = sorted(set.intersection(*(set(row.bar_date for row in rows) for rows in histories.values())))
    rows_by_symbol = {
        symbol: {row.bar_date: row for row in rows}
        for symbol, rows in histories.items()
    }
    close_history: dict[str, list[float]] = {symbol: [] for symbol in symbols}
    equity_curve: list[float] = []
    last_rebalance_index = -10_000

    for index, bar_date in enumerate(common_dates):
        for symbol in symbols:
            close_history[symbol].append(rows_by_symbol[symbol][bar_date].adj_close)
        equity_curve.append(_portfolio_value(cash, positions, rows_by_symbol, bar_date, adjusted=True))
        if index < max(strategy.momentum_lookback_days, strategy.trend_lookback_days):
            continue
        if index - last_rebalance_index < strategy.rebalance_interval_days:
            continue
        targets = _momentum_cash_guard_targets(symbols, close_history, index, strategy)
        cash, total_trade_cost, turnover = _rebalance_positions(
            bar_date,
            cash,
            positions,
            targets,
            rows_by_symbol,
            scenario,
            tax_trades,
            total_trade_cost,
            turnover,
        )
        last_rebalance_index = index

    final_date = common_dates[-1]
    for member in members:
        quantity = positions.get(member.symbol, 0)
        if quantity <= 0:
            continue
        last = rows_by_symbol[member.symbol][final_date]
        fill = sell_fill_price(last.close, scenario)
        gross = fill * quantity
        cost = trade_cost_usd(gross, scenario)
        cash += gross - cost
        total_trade_cost += cost
        turnover += gross
        tax_trades.append(TaxTrade(last.bar_date, member.symbol, "SELL", quantity, fill))
    tax_usd = compute_capital_gains_tax_usd(tax_trades, tax_config)
    final_equity = cash - tax_usd
    equity_curve.append(final_equity)

    total_return_pct = (final_equity / initial_cash_usd - 1.0) * 100.0
    start = min(rows[0].bar_date for rows in histories.values())
    end = max(rows[-1].bar_date for rows in histories.values())
    cagr_pct = _cagr_pct(initial_cash_usd, final_equity, start, end)
    max_drawdown = _max_drawdown_abs_pct(equity_curve)
    sharpe_ratio = _annualized_sharpe(equity_curve)
    return ScenarioResult(
        scenario=scenario,
        performance=PerformanceMetrics(
            net_total_return_pct=total_return_pct,
            net_cagr_pct=cagr_pct,
            max_drawdown_abs_pct=max_drawdown,
            risk_adjusted_return=_calmar_pct(cagr_pct, max_drawdown),
            sharpe_ratio=sharpe_ratio,
        ),
        tax_usd=tax_usd,
        trade_cost_usd=total_trade_cost,
        turnover_value_usd=turnover,
    )


def _momentum_cash_guard_targets(
    symbols: list[str],
    close_history: dict[str, list[float]],
    index: int,
    strategy: StrategyConfig,
) -> dict[str, float]:
    spy = close_history["SPY"]
    qqq = close_history["QQQ"]
    spy_trend = spy[-1] > _average(spy[-strategy.trend_lookback_days:])
    qqq_trend = qqq[-1] > _average(qqq[-strategy.trend_lookback_days:])
    if not (spy_trend and qqq_trend):
        return {symbol: 0.0 for symbol in symbols}
    scores = []
    for symbol in symbols:
        history = close_history[symbol]
        previous = history[-strategy.momentum_lookback_days - 1]
        score = history[-1] / previous - 1.0 if previous > 0 else -1.0
        scores.append((score, symbol))
    selected = {symbol for _score, symbol in sorted(scores, reverse=True)[: strategy.top_n]}
    targets = {
        symbol: (strategy.target_exposure / strategy.top_n if symbol in selected else 0.0)
        for symbol in symbols
    }
    return _apply_volatility_targeting(targets, close_history, strategy)


def _apply_volatility_targeting(
    targets: dict[str, float],
    close_history: dict[str, list[float]],
    strategy: StrategyConfig,
) -> dict[str, float]:
    if (
        not strategy.volatility_target_symbol
        or strategy.volatility_lookback_days <= 1
        or strategy.target_annual_volatility <= 0
        or not any(weight > 0 for weight in targets.values())
    ):
        return targets
    history = close_history.get(strategy.volatility_target_symbol.upper())
    if not history:
        return targets
    realized = _realized_annual_volatility(history, strategy.volatility_lookback_days)
    if realized <= 0:
        return targets
    scale = strategy.target_annual_volatility / realized
    scale = max(strategy.volatility_min_scale, min(strategy.volatility_max_scale, scale))
    return {symbol: weight * scale for symbol, weight in targets.items()}


def _normalized_weights(members: list[UniverseMember]) -> dict[str, float]:
    total = sum(max(member.target_weight, 0.0) for member in members)
    if total <= 0:
        equal = 1.0 / len(members)
        return {member.symbol: equal for member in members}
    return {member.symbol: max(member.target_weight, 0.0) / total for member in members}


def _rebalance_positions(
    bar_date: str,
    cash: float,
    positions: dict[str, int],
    targets: dict[str, float],
    rows_by_symbol: dict[str, dict[str, PriceRow]],
    scenario: CostScenario,
    tax_trades: list[TaxTrade],
    total_trade_cost: float,
    turnover: float,
) -> tuple[float, float, float]:
    value = _portfolio_value(cash, positions, rows_by_symbol, bar_date, adjusted=False)
    for symbol, current_quantity in list(positions.items()):
        target_quantity = int(value * targets.get(symbol, 0.0) / rows_by_symbol[symbol][bar_date].close)
        if current_quantity <= target_quantity:
            continue
        quantity = current_quantity - target_quantity
        fill = sell_fill_price(rows_by_symbol[symbol][bar_date].close, scenario)
        gross = quantity * fill
        cost = trade_cost_usd(gross, scenario)
        cash += gross - cost
        total_trade_cost += cost
        turnover += gross
        positions[symbol] -= quantity
        tax_trades.append(TaxTrade(bar_date, symbol, "SELL", quantity, fill))

    value = _portfolio_value(cash, positions, rows_by_symbol, bar_date, adjusted=False)
    for symbol, current_quantity in list(positions.items()):
        target_quantity = int(value * targets.get(symbol, 0.0) / rows_by_symbol[symbol][bar_date].close)
        if current_quantity >= target_quantity:
            continue
        quantity = target_quantity - current_quantity
        fill = buy_fill_price(rows_by_symbol[symbol][bar_date].close, scenario)
        gross = quantity * fill
        cost = trade_cost_usd(gross, scenario)
        if cash < gross + cost:
            quantity = int(cash / (fill * (1.0 + scenario.fee_rate + scenario.fx_buffer_rate)))
            gross = quantity * fill
            cost = trade_cost_usd(gross, scenario)
        if quantity <= 0:
            continue
        cash -= gross + cost
        total_trade_cost += cost
        turnover += gross
        positions[symbol] += quantity
        tax_trades.append(TaxTrade(bar_date, symbol, "BUY", quantity, fill))
    return cash, total_trade_cost, turnover


def _portfolio_value(
    cash: float,
    positions: dict[str, int],
    rows_by_symbol: dict[str, dict[str, PriceRow]],
    bar_date: str,
    *,
    adjusted: bool,
) -> float:
    value = cash
    for symbol, quantity in positions.items():
        row = rows_by_symbol[symbol][bar_date]
        value += quantity * (row.adj_close if adjusted else row.close)
    return value


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _realized_annual_volatility(values: list[float], lookback_days: int) -> float:
    if len(values) < lookback_days + 1:
        return 0.0
    tail = values[-lookback_days - 1:]
    returns = [
        tail[index] / tail[index - 1] - 1.0
        for index in range(1, len(tail))
        if tail[index - 1] > 0
    ]
    if len(returns) < 2:
        return 0.0
    avg = sum(returns) / len(returns)
    variance = sum((value - avg) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def _max_drawdown_abs_pct(equity_curve: list[float]) -> float:
    peak = None
    worst = 0.0
    for equity in equity_curve:
        peak = equity if peak is None else max(peak, equity)
        if peak and peak > 0:
            worst = min(worst, (equity / peak - 1.0) * 100.0)
    return abs(worst)


def _annualized_sharpe(equity_curve: list[float]) -> float:
    returns = [
        equity_curve[index] / equity_curve[index - 1] - 1.0
        for index in range(1, len(equity_curve))
        if equity_curve[index - 1] > 0
    ]
    if not returns:
        return 0.0
    avg = sum(returns) / len(returns)
    if len(returns) < 2:
        return avg * math.sqrt(252)
    variance = sum((value - avg) ** 2 for value in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return avg * math.sqrt(252)
    return avg / std * math.sqrt(252)


def _calmar_pct(cagr_pct: float, max_drawdown_abs_pct: float) -> float:
    if max_drawdown_abs_pct <= 0:
        return 999.0
    return cagr_pct / max_drawdown_abs_pct * 100.0


def _cagr_pct(initial: float, final: float, start: str, end: str) -> float:
    start_date = datetime.fromisoformat(start).date()
    end_date = datetime.fromisoformat(end).date()
    years = max((end_date - start_date).days / 365.25, 1.0 / 365.25)
    if initial <= 0 or final <= 0:
        return -100.0
    return ((final / initial) ** (1.0 / years) - 1.0) * 100.0


def _performance_rows(
    results: list[ScenarioResult],
    benchmark: BenchmarkMetrics,
    engine_status: str,
    objective_status: str,
    members: list[UniverseMember],
    strategy: StrategyConfig,
    universe_mode: str,
    universe_as_of: str,
) -> list[dict[str, str]]:
    warnings = " | ".join(sorted({member.survivorship_warning for member in members}))
    warning_flag = universe_survivorship_warning_flag(members)
    rows: list[dict[str, str]] = []
    for result in results:
        row = {
            "scenario": result.scenario.name,
            "strategy_name": strategy.name,
            "momentum_lookback_days": str(strategy.momentum_lookback_days),
            "trend_lookback_days": str(strategy.trend_lookback_days),
            "top_n": str(strategy.top_n),
            "target_exposure": _fmt(strategy.target_exposure),
            "rebalance_interval_days": str(strategy.rebalance_interval_days),
            "engine_status": engine_status,
            "objective_status": objective_status,
            "net_total_return_pct": _fmt(result.performance.net_total_return_pct),
            "net_cagr_pct": _fmt(result.performance.net_cagr_pct),
            "max_drawdown_abs_pct": _fmt(result.performance.max_drawdown_abs_pct),
            "risk_adjusted_return": _fmt(result.performance.risk_adjusted_return),
            "sharpe_ratio": _fmt(result.performance.sharpe_ratio),
            "risk_metric_policy": RISK_METRIC_POLICY,
            **_strategy_volatility_fields(strategy),
            "trade_cost_usd": _fmt(result.trade_cost_usd),
            "capital_gains_tax_usd": _fmt(result.tax_usd),
            "turnover_value_usd": _fmt(result.turnover_value_usd),
            "fee_rate": _fmt(result.scenario.fee_rate),
            "slippage_rate": _fmt(result.scenario.slippage_rate),
            "fx_buffer_rate": _fmt(result.scenario.fx_buffer_rate),
            "return_price_basis": RETURN_PRICE_BASIS,
            "trade_price_basis": TRADE_PRICE_BASIS,
            "tax_price_basis": TAX_PRICE_BASIS,
            "dividend_tax_policy": DIVIDEND_TAX_POLICY,
            "tax_consistency_warning": str(TAX_CONSISTENCY_WARNING),
            "survivorship_warning": warnings,
            "survivorship_warning_flag": str(warning_flag),
            "universe_mode": universe_mode,
            "universe_as_of": universe_as_of,
            "benchmark_report_sha256": benchmark.report_sha256,
            **PAPER_FLAGS,
        }
        rows.append(row)
    return rows


def _order_plan_rows(
    members: list[UniverseMember],
    histories: dict[str, list[PriceRow]],
    initial_cash_usd: float,
    benchmark_report_sha256: str,
    external_data: ExternalDataBundle | None = None,
) -> list[dict[str, str]]:
    weights = _normalized_weights(members)
    external_bundle = external_data or ExternalDataBundle.empty()
    rows: list[dict[str, str]] = []
    for member in members:
        latest = histories[member.symbol][-1]
        quantity = int(initial_cash_usd * weights[member.symbol] / latest.close)
        estimated_value = quantity * latest.close
        impact = estimate_liquidity_impact(
            symbol=member.symbol,
            order_value_usd=estimated_value,
            average_daily_dollar_volume=_average_daily_dollar_volume(histories[member.symbol]),
            annualized_volatility=_realized_annual_volatility(
                [row.close for row in histories[member.symbol]],
                min(21, max(2, len(histories[member.symbol]) - 1)),
            ),
            bundle=external_bundle,
        )
        external_row = external_bundle.symbol_rows.get(member.symbol)
        rows.append(
            {
                "symbol": member.symbol,
                "side": "BUY" if quantity > 0 else "SKIP",
                "quantity": str(quantity),
                "target_weight": _fmt(weights[member.symbol]),
                "reference_price": _fmt(latest.close),
                "estimated_market_impact_rate": _fmt(impact.estimated_impact_rate),
                "estimated_market_impact_usd": _fmt(impact.estimated_impact_usd),
                "liquidity_source": impact.liquidity_source,
                "external_data_policy": "free_local_csv_only" if external_bundle.symbol_rows else "none",
                "sector": external_row.sector if external_row else "",
                "beta": _fmt(external_row.beta) if external_row else "",
                "size_score": _fmt(external_row.size_score) if external_row else "",
                "value_score": _fmt(external_row.value_score) if external_row else "",
                "quality_score": _fmt(external_row.quality_score) if external_row else "",
                "momentum_score": _fmt(external_row.momentum_score) if external_row else "",
                "short_volume_ratio": _fmt(external_row.short_volume_ratio) if external_row else "",
                "news_article_count": str(external_row.news_article_count) if external_row else "",
                "news_sentiment_score": _fmt(external_row.news_sentiment_score) if external_row else "",
                "listing_status": external_row.listing_status if external_row else "",
                "delisted": str(external_row.delisted) if external_row else "",
                "return_price_basis": RETURN_PRICE_BASIS,
                "trade_price_basis": TRADE_PRICE_BASIS,
                "tax_price_basis": TAX_PRICE_BASIS,
                "dividend_tax_policy": DIVIDEND_TAX_POLICY,
                "tax_consistency_warning": str(TAX_CONSISTENCY_WARNING),
                "survivorship_warning": member.survivorship_warning,
                "benchmark_report_sha256": benchmark_report_sha256,
                **PAPER_FLAGS,
            }
        )
    return rows


def _average_daily_dollar_volume(rows: list[PriceRow], lookback_days: int = 20) -> float:
    recent = rows[-lookback_days:] if len(rows) > lookback_days else rows
    values = [row.close * row.volume for row in recent if row.close > 0 and row.volume > 0]
    if not values:
        return 1.0
    return sum(values) / len(values)


def _audit_log(
    *,
    prices_dir: Path,
    universe_path: Path,
    benchmark_report: Path,
    benchmark: BenchmarkMetrics,
    tax_config: TaxConfig,
    members: list[UniverseMember],
    evaluation,
    best_strategy: StrategyConfig,
    validation_scenarios_path: Path,
    validation_audit_path: Path,
    validation_audit_rows: list[dict[str, str]],
    external_data_dir: Path | None,
    external_data: ExternalDataBundle,
    universe_mode: str,
    universe_as_of: str,
) -> dict[str, object]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine_status": evaluation.engine_status,
        "objective_status": evaluation.objective_status,
        "objective_reasons": evaluation.reasons,
        "prices_dir": prices_dir.as_posix(),
        "universe": universe_path.as_posix(),
        "universe_mode": universe_mode,
        "universe_as_of": universe_as_of,
        "benchmark_report": benchmark_report.as_posix(),
        "benchmark_report_sha256": benchmark.report_sha256,
        "benchmark_row_selector": benchmark.row_selector,
        "return_price_basis": RETURN_PRICE_BASIS,
        "trade_price_basis": TRADE_PRICE_BASIS,
        "tax_price_basis": TAX_PRICE_BASIS,
        "dividend_tax_policy": DIVIDEND_TAX_POLICY,
        "tax_consistency_warning": TAX_CONSISTENCY_WARNING,
        "risk_metric_policy": RISK_METRIC_POLICY,
        "tax_proxy": tax_config.tax_proxy,
        "constant_usd_krw_rate": tax_config.usd_krw_rate,
        "annual_deduction_krw": tax_config.annual_deduction_krw,
        "capital_gains_tax_rate": tax_config.capital_gains_tax_rate,
        "lot_method": tax_config.lot_method,
        "tax_year_by": tax_config.tax_year_by,
        "settlement_lag_days": tax_config.settlement_lag_days,
        "cost_scenarios": [
            BASE_COST_SCENARIO.__dict__,
            CONSERVATIVE_COST_SCENARIO.__dict__,
        ],
        "strategy": {
            "name": best_strategy.name,
            "momentum_lookback_days": best_strategy.momentum_lookback_days,
            "trend_lookback_days": best_strategy.trend_lookback_days,
            "top_n": best_strategy.top_n,
            "target_exposure": best_strategy.target_exposure,
            "rebalance_interval_days": best_strategy.rebalance_interval_days,
            "risk_adjusted_return": "calmar_pct",
            "sharpe_ratio": "annualized_daily_equity_returns",
            "volatility_target_symbol": best_strategy.volatility_target_symbol,
            "volatility_lookback_days": best_strategy.volatility_lookback_days,
            "target_annual_volatility": best_strategy.target_annual_volatility,
            "volatility_min_scale": best_strategy.volatility_min_scale,
            "volatility_max_scale": best_strategy.volatility_max_scale,
        },
        "best_model": best_strategy.name,
        "validation_scenarios": validation_scenarios_path.as_posix(),
        "validation_audit": validation_audit_path.as_posix(),
        "validation_audit_status": {
            row.get("name", "unknown"): row.get("status", "UNKNOWN")
            for row in validation_audit_rows
        },
        "external_data_policy": "free_local_csv_only" if external_data.symbol_rows else "none",
        "external_data_dir": external_data_dir.as_posix() if external_data_dir else "",
        "external_data_sources": list(external_data.policy.free_data_sources),
        "external_data_network_policy": external_data.policy.network_policy,
        "external_data_live_execution_policy": external_data.policy.live_execution_policy,
        "survivorship_warning": " | ".join(sorted({member.survivorship_warning for member in members})),
        "survivorship_warning_flag": universe_survivorship_warning_flag(members),
        "paper_only": True,
        "dry_run": True,
        "execution_allowed": False,
        "production_effect": "none",
    }


def _model_config(
    *,
    benchmark: BenchmarkMetrics,
    tax_config: TaxConfig,
    best_strategy: StrategyConfig,
    evaluation: ObjectiveEvaluation,
) -> dict[str, object]:
    return {
        "model_id": best_strategy.name,
        "engine_status": evaluation.engine_status,
        "objective_status": evaluation.objective_status,
        "objective_reasons": evaluation.reasons,
        "strategy": {
            "name": best_strategy.name,
            "momentum_lookback_days": best_strategy.momentum_lookback_days,
            "trend_lookback_days": best_strategy.trend_lookback_days,
            "top_n": best_strategy.top_n,
            "target_exposure": best_strategy.target_exposure,
            "rebalance_interval_days": best_strategy.rebalance_interval_days,
            "volatility_target_symbol": best_strategy.volatility_target_symbol,
            "volatility_lookback_days": best_strategy.volatility_lookback_days,
            "target_annual_volatility": best_strategy.target_annual_volatility,
            "volatility_min_scale": best_strategy.volatility_min_scale,
            "volatility_max_scale": best_strategy.volatility_max_scale,
        },
        "benchmark_report_sha256": benchmark.report_sha256,
        "benchmark_row_selector": benchmark.row_selector,
        "return_price_basis": RETURN_PRICE_BASIS,
        "trade_price_basis": TRADE_PRICE_BASIS,
        "tax_price_basis": TAX_PRICE_BASIS,
        "dividend_tax_policy": DIVIDEND_TAX_POLICY,
        "tax_consistency_warning": TAX_CONSISTENCY_WARNING,
        "tax_proxy": tax_config.tax_proxy,
        "constant_usd_krw_rate": tax_config.usd_krw_rate,
        "paper_only": True,
        "dry_run": True,
        "execution_allowed": False,
        "production_effect": "none",
    }


def _cost_policy_markdown(tax_config: TaxConfig) -> str:
    lines = [
        "# Auto Paper Cost And Tax Policy",
        "",
        "paper-only / dry-run / no order submitted",
        "",
        "## Cost Scenarios",
        "",
        "| scenario | fee_rate | slippage_rate | fx_buffer_rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for scenario in [BASE_COST_SCENARIO, CONSERVATIVE_COST_SCENARIO]:
        lines.append(
            f"| {scenario.name} | {_fmt(scenario.fee_rate)} | "
            f"{_fmt(scenario.slippage_rate)} | {_fmt(scenario.fx_buffer_rate)} |"
        )
    lines.extend(
        [
            "",
            "## Tax Policy",
            "",
            f"- tax_proxy: `{tax_config.tax_proxy}`",
            f"- constant_usd_krw_rate: `{_fmt(tax_config.usd_krw_rate)}`",
            f"- lot_method: `{tax_config.lot_method}`",
            f"- tax_year_by: `{tax_config.tax_year_by}`",
            f"- settlement_lag_days: `{tax_config.settlement_lag_days}`",
            f"- annual_deduction_krw: `{_fmt(tax_config.annual_deduction_krw)}`",
            f"- capital_gains_tax_rate: `{_fmt(tax_config.capital_gains_tax_rate)}`",
            f"- return_price_basis: `{RETURN_PRICE_BASIS}`",
            f"- trade_price_basis: `{TRADE_PRICE_BASIS}`",
            f"- tax_price_basis: `{TAX_PRICE_BASIS}`",
            f"- dividend_tax_policy: `{DIVIDEND_TAX_POLICY}`",
            f"- tax_consistency_warning: `{TAX_CONSISTENCY_WARNING}`",
            "",
            "This is a paper-only comparison model, not tax advice and not a live trading instruction.",
            "",
        ]
    )
    return "\n".join(lines)


def _candidate_sweep_rows(
    evaluations: list[CandidateEvaluation],
    best_strategy_name: str,
    benchmark: BenchmarkMetrics,
    *,
    validation_pass_by_strategy: dict[str, bool] | None = None,
    concentration_ratio_by_strategy: dict[str, float] | None = None,
    validation_cache: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]] | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for evaluation in evaluations:
        result = evaluation.conservative_result
        strategy = evaluation.strategy
        audit_rows = (validation_cache or {}).get(strategy.name, ([], []))[1]
        adjusted = _apply_validation_audit_to_objective(
            ObjectiveEvaluation(
                engine_status=evaluation.engine_status,
                objective_status=evaluation.objective_status,
                core_conditions_passed=evaluation.objective_status in {"COMPLETE", "REVIEW"},
                risk_adjusted_passed=evaluation.objective_status == "COMPLETE",
                reasons=evaluation.reasons,
            ),
            audit_rows,
        )
        rows.append(
            {
                "strategy_name": strategy.name,
                "best_model": str(strategy.name == best_strategy_name),
                "validation_hard_gates_passed": str((validation_pass_by_strategy or {}).get(strategy.name, False)),
                "validation_concentration_ratio": _fmt((concentration_ratio_by_strategy or {}).get(strategy.name, float("inf"))),
                "validation_audit_status": _format_validation_audit_status(audit_rows),
                "engine_status": adjusted.engine_status,
                "objective_status": adjusted.objective_status,
                "reasons": adjusted.reasons,
                "momentum_lookback_days": str(strategy.momentum_lookback_days),
                "trend_lookback_days": str(strategy.trend_lookback_days),
                "top_n": str(strategy.top_n),
                "target_exposure": _fmt(strategy.target_exposure),
                "rebalance_interval_days": str(strategy.rebalance_interval_days),
                "scenario": result.scenario.name,
                "net_total_return_pct": _fmt(result.performance.net_total_return_pct),
                "net_cagr_pct": _fmt(result.performance.net_cagr_pct),
                "max_drawdown_abs_pct": _fmt(result.performance.max_drawdown_abs_pct),
                "risk_adjusted_return": _fmt(result.performance.risk_adjusted_return),
                "sharpe_ratio": _fmt(result.performance.sharpe_ratio),
                "risk_metric_policy": RISK_METRIC_POLICY,
                **_strategy_volatility_fields(strategy),
                "trade_cost_usd": _fmt(result.trade_cost_usd),
                "capital_gains_tax_usd": _fmt(result.tax_usd),
                "benchmark_report_sha256": benchmark.report_sha256,
                "return_price_basis": RETURN_PRICE_BASIS,
                "trade_price_basis": TRADE_PRICE_BASIS,
                "tax_price_basis": TAX_PRICE_BASIS,
                "dividend_tax_policy": DIVIDEND_TAX_POLICY,
                "tax_consistency_warning": str(TAX_CONSISTENCY_WARNING),
                **PAPER_FLAGS,
            }
        )
    return rows


def _format_validation_audit_status(rows: list[dict[str, str]]) -> str:
    return ";".join(f"{row.get('name', '')}={row.get('status', '')}" for row in rows)


def _strategy_volatility_fields(strategy: StrategyConfig) -> dict[str, str]:
    return {
        "volatility_target_symbol": strategy.volatility_target_symbol,
        "volatility_lookback_days": str(strategy.volatility_lookback_days),
        "target_annual_volatility": _fmt(strategy.target_annual_volatility),
        "volatility_min_scale": _fmt(strategy.volatility_min_scale),
        "volatility_max_scale": _fmt(strategy.volatility_max_scale),
    }


def _comparison_markdown(
    benchmark: BenchmarkMetrics,
    base: ScenarioResult,
    conservative: ScenarioResult,
    objective_status: str,
    reasons: str,
) -> str:
    lines = [
        "# Auto Paper Comparison",
        "",
        "paper-only / dry-run / no order submitted",
        "",
        f"- engine_status: `SUCCESS`",
        f"- objective_status: `{objective_status}`",
        f"- reasons: `{reasons}`",
        f"- benchmark_report_sha256: `{benchmark.report_sha256}`",
        f"- return_price_basis: `{RETURN_PRICE_BASIS}`",
        f"- trade_price_basis: `{TRADE_PRICE_BASIS}`",
        f"- tax_price_basis: `{TAX_PRICE_BASIS}`",
        f"- dividend_tax_policy: `{DIVIDEND_TAX_POLICY}`",
        f"- tax_consistency_warning: `{TAX_CONSISTENCY_WARNING}`",
        f"- risk_metric_policy: `{RISK_METRIC_POLICY}`",
        "",
        "| scenario | net total return | net CAGR | MDD abs | risk adjusted | sharpe_ratio | tax USD | trade cost USD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in [base, conservative]:
        lines.append(
            f"| {result.scenario.name} | {_fmt(result.performance.net_total_return_pct)} | "
            f"{_fmt(result.performance.net_cagr_pct)} | {_fmt(result.performance.max_drawdown_abs_pct)} | "
            f"{_fmt(result.performance.risk_adjusted_return)} | {_fmt(result.performance.sharpe_ratio)} | {_fmt(result.tax_usd)} | "
            f"{_fmt(result.trade_cost_usd)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"
