import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


READINESS_COLUMNS = ["name", "status", "detail"]


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ReadinessAction:
    priority: str
    action: str
    detail: str


def evaluate_readiness(
    *,
    required_artifacts: list[Path | str] | None = None,
    deployment_gate_path: Path | str | None = None,
    validation_scenarios_path: Path | str | None = None,
    risk_report_path: Path | str | None = None,
    coverage_report_path: Path | str | None = None,
    performance_report_path: Path | str | None = None,
) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    checks.extend(_artifact_checks(required_artifacts or []))
    if deployment_gate_path is not None:
        checks.append(_deployment_gate_check(Path(deployment_gate_path)))
    if validation_scenarios_path is not None:
        checks.append(_validation_scenario_check(Path(validation_scenarios_path)))
    if risk_report_path is not None:
        checks.append(_risk_report_check(Path(risk_report_path)))
    if coverage_report_path is not None:
        checks.append(_coverage_report_check(Path(coverage_report_path)))
    if performance_report_path is not None:
        checks.append(_performance_report_check(Path(performance_report_path)))
    if not checks:
        checks.append(ReadinessCheck("overall", "PASS", "no readiness inputs requested"))
    return checks


def readiness_status(checks: list[ReadinessCheck]) -> str:
    statuses = {check.status for check in checks}
    if "BLOCK" in statuses:
        return "BLOCK"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def readiness_exit_code(status: str, *, strict: bool = False) -> int:
    normalized = str(status).strip().upper()
    if normalized == "BLOCK":
        return 2
    if strict and normalized == "WARN":
        return 2
    return 0


def recommend_readiness_actions(checks: list[ReadinessCheck]) -> list[ReadinessAction]:
    actions: list[ReadinessAction] = []
    details = "\n".join(check.detail for check in checks)

    if any(check.name.startswith("artifact:") and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Regenerate missing readiness artifacts",
                "Live execution must not start until all required data, validation, and risk files exist.",
            )
        )

    if any(check.name == "deployment_gate" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Keep live executor disabled",
                "The monthly deployment gate is not deployable; paper review and data collection only.",
            )
        )

    if "universe_bias_warning" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce data bias",
                "Add stronger point-in-time and delisted-symbol coverage before accepting the excess return.",
            )
        )

    if "extreme_return_share" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce extreme-winner dependence",
                "Keep winner-exclusion stress tests required and add broader historical constituents before trusting high-return windows.",
            )
        )

    if any(check.name == "universe_price_coverage" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Expand KRX price coverage",
                "Fetch historical OHLCV for the missing point-in-time universe members before considering live deployment.",
            )
        )

    if "max_drawdown_breach" in details:
        actions.append(
            ReadinessAction(
                "P1",
                "Reduce stress drawdown",
                "Tune exposure caps, stop rules, or risk-off overlays until required stress scenarios pass.",
            )
        )

    if any(check.name == "risk_report" and check.status == "BLOCK" for check in checks):
        actions.append(
            ReadinessAction(
                "P0",
                "Keep risk report as an order hard stop",
                "A blocked risk report should prevent order generation even if signals look attractive.",
            )
        )

    if any(check.name == "performance_report" and check.status in {"BLOCK", "WARN"} for check in checks):
        actions.append(
            ReadinessAction(
                "P1",
                "Treat performance fragility as a live-size limiter",
                "Thin walk-forward margins, high drawdown pressure, or full-period concentration should keep trading in paper/live dry-run or very small sizing until they improve.",
            )
        )

    if not actions and readiness_status(checks) == "PASS":
        actions.append(
            ReadinessAction(
                "P2",
                "Continue paper/live dry-run",
                "Passing readiness checks confirms controls, not expected profit; keep monitoring drift and slippage.",
            )
        )
    return actions


def save_readiness_report(checks: list[ReadinessCheck], output_path: Path | str) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [ReadinessCheck("overall", readiness_status(checks), f"{len(checks)} checks")] + checks
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in READINESS_COLUMNS})
    return len(rows)


