from __future__ import annotations

import csv
import json
from pathlib import Path


ALLOWED_KIS_EXCHANGES = {"NAS", "NYS", "AMS"}
OUTPUT_FIELDNAMES = [
    "symbol",
    "exchange",
    "target_weight",
    "source_model",
    "benchmark_report_sha256",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]


def export_kis_targets_from_auto_paper(
    *,
    auto_order_plan_path: Path | str,
    universe_path: Path | str,
    audit_log_path: Path | str,
    output_path: Path | str,
) -> list[dict[str, str]]:
    audit = _load_audit(Path(audit_log_path))
    if audit.get("objective_status") != "COMPLETE":
        raise ValueError(f"auto paper objective_status is not COMPLETE: {audit.get('objective_status', '')}")
    if audit.get("execution_allowed") is not False:
        raise ValueError("auto paper audit must have execution_allowed=false")

    exchange_by_symbol = _load_exchange_map(Path(universe_path))
    rows: list[dict[str, str]] = []
    for row in _read_csv(Path(auto_order_plan_path)):
        _assert_safe_auto_row(row)
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        target_weight = float(row.get("target_weight", 0.0) or 0.0)
        if target_weight <= 0:
            continue
        exchange = exchange_by_symbol.get(symbol, "")
        if exchange not in ALLOWED_KIS_EXCHANGES:
            raise ValueError(f"missing or unsupported KIS exchange for {symbol}: {exchange}")
        rows.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "target_weight": f"{target_weight:.6f}",
                "source_model": str(audit.get("best_model", "")).strip(),
                "benchmark_report_sha256": str(audit.get("benchmark_report_sha256", "")).strip(),
                "paper_only": "True",
                "dry_run": "True",
                "execution_allowed": "False",
                "production_effect": "none",
            }
        )
    if not rows:
        raise ValueError("no positive target_weight rows exported for KIS paper plan")
    _write_csv(Path(output_path), rows)
    return rows


def _load_audit(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_exchange_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _read_csv(path):
        symbol = str(row.get("symbol", "")).strip().upper()
        exchange = str(row.get("exchange", "")).strip().upper()
        if symbol:
            mapping[symbol] = exchange
    return mapping


def _assert_safe_auto_row(row: dict[str, str]) -> None:
    expected = {
        "paper_only": "True",
        "dry_run": "True",
        "execution_allowed": "False",
        "production_effect": "none",
    }
    for key, expected_value in expected.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected_value:
            raise ValueError(f"unsafe auto order plan row for {row.get('symbol', '')}: {key}={actual}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return [dict(row) for row in reader]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
