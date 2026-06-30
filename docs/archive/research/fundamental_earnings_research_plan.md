# Fundamental/Earnings Research Plan

Status: research-only plan. Disabled by default. No production strategy behavior
changes are authorized by this document.

## Guardrails

- No live trading, no real order execution, and no Toss API use.
- Do not modify, tune, or promote the current `PAPER_REVIEW` candidate:
  `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`.
- Do not create new strategy candidates from this plan.
- Do not use post-cutoff OOS data for optimization or threshold selection.
- Do not fetch live earnings, disclosure, or statement data in this planning
  step.
- Do not add external dependencies.
- Any future implementation must be opt-in, must default to disabled, and must
  leave production strategy output unchanged while disabled.

## Initial Research Rules

- Earnings calendars are event-risk filters. Their first use is to block new
  entries near earnings, force review-only handling around earnings, and flag
  adverse disclosures.
- Financial statements are universe and fundamental-quality filters. Their
  first use is to identify fragile or low-quality symbols before selection.
- Earnings and fundamentals are not direct buy alpha initially. They may explain
  risk, exclusions, missed winners, and avoided losses, but they must not create
  standalone buy signals.
- The current protected candidate is not changed by this plan.
- Post-cutoff OOS observations may be used for monitoring notes only, not for
  tuning metric thresholds, event windows, or quality cutoffs.

## Point-In-Time Requirements

All rows used by backtests or audits must preserve the point-in-time evidence
needed to prevent leakage:

- `fiscal_period`: period the filing or statement describes.
- `report_type`: annual, quarterly, revision, preliminary, earnings release,
  guidance, correction, or other controlled type.
- `receipt_date`: source receipt date.
- `receipt_time`: source receipt time when available.
- `available_date`: first local date the normalized row exists.
- `usable_from`: earliest timestamp the row may be used by a decision.
- `source`: DART, exchange disclosure, manual calendar, vendor export, or other
  controlled source id.
- `source_report_id`: filing id, receipt id, event id, or deterministic source
  hash.

Rows missing `usable_from` are invalid for backtests. If receipt time is missing,
use a conservative next-session `usable_from` until a source-specific rule is
documented.

## Proposed Schemas

All schemas are append-only research artifacts. They are not production strategy
inputs until a separate approval loop explicitly wires them into paper-only
experiments.

### `earnings_event_observations`

| Column | Meaning |
| --- | --- |
| `symbol` | KRX symbol. |
| `company_name` | Source company name when available. |
| `event_date` | Expected or actual earnings/disclosure date. |
| `event_time` | Known event time, or blank if unknown. |
| `event_type` | `scheduled_earnings`, `preliminary_result`, `final_report`, `revision`, `guidance`, `adverse_disclosure`, etc. |
| `fiscal_period` | Fiscal period being reported. |
| `report_type` | Annual, quarterly, preliminary, correction, guidance, etc. |
| `receipt_date` | Filing or event receipt date. |
| `receipt_time` | Filing or event receipt time when available. |
| `available_date` | First date the normalized row is locally available. |
| `usable_from` | Earliest timestamp usable by a decision. |
| `source` | Source id such as `dart`, `exchange_disclosure`, or `manual_calendar`. |
| `source_report_id` | Source filing/event id or deterministic hash. |
| `event_risk_bucket` | `normal`, `review_only`, `block_new_entries`, or `adverse`. |
| `adverse_disclosure_flag` | Boolean flag for adverse or corrective disclosure. |
| `quality_flag` | `ok`, `missing_time`, `late`, `revised`, or `manual_review`. |
| `created_at` | Local row creation timestamp. |

### `fundamental_observations`

| Column | Meaning |
| --- | --- |
| `symbol` | KRX symbol. |
| `company_name` | Source company name when available. |
| `fiscal_period` | Fiscal period the row describes. |
| `report_type` | Annual, quarterly, preliminary, correction, etc. |
| `receipt_date` | Filing receipt date. |
| `receipt_time` | Filing receipt time when available. |
| `available_date` | First date the normalized row is locally available. |
| `usable_from` | Earliest timestamp usable by a decision. |
| `source` | Source id. |
| `source_report_id` | Filing id, receipt id, or deterministic source hash. |
| `revenue_growth_yoy` | Year-over-year revenue growth. |
| `operating_profit_growth_yoy` | Year-over-year operating profit growth. |
| `net_income_growth_yoy` | Year-over-year net income growth. |
| `operating_margin` | Operating profit divided by revenue. |
| `debt_ratio` | Debt ratio from source statements. |
| `current_ratio` | Current assets divided by current liabilities. |
| `roe` | Return on equity. |
| `operating_cashflow` | Operating cash flow. |
| `free_cashflow_proxy` | Operating cash flow minus capex where available. |
| `capital_impairment_flag` | Boolean flag for capital impairment/erosion. |
| `capital_increase_or_cb_flag` | Boolean flag for capital increase or convertible-bond financing risk. |
| `quality_flag` | `ok`, `partial`, `restated`, `missing`, or `manual_review`. |
| `created_at` | Local row creation timestamp. |

### `fundamental_quality_report`

