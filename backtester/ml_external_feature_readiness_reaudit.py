from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS = [
    "feature_group",
    "readiness",
    "leakage_check",
    "missing_rate",
    "evidence",
    "source",
    "training_allowed",
    "feature_added_to_training",
    "post_cutoff_data_used_for_train",
    "trading_allowed",
    "production_effect",
    "protected_candidate_unchanged",
    "next_safe_action",
]


@dataclass(frozen=True)
class ExternalFeatureReadinessReauditResult:
    rows: list[dict[str, str]]


def build_ml_external_feature_readiness_reaudit(
    *,
    financial_merge_audit_csv: Path | str = "data/reports/ml_financial_feature_merge_audit.csv",
    news_schema_plan_csv: Path | str = "data/reports/ml_news_event_schema_plan.csv",
    sentiment_scoring_plan_csv: Path | str = "data/reports/ml_sentiment_scoring_plan.csv",
) -> ExternalFeatureReadinessReauditResult:
    financial_rows, financial_error = _read_csv(financial_merge_audit_csv)
    news_rows, news_error = _read_csv(news_schema_plan_csv)
    sentiment_rows, sentiment_error = _read_csv(sentiment_scoring_plan_csv)

    financial_by_metric = {row.get("metric", ""): row for row in financial_rows}
    financial_leakage = financial_by_metric.get("leakage_check", {}).get("status", "BLOCK")
    financial_missing_rate = financial_by_metric.get("missing_rate", {}).get("value", "1.0000")
    financial_training_allowed = _all_column_equals(financial_rows, "training_allowed_now", "False")
    financial_feature_added = _all_column_equals(financial_rows, "feature_added_to_training", "False")
    financial_ready = (
        not financial_error
        and financial_leakage == "PASS"
        and financial_missing_rate not in {"1.0000", "missing"}
        and financial_training_allowed
        and financial_feature_added
    )

    news_schema_only = bool(news_rows) and _all_column_equals(news_rows, "current_status", "schema_plan_only")
    news_fetch_disabled = _all_column_equals(news_rows, "fetch_allowed_now", "False")
    news_training_disabled = _all_column_equals(news_rows, "training_allowed_now", "False")
    news_feature_added = _all_column_equals(news_rows, "feature_added_to_training", "False")
    news_timestamp_ok = all(
        all(field in row.get("timestamp_fields", "") for field in ("published_at", "collected_at", "visible_at", "usable_from"))
        for row in news_rows
    )

    sentiment_schema_only = bool(sentiment_rows) and _all_column_equals(sentiment_rows, "current_status", "schema_plan_only")
    sentiment_training_disabled = _all_column_equals(sentiment_rows, "training_allowed_now", "False")
    sentiment_model_training_disabled = _all_column_equals(sentiment_rows, "model_training_allowed", "False")
    sentiment_feature_added = _all_column_equals(sentiment_rows, "feature_added_to_training", "False")
    sentiment_timestamp_ok = all(
        all(field in row.get("timestamp_fields", "") for field in ("published_at", "collected_at", "visible_at", "scored_at", "usable_from"))
        for row in sentiment_rows
    )
    sentiment_lexicon = any(row.get("model_version") == "rule_lexicon_v1" for row in sentiment_rows)

    rows = [
        _row(
            feature_group="financial",
            readiness="ready" if financial_ready else "not_ready",
            leakage_check=financial_leakage if not financial_error else "BLOCK",
            missing_rate=financial_missing_rate,
            evidence=financial_error
            or f"merge_audit={financial_by_metric.get('summary', {}).get('status', 'missing')}; join_coverage={financial_by_metric.get('join_coverage', {}).get('value', 'missing')}; training_allowed_now={financial_training_allowed}",
            source=financial_merge_audit_csv,
            next_safe_action="Do not train; financial sample remains not ready until coverage and missingness pass under explicit approval.",
        ),
        _row(
            feature_group="news",
            readiness="not_ready",
            leakage_check="PASS" if not news_error and news_timestamp_ok and news_fetch_disabled else "BLOCK",
            missing_rate="not_measured_schema_only",
            evidence=news_error
            or f"schema_plan_only={news_schema_only}; fetch_allowed_now={news_fetch_disabled}; training_allowed_now={news_training_disabled}; feature_added_to_training={news_feature_added}",
            source=news_schema_plan_csv,
            next_safe_action="Keep news plan-only; no fetch or training until a future explicitly approved limited news-fetch goal.",
        ),
        _row(
            feature_group="sentiment",
            readiness="not_ready",
            leakage_check="PASS" if not sentiment_error and sentiment_timestamp_ok and sentiment_training_disabled else "BLOCK",
            missing_rate="not_measured_plan_only",
            evidence=sentiment_error
            or f"schema_plan_only={sentiment_schema_only}; rule_lexicon_v1={sentiment_lexicon}; model_training_allowed={sentiment_model_training_disabled}; feature_added_to_training={sentiment_feature_added}",
            source=sentiment_scoring_plan_csv,
            next_safe_action="Keep sentiment plan-only; do not score, train, or merge until external feature readiness is explicitly approved.",
        ),
    ]
    overall_ready = all(row["readiness"] == "ready" for row in rows)
    rows.append(
        _row(
            feature_group="overall",
            readiness="ready" if overall_ready else "BLOCK",
            leakage_check="PASS" if all(row["leakage_check"] == "PASS" for row in rows) else "BLOCK",
            missing_rate="mixed",
            evidence="; ".join(f"{row['feature_group']}={row['readiness']}" for row in rows),
            source=f"{financial_merge_audit_csv};{news_schema_plan_csv};{sentiment_scoring_plan_csv}",
            next_safe_action="External features are not approved for training; proceed only to a future paper-only experiment if separately approved.",
        )
    )
    return ExternalFeatureReadinessReauditResult(rows=rows)


