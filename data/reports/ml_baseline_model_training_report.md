# ML Baseline Model Training Report

## Do Not Trade / Paper-Only Baseline Training

This report is paper-only. It uses only the Phase 1 local feature/label dataset, does not rerun OOS, does not fetch data, does not compare or promote candidates, does not write a production artifact, does not call broker APIs, and does not authorize trading.

- Training status: `paper_only_baseline_trained`.
- Model type: `logistic_regression_sgd`.
- OOS data used: `False`.
- Trading allowed: `False`.
- Production effect: `none`.

## Checks

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | paper_only_baseline_trained | paper_only_baseline_trained | Phase 2 paper-only baseline model training scaffold; no OOS rerun, fetch, candidate compare, candidate promotion, broker call, or production linkage was performed. | derived |
| source_files_present | PASS | all required local sources readable | Phase 2 consumes the Phase 1 feature/label dataset and audit only. | data/reports/ml_baseline_feature_label_sample.csv;data/reports/ml_baseline_feature_label_dataset_audit.csv |
| model_type | PASS | logistic_regression_sgd | Simplest paper-only baseline implemented with standard-library deterministic SGD. | derived |
| dataset_ready | PASS | True | Requires Phase 1 ready_for_training_scaffold. | data/reports/ml_baseline_feature_label_dataset_audit.csv |
| train_cutoff | PASS | 2026-06-18 | Cutoff inherited from Phase 1 audit. | data/reports/ml_baseline_feature_label_dataset_audit.csv |
| train_row_count | PASS | 111 | Training split uses only pre-cutoff rows. | data/reports/ml_baseline_feature_label_sample.csv |
| validation_row_count | PASS | 88 | Validation split uses only pre-cutoff rows. | data/reports/ml_baseline_feature_label_sample.csv |
| train_validation_split_cutoff_safe | PASS | True | max_train_label_end=2024-09-30; max_validation_label_end=2026-06-18 | derived |
| post_cutoff_data_used_for_train | PASS | False | Rows after cutoff are excluded before train/validation split. | derived |
| oos_data_used | PASS | False | Post-cutoff OOS data is not used in Phase 2. | derived |
| label_distribution_train | PASS | positive=50;negative=61 | Binary positive/negative labels used for baseline scaffold. | derived |
| label_distribution_validation | PASS | positive=37;negative=51 | Validation labels are pre-cutoff only. | derived |
| train_accuracy | PASS | 0.5946 | In-sample diagnostic only; not a production claim. | derived |
| validation_accuracy | PASS | 0.5909 | Pre-cutoff validation diagnostic only; no OOS review performed. | derived |
| model_artifact_written | PASS | False | No model artifact is written in this scaffold loop. | derived |
| production_artifact_linked | PASS | False | No model artifact is connected to production. | derived |
| protected_candidate_status | PASS | PAPER_REVIEW | Protected PAPER_REVIEW candidate remains unchanged. | data/reports/ml_baseline_feature_label_dataset_audit.csv |
| candidate_promotion | PASS | False | Phase 2 cannot promote or tune candidates. | derived |
| trading_allowed | PASS | False | Training report only; no trading authorization. | derived |
| production_effect | PASS | none | Report has no production effect. | derived |
