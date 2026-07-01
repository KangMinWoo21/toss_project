import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backtester.auto_trading.benchmark import load_benchmark_metrics
from backtester.auto_trading.costs import (
    BASE_COST_SCENARIO,
    CONSERVATIVE_COST_SCENARIO,
    TaxConfig,
    TaxTrade,
    compute_capital_gains_tax_usd,
)
from backtester.auto_trading.gates import (
    PerformanceMetrics,
    evaluate_objective_status,
    max_drawdown_abs_pct,
)
from backtester.auto_trading.prices import assert_no_lookahead, load_price_history
from backtester.auto_trading.universe import (
    load_point_in_time_universe,
    load_universe,
    universe_survivorship_warning_flag,
)


class AutoTradingCoreTests(unittest.TestCase):
    def test_universe_requires_schema_active_rows_and_survivorship_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe.csv"
            path.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning\n"
                "SPY,SPDR S&P 500 ETF,ETF,2015-01-01,,manual,true,current-constituent universe; survivorship risk\n",
                encoding="utf-8",
            )

            rows = load_universe(path)

            self.assertEqual(rows[0].symbol, "SPY")
            self.assertEqual(rows[0].survivorship_warning, "current-constituent universe; survivorship risk")

    def test_universe_fails_closed_for_missing_columns_inactive_or_missing_warning(self):
        cases = [
            "symbol,name,asset_type,universe_start,universe_end,source,active_flag\n"
            "SPY,SPDR S&P 500 ETF,ETF,2015-01-01,,manual,true\n",
            "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning\n"
            "SPY,SPDR S&P 500 ETF,ETF,2015-01-01,,manual,false,current universe\n",
            "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning\n"
            "SPY,SPDR S&P 500 ETF,ETF,2015-01-01,,manual,true,\n",
        ]
        for text in cases:
            with self.subTest(text=text.splitlines()[0]):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "universe.csv"
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_universe(path)

    def test_point_in_time_universe_filters_by_as_of_and_excludes_delisted_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe_history.csv"
            path.write_text(
                "symbol,name,asset_type,exchange,effective_from,effective_to,status,source,survivorship_warning\n"
                "AAPL,Apple Inc,EQUITY,NAS,2015-01-01,,active,nasdaq_trader_history,point-in-time source\n"
                "OLD,Old Corp,EQUITY,NYS,2015-01-01,2020-12-31,active,nasdaq_trader_history,point-in-time source\n"
                "TSLA,Tesla Inc,EQUITY,NAS,2021-01-01,,active,nasdaq_trader_history,point-in-time source\n"
                "DEAD,Dead Inc,EQUITY,NAS,2015-01-01,,delisted,nasdaq_trader_history,point-in-time source\n",
                encoding="utf-8",
            )

            rows_2020 = load_point_in_time_universe(path, as_of="2020-06-30")
            rows_2022 = load_point_in_time_universe(path, as_of="2022-06-30")

            self.assertEqual({row.symbol for row in rows_2020}, {"AAPL", "OLD"})
            self.assertEqual({row.symbol for row in rows_2022}, {"AAPL", "TSLA"})
            self.assertEqual(rows_2022[0].exchange, "NAS")

    def test_point_in_time_universe_fails_closed_for_missing_source_warning_or_bad_period(self):
        cases = [
            "symbol,name,asset_type,exchange,effective_from,effective_to,status,source,survivorship_warning\n"
            "AAPL,Apple Inc,EQUITY,NAS,2015-01-01,,active,,point-in-time source\n",
            "symbol,name,asset_type,exchange,effective_from,effective_to,status,source,survivorship_warning\n"
            "AAPL,Apple Inc,EQUITY,NAS,2015-01-01,,active,nasdaq_trader_history,\n",
            "symbol,name,asset_type,exchange,effective_from,effective_to,status,source,survivorship_warning\n"
            "AAPL,Apple Inc,EQUITY,NAS,2020-01-01,2019-01-01,active,nasdaq_trader_history,point-in-time source\n",
        ]
        for text in cases:
            with self.subTest(text=text):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "universe_history.csv"
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_point_in_time_universe(path, as_of="2020-06-30")

    def test_current_universe_sets_survivorship_warning_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe.csv"
            path.write_text(
                "symbol,name,asset_type,universe_start,universe_end,source,active_flag,survivorship_warning\n"
                "SPY,SPDR S&P 500 ETF,ETF,2015-01-01,,manual,true,current-constituent universe; survivorship risk\n",
                encoding="utf-8",
            )

            rows = load_universe(path)

            self.assertTrue(universe_survivorship_warning_flag(rows))

    def test_price_loader_infers_bar_date_and_usable_from_and_blocks_lookahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SPY_daily.csv"
            path.write_text(
                "date,symbol,open,high,low,close,adj_close,volume,source\n"
                "2026-06-30,SPY,100,101,99,100,100,1000,yahoo\n",
                encoding="utf-8",
            )

            rows = load_price_history(Path(tmp), ["SPY"])

            self.assertEqual(rows["SPY"][0].bar_date, "2026-06-30")
            self.assertEqual(rows["SPY"][0].usable_from_kst, "2026-07-01T06:00:00+09:00")
            with self.assertRaises(ValueError):
                assert_no_lookahead(rows["SPY"], datetime.fromisoformat("2026-06-30T23:00:00+09:00"))
            assert_no_lookahead(rows["SPY"], datetime.fromisoformat("2026-07-01T06:00:00+09:00"))

    def test_mdd_is_compared_as_absolute_percent(self):
        self.assertEqual(max_drawdown_abs_pct(-21.7), 21.7)
        self.assertEqual(max_drawdown_abs_pct(21.7), 21.7)

    def test_cost_scenarios_are_fixed(self):
        self.assertEqual(BASE_COST_SCENARIO.fee_rate, 0.00015)
        self.assertEqual(BASE_COST_SCENARIO.slippage_rate, 0.0005)
        self.assertEqual(BASE_COST_SCENARIO.fx_buffer_rate, 0.0010)
        self.assertEqual(CONSERVATIVE_COST_SCENARIO.fee_rate, 0.00030)
        self.assertEqual(CONSERVATIVE_COST_SCENARIO.slippage_rate, 0.0015)
        self.assertEqual(CONSERVATIVE_COST_SCENARIO.fx_buffer_rate, 0.0030)

    def test_capital_gains_tax_uses_fifo_krw_realized_gain_and_annual_deduction(self):
        tax_usd = compute_capital_gains_tax_usd(
            [
                TaxTrade("2026-01-02", "SPY", "BUY", 100, 100.0),
                TaxTrade("2026-02-02", "SPY", "SELL", 100, 200.0),
            ],
            TaxConfig(usd_krw_rate=1400.0, settlement_lag_days=1),
        )

        expected_krw_tax = ((100.0 * 100 * 1400.0) - 2_500_000) * 0.22
        self.assertAlmostEqual(tax_usd, expected_krw_tax / 1400.0, places=6)

    def test_objective_status_complete_review_and_not_complete(self):
        benchmark = PerformanceMetrics(
            net_total_return_pct=10.0,
            net_cagr_pct=5.0,
            max_drawdown_abs_pct=20.0,
            risk_adjusted_return=1.0,
        )
        complete = PerformanceMetrics(12.0, 6.0, 19.0, 1.1)
        review = PerformanceMetrics(12.0, 6.0, 19.0, 0.9)
        not_complete = PerformanceMetrics(12.0, 4.0, 19.0, 1.1)

        self.assertEqual(evaluate_objective_status(complete, complete, benchmark).objective_status, "COMPLETE")
        self.assertEqual(evaluate_objective_status(review, review, benchmark).objective_status, "REVIEW")
        self.assertEqual(evaluate_objective_status(not_complete, complete, benchmark).objective_status, "NOT_COMPLETE")

    def test_benchmark_loader_records_sha256_and_selector(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "benchmark.csv"
            path.write_text(
                "name,status,detail\n"
                "required_excess,PASS,min_required_excess_pct=5.0000\n"
                "drawdown_buffer,WARN,worst_max_drawdown_pct=-20.0000\n"
                "return_concentration,WARN,full_excess_pct=10.0000; median_walk_forward_excess_pct=1.2000; ratio=8.3333\n",
                encoding="utf-8",
            )

            metrics = load_benchmark_metrics(path, row_selector="name=return_concentration")

            self.assertEqual(metrics.row_selector, "name=return_concentration")
            self.assertEqual(len(metrics.report_sha256), 64)
            self.assertEqual(metrics.performance.max_drawdown_abs_pct, 20.0)
            self.assertEqual(metrics.performance.risk_adjusted_return, 1.2)


if __name__ == "__main__":
    unittest.main()
