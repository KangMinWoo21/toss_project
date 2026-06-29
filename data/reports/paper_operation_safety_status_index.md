# Paper Operation Safety Status Index

## Do Not Trade / Status Index Only

This report is a status index only and does not authorize trading, broker submission, order execution, candidate promotion, or production readiness change.

- Overall status: `OBSERVE`.
- Trading allowed: `False`.
- Review allowed: `False`.
- Production effect: `none`.
- Recommended action: `keep_observing_no_tuning_no_promotion`.

## Safety Summary

- PASS rows: `22`.
- BLOCK rows: `0`.
- Scalper stale WARN is recorded separately from monthly paper review/OOS when present.

## Checks

| Check | Status | Expected | Observed | Source |
| --- | --- | --- | --- | --- |
| summary | PASS | overall_status=OBSERVE;trading_allowed=False;review_allowed=False;production_effect=none | overall_status=OBSERVE;trading_allowed=False;review_allowed=False;production_effect=none | derived |
| source_files_present | PASS | all source files readable | all source files readable | multiple |
| production_required_fields | PASS | production block columns present | present | data/reports/production_block_classification.csv |
| oos_guard_required_fields | PASS | OOS guard columns present | present | data/reports/protected_candidate_oos_review_eligibility_guard.csv |
| monthly_consistency_required_fields | PASS | monthly consistency columns present | present | data/reports/monthly_paper_operation_consistency_audit.csv |
| order_plan_required_fields | PASS | order plan columns present | present | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| review_packet_required_fields | PASS | review packet columns present | present | data/reports/monthly_paper_operation_review_packet.csv |
| trial_summary_required_fields | PASS | trial summary columns present | present | data/reports/monthly_candidate_research_trial_summary.csv |
| health_warn_required_fields | PASS | health warning columns present | present | data/reports/health_warn_classification.csv |
| production_block_retained | PASS | production remains BLOCK | block_rows=12; packet_status=BLOCK | data/reports/production_block_classification.csv |
| protected_candidate_paper_review | PASS | protected candidate PAPER_REVIEW | PAPER_REVIEW | data/reports/monthly_paper_operation_review_packet.csv |
| oos_review_eligibility_not_allowed | PASS | review_eligibility=REVIEW_NOT_ALLOWED | guard_status=PASS; review_eligibility=REVIEW_NOT_ALLOWED | data/reports/protected_candidate_oos_review_eligibility_guard.csv |
| oos_review_allowed_false | PASS | review_allowed=False | packet=False; guard=REVIEW_NOT_ALLOWED | data/reports/monthly_paper_operation_review_packet.csv |
| observed_days_below_required | PASS | observed days < required days | observed=0; required=15 | data/reports/monthly_paper_operation_review_packet.csv |
| remaining_days_positive | PASS | remaining days > 0 | remaining=15 | data/reports/monthly_paper_operation_review_packet.csv |
| monthly_consistency_pass_not_authorization | PASS | monthly consistency audit PASS but not authorization | rows=20; non_pass=0 | data/reports/monthly_paper_operation_consistency_audit.csv |
| actionable_rows_zero | PASS | actionable_rows=0 | packet=0; consistency=PASS | data/reports/monthly_paper_operation_review_packet.csv |
| all_order_rows_blocked | PASS | all order rows blocked and execution_allowed=False | rows=5; blocked=5 | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| promoted_candidates_zero | PASS | promoted candidates count=0 | trial=0; packet=0 | data/reports/monthly_candidate_research_trial_summary.csv |
| trading_allowed_false | PASS | trading_allowed=False | guard=False; packet_true=False | data/reports/protected_candidate_oos_review_eligibility_guard.csv |
| production_effect_none | PASS | production_effect=none | guard=none; consistency=PASS | data/reports/protected_candidate_oos_review_eligibility_guard.csv |
| scalper_warn_separated | PASS | scalper stale WARN separated from monthly paper review/OOS | {'warn_name': 'scalper_data', 'current_status': 'WARN', 'affects_monthly_rebalance': 'False', 'affects_protected_candidate_oos': 'False', 'affects_scalper_only': 'True', 'criticality': 'non_critical_for_monthly_paper_review_but_blocks_future_scalper_work', 'safe_remediation_available': 'not_in_this_loop_without_collector_restart_or_new_data', 'recommended_action': 'Keep WARN for scalper workflows; restart or inspect the cloud scalper collector before any scalper work.', 'reason': 'old scalper data: latest=005930_paper_scalp.csv; age_hours=478.33; mode=warn'} | data/reports/health_warn_classification.csv |
