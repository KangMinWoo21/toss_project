from dataclasses import dataclass
from statistics import mean, pstdev

from .events import EventScoreStore
from .flow import FlowScoreStore
from .models import Candle
from .regime import classify_regime


Signal = str


class Strategy:
    name = "base"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        raise NotImplementedError


class BuyAndHoldStrategy(Strategy):
    name = "buy_and_hold"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index == 0 and position is None:
            return "BUY"
        if index == len(candles) - 1 and position is not None:
            return "SELL"
        return "HOLD"


@dataclass
class MovingAverageCrossStrategy(Strategy):
    short_window: int = 5
    long_window: int = 20
    name: str = "moving_average_cross"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be smaller than long_window")
        if index < self.long_window - 1:
            return "HOLD"

        closes = [c.close for c in candles[: index + 1]]
        short_ma = mean(closes[-self.short_window :])
        long_ma = mean(closes[-self.long_window :])

        if position is None and short_ma > long_ma:
            return "BUY"
        if position is not None and short_ma < long_ma:
            return "SELL"
        return "HOLD"


@dataclass
class VolatilityBreakoutStrategy(Strategy):
    k: float = 0.5
    name: str = "volatility_breakout"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index == 0:
            return "HOLD"
        if index == len(candles) - 1 and position is not None:
            return "SELL"

        yesterday = candles[index - 1]
        today = candles[index]
        target = today.open + (yesterday.high - yesterday.low) * self.k
        if position is None and today.high >= target and today.close > today.open:
            return "BUY"
        return "HOLD"


@dataclass
class RsiReboundStrategy(Strategy):
    window: int = 14
    buy_below: float = 35.0
    sell_above: float = 60.0
    name: str = "rsi_rebound"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < self.window:
            return "HOLD"

        rsi = _rsi([c.close for c in candles[index - self.window : index + 1]])
        if position is None and rsi <= self.buy_below:
            return "BUY"
        if position is not None and rsi >= self.sell_above:
            return "SELL"
        if index == len(candles) - 1 and position is not None:
            return "SELL"
        return "HOLD"


@dataclass
class VolumeBreakoutStrategy(Strategy):
    window: int = 5
    multiplier: float = 1.5
    name: str = "volume_breakout"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < self.window:
            return "HOLD"

        avg_volume = mean(c.volume for c in candles[index - self.window : index])
        today = candles[index]
        recent_high = max(c.high for c in candles[index - self.window : index])
        if position is None and today.volume >= avg_volume * self.multiplier and today.close > recent_high:
            return "BUY"
        if position is not None and index == len(candles) - 1:
            return "SELL"
        return "HOLD"


@dataclass
class MarketRegimeEnsembleStrategy(Strategy):
    trend_window: int = 20
    breakout_k: float = 0.5
    rsi_window: int = 14
    rsi_buy_below: float = 35.0
    rsi_sell_above: float = 60.0
    name: str = "market_regime_ensemble"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        warmup = max(self.trend_window, self.rsi_window)
        if index < warmup:
            return "HOLD"

        closes = [c.close for c in candles[: index + 1]]
        trend_ma = mean(closes[-self.trend_window :])
        today = candles[index]
        yesterday = candles[index - 1]
        rsi = _rsi(closes[-(self.rsi_window + 1) :])
        uptrend = today.close > trend_ma

        if position is None:
            breakout_target = today.open + (yesterday.high - yesterday.low) * self.breakout_k
            breakout_buy = uptrend and today.high >= breakout_target and today.close > today.open
            rebound_buy = (not uptrend) and rsi <= self.rsi_buy_below and today.close > today.open
            if breakout_buy or rebound_buy:
                return "BUY"
            return "HOLD"

        if index == len(candles) - 1:
            return "SELL"
        if uptrend and today.close < trend_ma:
            return "SELL"
        if (not uptrend) and rsi >= self.rsi_sell_above:
            return "SELL"
        return "HOLD"


