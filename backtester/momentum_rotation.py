from dataclasses import dataclass

from .models import Candle


@dataclass(frozen=True)
class MomentumRotationConfig:
    initial_cash: float = 10_000_000.0
    fee_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.0005
    lookback_days: int = 180
    rebalance_days: int = 40
    top_n: int = 5
    require_positive_momentum: bool = False
    trend_filter_days: int = 120
    market_trend_filter_days: int = 180
    market_breadth_threshold: float = 0.4
    bull_breadth_threshold: float = 0.5
    bull_top_n: int = 5
    bull_trend_filter_days: int = 60
    liquidity_window_days: int = 20
    min_average_trading_value: float = 0.0
    max_trade_participation_rate: float = 0.0
    max_lookback_return_pct: float = 0.0
    target_persistence_signals: int = 1
    recovery_ranking_short_lookback_days: int = 0
    recovery_ranking_drawdown_lookback_days: int = 0
    recovery_ranking_weight: float = 0.0


@dataclass(frozen=True)
class MomentumRotationTrade:
    date: str
    symbol: str
    action: str
    price: float
    quantity: int
    cash_after: float
    pnl: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class MomentumRotationResult:
    initial_cash: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    trades: list[MomentumRotationTrade]
    equity_curve: list[float]
    dates: list[str]


@dataclass
class _Position:
    symbol: str
    quantity: int
    entry_price: float
    entry_date: str


def momentum_rotation_config_for_preset(preset: str) -> MomentumRotationConfig:
    if preset == "balanced":
        return MomentumRotationConfig()
    if preset == "aggressive":
        return MomentumRotationConfig(
            top_n=3,
            trend_filter_days=60,
            bull_breadth_threshold=0.8,
            bull_top_n=5,
            bull_trend_filter_days=60,
        )
    if preset == "retail":
        return MomentumRotationConfig(
            top_n=3,
            trend_filter_days=60,
            bull_breadth_threshold=0.8,
            bull_top_n=5,
            bull_trend_filter_days=60,
            min_average_trading_value=300_000_000,
            max_trade_participation_rate=0.005,
        )
    raise ValueError(f"unknown momentum rotation preset: {preset}")


