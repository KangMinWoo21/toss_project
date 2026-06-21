import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from statistics import mean, pstdev
from typing import Callable


@dataclass(frozen=True)
class ScalpTick:
    timestamp: datetime
    price: float
    volume: float
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float
    imbalance: float
    spread_pct: float
    price_up: bool = False
    price_down: bool = False
    volume_spike: bool = False
    ma_fast: float = 0.0
    ma_slow: float = 0.0
    zscore: float = 0.0


@dataclass(frozen=True)
class ScalpStrategySpec:
    name: str
    direction: str
    predicate: Callable[[ScalpTick], bool]


@dataclass(frozen=True)
class ScalpReplayResult:
    symbol: str
    date: str
    strategy_name: str
    horizon: int
    trade_count: int
    average_return_pct: float
    win_rate_pct: float
    profit_factor: float
    total_return_pct_sum: float
    gross_profit_pct_sum: float = 0.0
    gross_loss_pct_sum: float = 0.0


def discover_scalp_files(data_dir: str | Path, symbols: list[str] | None = None, include_us: bool = False) -> list[Path]:
    root = Path(data_dir)
    allowed = set(symbols or [])
    paths: list[Path] = []
    for path in root.glob("*_paper_scalp.csv"):
        parsed = _parse_scalp_filename(path)
        if parsed is None or path.stat().st_size <= 200:
            continue
        symbol, _ = parsed
        if allowed and symbol not in allowed:
            continue
        if not include_us and not re.fullmatch(r"\d{6}", symbol):
            continue
        paths.append(path)
    return sorted(paths)


def load_scalp_ticks(
    path: str | Path,
    *,
    start_time: time = time(9, 0),
    end_time: time = time(15, 20),
    max_spread_pct: float = 0.2,
    volume_window: int = 20,
    fast_window: int = 5,
    slow_window: int = 20,
    zscore_window: int = 20,
    volume_spike_multiplier: float = 2.0,
) -> list[ScalpTick]:
    raw_ticks: list[ScalpTick] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tick = _row_to_tick(row)
            if tick is None:
                continue
            if tick.timestamp.time() < start_time or tick.timestamp.time() >= end_time:
                continue
            if tick.spread_pct > max_spread_pct:
                continue
            raw_ticks.append(tick)

    enriched: list[ScalpTick] = []
    prices: list[float] = []
    volumes: list[float] = []
    for tick in raw_ticks:
        previous = enriched[-1] if enriched else None
        prices.append(tick.price)
        volumes.append(tick.volume)
        fast_prices = prices[-fast_window:]
        slow_prices = prices[-slow_window:]
        z_prices = prices[-zscore_window:]
        ma_fast = mean(fast_prices)
        ma_slow = mean(slow_prices)
        stdev = pstdev(z_prices) if len(z_prices) > 1 else 0.0
        zscore = (tick.price - mean(z_prices)) / stdev if stdev else 0.0
        volume_base = mean(volumes[-(volume_window + 1) : -1]) if len(volumes) > 1 else 0.0
        enriched.append(
            ScalpTick(
                timestamp=tick.timestamp,
                price=tick.price,
                volume=tick.volume,
                best_bid=tick.best_bid,
                best_ask=tick.best_ask,
                bid_volume=tick.bid_volume,
                ask_volume=tick.ask_volume,
                imbalance=tick.imbalance,
                spread_pct=tick.spread_pct,
                price_up=previous is not None and tick.price > previous.price,
                price_down=previous is not None and tick.price < previous.price,
                volume_spike=volume_base > 0 and tick.volume >= volume_base * volume_spike_multiplier,
                ma_fast=ma_fast,
                ma_slow=ma_slow,
                zscore=zscore,
            )
        )
    return enriched


