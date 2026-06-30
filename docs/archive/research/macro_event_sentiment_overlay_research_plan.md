# Macro/Event/Sentiment Overlay Research Plan

Status: research-only plan. Disabled by default. No production strategy behavior
changes are authorized by this document.

## Guardrails

- No live trading, no real order execution, and no Toss API use.
- Do not modify, tune, or promote the current `PAPER_REVIEW` candidate:
  `proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`.
- Do not use post-cutoff OOS data for optimization. Post-cutoff data is only
  observation evidence.
- Macro, event, news, and SNS inputs may be researched only as a risk overlay,
  not as direct buy alpha.
- Any future implementation must be opt-in, must default to disabled, and must
  leave production strategy output unchanged unless explicitly enabled in a
  separate paper-only experiment.
- This plan does not implement live data fetching or add dependencies.

## Prior Project Decisions

- Existing event/news work is a secondary overlay on top of price, liquidity,
  trend, and risk gates.
- News, SNS, and disclosure signals may be useful for vetoes, small weight
  adjustments, monitoring, or manual review, but not as standalone buy signals.
- The current candidate remains `PAPER_REVIEW`; documentation, OOS observation,
  or overlay research must not promote it.
- OOS observation must not be tuned. The observation period can explain risk,
  missed opportunities, and avoided losses, but cannot be used to pick better
  thresholds for the current candidate.

## Research References

- VIX / Cboe volatility: Cboe describes VIX as a leading measure of expected
  near-term volatility from S&P 500 option prices and a market volatility /
  investor sentiment barometer:
  https://www.cboe.com/tradable-products/vix
- Geopolitical Risk (GPR): Caldara and Iacoviello construct newspaper-count
  geopolitical risk indexes, hosted by Economic Policy Uncertainty:
  https://www.policyuncertainty.com/gpr.html
- Economic Policy Uncertainty (EPU): Baker, Bloom, and Davis maintain country
  and category policy-uncertainty indexes, including South Korea:
  https://www.policyuncertainty.com/
- Trading Costs: Frazzini, Israel, and Moskowitz, "Trading Costs", should be
  used as a reminder that any overlay reducing or increasing turnover must be
  evaluated net of realistic market-impact, fee, tax, and slippage assumptions.
- FinBERT: later-stage research only. ProsusAI FinBERT is a finance-domain BERT
  model for financial text sentiment, but it adds model and dependency risk and
  should not be introduced until simple timestamped event datasets are proven:
  https://github.com/ProsusAI/finBERT

## Open-Source Reference Options

- `pandas-datareader`: possible future FRED/macro access layer for research
  datasets such as rates, credit spreads, and macro indicators:
  https://pandas-datareader.readthedocs.io/en/latest/remote_data.html
- `yfinance`: possible research source for US index, ETF, and proxy data such
  as SPY, QQQ, IWM, VIX-linked products, USD/KRW proxies, or sector ETFs:
  https://github.com/ranaroussi/yfinance
- `pykrx`: existing KRX research data route for Korean market OHLCV and
  universe-related research:
  https://github.com/sharebook-kr/pykrx
- `OpenDartReader` / OpenDART: possible disclosure research source for Korean
  company events:
  https://github.com/FinanceData/OpenDartReader
- FinBERT: future financial text-sentiment research only; do not add it as a
  dependency in this planning step.

## Proposed Schemas

All tables are append-only research artifacts. Every row must include either
`usable_from` or `visible_at`; source timestamps must be preserved when known.

### `macro_observations`

| Column | Meaning |
| --- | --- |
| `observation_date` | Economic or market date the value describes. |
| `usable_from` | Earliest Korea time the row is allowed in a backtest. |
| `source` | `fred`, `cboe`, `yfinance`, `policyuncertainty`, or manual source id. |
| `series_id` | Source series id, such as `VIX`, `DGS10`, `BAMLH0A0HYM2`, `KOR_EPU`. |
| `region` | `US`, `KR`, `GLOBAL`, or other region code. |
| `value` | Numeric observed value. |
| `unit` | Percent, index level, spread bps, z-score, etc. |
| `transform` | `raw`, `diff_1d`, `z_252d`, `percentile_3y`, etc. |
| `risk_bucket` | `normal`, `caution`, `risk_off`, or `panic`. |
| `quality_flag` | `ok`, `late`, `revised`, `missing`, or `manual_review`. |
| `source_url` | Optional reference URL. |
| `created_at` | Local row creation timestamp. |

