# ML v2 Fixed-Spec Paper-Only Training Report

## Do Not Trade / Paper-Only ML v2

This report runs one fixed-spec ML v2 experiment only after the POST-21 readiness gate. It does not evaluate multiple models, tune hyperparameters, rank formulas, create candidates, rerun OOS, rerun candidate comparison, write a production artifact, call broker APIs, submit orders, or authorize trading.

- Training status: `paper_only_ml_v2_fixed_spec_trained`.
- Validation status: `paper_only_ml_v2_fixed_spec_validated`.
- Model type: `logistic_regression_sgd_fixed_v2`.
- External features used: `False`.
- Formula selection used: `False`.
- Model selection used: `False`.
- Hyperparameter sweep used: `False`.
- Candidate creation: `False`.
- Trading allowed: `False`.
- Production effect: `none`.

## Training Rows

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | paper_only_ml_v2_fixed_spec_trained | paper_only_ml_v2_fixed_spec_trained | One fixed-spec ML v2 paper-only model was trained; no selection, tuning, candidate, broker, order, or production work occurred. | derived |
| source_files_present | PASS | all required local sources readable | Uses existing local reports only. | data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv;data/reports/ml_baseline_feature_label_sample.csv;data/reports/ml_v2_fixed_spec_training_readiness_gate.csv |
| readiness_gate | PASS | ALLOW_PAPER_ONLY_TRAINING | Training requires the POST-21 fixed-spec readiness gate. | data/reports/ml_v2_fixed_spec_training_readiness_gate.csv |
| model_type | PASS | logistic_regression_sgd_fixed_v2 | Single fixed model type; no model comparison. | data/reports/ml_v2_fixed_spec_training_protocol.csv |
| fixed_feature_set | PASS | formula_hash_count=6 | Uses the fixed Stage 1 formulaic OHLCV feature set only. | data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv |
| joined_row_count | PASS | 98 | Rows joined by symbol and feature_date from local labels only. | data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv;data/reports/ml_baseline_feature_label_sample.csv |
| train_row_count | PASS | 74 | Chronological training split before validation and embargo date groups. | derived |
| validation_row_count | PASS | 20 | Chronological validation split; not an OOS rerun. | derived |
| embargo_date_groups | PASS | 2025-12-30 | One date group before validation is excluded from training. | derived |
| label_distribution_train | PASS | positive=31;negative=43 | Binary positive/negative labels from existing local baseline label file. | data/reports/ml_baseline_feature_label_sample.csv |
| train_accuracy | PASS | 0.6486 | In-sample diagnostic only; not a production or candidate-selection claim. | derived |
| model_artifact_written | PASS | False | The trained weights are not written as a model artifact. | derived |
| candidate_creation | PASS | False | This run creates no candidate_id. | derived |
| trading_allowed | PASS | False | Paper-only research report. | derived |
| production_effect | PASS | none | No production effect. | derived |

## Validation Rows

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | paper_only_ml_v2_fixed_spec_validated | paper_only_ml_v2_fixed_spec_validated | Fixed-spec ML v2 validation is pre-cutoff, local-only, and paper-only. | derived |
| split_policy | PASS | date_group_chronological_train_then_validation_with_purge_embargo_v1 | Fixed split policy from POST-21; no random row split. | data/reports/ml_v2_fixed_spec_training_protocol.csv |
| validation_accuracy | PASS | 0.5500 | Pre-cutoff validation diagnostic only; no OOS rerun. | derived |
| label_distribution_validation | PASS | positive=8;negative=12 | Validation labels are pre-cutoff only. | data/reports/ml_baseline_feature_label_sample.csv |
| formula_selection_used | PASS | False | All fixed feature hashes are used together; no formula ranking. | derived |
| model_selection_used | PASS | False | Only the fixed logistic SGD model is used. | derived |
| hyperparameter_sweep_used | PASS | False | No hyperparameter sweep or threshold tuning. | derived |
| oos_rerun | PASS | False | Validation is not an OOS rerun. | derived |
| candidate_comparison_rerun | PASS | False | No candidate comparison is run. | derived |
| candidate_promotion | PASS | False | No candidate promotion occurs. | derived |
| broker_submission | PASS | False | No broker submission. | derived |
| order_execution | PASS | False | No order execution. | derived |
| trading_allowed | PASS | False | Validation report only. | derived |
| production_effect | PASS | none | No production effect. | derived |