@dataclass
class OpeningRangeBreakoutStrategy(Strategy):
    range_bars: int = 15
    stop_loss_pct: float = -1.0
    name: str = "opening_range_breakout"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < self.range_bars:
            return "HOLD"

        opening_range = candles[: self.range_bars]
        range_high = max(c.high for c in opening_range)
        range_low = min(c.low for c in opening_range)
        today = candles[index]

        if position is None and today.high > range_high and today.close > range_high:
            return "BUY"
        if position is not None:
            entry_price = getattr(position, "entry_price", today.close)
            if (today.close / entry_price - 1) * 100 <= self.stop_loss_pct:
                return "SELL"
            if today.close < range_low:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class VwapTrendStrategy(Strategy):
    volume_window: int = 5
    volume_multiplier: float = 1.5
    stop_loss_pct: float = -0.8
    name: str = "vwap_trend"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < 2:
            return "HOLD"

        today = candles[index]
        current_vwap = _vwap(candles[: index + 1])
        previous_vwap = _vwap(candles[:index])
        previous_close = candles[index - 1].close
        avg_volume = mean(c.volume for c in candles[max(0, index - self.volume_window) : index])
        volume_confirmed = today.volume >= avg_volume * self.volume_multiplier

        if position is None and previous_close <= previous_vwap and today.close > current_vwap and volume_confirmed:
            return "BUY"
        if position is not None:
            entry_price = getattr(position, "entry_price", today.close)
            if (today.close / entry_price - 1) * 100 <= self.stop_loss_pct:
                return "SELL"
            if today.close < current_vwap:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class MinuteScalpingStrategy(Strategy):
    volume_window: int = 10
    volume_spike_multiplier: float = 3.0
    take_profit_pct: float = 0.8
    stop_loss_pct: float = -0.6
    name: str = "minute_scalping"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < self.volume_window:
            return "HOLD"

        today = candles[index]
        previous_high = max(c.high for c in candles[index - self.volume_window : index])
        avg_volume = mean(c.volume for c in candles[index - self.volume_window : index])

        if position is None:
            volume_spike = avg_volume > 0 and today.volume >= avg_volume * self.volume_spike_multiplier
            bullish_breakout = today.close > today.open and today.close > previous_high
            if volume_spike and bullish_breakout:
                return "BUY"
            return "HOLD"

        entry_price = getattr(position, "entry_price", today.close)
        pnl_pct = (today.close / entry_price - 1) * 100
        if pnl_pct >= self.take_profit_pct or pnl_pct <= self.stop_loss_pct:
            return "SELL"
        if index == len(candles) - 1:
            return "SELL"
        return "HOLD"


@dataclass
class RegimeSwitchingStrategy(Strategy):
    name: str = "regime_switching"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        regime = classify_regime(candles, index)
        if regime == "uptrend":
            return VolatilityBreakoutStrategy().on_candle(index, candles, position)
        if regime == "v_recovery":
            return MovingAverageCrossStrategy().on_candle(index, candles, position)
        if regime == "sideways":
            return RsiReboundStrategy().on_candle(index, candles, position)
        if regime == "crash":
            return VolumeBreakoutStrategy().on_candle(index, candles, position)
        if regime == "downtrend":
            return RsiReboundStrategy(buy_below=25.0, sell_above=55.0).on_candle(index, candles, position)
        if position is not None and index == len(candles) - 1:
            return "SELL"
        return "HOLD"


