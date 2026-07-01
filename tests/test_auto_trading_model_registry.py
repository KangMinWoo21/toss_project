import csv
import json
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.model_registry import register_model_release


class AutoTradingModelRegistryTests(unittest.TestCase):
    def test_register_model_release_records_required_audit_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text("date,symbol,close\n2026-06-30,AAPL,100\n", encoding="utf-8")
            universe = root / "universe.csv"
            universe.write_text("symbol,name\nAAPL,Apple\n", encoding="utf-8")
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text("symbol,source\nAAPL,fixture\n", encoding="utf-8")
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "COMPLETE",
                        "best_model": "model_x",
                        "benchmark_report_sha256": "a" * 64,
                        "prices_dir": prices.as_posix(),
                        "universe": universe.as_posix(),
                        "external_data_dir": external.as_posix(),
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            model_config = root / "model_config.json"
            model_config.write_text(json.dumps({"model_id": "model_x"}), encoding="utf-8")
            cost_policy = root / "cost.md"
            cost_policy.write_text("fee_rate\n", encoding="utf-8")
            risk_gate = root / "risk.csv"
            risk_gate.write_text(
                "check,status,detail,paper_only,dry_run,execution_allowed,production_effect\n"
                "beta_band,PASS,ok,True,True,False,none\n",
                encoding="utf-8",
            )
            output = root / "registry.json"

            record = register_model_release(
                audit_log_path=audit,
                model_config_path=model_config,
                cost_policy_path=cost_policy,
                risk_gate_path=risk_gate,
                output_path=output,
                version="v0.1.0",
                rollback_reference="previous:v0.0.9",
            )

            self.assertEqual(record["model_id"], "model_x")
            self.assertEqual(record["version"], "v0.1.0")
            self.assertEqual(record["objective_status"], "COMPLETE")
            self.assertEqual(record["risk_gate_status"], "PASS")
            self.assertEqual(len(record["data_snapshot_sha256"]), 64)
            self.assertEqual(record["benchmark_report_sha256"], "a" * 64)
            self.assertEqual(record["paper_only"], True)
            self.assertEqual(record["rollback_reference"], "previous:v0.0.9")
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(written["model_id"], "model_x")

    def test_register_model_release_fails_when_not_complete_or_risk_gate_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_config = root / "model_config.json"
            model_config.write_text(json.dumps({"model_id": "model_x"}), encoding="utf-8")
            cost_policy = root / "cost.md"
            cost_policy.write_text("fee_rate\n", encoding="utf-8")
            risk_gate = root / "risk.csv"
            risk_gate.write_text(
                "check,status,detail,paper_only,dry_run,execution_allowed,production_effect\n"
                "beta_band,BLOCK,beta too high,True,True,False,none\n",
                encoding="utf-8",
            )
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "REVIEW",
                        "best_model": "model_x",
                        "benchmark_report_sha256": "a" * 64,
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                register_model_release(
                    audit_log_path=audit,
                    model_config_path=model_config,
                    cost_policy_path=cost_policy,
                    risk_gate_path=risk_gate,
                    output_path=root / "registry.json",
                    version="v0.1.0",
                )

    def test_register_model_release_records_model_change_diff_from_previous_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "COMPLETE",
                        "best_model": "model_new",
                        "benchmark_report_sha256": "a" * 64,
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            model_config = root / "model_config.json"
            model_config.write_text(json.dumps({"model_id": "model_new"}), encoding="utf-8")
            cost_policy = root / "cost.md"
            cost_policy.write_text("fee_rate\n", encoding="utf-8")
            risk_gate = root / "risk.csv"
            risk_gate.write_text(
                "check,status,detail,paper_only,dry_run,execution_allowed,production_effect\n"
                "beta_band,PASS,ok,True,True,False,none\n",
                encoding="utf-8",
            )
            previous = root / "previous.json"
            previous.write_text(json.dumps({"model_id": "model_old", "version": "v0.0.1"}), encoding="utf-8")

            record = register_model_release(
                audit_log_path=audit,
                model_config_path=model_config,
                cost_policy_path=cost_policy,
                risk_gate_path=risk_gate,
                output_path=root / "registry.json",
                version="v0.1.0",
                previous_registry_path=previous,
            )

            self.assertIn("model_id:model_old->model_new", record["model_change_diff"])


if __name__ == "__main__":
    unittest.main()
