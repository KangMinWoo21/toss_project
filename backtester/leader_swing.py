from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable

from .data import load_candles
from .events import EventScoreStore
from .models import Candle


@dataclass(frozen=True)
class LeaderSwingConfig:
    initial_cash: float = 10_000_000.0
    fee_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.0005
    liquidity_window: int = 20
    momentum_short: int = 20
    momentum_long: int = 60
    breakout_window: int = 20
    trend_window: int = 60
    exit_ma_window: int = 10
    liquidity_top_n: int = 100
    max_positions: int = 5
    max_holding_days: int = 20
    min_short_return_pct: float = 5.0
    min_long_return_pct: float = 0.0
    stop_loss_pct: float = -8.0
    market_filter_window: int = 60
    market_breadth_threshold: float = 0.0
    event_scores: EventScoreStore | None = None
    event_lookback_days: int = 0
    min_entry_event_score: float = -0.2
    force_exit_event_score: float = -0.8
    symbol_weight_multipliers: dict[str, float] | None = None
    min_relative_long_return_pct: float | None = None
    trailing_stop_pct: float | None = None
    loss_cooldown_days: int = 0


@dataclass(frozen=True)
class LeaderSwingTrade:
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float
    reason: str


@dataclass(frozen=True)
class LeaderSwingResult:
    initial_cash: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate_pct: float
    trades: list[LeaderSwingTrade]
    equity_curve: list[float]


@dataclass
class _Position:
    symbol: str
    quantity: int
    entry_price: float
    entry_date: str
    entry_index: int
    peak_price: float


@dataclass(frozen=True)
class _Candidate:
    symbol: str
    score: float
    avg_trading_value: float


def load_symbol_candles(data_dir: str | Path) -> dict[str, list[Candle]]:
    root = Path(data_dir)
    symbols: dict[str, list[Candle]] = {}
    for path in sorted(root.glob("*.csv")):
        symbol = path.stem.split("_")[0]
        if not symbol:
            continue
        symbols[symbol] = load_candles(path)
    return symbols


def run_leader_swing_backtest(
    symbol_candles: dict[str, list[Candle]],
    config: LeaderSwingConfig | None = None,
    config_resolver: Callable[
        [str, dict[str, list[Candle]], dict[str, dict[str, int]], LeaderSwingConfig],
        LeaderSwingConfig,
    ]
    | None = None,
) -> LeaderSwingResult:
    base_cfg = config or LeaderSwingConfig()
    if not symbol_candles:
        raise ValueError("symbol_candles cannot be empty")
    if base_cfg.max_positions <= 0:
        raise ValueError("max_positions must be positive")

    index_by_symbol_date = {
        symbol: {candle.date: index for index, candle in enumerate(candles)}
        for symbol, candles in symbol_candles.items()
    }
    dates = sorted({candle.date for candles in symbol_candles.values() for candle in candles})
    cash = base_cfg.initial_cash
    positions: dict[str, _Position] = {}
    cooldown_until_index: dict[str, int] = {}
    trades: list[LeaderSwingTrade] = []
    equity_curve: list[float] = []
    last_prices: dict[str, float] = {}

    for date_index, date in enumerate(dates):
        cfg = (
            config_resolver(date, symbol_candles, index_by_symbol_date, base_cfg)
            if config_resolver is not None
            else base_cfg
        )
        for symbol, candles in symbol_candles.items():
            index = index_by_symbol_date[symbol].get(date)
            if index is not None:
                last_prices[symbol] = candles[index].close

        cash, closed = _close_positions(date, symbol_candles, index_by_symbol_date, positions, cash, cfg)
        for trade in closed:
            if trade.pnl < 0 and cfg.loss_cooldown_days > 0:
                cooldown_until_index[trade.symbol] = date_index + cfg.loss_cooldown_days
        trades.extend(closed)

        equity = _equity(cash, positions, last_prices)
        candidates = (
            _rank_candidates(date, symbol_candles, index_by_symbol_date, cfg)
            if _market_breadth_allows_entry(date, symbol_candles, index_by_symbol_date, cfg)
            else []
        )
        open_slots = cfg.max_positions - len(positions)
        for candidate in candidates:
            if open_slots <= 0:
                break
            if candidate.symbol in positions:
                continue
            if cooldown_until_index.get(candidate.symbol, -1) >= date_index:
                continue
            index = index_by_symbol_date[candidate.symbol].get(date)
            if index is None:
                continue
            candle = symbol_candles[candidate.symbol][index]
            budget = min(cash, equity / cfg.max_positions * _symbol_weight_multiplier(candidate.symbol, cfg))
            fill_price = candle.close * (1 + cfg.slippage_rate)
            quantity = int(budget / (fill_price * (1 + cfg.fee_rate)))
            if quantity <= 0:
                continue
            gross = quantity * fill_price
            fee = gross * cfg.fee_rate
            cash -= gross + fee
            positions[candidate.symbol] = _Position(
                symbol=candidate.symbol,
                quantity=quantity,
                entry_price=fill_price,
                entry_date=date,
                entry_index=index,
                peak_price=fill_price,
            )
            open_slots -= 1

        equity_curve.append(_equity(cash, positions, last_prices))

    if dates:
        final_date = dates[-1]
        cfg = (
            config_resolver(final_date, symbol_candles, index_by_symbol_date, base_cfg)
            if config_resolver is not None
            else base_cfg
        )
        cash, closed = _force_close(final_date, symbol_candles, index_by_symbol_date, positions, cash, cfg)
        trades.extend(closed)
        equity_curve.append(_equity(cash, positions, last_prices))

    final_equity = equity_curve[-1] if equity_curve else base_cfg.initial_cash
    total_return_pct = (final_equity / base_cfg.initial_cash - 1) * 100
    buy_hold_return_pct = _equal_weight_buy_hold_return(symbol_candles, base_cfg)
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    win_rate_pct = len(wins) / len(trades) * 100 if trades else 0.0
    return LeaderSwingResult(
        initial_cash=base_cfg.initial_cash,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        excess_return_pct=total_return_pct - buy_hold_return_pct,
        max_drawdown_pct=_max_drawdown_pct(equity_curve) if equity_curve else 0.0,
        trade_count=len(trades),
        win_rate_pct=win_rate_pct,
        trades=trades,
        equity_curve=equity_curve,
    )


