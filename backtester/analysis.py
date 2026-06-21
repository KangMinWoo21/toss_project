from dataclasses import dataclass
from statistics import mean

from .engine import BacktestConfig, Backtester, BacktestResult
from .models import Candle
from .strategies import Strategy


Window = tuple[str, str, str, str]


@dataclass(frozen=True)
class WalkForwardResult:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    best_strategy: str
    train_return_pct: float
    test_return_pct: float
    test_mdd_pct: float
    test_trade_count: int


@dataclass(frozen=True)
class WalkForwardSummary:
    strategy_name: str
    window_count: int
    average_test_return_pct: float
    total_test_return_pct: float
    average_test_mdd_pct: float


def filter_candles(candles: list[Candle], start: str | None = None, end: str | None = None) -> list[Candle]:
    return [
        candle
        for candle in candles
        if (start is None or candle.date >= start) and (end is None or candle.date <= end)
    ]


def generate_rolling_windows(
    candles: list[Candle],
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> list[Window]:
    if train_size <= 1:
        raise ValueError("train_size must be greater than 1")
    if test_size <= 1:
        raise ValueError("test_size must be greater than 1")
    step = step_size or test_size
    if step <= 0:
        raise ValueError("step_size must be positive")

    windows: list[Window] = []
    start_index = 0
    while start_index + train_size + test_size <= len(candles):
        train_start = candles[start_index].date
        train_end = candles[start_index + train_size - 1].date
        test_start = candles[start_index + train_size].date
        test_end = candles[start_index + train_size + test_size - 1].date
        windows.append((train_start, train_end, test_start, test_end))
        start_index += step
    return windows


def walk_forward(
    candles: list[Candle],
    strategies: list[Strategy],
    windows: list[Window],
    config: BacktestConfig,
) -> list[WalkForwardResult]:
    if not strategies:
        raise ValueError("strategies cannot be empty")
    if not windows:
        raise ValueError("windows cannot be empty")

    engine = Backtester(config=config)
    results: list[WalkForwardResult] = []
    for train_start, train_end, test_start, test_end in windows:
        train_candles = _require_period(candles, train_start, train_end)
        test_candles = _require_period(candles, test_start, test_end)
        train_results = [engine.run(train_candles, strategy) for strategy in strategies]
        best_train = max(train_results, key=_score_result)
        best_strategy = _strategy_by_name(strategies, best_train.strategy_name)
        test_result = engine.run(test_candles, best_strategy)
        results.append(
            WalkForwardResult(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                best_strategy=best_train.strategy_name,
                train_return_pct=best_train.total_return_pct,
                test_return_pct=test_result.total_return_pct,
                test_mdd_pct=test_result.max_drawdown_pct,
                test_trade_count=test_result.trade_count,
            )
        )
    return results


def summarize_walk_forward(results: list[WalkForwardResult]) -> list[WalkForwardSummary]:
    grouped: dict[str, list[WalkForwardResult]] = {}
    for result in results:
        grouped.setdefault(result.best_strategy, []).append(result)

    summaries = [
        WalkForwardSummary(
            strategy_name=strategy_name,
            window_count=len(strategy_results),
            average_test_return_pct=mean(r.test_return_pct for r in strategy_results),
            total_test_return_pct=sum(r.test_return_pct for r in strategy_results),
            average_test_mdd_pct=mean(r.test_mdd_pct for r in strategy_results),
        )
        for strategy_name, strategy_results in grouped.items()
    ]
    return sorted(summaries, key=lambda row: row.average_test_return_pct, reverse=True)


def _score_result(result: BacktestResult) -> tuple[float, float]:
    calmar = result.calmar_ratio if result.calmar_ratio != float("inf") else result.total_return_pct
    return (calmar, result.total_return_pct)


def _strategy_by_name(strategies: list[Strategy], name: str) -> Strategy:
    for strategy in strategies:
        if strategy.name == name:
            return strategy
    raise ValueError(f"strategy not found: {name}")


def _require_period(candles: list[Candle], start: str, end: str) -> list[Candle]:
    filtered = filter_candles(candles, start=start, end=end)
    if not filtered:
        raise ValueError(f"no candles in period {start} to {end}")
    return filtered
