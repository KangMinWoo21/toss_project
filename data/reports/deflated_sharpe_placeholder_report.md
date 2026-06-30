# Deflated Sharpe Placeholder Report

## Purpose

CP-01 reserves the data-snooping control fields needed before any serious ML v2
model selection or formulaic alpha sweep. This is a paper-only placeholder. It
does not calculate Deflated Sharpe, does not recompute returns, and does not use
the placeholder to select, promote, demote, or compare any candidate.

## Scope And Safety

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- No formula generation, formula evaluation, model training, model selection,
  OOS rerun, candidate comparison rerun, candidate creation, monthly plan
  regeneration, strategy parameter change, protected candidate change, broker
  work, data fetch, API call, or news/SNS scrape was performed.

## Required Placeholder Fields

| Field | Status | Notes |
| --- | --- | --- |
| `raw_sharpe` | `reserved_missing` | Future value must come from an approved validation report. |
| `skew` | `reserved_missing` | No return distribution was loaded or recalculated here. |
| `kurtosis` | `reserved_missing` | No statistic is inferred from summaries. |
| `sample_length` | `reserved_missing` | Future source must identify the exact validation sample. |
| `raw_trial_count` | `placeholder` | Existing bootstrap ledger is not sufficient for a complete project-wide count. |
| `effective_trial_count` | `placeholder` | Requires a future dependency/correlation adjustment method. |
| `deflated_sharpe_adjusted_score` | `placeholder_only` | Explicitly not calculated in this checkpoint. |

## Existing Local Evidence Used

- `data/reports/candidate_trial_ledger.csv`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/candidate_trial_ledger_schema_plan.csv`
- `data/reports/candidate_trial_ledger_schema_plan.md`

The local bootstrap ledger provides a starting inventory of report/trial
families and preserves `raw_trial_count` and `effective_trial_count`
placeholders. It does not provide enough evidence to calculate Deflated Sharpe
or to compute a reliable effective trial count.

## Recommendation

- Add trial-count collection before any broad alpha sweep.
- Add a documented method for `effective_trial_count` before model selection.
- Use purged/embargo validation design before serious ML v2 training.
- Keep this placeholder disabled for selection until all required inputs are
  available from approved future reports.
- Keep all outputs paper-only and `production_effect=none`.

## Completion Statement

CP-01 is complete as a placeholder/report-only checkpoint. The adjusted score is
reserved but not calculated, and it is not usable for model selection.
