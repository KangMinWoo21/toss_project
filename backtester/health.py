import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    detail: str
    path: str = ""
    modified_at: str = ""
    age_hours: float | None = None
    suggested_action: str = "No action required."


@dataclass(frozen=True)
class HealthReport:
    status: str
    generated_at: str
    checks: list[HealthCheck]


DEFAULT_CSV_SCHEMAS = {
    "monthly_order_plan": {
        "path": Path("data/reports/monthly_order_plan.csv"),
        "columns": {
            "as_of_date",
            "symbol",
            "action",
            "quantity",
            "reference_price",
            "estimated_value",
            "target_weight",
            "current_quantity",
            "reason",
            "adv_20d",
            "adv_participation_rate",
            "liquidity_status",
            "liquidity_reason",
            "estimated_slippage_rate",
            "estimated_total_cost",
            "execution_allowed",
            "execution_mode",
            "execution_block_reason",
            "risk_status",
            "risk_reasons",
        },
    },
    "production_readiness": {
        "path": Path("data/reports/production_readiness.csv"),
        "columns": {"name", "status", "detail"},
    },
    "data_quality_excluded_symbols": {
        "path": Path("data/reports/data_quality_excluded_symbols.csv"),
        "columns": {"symbol", "status", "reason"},
    },
}

OPTIONAL_CSV_SCHEMAS = {
    "monthly_universe_price_coverage": {
        "path": Path("data/reports/monthly_universe_price_coverage.csv"),
        "columns": {
            "date",
            "universe_symbols",
            "price_symbols",
            "covered_symbols",
            "missing_symbols",
            "coverage_pct",
            "status",
            "missing_preview",
        },
    },
    "krx_missing_ohlcv_fetch_summary": {
        "path": Path("data/reports/krx_missing_ohlcv_fetch_summary.csv"),
        "columns": {
            "status",
            "attempted_batches",
            "completed_batches",
            "timed_out_batches",
            "failed_batches",
            "saved",
            "remaining_targets",
            "command_count",
            "last_stdout_tail",
            "last_stderr_tail",
        },
    },
}

DERIVED_REPORT_INPUTS = {
    "monthly_universe_price_coverage": {
        "path": Path("data/reports/monthly_universe_price_coverage.csv"),
        "inputs": [
            Path("data/krx_expanded"),
            Path("data/krx_metadata/krx_universe_monthly.csv"),
        ],
    },
}


def evaluate_health(
    *,
    root: Path | str = ".",
    as_of: datetime | None = None,
    max_report_age_hours: float = 1080.0,
    block_report_age_hours: float = 1440.0,
    scalper_dir: Path | str = "data/scalper",
    scalper_mode: str = "required",
    max_scalper_age_hours: float = 24.0,
    block_scalper_age_hours: float = 72.0,
    logs_dir: Path | str = "logs",
) -> HealthReport:
    root_path = Path(root)
    now = _normalize_datetime(as_of or datetime.now(timezone.utc))
    checks: list[HealthCheck] = []
    for name, spec in DEFAULT_CSV_SCHEMAS.items():
        checks.append(
            _csv_report_check(
                name,
                root_path / Path(spec["path"]),
                required_columns=set(spec["columns"]),
                as_of=now,
                max_age_hours=max_report_age_hours,
                block_age_hours=block_report_age_hours,
            )
        )
    for name, spec in OPTIONAL_CSV_SCHEMAS.items():
        optional_path = root_path / Path(spec["path"])
        if optional_path.exists():
            checks.append(
                _csv_report_check(
                    name,
                    optional_path,
                    required_columns=set(spec["columns"]),
                    as_of=now,
                    max_age_hours=max_report_age_hours,
                    block_age_hours=block_report_age_hours,
                )
            )
    for name, spec in DERIVED_REPORT_INPUTS.items():
        report_path = root_path / Path(spec["path"])
        if report_path.exists():
            checks.append(
                _derived_report_inputs_check(
                    f"{name}_inputs",
                    report_path,
                    [root_path / Path(input_path) for input_path in spec["inputs"]],
                )
            )
    checks.append(
        _scalper_directory_check(
            root_path / scalper_dir,
            as_of=now,
            mode=scalper_mode,
            max_age_hours=max_scalper_age_hours,
            block_age_hours=block_scalper_age_hours,
        )
    )
    checks.append(_log_check(root_path / logs_dir))
    return HealthReport(status=health_status(checks), generated_at=now.isoformat(), checks=checks)


def health_status(checks: list[HealthCheck]) -> str:
    if any(check.status == "BLOCK" for check in checks):
        return "BLOCK"
    if any(check.status == "WARN" for check in checks):
        return "WARN"
    return "PASS"


