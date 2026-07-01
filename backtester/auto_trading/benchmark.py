from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .gates import PerformanceMetrics, max_drawdown_abs_pct


BENCHMARK_CANDIDATE_ID = "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244"


@dataclass(frozen=True)
class BenchmarkMetrics:
    candidate_id: str
    row_selector: str
    report_sha256: str
    performance: PerformanceMetrics


def load_benchmark_metrics(path: Path | str, *, row_selector: str) -> BenchmarkMetrics:
    csv_path = Path(path)
    payload = csv_path.read_bytes()
    rows = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
    by_name = {str(row.get("name", "")).strip(): row for row in rows}
    required = by_name.get("required_excess")
    drawdown = by_name.get("drawdown_buffer")
    concentration = by_name.get("return_concentration")
    if required is None or drawdown is None or concentration is None:
        raise ValueError(f"{csv_path} missing required benchmark audit rows")
    performance = PerformanceMetrics(
        net_total_return_pct=_extract_float(concentration["detail"], "full_excess_pct"),
        net_cagr_pct=_extract_float(required["detail"], "min_required_excess_pct"),
        max_drawdown_abs_pct=max_drawdown_abs_pct(_extract_float(drawdown["detail"], "worst_max_drawdown_pct")),
        risk_adjusted_return=_extract_float(concentration["detail"], "median_walk_forward_excess_pct"),
    )
    return BenchmarkMetrics(
        candidate_id=BENCHMARK_CANDIDATE_ID,
        row_selector=row_selector,
        report_sha256=hashlib.sha256(payload).hexdigest(),
        performance=performance,
    )


def _extract_float(text: str, key: str) -> float:
    match = re.search(rf"{re.escape(key)}=(-?\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"missing {key} in {text!r}")
    return float(match.group(1))
