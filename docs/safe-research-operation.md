# Safe Research Operation Workflow

This project is a research and paper-operation toolkit. It must not place real
orders from the CLI. Monthly workflows create order plans for review only.

## Safety Defaults

- `PRODUCTION_TRADING_ENABLED` is disabled by default.
- A `monthly-plan` order row is blocked unless risk checks pass and production
  trading is explicitly enabled.
- No tests should call real Toss Open API endpoints or print `.env` secrets.

## Data Quality

Run candle freshness and OHLCV checks before trusting backtests:

```powershell
python -m backtester data-check --path data/krx_expanded --max-stale-days 7
```

Write a reviewable exclusion list for blocked symbols without modifying raw data:

```powershell
python -m backtester data-check --path data/krx_expanded --max-stale-days 7 --exclude-output data/reports/data_quality_excluded_symbols.csv
```

Use `--data-quality-path` with `production-check` to include raw dataset quality
in readiness:

```powershell
python -m backtester production-check --strict --data-quality-path data/krx_expanded
```

## Monthly Plan Review

Generate a paper order plan, then inspect the CSV and Markdown summary:

```powershell
python -m backtester monthly-plan --data-dir data/krx_expanded --as-of 2026-06-20 --exclude-symbols data/reports/data_quality_excluded_symbols.csv
```

Every generated order row includes `risk_status` and `risk_reasons`. Treat
`BLOCKED` rows as non-actionable.

## Event Data Timing

Event CSVs may include `event_date` and `available_date`. Strategy decisions use
only `available_date <= as_of_date`. Legacy rows with only `date` are accepted
as available on that date and produce a warning. Rows with no usable date are
excluded.

## Cloud Collection

Cloud scripts may collect scalper data and run monthly paper plans. They should
not deploy or call any live order executor. Keep `production-check --strict` as
the final gate before any future manually reviewed action.
