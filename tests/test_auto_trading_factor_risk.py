import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.factor_risk import (
    FactorRiskLimits,
    build_factor_risk_rows,
    save_factor_risk_reports,
)


class AutoTradingFactorRiskTests(unittest.TestCase):
    def test_factor_risk_aggregates_exposures_and_blocks_limit_breaches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "targets.csv"
            targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.60,True,True,False,none\n"
                "MSFT,NAS,0.20,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,2.00,0.90,0.30,0.20,0.80,sec_edgar_proxy,2026-06-30\n"
                "MSFT,Technology,1.00,0.90,0.50,0.80,0.60,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_factor_risk_rows(
                targets_path=targets,
                external_data_dir=external,
                limits=FactorRiskLimits(
                    max_single_weight=0.35,
                    max_sector_weight=0.50,
                    max_weighted_beta=1.20,
                    max_negative_quality_tilt=0.15,
                ),
            )

            by_check = {row["check"]: row for row in rows}
            self.assertEqual(by_check["single_name_exposure"]["status"], "BLOCK")
            self.assertEqual(by_check["sector_exposure"]["status"], "BLOCK")
            self.assertEqual(by_check["weighted_beta"]["status"], "BLOCK")
            self.assertEqual(by_check["quality_tilt"]["status"], "BLOCK")
            self.assertEqual(by_check["weighted_momentum_score"]["status"], "PASS")
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))

    def test_factor_risk_passes_diversified_targets_and_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "targets.csv"
            targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.20,True,True,False,none\n"
                "MSFT,NAS,0.20,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.90,0.50,0.80,0.70,sec_edgar_proxy,2026-06-30\n"
                "MSFT,Software,1.00,0.90,0.55,0.85,0.60,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_factor_risk_rows(targets_path=targets, external_data_dir=external)

            self.assertTrue(all(row["status"] == "PASS" for row in rows))
            csv_path = root / "factor_risk.csv"
            md_path = root / "factor_risk.md"
            save_factor_risk_reports(rows, csv_path, md_path)
            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["paper_only"], "True")
            self.assertIn("Factor Risk Report", md_path.read_text(encoding="utf-8"))

    def test_factor_risk_fails_closed_when_factor_data_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "targets.csv"
            targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.20,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "MSFT,Software,1.00,0.90,0.55,0.85,0.60,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_factor_risk_rows(targets_path=targets, external_data_dir=external)


if __name__ == "__main__":
    unittest.main()
