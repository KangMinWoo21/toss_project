import argparse
import os
from datetime import date, timedelta
from pathlib import Path

from .analysis import generate_rolling_windows, summarize_walk_forward, walk_forward
from .auto_scalper import parse_symbol_list, run_auto_scalper_loop
from .config import load_env_into_process
from .data import load_candles
from .dart import (
    disclosure_rows_to_event_rows,
    fetch_dart_disclosures_for_symbols,
    fetch_dart_financial_rows_for_symbols,
    save_dart_event_rows,
    save_dart_financial_rows,
)
from .engine import BacktestConfig, Backtester
from .events import load_event_scores
from .leader_regime_switch import LeaderRegimeSwitchConfig, run_regime_switching_leader_backtest
from .flow import load_flow_scores
from .leader_swing import LeaderSwingConfig, load_symbol_candles, run_leader_swing_backtest
from .momentum_rotation import (
    MomentumRotationConfig,
    momentum_rotation_config_for_preset,
    run_momentum_rotation_backtest,
)
from .momentum_validation import (
    generate_yearly_walk_forward_windows,
    run_holdout_validation,
    run_walk_forward_validation,
    save_deployment_gate_summary,
    save_validation_rows,
    summarize_deployment_gate,
)
from .monthly_rebalance import (
    MonthlyRebalanceConfig,
    RiskLimits,
    audit_monthly_validation_data,
    audit_point_in_time_price_coverage,
    build_deployment_gate,
    build_monthly_performance_audit,
    build_order_plan,
    build_monthly_validation_gate,
    decide_monthly_allocation,
    diagnose_universe_bias,
    exclude_invalid_price_symbols,
    generate_monthly_validation_cases,
    is_monthly_rebalance_due,
    latest_reference_prices,
    load_deployment_gate,
    load_last_rebalance_date,
    load_performance_guard,
    load_point_in_time_universe,
    load_positions,
    exclude_extreme_period_return_symbols,
    apply_performance_guard,
    compress_decision_to_buyable_targets,
    mark_order_plan_execution,
    risk_exit_code,
    risk_status,
    run_monthly_rebalance_backtest,
    run_monthly_walk_forward_validation,
    run_monthly_validation_suite,
    save_deployment_gate,
    save_monthly_decision,
    save_monthly_performance_audit_rows,
    save_monthly_validation_rows,
    save_order_plan,
    save_risk_report,
    save_universe_price_coverage_rows,
    save_validation_data_quality_rows,
    save_rebalance_state,
    validate_pre_trade_risk,
)
from .reporting import (
    format_candidate_summary,
    format_candidate_validation_table,
    format_regime_study_table,
    format_results_table,
    format_walk_forward_summary_table,
    format_walk_forward_table,
)
from .readiness import (
    evaluate_readiness,
    readiness_exit_code,
    readiness_status,
    save_readiness_markdown,
    save_readiness_report,
)
from .news import (
    articles_to_event_rows,
    fetch_gdelt_articles,
    fetch_google_news_rss,
    rss_to_event_rows,
    save_event_rows,
)
from .pykrx_fetcher import (
    available_ohlcv_symbols,
    build_missing_ohlcv_targets,
    fetch_missing_ohlcv_batches,
    fetch_pykrx_flow_csv,
    fetch_pykrx_market_snapshot_csv,
    fetch_pykrx_ohlcv_csv,
    fetch_pykrx_ohlcv_universe_csv,
    fetch_pykrx_universe_snapshot_csv,
    fetch_pykrx_universe_snapshots_csv,
    load_universe_snapshot_rows,
    load_symbol_universe,
    run_missing_ohlcv_batch_subprocess_loop,
    save_missing_ohlcv_targets,
    save_universe_fetch_report,
)
from .scalper import ScalperConfig, run_paper_scalper
from .scalp_replay import aggregate_scalp_results, format_scalp_replay_table, replay_scalp_directory
from .study import data_files_from_dir, run_market_regime_study
from .strategies import FlowFilteredStrategy, NewsFilteredStrategy, Strategy, available_strategies, get_strategy
from .swing_sweep import run_candidate_validation, run_swing_parameter_sweep, summarize_candidate_validation
from .toss import download_daily_candles_csv, fetch_market_calendar, fetch_tick_snapshot, issue_token


