import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.portfolio_optimizer import (
    PortfolioOptimizationConfig,
    build_optimized_portfolio_rows,
    save_optimized_portfolio_reports,
)


class AutoTradingPortfolioOptimizerTests(unittest.TestCase):
    def test_optimizer_allocates_by_score_under_sector_and_single_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            candidates.write_text(
                "symbol,exchange,alpha_score,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.90,True,True,False,none\n"
                "MSFT,NAS,0.85,True,True,False,none\n"
                "GOOGL,NAS,0.80,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.90,0.50,0.80,0.70,sec_edgar_proxy,2026-06-30\n"
                "MSFT,Technology,1.00,0.90,0.55,0.85,0.60,sec_edgar_proxy,2026-06-30\n"
                "GOOGL,Communication Services,1.05,0.80,0.60,0.75,0.65,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_optimized_portfolio_rows(
                candidates_path=candidates,
                external_data_dir=external,
                config=PortfolioOptimizationConfig(
                    max_total_weight=0.60,
                    max_single_weight=0.30,
                    max_sector_weight=0.40,
                    weight_step=0.10,
                ),
            )

            weights = {row["symbol"]: row["target_weight"] for row in rows}
            self.assertEqual(weights["AAPL"], "0.300000")
            self.assertEqual(weights["MSFT"], "0.100000")
            self.assertEqual(weights["GOOGL"], "0.200000")
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["dry_run"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))
            self.assertTrue(all(row["production_effect"] == "none" for row in rows))

    def test_optimizer_fails_closed_for_unsafe_candidate_or_missing_factor_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            candidates.write_text(
                "symbol,exchange,alpha_score,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.90,True,True,True,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.90,0.50,0.80,0.70,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_optimized_portfolio_rows(candidates_path=candidates, external_data_dir=external)

            candidates.write_text(
                "symbol,exchange,alpha_score,paper_only,dry_run,execution_allowed,production_effect\n"
                "MSFT,NAS,0.80,True,True,False,none\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_optimized_portfolio_rows(candidates_path=candidates, external_data_dir=external)

    def test_optimizer_writes_csv_and_markdown_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            candidates.write_text(
                "symbol,exchange,alpha_score,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.90,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.90,0.50,0.80,0.70,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_optimized_portfolio_rows(
                candidates_path=candidates,
                external_data_dir=external,
                config=PortfolioOptimizationConfig(max_total_weight=0.30, max_single_weight=0.30),
            )
            csv_path = root / "optimized.csv"
            md_path = root / "optimized.md"
            save_optimized_portfolio_reports(rows, csv_path, md_path)

            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["symbol"], "AAPL")
            self.assertEqual(written[0]["execution_allowed"], "False")
            self.assertIn("Portfolio Optimizer", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
