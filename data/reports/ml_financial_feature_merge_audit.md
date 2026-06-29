# ML Financial Feature Merge Audit

## Do Not Trade / Merge Audit Only

This report audits whether the limited financial sample can be technically merged with the baseline ML dataset. It does not train models, rerun OOS, fetch data, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- Merge audit status: `financial_feature_merge_audit_complete`.
- Join coverage: `0/5`.
- Missing rate: `1.0000`.
- Leakage check: `PASS`.
- Feature added to training: `False`.
- Training allowed now: `False`.
- Trading allowed: `False`.
- Production effect: `none`.

## Checks

| Metric | Status | Value | Reason | Source |
| --- | --- | --- | --- | --- |
| summary | financial_feature_merge_audit_complete | financial_feature_merge_audit_complete | Phase 7 merge audit only; no model training, OOS rerun, fetch, candidate compare, candidate generation, strategy parameter change, or production change was performed. | derived |
| source_files_present | PASS | all required local sources readable | Requires Phase 1 dataset sample, Phase 6 observations, and Phase 6 PIT audit. | data/reports/ml_baseline_feature_label_sample.csv;data/reports/ml_financial_observations_sample.csv;data/reports/ml_financial_pit_audit.csv |
| join_coverage | WARN | 0/5 | Distinct baseline dataset symbols with at least one limited financial observation. | data/reports/ml_baseline_feature_label_sample.csv;data/reports/ml_financial_observations_sample.csv |
| missing_rate | WARN | 1.0000 | Symbol-level financial observation missing rate against the baseline sample. | derived |
| leakage_check | PASS | pit_leakage_pass=True; observation_safe=True; dataset_safe=True | Financial features are audited for merge readiness only and are not added to training. | data/reports/ml_financial_pit_audit.csv;data/reports/ml_financial_observations_sample.csv;data/reports/ml_baseline_feature_label_sample.csv |
| post_cutoff_data_used_for_train | PASS | False | No financial feature row is used for train in Phase 7. | derived |
| feature_added_to_training | PASS | False | Phase 7 does not alter the baseline model dataset or training inputs. | derived |
| training_allowed_now | PASS | False | Limited financial sample remains merge-audited only. | derived |
| trading_allowed | PASS | False | Merge audit only; no trading authorization. | derived |
| protected_candidate_status | PASS | PAPER_REVIEW unchanged | Protected candidate is not read for tuning, modified, promoted, or replaced. | derived |
| protected_candidate_unchanged | PASS | True | Protected PAPER_REVIEW candidate remains unchanged. | derived |
| production_effect | PASS | none | Report has no production effect. | derived |
