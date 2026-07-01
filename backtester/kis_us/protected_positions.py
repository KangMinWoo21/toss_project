import csv
from pathlib import Path

from .models import ProtectedPosition


def load_protected_positions(path: Path | str | None) -> dict[str, ProtectedPosition]:
    if path is None:
        return {}
    csv_path = Path(path)
    if not csv_path.exists():
        return {}
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = {"symbol", "reason"}.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        protected: dict[str, ProtectedPosition] = {}
        for row in reader:
            symbol = _normalize_symbol(row.get("symbol", ""))
            if symbol:
                protected[symbol] = ProtectedPosition(symbol=symbol, reason=str(row.get("reason", "")).strip())
        return protected


def is_protected(symbol: str, protected_positions: dict[str, ProtectedPosition]) -> bool:
    return _normalize_symbol(symbol) in protected_positions


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()