def save_ml_external_feature_readiness_reaudit(
    result: ExternalFeatureReadinessReauditResult,
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    _validate_rows(result.rows)
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(result.rows)

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_build_markdown(result.rows), encoding="utf-8")


def _row(
    *,
    feature_group: str,
    readiness: str,
    leakage_check: str,
    missing_rate: str,
    evidence: str,
    source: Path | str,
    next_safe_action: str,
) -> dict[str, str]:
    return {
        "feature_group": feature_group,
        "readiness": readiness,
        "leakage_check": leakage_check,
        "missing_rate": missing_rate,
        "evidence": evidence,
        "source": str(source),
        "training_allowed": "False",
        "feature_added_to_training": "False",
        "post_cutoff_data_used_for_train": "False",
        "trading_allowed": "False",
        "production_effect": "none",
        "protected_candidate_unchanged": "True",
        "next_safe_action": next_safe_action,
    }


def _read_csv(path: Path | str) -> tuple[list[dict[str, str]], str | None]:
    csv_path = Path(path)
    if not csv_path.exists():
        return [], f"missing {csv_path}"
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f)), None


def _all_column_equals(rows: list[dict[str, str]], column: str, expected: str) -> bool:
    return bool(rows) and all(row.get(column) == expected for row in rows)


def _validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("external feature readiness re-audit is empty")
    for index, row in enumerate(rows, start=1):
        missing = [column for column in EXTERNAL_FEATURE_READINESS_REAUDIT_COLUMNS if not row.get(column)]
        if missing:
            raise ValueError(f"external feature readiness re-audit row {index} missing: {','.join(missing)}")
        for column, expected in (
            ("training_allowed", "False"),
            ("feature_added_to_training", "False"),
            ("post_cutoff_data_used_for_train", "False"),
            ("trading_allowed", "False"),
            ("production_effect", "none"),
            ("protected_candidate_unchanged", "True"),
        ):
            if row[column] != expected:
                raise ValueError(f"external feature readiness re-audit row {index} {column}={row[column]} expected {expected}")


def _build_markdown(rows: list[dict[str, str]]) -> str:
    by_group = {row["feature_group"]: row for row in rows}
    lines = [
        "# ML External Feature Readiness Re-Audit",
        "",
        "## Do Not Trade / Re-Audit Only",
        "",
        "This report re-audits external feature readiness for paper-only ML research. It does not fetch data, call APIs, score sentiment, train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.",
        "",
        f"- Overall readiness: `{by_group.get('overall', {}).get('readiness', 'BLOCK')}`.",
        "- `training_allowed=False` for every row.",
        "- `feature_added_to_training=False` for every row.",
        "- `post_cutoff_data_used_for_train=False` for every row.",
        "- `trading_allowed=False` for every row.",
        "- `production_effect=none` for every row.",
        "",
        "## Re-Audit Rows",
        "",
        "| Feature Group | Readiness | Leakage Check | Missing Rate | Evidence | Next Safe Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {feature_group} | {readiness} | {leakage_check} | {missing_rate} | {evidence} | {next_safe_action} |".format(
                feature_group=row["feature_group"],
                readiness=row["readiness"],
                leakage_check=row["leakage_check"],
                missing_rate=row["missing_rate"],
                evidence=row["evidence"].replace("|", "/"),
                next_safe_action=row["next_safe_action"].replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"
