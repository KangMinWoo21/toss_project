from typing import Any


def arg_or_default(value: Any, default: Any) -> Any:
    return default if value is None else value


def normalize_symbol(value: str | None) -> str:
    text = str(value or "").strip().strip("'").strip('"')
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(6)
    return text.upper()


def parse_source_weights(value: str | None) -> dict[str, float] | None:
    if not value:
        return None
    weights: dict[str, float] = {}
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"invalid source weight '{item}', expected source=weight")
        source, weight = item.split("=", 1)
        source = source.strip()
        if not source:
            raise SystemExit(f"invalid source weight '{item}', source is empty")
        weights[source] = float(weight)
    return weights or None


def parse_windows(values: list[str]) -> list[tuple[str, str, str, str]]:
    windows: list[tuple[str, str, str, str]] = []
    for value in values:
        parts = value.split(":")
        if len(parts) != 4:
            raise SystemExit(f"invalid --window: {value}")
        windows.append((parts[0], parts[1], parts[2], parts[3]))
    return windows
