from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


FIELDNAMES = [
    "check",
    "artifact_path",
    "status",
    "observed_status",
    "reasons",
    "paper_only",
    "dry_run",
    "execution_allowed",
    "production_effect",
]
PAPER_FLAGS = {
    "paper_only": "True",
    "dry_run": "True",
    "execution_allowed": "False",
    "production_effect": "none",
}


@dataclass(frozen=True)
class SchedulerMonitoringInputs:
    audit_log: Path | str
    external_data_readiness: Path | str
    portfolio_risk_gate: Path | str
    factor_risk: Path | str
    tca_report: Path | str
    operation_health: Path | str


def build_scheduler_monitoring_rows(inputs: SchedulerMonitoringInputs) -> list[dict[str, str]]:
    return [
        _audit_row(Path(inputs.audit_log)),
        _csv_status_row("external_data_readiness", Path(inputs.external_data_readiness), "status"),
        _csv_status_row("portfolio_risk_gate", Path(inputs.portfolio_risk_gate), "status"),
        _csv_status_row("factor_risk", Path(inputs.factor_risk), "status"),
        _csv_status_row("tca_report", Path(inputs.tca_report), "tca_status"),
        _csv_status_row("operation_health", Path(inputs.operation_health), "status"),
    ]


def save_scheduler_monitoring_reports(
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
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(rows), encoding="utf-8")


def _audit_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return _row("audit_log", path, "BLOCK", "missing", "missing_file")
    audit = json.loads(path.read_text(encoding="utf-8"))
    observed = (
        f"engine_status={audit.get('engine_status', '')}; "
        f"objective_status={audit.get('objective_status', '')}; "
        f"paper_only={audit.get('paper_only', '')}; "
        f"dry_run={audit.get('dry_run', '')}; "
        f"execution_allowed={audit.get('execution_allowed', '')}; "
        f"production_effect={audit.get('production_effect', '')}"
    )
    reasons: list[str] = []
    if audit.get("engine_status") != "SUCCESS":
        reasons.append("engine_not_success")
    if audit.get("objective_status") != "COMPLETE":
        reasons.append("objective_not_complete")
    if audit.get("paper_only") is not True:
        reasons.append("paper_only_not_true")
    if audit.get("dry_run") is not True:
        reasons.append("dry_run_not_true")
    if audit.get("execution_allowed") is not False:
        reasons.append("execution_allowed_not_false")
    if audit.get("production_effect") != "none":
        reasons.append("production_effect_not_none")
    return _row("audit_log", path, "PASS" if not reasons else "BLOCK", observed, ",".join(reasons) or "none")


def _csv_status_row(
    check: str,
    path: Path,
    status_field: str,
    *,
    require_row_safety: bool = True,
) -> dict[str, str]:
    if not path.exists():
        return _row(check, path, "BLOCK", "missing", "missing_file")
    rows = _read_csv(path)
    if not rows:
        return _row(check, path, "BLOCK", "empty", "empty_file")
    statuses = [str(row.get(status_field, "")).strip().upper() for row in rows]
    observed = ",".join(f"{status}={statuses.count(status)}" for status in sorted(set(statuses)))
    reasons: list[str] = []
    if any(status != "PASS" for status in statuses):
        reasons.append("non_pass_status")
    if require_row_safety and _has_unsafe_row(rows):
        reasons.append("unsafe_flags")
    return _row(check, path, "PASS" if not reasons else "BLOCK", observed, ",".join(reasons) or "none")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return [dict(row) for row in reader]


def _has_unsafe_row(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        for key, expected in PAPER_FLAGS.items():
            if key in row and str(row.get(key, "")).strip() != expected:
                return True
    return False


def _row(check: str, path: Path, status: str, observed_status: str, reasons: str) -> dict[str, str]:
    return {
        "check": check,
        "artifact_path": str(path),
        "status": status,
        "observed_status": observed_status,
        "reasons": reasons,
        **PAPER_FLAGS,
    }


def _markdown(rows: list[dict[str, str]]) -> str:
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK"
    lines = [
        "# Scheduler Monitoring",
        "",
        "paper-only / dry-run / execution_allowed=False / production_effect=none",
        "",
        f"- overall_status: `{overall}`",
        "",
        "| check | status | observed_status | reasons |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['observed_status']} | {row['reasons']} |")
    lines.append("")
    return "\n".join(lines)
