import csv
from pathlib import Path

from .models import Candle


REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def load_candles(path: Path | str) -> list[Candle]:
    csv_path = Path(path)
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        candles = [
            Candle(
                date=row["date"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(float(row["volume"])),
            )
            for row in reader
        ]
    if not candles:
        raise ValueError(f"{csv_path} has no candle rows")
    return candles
