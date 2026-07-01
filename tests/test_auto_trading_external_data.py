import tempfile
import unittest
from pathlib import Path

from backtester.auto_trading.external_data import (
    ExternalDataBundle,
    build_external_data_readiness_rows,
    estimate_liquidity_impact,
    load_external_data_bundle,
    save_external_data_readiness_reports,
)


class AutoTradingExternalDataTests(unittest.TestCase):
    def test_external_data_bundle_loads_free_csv_sources_and_scores_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.2,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (root / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,200000,1000000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (root / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,12,-0.4,gdelt_alpha_vantage_proxy\n",
                encoding="utf-8",
            )
            (root / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )

            bundle = load_external_data_bundle(root, ["AAPL"])
            row = bundle.symbol_rows["AAPL"]

            self.assertEqual(row.sector, "Technology")
            self.assertAlmostEqual(row.short_volume_ratio, 0.2)
            self.assertEqual(row.news_article_count, 12)
            self.assertAlmostEqual(row.news_sentiment_score, -0.4)
            self.assertFalse(row.delisted)
            self.assertTrue(row.paper_only)
            self.assertTrue(row.dry_run)
            self.assertFalse(row.execution_allowed)
            self.assertEqual(row.production_effect, "none")
            self.assertIn("SEC EDGAR", bundle.policy.free_data_sources)
            self.assertIn("FINRA Daily Short Sale Volume", bundle.policy.free_data_sources)
            self.assertIn("GDELT", bundle.policy.free_data_sources)

    def test_external_data_bundle_fails_closed_for_missing_source_or_unknown_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.2,0.9,0.4,0.8,0.7,,2026-06-30\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_external_data_bundle(root, ["AAPL"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "MSFT,Technology,1.1,0.8,0.5,0.7,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_external_data_bundle(root, ["AAPL"])

    def test_liquidity_impact_uses_adv_and_volatility_proxies(self):
        bundle = ExternalDataBundle.empty()

        impact = estimate_liquidity_impact(
            symbol="AAPL",
            order_value_usd=200_000.0,
            average_daily_dollar_volume=10_000_000.0,
            annualized_volatility=0.25,
            bundle=bundle,
        )

        self.assertGreater(impact.estimated_impact_rate, 0.0)
        self.assertEqual(impact.liquidity_source, "daily_volume_adv_proxy")
        self.assertTrue(impact.paper_only)
        self.assertFalse(impact.execution_allowed)

    def test_external_data_readiness_manifest_checks_adapter_schema_and_symbol_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.2,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (root / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,200000,1000000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (root / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,12,-0.4,gdelt_alpha_vantage_proxy\n",
                encoding="utf-8",
            )
            (root / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )

            rows = build_external_data_readiness_rows(root, ["AAPL"])

            self.assertTrue(all(row["status"] == "PASS" for row in rows))
            self.assertEqual({row["adapter"] for row in rows}, {"factors", "short_sale_volume", "news_sentiment", "listing_status"})
            self.assertTrue(all(row["paper_only"] == "True" for row in rows))
            self.assertTrue(all(row["execution_allowed"] == "False" for row in rows))

    def test_external_data_readiness_manifest_blocks_missing_source_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.2,0.9,0.4,0.8,0.7,,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_external_data_readiness_rows(root, ["AAPL", "MSFT"])
            by_adapter = {row["adapter"]: row for row in rows}

            self.assertEqual(by_adapter["factors"]["status"], "BLOCK")
            self.assertIn("MSFT", by_adapter["factors"]["missing_symbols"])
            self.assertIn("missing_source", by_adapter["factors"]["reasons"])
            self.assertEqual(by_adapter["short_sale_volume"]["status"], "BLOCK")

    def test_external_data_readiness_manifest_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.2,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )

            rows = build_external_data_readiness_rows(root, ["AAPL"])
            csv_path = root / "readiness.csv"
            md_path = root / "readiness.md"
            save_external_data_readiness_reports(rows, csv_path, md_path)

            self.assertTrue(csv_path.exists())
            self.assertIn("External Data Readiness", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
