import unittest

from backtester.macro_overlay import (
    DISABLED_OVERLAY_CONFIG,
    EventRiskObservation,
    MacroObservation,
    MacroOverlayRegimeReport,
    RiskScore,
    SentimentObservation,
    combine_risk_scores,
)


class MacroOverlaySchemaTest(unittest.TestCase):
    def test_combine_risk_scores_uses_maximum_bucket(self):
        self.assertEqual(
            combine_risk_scores([RiskScore.NORMAL, RiskScore.RISK_OFF, RiskScore.CAUTION]),
            RiskScore.PANIC,
        )

    def test_combine_risk_scores_ignores_missing_inputs_without_lowering_risk(self):
        self.assertEqual(
            combine_risk_scores([None, RiskScore.RISK_OFF]),
            RiskScore.RISK_OFF,
        )

    def test_combine_risk_scores_defaults_to_normal_when_all_inputs_missing(self):
        self.assertEqual(combine_risk_scores([None, None]), RiskScore.NORMAL)

    def test_combine_risk_scores_rejects_unknown_bucket(self):
        with self.assertRaises(ValueError):
            combine_risk_scores(["stress"])

    def test_schema_stubs_preserve_point_in_time_fields(self):
        macro = MacroObservation(
            observation_date="2026-06-26",
            usable_from="2026-06-27T09:00:00+09:00",
            source="cboe",
            series_id="VIX",
            region="US",
            value=21.5,
            unit="index",
            transform="raw",
            risk_bucket=RiskScore.CAUTION,
        )
        event = EventRiskObservation(
            event_date="2026-06-26",
            visible_at="2026-06-26T16:00:00+09:00",
            usable_from="2026-06-27T09:00:00+09:00",
            scope="market",
            source="manual_calendar",
            event_type="macro_release",
            severity="1",
            direction="mixed",
            risk_bucket=RiskScore.CAUTION,
        )
        sentiment = SentimentObservation(
            collected_at="2026-06-26T15:05:00+09:00",
            visible_at="2026-06-26T15:05:00+09:00",
            usable_from="2026-06-26T15:10:00+09:00",
            source="google-news",
            scope="market",
            sentiment_score=-0.4,
            importance_score=0.8,
            risk_bucket=RiskScore.CAUTION,
        )

        self.assertEqual(macro.usable_from, "2026-06-27T09:00:00+09:00")
        self.assertEqual(event.visible_at, "2026-06-26T16:00:00+09:00")
        self.assertEqual(sentiment.collected_at, "2026-06-26T15:05:00+09:00")

    def test_regime_report_is_research_only_and_disabled_by_default(self):
        report = MacroOverlayRegimeReport(
            as_of_date="2026-06-29",
            usable_from="2026-06-30T09:00:00+09:00",
            candidate_label="proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244",
            baseline_strategy="monthly_rebalance",
            macro_risk_score=RiskScore.CAUTION,
            event_risk_score=RiskScore.NORMAL,
            sentiment_risk_score=RiskScore.NORMAL,
        )

        self.assertEqual(report.overlay_config, DISABLED_OVERLAY_CONFIG)
        self.assertEqual(report.production_effect, "none")
        self.assertEqual(report.combined_risk_score, RiskScore.CAUTION)
        self.assertEqual(report.recommended_action, "observe_only")


if __name__ == "__main__":
    unittest.main()
