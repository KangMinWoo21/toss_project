import csv
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.monthly_rebalance import (
    DeploymentGate,
    MonthlyValidationCase,
    MonthlyRebalanceConfig,
    MonthlyBacktestResult,
    MonthlyDecision,
    PerformanceGuard,
    Position,
    RiskLimits,
    audit_monthly_validation_data,
    audit_point_in_time_price_coverage,
    apply_performance_guard,
    build_deployment_gate,
    build_monthly_performance_audit,
    build_monthly_validation_gate,
    compress_decision_to_buyable_targets,
    build_order_plan,
    decide_monthly_allocation,
    diagnose_universe_bias,
    equal_weight_buy_hold_period_return,
    exclude_invalid_price_symbols,
    exclude_top_period_return_symbols,
    filter_symbol_candles_by_universe,
    generate_monthly_validation_cases,
    is_monthly_rebalance_due,
    load_last_rebalance_date,
    load_performance_guard,
    load_point_in_time_universe,
    liquidity_universe_exposure_scale,
    mark_order_plan_execution,
    market_volatility_exposure_scale,
    risk_exit_code,
    risk_status,
    select_point_in_time_universe,
    select_liquid_universe,
    run_monthly_rebalance_backtest,
    run_monthly_walk_forward_validation,
    run_monthly_validation_suite,
    save_rebalance_state,
    save_monthly_performance_audit_rows,
    save_order_plan,
    save_universe_price_coverage_rows,
    select_buyable_targets,
    scale_monthly_decision_targets,
    target_weights_for_symbols,
    validate_pre_trade_risk,
)
from backtester.models import Candle


def _candle(day: str, open_price: float, close_price: float | None = None) -> Candle:
    close = open_price if close_price is None else close_price
    return Candle(date=day, open=open_price, high=max(open_price, close), low=min(open_price, close), close=close, volume=1_000)


def _monthly_result(*, excess_return_pct: float, max_drawdown_pct: float, trade_count: int = 1) -> MonthlyBacktestResult:
    return MonthlyBacktestResult(
        initial_cash=1_000_000,
        final_equity=1_100_000,
        total_return_pct=10.0,
        buy_hold_return_pct=10.0 - excess_return_pct,
        excess_return_pct=excess_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        trade_count=trade_count,
        decisions=[],
        trades=[],
        dates=["2026-06-20"],
        equity_curve=[1_100_000],
    )


def _daily_candles(start_day: str, count: int) -> list[Candle]:
    start = date.fromisoformat(start_day)
    return [
        Candle(
            date=(start + timedelta(days=index)).isoformat(),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=1_000,
        )
        for index in range(count)
    ]


def _daily_candles_with_volume(start_day: str, count: int, *, close: float, volume: float) -> list[Candle]:
    start = date.fromisoformat(start_day)
    return [
        Candle(
            date=(start + timedelta(days=index)).isoformat(),
            open=close + index,
            high=close + index + 1,
            low=close + index - 1,
            close=close + index,
            volume=volume,
        )
        for index in range(count)
    ]


def _trend_candles_with_volume(start_day: str, count: int, *, close: float, step: float, volume: float) -> list[Candle]:
    start = date.fromisoformat(start_day)
    rows: list[Candle] = []
    for index in range(count):
        price = close + (step * index)
        rows.append(
            Candle(
                date=(start + timedelta(days=index)).isoformat(),
                open=price,
                high=price + 1,
                low=max(1, price - 1),
                close=price,
                volume=volume,
            )
        )
    return rows


