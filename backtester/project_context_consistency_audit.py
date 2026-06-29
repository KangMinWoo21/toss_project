from __future__ import annotations

import csv
import re
from pathlib import Path


AUDIT_COLUMNS = [
    "check",
    "status",
    "expected",
    "observed",
    "recommendation",
    "source",
    "audit_status",
    "trading_allowed",
    "review_allowed",
    "production_effect",
    "recommended_action",
]

RECOMMENDED_ACTION = "keep_observing_no_tuning_no_promotion"


SOURCES = [
    ("minimal_prompt", "minimal_prompt_md"),
    ("checkpoint", "checkpoint_md"),
    ("gpt_project_context", "gpt_project_context_md"),
    ("safety_status_index", "safety_status_index_md"),
]

REQUIRED_PATTERNS = [
    ("production_block", re.compile(r"production.*(not live-ready|remains|block_retained|readiness).*block|production remains block", re.I | re.S)),
    ("protected_candidate_paper_review", re.compile(r"paper_review", re.I)),
    ("oos_review_eligibility_not_allowed", re.compile(r"review_not_allowed", re.I)),
    ("trading_allowed_false", re.compile(r"trading[_ ]allowed\s*(?:=|:)\s*`?false`?", re.I)),
    ("review_allowed_false", re.compile(r"review[_ ]allowed\s*(?:=|:)\s*`?false`?", re.I)),
    ("production_effect_none", re.compile(r"production[_ ]effect\s*(?:=|:)\s*`?none`?", re.I)),
    ("actionable_rows_zero", re.compile(r"actionable[_ -]rows\s*(?:remain\s*)?(?:=|:)?\s*`?0`?", re.I)),
    ("promoted_candidates_zero", re.compile(r"promoted candidates(?: count)?(?: remains)?\s*(?:=|:)?\s*`?0`?|promoted_candidates_zero", re.I)),
    ("recommended_action", re.compile(re.escape(RECOMMENDED_ACTION), re.I)),
    ("scalper_warn_separated", re.compile(r"scalper stale [`']?warn[`']?.*(separate|separated)", re.I | re.S)),
]

DANGEROUS_PATTERNS = [
    re.compile(r"trading_allowed\s*=\s*true|trading allowed\s*:\s*`?true`?", re.I),
    re.compile(r"review_allowed\s*=\s*true|review allowed\s*:\s*`?true`?", re.I),
    re.compile(r"production_effect\s*=\s*(?!none\b)\w+|production effect\s*:\s*`?(?!none\b)\w+", re.I),
    re.compile(r"production\s+is\s+live-ready", re.I),
    re.compile(r"actionable[_ -]rows\s*(?:=|:)\s*`?[1-9]\d*`?", re.I),
    re.compile(r"promoted candidates(?: count)?\s*(?:=|:)\s*`?[1-9]\d*`?", re.I),
    re.compile(r"broker submission\s*:\s*(authorized|allowed)|order execution\s*:\s*(authorized|allowed)", re.I),
]

OUTDATED_PATTERNS = [
    re.compile(r"2026-06-25"),
    re.compile(r"latest pushed commit", re.I),
    re.compile(r"push to .*completed", re.I),
    re.compile(r"\b(?:block|pass|warn)=\d+\b", re.I),
    re.compile(r"\b613\s+pass\b", re.I),
    re.compile(r"latest verified counts before", re.I),
]


def _row(check: str, status: str, expected: str, observed: str, recommendation: str, source: str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "expected": expected,
        "observed": observed,
        "recommendation": recommendation,
        "source": source,
        "audit_status": "",
        "trading_allowed": "False",
        "review_allowed": "False",
        "production_effect": "none",
        "recommended_action": RECOMMENDED_ACTION,
    }


def _read_markdown(path: Path | str) -> tuple[str, str | None]:
    source = Path(path)
    if not source.exists():
        return "", f"missing source file: {source}"
    try:
        return source.read_text(encoding="utf-8-sig"), None
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return "", f"failed to read {source}: {exc}"


