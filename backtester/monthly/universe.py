from typing import Any


def exclude_invalid_price_symbols(symbol_candles: dict[str, list[Any]]) -> dict[str, list[Any]]:
    return {
        symbol: candles
        for symbol, candles in symbol_candles.items()
        if candles and not any(has_nonpositive_price(candle) for candle in candles)
    }


def has_nonpositive_price(candle: Any) -> bool:
    return candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0
