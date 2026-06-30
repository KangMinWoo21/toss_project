# Formulaic Alpha Candidate Inventory

## Purpose

CP-05 creates an inventory structure for possible formulaic alpha families
without generating formula candidates. It is a paper-only design artifact that
uses the existing OHLCV-only schema, trial ledger schema, US quant research
inventory, and candidate trial ledger bootstrap.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `generated_candidate_count=0`.
- `evaluation_performed=False`.
- `training_allowed_now=False`.
- `direct_buy_alpha_allowed=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_schema_plan.md`
- `data/reports/candidate_trial_ledger_schema_plan.md`
- `data/reports/us_quant_math_model_research_inventory.md`
- `data/reports/candidate_trial_ledger.md`

## Inventory Summary

- Total inventory rows: `10`.
- Concrete formula candidates generated: `0`.
- Formula evaluations performed: `0`.
- Model training runs: `0`.
- Alpha sweeps performed: `0`.
- Rows allowed as direct buy alpha: `0`.

## Inventory Families

The inventory covers price momentum, mean reversion, volatility regime,
volume/liquidity, price-volume interaction, trend quality, drawdown recovery,
cross-sectional rank, low-activity manual-review overlays, and rejected external
text/event formula families. These are categories only; no formula strings,
formula hashes, feature hashes, scores, returns, or selections are created.

## Required Future Controls

- Every future generated formula must receive a candidate trial ledger row.
- `formula_hash` and `feature_hash` must be deterministic and auditable.
- Lookback metadata must include `lookback_window`, `lookback_min_periods`, and
  `lookback_unit`.
- Label metadata must include `label_horizon`, `label_horizon_days`,
  `purge_window_days`, and `embargo_window_days`.
- PIT controls must include feature visibility and usable-from timestamps.
- Duplicate/spam checks must run before any broad formula sweep.
- No model selection should occur without raw and effective trial counts.

## Recommendation

Do not generate formulaic alpha candidates until CP-06 explicitly bounds the
sample size and ledger behavior. Keep all external text/news/SNS/event inputs
outside this formula inventory and disabled by default as risk overlays only.
No formula family in this inventory is direct buy alpha.

## Completion Statement

CP-05 is complete as a no-generation inventory. It lists categories, allowed
inputs/operators, required hashes, trial-ledger links, and rejection reasons
while recording `generated_candidate_count=0`.
