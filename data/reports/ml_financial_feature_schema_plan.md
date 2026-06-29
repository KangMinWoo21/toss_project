# ML Financial Feature Schema Plan

## Do Not Trade / Schema Plan Only

This report is a paper-only OpenDART schema plan. It does not fetch data, call APIs, read API keys, train models, rerun OOS, compare candidates, create candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- `fetch_allowed_now=False` for every row.
- `training_allowed_now=False` for every row.
- `trading_allowed=False` for every row.
- `production_effect=none` for every row.
- Required PIT timestamps include `receipt_date`, `receipt_time`, `collected_at`, and `usable_from`.

## Schema Rows

| Feature Group | Candidate Features | Timestamp Fields | Lineage Rule | Next Safe Action |
| --- | --- | --- | --- | --- |
| financial_statement_metrics | sales;operating_income;net_income;debt_ratio;roe | receipt_date;receipt_time;collected_at;usable_from;report_period_end;fiscal_period | append_only_by_receipt_no_and_account; retain restatements and correction lineage; never overwrite prior visible rows | Review schema only; do not fetch OpenDART data until a future goal explicitly approves limited fetch. |
| market_valuation_metrics | per;pbr | receipt_date;receipt_time;collected_at;usable_from;report_period_end;market_date;price_visible_at | join valuation inputs only when both financial observation and market snapshot are visible by usable_from | Define valuation join audit before any feature is added to training. |
| disclosure_lineage | filing_event_type;correction_filing_flag;report_name;receipt_no | receipt_date;receipt_time;collected_at;usable_from;report_period_end;original_receipt_date;correction_receipt_date | link every correction filing to original receipt_no; preserve receipt_date and receipt_time for each visible version | Create deterministic correction lineage audit before limited fetch. |
| pit_controls | usable_from;source_revision;financial_observation_id;feature_valid_asof | receipt_date;receipt_time;collected_at;usable_from;report_period_end;feature_generated_at | feature rows become training-eligible only when usable_from <= feature_date and quality_status=PASS | Write PIT audit rules; keep fetch_allowed_now=False and training_allowed_now=False. |