def main() -> int:
    load_env_into_process()

    parser = argparse.ArgumentParser(prog="backtester")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one strategy")
    _add_common_args(run_parser)
    _add_news_args(run_parser)
    _add_flow_args(run_parser)
    run_parser.add_argument("--strategy", choices=available_strategies(), required=True)

    compare_parser = subparsers.add_parser("compare", help="Compare all built-in strategies")
    _add_common_args(compare_parser)
    _add_news_args(compare_parser)
    _add_flow_args(compare_parser)

    walk_parser = subparsers.add_parser("walk-forward", help="Pick the best train-period strategy and test it later")
    _add_common_args(walk_parser)
    _add_news_args(walk_parser)
    _add_flow_args(walk_parser)
    walk_parser.add_argument(
        "--window",
        action="append",
        default=[],
        help="Date window: train_start:train_end:test_start:test_end. Can be repeated.",
    )
    walk_parser.add_argument("--train-size", type=int, default=None, help="Auto-generate rolling windows by row count")
    walk_parser.add_argument("--test-size", type=int, default=None, help="Auto-generate rolling windows by row count")
    walk_parser.add_argument("--step-size", type=int, default=None, help="Rolling window step by row count")
    walk_parser.add_argument(
        "--strategies",
        default=",".join(available_strategies()),
        help="Comma-separated strategy names to compare",
    )

    fetch_toss_parser = subparsers.add_parser("fetch-toss", help="Download Toss Invest daily candles to CSV")
    fetch_toss_parser.add_argument("--symbol", required=True, help="KRX symbol, e.g. 005930")
    fetch_toss_parser.add_argument("--output", required=True, help="Output CSV path")
    fetch_toss_parser.add_argument("--pages", type=int, default=5, help="200-candle pages to request")
    fetch_toss_parser.add_argument("--interval", choices=["1d", "1m"], default="1d")

    gdelt_parser = subparsers.add_parser("fetch-gdelt-events", help="Download GDELT news into event-score CSV")
    gdelt_parser.add_argument("--symbol", required=True, help="Symbol to write into event CSV, e.g. 005930")
    gdelt_parser.add_argument("--query", required=True, help="GDELT query, e.g. Samsung Electronics")
    gdelt_parser.add_argument("--output", required=True, help="Output event CSV path")
    gdelt_parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    gdelt_parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    gdelt_parser.add_argument("--max-records", type=int, default=100)

    google_news_parser = subparsers.add_parser("fetch-google-news-events", help="Download Google News RSS into event-score CSV")
    google_news_parser.add_argument("--symbol", required=True, help="Symbol to write into event CSV, e.g. 005930")
    google_news_parser.add_argument("--query", required=True, help="Google News query, e.g. 삼성전자")
    google_news_parser.add_argument("--output", required=True, help="Output event CSV path")
    google_news_parser.add_argument("--language", default="ko")
    google_news_parser.add_argument("--country", default="KR")

    dart_parser = subparsers.add_parser("fetch-dart-events", help="Download OpenDART disclosures into event-score CSV")
    dart_parser.add_argument("--symbol", default=None, help="KRX symbol, e.g. 005930")
    dart_parser.add_argument("--symbols", default=None, help="Comma-separated KRX symbols, e.g. 005930,000660")
    dart_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    dart_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    dart_parser.add_argument("--output", required=True, help="Output event CSV path")
    dart_parser.add_argument("--page-count", type=int, default=100)

    dart_financial_parser = subparsers.add_parser(
        "fetch-dart-financials",
        help="Download OpenDART financial statement account rows to CSV",
    )
    dart_financial_parser.add_argument("--symbol", default=None, help="KRX symbol, e.g. 005930")
    dart_financial_parser.add_argument("--symbols", default=None, help="Comma-separated KRX symbols")
    dart_financial_parser.add_argument("--business-year", required=True, help="Business year, e.g. 2025")
    dart_financial_parser.add_argument("--report-code", default="11011", help="11011 annual, 11014 Q3, 11012 half, 11013 Q1")
    dart_financial_parser.add_argument("--fs-div", default="CFS", choices=["CFS", "OFS"])
    dart_financial_parser.add_argument("--output", required=True, help="Output financial CSV path")

    pykrx_flow_parser = subparsers.add_parser("fetch-pykrx-flow", help="Download KRX investor flow with pykrx")
    pykrx_flow_parser.add_argument("--symbol", required=True, help="KRX symbol, e.g. 005930")
    pykrx_flow_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    pykrx_flow_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    pykrx_flow_parser.add_argument("--output", required=True, help="Output flow CSV path")

    pykrx_ohlcv_parser = subparsers.add_parser("fetch-pykrx-ohlcv", help="Download KRX daily OHLCV with pykrx")
    pykrx_ohlcv_parser.add_argument("--symbol", required=True, help="KRX symbol, e.g. 005930")
    pykrx_ohlcv_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    pykrx_ohlcv_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    pykrx_ohlcv_parser.add_argument("--output", required=True, help="Output candle CSV path")

    pykrx_universe_snapshot_parser = subparsers.add_parser(
        "fetch-pykrx-universe-snapshot",
        help="Download KRX listed ticker universe snapshot with pykrx",
    )
    pykrx_universe_snapshot_parser.add_argument("--date", default=None, help="Single snapshot date YYYY-MM-DD")
    pykrx_universe_snapshot_parser.add_argument("--start", default=None, help="Monthly snapshot start date YYYY-MM-DD")
    pykrx_universe_snapshot_parser.add_argument("--end", default=None, help="Monthly snapshot end date YYYY-MM-DD")
    pykrx_universe_snapshot_parser.add_argument("--output", required=True, help="Output universe CSV path")
    pykrx_universe_snapshot_parser.add_argument("--markets", default="KOSPI,KOSDAQ")

    pykrx_market_snapshot_parser = subparsers.add_parser(
        "fetch-pykrx-market-snapshot",
        help="Download KRX per-ticker OHLCV, trading value, and market cap snapshot with pykrx",
    )
    pykrx_market_snapshot_parser.add_argument("--date", required=True, help="Snapshot date YYYY-MM-DD")
    pykrx_market_snapshot_parser.add_argument("--output", required=True, help="Output market snapshot CSV path")
    pykrx_market_snapshot_parser.add_argument("--markets", default="KOSPI,KOSDAQ")

    pykrx_universe_parser = subparsers.add_parser(
        "fetch-pykrx-universe-ohlcv",
        help="Download daily OHLCV for a symbol universe CSV with pykrx",
    )
    pykrx_universe_parser.add_argument("--symbols-file", required=True, help="CSV with symbol,name,market columns")
    pykrx_universe_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    pykrx_universe_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    pykrx_universe_parser.add_argument("--output-dir", required=True, help="Directory for per-symbol candle CSVs")
    pykrx_universe_parser.add_argument(
        "--report-output",
        default="data/reports/krx_universe_fetch_report.csv",
        help="Output fetch report CSV path",
    )
    pykrx_universe_parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N symbols")
    pykrx_universe_parser.add_argument("--refresh", action="store_true", help="Re-download files that already exist")

    pykrx_missing_ohlcv_parser = subparsers.add_parser(
        "plan-pykrx-missing-ohlcv",
        help="Create a prioritized symbols CSV for missing KRX universe OHLCV coverage",
    )
    pykrx_missing_ohlcv_parser.add_argument("--universe-file", required=True, help="CSV with date,symbol,name,market")
    pykrx_missing_ohlcv_parser.add_argument("--data-dir", default="data/krx_expanded")
    pykrx_missing_ohlcv_parser.add_argument("--output", default="data/reports/krx_missing_ohlcv_targets.csv")
    pykrx_missing_ohlcv_parser.add_argument("--limit", type=int, default=None)

    pykrx_missing_batches_parser = subparsers.add_parser(
        "fetch-pykrx-missing-ohlcv-batches",
        help="Repeatedly plan and fetch missing KRX universe OHLCV in small batches",
    )
    pykrx_missing_batches_parser.add_argument("--universe-file", required=True, help="CSV with date,symbol,name,market")
    pykrx_missing_batches_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    pykrx_missing_batches_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    pykrx_missing_batches_parser.add_argument("--data-dir", default="data/krx_expanded")
    pykrx_missing_batches_parser.add_argument(
        "--targets-output",
        default="data/reports/krx_missing_ohlcv_targets.csv",
        help="Output CSV for remaining missing targets after each batch",
    )
    pykrx_missing_batches_parser.add_argument("--report-dir", default="data/reports")
    pykrx_missing_batches_parser.add_argument("--report-prefix", default="krx_missing_ohlcv_fetch")
    pykrx_missing_batches_parser.add_argument("--batch-size", type=int, default=50)
    pykrx_missing_batches_parser.add_argument("--batches", type=int, default=1)
    pykrx_missing_batches_parser.add_argument("--batch-pause-seconds", type=float, default=10.0)

    pykrx_missing_loop_parser = subparsers.add_parser(
        "fetch-pykrx-missing-ohlcv-loop",
        help="Run missing KRX OHLCV fetches as isolated one-batch subprocesses with per-batch timeout",
    )
    pykrx_missing_loop_parser.add_argument("--universe-file", required=True, help="CSV with date,symbol,name,market")
    pykrx_missing_loop_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    pykrx_missing_loop_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    pykrx_missing_loop_parser.add_argument("--data-dir", default="data/krx_expanded")
    pykrx_missing_loop_parser.add_argument(
        "--targets-output",
        default="data/reports/krx_missing_ohlcv_targets.csv",
        help="Output CSV for remaining missing targets after each child batch",
    )
    pykrx_missing_loop_parser.add_argument("--report-dir", default="data/reports")
    pykrx_missing_loop_parser.add_argument("--report-prefix", default="krx_missing_ohlcv_fetch")
    pykrx_missing_loop_parser.add_argument("--batch-size", type=int, default=50)
    pykrx_missing_loop_parser.add_argument("--max-batches", type=int, default=1)
    pykrx_missing_loop_parser.add_argument("--batch-timeout-seconds", type=float, default=300.0)
    pykrx_missing_loop_parser.add_argument("--batch-pause-seconds", type=float, default=10.0)
    pykrx_missing_loop_parser.add_argument("--python-executable", default=None)

    paper_scalp_parser = subparsers.add_parser("paper-scalp", help="Run paper scalping with Toss REST market data")
    paper_scalp_parser.add_argument("--symbol", required=True, help="KRX symbol, e.g. 005930")
    paper_scalp_parser.add_argument("--iterations", type=int, default=30)
    paper_scalp_parser.add_argument("--interval-seconds", type=float, default=1.0)
    paper_scalp_parser.add_argument("--output", default="data/scalper/paper_scalp.csv")
    paper_scalp_parser.add_argument("--append", action="store_true", help="Append to output CSV instead of overwriting")
    paper_scalp_parser.add_argument("--require-date", default=None, help="Only save ticks whose timestamp starts with YYYY-MM-DD")
    paper_scalp_parser.add_argument("--volume-spike-multiplier", type=float, default=3.0)
    paper_scalp_parser.add_argument("--imbalance-threshold", type=float, default=1.5)
    paper_scalp_parser.add_argument("--max-spread-pct", type=float, default=0.2)
    paper_scalp_parser.add_argument("--take-profit-pct", type=float, default=0.8)
    paper_scalp_parser.add_argument("--stop-loss-pct", type=float, default=-1.0)

    auto_scalp_parser = subparsers.add_parser("auto-scalp", help="Collect KR or US paper-scalp ticks when each market is open")
    auto_scalp_parser.add_argument("--kr-symbols", default="005930,000660")
    auto_scalp_parser.add_argument("--us-symbols", default="AAPL,NVDA,TSLA,QQQ")
    auto_scalp_parser.add_argument("--output-dir", default="data/scalper")
    auto_scalp_parser.add_argument("--iterations-per-symbol", type=int, default=1)
    auto_scalp_parser.add_argument("--interval-seconds", type=float, default=1.0)
    auto_scalp_parser.add_argument("--idle-seconds", type=float, default=60.0)
    auto_scalp_parser.add_argument("--volume-spike-multiplier", type=float, default=3.0)
    auto_scalp_parser.add_argument("--imbalance-threshold", type=float, default=1.5)
    auto_scalp_parser.add_argument("--max-spread-pct", type=float, default=0.2)
    auto_scalp_parser.add_argument("--take-profit-pct", type=float, default=0.8)
    auto_scalp_parser.add_argument("--stop-loss-pct", type=float, default=-1.0)

    scalp_replay_parser = subparsers.add_parser("scalp-replay", help="Replay saved scalp tick data across many rule variants")
    scalp_replay_parser.add_argument("--data-dir", default="data/scalper_cloud")
    scalp_replay_parser.add_argument("--symbols", default="", help="Comma-separated symbols. Empty means KR symbols only")
    scalp_replay_parser.add_argument("--include-us", action="store_true", help="Include non-6-digit symbols")
    scalp_replay_parser.add_argument("--horizons", default="3,5,10,20,40", help="Comma-separated tick holding periods")
    scalp_replay_parser.add_argument("--min-trades", type=int, default=30)
    scalp_replay_parser.add_argument("--max-spread-pct", type=float, default=0.2)
    scalp_replay_parser.add_argument("--limit", type=int, default=30)
    scalp_replay_parser.add_argument("--aggregate", action="store_true", help="Aggregate by symbol, strategy, and horizon")

    study_parser = subparsers.add_parser("study", help="Compare strategies across many symbols and up/down regimes")
    study_parser.add_argument("--data-dir", required=True, help="Directory containing CSV files")
    study_parser.add_argument("--train-size", type=int, default=80)
    study_parser.add_argument("--test-size", type=int, default=40)
    study_parser.add_argument("--step-size", type=int, default=40)
    study_parser.add_argument(
        "--strategies",
        default=",".join(available_strategies()),
        help="Comma-separated strategy names to compare",
    )
    _add_common_args_without_data(study_parser)

    swing_sweep_parser = subparsers.add_parser(
        "swing-sweep",
        help="Optimize swing strategy parameters on train windows and test out of sample",
    )
    _add_common_args(swing_sweep_parser)
    swing_sweep_parser.add_argument("--train-size", type=int, default=120)
    swing_sweep_parser.add_argument("--test-size", type=int, default=60)
    swing_sweep_parser.add_argument("--step-size", type=int, default=None)
    swing_sweep_parser.add_argument("--preset", choices=["compact", "full"], default="compact")

    swing_candidates_parser = subparsers.add_parser(
        "swing-candidates",
        help="Validate the final two swing candidates and accept only positive excess-return windows",
    )
    _add_common_args(swing_candidates_parser)
    swing_candidates_parser.add_argument("--train-size", type=int, default=240)
    swing_candidates_parser.add_argument("--test-size", type=int, default=60)
    swing_candidates_parser.add_argument("--step-size", type=int, default=None)

    leader_swing_parser = subparsers.add_parser(
        "leader-swing",
        help="Backtest a liquid leader-stock swing rotation strategy across many symbols",
    )
    leader_swing_parser.add_argument("--data-dir", default="data/krx_long")
    leader_swing_parser.add_argument("--initial-cash", type=float, default=10_000_000)
    leader_swing_parser.add_argument("--fee-rate", type=float, default=0.00015)
    leader_swing_parser.add_argument("--tax-rate", type=float, default=0.0018)
    leader_swing_parser.add_argument("--slippage-rate", type=float, default=0.0005)
    leader_swing_parser.add_argument("--liquidity-window", type=int, default=20)
    leader_swing_parser.add_argument("--momentum-short", type=int, default=20)
    leader_swing_parser.add_argument("--momentum-long", type=int, default=60)
    leader_swing_parser.add_argument("--breakout-window", type=int, default=20)
    leader_swing_parser.add_argument("--trend-window", type=int, default=60)
    leader_swing_parser.add_argument("--exit-ma-window", type=int, default=10)
    leader_swing_parser.add_argument("--liquidity-top-n", type=int, default=100)
    leader_swing_parser.add_argument("--max-positions", type=int, default=5)
    leader_swing_parser.add_argument("--max-holding-days", type=int, default=20)
    leader_swing_parser.add_argument("--min-short-return-pct", type=float, default=5.0)
    leader_swing_parser.add_argument("--min-long-return-pct", type=float, default=0.0)
    leader_swing_parser.add_argument("--stop-loss-pct", type=float, default=-8.0)
    leader_swing_parser.add_argument("--market-filter-window", type=int, default=60)
    leader_swing_parser.add_argument("--market-breadth-threshold", type=float, default=0.0)
    leader_swing_parser.add_argument("--events", default=None, help="CSV with date,symbol,source,title,sentiment_score,importance_score")
    leader_swing_parser.add_argument("--event-lookback-days", type=int, default=0)
    leader_swing_parser.add_argument("--min-entry-event-score", type=float, default=-0.2)
    leader_swing_parser.add_argument("--force-exit-event-score", type=float, default=-0.8)

    leader_regime_parser = subparsers.add_parser(
        "leader-regime",
        help="Backtest a regime-switching leader-stock strategy",
    )
    leader_regime_parser.add_argument("--data-dir", default="data/krx_long")
    leader_regime_parser.add_argument("--events", default=None)
    leader_regime_parser.add_argument("--initial-cash", type=float, default=10_000_000)
    leader_regime_parser.add_argument("--fee-rate", type=float, default=0.00015)
    leader_regime_parser.add_argument("--tax-rate", type=float, default=0.0018)
    leader_regime_parser.add_argument("--slippage-rate", type=float, default=0.0005)
    leader_regime_parser.add_argument("--regime-window", type=int, default=126)
    leader_regime_parser.add_argument("--bull-return-threshold-pct", type=float, default=8.0)
    leader_regime_parser.add_argument("--bull-breadth-threshold", type=float, default=0.5)

    momentum_rotation_parser = subparsers.add_parser(
        "momentum-rotation",
        help="Backtest a no-lookahead cross-sectional momentum rotation strategy",
    )
    momentum_rotation_parser.add_argument("--preset", choices=["balanced", "aggressive", "retail"], default="balanced")
    momentum_rotation_parser.add_argument("--data-dir", default="data/krx_long")
    momentum_rotation_parser.add_argument("--initial-cash", type=float, default=None)
    momentum_rotation_parser.add_argument("--fee-rate", type=float, default=None)
    momentum_rotation_parser.add_argument("--tax-rate", type=float, default=None)
    momentum_rotation_parser.add_argument("--slippage-rate", type=float, default=None)
    momentum_rotation_parser.add_argument("--lookback-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--rebalance-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--top-n", type=int, default=None)
    momentum_rotation_parser.add_argument("--require-positive-momentum", action="store_true")
    momentum_rotation_parser.add_argument("--trend-filter-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--market-trend-filter-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--market-breadth-threshold", type=float, default=None)
    momentum_rotation_parser.add_argument("--bull-breadth-threshold", type=float, default=None)
    momentum_rotation_parser.add_argument("--bull-top-n", type=int, default=None)
    momentum_rotation_parser.add_argument("--bull-trend-filter-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--liquidity-window-days", type=int, default=None)
    momentum_rotation_parser.add_argument("--min-average-trading-value", type=float, default=None)
    momentum_rotation_parser.add_argument("--max-trade-participation-rate", type=float, default=None)

    momentum_validate_parser = subparsers.add_parser(
        "momentum-validate",
        help="Run train-only selection, walk-forward testing, and final holdout validation",
    )
    momentum_validate_parser.add_argument("--data-dir", default="data/krx_expanded")
    momentum_validate_parser.add_argument("--first-year", type=int, default=2018)
    momentum_validate_parser.add_argument("--last-year", type=int, default=2026)
    momentum_validate_parser.add_argument("--train-years", type=int, default=3)
    momentum_validate_parser.add_argument("--test-years", type=int, default=1)
    momentum_validate_parser.add_argument("--holdout-start", default="2025-01-01")
    momentum_validate_parser.add_argument("--holdout-end", default=None)
    momentum_validate_parser.add_argument("--presets", default="balanced,aggressive,retail")
    momentum_validate_parser.add_argument("--min-train-trades", type=int, default=1)
    momentum_validate_parser.add_argument("--min-test-trades", type=int, default=1)
    momentum_validate_parser.add_argument(
        "--min-train-positive-ratio",
        type=float,
        default=0.5,
        help="Require this fraction of train subwindows to have positive excess return and trades",
    )
    momentum_validate_parser.add_argument(
        "--train-stability-years",
        type=int,
        default=2,
        help="Calendar years per rolling subwindow used for train stability checks",
    )
    momentum_validate_parser.add_argument(
        "--fallback-breadth-days",
        type=int,
        default=120,
        help="Trailing breadth window used to choose market-beta or cash fallback",
    )
    momentum_validate_parser.add_argument(
        "--fallback-breadth-threshold",
        type=float,
        default=0.4,
        help="Minimum prior market breadth for alpha trades or market-beta fallback",
    )
    momentum_validate_parser.add_argument(
        "--weak-breadth-min-train-avg-excess-pct",
        type=float,
        default=10.0,
        help="Allow alpha in weak breadth only if train subwindows averaged at least this excess return",
    )
    momentum_validate_parser.add_argument("--min-rows-per-window", type=int, default=120)
    momentum_validate_parser.add_argument(
        "--start-grace-days",
        type=int,
        default=14,
        help="Require each symbol to have a candle within N calendar days from each window start",
    )
    momentum_validate_parser.add_argument(
        "--walk-output",
        default="data/reports/momentum_rotation_walk_forward_validation.csv",
    )
    momentum_validate_parser.add_argument(
        "--holdout-output",
        default="data/reports/momentum_rotation_holdout_validation.csv",
    )
    momentum_validate_parser.add_argument(
        "--gate-output",
        default="data/reports/momentum_rotation_deployment_gate.csv",
    )
    momentum_validate_parser.add_argument("--min-walk-accepted-ratio", type=float, default=0.5)
    momentum_validate_parser.add_argument("--min-walk-avg-excess-pct", type=float, default=0.0)
    momentum_validate_parser.add_argument("--min-walk-worst-excess-pct", type=float, default=-20.0)

    monthly_plan_parser = subparsers.add_parser(
        "monthly-plan",
        help="Create a monthly rebalance decision and paper/live order plan without placing orders",
    )
    monthly_plan_parser.add_argument("--data-dir", default="data/krx_expanded")
    monthly_plan_parser.add_argument("--as-of", default=date.today().isoformat())
    monthly_plan_parser.add_argument("--last-rebalance-date", default=None)
    monthly_plan_parser.add_argument(
        "--state-file",
        default=None,
        help="Optional CSV state file used to skip duplicate monthly plans",
    )
    monthly_plan_parser.add_argument("--positions", default=None, help="CSV with symbol,quantity,average_price")
    monthly_plan_parser.add_argument("--cash", type=float, default=10_000_000)
    monthly_plan_parser.add_argument("--output", default="data/reports/monthly_order_plan.csv")
    monthly_plan_parser.add_argument("--decision-output", default="data/reports/monthly_decision.csv")
    monthly_plan_parser.add_argument("--risk-output", default="data/reports/monthly_risk_report.csv")
    monthly_plan_parser.add_argument("--performance-report", default="data/reports/monthly_performance_audit.csv")
    monthly_plan_parser.add_argument("--performance-warn-scale", type=float, default=0.1)
    monthly_plan_parser.add_argument("--performance-block-scale", type=float, default=0.0)
    monthly_plan_parser.add_argument("--require-performance-report", action="store_true")
    monthly_plan_parser.add_argument("--train-years", type=int, default=5)
    monthly_plan_parser.add_argument("--train-start", default=None)
    monthly_plan_parser.add_argument("--presets", default="balanced")
    monthly_plan_parser.add_argument("--min-train-trades", type=int, default=1)
    monthly_plan_parser.add_argument("--min-train-positive-ratio", type=float, default=0.5)
    monthly_plan_parser.add_argument("--train-stability-years", type=int, default=2)
    monthly_plan_parser.add_argument("--min-rows-per-window", type=int, default=120)
    monthly_plan_parser.add_argument("--start-grace-days", type=int, default=14)
    monthly_plan_parser.add_argument("--fallback-breadth-days", type=int, default=120)
    monthly_plan_parser.add_argument("--fallback-breadth-threshold", type=float, default=0.5)
    monthly_plan_parser.add_argument("--market-beta-breadth-threshold", type=float, default=0.25)
    monthly_plan_parser.add_argument("--market-trend-filter-days", type=int, default=60)
    monthly_plan_parser.add_argument("--market-trend-min-return-pct", type=float, default=-5.0)
    monthly_plan_parser.add_argument("--market-trend-risk-scale", type=float, default=0.25)
    monthly_plan_parser.add_argument("--market-volatility-filter-days", type=int, default=0)
    monthly_plan_parser.add_argument("--market-volatility-target-pct", type=float, default=25.0)
    monthly_plan_parser.add_argument("--market-volatility-min-scale", type=float, default=0.25)
    monthly_plan_parser.add_argument("--drawdown-guard-trigger-pct", type=float, default=-15.0)
    monthly_plan_parser.add_argument("--drawdown-guard-scale", type=float, default=0.75)
    monthly_plan_parser.add_argument("--daily-drawdown-stop-pct", type=float, default=0.0)
    monthly_plan_parser.add_argument("--daily-drawdown-cooldown-days", type=int, default=20)
    monthly_plan_parser.add_argument("--weak-breadth-min-train-avg-excess-pct", type=float, default=10.0)
    monthly_plan_parser.add_argument("--cash-buffer-weight", type=float, default=0.01)
    monthly_plan_parser.add_argument("--max-position-weight", type=float, default=0.15)
    monthly_plan_parser.add_argument("--candidate-pool-size", type=int, default=7)
    monthly_plan_parser.add_argument("--min-target-value", type=float, default=10_000)
    monthly_plan_parser.add_argument("--max-candidate-lookback-return-pct", type=float, default=90.0)
    monthly_plan_parser.add_argument("--point-in-time-liquidity-top-n", type=int, default=100)
    monthly_plan_parser.add_argument("--point-in-time-liquidity-window-days", type=int, default=20)
    monthly_plan_parser.add_argument("--liquidity-risk-reference-top-n", type=int, default=100)
    monthly_plan_parser.add_argument("--liquidity-risk-min-scale", type=float, default=0.8)
    monthly_plan_parser.add_argument("--liquidity-risk-min-top-n", type=int, default=20)
    monthly_plan_parser.add_argument("--point-in-time-min-history-days", type=int, default=252)
    monthly_plan_parser.add_argument("--point-in-time-min-reference-price", type=float, default=1_000)
    monthly_plan_parser.add_argument("--point-in-time-max-trailing-return-pct", type=float, default=300.0)
    monthly_plan_parser.add_argument("--point-in-time-trailing-return-days", type=int, default=252)
    monthly_plan_parser.add_argument("--point-in-time-universe", default=None, help="CSV with date,symbol snapshots")
    monthly_plan_parser.add_argument("--market-beta-symbol", default="069500")
    monthly_plan_parser.add_argument("--market-beta-proxy-size", type=int, default=12)
    monthly_plan_parser.add_argument("--min-trade-value", type=float, default=10_000)
    monthly_plan_parser.add_argument("--kill-switch-file", default="data/KILL_SWITCH")
    monthly_plan_parser.add_argument("--max-total-target-weight", type=float, default=1.0)
    monthly_plan_parser.add_argument("--max-single-order-value", type=float, default=2_000_000)
    monthly_plan_parser.add_argument("--max-total-buy-value", type=float, default=10_000_000)
    monthly_plan_parser.add_argument("--max-total-sell-value", type=float, default=10_000_000)
    monthly_plan_parser.add_argument("--max-order-count", type=int, default=15)
    monthly_plan_parser.add_argument("--max-signal-age-days", type=int, default=7)
    monthly_plan_parser.add_argument("--max-daily-loss-pct", type=float, default=3.0)
    monthly_plan_parser.add_argument("--day-start-equity", type=float, default=None)
    monthly_plan_parser.add_argument("--allow-skip-orders", action="store_true")
    monthly_plan_parser.add_argument("--deployment-gate-file", default="data/reports/monthly_deployment_gate.csv")
    monthly_plan_parser.add_argument("--require-deployment-gate", action="store_true")

    monthly_backtest_parser = subparsers.add_parser(
        "monthly-backtest",
        help="Backtest the monthly rebalance decision loop without placing orders",
    )
    monthly_backtest_parser.add_argument("--data-dir", default="data/krx_expanded")
    monthly_backtest_parser.add_argument("--start", required=True)
    monthly_backtest_parser.add_argument("--end", required=True)
    monthly_backtest_parser.add_argument("--initial-cash", type=float, default=10_000_000)
    monthly_backtest_parser.add_argument("--fee-rate", type=float, default=0.00015)
    monthly_backtest_parser.add_argument("--tax-rate", type=float, default=0.0018)
    monthly_backtest_parser.add_argument("--slippage-rate", type=float, default=0.0005)
    monthly_backtest_parser.add_argument("--min-trade-value", type=float, default=10_000)
    monthly_backtest_parser.add_argument("--train-years", type=int, default=5)
    monthly_backtest_parser.add_argument("--train-start", default=None)
    monthly_backtest_parser.add_argument("--presets", default="balanced")
    monthly_backtest_parser.add_argument("--min-train-trades", type=int, default=1)
    monthly_backtest_parser.add_argument("--min-train-positive-ratio", type=float, default=0.5)
    monthly_backtest_parser.add_argument("--train-stability-years", type=int, default=2)
    monthly_backtest_parser.add_argument("--min-rows-per-window", type=int, default=120)
    monthly_backtest_parser.add_argument("--start-grace-days", type=int, default=14)
    monthly_backtest_parser.add_argument("--fallback-breadth-days", type=int, default=120)
    monthly_backtest_parser.add_argument("--fallback-breadth-threshold", type=float, default=0.5)
    monthly_backtest_parser.add_argument("--market-beta-breadth-threshold", type=float, default=0.25)
    monthly_backtest_parser.add_argument("--market-trend-filter-days", type=int, default=60)
    monthly_backtest_parser.add_argument("--market-trend-min-return-pct", type=float, default=-5.0)
    monthly_backtest_parser.add_argument("--market-trend-risk-scale", type=float, default=0.25)
    monthly_backtest_parser.add_argument("--market-volatility-filter-days", type=int, default=0)
    monthly_backtest_parser.add_argument("--market-volatility-target-pct", type=float, default=25.0)
    monthly_backtest_parser.add_argument("--market-volatility-min-scale", type=float, default=0.25)
    monthly_backtest_parser.add_argument("--drawdown-guard-trigger-pct", type=float, default=-15.0)
    monthly_backtest_parser.add_argument("--drawdown-guard-scale", type=float, default=0.75)
    monthly_backtest_parser.add_argument("--daily-drawdown-stop-pct", type=float, default=0.0)
    monthly_backtest_parser.add_argument("--daily-drawdown-cooldown-days", type=int, default=20)
    monthly_backtest_parser.add_argument("--weak-breadth-min-train-avg-excess-pct", type=float, default=10.0)
    monthly_backtest_parser.add_argument("--cash-buffer-weight", type=float, default=0.01)
    monthly_backtest_parser.add_argument("--max-position-weight", type=float, default=0.15)
    monthly_backtest_parser.add_argument("--candidate-pool-size", type=int, default=7)
    monthly_backtest_parser.add_argument("--min-target-value", type=float, default=10_000)
    monthly_backtest_parser.add_argument("--max-candidate-lookback-return-pct", type=float, default=90.0)
    monthly_backtest_parser.add_argument("--point-in-time-liquidity-top-n", type=int, default=100)
    monthly_backtest_parser.add_argument("--point-in-time-liquidity-window-days", type=int, default=20)
    monthly_backtest_parser.add_argument("--liquidity-risk-reference-top-n", type=int, default=100)
    monthly_backtest_parser.add_argument("--liquidity-risk-min-scale", type=float, default=0.8)
    monthly_backtest_parser.add_argument("--liquidity-risk-min-top-n", type=int, default=20)
    monthly_backtest_parser.add_argument("--point-in-time-min-history-days", type=int, default=252)
    monthly_backtest_parser.add_argument("--point-in-time-min-reference-price", type=float, default=1_000)
    monthly_backtest_parser.add_argument("--point-in-time-max-trailing-return-pct", type=float, default=300.0)
    monthly_backtest_parser.add_argument("--point-in-time-trailing-return-days", type=int, default=252)
    monthly_backtest_parser.add_argument("--point-in-time-universe", default=None, help="CSV with date,symbol snapshots")
    monthly_backtest_parser.add_argument("--market-beta-symbol", default="069500")
    monthly_backtest_parser.add_argument("--market-beta-proxy-size", type=int, default=12)
    monthly_backtest_parser.add_argument(
        "--stress-exclude-return-above",
        type=float,
        default=None,
        help="Validation-only: exclude symbols whose full-period return is above this pct",
    )
    monthly_backtest_parser.add_argument("--deployment-gate-output", default="data/reports/monthly_deployment_gate.csv")
    monthly_backtest_parser.add_argument("--min-deployment-excess-pct", type=float, default=0.0)
    monthly_backtest_parser.add_argument("--max-deployment-drawdown-pct", type=float, default=-25.0)
    monthly_backtest_parser.add_argument("--allow-universe-bias-warning", action="store_true")

    monthly_validate_parser = subparsers.add_parser(
        "monthly-validate",
        help="Run duration, regime, and stress validation scenarios for monthly rebalance deployment",
    )
    monthly_validate_parser.add_argument("--data-dir", default="data/krx_expanded")
    monthly_validate_parser.add_argument("--start", required=True)
    monthly_validate_parser.add_argument("--end", required=True)
    monthly_validate_parser.add_argument("--initial-cash", type=float, default=10_000_000)
    monthly_validate_parser.add_argument("--fee-rate", type=float, default=0.00015)
    monthly_validate_parser.add_argument("--tax-rate", type=float, default=0.0018)
    monthly_validate_parser.add_argument("--slippage-rate", type=float, default=0.0005)
    monthly_validate_parser.add_argument("--min-trade-value", type=float, default=10_000)
    monthly_validate_parser.add_argument("--train-years", type=int, default=5)
    monthly_validate_parser.add_argument("--train-start", default=None)
    monthly_validate_parser.add_argument("--presets", default="balanced")
    monthly_validate_parser.add_argument("--min-train-trades", type=int, default=1)
    monthly_validate_parser.add_argument("--min-train-positive-ratio", type=float, default=0.5)
    monthly_validate_parser.add_argument("--train-stability-years", type=int, default=2)
    monthly_validate_parser.add_argument("--min-rows-per-window", type=int, default=120)
    monthly_validate_parser.add_argument("--start-grace-days", type=int, default=14)
    monthly_validate_parser.add_argument("--fallback-breadth-days", type=int, default=120)
    monthly_validate_parser.add_argument("--fallback-breadth-threshold", type=float, default=0.5)
    monthly_validate_parser.add_argument("--market-beta-breadth-threshold", type=float, default=0.25)
    monthly_validate_parser.add_argument("--market-trend-filter-days", type=int, default=60)
    monthly_validate_parser.add_argument("--market-trend-min-return-pct", type=float, default=-5.0)
    monthly_validate_parser.add_argument("--market-trend-risk-scale", type=float, default=0.25)
    monthly_validate_parser.add_argument("--market-volatility-filter-days", type=int, default=0)
    monthly_validate_parser.add_argument("--market-volatility-target-pct", type=float, default=25.0)
    monthly_validate_parser.add_argument("--market-volatility-min-scale", type=float, default=0.25)
    monthly_validate_parser.add_argument("--drawdown-guard-trigger-pct", type=float, default=-15.0)
    monthly_validate_parser.add_argument("--drawdown-guard-scale", type=float, default=0.75)
    monthly_validate_parser.add_argument("--daily-drawdown-stop-pct", type=float, default=0.0)
    monthly_validate_parser.add_argument("--daily-drawdown-cooldown-days", type=int, default=20)
    monthly_validate_parser.add_argument("--weak-breadth-min-train-avg-excess-pct", type=float, default=10.0)
    monthly_validate_parser.add_argument("--cash-buffer-weight", type=float, default=0.01)
    monthly_validate_parser.add_argument("--max-position-weight", type=float, default=0.15)
    monthly_validate_parser.add_argument("--candidate-pool-size", type=int, default=7)
    monthly_validate_parser.add_argument("--min-target-value", type=float, default=10_000)
    monthly_validate_parser.add_argument("--max-candidate-lookback-return-pct", type=float, default=90.0)
    monthly_validate_parser.add_argument("--point-in-time-liquidity-top-n", type=int, default=100)
    monthly_validate_parser.add_argument("--point-in-time-liquidity-window-days", type=int, default=20)
    monthly_validate_parser.add_argument("--liquidity-risk-reference-top-n", type=int, default=100)
    monthly_validate_parser.add_argument("--liquidity-risk-min-scale", type=float, default=0.8)
    monthly_validate_parser.add_argument("--liquidity-risk-min-top-n", type=int, default=20)
    monthly_validate_parser.add_argument("--point-in-time-min-history-days", type=int, default=252)
    monthly_validate_parser.add_argument("--point-in-time-min-reference-price", type=float, default=1_000)
    monthly_validate_parser.add_argument("--point-in-time-max-trailing-return-pct", type=float, default=300.0)
    monthly_validate_parser.add_argument("--point-in-time-trailing-return-days", type=int, default=252)
    monthly_validate_parser.add_argument("--point-in-time-universe", default=None, help="CSV with date,symbol snapshots")
    monthly_validate_parser.add_argument("--market-beta-symbol", default="069500")
    monthly_validate_parser.add_argument("--market-beta-proxy-size", type=int, default=12)
    monthly_validate_parser.add_argument("--scenario-output", default="data/reports/monthly_validation_scenarios.csv")
    monthly_validate_parser.add_argument(
        "--data-quality-output",
        default="data/reports/monthly_validation_data_quality.csv",
    )
    monthly_validate_parser.add_argument("--data-quality-min-rows", type=int, default=252)
    monthly_validate_parser.add_argument("--coverage-output", default="data/reports/monthly_universe_price_coverage.csv")
    monthly_validate_parser.add_argument("--performance-output", default="data/reports/monthly_performance_audit.csv")
    monthly_validate_parser.add_argument("--coverage-min-pct", type=float, default=80.0)
    monthly_validate_parser.add_argument("--deployment-gate-output", default="data/reports/monthly_deployment_gate.csv")
    monthly_validate_parser.add_argument("--min-deployment-excess-pct", type=float, default=0.0)
    monthly_validate_parser.add_argument("--max-deployment-drawdown-pct", type=float, default=-25.0)
    monthly_validate_parser.add_argument("--allow-universe-bias-warning", action="store_true")

    production_check_parser = subparsers.add_parser(
        "production-check",
        help="Evaluate whether local data, validation, and risk reports are ready for live trading",
    )
    production_check_parser.add_argument(
        "--required-artifact",
        action="append",
        default=None,
        help="Required artifact path. Can be repeated. Defaults to core PIT validation artifacts.",
    )
    production_check_parser.add_argument(
        "--deployment-gate-file",
        default="data/reports/monthly_deployment_gate_pit_universe.csv",
    )
    production_check_parser.add_argument(
        "--validation-scenarios",
        default="data/reports/monthly_validation_scenarios_pit_universe.csv",
    )
    production_check_parser.add_argument("--risk-report", default="data/reports/monthly_risk_report.csv")
    production_check_parser.add_argument(
        "--coverage-report",
        default="data/reports/monthly_universe_price_coverage.csv",
    )
    production_check_parser.add_argument(
        "--performance-report",
        default="data/reports/monthly_performance_audit.csv",
    )
    production_check_parser.add_argument("--output", default="data/reports/production_readiness.csv")
    production_check_parser.add_argument(
        "--markdown-output",
        default="data/reports/production_readiness_report.md",
    )
    production_check_parser.add_argument("--allow-blocked-exit-zero", action="store_true")
    production_check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code for WARN as well as BLOCK; use before live execution",
    )

    args = parser.parse_args()
    if args.command == "production-check":
        required_artifacts = args.required_artifact
        if required_artifacts is None:
            required_artifacts = [
                "data/krx_metadata/krx_universe_monthly.csv",
                "data/reports/monthly_validation_scenarios_pit_universe.csv",
                "data/reports/monthly_deployment_gate_pit_universe.csv",
                "data/reports/monthly_risk_report.csv",
                "data/reports/monthly_universe_price_coverage.csv",
                "data/reports/monthly_performance_audit.csv",
            ]
        checks = evaluate_readiness(
            required_artifacts=[Path(path) for path in required_artifacts],
            deployment_gate_path=args.deployment_gate_file,
            validation_scenarios_path=args.validation_scenarios,
            risk_report_path=args.risk_report,
            coverage_report_path=args.coverage_report,
            performance_report_path=args.performance_report,
        )
        status = readiness_status(checks)
        save_readiness_report(checks, args.output)
        save_readiness_markdown(checks, args.markdown_output)
        print(f"readiness_status  {status}")
        print(f"readiness_report  {args.output}")
        print(f"readiness_markdown  {args.markdown_output}")
        exit_code = readiness_exit_code(status, strict=args.strict)
        if exit_code and not args.allow_blocked_exit_zero:
            return exit_code
        return 0

    if args.command == "fetch-toss":
        client_id = os.environ.get("TOSSINVEST_CLIENT_ID")
        client_secret = os.environ.get("TOSSINVEST_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SystemExit("TOSSINVEST_CLIENT_ID and TOSSINVEST_CLIENT_SECRET environment variables are required")
        rows = download_daily_candles_csv(
            client_id=client_id,
            client_secret=client_secret,
            symbol=args.symbol,
            output_path=args.output,
            pages=args.pages,
            interval=args.interval,
        )
        print(f"saved {rows} candles to {args.output}")
        return 0

    if args.command == "fetch-gdelt-events":
        payload = fetch_gdelt_articles(
            query=args.query,
            start=args.start,
            end=args.end,
            max_records=args.max_records,
        )
        rows = articles_to_event_rows(payload, symbol=args.symbol)
        saved = save_event_rows(rows, args.output)
        print(f"saved {saved} events to {args.output}")
        return 0

    if args.command == "fetch-google-news-events":
        rss_text = fetch_google_news_rss(
            query=args.query,
            language=args.language,
            country=args.country,
        )
        rows = rss_to_event_rows(rss_text, symbol=args.symbol)
        saved = save_event_rows(rows, args.output)
        print(f"saved {saved} events to {args.output}")
        return 0

    if args.command == "fetch-dart-events":
        api_key = os.environ.get("DART_API_KEY")
        if not api_key:
            raise SystemExit("DART_API_KEY environment variable is required")
        symbols = parse_symbol_list(args.symbols or args.symbol or "")
        if not symbols:
            raise SystemExit("--symbol or --symbols is required")
        disclosures = fetch_dart_disclosures_for_symbols(
            api_key=api_key,
            symbols=symbols,
            start=args.start,
            end=args.end,
            page_count=args.page_count,
        )
        rows = disclosure_rows_to_event_rows(disclosures)
        saved = save_dart_event_rows(rows, args.output)
        print(f"saved {saved} DART events to {args.output}")
        return 0

    if args.command == "fetch-dart-financials":
        api_key = os.environ.get("DART_API_KEY")
        if not api_key:
            raise SystemExit("DART_API_KEY environment variable is required")
        symbols = parse_symbol_list(args.symbols or args.symbol or "")
        if not symbols:
            raise SystemExit("--symbol or --symbols is required")
        rows = fetch_dart_financial_rows_for_symbols(
            api_key=api_key,
            symbols=symbols,
            business_year=args.business_year,
            report_code=args.report_code,
            fs_div=args.fs_div,
        )
        saved = save_dart_financial_rows(rows, args.output)
        print(f"saved {saved} DART financial rows to {args.output}")
        return 0

    if args.command == "fetch-pykrx-flow":
        try:
            saved = fetch_pykrx_flow_csv(
                start=args.start,
                end=args.end,
                symbol=args.symbol,
                output_path=args.output,
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"saved {saved} flow rows to {args.output}")
        return 0

    if args.command == "fetch-pykrx-ohlcv":
        try:
            saved = fetch_pykrx_ohlcv_csv(
                start=args.start,
                end=args.end,
                symbol=args.symbol,
                output_path=args.output,
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"saved {saved} OHLCV rows to {args.output}")
        return 0

    if args.command == "fetch-pykrx-universe-snapshot":
        markets = tuple(value.strip() for value in args.markets.split(",") if value.strip())
        if args.start or args.end:
            if not args.start or not args.end:
                raise SystemExit("--start and --end must be used together")
            try:
                saved = fetch_pykrx_universe_snapshots_csv(
                    start=args.start,
                    end=args.end,
                    output_path=args.output,
                    markets=markets,
                )
            except RuntimeError as exc:
                raise SystemExit(str(exc)) from exc
            print(f"saved {saved} pykrx universe snapshot rows to {args.output}")
            return 0
        if not args.date:
            raise SystemExit("--date or --start/--end is required")
        try:
            saved = fetch_pykrx_universe_snapshot_csv(
                date=args.date,
                output_path=args.output,
                markets=markets,
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"saved {saved} pykrx universe snapshot rows to {args.output}")
        return 0

    if args.command == "fetch-pykrx-market-snapshot":
        markets = tuple(value.strip() for value in args.markets.split(",") if value.strip())
        try:
            saved = fetch_pykrx_market_snapshot_csv(
                date=args.date,
                output_path=args.output,
                markets=markets,
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"saved {saved} pykrx market snapshot rows to {args.output}")
        return 0

    if args.command == "fetch-pykrx-universe-ohlcv":
        symbols = load_symbol_universe(args.symbols_file)
        if args.limit is not None:
            symbols = symbols[: args.limit]
        report = fetch_pykrx_ohlcv_universe_csv(
            start=args.start,
            end=args.end,
            symbols=symbols,
            output_dir=args.output_dir,
            skip_existing=not args.refresh,
            checkpoint_report_path=args.report_output,
        )
        save_universe_fetch_report(report, args.report_output)
        saved = sum(1 for row in report if row["status"] == "saved")
        skipped = sum(1 for row in report if row["status"] == "skipped")
        failed = [row for row in report if row["status"] == "failed"]
        total_rows = sum(int(row["rows"]) for row in report)
        print(
            f"processed {len(report)} symbols: saved={saved} skipped={skipped} "
            f"failed={len(failed)} rows={total_rows}"
        )
        print(f"report: {args.report_output}")
        for row in failed[:5]:
            print(f"failed {row['symbol']}: {row['error']}")
        return 0

    if args.command == "plan-pykrx-missing-ohlcv":
        universe_rows = load_universe_snapshot_rows(args.universe_file)
        targets = build_missing_ohlcv_targets(
            universe_rows,
            available_symbols=available_ohlcv_symbols(args.data_dir),
        )
        if args.limit is not None:
            targets = targets[: args.limit]
        saved = save_missing_ohlcv_targets(targets, args.output)
        print(f"saved {saved} missing OHLCV targets to {args.output}")
        print(
            "next_fetch_command  "
            f"python -m backtester fetch-pykrx-universe-ohlcv --symbols-file \"{args.output}\" "
            f"--start 2024-01-01 --end 2026-06-18 --output-dir \"{args.data_dir}\""
        )
        return 0

    if args.command == "fetch-pykrx-missing-ohlcv-batches":
        try:
            summary = fetch_missing_ohlcv_batches(
                start=args.start,
                end=args.end,
                universe_file=args.universe_file,
                data_dir=args.data_dir,
                targets_output=args.targets_output,
                report_dir=args.report_dir,
                batch_size=args.batch_size,
                batches=args.batches,
                batch_pause_seconds=args.batch_pause_seconds,
                report_prefix=args.report_prefix,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print("Missing OHLCV batch fetch summary")
        print(f"batches_run  {summary['batches_run']}")
        print(f"processed  {summary['processed']}")
        print(f"saved  {summary['saved']}")
        print(f"skipped  {summary['skipped']}")
        print(f"failed  {summary['failed']}")
        print(f"rows  {summary['rows']}")
        print(f"remaining_targets  {summary['remaining_targets']}")
        print(f"targets_output  {args.targets_output}")
        for report_path in summary["reports"]:
            print(f"report  {report_path}")
        return 0

    if args.command == "fetch-pykrx-missing-ohlcv-loop":
        try:
            summary = run_missing_ohlcv_batch_subprocess_loop(
                start=args.start,
                end=args.end,
                universe_file=args.universe_file,
                data_dir=args.data_dir,
                targets_output=args.targets_output,
                report_dir=args.report_dir,
                report_prefix=args.report_prefix,
                batch_size=args.batch_size,
                max_batches=args.max_batches,
                batch_timeout_seconds=args.batch_timeout_seconds,
                batch_pause_seconds=args.batch_pause_seconds,
                python_executable=args.python_executable,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print("Missing OHLCV subprocess loop summary")
        print(f"status  {summary['status']}")
        print(f"attempted_batches  {summary['attempted_batches']}")
        print(f"completed_batches  {summary['completed_batches']}")
        print(f"timed_out_batches  {summary['timed_out_batches']}")
        print(f"failed_batches  {summary['failed_batches']}")
        print(f"saved  {summary['saved']}")
        print(f"remaining_targets  {summary['remaining_targets']}")
        print(f"targets_output  {args.targets_output}")
        return 0 if summary["status"] == "completed" else 1

    if args.command == "leader-swing":
        result = run_leader_swing_backtest(
            load_symbol_candles(args.data_dir),
            LeaderSwingConfig(
                initial_cash=args.initial_cash,
                fee_rate=args.fee_rate,
                tax_rate=args.tax_rate,
                slippage_rate=args.slippage_rate,
                liquidity_window=args.liquidity_window,
                momentum_short=args.momentum_short,
                momentum_long=args.momentum_long,
                breakout_window=args.breakout_window,
                trend_window=args.trend_window,
                exit_ma_window=args.exit_ma_window,
                liquidity_top_n=args.liquidity_top_n,
                max_positions=args.max_positions,
                max_holding_days=args.max_holding_days,
                min_short_return_pct=args.min_short_return_pct,
                min_long_return_pct=args.min_long_return_pct,
                stop_loss_pct=args.stop_loss_pct,
                market_filter_window=args.market_filter_window,
                market_breadth_threshold=args.market_breadth_threshold,
                event_scores=load_event_scores(args.events) if args.events else None,
                event_lookback_days=args.event_lookback_days,
                min_entry_event_score=args.min_entry_event_score,
                force_exit_event_score=args.force_exit_event_score,
            ),
        )
        print("Leader swing summary")
        print("metric  value")
        print("------  -----")
        print(f"final_equity  {result.final_equity:,.0f}")
        print(f"total_return_%  {result.total_return_pct:.2f}")
        print(f"buy_hold_%  {result.buy_hold_return_pct:.2f}")
        print(f"excess_%  {result.excess_return_pct:.2f}")
        print(f"mdd_%  {result.max_drawdown_pct:.2f}")
        print(f"trades  {result.trade_count}")
        print(f"win_%  {result.win_rate_pct:.2f}")
        return 0

    if args.command == "leader-regime":
        event_scores = load_event_scores(args.events) if args.events else None
        common = {
            "initial_cash": args.initial_cash,
            "fee_rate": args.fee_rate,
            "tax_rate": args.tax_rate,
            "slippage_rate": args.slippage_rate,
            "event_scores": event_scores,
            "event_lookback_days": 20,
            "min_entry_event_score": -0.2,
            "force_exit_event_score": -0.8,
        }
        result = run_regime_switching_leader_backtest(
            load_symbol_candles(args.data_dir),
            LeaderRegimeSwitchConfig(
                regime_window=args.regime_window,
                bull_return_threshold_pct=args.bull_return_threshold_pct,
                bull_breadth_threshold=args.bull_breadth_threshold,
                defensive=LeaderSwingConfig(
                    **common,
                    max_positions=5,
                    liquidity_top_n=10,
                    min_short_return_pct=8,
                    max_holding_days=20,
                    market_breadth_threshold=0.6,
                    loss_cooldown_days=10,
                ),
                bullish=LeaderSwingConfig(
                    **common,
                    max_positions=10,
                    liquidity_top_n=15,
                    min_short_return_pct=3,
                    min_long_return_pct=-5,
                    max_holding_days=90,
                    exit_ma_window=40,
                    stop_loss_pct=-15,
                    market_breadth_threshold=0.4,
                    symbol_weight_multipliers={"000660": 2.5, "005930": 1.5, "006400": 1.5},
                    loss_cooldown_days=10,
                ),
            ),
        )
        summary = result.result
        print("Leader regime summary")
        print("metric  value")
        print("------  -----")
        print(f"final_equity  {summary.final_equity:,.0f}")
        print(f"total_return_%  {summary.total_return_pct:.2f}")
        print(f"buy_hold_%  {summary.buy_hold_return_pct:.2f}")
        print(f"excess_%  {summary.excess_return_pct:.2f}")
        print(f"mdd_%  {summary.max_drawdown_pct:.2f}")
        print(f"trades  {summary.trade_count}")
        print(f"win_%  {summary.win_rate_pct:.2f}")
        print(f"bull_days  {result.mode_counts.get('bull', 0)}")
        print(f"defensive_days  {result.mode_counts.get('defensive', 0)}")
        return 0

    if args.command == "momentum-rotation":
        preset_cfg = momentum_rotation_config_for_preset(args.preset)
        result = run_momentum_rotation_backtest(
            load_symbol_candles(args.data_dir),
            MomentumRotationConfig(
                initial_cash=_arg_or_default(args.initial_cash, preset_cfg.initial_cash),
                fee_rate=_arg_or_default(args.fee_rate, preset_cfg.fee_rate),
                tax_rate=_arg_or_default(args.tax_rate, preset_cfg.tax_rate),
                slippage_rate=_arg_or_default(args.slippage_rate, preset_cfg.slippage_rate),
                lookback_days=_arg_or_default(args.lookback_days, preset_cfg.lookback_days),
                rebalance_days=_arg_or_default(args.rebalance_days, preset_cfg.rebalance_days),
                top_n=_arg_or_default(args.top_n, preset_cfg.top_n),
                require_positive_momentum=args.require_positive_momentum or preset_cfg.require_positive_momentum,
                trend_filter_days=_arg_or_default(args.trend_filter_days, preset_cfg.trend_filter_days),
                market_trend_filter_days=_arg_or_default(
                    args.market_trend_filter_days,
                    preset_cfg.market_trend_filter_days,
                ),
                market_breadth_threshold=_arg_or_default(
                    args.market_breadth_threshold,
                    preset_cfg.market_breadth_threshold,
                ),
                bull_breadth_threshold=_arg_or_default(
                    args.bull_breadth_threshold,
                    preset_cfg.bull_breadth_threshold,
                ),
                bull_top_n=_arg_or_default(args.bull_top_n, preset_cfg.bull_top_n),
                bull_trend_filter_days=_arg_or_default(
                    args.bull_trend_filter_days,
                    preset_cfg.bull_trend_filter_days,
                ),
                liquidity_window_days=_arg_or_default(
                    args.liquidity_window_days,
                    preset_cfg.liquidity_window_days,
                ),
                min_average_trading_value=_arg_or_default(
                    args.min_average_trading_value,
                    preset_cfg.min_average_trading_value,
                ),
                max_trade_participation_rate=_arg_or_default(
                    args.max_trade_participation_rate,
                    preset_cfg.max_trade_participation_rate,
                ),
            ),
        )
        print("Momentum rotation summary")
        print("metric  value")
        print("------  -----")
        print(f"final_equity  {result.final_equity:,.0f}")
        print(f"total_return_%  {result.total_return_pct:.2f}")
        print(f"buy_hold_%  {result.buy_hold_return_pct:.2f}")
        print(f"excess_%  {result.excess_return_pct:.2f}")
        print(f"mdd_%  {result.max_drawdown_pct:.2f}")
        print(f"trades  {result.trade_count}")
        return 0

    if args.command == "momentum-validate":
        symbol_candles = load_symbol_candles(args.data_dir)
        presets = [value.strip() for value in args.presets.split(",") if value.strip()]
        holdout_end = args.holdout_end or _max_candle_date(symbol_candles)
        windows = generate_yearly_walk_forward_windows(
            first_year=args.first_year,
            last_year=args.last_year,
            train_years=args.train_years,
            test_years=args.test_years,
            holdout_start=args.holdout_start,
        )
        walk_rows = run_walk_forward_validation(
            symbol_candles,
            windows,
            presets=presets,
            min_train_trades=args.min_train_trades,
            min_test_trades=args.min_test_trades,
            min_rows_per_window=args.min_rows_per_window,
            start_grace_days=args.start_grace_days,
            min_train_positive_ratio=args.min_train_positive_ratio,
            train_stability_years=args.train_stability_years,
            fallback_breadth_days=args.fallback_breadth_days,
            fallback_breadth_threshold=args.fallback_breadth_threshold,
            weak_breadth_min_train_avg_excess_pct=args.weak_breadth_min_train_avg_excess_pct,
        )
        save_validation_rows(walk_rows, args.walk_output)
        holdout_row = run_holdout_validation(
            symbol_candles,
            train_start=f"{args.first_year:04d}-01-01",
            train_end=_previous_day(args.holdout_start),
            holdout_start=args.holdout_start,
            holdout_end=holdout_end,
            presets=presets,
            min_train_trades=args.min_train_trades,
            min_test_trades=args.min_test_trades,
            min_rows_per_window=args.min_rows_per_window,
            start_grace_days=args.start_grace_days,
            min_train_positive_ratio=args.min_train_positive_ratio,
            train_stability_years=args.train_stability_years,
            fallback_breadth_days=args.fallback_breadth_days,
            fallback_breadth_threshold=args.fallback_breadth_threshold,
            weak_breadth_min_train_avg_excess_pct=args.weak_breadth_min_train_avg_excess_pct,
        )
        save_validation_rows([holdout_row], args.holdout_output)
        gate_summary = summarize_deployment_gate(
            walk_rows,
            min_accepted_ratio=args.min_walk_accepted_ratio,
            min_avg_test_excess_pct=args.min_walk_avg_excess_pct,
            min_worst_test_excess_pct=args.min_walk_worst_excess_pct,
        )
        save_deployment_gate_summary(gate_summary, args.gate_output)

        accepted = sum(1 for row in walk_rows if row["accepted"])
        avg_excess = (
            sum(float(row["test_excess_return_pct"]) for row in walk_rows) / len(walk_rows)
            if walk_rows
            else 0.0
        )
        print("Momentum validation summary")
        print(f"walk_forward_windows  {len(walk_rows)}")
        print(f"accepted_windows  {accepted}")
        print(f"avg_test_excess_%  {avg_excess:.2f}")
        print(f"walk_report  {args.walk_output}")
        print(
            "deployment_gate  "
            f"deployable={gate_summary['deployable']} "
            f"reason={gate_summary['reject_reason']} "
            f"accepted_ratio={float(gate_summary['accepted_ratio']):.2f}"
        )
        print(f"gate_report  {args.gate_output}")
        print(
            "holdout  "
            f"selected={holdout_row['selected_preset']} "
            f"accepted={holdout_row['accepted']} "
            f"test_excess_%={float(holdout_row['test_excess_return_pct']):.2f} "
            f"mdd_%={float(holdout_row['test_max_drawdown_pct']):.2f}"
        )
        print(f"holdout_report  {args.holdout_output}")
        return 0

    if args.command == "monthly-plan":
        last_rebalance_date = args.last_rebalance_date or load_last_rebalance_date(args.state_file)
        if not is_monthly_rebalance_due(as_of_date=args.as_of, last_rebalance_date=last_rebalance_date):
            save_order_plan([], args.output)
            print("monthly rebalance not due")
            print(f"order_plan  {args.output}")
            return 0
        symbol_candles = exclude_invalid_price_symbols(load_symbol_candles(args.data_dir))
        presets = tuple(value.strip() for value in args.presets.split(",") if value.strip())
        point_in_time_universe = (
            load_point_in_time_universe(args.point_in_time_universe)
            if args.point_in_time_universe
            else None
        )
        reference_prices = latest_reference_prices(symbol_candles, as_of_date=args.as_of)
        positions = load_positions(args.positions)
        portfolio_value = args.cash + sum(
            position.quantity * reference_prices.get(position.symbol, 0.0)
            for position in positions
        )
        decision = decide_monthly_allocation(
            symbol_candles,
            as_of_date=args.as_of,
            config=MonthlyRebalanceConfig(
                train_years=args.train_years,
                train_start=args.train_start,
                presets=presets,
                min_train_trades=args.min_train_trades,
                min_train_positive_ratio=args.min_train_positive_ratio,
                train_stability_years=args.train_stability_years,
                min_rows_per_window=args.min_rows_per_window,
                start_grace_days=args.start_grace_days,
                fallback_breadth_days=args.fallback_breadth_days,
                fallback_breadth_threshold=args.fallback_breadth_threshold,
                market_beta_breadth_threshold=args.market_beta_breadth_threshold,
                market_trend_filter_days=args.market_trend_filter_days,
                market_trend_min_return_pct=args.market_trend_min_return_pct,
                market_trend_risk_scale=args.market_trend_risk_scale,
                market_volatility_filter_days=args.market_volatility_filter_days,
                market_volatility_target_pct=args.market_volatility_target_pct,
                market_volatility_min_scale=args.market_volatility_min_scale,
                drawdown_guard_trigger_pct=args.drawdown_guard_trigger_pct,
                drawdown_guard_scale=args.drawdown_guard_scale,
                daily_drawdown_stop_pct=args.daily_drawdown_stop_pct,
                daily_drawdown_cooldown_days=args.daily_drawdown_cooldown_days,
                weak_breadth_min_train_avg_excess_pct=args.weak_breadth_min_train_avg_excess_pct,
                cash_buffer_weight=args.cash_buffer_weight,
                max_position_weight=args.max_position_weight,
                candidate_pool_size=args.candidate_pool_size,
                min_target_value=args.min_target_value,
                max_candidate_lookback_return_pct=args.max_candidate_lookback_return_pct,
                point_in_time_liquidity_top_n=args.point_in_time_liquidity_top_n,
                point_in_time_liquidity_window_days=args.point_in_time_liquidity_window_days,
                liquidity_risk_reference_top_n=args.liquidity_risk_reference_top_n,
                liquidity_risk_min_scale=args.liquidity_risk_min_scale,
                liquidity_risk_min_top_n=args.liquidity_risk_min_top_n,
                point_in_time_min_history_days=args.point_in_time_min_history_days,
                point_in_time_min_reference_price=args.point_in_time_min_reference_price,
                point_in_time_max_trailing_return_pct=args.point_in_time_max_trailing_return_pct,
                point_in_time_trailing_return_days=args.point_in_time_trailing_return_days,
                point_in_time_universe=point_in_time_universe,
                market_beta_symbol=args.market_beta_symbol,
                market_beta_proxy_size=args.market_beta_proxy_size,
            ),
            portfolio_value=portfolio_value,
            reference_prices=reference_prices,
        )
        performance_guard = load_performance_guard(
            args.performance_report,
            warn_scale=args.performance_warn_scale,
            block_scale=args.performance_block_scale,
        )
        decision = apply_performance_guard(decision, performance_guard)
        decision = compress_decision_to_buyable_targets(
            decision,
            reference_prices=reference_prices,
            portfolio_value=portfolio_value,
            max_position_weight=args.max_position_weight,
            min_target_value=args.min_trade_value,
        )
        orders = build_order_plan(
            decision,
            positions=positions,
            cash=args.cash,
            reference_prices=reference_prices,
            min_trade_value=args.min_trade_value,
        )
        deployment_gate = load_deployment_gate(args.deployment_gate_file)
        risk_checks = validate_pre_trade_risk(
            decision,
            orders,
            limits=RiskLimits(
                max_total_target_weight=args.max_total_target_weight,
                max_single_order_value=args.max_single_order_value,
                max_total_buy_value=args.max_total_buy_value,
                max_total_sell_value=args.max_total_sell_value,
                max_order_count=args.max_order_count,
                max_signal_age_days=args.max_signal_age_days,
                max_daily_loss_pct=args.max_daily_loss_pct,
                block_skip_orders=not args.allow_skip_orders,
            ),
            kill_switch_path=args.kill_switch_file,
            deployment_gate=deployment_gate,
            require_deployment_gate=args.require_deployment_gate,
            performance_guard=performance_guard,
            require_performance_guard=args.require_performance_report,
            day_start_equity=args.day_start_equity,
            current_equity=portfolio_value,
        )
        gate_status = risk_status(risk_checks)
        orders = mark_order_plan_execution(orders, risk_status_value=gate_status)
        save_monthly_decision(decision, args.decision_output)
        save_order_plan(orders, args.output)
        save_risk_report(risk_checks, args.risk_output)
        if args.state_file and gate_status == "PASS":
            save_rebalance_state(decision, args.state_file)
        print("Monthly rebalance decision")
        print(f"as_of  {decision.as_of_date}")
        print(f"signal_date  {decision.signal_date}")
        print(f"mode  {decision.mode}")
        print(f"selected_preset  {decision.selected_preset}")
        print(f"targets  {','.join(decision.target_weights.keys()) if decision.target_weights else 'cash'}")
        print(f"orders  {len(orders)}")
        print(f"risk_status  {gate_status}")
        print(f"decision_report  {args.decision_output}")
        print(f"order_plan  {args.output}")
        print(f"risk_report  {args.risk_output}")
        if args.deployment_gate_file:
            print(f"deployment_gate  {args.deployment_gate_file if deployment_gate else 'missing'}")
        if args.performance_report:
            if performance_guard:
                print(
                    "performance_guard  "
                    f"{performance_guard.status} scale={performance_guard.scale:.4f} report={args.performance_report}"
                )
            else:
                print(f"performance_guard  missing report={args.performance_report}")
        if args.state_file:
            if gate_status == "PASS":
                print(f"state_file  {args.state_file}")
            else:
                print(f"state_file  skipped_due_to_{gate_status.lower()}")
        return risk_exit_code(gate_status)

    if args.command == "monthly-backtest":
        symbol_candles = exclude_invalid_price_symbols(load_symbol_candles(args.data_dir))
        point_in_time_universe = (
            load_point_in_time_universe(args.point_in_time_universe)
            if args.point_in_time_universe
            else None
        )
        if args.stress_exclude_return_above is not None:
            symbol_candles = exclude_extreme_period_return_symbols(
                symbol_candles,
                start=args.start,
                end=args.end,
                max_period_return_pct=args.stress_exclude_return_above,
            )
        presets = tuple(value.strip() for value in args.presets.split(",") if value.strip())
        result = run_monthly_rebalance_backtest(
            symbol_candles,
            start=args.start,
            end=args.end,
            initial_cash=args.initial_cash,
            fee_rate=args.fee_rate,
            tax_rate=args.tax_rate,
            slippage_rate=args.slippage_rate,
            min_trade_value=args.min_trade_value,
            config=MonthlyRebalanceConfig(
                train_years=args.train_years,
                train_start=args.train_start,
                presets=presets,
                min_train_trades=args.min_train_trades,
                min_train_positive_ratio=args.min_train_positive_ratio,
                train_stability_years=args.train_stability_years,
                min_rows_per_window=args.min_rows_per_window,
                start_grace_days=args.start_grace_days,
                fallback_breadth_days=args.fallback_breadth_days,
                fallback_breadth_threshold=args.fallback_breadth_threshold,
                market_beta_breadth_threshold=args.market_beta_breadth_threshold,
                market_trend_filter_days=args.market_trend_filter_days,
                market_trend_min_return_pct=args.market_trend_min_return_pct,
                market_trend_risk_scale=args.market_trend_risk_scale,
                market_volatility_filter_days=args.market_volatility_filter_days,
                market_volatility_target_pct=args.market_volatility_target_pct,
                market_volatility_min_scale=args.market_volatility_min_scale,
                drawdown_guard_trigger_pct=args.drawdown_guard_trigger_pct,
                drawdown_guard_scale=args.drawdown_guard_scale,
                daily_drawdown_stop_pct=args.daily_drawdown_stop_pct,
                daily_drawdown_cooldown_days=args.daily_drawdown_cooldown_days,
                weak_breadth_min_train_avg_excess_pct=args.weak_breadth_min_train_avg_excess_pct,
                cash_buffer_weight=args.cash_buffer_weight,
                max_position_weight=args.max_position_weight,
                candidate_pool_size=args.candidate_pool_size,
                min_target_value=args.min_target_value,
                max_candidate_lookback_return_pct=args.max_candidate_lookback_return_pct,
                point_in_time_liquidity_top_n=args.point_in_time_liquidity_top_n,
                point_in_time_liquidity_window_days=args.point_in_time_liquidity_window_days,
                liquidity_risk_reference_top_n=args.liquidity_risk_reference_top_n,
                liquidity_risk_min_scale=args.liquidity_risk_min_scale,
                liquidity_risk_min_top_n=args.liquidity_risk_min_top_n,
                point_in_time_min_history_days=args.point_in_time_min_history_days,
                point_in_time_min_reference_price=args.point_in_time_min_reference_price,
                point_in_time_max_trailing_return_pct=args.point_in_time_max_trailing_return_pct,
                point_in_time_trailing_return_days=args.point_in_time_trailing_return_days,
                point_in_time_universe=point_in_time_universe,
                market_beta_symbol=args.market_beta_symbol,
                market_beta_proxy_size=args.market_beta_proxy_size,
            ),
        )
        print("Monthly rebalance backtest")
        print(f"period  {args.start}..{args.end}")
        print(f"initial_cash  {result.initial_cash:.0f}")
        print(f"final_equity  {result.final_equity:.0f}")
        print(f"total_return_%  {result.total_return_pct:.2f}")
        print(f"buy_hold_%  {result.buy_hold_return_pct:.2f}")
        print(f"excess_%  {result.excess_return_pct:.2f}")
        print(f"max_drawdown_%  {result.max_drawdown_pct:.2f}")
        print(f"decisions  {len(result.decisions)}")
        print(f"trades  {result.trade_count}")
        bias = diagnose_universe_bias(symbol_candles, start=args.start, end=args.end)
        deployment_gate = build_deployment_gate(
            result,
            universe_bias=bias,
            min_excess_return_pct=args.min_deployment_excess_pct,
            max_drawdown_pct=args.max_deployment_drawdown_pct,
            allow_universe_bias_warning=args.allow_universe_bias_warning,
            source=f"monthly-backtest:{args.start}..{args.end}",
        )
        if args.deployment_gate_output:
            save_deployment_gate(deployment_gate, args.deployment_gate_output)
        print(f"universe_symbols  {bias['symbol_count']}")
        print(f"universe_avg_symbol_return_%  {float(bias['average_symbol_return_pct']):.2f}")
        print(f"universe_median_symbol_return_%  {float(bias['median_symbol_return_pct']):.2f}")
        print(f"universe_extreme_500pct_symbols  {bias['extreme_return_symbols']}")
        print(f"universe_bias_warning  {bias['warning']}")
        print(f"deployment_gate  deployable={deployment_gate.deployable} reason={deployment_gate.reason}")
        if args.deployment_gate_output:
            print(f"deployment_gate_report  {args.deployment_gate_output}")
        return 0

    if args.command == "monthly-validate":
        symbol_candles = exclude_invalid_price_symbols(load_symbol_candles(args.data_dir))
        presets = tuple(value.strip() for value in args.presets.split(",") if value.strip())
        point_in_time_universe = (
            load_point_in_time_universe(args.point_in_time_universe)
            if args.point_in_time_universe
            else None
        )
        config = MonthlyRebalanceConfig(
            train_years=args.train_years,
            train_start=args.train_start,
            presets=presets,
            min_train_trades=args.min_train_trades,
            min_train_positive_ratio=args.min_train_positive_ratio,
            train_stability_years=args.train_stability_years,
            min_rows_per_window=args.min_rows_per_window,
            start_grace_days=args.start_grace_days,
            fallback_breadth_days=args.fallback_breadth_days,
            fallback_breadth_threshold=args.fallback_breadth_threshold,
            market_beta_breadth_threshold=args.market_beta_breadth_threshold,
            market_trend_filter_days=args.market_trend_filter_days,
            market_trend_min_return_pct=args.market_trend_min_return_pct,
            market_trend_risk_scale=args.market_trend_risk_scale,
            market_volatility_filter_days=args.market_volatility_filter_days,
            market_volatility_target_pct=args.market_volatility_target_pct,
            market_volatility_min_scale=args.market_volatility_min_scale,
            drawdown_guard_trigger_pct=args.drawdown_guard_trigger_pct,
            drawdown_guard_scale=args.drawdown_guard_scale,
            daily_drawdown_stop_pct=args.daily_drawdown_stop_pct,
            daily_drawdown_cooldown_days=args.daily_drawdown_cooldown_days,
            weak_breadth_min_train_avg_excess_pct=args.weak_breadth_min_train_avg_excess_pct,
            cash_buffer_weight=args.cash_buffer_weight,
            max_position_weight=args.max_position_weight,
            candidate_pool_size=args.candidate_pool_size,
            min_target_value=args.min_target_value,
            max_candidate_lookback_return_pct=args.max_candidate_lookback_return_pct,
            point_in_time_liquidity_top_n=args.point_in_time_liquidity_top_n,
            point_in_time_liquidity_window_days=args.point_in_time_liquidity_window_days,
            liquidity_risk_reference_top_n=args.liquidity_risk_reference_top_n,
            liquidity_risk_min_scale=args.liquidity_risk_min_scale,
            liquidity_risk_min_top_n=args.liquidity_risk_min_top_n,
            point_in_time_min_history_days=args.point_in_time_min_history_days,
            point_in_time_min_reference_price=args.point_in_time_min_reference_price,
            point_in_time_max_trailing_return_pct=args.point_in_time_max_trailing_return_pct,
            point_in_time_trailing_return_days=args.point_in_time_trailing_return_days,
            point_in_time_universe=point_in_time_universe,
            market_beta_symbol=args.market_beta_symbol,
            market_beta_proxy_size=args.market_beta_proxy_size,
        )
        cases = generate_monthly_validation_cases(symbol_candles, start=args.start, end=args.end)
        data_quality_rows = audit_monthly_validation_data(
            symbol_candles,
            start=args.start,
            end=args.end,
            min_rows=args.data_quality_min_rows,
        )
        save_validation_data_quality_rows(data_quality_rows, args.data_quality_output)
        coverage_rows = []
        if point_in_time_universe is not None:
            coverage_rows = audit_point_in_time_price_coverage(
                symbol_candles,
                point_in_time_universe,
                min_coverage_pct=args.coverage_min_pct,
            )
            save_universe_price_coverage_rows(coverage_rows, args.coverage_output)
        regular_cases = [case for case in cases if case.category != "walk_forward"]
        walk_forward_cases = [case for case in cases if case.category == "walk_forward"]
        rows = run_monthly_validation_suite(
            symbol_candles,
            cases=regular_cases,
            config=config,
            initial_cash=args.initial_cash,
            fee_rate=args.fee_rate,
            tax_rate=args.tax_rate,
            slippage_rate=args.slippage_rate,
            min_trade_value=args.min_trade_value,
            min_excess_return_pct=args.min_deployment_excess_pct,
            max_drawdown_pct=args.max_deployment_drawdown_pct,
            allow_universe_bias_warning=args.allow_universe_bias_warning,
        )
        rows.extend(
            run_monthly_walk_forward_validation(
                symbol_candles,
                cases=walk_forward_cases,
                config=config,
                initial_cash=args.initial_cash,
                fee_rate=args.fee_rate,
                tax_rate=args.tax_rate,
                slippage_rate=args.slippage_rate,
                min_trade_value=args.min_trade_value,
                min_excess_return_pct=args.min_deployment_excess_pct,
                max_drawdown_pct=args.max_deployment_drawdown_pct,
                allow_universe_bias_warning=args.allow_universe_bias_warning,
            )
        )
        data_quality_blocks = [row for row in data_quality_rows if row["status"] == "BLOCK"]
        if data_quality_blocks:
            rows.append(
                {
                    "name": "validation_data_quality",
                    "category": "data_quality",
                    "required": True,
                    "train_start": "",
                    "train_end": "",
                    "selected_preset": "",
                    "train_excess_return_pct": "",
                    "start": args.start,
                    "end": args.end,
                    "slippage_multiplier": 1.0,
                    "stress": "",
                    "final_equity": "",
                    "total_return_pct": "",
                    "buy_hold_return_pct": "",
                    "excess_return_pct": "",
                    "max_drawdown_pct": "",
                    "trade_count": "",
                    "universe_bias_warning": "",
                    "deployable": False,
                    "reason": f"data_quality_blocks:{len(data_quality_blocks)}",
                }
            )
        save_monthly_validation_rows(rows, args.scenario_output)
        performance_rows = build_monthly_performance_audit(rows)
        save_monthly_performance_audit_rows(performance_rows, args.performance_output)
        deployment_gate = build_monthly_validation_gate(
            rows,
            source=f"monthly-validate:{args.start}..{args.end}",
        )
        save_deployment_gate(deployment_gate, args.deployment_gate_output)
        failed_required = [
            row["name"]
            for row in rows
            if str(row.get("required", True)).lower() in {"true", "1", "yes"} and not row.get("deployable")
        ]
        print("Monthly validation summary")
        print(f"period  {args.start}..{args.end}")
        print(f"scenarios  {len(rows)}")
        print(f"walk_forward_scenarios  {len(walk_forward_cases)}")
        print(f"failed_required  {len(failed_required)}")
        print(f"data_quality_blocks  {len(data_quality_blocks)}")
        print(f"deployment_gate  deployable={deployment_gate.deployable} reason={deployment_gate.reason}")
        print(f"scenario_report  {args.scenario_output}")
        print(f"data_quality_report  {args.data_quality_output}")
        print(f"performance_report  {args.performance_output}")
        if point_in_time_universe is not None:
            coverage_blocks = [row for row in coverage_rows if row["status"] == "BLOCK"]
            print(f"coverage_blocks  {len(coverage_blocks)}")
            print(f"coverage_report  {args.coverage_output}")
        print(f"deployment_gate_report  {args.deployment_gate_output}")
        if failed_required:
            print(f"failed_required_names  {','.join(failed_required[:10])}")
        return 0

    if args.command == "paper-scalp":
        client_id = os.environ.get("TOSSINVEST_CLIENT_ID")
        client_secret = os.environ.get("TOSSINVEST_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SystemExit("TOSSINVEST_CLIENT_ID and TOSSINVEST_CLIENT_SECRET environment variables are required")
        access_token = issue_token(client_id, client_secret)
        scalper_config = ScalperConfig(
            volume_spike_multiplier=args.volume_spike_multiplier,
            bid_ask_imbalance_threshold=args.imbalance_threshold,
            max_spread_pct=args.max_spread_pct,
            take_profit_pct=args.take_profit_pct,
            stop_loss_pct=args.stop_loss_pct,
        )
        rows = run_paper_scalper(
            snapshot_fetcher=lambda: fetch_tick_snapshot(access_token, args.symbol),
            iterations=args.iterations,
            interval_seconds=args.interval_seconds,
            output_path=args.output,
            config=scalper_config,
            append=args.append,
            required_date=args.require_date,
        )
        buys = sum(1 for row in rows if row["signal"] == "BUY")
        sells = sum(1 for row in rows if row["signal"] == "SELL")
        realized = sum(float(row["realized_pnl_pct"]) for row in rows)
        print(f"saved {len(rows)} paper scalp ticks to {args.output}")
        print(f"signals: BUY={buys} SELL={sells} realized_pnl_pct_sum={realized:.4f}")
        return 0

    if args.command == "auto-scalp":
        client_id = os.environ.get("TOSSINVEST_CLIENT_ID")
        client_secret = os.environ.get("TOSSINVEST_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SystemExit("TOSSINVEST_CLIENT_ID and TOSSINVEST_CLIENT_SECRET environment variables are required")
        access_token = issue_token(client_id, client_secret)
        scalper_config = ScalperConfig(
            volume_spike_multiplier=args.volume_spike_multiplier,
            bid_ask_imbalance_threshold=args.imbalance_threshold,
            max_spread_pct=args.max_spread_pct,
            take_profit_pct=args.take_profit_pct,
            stop_loss_pct=args.stop_loss_pct,
        )
        run_auto_scalper_loop(
            access_token=access_token,
            kr_calendar_fetcher=lambda: fetch_market_calendar(access_token, "KR"),
            us_calendar_fetcher=lambda: fetch_market_calendar(access_token, "US"),
            kr_symbols=parse_symbol_list(args.kr_symbols),
            us_symbols=parse_symbol_list(args.us_symbols),
            output_dir=args.output_dir,
            interval_seconds=args.interval_seconds,
            iterations_per_symbol=args.iterations_per_symbol,
            idle_seconds=args.idle_seconds,
            config=scalper_config,
        )
        return 0

    if args.command == "scalp-replay":
        horizons = [int(value.strip()) for value in args.horizons.split(",") if value.strip()]
        symbols = [value.strip() for value in args.symbols.split(",") if value.strip()] or None
        results = replay_scalp_directory(
            data_dir=args.data_dir,
            symbols=symbols,
            include_us=args.include_us,
            horizons=horizons,
            min_trades=args.min_trades,
            max_spread_pct=args.max_spread_pct,
        )
        if args.aggregate:
            results = aggregate_scalp_results(results, min_trades=args.min_trades)
        print(format_scalp_replay_table(results, limit=args.limit))
        return 0

    config = BacktestConfig(
        initial_cash=args.initial_cash,
        fee_rate=args.fee_rate,
        tax_rate=args.tax_rate,
        slippage_rate=args.slippage_rate,
        position_fraction=args.position_fraction,
    )

    if args.command == "study":
        strategy_names = [name.strip() for name in args.strategies.split(",") if name.strip()]
        rows = run_market_regime_study(
            data_files=data_files_from_dir(args.data_dir),
            strategies=[get_strategy(name) for name in strategy_names],
            train_size=args.train_size,
            test_size=args.test_size,
            step_size=args.step_size,
            config=config,
        )
        print(format_regime_study_table(rows))
        return 0

    candles = load_candles(Path(args.data))
    engine = Backtester(config=config)

    if args.command == "swing-sweep":
        report = run_swing_parameter_sweep(
            candles=candles,
            train_size=args.train_size,
            test_size=args.test_size,
            step_size=args.step_size,
            config=config,
            preset=args.preset,
        )
        print(f"Swing sweep periods (strategies={report.strategy_count})")
        print(format_walk_forward_table(report.periods))
        print()
        print("Strategy summary")
        print(format_walk_forward_summary_table(report.summary))
    elif args.command == "swing-candidates":
        rows = run_candidate_validation(
            candles=candles,
            train_size=args.train_size,
            test_size=args.test_size,
            step_size=args.step_size,
            config=config,
        )
        print("Candidate validation")
        print(format_candidate_validation_table(rows))
        print()
        print("Candidate summary")
        print(format_candidate_summary(summarize_candidate_validation(rows)))
    elif args.command == "run":
        results = [engine.run(candles, _apply_optional_filters(get_strategy(args.strategy), args))]
        print(format_results_table(results))
    elif args.command == "compare":
        results = [
            engine.run(candles, _apply_optional_filters(get_strategy(name), args))
            for name in available_strategies()
        ]
        print(format_results_table(results))
    else:
        strategy_names = [name.strip() for name in args.strategies.split(",") if name.strip()]
        strategies = [_apply_optional_filters(get_strategy(name), args) for name in strategy_names]
        windows = _parse_windows(args.window)
        if not windows:
            if args.train_size is None or args.test_size is None:
                raise SystemExit("--window or both --train-size and --test-size are required")
            windows = generate_rolling_windows(
                candles,
                train_size=args.train_size,
                test_size=args.test_size,
                step_size=args.step_size,
            )
        results = walk_forward(candles=candles, strategies=strategies, windows=windows, config=config)
        summaries = summarize_walk_forward(results)
        print("Walk-forward periods")
        print(format_walk_forward_table(results))
        print()
        print("Strategy summary")
        print(format_walk_forward_summary_table(summaries))
    return 0


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data", required=True, help="CSV file with date,open,high,low,close,volume")
    _add_common_args_without_data(parser)


def _add_common_args_without_data(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--initial-cash", type=float, default=10_000_000)
    parser.add_argument("--fee-rate", type=float, default=0.00015)
    parser.add_argument("--tax-rate", type=float, default=0.0018)
    parser.add_argument("--slippage-rate", type=float, default=0.0005)
    parser.add_argument("--position-fraction", type=float, default=1.0)


def _add_news_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--news-filter", action="store_true", help="Apply event sentiment filter to strategy signals")
    parser.add_argument("--events", default=None, help="CSV with date,symbol,source,title,sentiment_score,importance_score")
    parser.add_argument("--symbol", default=None, help="Symbol for event score lookup, e.g. 005930")
    parser.add_argument("--min-buy-score", type=float, default=-0.2)
    parser.add_argument("--force-sell-score", type=float, default=-0.8)
    parser.add_argument("--event-lookback-days", type=int, default=0)


def _add_flow_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--flow-filter", action="store_true", help="Apply investor/insider flow filter to strategy signals")
    parser.add_argument("--flows", default=None, help="CSV with investor and insider flow values")
    parser.add_argument("--min-flow-score", type=float, default=-0.2)
    parser.add_argument("--force-flow-sell-score", type=float, default=-0.8)
    parser.add_argument("--flow-scale-value", type=float, default=100_000_000.0)


def _apply_optional_filters(strategy: Strategy, args: argparse.Namespace) -> Strategy:
    filtered = strategy
    if getattr(args, "news_filter", False):
        filtered = _news_filtered(filtered, args)
    if getattr(args, "flow_filter", False):
        filtered = _flow_filtered(filtered, args)
    return filtered


def _arg_or_default(value, default):
    return default if value is None else value


def _news_filtered(strategy: Strategy, args: argparse.Namespace) -> Strategy:
    if not args.events or not args.symbol:
        raise SystemExit("--events and --symbol are required with --news-filter")
    return NewsFilteredStrategy(
        base_strategy=strategy,
        event_scores=load_event_scores(args.events),
        symbol=args.symbol,
        min_buy_score=args.min_buy_score,
        force_sell_score=args.force_sell_score,
        event_lookback_days=args.event_lookback_days,
        name=f"{strategy.name}+news_filtered",
    )


def _flow_filtered(strategy: Strategy, args: argparse.Namespace) -> Strategy:
    if not args.flows or not args.symbol:
        raise SystemExit("--flows and --symbol are required with --flow-filter")
    return FlowFilteredStrategy(
        base_strategy=strategy,
        flow_scores=load_flow_scores(args.flows, scale_value=args.flow_scale_value),
        symbol=args.symbol,
        min_buy_score=args.min_flow_score,
        force_sell_score=args.force_flow_sell_score,
        name=f"{strategy.name}+flow_filtered",
    )


def _parse_windows(values: list[str]) -> list[tuple[str, str, str, str]]:
    windows: list[tuple[str, str, str, str]] = []
    for value in values:
        parts = value.split(":")
        if len(parts) != 4:
            raise SystemExit(f"invalid --window: {value}")
        windows.append((parts[0], parts[1], parts[2], parts[3]))
    return windows


def _max_candle_date(symbol_candles) -> str:
    return max(candle.date for candles in symbol_candles.values() for candle in candles)


def _previous_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
