import tempfile
import unittest
from pathlib import Path

from backtester.monthly_momentum_overlay import (
    OverlayTrial,
    build_monthly_momentum_overlay_report,
    evaluate_overlay_trial,
    load_overlay_trials,
    load_champion_metrics,
    save_monthly_momentum_overlay_markdown,
    save_monthly_momentum_overlay_report,
)


class MonthlyMomentumOverlayTests(unittest.TestCase):
    def test_load_champion_metrics_from_performance_audit(self):
        metrics = load_champion_metrics(
            "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
        )

        self.assertEqual(metrics.required_failures, 0)
        self.assertAlmostEqual(metrics.min_required_excess_pct, 0.8313, places=4)
        self.assertAlmostEqual(metrics.worst_max_drawdown_pct, -21.7069, places=4)
        self.assertAlmostEqual(metrics.full_excess_pct, 120.0483, places=4)
        self.assertAlmostEqual(metrics.median_walk_forward_excess_pct, 4.4114, places=4)
        self.assertAlmostEqual(metrics.return_concentration_ratio, 27.2132, places=4)

    def test_accepts_candidate_that_improves_median_without_worse_risk(self):
        metrics = load_champion_metrics(
            "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
        )
        trial = OverlayTrial(
            candidate_id="monthly_momentum_overlay_v0_cap10",
            overlay_cap=0.10,
            validation_evidence="validated",
            required_failures=0,
            min_required_excess_pct=1.25,
            worst_max_drawdown_pct=-21.0,
            full_excess_pct=115.0,
            median_walk_forward_excess_pct=5.0,
            return_concentration_ratio=23.0,
        )

        result = evaluate_overlay_trial(metrics, trial)

        self.assertEqual(result.status, "PAPER_DIAGNOSTIC_PASS")
        self.assertEqual(result.adoption_status, "FULL_VALIDATION_REQUIRED")
        self.assertEqual(result.trading_allowed, "False")
        self.assertEqual(result.production_effect, "none")

    def test_rejects_candidate_with_worse_drawdown(self):
        metrics = load_champion_metrics(
            "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
        )
        trial = OverlayTrial(
            candidate_id="monthly_momentum_overlay_v0_cap25",
            overlay_cap=0.25,
            validation_evidence="validated",
            required_failures=0,
            min_required_excess_pct=2.0,
            worst_max_drawdown_pct=-22.0,
            full_excess_pct=125.0,
            median_walk_forward_excess_pct=5.5,
            return_concentration_ratio=20.0,
        )

        result = evaluate_overlay_trial(metrics, trial)

        self.assertEqual(result.status, "REJECT")
        self.assertIn("worse_drawdown", result.reasons)
        self.assertEqual(result.trading_allowed, "False")
        self.assertEqual(result.production_effect, "none")

    def test_build_and_save_report_rows_are_paper_only(self):
        metrics = load_champion_metrics(
            "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
        )
        rows = build_monthly_momentum_overlay_report(
            metrics,
            [
                OverlayTrial(
                    candidate_id="monthly_momentum_overlay_v0_cap10",
                    overlay_cap=0.10,
                    validation_evidence="validated",
                    required_failures=0,
                    min_required_excess_pct=1.25,
                    worst_max_drawdown_pct=-21.0,
                    full_excess_pct=115.0,
                    median_walk_forward_excess_pct=5.0,
                    return_concentration_ratio=23.0,
                )
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trading_allowed"], "False")
        self.assertEqual(rows[0]["production_effect"], "none")
        self.assertEqual(rows[0]["champion_candidate_id"], "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "overlay.csv"
            save_monthly_momentum_overlay_report(rows, output)
            saved = output.read_text(encoding="utf-8")

        self.assertIn("monthly_momentum_overlay_v0_cap10", saved)
        self.assertIn("PAPER_DIAGNOSTIC_PASS", saved)

    def test_load_overlay_trials_and_save_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_csv = Path(tmpdir) / "trials.csv"
            input_csv.write_text(
                "candidate_id,overlay_cap,validation_evidence,required_failures,min_required_excess_pct,worst_max_drawdown_pct,"
                "full_excess_pct,median_walk_forward_excess_pct,return_concentration_ratio\n"
                "monthly_momentum_overlay_v0_cap10,0.10,validated,0,1.25,-21.0,115.0,5.0,23.0\n",
                encoding="utf-8",
            )
            trials = load_overlay_trials(input_csv)
            rows = build_monthly_momentum_overlay_report(
                load_champion_metrics(
                    "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
                ),
                trials,
            )
            markdown = Path(tmpdir) / "overlay.md"
            save_monthly_momentum_overlay_markdown(rows, markdown)
            text = markdown.read_text(encoding="utf-8")

        self.assertEqual(trials[0].candidate_id, "monthly_momentum_overlay_v0_cap10")
        self.assertIn("Monthly Momentum Overlay", text)
        self.assertIn("trading_allowed=False", text)

    def test_unvalidated_trial_needs_validation_even_if_metrics_look_better(self):
        metrics = load_champion_metrics(
            "data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv"
        )
        trial = OverlayTrial(
            candidate_id="monthly_momentum_overlay_v0_cap10",
            overlay_cap=0.10,
            validation_evidence="trial_input_only",
            required_failures=0,
            min_required_excess_pct=1.25,
            worst_max_drawdown_pct=-21.0,
            full_excess_pct=115.0,
            median_walk_forward_excess_pct=5.0,
            return_concentration_ratio=23.0,
        )

        result = evaluate_overlay_trial(metrics, trial)

        self.assertEqual(result.status, "NEEDS_VALIDATION")
        self.assertEqual(result.adoption_status, "FULL_VALIDATION_REQUIRED")
        self.assertIn("validation_evidence_not_validated", result.reasons)


if __name__ == "__main__":
    unittest.main()