def open_source_inspired_strategy_specs() -> list[ScalpStrategySpec]:
    specs: list[ScalpStrategySpec] = []
    for threshold in (1.5, 2.0, 3.0):
        specs.append(
            ScalpStrategySpec(
                name=f"imbalance_momentum_{threshold}",
                direction="long",
                predicate=lambda tick, threshold=threshold: tick.imbalance >= threshold,
            )
        )
        specs.append(
            ScalpStrategySpec(
                name=f"imbalance_price_momentum_{threshold}",
                direction="long",
                predicate=lambda tick, threshold=threshold: tick.imbalance >= threshold and tick.price_up,
            )
        )
        specs.append(
            ScalpStrategySpec(
                name=f"liquidity_sweep_{threshold}",
                direction="long",
                predicate=lambda tick, threshold=threshold: tick.imbalance >= threshold and tick.price_up and tick.volume_spike,
            )
        )
    for multiplier_name in ("2.0",):
        specs.append(
            ScalpStrategySpec(
                name=f"volume_price_breakout_{multiplier_name}",
                direction="long",
                predicate=lambda tick: tick.price_up and tick.volume_spike,
            )
        )
    specs.extend(
        [
            ScalpStrategySpec(
                name="ma_micro_trend",
                direction="long",
                predicate=lambda tick: tick.ma_fast > tick.ma_slow and tick.price_up and tick.imbalance >= 1.2,
            ),
            ScalpStrategySpec(
                name="bollinger_reversion_long",
                direction="long",
                predicate=lambda tick: tick.zscore <= -1.5 and tick.imbalance >= 1.0,
            ),
            ScalpStrategySpec(
                name="ask_pressure_short",
                direction="short",
                predicate=lambda tick: tick.imbalance <= 0.5 and tick.price_down,
            ),
            ScalpStrategySpec(
                name="bollinger_reversion_short",
                direction="short",
                predicate=lambda tick: tick.zscore >= 1.5 and tick.imbalance <= 1.0,
            ),
        ]
    )
    return specs


def replay_scalp_file(
    path: str | Path,
    *,
    horizons: list[int],
    min_trades: int = 30,
    max_spread_pct: float = 0.2,
) -> list[ScalpReplayResult]:
    parsed = _parse_scalp_filename(Path(path))
    if parsed is None:
        raise ValueError(f"invalid scalp filename: {path}")
    symbol, date = parsed
    ticks = load_scalp_ticks(path, max_spread_pct=max_spread_pct)
    results: list[ScalpReplayResult] = []
    for spec in open_source_inspired_strategy_specs():
        for horizon in horizons:
            returns = _replay_returns(ticks, spec, horizon)
            if len(returns) < min_trades:
                continue
            results.append(
                ScalpReplayResult(
                    symbol=symbol,
                    date=date,
                    strategy_name=spec.name,
                    horizon=horizon,
                    trade_count=len(returns),
                    average_return_pct=mean(returns),
                    win_rate_pct=sum(value > 0 for value in returns) / len(returns) * 100,
                    profit_factor=_profit_factor(returns),
                    total_return_pct_sum=sum(returns),
                    gross_profit_pct_sum=sum(value for value in returns if value > 0),
                    gross_loss_pct_sum=-sum(value for value in returns if value < 0),
                )
            )
    return sorted(results, key=lambda row: (row.average_return_pct, row.profit_factor, row.trade_count), reverse=True)


def replay_scalp_directory(
    data_dir: str | Path,
    *,
    symbols: list[str] | None = None,
    include_us: bool = False,
    horizons: list[int] | None = None,
    min_trades: int = 30,
    max_spread_pct: float = 0.2,
) -> list[ScalpReplayResult]:
    all_results: list[ScalpReplayResult] = []
    for path in discover_scalp_files(data_dir, symbols=symbols, include_us=include_us):
        all_results.extend(
            replay_scalp_file(
                path,
                horizons=horizons or [3, 5, 10, 20, 40],
                min_trades=min_trades,
                max_spread_pct=max_spread_pct,
            )
        )
    return sorted(all_results, key=lambda row: (row.average_return_pct, row.profit_factor, row.trade_count), reverse=True)


