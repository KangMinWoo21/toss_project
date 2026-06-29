from __future__ import annotations

import csv
from pathlib import Path


FINANCIAL_SCHEMA_COLUMNS = [
    "feature_group",
    "source_name",
    "candidate_features",
    "schema_fields",
    "timestamp_fields",
    "lineage_rule",
    "api_key_required",
    "fetch_allowed_now",
    "training_allowed_now",
    "trading_allowed",
    "production_effect",
    "pit_required",
    "usable_from_required",
    "leakage_risk",
    "data_quality_risk",
    "current_status",
    "next_safe_action",
]


def _row(
    *,
    feature_group: str,
    source_name: str,
    candidate_features: list[str],
    schema_fields: list[str],
    timestamp_fields: list[str],
    lineage_rule: str,
    leakage_risk: str,
    data_quality_risk: str,
    next_safe_action: str,
) -> dict[str, str]:
    return {
        "feature_group": feature_group,
        "source_name": source_name,
        "candidate_features": ";".join(candidate_features),
        "schema_fields": ";".join(schema_fields),
        "timestamp_fields": ";".join(timestamp_fields),
        "lineage_rule": lineage_rule,
        "api_key_required": "True",
        "fetch_allowed_now": "False",
        "training_allowed_now": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "pit_required": "True",
        "usable_from_required": "True",
        "leakage_risk": leakage_risk,
        "data_quality_risk": data_quality_risk,
        "current_status": "schema_plan_only",
        "next_safe_action": next_safe_action,
    }


def build_ml_financial_feature_schema_plan() -> list[dict[str, str]]:
    common_timestamps = [
        "receipt_date",
        "receipt_time",
        "collected_at",
        "usable_from",
        "report_period_end",
    ]
    return [
        _row(
            feature_group="financial_statement_metrics",
            source_name="OpenDART financial statements",
            candidate_features=["sales", "operating_income", "net_income", "debt_ratio", "roe"],
            schema_fields=[
                "corp_code",
                "stock_code",
                "symbol",
                "account_id",
                "account_name",
                "statement_type",
                "currency",
                "amount",
                "fiscal_year",
                "quarter",
            ],
            timestamp_fields=common_timestamps + ["fiscal_period"],
            lineage_rule="append_only_by_receipt_no_and_account; retain restatements and correction lineage; never overwrite prior visible rows",
            leakage_risk="high_if_report_period_end_is_used_without_receipt_date_or_usable_from",
            data_quality_risk="missing accounts, consolidated/separate mismatch, restatement drift, account taxonomy changes",
            next_safe_action="Review schema only; do not fetch OpenDART data until a future goal explicitly approves limited fetch.",
        ),
        _row(
            feature_group="market_valuation_metrics",
            source_name="OpenDART plus local market snapshot after future approval",
            candidate_features=["per", "pbr"],
            schema_fields=[
                "symbol",
                "market_date",
                "market_cap",
                "shares_outstanding",
                "book_value",
                "net_income_ttm",
                "per",
                "pbr",
            ],
            timestamp_fields=common_timestamps + ["market_date", "price_visible_at"],
            lineage_rule="join valuation inputs only when both financial observation and market snapshot are visible by usable_from",
            leakage_risk="high_if_market_date_or_revised_financials_are_joined_after_the_training_cutoff",
            data_quality_risk="stale shares, negative equity, ttm alignment, fiscal-period mismatch, split adjustments",
            next_safe_action="Define valuation join audit before any feature is added to training.",
        ),
        _row(
            feature_group="disclosure_lineage",
            source_name="OpenDART disclosure list",
            candidate_features=["filing_event_type", "correction_filing_flag", "report_name", "receipt_no"],
            schema_fields=[
                "receipt_no",
                "original_receipt_no",
                "corp_code",
                "symbol",
                "report_name",
                "filing_event_type",
                "correction_filing_flag",
                "correction_sequence",
            ],
            timestamp_fields=common_timestamps + ["original_receipt_date", "correction_receipt_date"],
            lineage_rule="link every correction filing to original receipt_no; preserve receipt_date and receipt_time for each visible version",
            leakage_risk="high_if_corrected_values_replace_original_rows_before_correction_receipt_time",
            data_quality_risk="amended filings, duplicate receipt numbers, missing original links, delayed disclosure visibility",
            next_safe_action="Create deterministic correction lineage audit before limited fetch.",
        ),
        _row(
            feature_group="pit_controls",
            source_name="derived PIT financial feature controls",
            candidate_features=["usable_from", "source_revision", "financial_observation_id", "feature_valid_asof"],
            schema_fields=[
                "financial_observation_id",
                "source_revision",
                "visible_version",
                "feature_valid_asof",
                "excluded_reason",
                "quality_status",
            ],
            timestamp_fields=common_timestamps + ["feature_generated_at"],
            lineage_rule="feature rows become training-eligible only when usable_from <= feature_date and quality_status=PASS",
            leakage_risk="block_if_usable_from_missing_or_after_feature_date",
            data_quality_risk="timezone ambiguity, delayed collection, missing timestamps, quality exclusion drift",
            next_safe_action="Write PIT audit rules; keep fetch_allowed_now=False and training_allowed_now=False.",
        ),
    ]


def _validate_rows(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [column for column in FINANCIAL_SCHEMA_COLUMNS if not row.get(column)]
        if missing:
            raise ValueError(f"financial schema row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("api_key_required", "True"),
            ("fetch_allowed_now", "False"),
            ("training_allowed_now", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("pit_required", "True"),
            ("usable_from_required", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"financial schema row {index} {column}={row[column]} expected {expected}")
        for field in ("receipt_date", "receipt_time", "collected_at", "usable_from"):
            if field not in row["timestamp_fields"]:
                raise ValueError(f"financial schema row {index} missing timestamp field {field}")


def save_ml_financial_feature_schema_plan(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINANCIAL_SCHEMA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# ML Financial Feature Schema Plan",
        "",
        "## Do Not Trade / Schema Plan Only",
        "",
        "This report is a paper-only OpenDART schema plan. It does not fetch data, call APIs, read API keys, train models, rerun OOS, compare candidates, create candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        "- `fetch_allowed_now=False` for every row.",
        "- `training_allowed_now=False` for every row.",
        "- `trading_allowed=False` for every row.",
        "- `production_effect=none` for every row.",
        "- Required PIT timestamps include `receipt_date`, `receipt_time`, `collected_at`, and `usable_from`.",
        "",
        "## Schema Rows",
        "",
        "| Feature Group | Candidate Features | Timestamp Fields | Lineage Rule | Next Safe Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {feature_group} | {candidate_features} | {timestamp_fields} | {lineage_rule} | {next_safe_action} |".format(
                feature_group=row["feature_group"],
                candidate_features=row["candidate_features"].replace("|", "/"),
                timestamp_fields=row["timestamp_fields"].replace("|", "/"),
                lineage_rule=row["lineage_rule"].replace("|", "/"),
                next_safe_action=row["next_safe_action"].replace("|", "/"),
            )
        )
    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