### `event_risk_observations`

| Column | Meaning |
| --- | --- |
| `event_date` | Date the event happened or was announced. |
| `visible_at` | Earliest timestamp the event was visible to the system. |
| `usable_from` | Earliest Korea time the row is allowed in a backtest. |
| `scope` | `market`, `sector`, `symbol`, `country`, or `global`. |
| `symbol` | Optional KRX symbol for company-specific events. |
| `source` | `opendart`, `manual_calendar`, `news`, `exchange_notice`, etc. |
| `event_type` | `earnings`, `disclosure`, `policy`, `macro_release`, `war`, etc. |
| `severity` | Integer 0-3 or controlled label. |
| `direction` | `negative`, `neutral`, `positive`, or `mixed`. |
| `risk_bucket` | `normal`, `caution`, `risk_off`, or `panic`. |
| `summary` | Short normalized description. |
| `source_id` | Filing id, article id, calendar id, or deterministic hash. |
| `created_at` | Local row creation timestamp. |

### `sentiment_observations`

| Column | Meaning |
| --- | --- |
| `published_at` | Source publication timestamp when available. |
| `collected_at` | Timestamp the row was collected locally. |
| `visible_at` | Earliest timestamp the source was visible to the system. |
| `usable_from` | Earliest Korea time the row is allowed in a backtest. |
| `source` | `google-news`, `gdelt`, `sns`, `dart`, or future source prefix. |
| `source_account` | Publisher, platform account, or disclosure source. |
| `scope` | `market`, `sector`, `symbol`, `country`, or `global`. |
| `symbol` | Optional KRX symbol. |
| `language` | `ko`, `en`, or other language code. |
| `sentiment_score` | Numeric score, preferably -1.0 to +1.0. |
| `importance_score` | Nonnegative capped importance or engagement weight. |
| `model_version` | `lexicon_v1`, `manual_v1`, future `finbert_*`, etc. |
| `risk_bucket` | `normal`, `caution`, `risk_off`, or `panic`. |
| `text_hash` | Hash of normalized title/text, not raw social content. |
| `created_at` | Local row creation timestamp. |

### `macro_overlay_regime_report`

| Column | Meaning |
| --- | --- |
| `as_of_date` | Strategy decision date being reviewed. |
| `usable_from` | Earliest Korea time report row is allowed. |
| `candidate_label` | Candidate under observation, if any. |
| `baseline_strategy` | Baseline strategy id. |
| `overlay_config` | `disabled`, `macro_only_v0`, `macro_event_v0`, etc. |
| `macro_risk_score` | `normal`, `caution`, `risk_off`, or `panic`. |
| `event_risk_score` | Same controlled label. |
| `sentiment_risk_score` | Same controlled label. |
| `combined_risk_score` | Same controlled label. |
| `recommended_action` | `observe_only`, `no_change`, `reduce_exposure_research`, etc. |
| `production_effect` | Must be `none` for this research plan. |
| `reason` | Short evidence summary. |
| `source_reports` | Semicolon-separated input report paths. |
| `created_at` | Local row creation timestamp. |

## Point-In-Time Rules

- Every row needs `usable_from` or `visible_at`; rows without one are invalid
  for backtests.
- No future leakage: a decision for date `D` can only use rows where
  `usable_from <= decision_timestamp`.
- US close data is usable only after the actual US close is known in Korea
  time. For daily bars, use a conservative next-Korea-business-morning
  `usable_from` unless a source-specific timestamp proves earlier availability.
