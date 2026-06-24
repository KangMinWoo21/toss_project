import os
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.readiness import (
    evaluate_readiness,
    recommend_readiness_actions,
    readiness_exit_code,
    readiness_status,
    save_readiness_markdown,
    save_readiness_report,
)


class ProductionReadinessTests(unittest.TestCase):
    def test_missing_required_artifact_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.csv"

            checks = evaluate_readiness(required_artifacts=[missing])

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "artifact:missing.csv")
        self.assertEqual(checks[0].status, "BLOCK")

    def test_non_deployable_gate_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            gate = Path(temp_dir) / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "False,failed_required_scenarios,monthly-validate,0,0,0,0,0,False\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(deployment_gate_path=gate)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "deployment_gate")
        self.assertIn("failed_required_scenarios", checks[0].detail)

    def test_validation_scenario_failures_block_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,required,deployable,reason,universe_bias_reasons\n"
                "full_period,True,False,universe_bias_warning,high_average_symbol_return;extreme_return_share\n"
                "stress_drawdown,True,False,max_drawdown_breach\n"
                "duration_3m,True,True,passed\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "validation_scenarios")
        self.assertIn("full_period", checks[0].detail)
        self.assertIn("universe_bias_warning=1", checks[0].detail)
        self.assertIn("max_drawdown_breach=1", checks[0].detail)
        self.assertIn("extreme_return_share=1", checks[0].detail)

    def test_walk_forward_single_train_candidate_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores\n"
                "walk_forward_001,walk_forward,True,True,passed,\"balanced:excess=1,drawdown=-5,trades=3,score=-4\"\n"
                "full_period,duration,True,True,passed,\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "WARN")
        self.assertIn("under_covered=1", coverage_checks[0].detail)
        self.assertEqual(readiness_status(checks), "WARN")

    def test_walk_forward_multiple_train_candidates_passes_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores\n"
                "walk_forward_001,walk_forward,True,True,passed,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4; "
                "defensive:excess=2,drawdown=-3,trades=4,score=-1\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "PASS")

    def test_walk_forward_duplicate_train_candidate_scores_warn_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores\n"
                "walk_forward_001,walk_forward,True,True,passed,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4; "
                "aggressive:excess=1,drawdown=-5,trades=3,score=-4\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "WARN")
        self.assertIn("low_diversity=1", coverage_checks[0].detail)

    def test_walk_forward_fallback_only_train_profiles_warn_readiness(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores,train_candidate_decision_profiles\n"
                "walk_forward_001,walk_forward,True,True,passed,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4; defensive:excess=2,drawdown=-3,trades=4,score=-1\","
                "\"balanced:modes=market_beta_proxy:3,selected=market_beta_proxy:3,alpha_ratio=0; "
                "defensive:modes=market_beta_proxy:3,selected=market_beta_proxy:3,alpha_ratio=0\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "WARN")
        self.assertIn("fallback_only=1", coverage_checks[0].detail)

    def test_walk_forward_single_fallback_candidate_counts_as_fallback_only(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores,train_candidate_decision_profiles\n"
                "walk_forward_001,walk_forward,True,True,passed,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4\","
                "\"balanced:modes=market_beta_proxy:3,selected=market_beta_proxy:3,alpha_ratio=0\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "WARN")
        self.assertIn("under_covered=1", coverage_checks[0].detail)
        self.assertIn("fallback_only=1", coverage_checks[0].detail)
        self.assertEqual(coverage_checks[0].detail.count("walk_forward_001:1/1"), 1)

    def test_walk_forward_fallback_only_with_negative_direct_scores_reports_ineligible_alpha(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores,train_candidate_decision_profiles,train_candidate_direct_scores\n"
                "walk_forward_001,walk_forward,True,False,train_window_rejected,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4\","
                "\"balanced:modes=market_beta_proxy:3,selected=market_beta_proxy:3,alpha_ratio=0\","
                "\"balanced:excess=-4,drawdown=-8,trades=3,score=-12; aggressive:excess=-2,drawdown=-9,trades=2,score=-11\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)

        coverage_checks = [check for check in checks if check.name == "walk_forward_train_candidate_coverage"]
        self.assertEqual(coverage_checks[0].status, "WARN")
        self.assertIn("fallback_only=1", coverage_checks[0].detail)
        self.assertIn("direct_alpha_ineligible=1", coverage_checks[0].detail)

    def test_walk_forward_direct_alpha_ineligible_recommends_train_alpha_diagnosis(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores,train_candidate_decision_profiles,train_candidate_direct_scores\n"
                "walk_forward_001,walk_forward,True,False,train_window_rejected,"
                "\"balanced:excess=1,drawdown=-5,trades=3,score=-4\","
                "\"balanced:modes=market_beta_proxy:3,selected=market_beta_proxy:3,alpha_ratio=0\","
                "\"balanced:excess=-4,drawdown=-8,trades=3,score=-12\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)
            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Diagnose walk-forward train alpha weakness", action_text)
        self.assertIn("direct_alpha_ineligible=1", action_text)

    def test_walk_forward_train_candidate_warning_recommends_candidate_expansion(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,category,required,deployable,reason,train_candidate_scores\n"
                "walk_forward_001,walk_forward,True,True,passed,\"balanced:excess=1,drawdown=-5,trades=3,score=-4\"\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_scenarios_path=scenarios)
            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Expand walk-forward train candidates", action_text)
        self.assertIn("under_covered=1", action_text)

    def test_risk_report_block_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            risk = Path(temp_dir) / "risk.csv"
            risk.write_text(
                "name,status,detail\n"
                "deployment_gate,BLOCK,gate blocked\n"
                "orders,PASS,valid\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(risk_report_path=risk)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "risk_report")
        self.assertIn("deployment_gate", checks[0].detail)

    def test_performance_report_warning_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            performance = Path(temp_dir) / "performance.csv"
            performance.write_text(
                "name,status,detail\n"
                "walk_forward_margin,WARN,min_walk_forward_excess_pct=3.2\n"
                "required_scenarios,PASS,0 failed\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(performance_report_path=performance)

        self.assertEqual(readiness_status(checks), "WARN")
        self.assertEqual(checks[0].name, "performance_report")
        self.assertIn("walk_forward_margin", checks[0].detail)

    def test_missing_performance_concentration_report_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "monthly_performance_concentration.csv"

            checks = evaluate_readiness(performance_concentration_path=missing)

        concentration = [check for check in checks if check.name == "performance_concentration"][0]
        self.assertEqual(concentration.status, "WARN")
        self.assertIn("missing", concentration.detail)

    def test_performance_concentration_block_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "concentration.csv"
            report.write_text(
                "source,concentration_status,concentration_reasons,top_1_month_contribution\n"
                "unit,BLOCK,top_1_month_contribution,0.9\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(performance_concentration_path=report)

        self.assertEqual(readiness_status(checks), "BLOCK")
        concentration = [check for check in checks if check.name == "performance_concentration"][0]
        self.assertIn("top_1_month_contribution", concentration.detail)

    def test_performance_concentration_wrong_source_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "concentration.csv"
            report.write_text(
                "source,concentration_status,concentration_reasons,top_1_month_contribution,top_5_symbol_contribution\n"
                "monthly-backtest:2024-01-02..2024-03-01,PASS,,0.1,0.2\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(performance_concentration_path=report)

        concentration = [check for check in checks if check.name == "performance_concentration"][0]
        self.assertEqual(concentration.status, "WARN")
        self.assertIn("unexpected_source", concentration.detail)

    def test_recommend_readiness_actions_splits_performance_bottlenecks(self):
        with TemporaryDirectory() as temp_dir:
            performance = Path(temp_dir) / "performance.csv"
            performance.write_text(
                "name,status,detail\n"
                "walk_forward_margin,WARN,min_walk_forward_excess_pct=3.2; warn_below=5.0\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-22.1; warn_at_or_below=-20.0\n"
                "return_concentration,WARN,full_excess_pct=173.8; median_walk_forward_excess_pct=5.9; ratio=29.3\n",
                encoding="utf-8",
            )
            checks = evaluate_readiness(performance_report_path=performance)

            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Improve walk-forward margin", action_text)
        self.assertIn("Reduce drawdown pressure", action_text)
        self.assertIn("Reduce return concentration", action_text)

    def test_validation_failure_report_adds_actionable_readiness_check(self):
        with TemporaryDirectory() as temp_dir:
            failures = Path(temp_dir) / "monthly_validation_failures.csv"
            failures.write_text(
                "name,category,reason,severity,failed_metric,metric_value,threshold,suggested_action,parameter_hints\n"
                "stress,stress,max_drawdown_breach,BLOCK,max_drawdown_pct,-28,-25,REDUCE_DRAWDOWN,lower max_position_weight\n"
                "walk,walk_forward,negative_excess_return,BLOCK,excess_return_pct,-5,0,IMPROVE_WEAK_WINDOW_DEFENSE,increase cash_buffer_weight\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_failures_path=failures)
            actions = recommend_readiness_actions(checks)

        failure_checks = [check for check in checks if check.name == "validation_failure_actions"]
        self.assertEqual(failure_checks[0].status, "BLOCK")
        self.assertIn("REDUCE_DRAWDOWN=1", failure_checks[0].detail)
        self.assertIn("IMPROVE_WEAK_WINDOW_DEFENSE=1", failure_checks[0].detail)
        self.assertIn("stress:max_drawdown_breach", failure_checks[0].detail)
        self.assertIn("walk:negative_excess_return", failure_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Apply validation failure playbook", action_text)
        self.assertIn("lower max_position_weight", action_text)
        self.assertIn("increase cash_buffer_weight", action_text)

    def test_missing_drawdown_attribution_warns_when_drawdown_failure_exists(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            failures = root / "monthly_validation_failures.csv"
            monthly = root / "monthly_drawdown_attribution.csv"
            symbols = root / "monthly_symbol_attribution.csv"
            failures.write_text(
                "name,category,reason,severity,failed_metric,metric_value,threshold,suggested_action,parameter_hints\n"
                "stress,stress,max_drawdown_breach,BLOCK,max_drawdown_pct,-28,-25,REDUCE_DRAWDOWN,lower exposure\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                validation_failures_path=failures,
                drawdown_attribution_path=monthly,
                symbol_attribution_path=symbols,
            )

        attribution = [check for check in checks if check.name == "drawdown_attribution"]
        self.assertEqual(attribution[0].status, "WARN")
        self.assertIn("missing", attribution[0].detail)
        self.assertIn("monthly_drawdown_attribution.csv", attribution[0].detail)

    def test_drawdown_attribution_summarizes_worst_month_and_symbol(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            monthly = root / "monthly_drawdown_attribution.csv"
            symbols = root / "monthly_symbol_attribution.csv"
            monthly.write_text(
                "month,start_date,end_date,start_equity,end_equity,equity_change,return_pct,worst_equity,worst_drawdown_pct,status\n"
                "2026-03,2026-03-02,2026-03-31,1500,1100,-400,-26.6667,1100,-26.6667,LOSS\n"
                "2026-04,2026-04-01,2026-04-30,1100,1200,100,9.0909,1080,-28,GAIN\n",
                encoding="utf-8",
            )
            symbols.write_text(
                "symbol,realized_pnl,realized_return_pct,buy_value,sell_value,quantity_bought,quantity_sold,open_quantity,unmatched_sell_quantity,trade_count,first_trade_date,last_trade_date,status\n"
                "AAA,-10,-1,100,90,1,1,0,0,2,2026-03-01,2026-03-31,LOSS\n"
                "BBB,-250,-25,1000,750,10,10,0,0,4,2026-03-01,2026-03-31,LOSS\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                drawdown_attribution_path=monthly,
                symbol_attribution_path=symbols,
            )

        attribution = [check for check in checks if check.name == "drawdown_attribution"]
        self.assertEqual(attribution[0].status, "PASS")
        self.assertIn("worst_month=2026-03", attribution[0].detail)
        self.assertIn("worst_drawdown_pct=-28", attribution[0].detail)
        self.assertIn("worst_symbol=BBB", attribution[0].detail)

    def test_validation_remediation_report_adds_experiment_check(self):
        with TemporaryDirectory() as temp_dir:
            remediation = Path(temp_dir) / "monthly_validation_remediation.csv"
            remediation.write_text(
                "priority,suggested_action,failure_count,blocked_count,affected_categories,affected_scenarios,failed_metrics,worst_metric_value,parameter_hints,next_experiment\n"
                "P1,IMPROVE_WEAK_WINDOW_DEFENSE,3,3,regime; walk_forward,regime_sideways; walk_forward_005,excess_return_pct,-7.1648,increase cash_buffer_weight,Run weak-window sweep\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_remediation_path=remediation)
            actions = recommend_readiness_actions(checks)

        remediation_checks = [check for check in checks if check.name == "validation_remediation"]
        self.assertEqual(remediation_checks[0].status, "BLOCK")
        self.assertIn("IMPROVE_WEAK_WINDOW_DEFENSE", remediation_checks[0].detail)
        self.assertIn("Run weak-window sweep", remediation_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Run validation remediation experiments", action_text)

    def test_validation_sweep_plan_report_adds_pending_experiment_check(self):
        with TemporaryDirectory() as temp_dir:
            sweep = Path(temp_dir) / "monthly_validation_sweep_plan.csv"
            sweep.write_text(
                "priority,suggested_action,experiment_id,target_scenarios,cash_buffer_weight,min_train_positive_ratio,candidate_pool_size,max_position_weight,drawdown_guard_scale,market_volatility_min_scale,expected_effect,risk_note\n"
                "P1,IMPROVE_WEAK_WINDOW_DEFENSE,weak_defense_cash_05,regime_sideways,0.05,0.55,5,,,,Reduce weak-window exposure,Re-run validation before adopting\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_sweep_plan_path=sweep)
            actions = recommend_readiness_actions(checks)

        sweep_checks = [check for check in checks if check.name == "validation_sweep_plan"]
        self.assertEqual(sweep_checks[0].status, "WARN")
        self.assertIn("weak_defense_cash_05", sweep_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Review validation sweep plan", action_text)

    def test_validation_sweep_results_report_adds_review_check(self):
        with TemporaryDirectory() as temp_dir:
            results = Path(temp_dir) / "monthly_validation_sweep_results.csv"
            results.write_text(
                "experiment_id,suggested_action,status,target_scenarios,scenario_count,failed_required,baseline_failed_required,failed_delta,min_excess_return_pct,worst_drawdown_pct,trade_count,config_changes,candidate_validation_args,validation_scope,adoption_status,adoption_requirements,result_summary,risk_note\n"
                "weak_defense_cash_05,IMPROVE_WEAK_WINDOW_DEFENSE,IMPROVED,regime_sideways,1,0,1,-1,1.2,-8,1,cash_buffer_weight=0.05,--cash-buffer-weight 0.05,TARGET_ONLY,FULL_VALIDATION_REQUIRED,Run monthly-validate and compare,failed_required 1 -> 0,Re-run full validation before adopting\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_sweep_results_path=results)
            actions = recommend_readiness_actions(checks)

        result_checks = [check for check in checks if check.name == "validation_sweep_results"]
        self.assertEqual(result_checks[0].status, "WARN")
        self.assertIn("IMPROVED=1", result_checks[0].detail)
        self.assertIn("weak_defense_cash_05", result_checks[0].detail)
        self.assertIn("improved=weak_defense_cash_05", result_checks[0].detail)
        self.assertIn("target_only", result_checks[0].detail)
        self.assertIn("FULL_VALIDATION_REQUIRED", result_checks[0].detail)
        self.assertIn("--cash-buffer-weight 0.05", result_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Review validation sweep results", action_text)

    def test_validation_candidate_followup_report_warns_with_next_commands(self):
        with TemporaryDirectory() as temp_dir:
            followup = Path(temp_dir) / "monthly_validation_candidate_followup.csv"
            followup.write_text(
                "priority_rank,experiment_id,status,adoption_status,failed_delta,candidate_validation_args,candidate_scenario_output,candidate_gate_output,comparison_output,delta_output,decision_output,validation_command,comparison_command,risk_note\n"
                "1,weak_cash_10_position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-2,--cash-buffer-weight 0.1,candidate.csv,gate.csv,comparison.csv,delta.csv,decision.csv,python -m backtester monthly-validate --cash-buffer-weight 0.1,python -m backtester monthly-compare-validation,Plan only\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_followup_path=followup)
            actions = recommend_readiness_actions(checks)

        followup_checks = [check for check in checks if check.name == "validation_candidate_followup"]
        self.assertEqual(followup_checks[0].status, "WARN")
        self.assertIn("weak_cash_10_position_stop_12", followup_checks[0].detail)
        self.assertIn("monthly-validate", followup_checks[0].detail)
        self.assertIn("monthly-compare-validation", followup_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Run candidate follow-up validation", action_text)

    def test_validation_candidate_followup_report_summarizes_completed_decisions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision = root / "candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "weak_cash_10_position_stop_12,REJECT,REJECT,new_failures=3,5,6,1,2,3,3,stress,regime_bear; walk_forward_002,walk_forward_003,selection_or_exposure_drag=2,Do not adopt rejected candidate.\n",
                encoding="utf-8",
            )
            followup = root / "monthly_validation_candidate_followup.csv"
            followup.write_text(
                "priority_rank,experiment_id,status,adoption_status,failed_delta,candidate_validation_args,candidate_scenario_output,candidate_gate_output,comparison_output,delta_output,decision_output,validation_command,comparison_command,risk_note\n"
                f"1,weak_cash_10_position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-2,--cash-buffer-weight 0.1,candidate.csv,gate.csv,comparison.csv,delta.csv,{decision},python -m backtester monthly-validate,python -m backtester monthly-compare-validation,Plan only\n"
                "2,position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-1,--position-trailing-stop-pct -12,candidate2.csv,gate2.csv,comparison2.csv,delta2.csv,missing_decision.csv,python -m backtester monthly-validate --position-trailing-stop-pct -12,python -m backtester monthly-compare-validation,Plan only\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_followup_path=followup)

        followup_checks = [check for check in checks if check.name == "validation_candidate_followup"]
        self.assertEqual(followup_checks[0].status, "WARN")
        self.assertIn("decisions: REJECT=1", followup_checks[0].detail)
        self.assertIn("top_decision=REJECT", followup_checks[0].detail)
        self.assertIn("candidate_failed_required=6", followup_checks[0].detail)
        self.assertIn("completed=1", followup_checks[0].detail)
        self.assertIn("pending=1", followup_checks[0].detail)
        self.assertIn("next_pending=position_stop_12", followup_checks[0].detail)
        self.assertIn("--position-trailing-stop-pct -12", followup_checks[0].detail)

    def test_validation_candidate_followup_omits_commands_when_all_completed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_decision = root / "first_decision.csv"
            first_decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "weak_cash_10_position_stop_12,REJECT,REJECT,new_failures=3,5,6,1,2,3,3,stress,regime_bear; walk_forward_002,walk_forward_003,selection_or_exposure_drag=2,Do not adopt rejected candidate.\n",
                encoding="utf-8",
            )
            second_decision = root / "second_decision.csv"
            second_decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "position_stop_12,REJECT,REJECT,unchanged_failures=5,5,5,0,2,0,5,stress,regime_bear,walk_forward_003,selection_or_exposure_drag=1,Do not adopt rejected candidate.\n",
                encoding="utf-8",
            )
            followup = root / "monthly_validation_candidate_followup.csv"
            followup.write_text(
                "priority_rank,experiment_id,status,adoption_status,failed_delta,candidate_validation_args,candidate_scenario_output,candidate_gate_output,comparison_output,delta_output,decision_output,validation_command,comparison_command,risk_note\n"
                f"1,weak_cash_10_position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-2,--cash-buffer-weight 0.1,candidate.csv,gate.csv,comparison.csv,delta.csv,{first_decision},python -m backtester monthly-validate,python -m backtester monthly-compare-validation,Plan only\n"
                f"2,position_stop_12,IMPROVED,FULL_VALIDATION_REQUIRED,-1,--position-trailing-stop-pct -12,candidate2.csv,gate2.csv,comparison2.csv,delta2.csv,{second_decision},python -m backtester monthly-validate --position-trailing-stop-pct -12,python -m backtester monthly-compare-validation,Plan only\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_followup_path=followup)

        followup_checks = [check for check in checks if check.name == "validation_candidate_followup"]
        detail = followup_checks[0].detail
        self.assertIn("decisions: REJECT=2", detail)
        self.assertIn("completed=2", detail)
        self.assertIn("pending=0", detail)
        self.assertIn("all_candidate_followups_completed", detail)
        self.assertNotIn("validation_command=", detail)
        self.assertNotIn("comparison_command=", detail)
        self.assertNotIn("monthly-validate", detail)

    def test_validation_failure_patterns_block_persistent_failures(self):
        with TemporaryDirectory() as temp_dir:
            patterns = Path(temp_dir) / "monthly_validation_failure_patterns.csv"
            patterns.write_text(
                "scenario,baseline_failed,failed_candidate_count,new_failure_candidate_count,resolved_candidate_count,unchanged_failure_candidate_count,candidate_labels_failed,candidate_labels_new_failure,candidate_labels_resolved,candidate_labels_unchanged,dominant_diagnostic,pattern_status,suggested_action,notes\n"
                "walk_001,True,3,0,0,3,cash_10; stop_12,, ,cash_10; stop_12,same_failure_persists,PERSISTENT_BLOCK,REVIEW_PERSISTENT_FAILURE,failed in every tested candidate\n"
                "walk_002,False,2,2,0,0,cash_10; stop_12,cash_10; stop_12,,,selection_or_exposure_drag,REGRESSION_RISK,AVOID_REGRESSION_CONFIGS,new failure introduced by candidates\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_failure_patterns_path=patterns)
            actions = recommend_readiness_actions(checks)

        pattern_checks = [check for check in checks if check.name == "validation_failure_patterns"]
        self.assertEqual(pattern_checks[0].status, "BLOCK")
        self.assertIn("PERSISTENT_BLOCK=1", pattern_checks[0].detail)
        self.assertIn("REGRESSION_RISK=1", pattern_checks[0].detail)
        self.assertIn("walk_001", pattern_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Analyze persistent validation failures", action_text)

    def test_validation_failure_drilldown_warns_on_missing_attribution_evidence(self):
        with TemporaryDirectory() as temp_dir:
            drilldown = Path(temp_dir) / "monthly_validation_failure_drilldown.csv"
            drilldown.write_text(
                "scenario,pattern_status,likely_root_cause,evidence_gaps,next_action\n"
                "regime_sideways,PERSISTENT_BLOCK,weak_window_return_drag,selected_symbols; exposure; cash_weight,Run scenario attribution before tuning more parameters.\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_failure_drilldown_path=drilldown)
            actions = recommend_readiness_actions(checks)

        drilldown_checks = [check for check in checks if check.name == "validation_failure_drilldown"]
        self.assertEqual(drilldown_checks[0].status, "WARN")
        self.assertIn("weak_window_return_drag=1", drilldown_checks[0].detail)
        self.assertIn("evidence_gaps=1", drilldown_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Fill validation drilldown evidence gaps", action_text)

    def test_validation_comparison_reject_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            comparison = Path(temp_dir) / "monthly_validation_comparison.csv"
            comparison.write_text(
                "baseline_label,candidate_label,status,baseline_failed_required,candidate_failed_required,failed_delta,resolved_failures,new_failures,unchanged_failures,summary\n"
                "baseline,combo,REJECT,5,6,1,stress,regime_bear; walk_forward_002,walk_forward_003,failed_required 5 -> 6\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_comparison_path=comparison)
            actions = recommend_readiness_actions(checks)

        comparison_checks = [check for check in checks if check.name == "validation_comparison"]
        self.assertEqual(comparison_checks[0].status, "WARN")
        self.assertIn("REJECT", comparison_checks[0].detail)
        self.assertIn("new_failures=regime_bear; walk_forward_002", comparison_checks[0].detail)
        self.assertIn("failed_required 5 -> 6", comparison_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Do not adopt rejected validation candidate", action_text)

    def test_validation_comparison_delta_report_summarizes_new_failure_diagnostics(self):
        with TemporaryDirectory() as temp_dir:
            deltas = Path(temp_dir) / "monthly_validation_comparison_deltas.csv"
            deltas.write_text(
                "name,classification,diagnostic,excess_return_delta,max_drawdown_delta,trade_count_delta\n"
                "stress,RESOLVED,candidate_fixed_required_failure,-2.3,8.9,120\n"
                "regime_bear,NEW_FAILURE,over_defense_or_filter_drag,-7.1,-2.0,54\n"
                "walk_forward_002,NEW_FAILURE,over_defense_or_filter_drag,-4.2,0.5,-22\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_comparison_delta_path=deltas)
            actions = recommend_readiness_actions(checks)

        delta_checks = [check for check in checks if check.name == "validation_comparison_deltas"]
        self.assertEqual(delta_checks[0].status, "WARN")
        self.assertIn("NEW_FAILURE=2", delta_checks[0].detail)
        self.assertIn("RESOLVED=1", delta_checks[0].detail)
        self.assertIn("over_defense_or_filter_drag=2", delta_checks[0].detail)
        self.assertIn("regime_bear", delta_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Review validation scenario deltas", action_text)
        self.assertIn("over_defense_or_filter_drag", action_text)

    def test_validation_candidate_decision_reject_warns_readiness(self):
        with TemporaryDirectory() as temp_dir:
            decision = Path(temp_dir) / "monthly_validation_candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "weak_cash10_stop12,REJECT,REJECT,new_failures=3,5,6,1,2,3,3,stress,regime_bear; walk_forward_002,walk_forward_003,selection_or_exposure_drag=2; train_gate_regression=1,Do not adopt rejected candidate.\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_decision_path=decision)
            actions = recommend_readiness_actions(checks)

        candidate_checks = [check for check in checks if check.name == "validation_candidate_decision"]
        self.assertEqual(candidate_checks[0].status, "WARN")
        self.assertIn("weak_cash10_stop12:REJECT", candidate_checks[0].detail)
        self.assertIn("new_failures=3", candidate_checks[0].detail)
        self.assertIn("regime_bear", candidate_checks[0].detail)
        self.assertIn("selection_or_exposure_drag=2", candidate_checks[0].detail)
        action_text = "\n".join(f"{action.action}: {action.detail}" for action in actions)
        self.assertIn("Do not adopt rejected validation candidate", action_text)

    def test_validation_candidate_decision_paper_review_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            decision = Path(temp_dir) / "monthly_validation_candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "neutral_loss_guard55_min_history244,IMPROVED,PAPER_REVIEW,no_required_failure_regression,1,0,-1,1,0,0,regime_sideways,,,,keep paper-only and complete OOS/post-cutoff review before promotion.\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_decision_path=decision)

        candidate_checks = [check for check in checks if check.name == "validation_candidate_decision"]
        self.assertEqual(candidate_checks[0].status, "BLOCK")
        self.assertIn("neutral_loss_guard55_min_history244:PAPER_REVIEW", candidate_checks[0].detail)
        self.assertIn("promotion_blocked", candidate_checks[0].detail)

    def test_missing_validation_candidate_decision_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            decision = Path(temp_dir) / "missing_candidate_decision.csv"

            checks = evaluate_readiness(validation_candidate_decision_path=decision)

        candidate_checks = [check for check in checks if check.name == "validation_candidate_decision"]
        self.assertEqual(candidate_checks[0].status, "BLOCK")
        self.assertIn("missing", candidate_checks[0].detail)

    def test_accepted_validation_candidate_requires_promotion_proof(self):
        with TemporaryDirectory() as temp_dir:
            decision = Path(temp_dir) / "monthly_validation_candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "manual_accept,IMPROVED,ACCEPT,no_required_failure_regression,1,0,-1,1,0,0,regime_sideways,,,,manual accept without OOS proof.\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_decision_path=decision)

        candidate_checks = [check for check in checks if check.name == "validation_candidate_decision"]
        self.assertEqual(candidate_checks[0].status, "BLOCK")
        self.assertIn("promotion_proof_missing", candidate_checks[0].detail)

    def test_accepted_validation_candidate_with_promotion_proof_passes(self):
        with TemporaryDirectory() as temp_dir:
            decision = Path(temp_dir) / "monthly_validation_candidate_decision.csv"
            decision.write_text(
                "candidate_label,comparison_status,decision,decision_reasons,baseline_failed_required,candidate_failed_required,failed_delta,resolved_count,new_failure_count,unchanged_failure_count,resolved_failure_names,new_failure_names,unchanged_failure_names,new_failure_diagnostics,recommendation\n"
                "manual_accept,IMPROVED,ACCEPT,oos_review_passed;production_readiness_approved,1,0,-1,1,0,0,regime_sideways,,,,manual accept with proof.\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(validation_candidate_decision_path=decision)

        candidate_checks = [check for check in checks if check.name == "validation_candidate_decision"]
        self.assertEqual(candidate_checks[0].status, "PASS")

    def test_stale_validation_reports_block_readiness(self):
        with TemporaryDirectory() as temp_dir:
            performance = Path(temp_dir) / "performance.csv"
            performance.write_text("name,status,detail\nall,PASS,ok\n", encoding="utf-8")
            stale_timestamp = datetime(2026, 1, 1, 9, 0, 0).timestamp()
            os.utime(performance, (stale_timestamp, stale_timestamp))

            checks = evaluate_readiness(
                performance_report_path=performance,
                max_report_age_days=30,
                as_of_date="2026-06-21",
            )

        self.assertEqual(readiness_status(checks), "BLOCK")
        stale_checks = [check for check in checks if check.name == "performance_report_freshness"]
        self.assertEqual(stale_checks[0].status, "BLOCK")
        self.assertIn("exceeds 30d", stale_checks[0].detail)

    def test_stale_dataset_blocks_readiness_when_data_quality_path_is_provided(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "005930.csv").write_text(
                "date,open,high,low,close,volume\n"
                "2026-05-01,100,101,99,100,1000\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                data_quality_path=root,
                max_data_stale_days=7,
                as_of_date="2026-06-21",
            )

        self.assertEqual(readiness_status(checks), "BLOCK")
        data_checks = [check for check in checks if check.name == "data_quality"]
        self.assertEqual(data_checks[0].status, "BLOCK")
        self.assertIn("stale", data_checks[0].detail)

    def test_data_quality_exclusion_report_blocks_when_monthly_reports_lack_marker(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            exclusions = root / "data_quality_excluded_symbols.csv"
            exclusions.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")
            gate = root / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "True,passed,monthly-backtest,0,0,0,0,1,False\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                deployment_gate_path=gate,
                data_quality_exclusions_path=exclusions,
            )

        exclusion_checks = [check for check in checks if check.name == "data_quality_exclusions"]
        self.assertEqual(exclusion_checks[0].status, "BLOCK")
        self.assertIn("lack applied marker", exclusion_checks[0].detail)
        self.assertEqual(readiness_status(checks), "BLOCK")

    def test_data_quality_exclusion_report_passes_when_monthly_reports_have_marker(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            exclusions = root / "data_quality_excluded_symbols.csv"
            exclusions.write_text("symbol,status,reason\n222222,BLOCK,bad data\n", encoding="utf-8")
            gate = root / "gate.csv"
            gate.write_text(
                "deployable,reason,source,total_return_pct,buy_hold_return_pct,excess_return_pct,max_drawdown_pct,trade_count,universe_bias_warning\n"
                "True,passed,monthly-backtest;data_quality_exclusions=auto:data/reports/data_quality_excluded_symbols.csv;excluded_symbols=1,0,0,0,0,1,False\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                deployment_gate_path=gate,
                data_quality_exclusions_path=exclusions,
            )

        exclusion_checks = [check for check in checks if check.name == "data_quality_exclusions"]
        self.assertEqual(exclusion_checks[0].status, "PASS")

    def test_recent_validation_reports_pass_freshness_readiness(self):
        with TemporaryDirectory() as temp_dir:
            performance = Path(temp_dir) / "performance.csv"
            performance.write_text("name,status,detail\nall,PASS,ok\n", encoding="utf-8")
            recent_timestamp = datetime(2026, 6, 20, 9, 0, 0).timestamp()
            os.utime(performance, (recent_timestamp, recent_timestamp))

            checks = evaluate_readiness(
                performance_report_path=performance,
                max_report_age_days=30,
                as_of_date="2026-06-21",
            )

        self.assertEqual(readiness_status(checks), "PASS")
        freshness = [check for check in checks if check.name == "performance_report_freshness"]
        self.assertEqual(freshness[0].status, "PASS")

    def test_readiness_exit_code_can_treat_warn_as_block(self):
        self.assertEqual(readiness_exit_code("PASS"), 0)
        self.assertEqual(readiness_exit_code("WARN"), 0)
        self.assertEqual(readiness_exit_code("WARN", strict=True), 2)
        self.assertEqual(readiness_exit_code("BLOCK"), 2)

    def test_low_universe_price_coverage_blocks_readiness(self):
        with TemporaryDirectory() as temp_dir:
            coverage = Path(temp_dir) / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,20,20,80,20.0,BLOCK,AAA;BBB\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(coverage_report_path=coverage)

        self.assertEqual(readiness_status(checks), "BLOCK")
        self.assertEqual(checks[0].name, "universe_price_coverage")
        self.assertIn("min_coverage_pct=20.0", checks[0].detail)
        self.assertIn("need_to_80pct=60", checks[0].detail)
        self.assertIn("batches_of_50=2", checks[0].detail)

    def test_marginal_universe_price_coverage_warns_with_collection_gap(self):
        with TemporaryDirectory() as temp_dir:
            coverage = Path(temp_dir) / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,83,83,17,83.0,PASS,AAA;BBB\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(coverage_report_path=coverage)
            actions = recommend_readiness_actions(checks)

        self.assertEqual(readiness_status(checks), "WARN")
        self.assertEqual(checks[0].name, "universe_price_coverage")
        self.assertEqual(checks[0].status, "WARN")
        self.assertIn("warning_min_coverage_pct=90.0", checks[0].detail)
        self.assertIn("need_to_90pct=7", checks[0].detail)
        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Expand KRX price coverage", action_text)

    def test_missing_ohlcv_targets_report_lists_top_coverage_plan_symbols(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,83,83,17,83.0,PASS,AAA;BBB\n",
                encoding="utf-8",
            )
            targets = root / "krx_missing_ohlcv_targets.csv"
            targets.write_text(
                "symbol,name,market,missing_snapshots,first_missing_date,last_missing_date\n"
                "000660,Hynix,KOSPI,5,2024-01-31,2024-05-31\n"
                "035420,Naver,KOSPI,3,2024-03-31,2024-05-31\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(
                coverage_report_path=coverage,
                missing_ohlcv_targets_path=targets,
            )

        target_checks = [check for check in checks if check.name == "krx_missing_ohlcv_targets"]
        self.assertEqual(target_checks[0].status, "PASS")
        self.assertIn("targets=2", target_checks[0].detail)
        self.assertIn("top=000660:5; 035420:3", target_checks[0].detail)
        self.assertIn("fetch-pykrx-missing-ohlcv-loop", target_checks[0].detail)

    def test_missing_ohlcv_fetch_plan_summarizes_safe_loop_settings(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fetch_plan = root / "krx_missing_ohlcv_fetch_plan.csv"
            fetch_plan.write_text(
                "plan_id,status,target_count,batch_size,max_batches,planned_batches,planned_symbols,remaining_after_plan,batch_timeout_seconds,batch_pause_seconds,top_symbols,start,end,universe_file,data_dir,targets_output,report_dir,recommended_command,risk_note\n"
                "missing_ohlcv_fetch,READY,397,50,1,1,50,347,300,10,474930:27; 475250:27,2024-01-01,2026-06-18,universe.csv,data/krx_expanded,targets.csv,data/reports,python -m backtester fetch-pykrx-missing-ohlcv-loop --batch-size 50,Plan only\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(missing_ohlcv_fetch_plan_path=fetch_plan)

        plan_checks = [check for check in checks if check.name == "krx_missing_ohlcv_fetch_plan"]
        self.assertEqual(plan_checks[0].status, "PASS")
        self.assertIn("planned_symbols=50", plan_checks[0].detail)
        self.assertIn("remaining_after_plan=347", plan_checks[0].detail)
        self.assertIn("batch_timeout_seconds=300", plan_checks[0].detail)
        self.assertIn("fetch-pykrx-missing-ohlcv-loop", plan_checks[0].detail)

    def test_missing_ohlcv_fetch_plan_warns_when_target_plan_exists_without_fetch_plan(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            targets = root / "targets.csv"
            targets.write_text(
                "symbol,name,market,missing_snapshots,first_missing_date,last_missing_date\n"
                "000660,Hynix,KOSPI,5,2024-01-31,2024-05-31\n",
                encoding="utf-8",
            )
            missing_fetch_plan = root / "missing_fetch_plan.csv"

            checks = evaluate_readiness(
                missing_ohlcv_targets_path=targets,
                missing_ohlcv_fetch_plan_path=missing_fetch_plan,
            )
            actions = recommend_readiness_actions(checks)

        plan_checks = [check for check in checks if check.name == "krx_missing_ohlcv_fetch_plan"]
        self.assertEqual(plan_checks[0].status, "WARN")
        self.assertIn("missing fetch plan", plan_checks[0].detail)
        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Review KRX missing OHLCV fetch plan", action_text)

    def test_missing_ohlcv_fetch_summary_warns_on_failed_or_timed_out_loop(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "krx_missing_ohlcv_fetch_summary.csv"
            summary.write_text(
                "status,attempted_batches,completed_batches,timed_out_batches,failed_batches,saved,remaining_targets,command_count,last_stdout_tail,last_stderr_tail\n"
                "timed_out,2,1,1,0,50,347,2,saved 50,timeout\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(missing_ohlcv_fetch_summary_path=summary)
            actions = recommend_readiness_actions(checks)

        summary_checks = [check for check in checks if check.name == "krx_missing_ohlcv_fetch_summary"]
        self.assertEqual(summary_checks[0].status, "WARN")
        self.assertIn("status=timed_out", summary_checks[0].detail)
        self.assertIn("remaining_targets=347", summary_checks[0].detail)
        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Inspect KRX missing OHLCV fetch result", action_text)

    def test_missing_ohlcv_fetch_summary_passes_when_loop_completed_without_failures(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "krx_missing_ohlcv_fetch_summary.csv"
            summary.write_text(
                "status,attempted_batches,completed_batches,timed_out_batches,failed_batches,saved,remaining_targets,command_count,last_stdout_tail,last_stderr_tail\n"
                "completed,1,1,0,0,50,347,1,saved 50,\n",
                encoding="utf-8",
            )

            checks = evaluate_readiness(missing_ohlcv_fetch_summary_path=summary)

        summary_checks = [check for check in checks if check.name == "krx_missing_ohlcv_fetch_summary"]
        self.assertEqual(summary_checks[0].status, "PASS")
        self.assertIn("saved=50", summary_checks[0].detail)

    def test_missing_ohlcv_targets_warns_when_low_coverage_has_no_plan(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            coverage = root / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2024-01-31,100,83,83,17,83.0,PASS,AAA;BBB\n",
                encoding="utf-8",
            )
            missing_targets = root / "missing_targets.csv"

            checks = evaluate_readiness(
                coverage_report_path=coverage,
                missing_ohlcv_targets_path=missing_targets,
            )
            actions = recommend_readiness_actions(checks)

        target_checks = [check for check in checks if check.name == "krx_missing_ohlcv_targets"]
        self.assertEqual(target_checks[0].status, "WARN")
        self.assertIn("missing target plan", target_checks[0].detail)
        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Create KRX missing OHLCV target plan", action_text)

    def test_save_readiness_reports(self):
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "readiness.csv"
            md_path = Path(temp_dir) / "readiness.md"
            checks = evaluate_readiness(required_artifacts=[])

            saved_csv = save_readiness_report(checks, csv_path)
            save_readiness_markdown(checks, md_path, title="Test Readiness")

            csv_text = csv_path.read_text(encoding="utf-8")
            md_text = md_path.read_text(encoding="utf-8")

        self.assertEqual(saved_csv, 2)
        self.assertIn("overall", csv_text)
        self.assertIn("PASS", csv_text)
        self.assertIn("# Test Readiness", md_text)
        self.assertIn("Overall status: PASS", md_text)

    def test_recommend_readiness_actions_prioritizes_bias_and_drawdown(self):
        with TemporaryDirectory() as temp_dir:
            scenarios = Path(temp_dir) / "scenarios.csv"
            scenarios.write_text(
                "name,required,deployable,reason,universe_bias_reasons\n"
                "full_period,True,False,universe_bias_warning,high_average_symbol_return;extreme_return_share\n"
                "stress_drawdown,True,False,max_drawdown_breach\n",
                encoding="utf-8",
            )
            checks = evaluate_readiness(validation_scenarios_path=scenarios)

            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(action.action for action in actions)
        self.assertIn("Reduce data bias", action_text)
        self.assertIn("Reduce extreme-winner dependence", action_text)
        self.assertIn("Reduce stress drawdown", action_text)

    def test_recommend_readiness_actions_does_not_expand_coverage_when_coverage_passes(self):
        with TemporaryDirectory() as temp_dir:
            coverage = Path(temp_dir) / "coverage.csv"
            coverage.write_text(
                "date,universe_symbols,price_symbols,covered_symbols,missing_symbols,coverage_pct,status,missing_preview\n"
                "2026-01-31,100,90,90,10,90.0,PASS,\n",
                encoding="utf-8",
            )
            checks = evaluate_readiness(coverage_report_path=coverage)

            actions = recommend_readiness_actions(checks)

        action_text = "\n".join(action.action for action in actions)
        self.assertNotIn("Expand KRX price coverage", action_text)


if __name__ == "__main__":
    unittest.main()
