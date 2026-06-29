# Regime Sideways Fundamental Sample Fill Guide

Status: research-only local fill guide. It does not authorize OpenDART fetches,
network access, strategy changes, candidate creation, candidate promotion, or
live trading.

## Input File

Fill local point-in-time rows in:

`data/reports/regime_sideways_fundamental_sample_input_template.csv`

The template has one row per current `regime_sideways` audit symbol/group. Keep
rows append-only: if a source filing is corrected, add a new row with the new
`source_report_id`, `receipt_date`, `available_date`, and `usable_from` instead
of overwriting the earlier PIT row.

## `usable_from`

`usable_from` is the first timestamp at which a strategy decision or audit could
legally have used the row.

- If `receipt_date`, `receipt_time`, and local normalization time are known, set
  `usable_from` to the first decision timestamp after both source receipt and
  local availability.
- If `receipt_time` is missing, use a conservative next-session timestamp.
- If the row was only collected later, do not backdate `usable_from` before the
  evidence was locally available.
- A row with blank or `not_available` `usable_from` is invalid and must not be
  used by the audit.

## `receipt_date` vs `fiscal_period`

`fiscal_period` is the accounting period being described, such as `2024Q3` or
`2023FY`. It is not the date when the market knew the data.

`receipt_date` is when the source disclosure or filing was received. The audit
must be governed by `receipt_date`, `receipt_time`, `available_date`, and
`usable_from`, not by the older fiscal period label.

Example: a `2024FY` annual report may describe 2024, but if it was received in
March 2025 it cannot explain January or February 2025 decisions unless a
separate preliminary row existed and was usable earlier.

## Missing Values

Use blank or `not_available` for unknown metrics. Do not use `0` unless the
source value is actually zero.

For flags:

- Use `True` only when the source evidence supports the flag.
- Use `False` only when the source evidence is checked and no flag is present.
- Use `not_available` when the evidence has not been checked.

For ratios or growth metrics, keep source-consistent units and document unusual
cases in `source_report_id` or an adjacent research note if needed.

## Avoiding Future Leakage

For each audit decision date, only use rows where `usable_from` is on or before
that decision date. Do not use later filings, later corrections, later
restatements, or later locally collected data to explain earlier selection or
ranking decisions.

Target fiscal periods for this audit should emphasize data usable before the
`regime_sideways` window and its recovery subwindow:

- `2023FY`
- `2024Q1`
- `2024Q2`
- `2024Q3`
- `2024Q4` only when the filing, preliminary disclosure, or corrected row has a
  documented `usable_from` before the signal date being audited

## Local-Only Workflow

1. Resolve `corp_code` only in a future approved local or network-fetch loop.
2. Fill sample rows only from source evidence that has PIT receipt and
   availability fields.
3. Leave unverified fields blank or `not_available`.
4. Run the local validator/audit builder.
5. Treat the output as explanatory research only. It must not change orders,
   weights, target symbols, candidate status, or production readiness.