def _line_matches(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    matches: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern.search(line):
                matches.append(f"line {lineno}: {line.strip()}")
                break
    return matches


def _required_missing(texts: dict[str, str]) -> list[str]:
    missing: list[str] = []
    for source_name, text in texts.items():
        for marker_name, pattern in REQUIRED_PATTERNS:
            if not pattern.search(text):
                missing.append(f"{source_name}:{marker_name}")
    return missing


def _dangerous_matches(texts: dict[str, str]) -> list[str]:
    matches: list[str] = []
    for source_name, text in texts.items():
        for match in _line_matches(text, DANGEROUS_PATTERNS):
            matches.append(f"{source_name}:{match}")
    return matches


def _outdated_matches(texts: dict[str, str]) -> list[str]:
    matches: list[str] = []
    for source_name, text in texts.items():
        for match in _line_matches(text, OUTDATED_PATTERNS):
            matches.append(f"{source_name}:{match}")
    return matches


def build_project_context_consistency_audit(
    *,
    minimal_prompt_md: Path | str,
    checkpoint_md: Path | str,
    gpt_project_context_md: Path | str,
    safety_status_index_md: Path | str,
) -> list[dict[str, str]]:
    paths = {
        "minimal_prompt_md": minimal_prompt_md,
        "checkpoint_md": checkpoint_md,
        "gpt_project_context_md": gpt_project_context_md,
        "safety_status_index_md": safety_status_index_md,
    }
    texts: dict[str, str] = {}
    source_errors: list[str] = []
    for source_name, arg_name in SOURCES:
        text, error = _read_markdown(paths[arg_name])
        texts[source_name] = text
        if error:
            source_errors.append(error)

    missing_required = _required_missing(texts)
    dangerous = _dangerous_matches(texts)
    outdated = _outdated_matches(texts)
    safety_index_observe = bool(re.search(r"overall[_ ]status\s*(?:=|:)\s*`?observe`?", texts.get("safety_status_index", ""), re.I))

    rows = [
        _row(
            "source_files_present",
            "BLOCK" if source_errors else "PASS",
            "all context sources readable",
            "; ".join(source_errors) if source_errors else "all context sources readable",
            "Restore or pass the missing local source file path; fail closed until readable.",
            "multiple",
        ),
        _row(
            "required_safety_status_present",
            "BLOCK" if missing_required else "PASS",
            "all restart/context documents describe the current safety status",
            "; ".join(missing_required) if missing_required else "all required safety markers present",
            "Add only the missing current safety marker; do not change strategy or reports.",
            "multiple",
        ),
        _row(
            "dangerous_authorization_text_absent",
            "BLOCK" if dangerous else "PASS",
            "no text suggests trading, review, production effect, or promotion is allowed",
            "; ".join(dangerous) if dangerous else "no dangerous authorization text found",
            "Remove or correct the authorization-looking text; keep trading_allowed=False and production_effect=none.",
            "multiple",
        ),
        _row(
            "outdated_text_absent",
            "WARN" if outdated else "PASS",
            "no stale test counts, push status, or outdated BLOCK/WARN counts",
            "; ".join(outdated) if outdated else "no stale counts or old push state found",
            "Refresh the stale text to the latest checkpoint baseline; audit does not auto-fix it.",
            "multiple",
        ),
        _row(
            "safety_status_index_observe_present",
            "PASS" if safety_index_observe else "BLOCK",
            "safety index says overall_status=OBSERVE",
            "overall_status=OBSERVE" if safety_index_observe else "overall_status=OBSERVE missing",
            "Regenerate only the audit after restoring the local safety index source; do not authorize trading.",
            str(safety_status_index_md),
        ),
    ]

    if any(row["status"] == "BLOCK" for row in rows):
        audit_status = "BLOCK"
    elif any(row["status"] == "WARN" for row in rows):
        audit_status = "WARN"
    else:
        audit_status = "PASS"

    summary = _row(
        "summary",
        audit_status,
        "audit_status=PASS with aligned safety context",
        f"audit_status={audit_status}; trading_allowed=False; review_allowed=False; production_effect=none",
        "Use this report as context audit only; it grants no trading, review, promotion, or production readiness change.",
        "derived",
    )
    summary["audit_status"] = audit_status
    rows.insert(0, summary)
    for row in rows[1:]:
        row["audit_status"] = audit_status
    return rows


def save_project_context_consistency_audit(
    rows: list[dict[str, str]],
    csv_output: Path | str,
    markdown_output: Path | str,
) -> None:
    csv_path = Path(csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = rows[0] if rows else {}
    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    warn_count = sum(1 for row in rows if row.get("status") == "WARN")
    block_count = sum(1 for row in rows if row.get("status") == "BLOCK")
    lines = [
        "# Project Context Consistency Audit",
        "",
        "## Do Not Trade / Context Audit Only",
        "",
        "This report is a context consistency audit only and does not authorize trading, broker submission, order execution, candidate promotion, OOS review, or production readiness change.",
        "",
        f"- Audit status: `{summary.get('audit_status', 'BLOCK')}`.",
        "- Trading allowed: `False`.",
        "- Review allowed: `False`.",
        "- Production effect: `none`.",
        f"- Recommended action: `{summary.get('recommended_action', RECOMMENDED_ACTION)}`.",
        "",
        "## Summary",
        "",
        f"- PASS rows: `{pass_count}`.",
        f"- WARN rows: `{warn_count}`.",
        f"- BLOCK rows: `{block_count}`.",
        "- Outdated text is reported only; this audit does not modify source documents.",
        "- Scalper stale WARN must remain separate from monthly paper review/OOS.",
        "",
        "## Checks",
        "",
        "| Check | Status | Expected | Observed | Recommendation | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {check} | {status} | {expected} | {observed} | {recommendation} | {source} |".format(
                check=row.get("check", ""),
                status=row.get("status", ""),
                expected=str(row.get("expected", "")).replace("|", "/"),
                observed=str(row.get("observed", "")).replace("|", "/"),
                recommendation=str(row.get("recommendation", "")).replace("|", "/"),
                source=row.get("source", ""),
            )
        )

    markdown_path = Path(markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