def save_health_json(report: HealthReport, output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": report.status,
        "generated_at": report.generated_at,
        "checks": [asdict(check) for check in report.checks],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_health_markdown(report: HealthReport, output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Health Status",
        "",
        f"Overall status: {report.status}",
        f"Generated at: {report.generated_at}",
        "",
        "| Check | Status | Detail | Modified At | Age Hours | Suggested Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for check in report.checks:
        age = "" if check.age_hours is None else f"{check.age_hours:.2f}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_markdown(check.name),
                    check.status,
                    _escape_markdown(check.detail),
                    _escape_markdown(check.modified_at),
                    age,
                    _escape_markdown(check.suggested_action),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _csv_report_check(
    name: str,
    path: Path,
    *,
    required_columns: set[str],
    as_of: datetime,
    max_age_hours: float,
    block_age_hours: float,
) -> HealthCheck:
    if not path.exists():
        return HealthCheck(
            name,
            "BLOCK",
            f"missing required report: {path}",
            path=str(path),
            suggested_action=f"Regenerate {path.name} before relying on operational readiness.",
        )
    schema_status, schema_detail = _csv_schema_status(path, required_columns)
    modified = _modified_at(path)
    age_hours = _age_hours(modified, as_of)
    if schema_status == "BLOCK":
        return HealthCheck(
            name,
            "BLOCK",
            schema_detail,
            path=str(path),
            modified_at=modified.isoformat(),
            age_hours=age_hours,
            suggested_action=(
                f"Regenerate {path.name} with the current CLI so required columns match the code schema."
            ),
        )
    stale_status = _stale_status(age_hours, max_age_hours=max_age_hours, block_age_hours=block_age_hours)
    if stale_status == "BLOCK":
        status = "BLOCK"
        detail = f"stale report: age_hours={age_hours:.2f} > block={block_age_hours:.2f}; {schema_detail}"
    elif stale_status == "WARN":
        status = "WARN"
        detail = f"stale report: age_hours={age_hours:.2f} > warn={max_age_hours:.2f}; {schema_detail}"
    else:
        status = "PASS"
        detail = f"fresh report; {schema_detail}"
    suggested_action = (
        f"Regenerate {path.name}; current age is {age_hours:.2f} hours."
        if status in {"WARN", "BLOCK"}
        else "No action required."
    )
    return HealthCheck(
        name,
        status,
        detail,
        path=str(path),
        modified_at=modified.isoformat(),
        age_hours=age_hours,
        suggested_action=suggested_action,
    )


def _csv_schema_status(path: Path, required_columns: set[str]) -> tuple[str, str]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return "BLOCK", f"schema_drift: unreadable CSV: {exc}"
    missing = sorted(required_columns - columns)
    if missing:
        return "BLOCK", f"schema_drift: missing_columns={','.join(missing)}"
    return "PASS", f"schema_ok columns={len(columns)}"


def _derived_report_inputs_check(name: str, report_path: Path, input_paths: list[Path]) -> HealthCheck:
    report_modified = _modified_at(report_path)
    missing_inputs = [str(path) for path in input_paths if not path.exists()]
    if missing_inputs:
        return HealthCheck(
            name,
            "WARN",
            f"missing derived report inputs: {', '.join(missing_inputs)}",
            path=str(report_path),
            modified_at=report_modified.isoformat(),
            suggested_action=f"Verify inputs, then regenerate {report_path.name}.",
        )

    newest_input_path = ""
    newest_input_modified: datetime | None = None
    for input_path in input_paths:
        candidate_path, candidate_modified = _latest_modified_input(input_path)
        if candidate_modified is None:
            continue
        if newest_input_modified is None or candidate_modified > newest_input_modified:
            newest_input_path = str(candidate_path)
            newest_input_modified = candidate_modified

    if newest_input_modified is None:
        return HealthCheck(
            name,
            "WARN",
            "derived report inputs exist but contain no readable files",
            path=str(report_path),
            modified_at=report_modified.isoformat(),
            suggested_action=f"Verify inputs, then regenerate {report_path.name}.",
        )

    if newest_input_modified > report_modified:
        return HealthCheck(
            name,
            "WARN",
            (
                "input_newer_than_report: "
                f"newest_input={newest_input_path}; "
                f"input_modified_at={newest_input_modified.isoformat()}"
            ),
            path=str(report_path),
            modified_at=report_modified.isoformat(),
            suggested_action=f"Regenerate {report_path.name} after the latest input data update.",
        )

    return HealthCheck(
        name,
        "PASS",
        "derived report inputs are not newer than report",
        path=str(report_path),
        modified_at=report_modified.isoformat(),
        suggested_action="No action required.",
    )


def _latest_modified_input(path: Path) -> tuple[Path, datetime | None]:
    if path.is_file():
        return path, _modified_at(path)
    newest_path = path
    newest_modified: datetime | None = None
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        child_modified = _modified_at(child)
        if newest_modified is None or child_modified > newest_modified:
            newest_path = child
            newest_modified = child_modified
    return newest_path, newest_modified


def _scalper_directory_check(
    path: Path,
    *,
    as_of: datetime,
    mode: str,
    max_age_hours: float,
    block_age_hours: float,
) -> HealthCheck:
    normalized_mode = str(mode).strip().lower() or "required"
    if normalized_mode == "off":
        return HealthCheck(
            "scalper_data",
            "PASS",
            "scalper monitoring disabled; mode=off",
            path=str(path),
            suggested_action="No action required.",
        )
    if normalized_mode not in {"required", "warn"}:
        return HealthCheck(
            "scalper_data",
            "BLOCK",
            f"invalid scalper monitoring mode: {mode}",
            path=str(path),
            suggested_action="Use scalper_mode required, warn, or off.",
        )
    if not path.exists():
        status = "WARN" if normalized_mode == "warn" else "WARN"
        return HealthCheck(
            "scalper_data",
            status,
            f"missing scalper directory: {path}; mode={normalized_mode}",
            path=str(path),
            suggested_action="Create the scalper data directory or disable scalper freshness monitoring if unused.",
        )
    files = [item for item in path.glob("*.csv") if item.is_file()]
    if not files:
        status = "WARN" if normalized_mode == "warn" else "WARN"
        return HealthCheck(
            "scalper_data",
            status,
            f"no scalper CSV files in {path}; mode={normalized_mode}",
            path=str(path),
            suggested_action="Start the paper scalper collector or disable scalper freshness monitoring if unused.",
        )
    latest = max(files, key=lambda item: item.stat().st_mtime)
    modified = _modified_at(latest)
    age_hours = _age_hours(modified, as_of)
    stale_status = _stale_status(age_hours, max_age_hours=max_age_hours, block_age_hours=block_age_hours)
    if normalized_mode == "warn" and stale_status == "BLOCK":
        stale_status = "WARN"
    if stale_status == "BLOCK":
        detail = f"stale scalper data: latest={latest.name}; age_hours={age_hours:.2f}; mode={normalized_mode}"
    elif stale_status == "WARN":
        detail = f"old scalper data: latest={latest.name}; age_hours={age_hours:.2f}; mode={normalized_mode}"
    else:
        detail = f"latest scalper data: {latest.name}; mode={normalized_mode}"
    suggested_action = (
        "Restart or inspect the cloud scalper collector; latest file is stale."
        if stale_status in {"WARN", "BLOCK"}
        else "No action required."
    )
    return HealthCheck(
        "scalper_data",
        stale_status,
        detail,
        path=str(latest),
        modified_at=modified.isoformat(),
        age_hours=age_hours,
        suggested_action=suggested_action,
    )


def _log_check(path: Path) -> HealthCheck:
    if not path.exists():
        return HealthCheck("logs", "PASS", f"no logs directory: {path}", path=str(path))
    files = [item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in {".log", ".txt"}]
    if not files:
        return HealthCheck("logs", "PASS", f"no log files in {path}", path=str(path))
    latest = max(files, key=lambda item: item.stat().st_mtime)
    text = latest.read_text(encoding="utf-8", errors="replace")
    error_count = sum(1 for line in text.splitlines() if "ERROR" in line.upper())
    warning_count = sum(
        1
        for line in text.splitlines()
        if "WARNING" in line.upper() or "WARN" in line.upper()
    )
    if error_count:
        status = "BLOCK"
    elif warning_count:
        status = "WARN"
    else:
        status = "PASS"
    modified = _modified_at(latest)
    if error_count:
        suggested_action = f"Inspect {latest.name}; ERROR lines indicate failed operational jobs."
    elif warning_count:
        suggested_action = f"Review {latest.name}; WARNING lines may indicate degraded operation."
    else:
        suggested_action = "No action required."
    return HealthCheck(
        "logs",
        status,
        f"latest={latest.name}; errors={error_count}; warnings={warning_count}",
        path=str(latest),
        modified_at=modified.isoformat(),
        suggested_action=suggested_action,
    )


def _stale_status(age_hours: float, *, max_age_hours: float, block_age_hours: float) -> str:
    if age_hours > block_age_hours:
        return "BLOCK"
    if age_hours > max_age_hours:
        return "WARN"
    return "PASS"


def _modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _age_hours(modified: datetime, as_of: datetime) -> float:
    return max((as_of - modified).total_seconds() / 3600.0, 0.0)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _escape_markdown(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
