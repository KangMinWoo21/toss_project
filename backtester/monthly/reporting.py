from typing import Any


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_semicolon_values(value: Any) -> list[str]:
    return [part.strip() for part in str(value).split(";") if part.strip()]


def count_diagnostic_rows(rows: list[dict[str, Any]], token: str) -> int:
    return sum(1 for row in rows if token in _split_semicolon_values(str(row.get("diagnostic", ""))))


def format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def format_equal_symbol_weights(symbols: list[str]) -> str:
    if not symbols:
        return ""
    weight = 1 / len(symbols)
    return ";".join(f"{symbol}:{format_optional_float(weight)}" for symbol in symbols)


def min_numeric_row(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    numeric_rows = [(value, row) for row in rows if (value := _float_or_none(row.get(column))) is not None]
    if not numeric_rows:
        return {}
    return min(numeric_rows, key=lambda item: item[0])[1]


def sum_numeric(values: Any) -> float | None:
    numeric = [value for value in (_float_or_none(value) for value in values) if value is not None]
    return sum(numeric) if numeric else None


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