class MonthlyRebalanceTests(unittest.TestCase):
    def test_monthly_config_defaults_to_five_candidate_slots(self):
        self.assertEqual(MonthlyRebalanceConfig().train_years, 5)
        self.assertEqual(MonthlyRebalanceConfig().presets, ("balanced",))
        self.assertEqual(MonthlyRebalanceConfig().candidate_pool_size, 7)
        self.assertEqual(MonthlyRebalanceConfig().max_candidate_lookback_return_pct, 90.0)
        self.assertEqual(MonthlyRebalanceConfig().fallback_breadth_threshold, 0.5)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_breadth_threshold, 0.25)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_filter_days, 60)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_min_return_pct, -5.0)
        self.assertEqual(MonthlyRebalanceConfig().market_trend_risk_scale, 0.25)
        self.assertEqual(MonthlyRebalanceConfig().market_volatility_filter_days, 0)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_trigger_pct, -15.0)
        self.assertEqual(MonthlyRebalanceConfig().drawdown_guard_scale, 0.75)
        self.assertEqual(MonthlyRebalanceConfig().daily_drawdown_stop_pct, 0.0)
        self.assertEqual(MonthlyRebalanceConfig().cash_buffer_weight, 0.01)
        self.assertEqual(MonthlyRebalanceConfig().max_position_weight, 0.15)
        self.assertEqual(MonthlyRebalanceConfig().point_in_time_liquidity_top_n, 100)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_reference_top_n, 100)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_min_scale, 0.8)
        self.assertEqual(MonthlyRebalanceConfig().liquidity_risk_min_top_n, 20)
        self.assertEqual(MonthlyRebalanceConfig().market_beta_proxy_size, 12)
        self.assertEqual(RiskLimits().max_total_target_weight, 1.0)
        self.assertEqual(RiskLimits().max_total_buy_value, 10_000_000.0)
        self.assertEqual(RiskLimits().max_order_count, 15)

    def test_risk_gate_blocks_kill_switch_file(self):
        with TemporaryDirectory() as temp_dir:
            kill_switch = Path(temp_dir) / "KILL_SWITCH"
            kill_switch.write_text("pause trading", encoding="utf-8")

            checks = validate_pre_trade_risk(
                MonthlyDecision(
                    as_of_date="2026-06-20",
                    signal_date="2026-06-19",
                    mode="cash",
                    selected_preset="cash",
                    target_weights={},
                    reason="unit-test",
                ),
                [],
                kill_switch_path=kill_switch,
            )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("kill_switch", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_blocks_excess_total_target_weight(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.6, "222222": 0.3},
                reason="unit-test",
            ),
            [],
            limits=RiskLimits(max_total_target_weight=0.8),
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("total_target_weight", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_passes_conservative_buy_plan(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="alpha",
            selected_preset="balanced",
            target_weights={"111111": 0.4, "222222": 0.4},
            reason="unit-test",
        )
        orders = build_order_plan(
            decision,
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 100_000, "222222": 100_000},
            min_trade_value=0,
        )

        checks = validate_pre_trade_risk(
            decision,
            orders,
            limits=RiskLimits(
                max_total_target_weight=0.8,
                max_single_order_value=500_000,
                max_total_buy_value=1_000_000,
                max_order_count=5,
            ),
            day_start_equity=1_000_000,
            current_equity=1_000_000,
        )

        self.assertEqual(risk_status(checks), "PASS")

    def test_risk_gate_blocks_daily_loss_limit(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="cash",
                selected_preset="cash",
                target_weights={},
                reason="unit-test",
            ),
            [],
            limits=RiskLimits(max_daily_loss_pct=3.0),
            day_start_equity=1_000_000,
            current_equity=960_000,
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("daily_loss", {check.name for check in checks if check.status == "BLOCK"})

    def test_risk_gate_blocks_failed_deployment_gate(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.4},
                reason="unit-test",
            ),
            [],
            deployment_gate=DeploymentGate(deployable=False, reason="negative_excess_return", source="unit"),
        )

        self.assertEqual(risk_status(checks), "BLOCK")
        self.assertIn("deployment_gate", {check.name for check in checks if check.status == "BLOCK"})

    def test_performance_guard_warn_scales_decision_targets(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="alpha",
            selected_preset="balanced",
            target_weights={"111111": 0.5, "222222": 0.4},
            reason="unit-test",
        )

        guarded = apply_performance_guard(
            decision,
            PerformanceGuard(status="WARN", detail="thin margin", scale=0.1, source="unit"),
        )

        self.assertAlmostEqual(guarded.target_weights["111111"], 0.05)
        self.assertAlmostEqual(guarded.target_weights["222222"], 0.04)
        self.assertIn("performance_warn_scale_0.1000", guarded.reason)

    def test_risk_gate_warns_on_performance_guard_warning(self):
        checks = validate_pre_trade_risk(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            [],
            performance_guard=PerformanceGuard(status="WARN", detail="thin margin", scale=0.1, source="unit"),
        )

        self.assertEqual(risk_status(checks), "WARN")
        self.assertIn("performance_guard", {check.name for check in checks if check.status == "WARN"})

    def test_load_performance_guard_warn_uses_configured_scale(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "performance.csv"
            report.write_text(
                "name,status,detail\n"
                "required_scenarios,PASS,ok\n"
                "walk_forward_margin,WARN,min_walk_forward_excess_pct=3.2\n",
                encoding="utf-8",
            )

            guard = load_performance_guard(report, warn_scale=0.2, block_scale=0.0)

        self.assertIsNotNone(guard)
        assert guard is not None
        self.assertEqual(guard.status, "WARN")
        self.assertEqual(guard.scale, 0.2)
        self.assertIn("walk_forward_margin", guard.detail)

    def test_compress_decision_to_buyable_targets_drops_unbuyable_high_price_names(self):
        decision = MonthlyDecision(
            as_of_date="2026-06-20",
            signal_date="2026-06-19",
            mode="market_beta_proxy",
            selected_preset="market_beta_proxy",
            target_weights={"HIGH": 0.033, "LOW1": 0.033, "LOW2": 0.033},
            reason="unit-test",
        )

        compressed = compress_decision_to_buyable_targets(
            decision,
            reference_prices={"HIGH": 120_000, "LOW1": 10_000, "LOW2": 20_000},
            portfolio_value=1_000_000,
            max_position_weight=0.15,
            min_target_value=10_000,
        )

        self.assertNotIn("HIGH", compressed.target_weights)
        self.assertAlmostEqual(sum(compressed.target_weights.values()), 0.099)
        self.assertIn("buyable_targets_2of3", compressed.reason)

    def test_risk_exit_code_is_nonzero_for_blocked_plan(self):
        self.assertEqual(risk_exit_code("PASS"), 0)
        self.assertEqual(risk_exit_code("WARN"), 0)
        self.assertEqual(risk_exit_code("BLOCK"), 2)

    def test_deployment_gate_rejects_negative_excess_return(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=-1.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": False},
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "negative_excess_return")

    def test_monthly_performance_audit_warns_on_thin_walk_forward_margin(self):
        rows = [
            {
                "name": "full_period",
                "category": "duration",
                "required": True,
                "deployable": True,
                "excess_return_pct": 30.0,
                "max_drawdown_pct": -10.0,
                "trade_count": 10,
            },
            {
                "name": "walk_forward_001",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 3.0,
                "max_drawdown_pct": -8.0,
                "trade_count": 5,
            },
        ]

        checks = build_monthly_performance_audit(rows, min_walk_forward_warn_excess_pct=5.0)

        warning_names = {check["name"] for check in checks if check["status"] == "WARN"}
        self.assertIn("walk_forward_margin", warning_names)

    def test_monthly_performance_audit_warns_when_full_period_dominates_oos(self):
        rows = [
            {
                "name": "full_period",
                "category": "duration",
                "required": True,
                "deployable": True,
                "excess_return_pct": 120.0,
                "max_drawdown_pct": -10.0,
                "trade_count": 10,
            },
            {
                "name": "walk_forward_001",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 3.0,
                "max_drawdown_pct": -8.0,
                "trade_count": 5,
            },
            {
                "name": "walk_forward_002",
                "category": "walk_forward",
                "required": True,
                "deployable": True,
                "excess_return_pct": 5.0,
                "max_drawdown_pct": -9.0,
                "trade_count": 5,
            },
        ]

        checks = build_monthly_performance_audit(rows, max_full_to_walk_median_excess_ratio=20.0)

        warning_names = {check["name"] for check in checks if check["status"] == "WARN"}
        self.assertIn("return_concentration", warning_names)

    def test_save_monthly_performance_audit_rows(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "audit.csv"
            count = save_monthly_performance_audit_rows(
                [{"name": "walk_forward_margin", "status": "PASS", "detail": "ok"}],
                output,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(count, 1)
        self.assertIn("walk_forward_margin", text)

    def test_deployment_gate_rejects_universe_bias_warning(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": True},
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "universe_bias_warning")

    def test_deployment_gate_accepts_positive_excess_with_controlled_drawdown(self):
        gate = build_deployment_gate(
            _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0),
            universe_bias={"warning": False},
        )

        self.assertTrue(gate.deployable)
        self.assertEqual(gate.reason, "passed")

    def test_monthly_validation_gate_rejects_any_failed_required_scenario(self):
        gate = build_monthly_validation_gate(
            [
                {"name": "base", "deployable": True, "required": True},
                {"name": "stress_top_winners", "deployable": False, "required": True},
            ],
            source="unit",
        )

        self.assertFalse(gate.deployable)
        self.assertEqual(gate.reason, "failed_required_scenarios:stress_top_winners")

    def test_monthly_validation_gate_accepts_when_all_required_scenarios_pass(self):
        gate = build_monthly_validation_gate(
            [
                {"name": "base", "deployable": True, "required": True},
                {"name": "optional_probe", "deployable": False, "required": False},
            ],
            source="unit",
        )

        self.assertTrue(gate.deployable)
        self.assertEqual(gate.reason, "passed")

    def test_run_monthly_validation_suite_marks_failed_scenario(self):
        def fake_runner(symbol_candles, **kwargs):
            excess = 5.0 if kwargs["start"] == "2024-01-01" else -1.0
            return _monthly_result(excess_return_pct=excess, max_drawdown_pct=-10.0)

        rows = run_monthly_validation_suite(
            {"111111": [_candle("2024-01-02", 100, 110), _candle("2024-02-01", 110, 120)]},
            cases=[
                MonthlyValidationCase(name="passing", category="duration", start="2024-01-01", end="2024-01-31"),
                MonthlyValidationCase(name="failing", category="stress", start="2024-02-01", end="2024-02-29"),
            ],
            config=MonthlyRebalanceConfig(),
            backtest_runner=fake_runner,
        )

        self.assertEqual([row["deployable"] for row in rows], [True, False])
        self.assertEqual(build_monthly_validation_gate(rows).reason, "failed_required_scenarios:failing")

    def test_run_monthly_validation_suite_applies_slippage_multiplier(self):
        seen_slippage_rates: list[float] = []

        def fake_runner(symbol_candles, **kwargs):
            seen_slippage_rates.append(kwargs["slippage_rate"])
            return _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0)

        run_monthly_validation_suite(
            {"111111": [_candle("2024-01-02", 100, 110)]},
            cases=[
                MonthlyValidationCase(
                    name="slippage_x3",
                    category="stress",
                    start="2024-01-01",
                    end="2024-01-31",
                    slippage_multiplier=3.0,
                ),
            ],
            config=MonthlyRebalanceConfig(),
            slippage_rate=0.001,
            backtest_runner=fake_runner,
        )

        self.assertEqual(seen_slippage_rates, [0.003])

    def test_run_monthly_validation_suite_records_universe_bias_details(self):
        def fake_runner(symbol_candles, **kwargs):
            return _monthly_result(excess_return_pct=5.0, max_drawdown_pct=-10.0)

        rows = run_monthly_validation_suite(
            {
                "NORMAL": [_candle("2024-01-02", 100, 120)],
                "WINNER": [_candle("2024-01-02", 100, 800)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            cases=[MonthlyValidationCase(name="biased", category="duration", start="2024-01-01", end="2024-01-31")],
            config=MonthlyRebalanceConfig(),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["reason"], "universe_bias_warning")
        self.assertIn("high_average_symbol_return", rows[0]["universe_bias_reasons"])
        self.assertIn("extreme_return_share", rows[0]["universe_bias_reasons"])
        self.assertEqual(rows[0]["universe_extreme_return_symbols"], 1)

    def test_run_monthly_walk_forward_validation_selects_train_winner_for_test(self):
        test_presets: list[str] = []

        def fake_runner(symbol_candles, **kwargs):
            preset = kwargs["config"].presets[0]
            if kwargs["end"] == "2024-03-31":
                excess = 10.0 if preset == "balanced" else -5.0
            else:
                test_presets.append(preset)
                excess = 3.0 if preset == "balanced" else -3.0
            return _monthly_result(excess_return_pct=excess, max_drawdown_pct=-10.0)

        rows = run_monthly_walk_forward_validation(
            {"111111": _daily_candles("2024-01-01", 180)},
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(presets=("balanced", "aggressive")),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "balanced")
        self.assertEqual(rows[0]["train_excess_return_pct"], 10.0)
        self.assertEqual(rows[0]["deployable"], True)
        self.assertEqual(test_presets, ["balanced"])

    def test_run_monthly_walk_forward_validation_penalizes_fragile_train_winner(self):
        test_presets: list[str] = []

        def fake_runner(symbol_candles, **kwargs):
            preset = kwargs["config"].presets[0]
            if kwargs["end"] == "2024-03-31":
                if preset == "aggressive":
                    return _monthly_result(excess_return_pct=20.0, max_drawdown_pct=-35.0, trade_count=4)
                return _monthly_result(excess_return_pct=12.0, max_drawdown_pct=-4.0, trade_count=4)
            test_presets.append(preset)
            return _monthly_result(excess_return_pct=2.0, max_drawdown_pct=-8.0, trade_count=2)

        rows = run_monthly_walk_forward_validation(
            {"111111": _daily_candles("2024-01-01", 180)},
            cases=[
                MonthlyValidationCase(
                    name="wf_001",
                    category="walk_forward",
                    train_start="2024-01-01",
                    train_end="2024-03-31",
                    start="2024-04-01",
                    end="2024-06-30",
                )
            ],
            config=MonthlyRebalanceConfig(presets=("balanced", "aggressive")),
            backtest_runner=fake_runner,
        )

        self.assertEqual(rows[0]["selected_preset"], "balanced")
        self.assertEqual(rows[0]["train_excess_return_pct"], 12.0)
        self.assertEqual(test_presets, ["balanced"])

    def test_generate_monthly_validation_cases_includes_duration_regime_and_stress(self):
        cases = generate_monthly_validation_cases(
            {"111111": _daily_candles("2024-01-01", 320)},
            start="2024-01-01",
            end="2024-11-15",
        )
        names = {case.name for case in cases}
        categories = {case.category for case in cases}

        self.assertIn("full_period", names)
        self.assertIn("duration_3m", names)
        self.assertIn("stress_exclude_500pct_winners", names)
        self.assertIn("stress_exclude_top_5_winners", names)
        self.assertIn("stress_slippage_x3", names)
        self.assertTrue(any(case.category == "walk_forward" for case in cases))
        self.assertIn("duration", categories)
        self.assertIn("regime", categories)
        self.assertIn("stress", categories)
        self.assertIn("walk_forward", categories)

    def test_audit_monthly_validation_data_flags_quality_issues(self):
        rows = audit_monthly_validation_data(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101)],
                "SHORT": [_candle("2024-01-02", 100)],
                "BADPRICE": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                ],
            },
            start="2024-01-01",
            end="2024-01-02",
            min_rows=2,
        )

        statuses = {row["symbol"]: row["status"] for row in rows}
        self.assertEqual(statuses["GOOD"], "PASS")
        self.assertEqual(statuses["SHORT"], "BLOCK")
        self.assertEqual(statuses["BADPRICE"], "BLOCK")

    def test_audit_point_in_time_price_coverage_blocks_low_snapshot_coverage(self):
        rows = audit_point_in_time_price_coverage(
            {
                "AAA": [_candle("2024-01-15", 100)],
                "CCC": [_candle("2024-02-15", 100)],
            },
            {
                "2024-01-31": {"AAA", "BBB", "CCC"},
                "2024-02-29": {"AAA"},
            },
            min_coverage_pct=80.0,
        )

        self.assertEqual(rows[0]["date"], "2024-01-31")
        self.assertEqual(rows[0]["covered_symbols"], 1)
        self.assertEqual(rows[0]["missing_symbols"], 2)
        self.assertEqual(rows[0]["status"], "BLOCK")
        self.assertIn("BBB", rows[0]["missing_preview"])
        self.assertEqual(rows[1]["status"], "PASS")

    def test_save_universe_price_coverage_rows_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coverage.csv"
            saved = save_universe_price_coverage_rows(
                [
                    {
                        "date": "2024-01-31",
                        "universe_symbols": 2,
                        "price_symbols": 1,
                        "covered_symbols": 1,
                        "missing_symbols": 1,
                        "coverage_pct": 50.0,
                        "status": "BLOCK",
                        "missing_preview": "BBB",
                    }
                ],
                path,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(saved, 1)
        self.assertIn("coverage_pct", text)
        self.assertIn("BBB", text)

    def test_select_point_in_time_universe_excludes_nonpositive_price_history(self):
        selected = select_point_in_time_universe(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101), _candle("2024-01-03", 102)],
                "BAD": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                    _candle("2024-01-03", 102),
                ],
            },
            signal_date="2024-01-03",
            min_history_days=3,
            min_reference_price=1,
            max_trailing_return_pct=300,
            trailing_return_days=3,
        )

        self.assertEqual(set(selected), {"GOOD"})

    def test_exclude_invalid_price_symbols_removes_nonpositive_price_history(self):
        filtered = exclude_invalid_price_symbols(
            {
                "GOOD": [_candle("2024-01-01", 100), _candle("2024-01-02", 101)],
                "BAD": [
                    _candle("2024-01-01", 100),
                    Candle("2024-01-02", 0, 0, 0, 0, 1_000),
                ],
            }
        )

        self.assertEqual(set(filtered), {"GOOD"})

    def test_market_volatility_exposure_scale_reduces_high_volatility(self):
        scale = market_volatility_exposure_scale(
            {
                "VOL": [
                    _candle("2024-01-01", 100),
                    _candle("2024-01-02", 120),
                    _candle("2024-01-03", 90),
                    _candle("2024-01-04", 125),
                    _candle("2024-01-05", 95),
                    _candle("2024-01-06", 130),
                ]
            },
            before_date="2024-01-07",
            lookback_days=5,
            target_volatility_pct=10.0,
            min_scale=0.25,
        )

        self.assertGreaterEqual(scale, 0.25)
        self.assertLess(scale, 1.0)

    def test_market_volatility_exposure_scale_keeps_low_volatility_full_size(self):
        scale = market_volatility_exposure_scale(
            {"CALM": _daily_candles("2024-01-01", 20)},
            before_date="2024-01-21",
            lookback_days=10,
            target_volatility_pct=50.0,
            min_scale=0.25,
        )

        self.assertEqual(scale, 1.0)

    def test_decide_monthly_allocation_uses_liquid_proxy_when_market_beta_symbol_missing(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=3_000),
                "BBB": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=2_000),
                "CCC": _daily_candles_with_volume("2024-01-01", 10, close=100, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.4,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 109},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.selected_preset, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_strong_breadth_proxy")
        self.assertEqual(decision.target_weights, {"AAA": 0.495, "BBB": 0.495})

    def test_decide_monthly_allocation_uses_proxy_for_neutral_breadth_below_alpha_threshold(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy")
        self.assertEqual(decision.target_weights, {"AAA": 0.495, "BBB": 0.495})

    def test_decide_monthly_allocation_scales_exposure_when_market_trend_is_negative(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.0,
                market_trend_filter_days=3,
                market_trend_min_return_pct=0.0,
                market_trend_risk_scale=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 101, "BBB": 101, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_trend_scaled")
        self.assertEqual(decision.target_weights, {"AAA": 0.2475, "BBB": 0.2475})

    def test_liquidity_universe_exposure_scale_reduces_only_meaningful_narrow_universe(self):
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=100,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            1.0,
        )
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=50,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            0.8,
        )
        self.assertEqual(
            liquidity_universe_exposure_scale(
                top_n=3,
                reference_top_n=100,
                min_scale=0.8,
                min_top_n=20,
            ),
            1.0,
        )

    def test_decide_monthly_allocation_scales_exposure_when_liquidity_universe_is_narrow(self):
        decision = decide_monthly_allocation(
            {
                "AAA": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=3_000),
                "BBB": _trend_candles_with_volume("2024-01-01", 10, close=100, step=1, volume=2_000),
                "CCC": _trend_candles_with_volume("2024-01-01", 10, close=110, step=-1, volume=1_000),
            },
            as_of_date="2024-01-10",
            config=MonthlyRebalanceConfig(
                train_start="2024-01-01",
                min_train_trades=999,
                min_rows_per_window=3,
                fallback_breadth_days=3,
                fallback_breadth_threshold=0.8,
                market_beta_breadth_threshold=0.5,
                point_in_time_min_history_days=3,
                point_in_time_min_reference_price=1,
                point_in_time_liquidity_window_days=3,
                point_in_time_liquidity_top_n=3,
                liquidity_risk_reference_top_n=6,
                liquidity_risk_min_top_n=3,
                liquidity_risk_min_scale=0.8,
                market_beta_proxy_size=2,
                max_position_weight=0.5,
            ),
            portfolio_value=1_000_000,
            reference_prices={"AAA": 109, "BBB": 109, "CCC": 101},
        )

        self.assertEqual(decision.mode, "market_beta_proxy")
        self.assertEqual(decision.reason, "no_train_candidate_neutral_breadth_proxy_liquidity_scaled")
        self.assertEqual(decision.target_weights, {"AAA": 0.396, "BBB": 0.396})

    def test_scale_monthly_decision_targets_reduces_weights_and_marks_reason(self):
        decision = scale_monthly_decision_targets(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"AAA": 0.4, "BBB": 0.2},
                reason="selected_monthly_alpha",
            ),
            scale=0.5,
            reason_suffix="_drawdown_guard",
        )

        self.assertEqual(decision.target_weights, {"AAA": 0.2, "BBB": 0.1})
        self.assertEqual(decision.reason, "selected_monthly_alpha_drawdown_guard")

    def test_load_point_in_time_universe_groups_symbols_by_snapshot_date(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "universe.csv"
            path.write_text(
                "date,symbol,name,market\n"
                "2024-01-31,5930,Samsung,KOSPI\n"
                "2024-01-31,000660,SK hynix,KOSPI\n"
                "2024-02-29,005930,Samsung,KOSPI\n",
                encoding="utf-8",
            )

            universe = load_point_in_time_universe(path)

        self.assertEqual(universe["2024-01-31"], {"005930", "000660"})
        self.assertEqual(universe["2024-02-29"], {"005930"})

    def test_filter_symbol_candles_by_universe_uses_latest_snapshot_before_signal_date(self):
        universe = {
            "2024-01-31": {"LIVE"},
            "2024-02-29": {"LIVE", "NEW"},
        }

        filtered = filter_symbol_candles_by_universe(
            {
                "LIVE": [_candle("2024-01-31", 100)],
                "NEW": [_candle("2024-01-31", 100)],
            },
            universe,
            signal_date="2024-02-15",
        )

        self.assertEqual(set(filtered), {"LIVE"})

    def test_is_monthly_rebalance_due_only_once_per_month(self):
        self.assertTrue(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date=None))
        self.assertFalse(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date="2026-06-03"))
        self.assertTrue(is_monthly_rebalance_due(as_of_date="2026-06-20", last_rebalance_date="2026-05-31"))

    def test_build_order_plan_sells_removed_position_and_buys_target(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="aggressive",
                target_weights={"222222": 1.0},
                reason="unit-test",
            ),
            positions=[Position(symbol="111111", quantity=10, average_price=100)],
            cash=0,
            reference_prices={"111111": 100, "222222": 50},
            min_trade_value=0,
        )

        self.assertEqual([(order.action, order.symbol, order.quantity) for order in orders], [
            ("SELL", "111111", 10),
            ("BUY", "222222", 20),
        ])

    def test_build_order_plan_respects_cash_buffer_in_target_weights(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.49, "222222": 0.49},
                reason="cash-buffer",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000, "222222": 10_000},
            min_trade_value=0,
        )

        self.assertEqual(sum(order.estimated_value for order in orders), 980_000)

    def test_build_order_plan_reports_target_below_one_share(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.2},
                reason="small-slot",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 300_000},
            min_trade_value=0,
        )

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].action, "SKIP")
        self.assertEqual(orders[0].reason, "target_value_below_one_share")

    def test_warn_order_plan_is_not_execution_allowed(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )

        guarded = mark_order_plan_execution(orders, risk_status_value="WARN")

        self.assertFalse(guarded[0].execution_allowed)
        self.assertEqual(guarded[0].execution_mode, "blocked")
        self.assertEqual(guarded[0].execution_block_reason, "risk_status_WARN")

    def test_pass_order_plan_is_execution_allowed(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )

        guarded = mark_order_plan_execution(orders, risk_status_value="PASS")

        self.assertTrue(guarded[0].execution_allowed)
        self.assertEqual(guarded[0].execution_mode, "live_ready")
        self.assertEqual(guarded[0].execution_block_reason, "")

    def test_save_order_plan_writes_execution_guard_columns(self):
        orders = build_order_plan(
            MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-19",
                mode="alpha",
                selected_preset="balanced",
                target_weights={"111111": 0.1},
                reason="unit-test",
            ),
            positions=[],
            cash=1_000_000,
            reference_prices={"111111": 10_000},
            min_trade_value=0,
        )
        guarded = mark_order_plan_execution(orders, risk_status_value="WARN")
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "orders.csv"
            save_order_plan(guarded, output)
            with output.open(newline="", encoding="utf-8-sig") as f:
                row = next(csv.DictReader(f))

        self.assertEqual(row["execution_allowed"], "False")
        self.assertEqual(row["execution_mode"], "blocked")
        self.assertEqual(row["execution_block_reason"], "risk_status_WARN")

    def test_target_weights_cap_single_position_exposure(self):
        weights = target_weights_for_symbols(
            ["111111", "222222", "333333"],
            target_budget=0.98,
            max_position_weight=0.2,
        )

        self.assertEqual(weights, {"111111": 0.2, "222222": 0.2, "333333": 0.2})

    def test_select_buyable_targets_skips_unaffordable_ranked_symbols(self):
        selected = select_buyable_targets(
            ["EXPENS", "MIDCAP", "CHEAP1", "CHEAP2"],
            reference_prices={
                "EXPENS": 300_000,
                "MIDCAP": 190_000,
                "CHEAP1": 50_000,
                "CHEAP2": 30_000,
            },
            portfolio_value=1_000_000,
            target_budget=0.98,
            max_position_weight=0.2,
            min_target_value=0,
        )

        self.assertEqual(selected, ["MIDCAP", "CHEAP1", "CHEAP2"])

    def test_select_liquid_universe_uses_only_signal_date_history(self):
        selected = select_liquid_universe(
            {
                "NOW": [
                    Candle("2024-01-01", 10, 10, 10, 10, 100),
                    Candle("2024-01-02", 10, 10, 10, 10, 100),
                ],
                "FUTURE": [
                    Candle("2024-01-01", 10, 10, 10, 10, 1),
                    Candle("2024-01-02", 10, 10, 10, 10, 10_000),
                ],
            },
            signal_date="2024-01-01",
            top_n=1,
            window_days=1,
        )

        self.assertEqual(list(selected), ["NOW"])

    def test_select_point_in_time_universe_excludes_only_asof_bias_risks(self):
        selected = select_point_in_time_universe(
            {
                "STABLE": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 110),
                    _candle("2024-01-03", 110, 120),
                ],
                "FUTURE_WINNER": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 110),
                    _candle("2024-01-03", 110, 120),
                    _candle("2024-01-04", 120, 1_000),
                ],
                "RECENT_SPIKE": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 500),
                    _candle("2024-01-03", 500, 550),
                ],
                "SHORT_HISTORY": [
                    _candle("2024-01-03", 100, 120),
                ],
                "PENNY": [
                    _candle("2024-01-01", 100, 100),
                    _candle("2024-01-02", 100, 90),
                    _candle("2024-01-03", 90, 80),
                ],
            },
            signal_date="2024-01-03",
            min_history_days=3,
            min_reference_price=90,
            max_trailing_return_pct=300,
            trailing_return_days=3,
        )

        self.assertEqual(list(selected), ["STABLE", "FUTURE_WINNER"])

    def test_equal_weight_buy_hold_counts_expensive_symbols_fractionally(self):
        result = equal_weight_buy_hold_period_return(
            {
                "CHEAP": [_candle("2024-01-02", 100, 200)],
                "EXPENS": [_candle("2024-01-02", 1_000, 2_000)],
            },
            start="2024-01-01",
            end="2024-01-31",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
        )

        self.assertAlmostEqual(result, 100.0)

    def test_diagnose_universe_bias_flags_extreme_winner_dependence(self):
        row = diagnose_universe_bias(
            {
                "NORMAL": [_candle("2024-01-02", 100, 120)],
                "WINNER": [_candle("2024-01-02", 100, 800)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            start="2024-01-01",
            end="2024-01-31",
            extreme_return_threshold_pct=500.0,
        )

        self.assertEqual(row["symbol_count"], 3)
        self.assertEqual(row["extreme_return_symbols"], 1)
        self.assertIn("high_average_symbol_return", row["warning_reasons"])
        self.assertIn("extreme_return_share", row["warning_reasons"])
        self.assertTrue(row["warning"])

    def test_exclude_top_period_return_symbols_is_stress_only_filter(self):
        selected = exclude_top_period_return_symbols(
            {
                "FLAT": [_candle("2024-01-02", 100, 100)],
                "WINNER": [_candle("2024-01-02", 100, 200)],
                "LOSER": [_candle("2024-01-02", 100, 80)],
            },
            start="2024-01-01",
            end="2024-01-31",
            top_n=1,
        )

        self.assertEqual(set(selected), {"FLAT", "LOSER"})

    def test_rebalance_state_round_trips_last_plan_date(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.csv"
            decision = MonthlyDecision(
                as_of_date="2026-06-20",
                signal_date="2026-06-18",
                mode="alpha",
                selected_preset="aggressive",
                target_weights={"005930": 0.98},
                reason="unit-test",
            )

            save_rebalance_state(decision, path)

            self.assertEqual(load_last_rebalance_date(path), "2026-06-20")

    def test_monthly_backtest_uses_only_prior_candles_and_trades_at_open(self):
        seen: list[tuple[str, str]] = []

        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            seen.append((as_of_date, latest_seen))
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 90, 90),
                    _candle("2024-02-01", 100, 110),
                    _candle("2024-02-29", 120, 120),
                ]
            },
            start="2024-02-01",
            end="2024-02-29",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            decision_provider=decision_provider,
        )

        self.assertEqual(seen, [("2024-02-01", "2024-01-31")])
        self.assertEqual(result.trade_count, 1)
        self.assertAlmostEqual(result.final_equity, 1_200)

    def test_daily_drawdown_stop_liquidates_on_next_open(self):
        def decision_provider(symbol_candles, *, as_of_date, config):
            latest_seen = max(candle.date for candles in symbol_candles.values() for candle in candles)
            return MonthlyDecision(
                as_of_date=as_of_date,
                signal_date=latest_seen,
                mode="alpha",
                selected_preset="unit",
                target_weights={"111111": 1.0},
                reason="unit-test",
            )

        result = run_monthly_rebalance_backtest(
            {
                "111111": [
                    _candle("2024-01-31", 100, 100),
                    _candle("2024-02-01", 100, 100),
                    _candle("2024-02-02", 70, 70),
                    _candle("2024-02-05", 70, 70),
                ]
            },
            start="2024-02-01",
            end="2024-02-05",
            initial_cash=1_000,
            fee_rate=0.0,
            tax_rate=0.0,
            slippage_rate=0.0,
            min_trade_value=0.0,
            config=MonthlyRebalanceConfig(daily_drawdown_stop_pct=-10.0),
            decision_provider=decision_provider,
        )

        self.assertEqual([(trade.date, trade.action, trade.reason) for trade in result.trades], [
            ("2024-02-01", "BUY", "unit-test"),
            ("2024-02-05", "SELL", "daily_drawdown_stop"),
        ])
        self.assertAlmostEqual(result.final_equity, 700)


if __name__ == "__main__":
    unittest.main()
