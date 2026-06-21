from .engine import BacktestResult
from .analysis import WalkForwardResult, WalkForwardSummary
from .study import RegimeStudyRow
from .swing_sweep import CandidateValidationRow


def format_results_table(results: list[BacktestResult]) -> str:
    headers = [
        "strategy",
        "final_equity",
        "return_%",
        "mdd_%",
        "trades",
        "win_%",
        "profit_factor",
        "sharpe",
        "calmar",
    ]
    rows = [
        [
            result.strategy_name,
            f"{result.final_equity:,.0f}",
            f"{result.total_return_pct:.2f}",
            f"{result.max_drawdown_pct:.2f}",
            str(result.trade_count),
            f"{result.win_rate_pct:.2f}",
            _format_profit_factor(result.profit_factor),
            f"{result.sharpe_ratio:.2f}",
            _format_profit_factor(result.calmar_ratio),
        ]
        for result in results
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _format_profit_factor(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return f"{value:.2f}"


def format_walk_forward_table(results: list[WalkForwardResult]) -> str:
    headers = [
        "train",
        "test",
        "best_strategy",
        "train_%",
        "test_%",
        "test_mdd_%",
        "trades",
    ]
    rows = [
        [
            f"{result.train_start}~{result.train_end}",
            f"{result.test_start}~{result.test_end}",
            result.best_strategy,
            f"{result.train_return_pct:.2f}",
            f"{result.test_return_pct:.2f}",
            f"{result.test_mdd_pct:.2f}",
            str(result.test_trade_count),
        ]
        for result in results
    ]
    return _format_table(headers, rows)


def format_walk_forward_summary_table(summaries: list[WalkForwardSummary]) -> str:
    headers = [
        "strategy",
        "picked",
        "avg_test_%",
        "total_test_%",
        "avg_mdd_%",
    ]
    rows = [
        [
            summary.strategy_name,
            str(summary.window_count),
            f"{summary.average_test_return_pct:.2f}",
            f"{summary.total_test_return_pct:.2f}",
            f"{summary.average_test_mdd_pct:.2f}",
        ]
        for summary in summaries
    ]
    return _format_table(headers, rows)


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "no results"
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def format_regime_study_table(rows: list[RegimeStudyRow]) -> str:
    headers = [
        "regime",
        "strategy",
        "windows",
        "avg_return_%",
        "avg_mdd_%",
        "win_%",
    ]
    table_rows = [
        [
            row.regime,
            row.strategy_name,
            str(row.window_count),
            f"{row.average_return_pct:.2f}",
            f"{row.average_mdd_pct:.2f}",
            f"{row.win_rate_pct:.2f}",
        ]
        for row in rows
    ]
    return _format_table(headers, table_rows)


def format_candidate_validation_table(rows: list[CandidateValidationRow]) -> str:
    headers = [
        "test",
        "strategy",
        "train_%",
        "test_%",
        "bh_%",
        "excess_%",
        "trades",
        "accepted",
        "reason",
    ]
    table_rows = [
        [
            f"{row.test_start}~{row.test_end}",
            row.best_strategy,
            f"{row.train_return_pct:.2f}",
            f"{row.test_return_pct:.2f}",
            f"{row.buy_hold_return_pct:.2f}",
            f"{row.excess_return_pct:.2f}",
            str(row.test_trade_count),
            "Y" if row.accepted else "N",
            row.reject_reason,
        ]
        for row in rows
    ]
    return _format_table(headers, table_rows)


def format_candidate_summary(summary: dict[str, float]) -> str:
    headers = ["windows", "accepted", "accepted_%", "avg_test_%", "avg_bh_%", "avg_excess_%"]
    rows = [
        [
            str(int(summary["windows"])),
            str(int(summary["accepted"])),
            f"{summary['accepted_pct']:.2f}",
            f"{summary['avg_test_pct']:.2f}",
            f"{summary['avg_buy_hold_pct']:.2f}",
            f"{summary['avg_excess_pct']:.2f}",
        ]
    ]
    return _format_table(headers, rows)
