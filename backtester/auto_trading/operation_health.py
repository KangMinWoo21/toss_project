from __future__ import annotations

import csv
import json
from pathlib import Path


FIELDNAMES = ["check", "status", "detail", "paper_only", "dry_run", "execution_allowed", "production_effect"]
SAFE_ROW_FLAGS = {
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


def build_operation_health_rows(
    *,
    audit_log_path: Path | str,
    auto_order_plan_path: Path | str,
    kis_targets_path: Path | str,
    kis_order_plan_path: Path | str,
) -> list[dict[str, str]]:
    audit = json.loads(Path(audit_log_path).read_text(encoding="utf-8"))
    rows = [
        _check(
            "objective_complete",
            audit.get("engine_status") == "SUCCESS" and audit.get("objective_status") == "COMPLETE",
            f"engine_status={audit.get('engine_status', '')}; objective_status={audit.get('objective_status', '')}",
        ),
        _check(
            "audit_safe_flags",
            audit.get("paper_only") is True
            and audit.get("dry_run") is True
            and audit.get("execution_allowed") is False
            and audit.get("production_effect") == "none",
            (
                f"paper_only={audit.get('paper_only', '')}; dry_run={audit.get('dry_run', '')}; "
                f"execution_allowed={audit.get('execution_allowed', '')}; "
                f"production_effect={audit.get('production_effect', '')}"
            ),
        ),
    ]
    rows.append(_safe_csv_check("auto_order_plan_safe", Path(auto_order_plan_path), SAFE_ROW_FLAGS))
    rows.append(_safe_csv_check("kis_targets_safe", Path(kis_targets_path), SAFE_ROW_FLAGS))
    rows.append(_kis_order_plan_check(Path(kis_order_plan_path)))
    rows.append(_kis_target_weight_check(Path(kis_targets_path)))
    return rows


def save_operation_health_reports(
    rows: list[dict[str, str]],
    csv_path: Path | str,
    markdown_path: Path | str,
) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).write_text(_health_markdown(rows), encoding="utf-8")


def _safe_csv_check(check_name: str, path: Path, expected: dict[str, str]) -> dict[str, str]:
    rows = _read_csv(path)
    if not rows:
        return _check(check_name, False, f"no rows: {path}")
    failures: list[str] = []
    for index, row in enumerate(rows, start=1):
        for key, expected_value in expected.items():
            actual = str(row.get(key, "")).strip()
            if actual != expected_value:
                failures.append(f"row={index} symbol={row.get('symbol', '')} {key}={actual}")
    detail = f"rows={len(rows)}" if not failures else "; ".join(failures[:5])
    return _check(check_name, not failures, detail)


def _kis_order_plan_check(path: Path) -> dict[str, str]:
    rows = _read_csv(path)
    if not rows:
        return _check("kis_order_plan_safe", False, f"no rows: {path}")
    failures: list[str] = []
    for index, row in enumerate(rows, start=1):
        for key, expected_value in SAFE_ROW_FLAGS.items():
            actual = str(row.get(key, "")).strip()
            if actual != expected_value:
                failures.append(f"row={index} symbol={row.get('symbol', '')} {key}={actual}")
    detail = f"rows={len(rows)}; statuses={_status_counts(rows)}" if not failures else "; ".join(failures[:5])
    return _check("kis_order_plan_safe", not failures, detail)


def _kis_target_weight_check(path: Path) -> dict[str, str]:
    rows = _read_csv(path)
    total = sum(float(row.get("target_weight", 0.0) or 0.0) for row in rows)
    return _check("kis_target_weight_total", total <= 1.0 + 1e-12, f"total_weight={total:.6f}; rows={len(rows)}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return [dict(row) for row in reader]


def _status_counts(rows: list[dict[str, str]]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("risk_status", "") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return ",".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": "PASS" if passed else "BLOCK", "detail": detail, **SAFE_ROW_FLAGS}


def _health_markdown(rows: list[dict[str, str]]) -> str:
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK"
    lines = [
        "# Auto Paper Operation Health",
        "",
        "paper-only / dry-run / execution_allowed=False",
        "",
        f"- overall_status: `{overall}`",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['detail']} |")
    lines.append("")
    return "\n".join(lines)
