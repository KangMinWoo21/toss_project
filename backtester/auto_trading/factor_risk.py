from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .external_data import ExternalDataBundle, load_external_data_bundle


FIELDNAMES = [
    "check",
    "status",
    "metric_value",
    "limit_value",
    "detail",
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
class FactorRiskLimits:
    max_single_weight: float = 0.35
    max_sector_weight: float = 0.50
    max_weighted_beta: float = 1.50
    max_negative_quality_tilt: float = 0.20


def build_factor_risk_rows(
    *,
    targets_path: Path | str,
    external_data_dir: Path | str,
    limits: FactorRiskLimits | None = None,
) -> list[dict[str, str]]:
    active_limits = limits or FactorRiskLimits()
    targets = _load_safe_targets(Path(targets_path))
    symbols = [row["symbol"] for row in targets]
    external = load_external_data_bundle(external_data_dir, symbols)
    return _factor_risk_rows(targets, external, active_limits)


def save_factor_risk_reports(rows: list[dict[str, str]], csv_path: Path | str, markdown_path: Path | str) -> None:
    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    markdown_output = Path(markdown_path)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(_markdown(rows), encoding="utf-8")


def _factor_risk_rows(
    targets: list[dict[str, float | str]],
    external: ExternalDataBundle,
    limits: FactorRiskLimits,
) -> list[dict[str, str]]:
    sector_weights = _sector_weights(targets, external)
    max_single = max(float(row["target_weight"]) for row in targets)
    max_sector = max(sector_weights.values())
    weighted_beta = _weighted_sum(targets, external, "beta")
    weighted_size = _weighted_sum(targets, external, "size_score")
    weighted_value = _weighted_sum(targets, external, "value_score")
    weighted_quality = _weighted_sum(targets, external, "quality_score")
    weighted_momentum = _weighted_sum(targets, external, "momentum_score")
    negative_quality_tilt = max(0.0, 0.50 - weighted_quality)
    return [
        _row(
            "single_name_exposure",
            max_single <= limits.max_single_weight,
            max_single,
            limits.max_single_weight,
            f"max_symbol_weight={max_single:.6f}",
        ),
        _row(
            "sector_exposure",
            max_sector <= limits.max_sector_weight,
            max_sector,
            limits.max_sector_weight,
            "sector_weights=" + ",".join(f"{sector}:{weight:.6f}" for sector, weight in sorted(sector_weights.items())),
        ),
        _row("weighted_beta", weighted_beta <= limits.max_weighted_beta, weighted_beta, limits.max_weighted_beta, "cash_beta=0"),
        _row("weighted_size_score", True, weighted_size, 1.0, "report_only"),
        _row("weighted_value_score", True, weighted_value, 1.0, "report_only"),
        _row("weighted_quality_score", True, weighted_quality, 1.0, "report_only"),
        _row(
            "quality_tilt",
            negative_quality_tilt <= limits.max_negative_quality_tilt,
            negative_quality_tilt,
            limits.max_negative_quality_tilt,
            f"weighted_quality_score={weighted_quality:.6f}",
        ),
        _row("weighted_momentum_score", True, weighted_momentum, 1.0, "report_only"),
    ]


def _load_safe_targets(path: Path) -> list[dict[str, float | str]]:
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        rows: list[dict[str, float | str]] = []
        for row in reader:
            _assert_safe_target_row(row)
            symbol = str(row.get("symbol", "")).strip().upper()
            weight = float(row.get("target_weight", 0) or 0)
            if symbol and weight > 0:
                rows.append({"symbol": symbol, "target_weight": weight})
    if not rows:
        raise ValueError(f"{path} has no positive target weights")
    return rows


def _assert_safe_target_row(row: dict[str, str]) -> None:
    expected = {
        "paper_only": "True",
        "dry_run": "True",
        "execution_allowed": "False",
        "production_effect": "none",
    }
    for key, expected_value in expected.items():
        actual = str(row.get(key, "")).strip()
        if actual != expected_value:
            raise ValueError(f"unsafe factor risk target row for {row.get('symbol', '')}: {key}={actual}")


def _sector_weights(targets: list[dict[str, float | str]], external: ExternalDataBundle) -> dict[str, float]:
    weights: dict[str, float] = {}
    for target in targets:
        symbol = str(target["symbol"])
        sector = external.symbol_rows[symbol].sector or "unknown"
        weights[sector] = weights.get(sector, 0.0) + float(target["target_weight"])
    return weights


def _weighted_sum(targets: list[dict[str, float | str]], external: ExternalDataBundle, field_name: str) -> float:
    total = 0.0
    for target in targets:
        symbol = str(target["symbol"])
        value = getattr(external.symbol_rows[symbol], field_name)
        total += float(target["target_weight"]) * float(value)
    return total


def _row(check: str, passed: bool, metric_value: float, limit_value: float, detail: str) -> dict[str, str]:
    return {
        "check": check,
        "status": "PASS" if passed else "BLOCK",
        "metric_value": f"{metric_value:.6f}",
        "limit_value": f"{limit_value:.6f}",
        "detail": detail,
        **PAPER_FLAGS,
    }


def _markdown(rows: list[dict[str, str]]) -> str:
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK"
    lines = [
        "# Factor Risk Report",
        "",
        "paper-only / dry-run / execution_allowed=False",
        "",
        f"- overall_status: `{overall}`",
        "",
        "| check | status | metric_value | limit_value | detail |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check']} | {row['status']} | {row['metric_value']} | {row['limit_value']} | {row['detail']} |"
        )
    lines.append("")
    return "\n".join(lines)
