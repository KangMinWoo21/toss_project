# Regime Sideways Manual Fundamental Fill Checklist

Status: research-only manual workflow. Do not fetch network data in this loop,
do not alter strategy behavior, and do not change candidate status.

## Scope

Use this checklist for the small manual sample todo:

`data/reports/regime_sideways_fundamental_manual_sample_todo.csv`

Fill only locally verified point-in-time evidence into a separate sample copy or
append-only rows. Do not invent missing values.

## PIT Dates

- `fiscal_period` is the accounting period described by the report.
- `receipt_date` is when the source filing or disclosure was received.
- `available_date` is when the normalized local row became available.
- `usable_from` is the first decision timestamp after both receipt and local
  availability.

Use `receipt_date`, `available_date`, and `usable_from` to decide whether a row
can be used. Never treat `fiscal_period` as an availability date.

## Missing Values

- Use `not_available` for unknown metrics.
- Leave values blank only while actively editing; normalize blanks to
  `not_available` before validation.
- Do not enter `0` unless the source value is actually zero.
- For flags, use `True` only with source evidence, `False` only after checking,
  and `not_available` when unchecked.

## Append-Only Corrections

If a filing is corrected, restated, or replaced, add a new row with its own
`source_report_id`, `receipt_date`, `available_date`, and `usable_from`.

Do not overwrite the earlier PIT row. The audit loader should choose the latest
row that was usable as of the audited decision date.

## No Future Leakage

Before using a row in the audit:

1. Confirm `usable_from` is present.
2. Confirm `receipt_date` or `available_date` is present.
3. Confirm `usable_from` is on or before the audited signal date.
4. Exclude later annual reports, corrections, or locally collected rows from
   earlier decisions.

Rows that fail these checks should be reported by validation and must not be
used silently.

## Manual Fill Steps

1. Pick one todo row.
2. Locate a local filing/disclosure copy or an already approved export.
3. Record source identity in `source` and `source_report_id`.
4. Fill PIT fields first: `fiscal_period`, `report_type`, `receipt_date`,
   `receipt_time` if known, `available_date`, and `usable_from`.
5. Fill only metrics directly supported by the source.
6. Keep all unsupported metrics as `not_available`.
7. Run the local sample validator and regenerate the research-only audit.
8. Review whether `explains_ranking_gap` changes from
   `insufficient_fundamental_data`; do not treat the result as strategy alpha.

