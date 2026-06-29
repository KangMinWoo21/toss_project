# News, SNS, and Disclosure Event Integration

The project can now use weighted event data in monthly allocation, backtests,
and validation. The event layer is intentionally a secondary overlay on top of
price, liquidity, trend, and risk gates.

## Event CSV Format

```csv
date,symbol,source,title,sentiment_score,importance_score
2026-01-08,005930,news,negative chip cycle note,-0.9,1.0
2026-01-11,005930,sns,positive product momentum,0.7,0.8
```

Fields:

- `date`: event date in `YYYY-MM-DD`
- `symbol`: stock code or ticker
- `source`: source family or source prefix, for example `news`, `sns`,
  `google-news:publisher`, or `dart:company`
- `sentiment_score`: recommended range `-1.0` to `+1.0`
- `importance_score`: nonnegative event importance

The base daily score is an importance-weighted average:

```text
sum(sentiment_score * importance_score * source_weight)
/ sum(importance_score * source_weight)
```

## Source Weights

Source weights let the same event file combine fast but noisy sources with
slower but more reliable sources.

Examples:

```text
news=1.0,sns=0.25,dart=0.5
google-news=1.0,dart=0.5
```

The loader supports exact source names and prefixes before `:`.

## Building a Combined Event File

Google News and GDELT downloads already write the standard event format. SNS or
community exports can be imported from a CSV with columns such as `date`,
`timestamp`, `symbol`, `platform`, `text`, `likes`, `reposts`, and `comments`.

```bash
python -m backtester import-social-events \
  --input data/raw/sns_posts.csv \
  --symbol 005930 \
  --source x \
  --output data/events/005930_sns.csv

python -m backtester merge-events \
  --input data/events/005930_google_news.csv \
  --input data/events/005930_sns.csv \
  --input data/events/krx15_dart_2018_2026.csv \
  --output data/events/combined_events.csv
```

For SNS rows, engagement is converted into `importance_score` with a capped
log-scale weight. This makes a high-engagement post matter more than a random
low-engagement post, without letting viral noise dominate the model.

## Monthly Strategy Usage

Example validation command:

```bash
python -m backtester monthly-validate \
  --data-dir data/krx_expanded \
  --start 2024-01-01 \
  --end 2026-06-18 \
  --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv \
  --events data/events/combined_events.csv \
  --event-source-weights google-news=1.0,sns=0.25,dart=0.5 \
  --event-lookback-days 20 \
  --min-entry-event-score -0.4 \
  --event-weight 0.25
```

How it is applied:

1. Momentum and liquidity ranking creates candidate targets.
2. Candidates with event score below `--min-entry-event-score` are removed.
3. Remaining candidates receive a target-weight multiplier of
   `1 + event_score * --event-weight`.
4. Multipliers are clipped by internal bounds, and position caps still apply.

## Current Empirical Finding

Local test with `data/events/krx15_dart_2018_2026.csv`:

- Full-period excess return improved slightly.
- Last walk-forward window was unchanged.
- Max drawdown was unchanged.

Interpretation: DART event data is useful as a risk/context overlay, but the
current 15-symbol DART dataset is not broad enough to fix the production
readiness WARN by itself. Broader news/SNS coverage would be needed before this
overlay can be treated as a material alpha source.

## Practical Rule

Use event data as:

- a veto for clearly negative recent events,
- a small weight adjustment for positive/negative sentiment,
- a monitoring input for manual review.

Do not use event data as:

- a standalone buy signal,
- a way to override failed walk-forward validation,
- a reason to bypass `production-check --strict`.
