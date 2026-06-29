# Monthly Paper Operation Consistency Audit

## Do Not Trade / Review Only

This report is review-only. It does not authorize trading, broker submission, or order execution.

- Production BLOCK is retained.
- Protected candidate remains `PAPER_REVIEW`.
- OOS observation remains `review_allowed=False`.
- The actionable row count remains `0`.
- Broker submission remains forbidden.

## Summary

- Overall status: `PASS`.
- PASS rows: `20`.
- WARN rows: `0`.
- BLOCK rows: `0`.

## Checks

| Check | Status | Expected | Observed | Source |
| --- | --- | --- | --- | --- |
| source_files_present | PASS | all source files readable | all source files readable | multiple |
| review_packet_required_fields | PASS | required review packet columns present | present | data/reports/monthly_paper_operation_review_packet.csv |
| order_plan_required_fields | PASS | required order-plan columns present | present | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| markdown_audit_required_fields | PASS | required Markdown audit columns present | present | data/reports/monthly_order_plan_markdown_blocked_row_audit.csv |
| trading_allowed_false | PASS | trading_allowed=False for every packet row | rows=11; true_present=False | data/reports/monthly_paper_operation_review_packet.csv |
| actionable_rows_zero | PASS | actionable_rows=0 | actionable_rows=0 | data/reports/monthly_paper_operation_review_packet.csv |
| broker_submission_forbidden | PASS | broker_submission=forbidden | broker_submission=summary_text | data/reports/monthly_paper_operation_review_packet.csv |
| manual_review_required | PASS | manual_review_required=True | True;True;True;True;True;True;True;True;True;True;True | data/reports/monthly_paper_operation_review_packet.csv |
| production_status_block | PASS | production_status=BLOCK | status=BLOCK | data/reports/monthly_paper_operation_review_packet.csv |
| production_effect_none | PASS | production_effect=none | production_effect=none | data/reports/monthly_paper_operation_review_packet.csv |
| protected_candidate_paper_review | PASS | protected candidate status PAPER_REVIEW | status=PAPER_REVIEW | data/reports/monthly_paper_operation_review_packet.csv |
| oos_review_not_allowed | PASS | OOS review_allowed=False | review_allowed=False | data/reports/monthly_paper_operation_review_packet.csv |
| all_order_rows_blocked | PASS | all order-plan rows risk_status=BLOCKED | rows=5; blocked=5 | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| no_execution_allowed_true | PASS | no execution_allowed=True | 000270=False;016360=False;028050=False;088350=False;161390=False | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| execution_mode_blocked_only | PASS | execution_mode=blocked for every row | 000270=blocked;016360=blocked;028050=blocked;088350=blocked;161390=blocked | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| blocked_rows_visible | PASS | five blocked rows visible in Markdown and summary | csv_rows=5; symbols=000270,016360,028050,088350,161390 | data/reports/monthly_order_plan_blocked_rows_review_summary.md |
| required_symbols_present | PASS | 000270,016360,028050,088350,161390 | 000270,016360,028050,088350,161390 | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| hard_stop_reason_risk_status_block | PASS | risk_status_BLOCK visible in CSV and Markdown | 000270=risk_status_BLOCK;016360=risk_status_BLOCK;028050=risk_status_BLOCK;088350=risk_status_BLOCK;161390=risk_status_BLOCK | data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv |
| markdown_audit_row_coverage | PASS | blocked-row audit confirms 5/5 rows and risk_status_BLOCK | {'as_of_date': '2026-06-18', 'order_plan_csv': 'data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.csv', 'order_plan_markdown': 'data/reports/monthly_order_plan_neutral_loss_guard55_min_history244.md', 'csv_order_rows': '5', 'markdown_order_rows_visible': '5', 'csv_blocked_rows': '5', 'markdown_blocked_rows_visible': '5', 'all_blocked_rows_explained': 'True', 'missing_blocked_row_count': '0', 'risk_status_visible': 'True', 'risk_reasons_visible': 'True', 'execution_allowed_visible': 'False', 'execution_mode_visible': 'False', 'production_block_visible': 'True', 'trading_allowed_false_visible': 'False', 'manual_review_required_visible': 'False', 'broker_submission_forbidden_visible': 'False', 'recommendation': 'create_review_only_blocked_rows_summary', 'reason': 'Existing Markdown exposes all five blocked order rows and the shared risk_status_BLOCK hard-stop reason, but it does not visibly state execution_allowed=False, execution_mode=blocked, trading_allowed=False, manual review required, or broker submission forbidden.'} | data/reports/monthly_order_plan_markdown_blocked_row_audit.csv |
| do_not_trade_banner | PASS | Markdown output starts with Do Not Trade / Review Only | enforced by save_monthly_paper_operation_consistency_audit | generated_markdown |
