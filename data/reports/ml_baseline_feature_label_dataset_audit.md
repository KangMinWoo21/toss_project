# ML Baseline Feature/Label Dataset Audit

## Do Not Trade / Feature-Label Dataset Only

This report is paper-only and does not train models, rerun OOS, fetch data, compare candidates, generate candidates, tune strategy parameters, promote candidates, call broker APIs, or authorize trading.

- Dataset status: `ready_for_training_scaffold`.
- Training ran: `False`.
- Trading allowed: `False`.
- Production effect: `none`.

## Checks

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | ready_for_training_scaffold | ready_for_training_scaffold | Phase 1 baseline feature/label dataset audit only; no model training, OOS rerun, fetch, candidate compare, candidate generation, or strategy parameter change was performed. | derived |
| source_files_present | PASS | all required local sources readable | Required for deterministic local-only feature/label dataset construction. | multiple |
| train_cutoff | PASS | 2026-06-18 | Cutoff read from protected candidate ledger unless explicitly overridden. | data/reports/monthly_candidate_research_ledger.csv |
| available_symbol_count | PASS | 2184 | PASS data-quality symbols, falling back to local price files. | data/reports/monthly_validation_data_quality.csv |
| feature_row_count | PASS | 69915 | Rows with a feature date and next-month label ending on or before cutoff. | data/krx_expanded |
| label_row_count | PASS | 69915 | Label rows available for a future training scaffold; no training ran here. | data/krx_expanded |
| feature_candidates | PASS | return_1m;return_3m;return_6m;volatility_3m;volume_change_1m;price_vs_3m_sma;drawdown_3m | Baseline tabular technical feature candidates from local OHLCV only. | derived |
| feature_missing_rates | PASS | return_1m=0.0312;return_3m=0.0937;return_6m=0.1874;volatility_3m=0.0625;volume_change_1m=0.0355;price_vs_3m_sma=0.0625;drawdown_3m=0.0000 | Missing-rate denominator is feature/label dataset rows. | derived |
| label_distribution | PASS | positive=30350;negative=38885;flat=680 | Next-month return labels: positive/negative/flat. | derived |
| post_cutoff_data_used_for_train | PASS | False | max_feature_date=2026-05-29; max_label_end=2026-06-18 | derived |
| training_ran | PASS | False | Phase 1 creates/audits feature-label data only. | derived |
| pit_universe_available | PASS | True | Requires local PIT universe metadata and PASS universe coverage report. | data/krx_metadata/krx_universe_monthly.csv;data/reports/monthly_universe_price_coverage.csv |
| data_quality_exclusion_applied | WARN | True | excluded_symbols=355 | data/reports/data_quality_excluded_symbols.csv |
| protected_candidate_status | PASS | PAPER_REVIEW | Protected PAPER_REVIEW candidate is read-only and remains locked from tuning. | data/reports/monthly_candidate_research_ledger.csv |
| trading_allowed | PASS | False | Dataset audit only; no trading authorization. | derived |
| production_effect | PASS | none | Report has no production effect. | derived |
