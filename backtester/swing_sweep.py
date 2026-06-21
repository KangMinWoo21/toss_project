from dataclasses import dataclass
from statistics import mean

from .analysis import WalkForwardResult, WalkForwardSummary, filter_candles, generate_rolling_windows, summarize_walk_forward
from .engine import BacktestConfig, BacktestResult, Backtester
from .models import Candle
from .strategies import (
    BollingerMeanReversionStrategy,
    CompositeSwingStrategy,
    DonchianAtrBreakoutStrategy,
    MacdRsiTrendStrategy,
    Strategy,
    TimeSeriesMomentumStrategy,
)


@dataclass(frozen=True)
class SwingSweepReport:
    periods: list[WalkForwardResult]
    summary: list[WalkForwardSummary]
    strategy_count: int


@dataclass(frozen=True)
class CandidateValidationRow:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    best_strategy: str
    train_return_pct: float
    test_return_pct: float
    buy_hold_return_pct: float
    excess_return_pct: float
    test_mdd_pct: float
    test_trade_count: int
    accepted: bool
    reject_reason: str


def build_swing_strategy_grid(preset: str = "compact") -> list[Strategy]:
    if preset not in {"compact", "full"}:
        raise ValueError("preset must be compact or full")

    if preset == "compact":
        momentum_lookbacks = [20, 40]
        momentum_returns = [3.0, 5.0]
        bollinger_windows = [10, 20]
        bollinger_stdevs = [1.5, 2.0]
        donchian_entries = [10, 20]
        composite_votes = [2, 3]
    else:
        momentum_lookbacks = [20, 40, 60]
        momentum_returns = [3.0, 5.0, 8.0]
        bollinger_windows = [10, 20, 30]
        bollinger_stdevs = [1.5, 2.0, 2.5]
        donchian_entries = [10, 20, 40]
        composite_votes = [2, 3, 4]

    strategies: list[Strategy] = []
    for lookback in momentum_lookbacks:
        for min_return in momentum_returns:
            strategies.append(
                TimeSeriesMomentumStrategy(
                    lookback=lookback,
                    min_return_pct=min_return,
                    name=f"tsm_l{lookback}_r{_fmt(min_return)}",
                )
            )

    for buy_rsi in (50.0, 55.0):
        strategies.append(
            MacdRsiTrendStrategy(
                buy_rsi=buy_rsi,
                sell_rsi=buy_rsi - 7.0,
                name=f"macd_rsi_b{_fmt(buy_rsi)}",
            )
        )

    for window in bollinger_windows:
        for stdev in bollinger_stdevs:
            for rsi_buy in (30.0, 35.0):
                strategies.append(
                    BollingerMeanReversionStrategy(
                        window=window,
                        stdev_multiplier=stdev,
                        rsi_buy_below=rsi_buy,
                        name=f"bb_revert_w{window}_s{_fmt(stdev)}_r{_fmt(rsi_buy)}",
                    )
                )

    for entry_window in donchian_entries:
        exit_window = max(5, entry_window // 2)
        for atr_stop in (1.5, 2.0):
            strategies.append(
                DonchianAtrBreakoutStrategy(
                    entry_window=entry_window,
                    exit_window=exit_window,
                    atr_stop_multiplier=atr_stop,
                    name=f"donchian_e{entry_window}_x{exit_window}_atr{_fmt(atr_stop)}",
                )
            )

    for momentum_lookback in momentum_lookbacks:
        for min_votes in composite_votes:
            trend_window = max(20, momentum_lookback)
            breakout_window = max(10, momentum_lookback // 2)
            strategies.append(
                CompositeSwingStrategy(
                    momentum_lookback=momentum_lookback,
                    trend_window=trend_window,
                    breakout_window=breakout_window,
                    min_votes=min_votes,
                    name=f"composite_m{momentum_lookback}_t{trend_window}_b{breakout_window}_v{min_votes}",
                )
            )

    return strategies


def build_candidate_strategy_grid() -> list[Strategy]:
    return [
        TimeSeriesMomentumStrategy(lookback=20, min_return_pct=5.0, name="tsm_l20_r5"),
        CompositeSwingStrategy(
            momentum_lookback=20,
            trend_window=20,
            breakout_window=10,
            min_votes=2,
            name="composite_m20_t20_b10_v2",
        ),
    ]


def run_swing_parameter_sweep(
    *,
    candles: list[Candle],
    train_size: int,
    test_size: int,
    step_size: int | None,
    config: BacktestConfig,
    preset: str = "compact",
) -> SwingSweepReport:
    strategies = build_swing_strategy_grid(preset=preset)
    windows = generate_rolling_windows(candles, train_size=train_size, test_size=test_size, step_size=step_size)
    engine = Backtester(config=config)
    periods: list[WalkForwardResult] = []
    for train_start, train_end, test_start, test_end in windows:
        train_candles = _require_period(candles, train_start, train_end)
        test_candles = _require_period(candles, test_start, test_end)
        train_results = [engine.run(train_candles, strategy) for strategy in strategies]
        best_train = max(train_results, key=score_swing_train_result)
        best_strategy = _strategy_by_name(strategies, best_train.strategy_name)
        test_result = engine.run(test_candles, best_strategy)
        periods.append(
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
    return SwingSweepReport(
        periods=periods,
        summary=summarize_walk_forward(periods),
        strategy_count=len(strategies),
    )


def run_candidate_validation(
    *,
    candles: list[Candle],
    train_size: int,
    test_size: int,
    step_size: int | None,
    config: BacktestConfig,
) -> list[CandidateValidationRow]:
    strategies = build_candidate_strategy_grid()
    windows = generate_rolling_windows(candles, train_size=train_size, test_size=test_size, step_size=step_size)
    engine = Backtester(config=config)
    rows: list[CandidateValidationRow] = []
    for train_start, train_end, test_start, test_end in windows:
        train_candles = _require_period(candles, train_start, train_end)
        test_candles = _require_period(candles, test_start, test_end)
        train_results = [engine.run(train_candles, strategy) for strategy in strategies]
        best_train = max(train_results, key=score_swing_train_result)
        best_strategy = _strategy_by_name(strategies, best_train.strategy_name)
        test_result = engine.run(test_candles, best_strategy)
        buy_hold_result = engine.run(test_candles, _BuyAndHoldForCandidate())
        excess = test_result.total_return_pct - buy_hold_result.total_return_pct
        accepted = test_result.trade_count > 0 and excess > 0
        reject_reason = ""
        if test_result.trade_count == 0:
            reject_reason = "no_test_trade"
        elif excess <= 0:
            reject_reason = "no_positive_excess"
        rows.append(
            CandidateValidationRow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                best_strategy=best_train.strategy_name,
                train_return_pct=best_train.total_return_pct,
                test_return_pct=test_result.total_return_pct,
                buy_hold_return_pct=buy_hold_result.total_return_pct,
                excess_return_pct=excess,
                test_mdd_pct=test_result.max_drawdown_pct,
                test_trade_count=test_result.trade_count,
                accepted=accepted,
                reject_reason=reject_reason,
            )
        )
    return rows


def summarize_candidate_validation(rows: list[CandidateValidationRow]) -> dict[str, float]:
    if not rows:
        return {
            "windows": 0,
            "accepted": 0,
            "accepted_pct": 0.0,
            "avg_test_pct": 0.0,
            "avg_buy_hold_pct": 0.0,
            "avg_excess_pct": 0.0,
        }
    return {
        "windows": len(rows),
        "accepted": sum(row.accepted for row in rows),
        "accepted_pct": sum(row.accepted for row in rows) / len(rows) * 100,
        "avg_test_pct": mean(row.test_return_pct for row in rows),
        "avg_buy_hold_pct": mean(row.buy_hold_return_pct for row in rows),
        "avg_excess_pct": mean(row.excess_return_pct for row in rows),
    }


def score_swing_train_result(result: BacktestResult) -> tuple[int, float, float, float]:
    active = 1 if result.trade_count > 0 else 0
    calmar = result.calmar_ratio if result.calmar_ratio != float("inf") else result.total_return_pct
    return (active, calmar, result.total_return_pct, -abs(result.max_drawdown_pct))


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


class _BuyAndHoldForCandidate(Strategy):
    name = "buy_and_hold_candidate"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> str:
        if index == 0 and position is None:
            return "BUY"
        if index == len(candles) - 1 and position is not None:
            return "SELL"
        return "HOLD"


def _fmt(value: float) -> str:
    text = f"{value:g}"
    return text.replace(".", "p")
