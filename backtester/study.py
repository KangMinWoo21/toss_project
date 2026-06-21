from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from .analysis import filter_candles, generate_rolling_windows
from .data import load_candles
from .engine import BacktestConfig, Backtester
from .strategies import Strategy


@dataclass(frozen=True)
class RegimeStudyRow:
    regime: str
    strategy_name: str
    window_count: int
    average_return_pct: float
    average_mdd_pct: float
    win_rate_pct: float


def run_market_regime_study(
    data_files: list[Path],
    strategies: list[Strategy],
    train_size: int,
    test_size: int,
    step_size: int | None,
    config: BacktestConfig,
) -> list[RegimeStudyRow]:
    grouped: dict[tuple[str, str], list[tuple[float, float]]] = {}
    engine = Backtester(config=config)

    for path in data_files:
        candles = load_candles(path)
        windows = generate_rolling_windows(candles, train_size=train_size, test_size=test_size, step_size=step_size)
        for _, _, test_start, test_end in windows:
            test_candles = filter_candles(candles, start=test_start, end=test_end)
            if not test_candles:
                continue
            buy_hold_return = (test_candles[-1].close / test_candles[0].close - 1) * 100
            regime = "up" if buy_hold_return >= 0 else "down"
            for strategy in strategies:
                result = engine.run(test_candles, strategy)
                grouped.setdefault((regime, strategy.name), []).append(
                    (result.total_return_pct, result.max_drawdown_pct)
                )

    rows: list[RegimeStudyRow] = []
    for (regime, strategy_name), values in grouped.items():
        returns = [value[0] for value in values]
        mdds = [value[1] for value in values]
        rows.append(
            RegimeStudyRow(
                regime=regime,
                strategy_name=strategy_name,
                window_count=len(values),
                average_return_pct=mean(returns),
                average_mdd_pct=mean(mdds),
                win_rate_pct=sum(1 for value in returns if value > 0) / len(returns) * 100,
            )
        )

    return sorted(rows, key=lambda row: (row.regime, -row.average_return_pct, row.strategy_name))


def data_files_from_dir(data_dir: Path | str) -> list[Path]:
    return sorted(Path(data_dir).glob("*.csv"))