def run_momentum_rotation_backtest(
    symbol_candles: dict[str, list[Candle]],
    config: MomentumRotationConfig | None = None,
) -> MomentumRotationResult:
    cfg = config or MomentumRotationConfig()
    if not symbol_candles:
        raise ValueError("symbol_candles cannot be empty")
    if cfg.lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    if cfg.rebalance_days <= 0:
        raise ValueError("rebalance_days must be positive")
    if cfg.top_n <= 0:
        raise ValueError("top_n must be positive")
    if cfg.trend_filter_days < 0:
        raise ValueError("trend_filter_days cannot be negative")
    if cfg.market_trend_filter_days < 0:
        raise ValueError("market_trend_filter_days cannot be negative")
    if not 0 <= cfg.market_breadth_threshold <= 1:
        raise ValueError("market_breadth_threshold must be between 0 and 1")
    if not 0 <= cfg.bull_breadth_threshold <= 1:
        raise ValueError("bull_breadth_threshold must be between 0 and 1")
    if cfg.bull_top_n <= 0:
        raise ValueError("bull_top_n must be positive")
    if cfg.bull_trend_filter_days < 0:
        raise ValueError("bull_trend_filter_days cannot be negative")
    if cfg.liquidity_window_days <= 0:
        raise ValueError("liquidity_window_days must be positive")
    if cfg.min_average_trading_value < 0:
        raise ValueError("min_average_trading_value cannot be negative")
    if cfg.max_trade_participation_rate < 0:
        raise ValueError("max_trade_participation_rate cannot be negative")
    if cfg.max_lookback_return_pct < 0:
        raise ValueError("max_lookback_return_pct cannot be negative")
    if cfg.target_persistence_signals <= 0:
        raise ValueError("target_persistence_signals must be positive")
    if cfg.recovery_ranking_short_lookback_days < 0:
        raise ValueError("recovery_ranking_short_lookback_days cannot be negative")
    if cfg.recovery_ranking_drawdown_lookback_days < 0:
        raise ValueError("recovery_ranking_drawdown_lookback_days cannot be negative")
    if cfg.recovery_ranking_weight < 0:
        raise ValueError("recovery_ranking_weight cannot be negative")

    candles_by_symbol = {
        symbol: sorted(candles, key=lambda candle: candle.date) for symbol, candles in symbol_candles.items()
    }
    by_date = {
        symbol: {candle.date: candle for candle in candles}
        for symbol, candles in candles_by_symbol.items()
    }
    index_by_symbol_date = {
        symbol: {candle.date: index for index, candle in enumerate(candles)}
        for symbol, candles in candles_by_symbol.items()
    }
    dates = _all_dates(candles_by_symbol)
    cash = cfg.initial_cash
    positions: dict[str, _Position] = {}
    trades: list[MomentumRotationTrade] = []
    equity_curve: list[float] = []
    curve_dates: list[str] = []
    last_prices: dict[str, float] = {}
    first_rebalance_index = cfg.lookback_days + 1

    for date_index, trade_date in enumerate(dates):
        for symbol, candles in candles_by_symbol.items():
            symbol_index = index_by_symbol_date[symbol].get(trade_date)
            if symbol_index is not None:
                last_prices[symbol] = candles[symbol_index].close

        if date_index >= first_rebalance_index and (date_index - first_rebalance_index) % cfg.rebalance_days == 0:
            signal_date = dates[date_index - 1]
            market_breadth = _market_breadth_value(
                candles_by_symbol,
                index_by_symbol_date=index_by_symbol_date,
                signal_date=signal_date,
                trend_days=cfg.market_trend_filter_days,
            )
            ranking_top_n, ranking_trend_days = _ranking_profile(cfg, market_breadth)
            target_symbols = (
                _rank_momentum_symbols(
                    candles_by_symbol,
                    index_by_symbol_date=index_by_symbol_date,
                    trade_date=trade_date,
                    cfg=cfg,
                    top_n=ranking_top_n,
                    trend_filter_days=ranking_trend_days,
                )
                if _market_breadth_allows_entry(market_breadth, cfg)
                else []
            )
            target_symbols = _filter_persistent_targets(
                target_symbols,
                candles_by_symbol,
                index_by_symbol_date=index_by_symbol_date,
                dates=dates,
                signal_date=signal_date,
                cfg=cfg,
            )
            cash, sold = _sell_non_targets(trade_date, target_symbols, positions, by_date, cash, cfg)
            trades.extend(sold)
            cash, bought = _buy_missing_targets(
                trade_date,
                target_symbols,
                positions,
                by_date,
                candles_by_symbol,
                index_by_symbol_date,
                cash,
                cfg,
            )
            trades.extend(bought)

        equity_curve.append(_equity_from_prices(positions, last_prices, cash))
        curve_dates.append(trade_date)

    if dates:
        cash, sold = _force_sell_all(candles_by_symbol, positions, cash, cfg)
        trades.extend(sold)
        equity_curve.append(cash)
        curve_dates.append(dates[-1])

    final_equity = equity_curve[-1] if equity_curve else cfg.initial_cash
    total_return_pct = (final_equity / cfg.initial_cash - 1) * 100
    buy_hold_return_pct = _equal_weight_buy_hold_return(candles_by_symbol, cfg)
    return MomentumRotationResult(
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        excess_return_pct=total_return_pct - buy_hold_return_pct,
        max_drawdown_pct=_max_drawdown_pct(equity_curve) if equity_curve else 0.0,
        trade_count=len(trades),
        trades=trades,
        equity_curve=equity_curve,
        dates=curve_dates,
    )


