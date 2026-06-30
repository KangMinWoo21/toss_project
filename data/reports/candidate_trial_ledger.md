# Candidate Trial Ledger Bootstrap

## Safety Status

This is a ledger/bootstrap-only artifact built from existing local reports under
`data/reports` and the candidate trial ledger schema plan. It did not generate
formulaic alpha candidates, evaluate formulas, train a model, fetch data, call
APIs, scrape news or SNS, rerun OOS, rerun candidate comparison, create a
candidate, regenerate monthly plans, change strategy parameters, or modify the
protected `PAPER_REVIEW` candidate.

- Production remains `BLOCK`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- Deflated Sharpe was not calculated.
- The ledger is not used to promote or demote any candidate.

## Summary

| Metric | Value |
| --- | ---: |
| total ledger rows | 29 |
| baseline-related rows | 12 |
| protected `PAPER_REVIEW`-related rows | 6 |
| ML-related rows | 6 |
| comparison/report-only rows | 22 |
| rejected_or_blocked rows | 7 |
| formulaic_alpha rows | 8 |

- `data_snooping_risk_status`: `PLACEHOLDER_ONLY_DEF_SHARPE_NOT_CALCULATED`
- Reason: the ledger reserves `raw_trial_count` and `effective_trial_count`,
  but exact effective trial counts are not computable from the available local
  reports. The only exact sourced candidate count used here is
  `total_candidates_tested=5` from
  `data/reports/monthly_candidate_research_trial_summary.csv`.
- Missing evidence / `not_available` fields: source commands, attempted dates,
  formula hashes, model hashes, most candidate IDs for report-only artifacts,
  and effective trial counts are not available in the source reports and are
  intentionally left as `not_available`.

## Bootstrap Rules Applied

- No source commands or dates were invented.
- No performance metrics were inferred unless already present in a cited source
  report, and this ledger does not copy those metrics into decision fields.
- Schema/design/report-only artifacts are marked `design_only` or
  `report_only`.
- Blocked or rejected candidates are marked `rejected_or_blocked` only where
  the local candidate ledger, trial summary, protected guard, or comparison
  reports support that status.
- `raw_trial_count` and `effective_trial_count` remain placeholders except for
  the explicitly sourced `total_candidates_tested=5` summary row.
- No Deflated Sharpe calculation was performed.
- No production strategy output changes were made.
- CP-06 added 6 bounded formulaic alpha sample ledger rows marked
  `sample_only_no_eval`; no feature values, formula evaluations, model
  training, candidate creation, comparison, or order output were produced.

## Source Files

The CSV companion file is the source of truth:

`data/reports/candidate_trial_ledger.csv`

Primary evidence files include:

- `data/reports/candidate_trial_ledger_schema_plan.csv`
- `data/reports/candidate_trial_ledger_schema_plan.md`
- `data/reports/monthly_candidate_research_ledger.csv`
- `data/reports/monthly_candidate_research_trial_summary.csv`
- `data/reports/protected_candidate_oos_review_eligibility_guard.csv`
- `data/reports/ml_vs_original_model_comparison.csv`
- `data/reports/fee_tax_slippage_adjusted_expectancy_report.csv`
- `data/reports/month_symbol_concentration_report.csv`
- `data/reports/ml_v2_external_research_source_inventory.csv`
- `data/reports/us_quant_math_model_research_inventory.csv`
- `data/reports/formulaic_alpha_schema_plan.csv`

## Interpretation

This bootstrap ledger is an audit index over existing report families. It is
not a new comparison, not a candidate set, not a model-selection report, and not
permission to run a formula sweep. The protected `PAPER_REVIEW` candidate
remains unchanged and unpromoted.