@dataclass
class TimeSeriesMomentumStrategy(Strategy):
    lookback: int = 60
    min_return_pct: float = 5.0
    exit_return_pct: float = 0.0
    name: str = "time_series_momentum"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        if index < self.lookback:
            return "HOLD"

        today = candles[index]
        previous = candles[index - self.lookback]
        lookback_return_pct = (today.close / previous.close - 1) * 100

        if position is None and lookback_return_pct >= self.min_return_pct:
            return "BUY"
        if position is not None:
            if lookback_return_pct <= self.exit_return_pct:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class MacdRsiTrendStrategy(Strategy):
    fast_window: int = 12
    slow_window: int = 26
    signal_window: int = 9
    rsi_window: int = 14
    buy_rsi: float = 50.0
    sell_rsi: float = 45.0
    name: str = "macd_rsi_trend"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        warmup = self.slow_window + self.signal_window + self.rsi_window
        if index < warmup:
            return "HOLD"

        closes = [c.close for c in candles[: index + 1]]
        macd_line, signal_line = _macd(closes, self.fast_window, self.slow_window, self.signal_window)
        rsi = _rsi(closes[-(self.rsi_window + 1) :])

        if position is None and macd_line > signal_line and rsi >= self.buy_rsi:
            return "BUY"
        if position is not None:
            if macd_line < signal_line or rsi <= self.sell_rsi:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class BollingerMeanReversionStrategy(Strategy):
    window: int = 20
    stdev_multiplier: float = 2.0
    rsi_window: int = 14
    rsi_buy_below: float = 35.0
    name: str = "bollinger_mean_reversion"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        warmup = max(self.window, self.rsi_window + 1)
        if index < warmup - 1:
            return "HOLD"

        closes = [c.close for c in candles[: index + 1]]
        band_values = closes[-self.window :]
        middle = mean(band_values)
        stdev = pstdev(band_values)
        lower = middle - self.stdev_multiplier * stdev
        upper = middle + self.stdev_multiplier * stdev
        today = candles[index]
        rsi = _rsi(closes[-(self.rsi_window + 1) :])

        if position is None and today.close <= lower and rsi <= self.rsi_buy_below:
            return "BUY"
        if position is not None:
            if today.close >= middle or today.close >= upper:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class DonchianAtrBreakoutStrategy(Strategy):
    entry_window: int = 20
    exit_window: int = 10
    atr_window: int = 14
    atr_stop_multiplier: float = 2.0
    name: str = "donchian_atr_breakout"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        entry_warmup = max(self.entry_window, self.atr_window)
        if position is None and index < entry_warmup:
            return "HOLD"
        if position is not None and index < max(self.exit_window, self.atr_window):
            return "HOLD"

        today = candles[index]
        entry_high = max(c.high for c in candles[index - self.entry_window : index])
        exit_low = min(c.low for c in candles[index - self.exit_window : index])
        atr = _atr(candles[: index + 1], self.atr_window)

        if position is None and today.close > entry_high:
            return "BUY"
        if position is not None:
            entry_price = getattr(position, "entry_price", today.close)
            atr_stop = entry_price - atr * self.atr_stop_multiplier
            if today.close < exit_low or today.close <= atr_stop:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class CompositeSwingStrategy(Strategy):
    momentum_lookback: int = 60
    trend_window: int = 50
    breakout_window: int = 20
    rsi_window: int = 14
    min_votes: int = 2
    stop_loss_pct: float = -8.0
    name: str = "composite_swing"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        warmup = max(self.momentum_lookback, self.trend_window, self.breakout_window, self.rsi_window + 1)
        if index < warmup:
            return "HOLD"

        today = candles[index]
        closes = [c.close for c in candles[: index + 1]]
        momentum_positive = today.close > candles[index - self.momentum_lookback].close
        trend_positive = today.close > mean(closes[-self.trend_window :])
        breakout_positive = today.close > max(c.high for c in candles[index - self.breakout_window : index])
        macd_line, signal_line = _macd(closes, 12, 26, 9)
        macd_positive = macd_line > signal_line
        rsi = _rsi(closes[-(self.rsi_window + 1) :])
        rsi_confirmed = 45 <= rsi <= 75
        votes = sum([momentum_positive, trend_positive, breakout_positive, macd_positive, rsi_confirmed])

        if position is None and votes >= self.min_votes:
            return "BUY"
        if position is not None:
            entry_price = getattr(position, "entry_price", today.close)
            pnl_pct = (today.close / entry_price - 1) * 100
            if pnl_pct <= self.stop_loss_pct:
                return "SELL"
            if votes < self.min_votes:
                return "SELL"
            if index == len(candles) - 1:
                return "SELL"
        return "HOLD"