def save_readiness_markdown(
    checks: list[ReadinessCheck],
    output_path: Path | str,
    *,
    title: str = "Production Readiness Report",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    status = readiness_status(checks)
    lines = [
        f"# {title}",
        "",
        f"Overall status: {status}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {_escape_markdown_cell(check.detail)} |")
    actions = recommend_readiness_actions(checks)
    if actions:
        lines.extend(
            [
                "",
                "## Required Next Actions",
                "",
                "| Priority | Action | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for action in actions:
            lines.append(
                f"| {action.priority} | {action.action} | {_escape_markdown_cell(action.detail)} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _artifact_checks(paths: list[Path | str]) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    for raw_path in paths:
        path = Path(raw_path)
        name = f"artifact:{path.name}"
        if not path.exists():
            checks.append(ReadinessCheck(name, "BLOCK", f"missing: {path}"))
        elif path.is_file() and path.stat().st_size <= 0:
            checks.append(ReadinessCheck(name, "BLOCK", f"empty: {path}"))
        else:
            checks.append(ReadinessCheck(name, "PASS", f"present: {path}"))
    return checks


def _deployment_gate_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("deployment_gate", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("deployment_gate", "BLOCK", f"empty: {path}")
    row = rows[-1]
    deployable = _parse_bool(row.get("deployable", ""))
    reason = str(row.get("reason", "")).strip() or "no reason"
    source = str(row.get("source", "")).strip() or str(path)
    if deployable:
        return ReadinessCheck("deployment_gate", "PASS", f"{source}:passed")
    return ReadinessCheck("deployment_gate", "BLOCK", f"{source}:{reason}")


def _validation_scenario_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("validation_scenarios", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    failed_rows = [
        row
        for row in rows
        if _parse_bool(row.get("required", "False")) and not _parse_bool(row.get("deployable", "False"))
    ]
    failed = [str(row.get("name", "unknown")) for row in failed_rows]
    if failed:
        preview = ",".join(failed[:10])
        suffix = f" (+{len(failed) - 10} more)" if len(failed) > 10 else ""
        reasons = Counter(str(row.get("reason", "unknown")).strip() or "unknown" for row in failed_rows)
        reason_summary = ", ".join(f"{reason}={count}" for reason, count in sorted(reasons.items()))
        bias_reasons = Counter()
        for row in failed_rows:
            if str(row.get("reason", "")).strip() != "universe_bias_warning":
                continue
            for reason in _split_bias_reasons(str(row.get("universe_bias_reasons", ""))):
                bias_reasons[reason] += 1
        bias_summary = ""
        if bias_reasons:
            bias_summary = "; bias: " + ", ".join(
                f"{reason}={count}" for reason, count in sorted(bias_reasons.items())
            )
        return ReadinessCheck(
            "validation_scenarios",
            "BLOCK",
            f"{len(failed)} failed: {preview}{suffix}; reasons: {reason_summary}{bias_summary}",
        )
    return ReadinessCheck("validation_scenarios", "PASS", f"{len(rows)} scenarios passed")


def _risk_report_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("risk_report", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    blocked = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "BLOCK"
    ]
    if blocked:
        return ReadinessCheck("risk_report", "BLOCK", "; ".join(blocked[:5]))
    warned = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "WARN"
    ]
    if warned:
        return ReadinessCheck("risk_report", "WARN", "; ".join(warned[:5]))
    return ReadinessCheck("risk_report", "PASS", f"{len(rows)} risk checks passed")


def _performance_report_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("performance_report", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("performance_report", "BLOCK", f"empty: {path}")
    blocked = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "BLOCK"
    ]
    if blocked:
        return ReadinessCheck("performance_report", "BLOCK", "; ".join(blocked[:5]))
    warned = [
        f"{row.get('name', 'unknown')}:{row.get('detail', '')}"
        for row in rows
        if str(row.get("status", "")).upper() == "WARN"
    ]
    if warned:
        return ReadinessCheck("performance_report", "WARN", "; ".join(warned[:5]))
    return ReadinessCheck("performance_report", "PASS", f"{len(rows)} performance checks passed")


def _coverage_report_check(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("universe_price_coverage", "BLOCK", f"missing: {path}")
    rows = _read_csv_rows(path)
    if not rows:
        return ReadinessCheck("universe_price_coverage", "BLOCK", f"empty: {path}")
    blocked = [row for row in rows if str(row.get("status", "")).upper() == "BLOCK"]
    coverage_values = [
        float(row.get("coverage_pct", 0) or 0)
        for row in rows
        if str(row.get("coverage_pct", "")).strip() != ""
    ]
    min_coverage = min(coverage_values) if coverage_values else 0.0
    if blocked:
        worst = min(blocked, key=lambda row: float(row.get("coverage_pct", 0) or 0))
        covered = _parse_int(worst.get("covered_symbols", 0))
        universe = _parse_int(worst.get("universe_symbols", 0))
        target_80 = math.ceil(universe * 0.8) if universe > 0 else 0
        need_to_80 = max(0, target_80 - covered)
        batches_of_50 = math.ceil(need_to_80 / 50) if need_to_80 > 0 else 0
        return ReadinessCheck(
            "universe_price_coverage",
            "BLOCK",
            (
                f"{len(blocked)} blocked snapshots; min_coverage_pct={min_coverage:.1f}; "
                f"worst_date={worst.get('date', 'unknown')}; missing={worst.get('missing_symbols', '')}; "
                f"need_to_80pct={need_to_80}; batches_of_50={batches_of_50}"
            ),
        )
    return ReadinessCheck(
        "universe_price_coverage",
        "PASS",
        f"{len(rows)} snapshots covered; min_coverage_pct={min_coverage:.1f}",
    )


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _parse_bool(value: Any) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "pass", "passed"}


def _parse_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _split_bias_reasons(value: str) -> list[str]:
    return [part.strip() for part in str(value).replace("|", ";").split(";") if part.strip()]


def _escape_markdown_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