def aggregate_scalp_results(results: list[ScalpReplayResult], *, min_trades: int = 100) -> list[ScalpReplayResult]:
    grouped: dict[tuple[str, str, int], list[ScalpReplayResult]] = defaultdict(list)
    for result in results:
        grouped[(result.symbol, result.strategy_name, result.horizon)].append(result)

    aggregated: list[ScalpReplayResult] = []
    for (symbol, strategy_name, horizon), rows in grouped.items():
        trade_count = sum(row.trade_count for row in rows)
        if trade_count < min_trades:
            continue
        weighted_sum = sum(row.average_return_pct * row.trade_count for row in rows)
        win_count = sum(row.win_rate_pct / 100 * row.trade_count for row in rows)
        total_return = sum(row.total_return_pct_sum for row in rows)
        gross_profit = sum(row.gross_profit_pct_sum for row in rows)
        gross_loss = sum(row.gross_loss_pct_sum for row in rows)
        aggregated.append(
            ScalpReplayResult(
                symbol=symbol,
                date="ALL",
                strategy_name=strategy_name,
                horizon=horizon,
                trade_count=trade_count,
                average_return_pct=weighted_sum / trade_count,
                win_rate_pct=win_count / trade_count * 100,
                profit_factor=(gross_profit / gross_loss) if gross_loss else (math.inf if gross_profit else 0.0),
                total_return_pct_sum=total_return,
                gross_profit_pct_sum=gross_profit,
                gross_loss_pct_sum=gross_loss,
            )
        )
    return sorted(aggregated, key=lambda row: (row.average_return_pct, row.trade_count), reverse=True)


def format_scalp_replay_table(results: list[ScalpReplayResult], *, limit: int = 30) -> str:
    headers = ["symbol", "date", "strategy", "h", "trades", "avg_%", "win_%", "pf", "sum_%"]
    rows = [
        [
            row.symbol,
            row.date,
            row.strategy_name,
            str(row.horizon),
            str(row.trade_count),
            f"{row.average_return_pct:.4f}",
            f"{row.win_rate_pct:.2f}",
            _format_float(row.profit_factor),
            f"{row.total_return_pct_sum:.2f}",
        ]
        for row in results[:limit]
    ]
    return _format_table(headers, rows)


def _row_to_tick(row: dict[str, str]) -> ScalpTick | None:
    try:
        price = float(row["last_price"])
        best_bid = float(row["best_bid"])
        best_ask = float(row["best_ask"])
        if price <= 0 or best_bid <= 0 or best_ask <= 0:
            return None
        spread_pct = abs(best_ask - best_bid) / price * 100
        return ScalpTick(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            price=price,
            volume=float(row.get("recent_trade_volume") or 0),
            best_bid=best_bid,
            best_ask=best_ask,
            bid_volume=float(row.get("bid_volume_5") or 0),
            ask_volume=float(row.get("ask_volume_5") or 0),
            imbalance=float(row.get("bid_ask_imbalance") or 0),
            spread_pct=spread_pct,
        )
    except (KeyError, ValueError):
        return None


def _replay_returns(ticks: list[ScalpTick], spec: ScalpStrategySpec, horizon: int) -> list[float]:
    returns: list[float] = []
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    for index, tick in enumerate(ticks[:-horizon]):
        if not spec.predicate(tick):
            continue
        exit_price = ticks[index + horizon].price
        if spec.direction == "long":
            gross = (exit_price / tick.price - 1) * 100
        elif spec.direction == "short":
            gross = (tick.price / exit_price - 1) * 100
        else:
            raise ValueError(f"unknown direction: {spec.direction}")
        returns.append(gross - tick.spread_pct)
    return returns


def _profit_factor(returns: list[float]) -> float:
    gains = sum(value for value in returns if value > 0)
    losses = -sum(value for value in returns if value < 0)
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def _parse_scalp_filename(path: Path) -> tuple[str, str] | None:
    match = re.fullmatch(r"(.+?)_(\d{4}-\d{2}-\d{2})_paper_scalp\.csv", path.name)
    if not match:
        return None
    return match.group(1), match.group(2)


def _format_float(value: float) -> str:
    if value == math.inf:
        return "inf"
    return f"{value:.2f}"


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "no results"
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows)
    return "\n".join(lines)
