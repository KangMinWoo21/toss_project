import os
from pathlib import Path


TRUTHY_VALUES = {"1", "true", "yes", "y", "on"}


def load_env_file(path: Path | str = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _unquote(value.strip())
    return values


def load_env_into_process(path: Path | str = ".env") -> None:
    for key, value in load_env_file(path).items():
        os.environ.setdefault(key, value)


def is_production_trading_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("PRODUCTION_TRADING_ENABLED", "")).strip().casefold() in TRUTHY_VALUES


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
