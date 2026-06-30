from typing import Any


def format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def format_equal_symbol_weights(symbols: list[str]) -> str:
    if not symbols:
        return ""
    weight = 1 / len(symbols)
    return ";".join(f"{symbol}:{format_optional_float(weight)}" for symbol in symbols)


def unique_join(values: Any) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return "; ".join(ordered)
