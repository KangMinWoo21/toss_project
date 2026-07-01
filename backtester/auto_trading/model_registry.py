from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def register_model_release(
    *,
    audit_log_path: Path | str,
    model_config_path: Path | str,
    cost_policy_path: Path | str,
    risk_gate_path: Path | str,
    output_path: Path | str,
    version: str,
    rollback_reference: str = "",
    previous_registry_path: Path | str | None = None,
) -> dict[str, Any]:
    audit = json.loads(Path(audit_log_path).read_text(encoding="utf-8"))
    _assert_release_allowed(audit, Path(risk_gate_path))
    model_config = json.loads(Path(model_config_path).read_text(encoding="utf-8"))
    previous = _load_previous_registry(previous_registry_path)
    record = {
        "model_id": str(audit.get("best_model") or model_config.get("model_id") or "").strip(),
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine_status": audit.get("engine_status", ""),
        "objective_status": audit.get("objective_status", ""),
        "risk_gate_status": _risk_gate_status(Path(risk_gate_path)),
        "benchmark_report_sha256": str(audit.get("benchmark_report_sha256", "")).strip(),
        "data_snapshot_sha256": _data_snapshot_sha256(audit),
        "model_config_sha256": _sha256_path(Path(model_config_path)),
        "cost_policy_sha256": _sha256_path(Path(cost_policy_path)),
        "risk_gate_sha256": _sha256_path(Path(risk_gate_path)),
        "model_change_diff": _model_change_diff(previous, audit, version),
        "rollback_reference": rollback_reference,
        "paper_only": True,
        "dry_run": True,
        "execution_allowed": False,
        "production_effect": "none",
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def _assert_release_allowed(audit: dict[str, Any], risk_gate_path: Path) -> None:
    if audit.get("engine_status") != "SUCCESS":
        raise ValueError(f"engine_status is not SUCCESS: {audit.get('engine_status', '')}")
    if audit.get("objective_status") != "COMPLETE":
        raise ValueError(f"objective_status is not COMPLETE: {audit.get('objective_status', '')}")
    if audit.get("paper_only") is not True or audit.get("dry_run") is not True:
        raise ValueError("audit safety flags must be paper_only=true and dry_run=true")
    if audit.get("execution_allowed") is not False or audit.get("production_effect") != "none":
        raise ValueError("audit execution flags are unsafe")
    if _risk_gate_status(risk_gate_path) != "PASS":
        raise ValueError("risk gate is not PASS")


def _risk_gate_status(path: Path) -> str:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} has no risk gate rows")
    return "PASS" if all(str(row.get("status", "")).strip() == "PASS" for row in rows) else "BLOCK"


def _data_snapshot_sha256(audit: dict[str, Any]) -> str:
    paths = [
        str(audit.get("prices_dir", "")).strip(),
        str(audit.get("universe", "")).strip(),
        str(audit.get("external_data_dir", "")).strip(),
    ]
    digest = hashlib.sha256()
    for text in sorted(path for path in paths if path):
        path = Path(text)
        digest.update(text.encode("utf-8"))
        if path.exists():
            digest.update(_sha256_path(path).encode("utf-8"))
    return digest.hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.as_posix().encode("utf-8"))
            digest.update(child.read_bytes())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _load_previous_registry(previous_registry_path: Path | str | None) -> dict[str, Any]:
    if not previous_registry_path:
        return {}
    path = Path(previous_registry_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _model_change_diff(previous: dict[str, Any], audit: dict[str, Any], version: str) -> list[str]:
    if not previous:
        return ["initial_release"]
    current = {
        "model_id": str(audit.get("best_model", "")),
        "version": version,
        "benchmark_report_sha256": str(audit.get("benchmark_report_sha256", "")),
    }
    diffs: list[str] = []
    for key, current_value in current.items():
        previous_value = str(previous.get(key, ""))
        if previous_value != str(current_value):
            diffs.append(f"{key}:{previous_value}->{current_value}")
    return diffs or ["no_change"]