@dataclass
class NewsFilteredStrategy(Strategy):
    base_strategy: Strategy
    event_scores: EventScoreStore
    symbol: str
    min_buy_score: float = -0.2
    force_sell_score: float = -0.8
    event_lookback_days: int = 0
    name: str = "news_filtered"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        base_signal = self.base_strategy.on_candle(index, candles, position)
        score = self.event_scores.score_window(self.symbol, candles[index].date, self.event_lookback_days)

        if position is not None and score <= self.force_sell_score:
            return "SELL"
        if base_signal == "BUY" and score < self.min_buy_score:
            return "HOLD"
        return base_signal


@dataclass
class FlowFilteredStrategy(Strategy):
    base_strategy: Strategy
    flow_scores: FlowScoreStore
    symbol: str
    min_buy_score: float = -0.2
    force_sell_score: float = -0.8
    name: str = "flow_filtered"

    def on_candle(self, index: int, candles: list[Candle], position: object | None) -> Signal:
        base_signal = self.base_strategy.on_candle(index, candles, position)
        score = self.flow_scores.score(self.symbol, candles[index].date)

        if position is not None and score <= self.force_sell_score:
            return "SELL"
        if base_signal == "BUY" and score < self.min_buy_score:
            return "HOLD"
        return base_signal


def _rsi(closes: list[float]) -> float:
    gains = []
    losses = []
    for previous, current in zip(closes, closes[1:]):
        delta = current - previous
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))
    avg_gain = mean(gains)
    avg_loss = mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _vwap(candles: list[Candle]) -> float:
    volume_sum = sum(c.volume for c in candles)
    if volume_sum == 0:
        return candles[-1].close
    return sum(((c.high + c.low + c.close) / 3) * c.volume for c in candles) / volume_sum


def _ema(values: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    alpha = 2 / (window + 1)
    ema_values: list[float] = []
    for value in values:
        if not ema_values:
            ema_values.append(value)
        else:
            ema_values.append(value * alpha + ema_values[-1] * (1 - alpha))
    return ema_values


def _macd(closes: list[float], fast_window: int, slow_window: int, signal_window: int) -> tuple[float, float]:
    fast = _ema(closes, fast_window)
    slow = _ema(closes, slow_window)
    macd_values = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
    signal_values = _ema(macd_values, signal_window)
    return macd_values[-1], signal_values[-1]


def _atr(candles: list[Candle], window: int) -> float:
    if len(candles) < 2:
        return candles[-1].high - candles[-1].low
    true_ranges = []
    for previous, current in zip(candles, candles[1:]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    values = true_ranges[-window:] if len(true_ranges) >= window else true_ranges
    return mean(values) if values else 0.0


def get_strategy(name: str) -> Strategy:
    strategies: dict[str, Strategy] = {
        "buy_and_hold": BuyAndHoldStrategy(),
        "moving_average_cross": MovingAverageCrossStrategy(),
        "volatility_breakout": VolatilityBreakoutStrategy(),
        "rsi_rebound": RsiReboundStrategy(),
        "volume_breakout": VolumeBreakoutStrategy(),
        "market_regime_ensemble": MarketRegimeEnsembleStrategy(),
        "opening_range_breakout": OpeningRangeBreakoutStrategy(),
        "vwap_trend": VwapTrendStrategy(),
        "minute_scalping": MinuteScalpingStrategy(),
        "regime_switching": RegimeSwitchingStrategy(),
        "time_series_momentum": TimeSeriesMomentumStrategy(),
        "macd_rsi_trend": MacdRsiTrendStrategy(),
        "bollinger_mean_reversion": BollingerMeanReversionStrategy(),
        "donchian_atr_breakout": DonchianAtrBreakoutStrategy(),
        "composite_swing": CompositeSwingStrategy(),
    }
    try:
        return strategies[name]
    except KeyError as exc:
        raise ValueError(f"unknown strategy: {name}") from exc


def available_strategies() -> list[str]:
    return [
        "buy_and_hold",
        "moving_average_cross",
        "volatility_breakout",
        "rsi_rebound",
        "volume_breakout",
        "market_regime_ensemble",
        "opening_range_breakout",
        "vwap_trend",
        "minute_scalping",
        "regime_switching",
        "time_series_momentum",
        "macd_rsi_trend",
        "bollinger_mean_reversion",
        "donchian_atr_breakout",
        "composite_swing",
    ]
