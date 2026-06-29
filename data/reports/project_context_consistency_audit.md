# Project Context Consistency Audit

## Do Not Trade / Context Audit Only

This report is a context consistency audit only and does not authorize trading, broker submission, order execution, candidate promotion, OOS review, or production readiness change.

- Audit status: `PASS`.
- Trading allowed: `False`.
- Review allowed: `False`.
- Production effect: `none`.
- Recommended action: `keep_observing_no_tuning_no_promotion`.

## Summary

- PASS rows: `6`.
- WARN rows: `0`.
- BLOCK rows: `0`.
- Outdated text is reported only; this audit does not modify source documents.
- Scalper stale WARN must remain separate from monthly paper review/OOS.

## Checks

| Check | Status | Expected | Observed | Recommendation | Source |
| --- | --- | --- | --- | --- | --- |
| summary | PASS | audit_status=PASS with aligned safety context | audit_status=PASS; trading_allowed=False; review_allowed=False; production_effect=none | Use this report as context audit only; it grants no trading, review, promotion, or production readiness change. | derived |
| source_files_present | PASS | all context sources readable | all context sources readable | Restore or pass the missing local source file path; fail closed until readable. | multiple |
| required_safety_status_present | PASS | all restart/context documents describe the current safety status | all required safety markers present | Add only the missing current safety marker; do not change strategy or reports. | multiple |
| dangerous_authorization_text_absent | PASS | no text suggests trading, review, production effect, or promotion is allowed | no dangerous authorization text found | Remove or correct the authorization-looking text; keep trading_allowed=False and production_effect=none. | multiple |
| outdated_text_absent | PASS | no stale test counts, push status, or outdated BLOCK/WARN counts | no stale counts or old push state found | Refresh the stale text to the latest checkpoint baseline; audit does not auto-fix it. | multiple |
| safety_status_index_observe_present | PASS | safety index says overall_status=OBSERVE | overall_status=OBSERVE | Regenerate only the audit after restoring the local safety index source; do not authorize trading. | data/reports/paper_operation_safety_status_index.md |
