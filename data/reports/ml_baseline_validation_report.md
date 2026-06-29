# ML Baseline Validation Report

## Do Not Trade / Paper-Only ML Validation

This report is paper-only. It performs pre-cutoff monthly validation diagnostics only, does not rerun OOS, does not fetch data, does not perform candidate comparison for promotion, does not allow candidate modification, does not call broker APIs, and does not authorize trading.

- Validation status: `paper_only_validation_complete`.
- Leakage check: `PASS` when recorded in the checks table.
- Trading allowed: `False`.
- Production effect: `none`.

## Checks

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | paper_only_validation_complete | paper_only_validation_complete | Phase 3 paper-only monthly walk-forward validation; no OOS rerun, fetch, candidate compare, candidate modification, promotion, broker call, or production change was performed. | derived |
| source_files_present | PASS | all required local sources readable | Phase 3 consumes only Phase 1 dataset sample and Phase 2 training report. | data/reports/ml_baseline_feature_label_sample.csv;data/reports/ml_baseline_model_training_report.csv |
| training_report_ready | PASS | True | Requires Phase 2 paper_only_baseline_trained. | data/reports/ml_baseline_model_training_report.csv |
| train_cutoff | PASS | 2026-06-18 | Cutoff inherited from Phase 2 training report. | data/reports/ml_baseline_model_training_report.csv |
| walk_forward_months | PASS | months=100 | Monthly expanding-window validation over pre-cutoff rows. | derived |
| leakage_check | PASS | True | max_label_end=2026-06-18; cutoff=2026-06-18 | derived |
| pit_universe_check | PASS | True | Dataset rows must carry post_cutoff_data_used_for_train=False. | data/reports/ml_baseline_feature_label_sample.csv |
| feature_availability_check | PASS | missing_rate=0.0538 | At least some baseline features must be available for validation. | data/reports/ml_baseline_feature_label_sample.csv |
| post_cutoff_data_used_for_validation | PASS | False | Post-cutoff rows are excluded before validation. | derived |
| oos_rerun | PASS | False | No OOS rerun is performed in Phase 3. | derived |
| validation_accuracy | PASS | 0.5335 | Average monthly validation accuracy; pre-cutoff diagnostic only. | derived |
| benchmark_relative_performance | PASS | model_return=0.0028;benchmark_return=0.0010;excess=0.0019 | Read-only benchmark comparison from validation rows; no candidate compare or promotion. | derived |
| drawdown | PASS | -0.5687 | Drawdown of monthly selected-return path. | derived |
| hit_rate | PASS | 0.4800 | Share of validation months with positive selected return. | derived |
| turnover | PASS | turnover=0.1481 | Average symbol-set turnover across validation months. | derived |
| label_distribution_validation | PASS | positive=37;negative=51 | Holdout validation labels remain pre-cutoff. | derived |
| protected_candidate_status | PASS | PAPER_REVIEW | Protected PAPER_REVIEW candidate remains unchanged. | data/reports/ml_baseline_model_training_report.csv |
| candidate_modified | PASS | False | Phase 3 may reference existing status only; no candidate is modified, tuned, or promoted. | derived |
| candidate_promotion | PASS | False | No promotion occurs in Phase 3. | derived |
| trading_allowed | PASS | False | Validation report only; no trading authorization. | derived |
| production_effect | PASS | none | Report has no production effect. | derived |