def rank_momentum_targets(
    symbol_candles: dict[str, list[Candle]],
    *,
    signal_date: str,
    config: MomentumRotationConfig | None = None,
) -> list[str]:
    cfg = config or MomentumRotationConfig()
    candles_by_symbol = {
        symbol: sorted(candles, key=lambda candle: candle.date) for symbol, candles in symbol_candles.items()
    }
    index_by_symbol_date = {
        symbol: {candle.date: index for index, candle in enumerate(candles)}
        for symbol, candles in candles_by_symbol.items()
    }
    market_breadth = _market_breadth_value(
        candles_by_symbol,
        index_by_symbol_date=index_by_symbol_date,
        signal_date=signal_date,
        trend_days=cfg.market_trend_filter_days,
    )
    if not _market_breadth_allows_entry(market_breadth, cfg):
        return []
    ranking_top_n, ranking_trend_days = _ranking_profile(cfg, market_breadth)
    targets = _rank_momentum_symbols_on_signal_date(
        candles_by_symbol,
        index_by_symbol_date=index_by_symbol_date,
        signal_date=signal_date,
        cfg=cfg,
        top_n=ranking_top_n,
        trend_filter_days=ranking_trend_days,
    )
    return _filter_persistent_targets(
        targets,
        candles_by_symbol,
        index_by_symbol_date=index_by_symbol_date,
        dates=_all_dates(candles_by_symbol),
        signal_date=signal_date,
        cfg=cfg,
    )


def _all_dates(symbol_candles: dict[str, list[Candle]]) -> list[str]:
    dates = sorted({candle.date for candles in symbol_candles.values() for candle in candles})
    if not dates:
        raise ValueError("symbol_candles have no dates")
    return dates


def _rank_momentum_symbols(
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    trade_date: str,
    cfg: MomentumRotationConfig,
    top_n: int | None = None,
    trend_filter_days: int | None = None,
) -> list[str]:
    selected_top_n = top_n if top_n is not None else cfg.top_n
    selected_trend_filter_days = trend_filter_days if trend_filter_days is not None else cfg.trend_filter_days
    rows: list[tuple[str, float]] = []
    for symbol, candles in symbol_candles.items():
        current_index = index_by_symbol_date[symbol].get(trade_date)
        if current_index is None or current_index <= cfg.lookback_days:
            continue
        signal_index = current_index - 1
        lookback_index = signal_index - cfg.lookback_days
        if lookback_index < 0:
            continue
        signal_close = candles[signal_index].close
        base_close = candles[lookback_index].close
        momentum = signal_close / base_close - 1
        if cfg.require_positive_momentum and momentum <= 0:
            continue
        if cfg.max_lookback_return_pct > 0 and momentum * 100 > cfg.max_lookback_return_pct:
            continue
        if cfg.min_average_trading_value > 0:
            avg_trading_value = _average_trading_value(candles, signal_index, cfg.liquidity_window_days)
            if avg_trading_value is None or avg_trading_value < cfg.min_average_trading_value:
                continue
        if selected_trend_filter_days > 0:
            if signal_index + 1 < selected_trend_filter_days:
                continue
            trend_values = candles[signal_index - selected_trend_filter_days + 1 : signal_index + 1]
            trend_average = sum(candle.close for candle in trend_values) / len(trend_values)
            if signal_close < trend_average:
                continue
        ranking_score = momentum + _recovery_ranking_bonus(candles, signal_index, cfg)
        rows.append((symbol, ranking_score))
    rows.sort(key=lambda row: row[1], reverse=True)
    return [symbol for symbol, _ in rows[:selected_top_n]]


