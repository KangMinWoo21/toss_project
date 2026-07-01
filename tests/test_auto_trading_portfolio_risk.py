import csv
import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.portfolio_risk import (
    PortfolioRiskLimits,
    adjust_targets_for_portfolio_risk,
    build_portfolio_risk_rows,
    save_portfolio_risk_reports,
)


class AutoTradingPortfolioRiskTests(unittest.TestCase):
    def test_portfolio_risk_blocks_concentration_beta_news_short_delisting_and_adv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "kis_targets.csv"
            targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.60,True,True,False,none\n"
                "TSLA,NAS,0.30,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,2.10,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n"
                "TSLA,Consumer Discretionary,1.20,0.7,0.2,0.4,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (external / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,500,1000,finra_daily_short_sale_volume\n"
                "TSLA,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (external / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,10,-0.80,gdelt_proxy\n"
                "TSLA,2026-06-30,3,0.10,gdelt_proxy\n",
                encoding="utf-8",
            )
            (external / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n"
                "TSLA,Tesla Inc,NASDAQ,Stock,2010-06-29,2026-06-30,Delisted,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-06-29,AAPL,100,100,100,100,100,1000,yahoo\n"
                "2026-06-30,AAPL,100,100,100,100,100,1000,yahoo\n",
                encoding="utf-8",
            )
            (prices / "TSLA_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-06-29,TSLA,100,100,100,100,100,100000,yahoo\n"
                "2026-06-30,TSLA,100,100,100,100,100,100000,yahoo\n",
                encoding="utf-8",
            )

            rows = build_portfolio_risk_rows(
                targets_path=targets,
                external_data_dir=external,
                prices_dir=prices,
                portfolio_value_usd=1_000_000.0,
                limits=PortfolioRiskLimits(max_single_weight=0.35, max_adv_participation=0.05),
            )

            blocked = {row["check"] for row in rows if row["status"] == "BLOCK"}
            self.assertIn("single_name_weight", blocked)
            self.assertIn("sector_weight", blocked)
            self.assertIn("beta_band", blocked)
            self.assertIn("short_volume_ratio", blocked)
            self.assertIn("news_sentiment", blocked)
            self.assertIn("listing_status", blocked)
            self.assertIn("adv_participation", blocked)
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))

    def test_portfolio_risk_passes_diversified_safe_targets_and_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "kis_targets.csv"
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
                "AAPL,Technology,1.10,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n"
                "MSFT,Software,1.00,0.9,0.5,0.8,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (external / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,100,1000,finra_daily_short_sale_volume\n"
                "MSFT,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (external / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,3,0.20,gdelt_proxy\n"
                "MSFT,2026-06-30,3,0.10,gdelt_proxy\n",
                encoding="utf-8",
            )
            (external / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n"
                "MSFT,Microsoft Corp,NASDAQ,Stock,1986-03-13,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            for symbol in ["AAPL", "MSFT"]:
                (prices / f"{symbol}_daily.csv").write_text(
                    "date,symbol,open,high,low,close,adj_close,volume,source\n"
                    f"2026-06-29,{symbol},100,100,100,100,100,1000000,yahoo\n"
                    f"2026-06-30,{symbol},100,100,100,100,100,1000000,yahoo\n",
                    encoding="utf-8",
                )

            rows = build_portfolio_risk_rows(
                targets_path=targets,
                external_data_dir=external,
                prices_dir=prices,
                portfolio_value_usd=100_000.0,
                limits=PortfolioRiskLimits(max_sector_weight=0.35),
            )
            self.assertTrue(all(row["status"] == "PASS" for row in rows))

            csv_path = root / "risk.csv"
            md_path = root / "risk.md"
            save_portfolio_risk_reports(rows, csv_path, md_path)
            with csv_path.open(encoding="utf-8") as fp:
                written = list(csv.DictReader(fp))
            self.assertEqual(written[0]["paper_only"], "True")
            self.assertIn("Portfolio Risk Gate", md_path.read_text(encoding="utf-8"))

    def test_adjust_targets_removes_symbol_risk_offenders_and_leaves_cash_unallocated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "kis_targets.csv"
            targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.30,True,True,False,none\n"
                "TSLA,NAS,0.20,True,True,False,none\n",
                encoding="utf-8",
            )
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n"
                "TSLA,Consumer Discretionary,2.10,0.7,0.2,0.4,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (external / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,100,1000,finra_daily_short_sale_volume\n"
                "TSLA,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (external / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,3,0.20,gdelt_proxy\n"
                "TSLA,2026-06-30,3,0.10,gdelt_proxy\n",
                encoding="utf-8",
            )
            (external / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n"
                "TSLA,Tesla Inc,NASDAQ,Stock,2010-06-29,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            for symbol in ["AAPL", "TSLA"]:
                (prices / f"{symbol}_daily.csv").write_text(
                    "date,symbol,open,high,low,close,adj_close,volume,source\n"
                    f"2026-06-30,{symbol},100,100,100,100,100,1000000,yahoo\n",
                    encoding="utf-8",
                )

            rows = adjust_targets_for_portfolio_risk(
                targets_path=targets,
                external_data_dir=external,
                prices_dir=prices,
                portfolio_value_usd=100_000.0,
                limits=PortfolioRiskLimits(max_beta=1.80),
            )

            self.assertEqual([row["symbol"] for row in rows], ["AAPL"])
            self.assertEqual(rows[0]["target_weight"], "0.300000")
            self.assertEqual(rows[0]["risk_adjustment"], "kept")
            self.assertEqual(rows[0]["execution_allowed"], "False")


if __name__ == "__main__":
    unittest.main()
