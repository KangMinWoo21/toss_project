from statistics import mean, pstdev

from .models import Candle


Regime = str


def classify_regime(candles: list[Candle], index: int) -> Regime:
    if index < 60:
        return "uncertain"

    closes = [c.close for c in candles[: index + 1]]
    recent_20 = _return_pct(closes[-20], closes[-1])
    recent_40_low_return = _return_pct(max(closes[-40:]), min(closes[-40:]))
    ma20 = mean(closes[-20:])
    ma60 = mean(closes[-60:])
    close = closes[-1]
    volatility_20 = _volatility(closes[-20:])

    had_recent_crash = recent_40_low_return <= -10
    recovered_ma20 = close > ma20 and closes[-2] <= mean(closes[-21:-1])

    if recent_20 <= -10:
        return "crash"
    if close > ma60 and ma20 > ma60 and recent_20 > 3:
        return "uptrend"
    if had_recent_crash and close > ma20:
        return "v_recovery"
    if abs(recent_20) <= 3 and abs(close / ma60 - 1) <= 0.05:
        return "sideways"
    if close < ma60 and ma20 < ma60:
        return "downtrend"
    if recovered_ma20:
        return "v_recovery"
    return "uncertain"


def _return_pct(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end / start - 1) * 100


def _volatility(closes: list[float]) -> float:
    returns = [
        _return_pct(previous, current)
        for previous, current in zip(closes, closes[1:])
        if previous != 0
    ]
    if len(returns) < 2:
        return 0.0
    return pstdev(returns)