def _rank_momentum_symbols_on_signal_date(
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    signal_date: str,
    cfg: MomentumRotationConfig,
    top_n: int,
    trend_filter_days: int,
) -> list[str]:
    rows: list[tuple[str, float]] = []
    for symbol, candles in symbol_candles.items():
        signal_index = index_by_symbol_date[symbol].get(signal_date)
        if signal_index is None:
            continue
        lookback_index = signal_index - cfg.lookback_days
        if lookback_index < 0:
            continue
        signal_close = candles[signal_index].close
        base_close = candles[lookback_index].close
        momentum = signal_close / base_close - 1
        if cfg.require_positive_momentum and momentum <= 0:
            continue
        if cfg.max_lookback_return_pct > 0 and momentum * 100 > cfg.max_lookback_return_pct:
            continue
        if cfg.min_average_trading_value > 0:
            avg_trading_value = _average_trading_value(candles, signal_index, cfg.liquidity_window_days)
            if avg_trading_value is None or avg_trading_value < cfg.min_average_trading_value:
                continue
        if trend_filter_days > 0:
            if signal_index + 1 < trend_filter_days:
                continue
            trend_values = candles[signal_index - trend_filter_days + 1 : signal_index + 1]
            trend_average = sum(candle.close for candle in trend_values) / len(trend_values)
            if signal_close < trend_average:
                continue
        ranking_score = momentum + _recovery_ranking_bonus(candles, signal_index, cfg)
        rows.append((symbol, ranking_score))
    rows.sort(key=lambda row: row[1], reverse=True)
    return [symbol for symbol, _ in rows[:top_n]]


def _recovery_ranking_bonus(
    candles: list[Candle],
    signal_index: int,
    cfg: MomentumRotationConfig,
) -> float:
    if (
        cfg.recovery_ranking_weight <= 0
        or cfg.recovery_ranking_short_lookback_days <= 0
        or cfg.recovery_ranking_drawdown_lookback_days <= 0
    ):
        return 0.0
    short_days = cfg.recovery_ranking_short_lookback_days
    drawdown_days = cfg.recovery_ranking_drawdown_lookback_days
    if signal_index < short_days or signal_index + 1 < drawdown_days:
        return 0.0
    signal_close = candles[signal_index].close
    short_base = candles[signal_index - short_days].close
    if short_base <= 0:
        return 0.0
    recent_return = signal_close / short_base - 1
    drawdown_window = candles[signal_index - drawdown_days + 1 : signal_index + 1]
    trough_close = min(candle.close for candle in drawdown_window)
    if trough_close <= 0:
        return 0.0
    trough_recovery = signal_close / trough_close - 1
    if recent_return <= 0 or trough_recovery <= 0:
        return 0.0
    return cfg.recovery_ranking_weight * (recent_return + trough_recovery)


def _filter_persistent_targets(
    target_symbols: list[str],
    symbol_candles: dict[str, list[Candle]],
    *,
    index_by_symbol_date: dict[str, dict[str, int]],
    dates: list[str],
    signal_date: str,
    cfg: MomentumRotationConfig,
) -> list[str]:
    if cfg.target_persistence_signals <= 1 or not target_symbols:
        return target_symbols
    try:
        signal_index = dates.index(signal_date)
    except ValueError:
        return []
    persistent = list(target_symbols)
    for offset in range(1, cfg.target_persistence_signals):
        prior_index = signal_index - (cfg.rebalance_days * offset)
        if prior_index < 0:
            return []
        prior_signal_date = dates[prior_index]
        prior_breadth = _market_breadth_value(
            symbol_candles,
            index_by_symbol_date=index_by_symbol_date,
            signal_date=prior_signal_date,
            trend_days=cfg.market_trend_filter_days,
        )
        if not _market_breadth_allows_entry(prior_breadth, cfg):
            return []
        prior_top_n, prior_trend_days = _ranking_profile(cfg, prior_breadth)
        prior_targets = set(
            _rank_momentum_symbols_on_signal_date(
                symbol_candles,
                index_by_symbol_date=index_by_symbol_date,
                signal_date=prior_signal_date,
                cfg=cfg,
                top_n=prior_top_n,
                trend_filter_days=prior_trend_days,
            )
        )
        persistent = [symbol for symbol in persistent if symbol in prior_targets]
        if not persistent:
            return []
    return persistent


