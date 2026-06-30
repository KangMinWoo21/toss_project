from __future__ import annotations

from collections.abc import Iterable

FORMULA_PREFIXES = ("=", "+", "-", "@")
FORMULA_PREFIX_WHITESPACE = " \t\r\n"


def neutralize_csv_formula_fields(
    rows: Iterable[dict[str, str]],
    fieldnames: set[str],
) -> list[dict[str, str]]:
    neutralized: list[dict[str, str]] = []
    for row in rows:
        next_row = dict(row)
        for fieldname in fieldnames:
            value = next_row.get(fieldname)
            if isinstance(value, str) and value.lstrip(FORMULA_PREFIX_WHITESPACE).startswith(FORMULA_PREFIXES):
                next_row[fieldname] = f"'{value}"
        neutralized.append(next_row)
    return neutralized