| Column | Meaning |
| --- | --- |
| `as_of_date` | Strategy decision or audit date. |
| `usable_from` | Earliest timestamp usable by a decision. |
| `symbol` | KRX symbol. |
| `fiscal_period` | Latest fiscal period used. |
| `report_type` | Source report type used. |
| `receipt_date` | Source receipt date. |
| `receipt_time` | Source receipt time when available. |
| `available_date` | First normalized availability date. |
| `source` | Source id. |
| `source_report_id` | Filing id, receipt id, or deterministic hash. |
| `fundamental_quality_bucket` | `pass`, `watch`, `exclude_research`, or `insufficient_data`. |
| `metric_flags` | Semicolon-separated metric issues. |
| `used_metrics` | Semicolon-separated metrics present in the row. |
| `missing_metrics` | Semicolon-separated unavailable metrics. |
| `production_effect` | Must be `none` for this research plan. |
| `reason` | Short explanation. |
| `created_at` | Local row creation timestamp. |

### `earnings_event_risk_report`

| Column | Meaning |
| --- | --- |
| `as_of_date` | Strategy decision or audit date. |
| `usable_from` | Earliest timestamp usable by a decision. |
| `symbol` | KRX symbol. |
| `event_date` | Event date being evaluated. |
| `event_type` | Earnings or disclosure event type. |
| `fiscal_period` | Fiscal period involved. |
| `report_type` | Source report type. |
| `receipt_date` | Source receipt date. |
| `receipt_time` | Source receipt time when available. |
| `available_date` | First normalized availability date. |
| `source` | Source id. |
| `source_report_id` | Filing id, receipt id, event id, or deterministic hash. |
| `event_risk_action` | `no_change`, `block_new_entry_research`, `review_only`, or `adverse_disclosure_review`. |
| `days_to_event` | Trading or calendar days to the event, clearly labeled by report metadata. |
| `days_since_event` | Trading or calendar days since the event. |
| `adverse_disclosure_flag` | Boolean adverse disclosure flag. |
| `production_effect` | Must be `none` for this research plan. |
| `reason` | Short explanation. |
| `created_at` | Local row creation timestamp. |

## Initial Metrics

The first fundamental metric set is deliberately simple and auditable:

- `revenue_growth_yoy`
- `operating_profit_growth_yoy`
- `net_income_growth_yoy`
- `operating_margin`
- `debt_ratio`
- `current_ratio`
- `roe`
- `operating_cashflow`
- `free_cashflow_proxy`
- `capital_impairment_flag`
- `capital_increase_or_cb_flag`

Metric rows must retain raw-source lineage and should distinguish missing data
from valid zero values. Restatements and corrections must not overwrite prior
point-in-time rows.

## Event-Risk Rules

Initial event-risk rules are research-only:

1. Block new entries near earnings when a symbol has an upcoming scheduled or
   uncertain earnings/disclosure event inside a documented event window.
2. Mark existing positions or candidates as review-only around earnings when
   receipt timing, guidance, or event severity is uncertain.
3. Raise an adverse disclosure flag for corrective filings, capital impairment,
   large loss announcements, audit concerns, capital increases, convertible-bond
   risk, or other source-labeled adverse events.

These rules may only produce reports at this stage. They must not alter orders,
portfolio weights, target symbols, or candidate status.

## Ablation Plan

All ablations are pre-cutoff, paper-only research diagnostics unless a future
approval explicitly expands the scope. Parameters for the baseline and protected
candidate remain fixed.

1. `baseline`: current strategy reports with earnings/fundamentals disabled.
2. `baseline + earnings_event_risk`: add event-risk reports only; measure
   blocked entries, review-only flags, missed winners, avoided losses, turnover,
   and drawdown effect.
3. `baseline + fundamental_quality`: add fundamental-quality reports only;
   measure universe exclusions, data coverage, missed winners, avoided losses,
   turnover, and drawdown effect.
4. `baseline + earnings + fundamental`: combine both report layers and compare
   net effect against the separate ablations.

Every ablation report must include `uses_post_cutoff_for_optimization=False`,
`production_effect=none`, fixed scenario windows, gross return, excess return,
max drawdown, trade count, turnover, missed winners, avoided losses, and false
exclusions.

## `regime_sideways` Audit

The first scenario audit should focus on explanation, not optimization:

1. Compare the 9 liquid, data-quality-passing, 252-day eligible missed recovery
   names from `regime_sideways_252safe_missed_recovery_ranking_diagnostic.csv`.
2. Compare the five min-history244 contribution names from
   `regime_sideways_min_history244_contribution_audit.csv`.
3. Check whether fundamental quality, adverse events, earnings timing, or
   financing/capital flags explain recovery participation or missed selection.
4. Separate explanations into:
   - fundamental_quality_supported_recovery
   - event_risk_explains_exclusion
   - fundamentals_do_not_explain_recovery
   - insufficient_pit_fundamental_data
   - mixed
5. Do not tune selection ranks, history gates, event windows, or fundamental
   thresholds from this audit.

## Acceptance Criteria For Future Implementation

- Earnings/fundamental research remains disabled by default.
- Production strategy output is unchanged while disabled.
- All rows include point-in-time receipt and usability fields.
- Missing receipt times use conservative usability rules.
- Reports expose both avoided losses and missed winners.
- No candidate can cite this research for promotion without a separate approval
  loop, clean paper-only validation, post-cutoff observation discipline, and
  production-readiness changes.
