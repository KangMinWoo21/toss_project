from collections import defaultdict
from statistics import mean

from .leader_swing import LeaderSwingConfig, run_leader_swing_backtest
from .models import Candle


def generate_date_windows(dates: list[str], window_size: int, step_size: int) -> list[tuple[str, str]]:
    if window_size <= 1:
        raise ValueError("window_size must be greater than 1")
    if step_size <= 0:
        raise ValueError("step_size must be positive")
    windows: list[tuple[str, str]] = []
    start_index = 0
    while start_index + window_size <= len(dates):
        windows.append((dates[start_index], dates[start_index + window_size - 1]))
        start_index += step_size
    return windows


def classify_regime(buy_hold_return_pct: float) -> str:
    if buy_hold_return_pct >= 10.0:
        return "up"
    if buy_hold_return_pct <= -10.0:
        return "down"
    return "sideways"


def run_leader_window_study(
    symbol_candles: dict[str, list[Candle]],
    configs: dict[str, LeaderSwingConfig],
    window_lengths: list[int],
    step_fraction: float = 0.5,
    min_rows: int = 80,
) -> list[dict[str, object]]:
    dates = sorted({candle.date for candles in symbol_candles.values() for candle in candles})
    rows: list[dict[str, object]] = []
    for window_length in window_lengths:
        step_size = max(1, int(window_length * step_fraction))
        for start, end in generate_date_windows(dates, window_length, step_size):
            window_data = _slice_symbol_candles(symbol_candles, start, end, min_rows=min_rows)
            if not window_data:
                continue
            buy_hold_pct = _equal_weight_period_return(window_data)
            regime = classify_regime(buy_hold_pct)
            for config_name, config in configs.items():
                result = run_leader_swing_backtest(window_data, config)
                rows.append(
                    {
                        "config_name": config_name,
                        "window_length": window_length,
                        "start": start,
                        "end": end,
                        "regime": regime,
                        "symbols": len(window_data),
                        "return_pct": round(result.total_return_pct, 4),
                        "buy_hold_pct": round(buy_hold_pct, 4),
                        "excess_pct": round(result.total_return_pct - buy_hold_pct, 4),
                        "mdd_pct": round(result.max_drawdown_pct, 4),
                        "trades": result.trade_count,
                        "win_pct": round(result.win_rate_pct, 4),
                    }
                )
    return rows


def summarize_window_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["config_name"]), int(row["window_length"]), str(row["regime"]))].append(row)

    summaries: list[dict[str, object]] = []
    for (config_name, window_length, regime), values in grouped.items():
        returns = [float(row["return_pct"]) for row in values]
        buy_holds = [float(row["buy_hold_pct"]) for row in values]
        excesses = [float(row["excess_pct"]) for row in values]
        mdds = [float(row["mdd_pct"]) for row in values]
        summaries.append(
            {
                "config_name": config_name,
                "window_length": window_length,
                "regime": regime,
                "windows": len(values),
                "avg_return_pct": round(mean(returns), 4),
                "avg_buy_hold_pct": round(mean(buy_holds), 4),
                "avg_excess_pct": round(mean(excesses), 4),
                "avg_mdd_pct": round(mean(mdds), 4),
                "positive_window_pct": round(sum(1 for value in returns if value > 0) / len(returns) * 100, 4),
                "positive_excess_pct": round(sum(1 for value in excesses if value > 0) / len(excesses) * 100, 4),
            }
        )
    return sorted(summaries, key=lambda row: (int(row["window_length"]), str(row["regime"]), -float(row["avg_return_pct"])))


def _slice_symbol_candles(
    symbol_candles: dict[str, list[Candle]],
    start: str,
    end: str,
    min_rows: int,
) -> dict[str, list[Candle]]:
    sliced: dict[str, list[Candle]] = {}
    for symbol, candles in symbol_candles.items():
        rows = [candle for candle in candles if start <= candle.date <= end]
        if len(rows) >= min_rows:
            sliced[symbol] = rows
    return sliced


def _equal_weight_period_return(symbol_candles: dict[str, list[Candle]]) -> float:
    returns = [(candles[-1].close / candles[0].close - 1) * 100 for candles in symbol_candles.values()]
    return mean(returns) if returns else 0.0
