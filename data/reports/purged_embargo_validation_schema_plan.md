# Purged / Embargo Validation Schema Plan

## Purpose

CP-02 defines the validation schema required before serious ML v2 training. It
is a paper-only schema plan. It does not rerun validation, does not rerun OOS,
does not evaluate formulaic alphas, and does not train any model.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `validation_rerun_allowed_now=False`.
- `oos_rerun_allowed_now=False`.

## Local Evidence Used

- `data/reports/ml_baseline_feature_label_dataset_audit.md`
- `data/reports/ml_baseline_validation_report.md`
- `data/reports/formulaic_alpha_schema_plan.md`
- `data/reports/deflated_sharpe_placeholder_report.md`

Existing local reports show a pre-cutoff ML baseline context, including
`train_cutoff=2026-06-18`, monthly walk-forward validation context,
`post_cutoff_data_used_for_train=False`, and
`post_cutoff_data_used_for_validation=False`. CP-02 only turns those controls
into an explicit future ML v2 schema.

## Required Schema Areas

- Split identifiers: `split_id` and `fold_id`.
- Date grouping: `date_group`, with monthly grouping supported by current
  local ML baseline evidence.
- Label horizon metadata: `label_horizon_unit`, `label_horizon_value`,
  `label_start_date`, and `label_end_date`.
- Purge metadata: `purge_window_days`, `purge_start_date`, and
  `purge_end_date`.
- Embargo metadata: `embargo_window_days`, `embargo_start_date`, and
  `embargo_end_date`.
- Cutoff controls: `train_cutoff`, `post_cutoff_data_used_for_train`, and
  `post_cutoff_data_used_for_validation`.
- PIT feature controls: `feature_visible_at` and `feature_usable_from`.
- Audit controls: `leakage_check_status` and `split_source_report`.

## Validation Rules Reserved

- No row-level random split should be used for time-series ML v2 validation.
- Training rows whose label windows overlap validation windows must be purged.
- Rows immediately after validation windows must be embargoed when required by
  the chosen label horizon and grouping.
- `post_cutoff_data_used_for_train` must remain `False`.
- `post_cutoff_data_used_for_validation` must remain `False` unless a future
  explicitly approved validation checkpoint changes the evidence source.
- Feature `visible_at` and `usable_from` timestamps must be point-in-time safe.
- Any `leakage_check_status=BLOCK` should block CP-09 training readiness.

## Recommendation

Use this schema before any serious ML v2 training or formulaic alpha feature
merge. Keep purged/embargo validation separate from OOS proof: this checkpoint
does not create OOS evidence and does not use validation results for promotion,
demotion, or production readiness.

## Completion Statement

CP-02 is complete as a schema/design-only checkpoint. It defines label horizon,
purge window, embargo window, split identifiers, date grouping, and post-cutoff
exclusion fields without rerunning validation or OOS.