def _rank_candidates(
    date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    cfg: LeaderSwingConfig,
) -> list[_Candidate]:
    liquid_universe: list[tuple[str, float, float]] = []
    warmup = max(cfg.liquidity_window, cfg.momentum_short, cfg.momentum_long, cfg.breakout_window, cfg.trend_window)
    for symbol, candles in symbol_candles.items():
        index = index_by_symbol_date[symbol].get(date)
        if index is None or index < warmup:
            continue
        avg_trading_value = mean(c.close * c.volume for c in candles[index - cfg.liquidity_window + 1 : index + 1])
        long_return = (candles[index].close / candles[index - cfg.momentum_long].close - 1) * 100
        liquid_universe.append((symbol, avg_trading_value, long_return))

    candidates: list[_Candidate] = []
    market_long_return = mean(row[2] for row in liquid_universe) if liquid_universe else 0.0
    for symbol, avg_trading_value, long_return in sorted(liquid_universe, key=lambda row: row[1], reverse=True)[: cfg.liquidity_top_n]:
        candles = symbol_candles[symbol]
        index = index_by_symbol_date[symbol][date]
        current = candles[index]
        short_return = (current.close / candles[index - cfg.momentum_short].close - 1) * 100
        breakout_high = max(c.close for c in candles[index - cfg.breakout_window + 1 : index + 1])
        trend_ma = mean(c.close for c in candles[index - cfg.trend_window + 1 : index + 1])
        if short_return < cfg.min_short_return_pct:
            continue
        if long_return < cfg.min_long_return_pct:
            continue
        if (
            cfg.min_relative_long_return_pct is not None
            and long_return - market_long_return < cfg.min_relative_long_return_pct
        ):
            continue
        if current.close < breakout_high:
            continue
        if current.close < trend_ma:
            continue
        if cfg.event_scores is not None:
            event_score = cfg.event_scores.score_window(symbol, date, cfg.event_lookback_days)
            if event_score < cfg.min_entry_event_score:
                continue
        score = short_return * 0.6 + long_return * 0.4
        candidates.append(_Candidate(symbol=symbol, score=score, avg_trading_value=avg_trading_value))

    return sorted(candidates, key=lambda row: (row.score, row.avg_trading_value), reverse=True)


def _market_breadth_allows_entry(
    date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    cfg: LeaderSwingConfig,
) -> bool:
    if cfg.market_breadth_threshold <= 0:
        return True
    checks = []
    for symbol, candles in symbol_candles.items():
        index = index_by_symbol_date[symbol].get(date)
        if index is None or index < cfg.market_filter_window:
            continue
        moving_average = mean(c.close for c in candles[index - cfg.market_filter_window + 1 : index + 1])
        checks.append(candles[index].close > moving_average)
    if not checks:
        return False
    return sum(checks) / len(checks) >= cfg.market_breadth_threshold