- Macro releases, revisions, and delayed publications must preserve both the
  observed period and the release/visibility timestamp.
- News and SNS use `published_at`, `collected_at`, and `visible_at`; if
  `published_at` is missing, `collected_at` is the earliest allowed timestamp.
- Disclosure data uses filing receipt time when available; otherwise use a
  conservative next-session `usable_from`.
- Revised macro series must either store vintage/revision metadata or be
  excluded from optimization until point-in-time vintages are available.

## Simple Risk Score

The initial score is deliberately coarse and deterministic:

| Score | Meaning | Research-only overlay interpretation |
| --- | --- | --- |
| `normal` | No broad stress evidence. | No research adjustment. |
| `caution` | One mild stress signal or localized event risk. | Flag for review; no automatic action. |
| `risk_off` | Multiple stress signals or severe market/event deterioration. | Test exposure reduction in ablation only. |
| `panic` | Extreme volatility, systemic event risk, or severe sentiment shock. | Test maximum defensive overlay in ablation only. |

Example combination rule for later tests:

1. Map each input bucket to ordinal values: `normal=0`, `caution=1`,
   `risk_off=2`, `panic=3`.
2. Combined score is the maximum available ordinal.
3. If two or more independent inputs are at least `caution`, lift the combined
   score by one level, capped at `panic`.
4. Missing inputs do not reduce risk; they should add a data-quality note.

## Ablation Plan

All ablations are paper-only research runs and must use the same fixed baseline
and candidate parameters. Do not use post-cutoff OOS data to choose thresholds.

1. `baseline`: current approved baseline/candidate run with overlay disabled.
2. `baseline + macro`: macro-only risk score, no news/events/SNS.
3. `baseline + macro + event/news`: add timestamped disclosures, scheduled
   macro/event calendar, and news risk observations.
4. `baseline + macro + event/news + SNS`: add capped SNS sentiment after
   coverage and spam/duplication checks.

For every stage, compare gross return, excess return, max drawdown, turnover,
trade count, missed winners, avoided losses, and false risk-off episodes.

## Required Reports

### `macro_overlay_ablation_report.csv`

Minimum columns: `experiment_id`, `overlay_stage`, `start_date`, `end_date`,
`cutoff_date`, `uses_post_cutoff_for_optimization`, `gross_return_pct`,
`benchmark_return_pct`, `excess_return_pct`, `max_drawdown_pct`, `turnover`,
`trade_count`, `required_failures`, `status`, `reason`, `source_reports`.

`uses_post_cutoff_for_optimization` must be `False`.

### `avoided_loss_report.csv`

Minimum columns: `as_of_date`, `overlay_stage`, `risk_score`, `symbol`,
`baseline_action`, `overlay_action`, `next_return_pct`,
`avoided_loss_pct`, `source_reason`, `usable_from`.

Purpose: identify losses a research overlay would have reduced.

### `missed_winner_report.csv`

Minimum columns: `as_of_date`, `overlay_stage`, `risk_score`, `symbol`,
`baseline_action`, `overlay_action`, `next_return_pct`,
`missed_gain_pct`, `source_reason`, `usable_from`.

Purpose: expose opportunity cost and avoid building a one-sided loss-avoidance
narrative.

### `false_risk_off_report.csv`

Minimum columns: `as_of_date`, `overlay_stage`, `risk_score`,
`risk_off_reason`, `market_return_after_signal_pct`,
`candidate_return_after_signal_pct`, `false_risk_off_flag`, `usable_from`,
`source_reports`.

Purpose: quantify episodes where a defensive overlay would have reduced
exposure during favorable markets.

## Acceptance Criteria For Future Implementation

- Overlay remains disabled by default.
- Production strategy output is byte-for-byte unchanged when disabled.
- All inputs pass point-in-time visibility checks.
- Full validation includes the ablation reports above.
- Costs are reported net of fees, taxes, slippage, and turnover assumptions.
- No candidate promotion can cite this overlay unless a separate approval loop
  explicitly changes production readiness and OOS gates.
