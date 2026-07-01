from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_KIS_US_TARGETS_SAMPLE = Path("data/examples/kis_us_targets_sample.csv")
DEFAULT_KIS_US_PROTECTED_SAMPLE = Path("data/examples/kis_us_protected_positions_sample.csv")
DEFAULT_KIS_US_DEMO_POSITIONS = Path("data/examples/kis_us_demo_positions.csv")
DEFAULT_KIS_US_DEMO_QUOTES = Path("data/examples/kis_us_demo_quotes.csv")


def register_us_paper_commands(subparsers: Any) -> None:
    kis_us_parser = subparsers.add_parser(
        "kis-us-paper-plan",
        help="Create a KIS US stock mock-account dry-run order plan without placing orders",
    )
    kis_us_parser.add_argument("--targets", required=True, help="CSV with symbol,exchange,target_weight")
    kis_us_parser.add_argument("--protected-positions", default=None, help="CSV with symbol,reason")
    kis_us_parser.add_argument("--balance-exchanges", default="NASD,NYSE,AMEX")
    kis_us_parser.add_argument("--cash-usd", type=float, default=None)
    kis_us_parser.add_argument("--request-interval-seconds", type=float, default=0.0)
    kis_us_parser.add_argument("--as-of", default=date.today().isoformat())
    kis_us_parser.add_argument("--output", default="data/reports/kis_us_paper_order_plan.csv")
    kis_us_parser.add_argument("--summary-output", default="data/reports/kis_us_paper_order_plan.md")

    kis_us_demo_parser = subparsers.add_parser(
        "kis-us-paper-plan-demo",
        help="Create a KIS US paper-only demo plan from local sample files without API credentials",
    )
    kis_us_demo_parser.add_argument("--targets", default=str(DEFAULT_KIS_US_TARGETS_SAMPLE))
    kis_us_demo_parser.add_argument("--protected-positions", default=str(DEFAULT_KIS_US_PROTECTED_SAMPLE))
    kis_us_demo_parser.add_argument("--positions", default=str(DEFAULT_KIS_US_DEMO_POSITIONS))
    kis_us_demo_parser.add_argument("--quotes", default=str(DEFAULT_KIS_US_DEMO_QUOTES))
    kis_us_demo_parser.add_argument("--cash-usd", type=float, default=1200.0)
    kis_us_demo_parser.add_argument("--as-of", default=date.today().isoformat())
    kis_us_demo_parser.add_argument("--output", default="data/reports/kis_us_paper_order_plan_demo.csv")
    kis_us_demo_parser.add_argument("--summary-output", default="data/reports/kis_us_paper_order_plan_demo.md")

    kis_us_smoke_parser = subparsers.add_parser(
        "kis-us-smoke-check",
        help="Verify KIS US mock token, balance, and quote reads without placing orders",
    )
    kis_us_smoke_parser.add_argument("--symbols", default="AAPL", help="Comma-separated symbols for quote checks")
    kis_us_smoke_parser.add_argument("--quote-exchange", default="NAS", help="KIS quote exchange code")
    kis_us_smoke_parser.add_argument("--balance-exchanges", default="NASD", help="Comma-separated balance exchange codes")
    kis_us_smoke_parser.add_argument("--request-interval-seconds", type=float, default=0.0)
    kis_us_smoke_parser.add_argument("--output", default="data/reports/kis_us_smoke_check.md")

    auto_paper_parser = subparsers.add_parser(
        "auto-paper-run",
        help="Run the local-CSV-only US paper auto-trading research engine",
    )
    auto_paper_parser.add_argument("--prices-dir", default="data/external/yahoo/us_daily")
    auto_paper_parser.add_argument("--universe", default="data/auto_trading/us_core_universe.csv")
    auto_paper_parser.add_argument(
        "--universe-as-of",
        default=None,
        help="Optional YYYY-MM-DD point-in-time universe date; when set, --universe must be a universe history CSV",
    )
    auto_paper_parser.add_argument(
        "--benchmark-report",
        default="data/reports/monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv",
    )
    auto_paper_parser.add_argument("--benchmark-row-selector", default="name=return_concentration")
    auto_paper_parser.add_argument("--usd-krw-rate", type=float, default=1400.0)
    auto_paper_parser.add_argument("--output-dir", default="data/reports/auto_trading")
    auto_paper_parser.add_argument(
        "--external-data-dir",
        default=None,
        help="Optional local CSV directory for free external data proxies; no network calls are made",
    )

    auto_paper_kis_export_parser = subparsers.add_parser(
        "auto-paper-export-kis-targets",
        help="Export a COMPLETE auto paper order plan into a KIS US paper-only target CSV",
    )
    auto_paper_kis_export_parser.add_argument(
        "--auto-order-plan",
        default="data/reports/auto_trading/auto_paper_order_plan.csv",
    )
    auto_paper_kis_export_parser.add_argument("--universe", default="data/auto_trading/us_core_universe.csv")
    auto_paper_kis_export_parser.add_argument(
        "--audit-log",
        default="data/reports/auto_trading/auto_paper_audit_log.json",
    )
    auto_paper_kis_export_parser.add_argument(
        "--output",
        default="data/auto_trading/kis_us_targets_from_auto_paper.csv",
    )

    auto_paper_health_parser = subparsers.add_parser(
        "auto-paper-health-check",
        help="Validate auto paper and KIS paper-only artifacts before any broker read step",
    )
    auto_paper_health_parser.add_argument(
        "--audit-log",
        default="data/reports/auto_trading/auto_paper_audit_log.json",
    )
    auto_paper_health_parser.add_argument(
        "--auto-order-plan",
        default="data/reports/auto_trading/auto_paper_order_plan.csv",
    )
    auto_paper_health_parser.add_argument(
        "--kis-targets",
        default="data/auto_trading/kis_us_targets_from_auto_paper.csv",
    )
    auto_paper_health_parser.add_argument(
        "--kis-order-plan",
        default="data/reports/kis_us_paper_order_plan_from_auto_demo.csv",
    )
    auto_paper_health_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_operation_health.csv",
    )
    auto_paper_health_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_operation_health.md",
    )

    auto_paper_risk_parser = subparsers.add_parser(
        "auto-paper-risk-gate",
        help="Run paper-only portfolio risk gates on exported KIS targets",
    )
    auto_paper_risk_parser.add_argument(
        "--kis-targets",
        default="data/auto_trading/kis_us_targets_from_auto_paper.csv",
    )
    auto_paper_risk_parser.add_argument(
        "--external-data-dir",
        default="data/auto_trading/free_external_data",
    )
    auto_paper_risk_parser.add_argument("--prices-dir", default="data/external/yahoo/us_daily")
    auto_paper_risk_parser.add_argument("--portfolio-value-usd", type=float, default=100_000.0)
    auto_paper_risk_parser.add_argument("--max-single-weight", type=float, default=0.35)
    auto_paper_risk_parser.add_argument("--max-sector-weight", type=float, default=0.50)
    auto_paper_risk_parser.add_argument("--min-beta", type=float, default=0.0)
    auto_paper_risk_parser.add_argument("--max-beta", type=float, default=1.80)
    auto_paper_risk_parser.add_argument("--max-short-volume-ratio", type=float, default=0.35)
    auto_paper_risk_parser.add_argument("--min-news-sentiment", type=float, default=-0.60)
    auto_paper_risk_parser.add_argument("--max-adv-participation", type=float, default=0.05)
    auto_paper_risk_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_portfolio_risk_gate.csv",
    )
    auto_paper_risk_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_portfolio_risk_gate.md",
    )

    auto_paper_adjust_parser = subparsers.add_parser(
        "auto-paper-adjust-targets",
        help="Create risk-adjusted KIS target CSV by removing/capping portfolio risk offenders",
    )
    auto_paper_adjust_parser.add_argument(
        "--kis-targets",
        default="data/auto_trading/kis_us_targets_from_auto_paper.csv",
    )
    auto_paper_adjust_parser.add_argument(
        "--external-data-dir",
        default="data/auto_trading/free_external_data",
    )
    auto_paper_adjust_parser.add_argument("--prices-dir", default="data/external/yahoo/us_daily")
    auto_paper_adjust_parser.add_argument("--portfolio-value-usd", type=float, default=100_000.0)
    auto_paper_adjust_parser.add_argument("--max-single-weight", type=float, default=0.35)
    auto_paper_adjust_parser.add_argument("--max-sector-weight", type=float, default=0.50)
    auto_paper_adjust_parser.add_argument("--min-beta", type=float, default=0.0)
    auto_paper_adjust_parser.add_argument("--max-beta", type=float, default=1.80)
    auto_paper_adjust_parser.add_argument("--max-short-volume-ratio", type=float, default=0.35)
    auto_paper_adjust_parser.add_argument("--min-news-sentiment", type=float, default=-0.60)
    auto_paper_adjust_parser.add_argument("--max-adv-participation", type=float, default=0.05)
    auto_paper_adjust_parser.add_argument(
        "--output",
        default="data/auto_trading/kis_us_targets_from_auto_paper_risk_adjusted.csv",
    )

    auto_paper_register_parser = subparsers.add_parser(
        "auto-paper-register-model",
        help="Register a COMPLETE paper-only model release after risk gate PASS",
    )
    auto_paper_register_parser.add_argument(
        "--audit-log",
        default="data/reports/auto_trading/auto_paper_audit_log.json",
    )
    auto_paper_register_parser.add_argument(
        "--model-config",
        default="data/reports/auto_trading/auto_paper_model_config.json",
    )
    auto_paper_register_parser.add_argument(
        "--cost-policy",
        default="data/reports/auto_trading/auto_paper_cost_policy.md",
    )
    auto_paper_register_parser.add_argument(
        "--risk-gate",
        default="data/reports/auto_trading/auto_paper_portfolio_risk_gate_adjusted.csv",
    )
    auto_paper_register_parser.add_argument("--version", required=True)
    auto_paper_register_parser.add_argument("--rollback-reference", default="")
    auto_paper_register_parser.add_argument("--previous-registry", default=None)
    auto_paper_register_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_model_registry.json",
    )

    auto_paper_execution_parser = subparsers.add_parser(
        "auto-paper-simulate-execution",
        help="Simulate paper-only fills from a dry-run order plan",
    )
    auto_paper_execution_parser.add_argument(
        "--orders",
        default="data/reports/kis_us_paper_order_plan_from_auto_risk_adjusted_demo.csv",
    )
    auto_paper_execution_parser.add_argument("--prices-dir", default="data/external/yahoo/us_daily")
    auto_paper_execution_parser.add_argument(
        "--fill-policy",
        choices=["close", "open", "next_bar", "vwap_proxy"],
        default="close",
    )
    auto_paper_execution_parser.add_argument("--max-adv-participation", type=float, default=0.05)
    auto_paper_execution_parser.add_argument("--spread-rate", type=float, default=0.001)
    auto_paper_execution_parser.add_argument("--slippage-rate", type=float, default=0.001)
    auto_paper_execution_parser.add_argument("--execution-time-kst", default="")
    auto_paper_execution_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_execution_simulation.csv",
    )

    auto_paper_market_impact_parser = subparsers.add_parser(
        "auto-paper-market-impact",
        help="Estimate paper-only market impact from a dry-run order plan and local daily prices",
    )
    auto_paper_market_impact_parser.add_argument(
        "--orders",
        default="data/reports/kis_us_paper_order_plan_from_auto_risk_adjusted_demo.csv",
    )
    auto_paper_market_impact_parser.add_argument("--prices-dir", default="data/external/yahoo/us_daily")
    auto_paper_market_impact_parser.add_argument(
        "--scenario",
        choices=["base", "conservative", "stress"],
        default="base",
    )
    auto_paper_market_impact_parser.add_argument("--spread-rate", type=float, default=0.001)
    auto_paper_market_impact_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_market_impact.csv",
    )

    auto_paper_factor_risk_parser = subparsers.add_parser(
        "auto-paper-factor-risk",
        help="Evaluate institutional-style paper-only factor risk from local target and factor CSVs",
    )
    auto_paper_factor_risk_parser.add_argument(
        "--kis-targets",
        default="data/auto_trading/kis_us_targets_from_auto_paper_risk_adjusted.csv",
    )
    auto_paper_factor_risk_parser.add_argument(
        "--external-data-dir",
        default="data/auto_trading/free_external_data",
    )
    auto_paper_factor_risk_parser.add_argument("--max-single-weight", type=float, default=0.35)
    auto_paper_factor_risk_parser.add_argument("--max-sector-weight", type=float, default=0.50)
    auto_paper_factor_risk_parser.add_argument("--max-weighted-beta", type=float, default=1.50)
    auto_paper_factor_risk_parser.add_argument("--max-negative-quality-tilt", type=float, default=0.20)
    auto_paper_factor_risk_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_factor_risk.csv",
    )
    auto_paper_factor_risk_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_factor_risk.md",
    )

    auto_paper_optimizer_parser = subparsers.add_parser(
        "auto-paper-optimize-portfolio",
        help="Create paper-only optimized target weights from local candidate and factor CSVs",
    )
    auto_paper_optimizer_parser.add_argument(
        "--candidates",
        default="data/auto_trading/us_portfolio_optimizer_candidates.csv",
    )
    auto_paper_optimizer_parser.add_argument(
        "--external-data-dir",
        default="data/auto_trading/free_external_data",
    )
    auto_paper_optimizer_parser.add_argument("--max-total-weight", type=float, default=0.98)
    auto_paper_optimizer_parser.add_argument("--max-single-weight", type=float, default=0.35)
    auto_paper_optimizer_parser.add_argument("--max-sector-weight", type=float, default=0.50)
    auto_paper_optimizer_parser.add_argument("--max-weighted-beta", type=float, default=1.50)
    auto_paper_optimizer_parser.add_argument("--max-symbol-beta", type=float, default=1.80)
    auto_paper_optimizer_parser.add_argument("--min-quality-score", type=float, default=0.50)
    auto_paper_optimizer_parser.add_argument("--min-alpha-score", type=float, default=0.0)
    auto_paper_optimizer_parser.add_argument("--weight-step", type=float, default=0.01)
    auto_paper_optimizer_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_optimized_targets.csv",
    )
    auto_paper_optimizer_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_optimized_targets.md",
    )

    auto_paper_tca_parser = subparsers.add_parser(
        "auto-paper-tca",
        help="Write a paper-only transaction-cost-analysis report from simulated fills",
    )
    auto_paper_tca_parser.add_argument(
        "--executions",
        default="data/reports/auto_trading/auto_paper_execution_simulation.csv",
    )
    auto_paper_tca_parser.add_argument(
        "--market-impact",
        default="data/reports/auto_trading/auto_paper_market_impact.csv",
    )
    auto_paper_tca_parser.add_argument("--max-shortfall-bps", type=float, default=50.0)
    auto_paper_tca_parser.add_argument("--max-cost-variance-usd", type=float, default=5.0)
    auto_paper_tca_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_tca.csv",
    )
    auto_paper_tca_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_tca.md",
    )

    auto_paper_external_readiness_parser = subparsers.add_parser(
        "auto-paper-external-data-readiness",
        help="Validate local free external data adapters and write a paper-only readiness manifest",
    )
    auto_paper_external_readiness_parser.add_argument(
        "--external-data-dir",
        default="data/auto_trading/free_external_data",
    )
    auto_paper_external_readiness_parser.add_argument("--symbols", default="")
    auto_paper_external_readiness_parser.add_argument(
        "--candidates",
        default="data/auto_trading/us_portfolio_optimizer_candidates.csv",
    )
    auto_paper_external_readiness_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_external_data_readiness.csv",
    )
    auto_paper_external_readiness_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_external_data_readiness.md",
    )

    auto_paper_monitoring_parser = subparsers.add_parser(
        "auto-paper-monitoring-report",
        help="Summarize local paper-only scheduler gate artifacts into one monitoring report",
    )
    auto_paper_monitoring_parser.add_argument(
        "--audit-log",
        default="data/reports/auto_trading/auto_paper_audit_log.json",
    )
    auto_paper_monitoring_parser.add_argument(
        "--external-data-readiness",
        default="data/reports/auto_trading/auto_paper_external_data_readiness.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--portfolio-risk-gate",
        default="data/reports/auto_trading/auto_paper_portfolio_risk_gate_adjusted.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--factor-risk",
        default="data/reports/auto_trading/auto_paper_factor_risk.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--tca-report",
        default="data/reports/auto_trading/auto_paper_tca.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--operation-health",
        default="data/reports/auto_trading/auto_paper_operation_health_risk_adjusted.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--output",
        default="data/reports/auto_trading/auto_paper_scheduler_monitoring.csv",
    )
    auto_paper_monitoring_parser.add_argument(
        "--markdown-output",
        default="data/reports/auto_trading/auto_paper_scheduler_monitoring.md",
    )