def _market_breadth_value(
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    signal_date: str,
    trend_days: int,
) -> float | None:
    if trend_days <= 0:
        return None
    checks: list[bool] = []
    for symbol, candles in symbol_candles.items():
        signal_index = index_by_symbol_date[symbol].get(signal_date)
        if signal_index is None or signal_index + 1 < trend_days:
            continue
        trend_values = candles[signal_index - trend_days + 1 : signal_index + 1]
        trend_average = sum(candle.close for candle in trend_values) / len(trend_values)
        checks.append(candles[signal_index].close >= trend_average)
    if not checks:
        return None
    return sum(checks) / len(checks)


def _market_breadth_allows_entry(market_breadth: float | None, cfg: MomentumRotationConfig) -> bool:
    if cfg.market_trend_filter_days <= 0 or cfg.market_breadth_threshold <= 0:
        return True
    if market_breadth is None:
        return False
    return market_breadth >= cfg.market_breadth_threshold


def _ranking_profile(cfg: MomentumRotationConfig, market_breadth: float | None) -> tuple[int, int]:
    if market_breadth is not None and market_breadth >= cfg.bull_breadth_threshold:
        return cfg.bull_top_n, cfg.bull_trend_filter_days
    return cfg.top_n, cfg.trend_filter_days


def _sell_non_targets(
    trade_date: str,
    target_symbols: list[str],
    positions: dict[str, _Position],
    by_date: dict[str, dict[str, Candle]],
    cash: float,
    cfg: MomentumRotationConfig,
    reason: str = "rebalance",
) -> tuple[float, list[MomentumRotationTrade]]:
    target_set = set(target_symbols)
    trades: list[MomentumRotationTrade] = []
    for symbol, position in list(positions.items()):
        if symbol in target_set:
            continue
        if trade_date not in by_date[symbol]:
            continue
        if by_date[symbol][trade_date].open <= 0:
            continue
        fill_price = by_date[symbol][trade_date].open * (1 - cfg.slippage_rate)
        gross = position.quantity * fill_price
        fee = gross * cfg.fee_rate
        tax = gross * cfg.tax_rate
        cash += gross - fee - tax
        pnl = (fill_price - position.entry_price) * position.quantity - fee - tax
        trades.append(
            MomentumRotationTrade(
                date=trade_date,
                symbol=symbol,
                action="SELL",
                price=fill_price,
                quantity=position.quantity,
                cash_after=cash,
                pnl=pnl,
                reason=reason,
            )
        )
        del positions[symbol]
    return cash, trades


def _buy_missing_targets(
    trade_date: str,
    target_symbols: list[str],
    positions: dict[str, _Position],
    by_date: dict[str, dict[str, Candle]],
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    cash: float,
    cfg: MomentumRotationConfig,
) -> tuple[float, list[MomentumRotationTrade]]:
    if not target_symbols:
        return cash, []
    target_value = _equity_at_open(trade_date, positions, by_date, cash) / len(target_symbols)
    trades: list[MomentumRotationTrade] = []
    for symbol in target_symbols:
        if symbol in positions:
            continue
        if trade_date not in by_date[symbol]:
            continue
        if by_date[symbol][trade_date].open <= 0:
            continue
        fill_price = by_date[symbol][trade_date].open * (1 + cfg.slippage_rate)
        budget = min(cash, target_value)
        budget = min(budget, _trade_participation_budget(symbol, trade_date, symbol_candles, index_by_symbol_date, cfg))
        quantity = int(budget / (fill_price * (1 + cfg.fee_rate)))
        if quantity <= 0:
            continue
        gross = quantity * fill_price
        fee = gross * cfg.fee_rate
        cash -= gross + fee
        positions[symbol] = _Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=fill_price,
            entry_date=trade_date,
        )
        trades.append(
            MomentumRotationTrade(
                date=trade_date,
                symbol=symbol,
                action="BUY",
                price=fill_price,
                quantity=quantity,
                cash_after=cash,
                reason="rebalance",
            )
        )
    return cash, trades


