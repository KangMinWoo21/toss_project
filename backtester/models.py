from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