def _close_positions(
    date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    positions: dict[str, _Position],
    cash: float,
    cfg: LeaderSwingConfig,
) -> tuple[float, list[LeaderSwingTrade]]:
    closed: list[LeaderSwingTrade] = []
    for symbol, position in list(positions.items()):
        index = index_by_symbol_date[symbol].get(date)
        if index is None:
            continue
        candles = symbol_candles[symbol]
        candle = candles[index]
        position.peak_price = max(position.peak_price, candle.close)
        hold_days = index - position.entry_index
        pnl_pct = (candle.close / position.entry_price - 1) * 100
        peak_drawdown_pct = (candle.close / position.peak_price - 1) * 100
        exit_ma = mean(c.close for c in candles[max(0, index - cfg.exit_ma_window + 1) : index + 1])
        reason = ""
        if cfg.event_scores is not None and cfg.event_scores.score_window(symbol, date, cfg.event_lookback_days) <= cfg.force_exit_event_score:
            reason = "event_risk"
        elif cfg.trailing_stop_pct is not None and peak_drawdown_pct <= -abs(cfg.trailing_stop_pct):
            reason = "trailing_stop"
        elif hold_days >= cfg.max_holding_days:
            reason = "max_holding_days"
        elif pnl_pct <= cfg.stop_loss_pct:
            reason = "stop_loss"
        elif index >= cfg.exit_ma_window and candle.close < exit_ma:
            reason = "exit_ma_break"
        if reason:
            cash, trade = _sell(candle.date, candle.close, position, cash, cfg, reason)
            closed.append(trade)
            del positions[symbol]
    return cash, closed


def _force_close(
    date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    positions: dict[str, _Position],
    cash: float,
    cfg: LeaderSwingConfig,
) -> tuple[float, list[LeaderSwingTrade]]:
    closed: list[LeaderSwingTrade] = []
    for symbol, position in list(positions.items()):
        index = index_by_symbol_date[symbol].get(date)
        if index is None:
            continue
        candle = symbol_candles[symbol][index]
        cash, trade = _sell(candle.date, candle.close, position, cash, cfg, "final_close")
        closed.append(trade)
        del positions[symbol]
    return cash, closed


def _sell(
    date: str,
    close: float,
    position: _Position,
    cash: float,
    cfg: LeaderSwingConfig,
    reason: str,
) -> tuple[float, LeaderSwingTrade]:
    fill_price = close * (1 - cfg.slippage_rate)
    gross = position.quantity * fill_price
    fee = gross * cfg.fee_rate
    tax = gross * cfg.tax_rate
    cash += gross - fee - tax
    pnl = (fill_price - position.entry_price) * position.quantity - fee - tax
    return_pct = (fill_price / position.entry_price - 1) * 100
    return cash, LeaderSwingTrade(
        symbol=position.symbol,
        entry_date=position.entry_date,
        exit_date=date,
        entry_price=position.entry_price,
        exit_price=fill_price,
        quantity=position.quantity,
        pnl=pnl,
        return_pct=return_pct,
        reason=reason,
    )


def _equity(cash: float, positions: dict[str, _Position], prices: dict[str, float]) -> float:
    return cash + sum(position.quantity * prices.get(symbol, position.entry_price) for symbol, position in positions.items())


def _symbol_weight_multiplier(symbol: str, cfg: LeaderSwingConfig) -> float:
    if not cfg.symbol_weight_multipliers:
        return 1.0
    return max(cfg.symbol_weight_multipliers.get(symbol, 1.0), 0.0)


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1) * 100)
    return worst


def _equal_weight_buy_hold_return(symbol_candles: dict[str, list[Candle]], cfg: LeaderSwingConfig) -> float:
    per_symbol_cash = cfg.initial_cash / len(symbol_candles)
    final_equity = 0.0
    for candles in symbol_candles.values():
        first = candles[0]
        last = candles[-1]
        fill_price = first.close * (1 + cfg.slippage_rate)
        quantity = int(per_symbol_cash / (fill_price * (1 + cfg.fee_rate)))
        leftover = per_symbol_cash - quantity * fill_price * (1 + cfg.fee_rate)
        exit_price = last.close * (1 - cfg.slippage_rate)
        gross = quantity * exit_price
        final_equity += leftover + gross - gross * cfg.fee_rate - gross * cfg.tax_rate
    return (final_equity / cfg.initial_cash - 1) * 100