def _average_trading_value(candles: list[Candle], signal_index: int, window_days: int) -> float | None:
    if signal_index + 1 < window_days:
        return None
    values = [candle.close * candle.volume for candle in candles[signal_index - window_days + 1 : signal_index + 1]]
    return sum(values) / len(values)


def _trade_participation_budget(
    symbol: str,
    trade_date: str,
    symbol_candles: dict[str, list[Candle]],
    index_by_symbol_date: dict[str, dict[str, int]],
    cfg: MomentumRotationConfig,
) -> float:
    if cfg.max_trade_participation_rate <= 0:
        return float("inf")
    trade_index = index_by_symbol_date[symbol].get(trade_date)
    if trade_index is None or trade_index <= 0:
        return 0.0
    signal_index = trade_index - 1
    avg_trading_value = _average_trading_value(symbol_candles[symbol], signal_index, cfg.liquidity_window_days)
    if avg_trading_value is None:
        return 0.0
    return avg_trading_value * cfg.max_trade_participation_rate


def _equity_at_open(
    trade_date: str,
    positions: dict[str, _Position],
    by_date: dict[str, dict[str, Candle]],
    cash: float,
) -> float:
    total = cash
    for symbol, position in positions.items():
        candle = by_date[symbol].get(trade_date)
        if candle is not None and candle.open > 0:
            total += position.quantity * candle.open
        else:
            total += position.quantity * position.entry_price
    return total


def _equity_from_prices(
    positions: dict[str, _Position],
    prices: dict[str, float],
    cash: float,
) -> float:
    return cash + sum(position.quantity * prices.get(symbol, position.entry_price) for symbol, position in positions.items())


def _force_sell_all(
    symbol_candles: dict[str, list[Candle]],
    positions: dict[str, _Position],
    cash: float,
    cfg: MomentumRotationConfig,
) -> tuple[float, list[MomentumRotationTrade]]:
    trades: list[MomentumRotationTrade] = []
    for symbol, position in list(positions.items()):
        candle = symbol_candles[symbol][-1]
        fill_price = candle.close * (1 - cfg.slippage_rate)
        gross = position.quantity * fill_price
        fee = gross * cfg.fee_rate
        tax = gross * cfg.tax_rate
        cash += gross - fee - tax
        pnl = (fill_price - position.entry_price) * position.quantity - fee - tax
        trades.append(
            MomentumRotationTrade(
                date=candle.date,
                symbol=symbol,
                action="SELL",
                price=fill_price,
                quantity=position.quantity,
                cash_after=cash,
                pnl=pnl,
                reason="final_close",
            )
        )
        del positions[symbol]
    return cash, trades


def _equal_weight_buy_hold_return(
    symbol_candles: dict[str, list[Candle]],
    cfg: MomentumRotationConfig,
) -> float:
    tradeable_pairs: list[tuple[Candle, Candle]] = []
    for candles in symbol_candles.values():
        first = next((candle for candle in candles if candle.open > 0), None)
        last = next((candle for candle in reversed(candles) if candle.close > 0), None)
        if first is not None and last is not None and first.date <= last.date:
            tradeable_pairs.append((first, last))
    if not tradeable_pairs:
        return 0.0
    per_symbol_cash = cfg.initial_cash / len(tradeable_pairs)
    final_equity = 0.0
    for first, last in tradeable_pairs:
        fill_price = first.open * (1 + cfg.slippage_rate)
        quantity = int(per_symbol_cash / (fill_price * (1 + cfg.fee_rate)))
        leftover = per_symbol_cash - quantity * fill_price * (1 + cfg.fee_rate)
        exit_price = last.close * (1 - cfg.slippage_rate)
        gross = quantity * exit_price
        final_equity += leftover + gross - gross * cfg.fee_rate - gross * cfg.tax_rate
    return (final_equity / cfg.initial_cash - 1) * 100


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1) * 100)
    return worst
