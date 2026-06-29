import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudScriptTests(unittest.TestCase):
    def test_monthly_plan_script_runs_paper_plan_with_required_gates(self):
        script = (ROOT / "scripts/cloud/run_monthly_plan.sh").read_text(encoding="utf-8")

        self.assertIn("monthly-plan", script)
        self.assertIn("--require-performance-report", script)
        self.assertIn("--require-deployment-gate", script)
        self.assertIn("--max-report-age-days", script)
        self.assertIn("--summary-output", script)
        self.assertIn("--point-in-time-universe", script)
        self.assertIn("--event-source-weights", script)
        self.assertIn("production-check", script)
        self.assertIn("READINESS_OUTPUT", script)
        self.assertIn("READINESS_MARKDOWN_OUTPUT", script)
        self.assertIn("--risk-report \"$RISK_OUTPUT\"", script)
        self.assertIn("--allow-blocked-exit-zero", script)
        self.assertIn("monthly_status", script)
        self.assertIn("missing required monthly plan input", script)
        self.assertIn("POINT_IN_TIME_UNIVERSE", script)
        self.assertIn("PERFORMANCE_REPORT", script)
        self.assertIn("DEPLOYMENT_GATE_FILE", script)
        self.assertNotIn("place-order", script)
        self.assertNotIn("live-order", script)

    def test_monthly_plan_service_is_oneshot_and_uses_cloud_script(self):
        service = (ROOT / "scripts/cloud/toss-monthly-plan.service").read_text(encoding="utf-8")

        self.assertIn("Type=oneshot", service)
        self.assertIn("run_monthly_plan.sh", service)
        self.assertIn("DEPLOYMENT_GATE_FILE=data/reports/monthly_deployment_gate_pit_universe.csv", service)
        self.assertIn("MAX_REPORT_AGE_DAYS=45", service)
        self.assertIn("EVENT_SOURCE_WEIGHTS=dart=0.5", service)

    def test_monthly_plan_timer_is_persistent(self):
        timer = (ROOT / "scripts/cloud/toss-monthly-plan.timer").read_text(encoding="utf-8")

        self.assertIn("OnCalendar=*-*-01 09:10:00 Asia/Seoul", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("Unit=toss-monthly-plan.service", timer)

    def test_cloud_report_download_script_fetches_monthly_plan_outputs(self):
        script = (ROOT / "scripts/download_cloud_reports.ps1").read_text(encoding="utf-8")

        self.assertIn("data\\reports_cloud", script)
        self.assertIn("monthly_order_plan_cloud.csv", script)
        self.assertIn("monthly_order_plan_summary_cloud.md", script)
        self.assertIn("monthly_decision_cloud.csv", script)
        self.assertIn("monthly_risk_report_cloud.csv", script)
        self.assertIn("monthly_deployment_gate_pit_universe.csv", script)
        self.assertIn("production_readiness.csv", script)
        self.assertIn("scp", script)
        self.assertIn("IdentityFile", script)
        self.assertIn("scp failed", script)
        self.assertNotIn("place-order", script)
        self.assertNotIn("live-order", script)

    def test_cloud_report_download_task_registers_logon_sync(self):
        script = (ROOT / "scripts/register_cloud_reports_download_task.ps1").read_text(encoding="utf-8")

        self.assertIn("TossMonthlyReportsDownload", script)
        self.assertIn("download_cloud_reports.ps1", script)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", script)
        self.assertIn("IdentityFile", script)
        self.assertIn("reports_cloud", script)

    def test_health_check_cloud_script_runs_health_cli(self):
        script = (ROOT / "scripts/cloud/run_health_check.sh").read_text(encoding="utf-8")

        self.assertIn("health-check", script)
        self.assertIn("health_status.json", script)
        self.assertIn("health_status.md", script)
        self.assertIn("MAX_REPORT_AGE_HOURS", script)


if __name__ == "__main__":
    unittest.main()
