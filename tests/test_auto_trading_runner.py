import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from backtester.auto_trading.costs import CostScenario
from backtester.auto_trading.gates import PerformanceMetrics
from backtester.auto_trading.runner import (
    CandidateEvaluation,
    DEFAULT_CANDIDATE_GRID,
    ScenarioResult,
    StrategyConfig,
    _apply_validation_audit_to_objective,
    _monthly_style_validation_rows,
    _momentum_cash_guard_targets,
    _select_best_candidate,
    run_auto_paper_run,
)
from backtester.auto_trading.gates import ObjectiveEvaluation
from backtester.auto_trading.benchmark import BenchmarkMetrics
from backtester.auto_trading.costs import TaxConfig
from backtester.auto_trading.prices import load_price_history
from backtester.auto_trading.universe import load_universe


def _write_price(path: Path, symbol: str, closes: list[float]) -> None:
    rows = ["date,symbol,open,high,low,close,adj_close,volume,source"]
    start = date(2025, 1, 1)
    for index, close in enumerate(closes):
        current = start + timedelta(days=index)
        rows.append(
            f"{current.isoformat()},{symbol},{close},{close},{close},{close},{close},1000,yahoo"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


class AutoTradingRunnerTests(unittest.TestCase):
    def test_default_candidate_grid_includes_concentration_pass_exposure_candidate(self):
        names = {strategy.name for strategy in DEFAULT_CANDIDATE_GRID}

        self.assertIn("momentum_cash_guard_m84_t70_top1_exp13_reb70", names)
        self.assertIn("momentum_cash_guard_vol_spy42_tvol12_floor80_m84_t70_top1_exp18_reb70", names)
        self.assertIn("momentum_cash_guard_vol_spy21_tvol10_floor75_cap105_m84_t70_top1_exp18_reb70", names)

    def test_volatility_targeting_scales_momentum_targets_when_realized_vol_is_high(self):
        strategy = StrategyConfig(
            "vol_scaled",
            2,
            2,
            1,
            0.20,
            1,
            volatility_target_symbol="SPY",
            volatility_lookback_days=2,
            target_annual_volatility=0.01,
            volatility_min_scale=0.50,
            volatility_max_scale=1.00,
        )
        close_history = {
            "SPY": [100.0, 130.0, 100.0, 110.0],
            "QQQ": [100.0, 101.0, 102.0, 103.0],
            "AAA": [100.0, 100.0, 100.0, 130.0],
        }

        targets = _momentum_cash_guard_targets(["SPY", "QQQ", "AAA"], close_history, 3, strategy)

        self.assertAlmostEqual(targets["AAA"], 0.10, places=6)
        self.assertEqual(targets["SPY"], 0.0)
        self.assertEqual(targets["QQQ"], 0.0)

    def test_select_best_candidate_prefers_validation_pass_over_in_sample_score(self):
        scenario = CostScenario("conservative", fee_rate=0.0, slippage_rate=0.0, fx_buffer_rate=0.0)
        aggressive = CandidateEvaluation(
            strategy=StrategyConfig("aggressive", 10, 10, 1, 0.9, 21),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(500.0, 20.0, 20.0, 100.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(500.0, 20.0, 20.0, 100.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            reasons="full_period_only",
        )
        robust = CandidateEvaluation(
            strategy=StrategyConfig("robust", 20, 20, 1, 0.3, 63),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(250.0, 12.0, 15.0, 80.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(250.0, 12.0, 15.0, 80.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            reasons="robust",
        )

        best = _select_best_candidate(
            [aggressive, robust],
            validation_pass_by_strategy={"aggressive": False, "robust": True},
        )

        self.assertEqual(best.strategy.name, "robust")

    def test_select_best_candidate_prefers_lower_concentration_among_validation_passes(self):
        scenario = CostScenario("conservative", fee_rate=0.0, slippage_rate=0.0, fx_buffer_rate=0.0)
        concentrated = CandidateEvaluation(
            strategy=StrategyConfig("concentrated", 10, 10, 1, 0.5, 21),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(300.0, 16.0, 15.0, 90.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(300.0, 16.0, 15.0, 90.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            reasons="high_return",
        )
        balanced = CandidateEvaluation(
            strategy=StrategyConfig("balanced", 20, 20, 1, 0.2, 75),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(150.0, 9.0, 12.0, 60.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(150.0, 9.0, 12.0, 60.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            reasons="lower_concentration",
        )

        best = _select_best_candidate(
            [concentrated, balanced],
            validation_pass_by_strategy={"concentrated": True, "balanced": True},
            concentration_ratio_by_strategy={"concentrated": 38.0, "balanced": 22.0},
        )

        self.assertEqual(best.strategy.name, "balanced")

    def test_select_best_candidate_prefers_review_over_not_complete_even_with_lower_concentration(self):
        scenario = CostScenario("conservative", fee_rate=0.0, slippage_rate=0.0, fx_buffer_rate=0.0)
        too_defensive = CandidateEvaluation(
            strategy=StrategyConfig("too_defensive", 84, 70, 1, 0.13, 70),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(90.0, 5.0, 14.0, 35.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(90.0, 5.0, 14.0, 35.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="NOT_COMPLETE",
            reasons="conservative_net_total_return_not_above_benchmark",
        )
        review_candidate = CandidateEvaluation(
            strategy=StrategyConfig("review_candidate", 84, 70, 1, 0.18, 70),
            base_result=ScenarioResult(
                scenario,
                PerformanceMetrics(140.0, 8.0, 19.0, 40.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            conservative_result=ScenarioResult(
                scenario,
                PerformanceMetrics(140.0, 8.0, 19.0, 40.0),
                tax_usd=0.0,
                trade_cost_usd=0.0,
                turnover_value_usd=100.0,
            ),
            engine_status="SUCCESS",
            objective_status="REVIEW",
            reasons="monthly_style_validation_warn=return_concentration",
        )

        best = _select_best_candidate(
            [too_defensive, review_candidate],
            validation_pass_by_strategy={"too_defensive": True, "review_candidate": True},
            concentration_ratio_by_strategy={"too_defensive": 19.0, "review_candidate": 22.0},
        )

        self.assertEqual(best.strategy.name, "review_candidate")

    def test_validation_walk_forward_uses_the_candidate_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            rising = [100.0 + index for index in range(1100)]
            _write_price(prices / "SPY_daily.csv", "SPY", rising)
            _write_price(prices / "QQQ_daily.csv", "QQQ", rising)
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,target_weight\n"
                "SPY,SPDR S&P 500 ETF,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n"
                "QQQ,Invesco QQQ Trust,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n",
                encoding="utf-8",
            )
            members = load_universe(universe)
            histories = load_price_history(prices, [member.symbol for member in members])
            strategy = StrategyConfig("candidate_under_test", 70, 84, 1, 0.30, 75)
            benchmark = BenchmarkMetrics(
                candidate_id="fixture",
                row_selector="fixture",
                report_sha256="0" * 64,
                performance=PerformanceMetrics(1.0, 1.0, 50.0, 1.0),
            )

            rows = _monthly_style_validation_rows(
                members,
                histories,
                TaxConfig(),
                benchmark,
                100_000.0,
                strategy,
            )

            walk_rows = [row for row in rows if row["category"] == "walk_forward"]
            self.assertTrue(walk_rows)
            self.assertEqual({row["selected_preset"] for row in walk_rows}, {"candidate_under_test"})

    def test_validation_concentration_warn_downgrades_complete_to_review(self):
        evaluation = ObjectiveEvaluation(
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            core_conditions_passed=True,
            risk_adjusted_passed=True,
            reasons="beats_benchmark_after_costs_and_tax",
        )

        reviewed = _apply_validation_audit_to_objective(
            evaluation,
            [
                {
                    "name": "return_concentration",
                    "status": "WARN",
                    "detail": "full_net_total_return_pct=136.8829; median_walk_forward_net_total_return_pct=6.0597; ratio=22.5890; warn_above=20.0000",
                }
            ],
        )

        self.assertEqual(reviewed.objective_status, "REVIEW")
        self.assertIn("monthly_style_validation_warn=return_concentration", reviewed.reasons)

    def test_validation_block_downgrades_complete_to_not_complete(self):
        evaluation = ObjectiveEvaluation(
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            core_conditions_passed=True,
            risk_adjusted_passed=True,
            reasons="beats_benchmark_after_costs_and_tax",
        )

        reviewed = _apply_validation_audit_to_objective(
            evaluation,
            [
                {"name": "required_scenarios", "status": "BLOCK", "detail": "1 failed of 10 required"},
                {"name": "return_concentration", "status": "WARN", "detail": "ratio=22.5890"},
            ],
        )

        self.assertEqual(reviewed.objective_status, "NOT_COMPLETE")
        self.assertIn("monthly_style_validation_block=required_scenarios", reviewed.reasons)

    def test_validation_concentration_pass_allows_complete_to_stay_complete(self):
        evaluation = ObjectiveEvaluation(
            engine_status="SUCCESS",
            objective_status="COMPLETE",
            core_conditions_passed=True,
            risk_adjusted_passed=True,
            reasons="beats_benchmark_after_costs_and_tax",
        )

        completed = _apply_validation_audit_to_objective(
            evaluation,
            [{"name": "return_concentration", "status": "PASS", "detail": "ratio=12.0000"}],
        )

        self.assertEqual(completed.objective_status, "COMPLETE")

    def test_runner_writes_reports_with_not_complete_status_and_safety_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            _write_price(prices / "SPY_daily.csv", "SPY", [100, 101, 102, 103])
            external = root / "external"
            external.mkdir()
            external.joinpath("factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "SPY,ETF,1.0,0.8,0.5,0.7,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            external.joinpath("short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "SPY,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            external.joinpath("news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "SPY,2026-06-30,3,0.2,gdelt_alpha_vantage_proxy\n",
                encoding="utf-8",
            )
            external.joinpath("listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "SPY,SPDR S&P 500 ETF,NYSEARCA,ETF,1993-01-22,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,target_weight\n"
                "SPY,SPDR S&P 500 ETF,ETF,2026-01-01,,fixture,true,current universe fixture,1.0\n",
                encoding="utf-8",
            )
            benchmark = root / "benchmark.csv"
            benchmark.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=99.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-1.0000\n"
                "return_concentration,WARN,full_excess_pct=99.0000; median_walk_forward_excess_pct=9.0000; ratio=11.0000\n",
                encoding="utf-8",
            )

            result = run_auto_paper_run(
                prices_dir=prices,
                universe_path=universe,
                benchmark_report=benchmark,
                benchmark_row_selector="name=return_concentration",
                output_dir=root / "out",
                usd_krw_rate=1400.0,
                external_data_dir=external,
            )

            self.assertEqual(result.engine_status, "SUCCESS")
            self.assertEqual(result.objective_status, "NOT_COMPLETE")
            self.assertTrue(result.model_config_path.exists())
            self.assertTrue(result.cost_policy_path.exists())
            model_config = json.loads(result.model_config_path.read_text(encoding="utf-8"))
            self.assertIn("strategy", model_config)
            self.assertEqual(model_config["paper_only"], True)
            self.assertEqual(model_config["execution_allowed"], False)
            cost_policy = result.cost_policy_path.read_text(encoding="utf-8")
            self.assertIn("fee_rate", cost_policy)
            self.assertIn("capital_gains_tax_rate", cost_policy)
            self.assertIn("tax_proxy", cost_policy)
            with (root / "out" / "auto_paper_performance.csv").open(encoding="utf-8") as fp:
                performance_rows = list(csv.DictReader(fp))
            self.assertTrue(performance_rows)
            for row in performance_rows:
                self.assertIn("sharpe_ratio", row)
                self.assertIn("risk_metric_policy", row)
                self.assertIn("volatility_target_symbol", row)
                self.assertIn("volatility_lookback_days", row)
                self.assertIn("target_annual_volatility", row)
                self.assertIn("volatility_min_scale", row)
                self.assertIn("volatility_max_scale", row)
                self.assertEqual(row["risk_metric_policy"], "risk_adjusted_return=calmar_pct;sharpe_ratio=annualized_daily_equity_returns")
                self.assertEqual(row["paper_only"], "True")
                self.assertEqual(row["dry_run"], "True")
                self.assertEqual(row["execution_allowed"], "False")
                self.assertEqual(row["production_effect"], "none")
                self.assertIn("benchmark_report_sha256", row)
                self.assertEqual(len(row["benchmark_report_sha256"]), 64)
            with (root / "out" / "auto_paper_order_plan.csv").open(encoding="utf-8") as fp:
                order_rows = list(csv.DictReader(fp))
            self.assertTrue(order_rows)
            self.assertEqual(len(order_rows[0]["benchmark_report_sha256"]), 64)
            self.assertEqual(order_rows[0]["sector"], "ETF")
            self.assertEqual(order_rows[0]["external_data_policy"], "free_local_csv_only")
            self.assertIn("estimated_market_impact_rate", order_rows[0])
            with (root / "out" / "auto_paper_candidate_sweep.csv").open(encoding="utf-8") as fp:
                sweep_rows = list(csv.DictReader(fp))
            self.assertTrue(sweep_rows)
            self.assertIn("strategy_name", sweep_rows[0])
            self.assertIn("best_model", sweep_rows[0])
            self.assertIn("validation_hard_gates_passed", sweep_rows[0])
            self.assertIn("sharpe_ratio", sweep_rows[0])
            self.assertIn("risk_metric_policy", sweep_rows[0])
            self.assertIn("volatility_target_symbol", sweep_rows[0])
            with (root / "out" / "auto_paper_validation_audit.csv").open(encoding="utf-8") as fp:
                validation_audit_rows = list(csv.DictReader(fp))
            self.assertTrue(validation_audit_rows)
            self.assertIn("required_scenarios", {row["name"] for row in validation_audit_rows})
            with (root / "out" / "auto_paper_validation_scenarios.csv").open(encoding="utf-8") as fp:
                validation_scenario_rows = list(csv.DictReader(fp))
            self.assertTrue(validation_scenario_rows)
            self.assertIn("deployable", validation_scenario_rows[0])
            self.assertIn("sharpe_ratio", validation_scenario_rows[0])
            self.assertIn("risk_metric_policy", validation_scenario_rows[0])
            self.assertIn("volatility_target_symbol", validation_scenario_rows[0])
            audit = json.loads((root / "out" / "auto_paper_audit_log.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["engine_status"], "SUCCESS")
            self.assertEqual(audit["objective_status"], "NOT_COMPLETE")
            self.assertEqual(
                audit["risk_metric_policy"],
                "risk_adjusted_return=calmar_pct;sharpe_ratio=annualized_daily_equity_returns",
            )
            self.assertEqual(audit["return_price_basis"], "adj_close")
            self.assertEqual(audit["trade_price_basis"], "close")
            self.assertEqual(audit["tax_price_basis"], "trade_fill_price")
            self.assertEqual(audit["dividend_tax_policy"], "excluded_v1")
            self.assertTrue(audit["tax_consistency_warning"])
            self.assertEqual(audit["universe_mode"], "current")
            self.assertTrue(audit["survivorship_warning_flag"])
            self.assertEqual(len(audit["benchmark_report_sha256"]), 64)
            self.assertIn("best_model", audit)
            self.assertIn("validation_audit_status", audit)
            self.assertEqual(audit["external_data_policy"], "free_local_csv_only")
            self.assertIn("SEC EDGAR", audit["external_data_sources"])
            self.assertEqual(audit["external_data_dir"], external.as_posix())
            self.assertIn("volatility_target_symbol", audit["strategy"])
            self.assertIn("volatility_lookback_days", audit["strategy"])
            comparison = (root / "out" / "auto_paper_comparison.md").read_text(encoding="utf-8")
            self.assertIn("sharpe_ratio", comparison)
            self.assertIn("risk_metric_policy", comparison)

    def test_runner_can_load_point_in_time_universe_by_as_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            _write_price(prices / "AAPL_daily.csv", "AAPL", [100, 101, 102, 103])
            universe = root / "universe_history.csv"
            universe.write_text(
                "symbol,name,asset_type,exchange,effective_from,effective_to,status,source,survivorship_warning,target_weight\n"
                "AAPL,Apple Inc,EQUITY,NAS,2015-01-01,,active,nasdaq_trader_history,point-in-time source,1.0\n"
                "TSLA,Tesla Inc,EQUITY,NAS,2021-01-01,,active,nasdaq_trader_history,point-in-time source,1.0\n",
                encoding="utf-8",
            )
            benchmark = root / "benchmark.csv"
            benchmark.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=99.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-1.0000\n"
                "return_concentration,WARN,full_excess_pct=99.0000; median_walk_forward_excess_pct=9.0000; ratio=11.0000\n",
                encoding="utf-8",
            )

            result = run_auto_paper_run(
                prices_dir=prices,
                universe_path=universe,
                benchmark_report=benchmark,
                benchmark_row_selector="name=return_concentration",
                output_dir=root / "out",
                usd_krw_rate=1400.0,
                universe_as_of="2020-06-30",
            )

            self.assertEqual(result.engine_status, "SUCCESS")
            with (root / "out" / "auto_paper_order_plan.csv").open(encoding="utf-8") as fp:
                order_rows = list(csv.DictReader(fp))
            self.assertEqual({row["symbol"] for row in order_rows}, {"AAPL"})
            audit = json.loads((root / "out" / "auto_paper_audit_log.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["universe_mode"], "point_in_time")
            self.assertEqual(audit["universe_as_of"], "2020-06-30")
            self.assertFalse(audit["survivorship_warning_flag"])

    def test_runner_can_mark_complete_only_when_all_hard_gates_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            rising = [100.0 + index for index in range(320)]
            _write_price(prices / "SPY_daily.csv", "SPY", rising)
            _write_price(prices / "QQQ_daily.csv", "QQQ", rising)
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,target_weight\n"
                "SPY,SPDR S&P 500 ETF,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n"
                "QQQ,Invesco QQQ Trust,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n",
                encoding="utf-8",
            )
            benchmark = root / "benchmark.csv"
            benchmark.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=1.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-50.0000\n"
                "return_concentration,WARN,full_excess_pct=1.0000; median_walk_forward_excess_pct=0.1000; ratio=10.0000\n",
                encoding="utf-8",
            )

            result = run_auto_paper_run(
                prices_dir=prices,
                universe_path=universe,
                benchmark_report=benchmark,
                benchmark_row_selector="name=return_concentration",
                output_dir=root / "out",
                usd_krw_rate=1400.0,
            )

            self.assertEqual(result.objective_status, "REVIEW")

    def test_runner_selects_best_model_from_candidate_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            rising = [100.0 + index for index in range(360)]
            _write_price(prices / "SPY_daily.csv", "SPY", rising)
            _write_price(prices / "QQQ_daily.csv", "QQQ", rising)
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,target_weight\n"
                "SPY,SPDR S&P 500 ETF,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n"
                "QQQ,Invesco QQQ Trust,ETF,2026-01-01,,fixture,true,current universe fixture,0.5\n",
                encoding="utf-8",
            )
            benchmark = root / "benchmark.csv"
            benchmark.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=1.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-50.0000\n"
                "return_concentration,WARN,full_excess_pct=1.0000; median_walk_forward_excess_pct=0.1000; ratio=10.0000\n",
                encoding="utf-8",
            )

            result = run_auto_paper_run(
                prices_dir=prices,
                universe_path=universe,
                benchmark_report=benchmark,
                benchmark_row_selector="name=return_concentration",
                output_dir=root / "out",
                usd_krw_rate=1400.0,
            )

            self.assertEqual(result.objective_status, "REVIEW")
            with (root / "out" / "auto_paper_candidate_sweep.csv").open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            best_rows = [row for row in rows if row["best_model"] == "True"]
            self.assertEqual(len(best_rows), 1)
            self.assertEqual(best_rows[0]["objective_status"], "REVIEW")
            self.assertIn("monthly_style_validation_warn=return_concentration", best_rows[0]["reasons"])

    def test_runner_fails_closed_when_price_rows_are_not_usable_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            (prices / "SPY_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-01-28,SPY,100,100,100,100,100,1000,yahoo,2026-01-30T06:00:00+09:00\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,target_weight\n"
                "SPY,SPDR S&P 500 ETF,ETF,2026-01-01,,fixture,true,current universe fixture,1.0\n",
                encoding="utf-8",
            )
            benchmark = root / "benchmark.csv"
            benchmark.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=1.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-50.0000\n"
                "return_concentration,WARN,full_excess_pct=1.0000; median_walk_forward_excess_pct=0.1000; ratio=10.0000\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                run_auto_paper_run(
                    prices_dir=prices,
                    universe_path=universe,
                    benchmark_report=benchmark,
                    benchmark_row_selector="name=return_concentration",
                    output_dir=root / "out",
                    usd_krw_rate=1400.0,
                    decision_time_kst=datetime.fromisoformat("2026-01-29T06:00:00+09:00"),
                )


if __name__ == "__main__":
    unittest.main()
