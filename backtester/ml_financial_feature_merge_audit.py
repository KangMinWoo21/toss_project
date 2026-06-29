from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


FINANCIAL_FEATURE_MERGE_AUDIT_COLUMNS = [
    "metric",
    "status",
    "value",
    "reason",
    "source",
    "post_cutoff_data_used_for_train",
    "feature_added_to_training",
    "training_allowed_now",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
]


@dataclass(frozen=True)
class FinancialFeatureMergeAuditResult:
    audit_rows: list[dict[str, str]]


def build_ml_financial_feature_merge_audit(
    *,
    dataset_csv: Path | str = "data/reports/ml_baseline_feature_label_sample.csv",
    financial_observations_csv: Path | str = "data/reports/ml_financial_observations_sample.csv",
    financial_pit_audit_csv: Path | str = "data/reports/ml_financial_pit_audit.csv",
) -> FinancialFeatureMergeAuditResult:
    dataset_rows, dataset_error = _read_csv(dataset_csv)
    observation_rows, observation_error = _read_csv(financial_observations_csv)
    pit_rows, pit_error = _read_csv(financial_pit_audit_csv)

    dataset_symbols = {row.get("symbol", "").strip() for row in dataset_rows if row.get("symbol", "").strip()}
    observation_symbols = {row.get("symbol", "").strip() for row in observation_rows if row.get("symbol", "").strip()}
    joined_symbols = dataset_symbols & observation_symbols
    dataset_count = len(dataset_symbols)
    joined_count = len(joined_symbols)
    missing_rate = 1.0 if dataset_count == 0 else (dataset_count - joined_count) / dataset_count

    source_errors = [error for error in (dataset_error, observation_error, pit_error) if error]
    pit_by_name = {row.get("check_name", ""): row for row in pit_rows}
    pit_leakage_pass = pit_by_name.get("post_cutoff_train_leakage", {}).get("check_status") == "PASS"
    observation_safe = all(
        row.get("training_allowed_now") == "False"
        and row.get("trading_allowed") == "False"
        and row.get("production_effect") == "none"
        for row in observation_rows
    )
    dataset_safe = all(
        row.get("post_cutoff_data_used_for_train") == "False"
        and row.get("trading_allowed") == "False"
        and row.get("production_effect") == "none"
        for row in dataset_rows
    )
    safe_to_audit = not source_errors and bool(dataset_rows) and bool(observation_rows)
    leakage_pass = safe_to_audit and pit_leakage_pass and observation_safe and dataset_safe

    audit_rows = [
        _row(
            "summary",
            "financial_feature_merge_audit_complete" if safe_to_audit else "partial_merge_audit_only",
            "financial_feature_merge_audit_complete" if safe_to_audit else "; ".join(source_errors) or "missing rows",
            "Phase 7 merge audit only; no model training, OOS rerun, fetch, candidate compare, candidate generation, strategy parameter change, or production change was performed.",
            "derived",
        ),
        _row(
            "source_files_present",
            "PASS" if not source_errors else "BLOCK",
            "all required local sources readable" if not source_errors else "; ".join(source_errors),
            "Requires Phase 1 dataset sample, Phase 6 observations, and Phase 6 PIT audit.",
            f"{dataset_csv};{financial_observations_csv};{financial_pit_audit_csv}",
        ),
        _row(
            "join_coverage",
            "PASS" if joined_count > 0 else "WARN",
            f"{joined_count}/{dataset_count}",
            "Distinct baseline dataset symbols with at least one limited financial observation.",
            f"{dataset_csv};{financial_observations_csv}",
        ),
        _row(
            "missing_rate",
            "PASS" if missing_rate < 1.0 else "WARN",
            f"{missing_rate:.4f}",
            "Symbol-level financial observation missing rate against the baseline sample.",
            "derived",
        ),
        _row(
            "leakage_check",
            "PASS" if leakage_pass else "BLOCK",
            f"pit_leakage_pass={pit_leakage_pass}; observation_safe={observation_safe}; dataset_safe={dataset_safe}",
            "Financial features are audited for merge readiness only and are not added to training.",
            f"{financial_pit_audit_csv};{financial_observations_csv};{dataset_csv}",
        ),
        _row(
            "post_cutoff_data_used_for_train",
            "PASS",
            "False",
            "No financial feature row is used for train in Phase 7.",
            "derived",
        ),
        _row(
            "feature_added_to_training",
            "PASS",
            "False",
            "Phase 7 does not alter the baseline model dataset or training inputs.",
            "derived",
        ),
        _row(
            "training_allowed_now",
            "PASS",
            "False",
            "Limited financial sample remains merge-audited only.",
            "derived",
        ),
        _row(
            "trading_allowed",
            "PASS",
            "False",
            "Merge audit only; no trading authorization.",
            "derived",
        ),
        _row(
            "protected_candidate_status",
            "PASS",
            "PAPER_REVIEW unchanged",
            "Protected candidate is not read for tuning, modified, promoted, or replaced.",
            "derived",
        ),
        _row(
            "protected_candidate_unchanged",
            "PASS",
            "True",
            "Protected PAPER_REVIEW candidate remains unchanged.",
            "derived",
        ),
        _row(
            "production_effect",
            "PASS",
            "none",
            "Report has no production effect.",
            "derived",
        ),
    ]
    return FinancialFeatureMergeAuditResult(audit_rows=audit_rows)


def save_ml_financial_feature_merge_audit(
    result: FinancialFeatureMergeAuditResult,
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINANCIAL_FEATURE_MERGE_AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(result.audit_rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_markdown(result.audit_rows), encoding="utf-8")


def _row(metric: str, status: str, value: object, reason: str, source: Path | str) -> dict[str, str]:
    return {
        "metric": metric,
        "status": status,
        "value": str(value),
        "reason": reason,
        "source": str(source),
        "post_cutoff_data_used_for_train": "False",
        "feature_added_to_training": "False",
        "training_allowed_now": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
    }


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    csv_path = Path(path)
    if not csv_path.exists():
        return [], f"missing {csv_path}"
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f)), None


def _build_markdown(audit_rows: list[dict[str, str]]) -> str:
    by_metric = {row["metric"]: row for row in audit_rows}
    lines = [
        "# ML Financial Feature Merge Audit",
        "",
        "## Do Not Trade / Merge Audit Only",
        "",
        "This report audits whether the limited financial sample can be technically merged with the baseline ML dataset. It does not train models, rerun OOS, fetch data, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        f"- Merge audit status: `{by_metric.get('summary', {}).get('status', 'partial_merge_audit_only')}`.",
        f"- Join coverage: `{by_metric.get('join_coverage', {}).get('value', '')}`.",
        f"- Missing rate: `{by_metric.get('missing_rate', {}).get('value', '')}`.",
        f"- Leakage check: `{by_metric.get('leakage_check', {}).get('status', '')}`.",
        "- Feature added to training: `False`.",
        "- Training allowed now: `False`.",
        "- Trading allowed: `False`.",
        "- Production effect: `none`.",
        "",
        "## Checks",
        "",
        "| Metric | Status | Value | Reason | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in audit_rows:
        lines.append(
            "| {metric} | {status} | {value} | {reason} | {source} |".format(
                metric=row.get("metric", ""),
                status=row.get("status", ""),
                value=str(row.get("value", "")).replace("|", "/"),
                reason=str(row.get("reason", "")).replace("|", "/"),
                source=str(row.get("source", "")).replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"
