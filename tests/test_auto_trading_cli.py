import csv
import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from backtester.__main__ import main


class AutoTradingCliTests(unittest.TestCase):
    def test_auto_paper_run_cli_is_local_csv_only_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            (prices / "SPY_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-01-28,SPY,100,100,100,100,100,1000,yahoo\n"
                "2026-02-28,SPY,101,101,101,101,101,1000,yahoo\n",
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
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "SPY,ETF,1.0,0.8,0.5,0.7,0.6,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            output_dir = root / "out"

            argv = [
                "backtester",
                "auto-paper-run",
                "--prices-dir",
                str(prices),
                "--universe",
                str(universe),
                "--benchmark-report",
                str(benchmark),
                "--benchmark-row-selector",
                "name=return_concentration",
                "--output-dir",
                str(output_dir),
                "--external-data-dir",
                str(external),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("urllib.request.urlopen", side_effect=AssertionError("network called")),
                patch("backtester.__main__.KisUsClient", side_effect=AssertionError("KIS called")),
                patch("backtester.__main__.download_daily_candles_csv", side_effect=AssertionError("Toss called")),
                patch("backtester.__main__.issue_token", side_effect=AssertionError("Toss token called")),
                patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                self.assertEqual(main(), 0)
                output = stdout.getvalue()

            with (output_dir / "auto_paper_order_plan.csv").open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertTrue(rows)
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertEqual(rows[0]["production_effect"], "none")
            self.assertEqual(rows[0]["external_data_policy"], "free_local_csv_only")
            self.assertEqual(rows[0]["sector"], "ETF")
            self.assertIn("model_config", output)
            self.assertIn("cost_policy", output)
            self.assertIn("external_data", output)

    def test_auto_paper_run_cli_accepts_point_in_time_universe_as_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-01-28,AAPL,100,100,100,100,100,1000,yahoo\n"
                "2026-02-28,AAPL,101,101,101,101,101,1000,yahoo\n",
                encoding="utf-8",
            )
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
            output_dir = root / "out"
            argv = [
                "backtester",
                "auto-paper-run",
                "--prices-dir",
                str(prices),
                "--universe",
                str(universe),
                "--universe-as-of",
                "2020-06-30",
                "--benchmark-report",
                str(benchmark),
                "--benchmark-row-selector",
                "name=return_concentration",
                "--output-dir",
                str(output_dir),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO):
                self.assertEqual(main(), 0)

            audit = json.loads((output_dir / "auto_paper_audit_log.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["universe_mode"], "point_in_time")
            self.assertEqual(audit["universe_as_of"], "2020-06-30")

    def test_auto_paper_export_kis_targets_cli_writes_safe_target_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            order_plan = root / "auto_paper_order_plan.csv"
            order_plan.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            universe = root / "universe.csv"
            universe.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning,exchange\n"
                "AAPL,Apple Inc,EQUITY,2015-01-01,,fixture,true,current universe,NAS\n",
                encoding="utf-8",
            )
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "objective_status": "COMPLETE",
                        "best_model": "model_x",
                        "benchmark_report_sha256": "a" * 64,
                        "execution_allowed": False,
                    }
                ),
                encoding="utf-8",
            )
            output_path = root / "kis_targets.csv"
            argv = [
                "backtester",
                "auto-paper-export-kis-targets",
                "--auto-order-plan",
                str(order_plan),
                "--universe",
                str(universe),
                "--audit-log",
                str(audit),
                "--output",
                str(output_path),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output_path.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["symbol"], "AAPL")
            self.assertEqual(rows[0]["exchange"], "NAS")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("kis_targets", text)

    def test_auto_paper_health_check_cli_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "COMPLETE",
                        "paper_only": True,
                        "dry_run": True,
                        "execution_allowed": False,
                        "production_effect": "none",
                    }
                ),
                encoding="utf-8",
            )
            auto_order = root / "auto_order.csv"
            auto_order.write_text(
                "symbol,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            kis_targets = root / "kis_targets.csv"
            kis_targets.write_text(
                "symbol,exchange,target_weight,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.10,True,True,False,none\n",
                encoding="utf-8",
            )
            kis_plan = root / "kis_plan.csv"
            kis_plan.write_text(
                "symbol,risk_status,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,PASS,True,True,False,none\n",
                encoding="utf-8",
            )
            output = root / "health.csv"
            markdown = root / "health.md"
            argv = [
                "backtester",
                "auto-paper-health-check",
                "--audit-log",
                str(audit),
                "--auto-order-plan",
                str(auto_order),
                "--kis-targets",
                str(kis_targets),
                "--kis-order-plan",
                str(kis_plan),
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            self.assertTrue(output.exists())
            self.assertTrue(markdown.exists())
            self.assertIn("operation_health_status  PASS", text)

    def test_auto_paper_risk_gate_cli_writes_reports(self):
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
                "AAPL,Technology,1.10,0.9,0.4,0.8,0.7,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (external / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (external / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,3,0.20,gdelt_proxy\n",
                encoding="utf-8",
            )
            (external / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-06-30,AAPL,100,100,100,100,100,1000000,yahoo\n",
                encoding="utf-8",
            )
            output = root / "risk.csv"
            markdown = root / "risk.md"
            argv = [
                "backtester",
                "auto-paper-risk-gate",
                "--kis-targets",
                str(targets),
                "--external-data-dir",
                str(external),
                "--prices-dir",
                str(prices),
                "--portfolio-value-usd",
                "100000",
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            self.assertTrue(output.exists())
            self.assertTrue(markdown.exists())
            self.assertIn("portfolio_risk_status  PASS", text)

    def test_auto_paper_adjust_targets_cli_writes_risk_adjusted_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = root / "targets.csv"
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
            output = root / "adjusted.csv"
            argv = [
                "backtester",
                "auto-paper-adjust-targets",
                "--kis-targets",
                str(targets),
                "--external-data-dir",
                str(external),
                "--prices-dir",
                str(prices),
                "--portfolio-value-usd",
                "100000",
                "--output",
                str(output),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual([row["symbol"] for row in rows], ["AAPL"])
            self.assertIn("adjusted_targets", text)

    def test_auto_paper_register_model_cli_writes_registry_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "engine_status": "SUCCESS",
                        "objective_status": "COMPLETE",
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
            argv = [
                "backtester",
                "auto-paper-register-model",
                "--audit-log",
                str(audit),
                "--model-config",
                str(model_config),
                "--cost-policy",
                str(cost_policy),
                "--risk-gate",
                str(risk_gate),
                "--version",
                "v0.1.0",
                "--output",
                str(output),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["model_id"], "model_x")
            self.assertEqual(record["risk_gate_status"], "PASS")
            self.assertIn("model_registry", text)

    def test_auto_paper_simulate_execution_cli_writes_simulated_fill_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "as_of,symbol,side,quantity,execution_allowed\n"
                "2026-06-30,AAPL,BUY,10,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source,usable_from_kst\n"
                "2026-06-30,AAPL,100,110,90,105,105,1000,yahoo,2026-07-01T06:00:00+09:00\n",
                encoding="utf-8",
            )
            output = root / "fills.csv"
            argv = [
                "backtester",
                "auto-paper-simulate-execution",
                "--orders",
                str(orders),
                "--prices-dir",
                str(prices),
                "--fill-policy",
                "close",
                "--execution-time-kst",
                "2026-07-01T06:00:00+09:00",
                "--output",
                str(output),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["simulated"], "True")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("execution_simulation", text)

    def test_auto_paper_market_impact_cli_writes_impact_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "orders.csv"
            orders.write_text(
                "symbol,side,quantity,reference_price,estimated_value,execution_allowed\n"
                "AAPL,BUY,10,100,1000,False\n",
                encoding="utf-8",
            )
            prices = root / "prices"
            prices.mkdir()
            (prices / "AAPL_daily.csv").write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-06-29,AAPL,100,105,95,100,100,1000,yahoo\n"
                "2026-06-30,AAPL,100,110,90,105,105,1000,yahoo\n",
                encoding="utf-8",
            )
            output = root / "impact.csv"
            argv = [
                "backtester",
                "auto-paper-market-impact",
                "--orders",
                str(orders),
                "--prices-dir",
                str(prices),
                "--scenario",
                "stress",
                "--output",
                str(output),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["symbol"], "AAPL")
            self.assertEqual(rows[0]["scenario"], "stress")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("market_impact", text)

    def test_auto_paper_factor_risk_cli_writes_factor_report(self):
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
            output = root / "factor.csv"
            markdown = root / "factor.md"
            argv = [
                "backtester",
                "auto-paper-factor-risk",
                "--kis-targets",
                str(targets),
                "--external-data-dir",
                str(external),
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertTrue(rows)
            self.assertEqual(rows[0]["paper_only"], "True")
            self.assertIn("factor_risk", text)

    def test_auto_paper_optimize_portfolio_cli_writes_optimized_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            candidates.write_text(
                "symbol,exchange,alpha_score,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,NAS,0.90,True,True,False,none\n"
                "MSFT,NAS,0.80,True,True,False,none\n",
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
            output = root / "optimized.csv"
            markdown = root / "optimized.md"
            argv = [
                "backtester",
                "auto-paper-optimize-portfolio",
                "--candidates",
                str(candidates),
                "--external-data-dir",
                str(external),
                "--max-total-weight",
                "0.40",
                "--max-single-weight",
                "0.20",
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("portfolio_optimizer", text)

    def test_auto_paper_tca_cli_writes_tca_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executions = root / "executions.csv"
            executions.write_text(
                "as_of,symbol,side,requested_quantity,filled_quantity,fill_status,fill_reasons,"
                "reference_price_basis,reference_price,simulated_fill_price,estimated_spread_cost_usd,"
                "estimated_slippage_cost_usd,simulated,paper_only,dry_run,execution_allowed,production_effect\n"
                "2026-07-01,AAPL,BUY,1,1,FILLED,filled,close,100.00,100.10,0.05,0.10,True,True,True,False,none\n",
                encoding="utf-8",
            )
            impact = root / "impact.csv"
            impact.write_text(
                "symbol,scenario,order_value_usd,average_daily_dollar_volume,participation_rate,"
                "annualized_volatility,spread_rate,estimated_impact_rate,estimated_impact_usd,"
                "risk_bucket,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,base,100,1000000,0.0001,0.20,0.001,0.001,0.05,LOW,True,True,False,none\n",
                encoding="utf-8",
            )
            output = root / "tca.csv"
            markdown = root / "tca.md"
            argv = [
                "backtester",
                "auto-paper-tca",
                "--executions",
                str(executions),
                "--market-impact",
                str(impact),
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["tca_status"], "PASS")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("tca_report", text)

    def test_auto_paper_external_data_readiness_cli_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            (external / "factors.csv").write_text(
                "symbol,sector,beta,size_score,value_score,quality_score,momentum_score,source,as_of\n"
                "AAPL,Technology,1.10,0.90,0.50,0.80,0.70,sec_edgar_proxy,2026-06-30\n",
                encoding="utf-8",
            )
            (external / "short_sale_volume.csv").write_text(
                "symbol,date,short_volume,total_volume,source\n"
                "AAPL,2026-06-30,100,1000,finra_daily_short_sale_volume\n",
                encoding="utf-8",
            )
            (external / "news_sentiment.csv").write_text(
                "symbol,date,article_count,sentiment_score,source\n"
                "AAPL,2026-06-30,2,0.10,alpha_vantage_news_sentiment\n",
                encoding="utf-8",
            )
            (external / "listing_status.csv").write_text(
                "symbol,name,exchange,asset_type,ipo_date,delisting_date,status,source\n"
                "AAPL,Apple Inc,NASDAQ,Stock,1980-12-12,,Active,alpha_vantage_listing_status\n",
                encoding="utf-8",
            )
            output = root / "readiness.csv"
            markdown = root / "readiness.md"
            argv = [
                "backtester",
                "auto-paper-external-data-readiness",
                "--external-data-dir",
                str(external),
                "--symbols",
                "AAPL",
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["status"], "PASS")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("external_data_readiness", text)

    def test_auto_paper_monitoring_report_cli_writes_scheduler_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            audit.write_text(
                '{"engine_status":"SUCCESS","objective_status":"COMPLETE","paper_only":true,'
                '"dry_run":true,"execution_allowed":false,"production_effect":"none"}',
                encoding="utf-8",
            )
            external = root / "external.csv"
            external.write_text(
                "adapter,status,paper_only,dry_run,execution_allowed,production_effect\n"
                "factors,PASS,True,True,False,none\n",
                encoding="utf-8",
            )
            risk = root / "risk.csv"
            risk.write_text(
                "check,status,paper_only,dry_run,execution_allowed,production_effect\n"
                "single_name_weight,PASS,True,True,False,none\n",
                encoding="utf-8",
            )
            factor = root / "factor.csv"
            factor.write_text(
                "check,status,paper_only,dry_run,execution_allowed,production_effect\n"
                "weighted_beta,PASS,True,True,False,none\n",
                encoding="utf-8",
            )
            tca = root / "tca.csv"
            tca.write_text(
                "symbol,tca_status,paper_only,dry_run,execution_allowed,production_effect\n"
                "AAPL,PASS,True,True,False,none\n",
                encoding="utf-8",
            )
            health = root / "health.csv"
            health.write_text("check,status,detail\nobjective_complete,PASS,ok\n", encoding="utf-8")
            output = root / "monitoring.csv"
            markdown = root / "monitoring.md"
            argv = [
                "backtester",
                "auto-paper-monitoring-report",
                "--audit-log",
                str(audit),
                "--external-data-readiness",
                str(external),
                "--portfolio-risk-gate",
                str(risk),
                "--factor-risk",
                str(factor),
                "--tca-report",
                str(tca),
                "--operation-health",
                str(health),
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
            ]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=StringIO) as stdout:
                self.assertEqual(main(), 0)
                text = stdout.getvalue()

            with output.open(encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]["status"], "PASS")
            self.assertEqual(rows[0]["execution_allowed"], "False")
            self.assertIn("scheduler_monitoring", text)


if __name__ == "__main__":
    unittest.main()
