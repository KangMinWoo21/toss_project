# ML v2 Fixed-Spec Bounded Robustness Diagnostic

This is the single bounded paper-only robustness diagnostic allowed by POST-28. It uses existing local reports and local CSV inputs only. It does not train a model, rerun validation, rerun OOS, compare candidates, tune hyperparameters, rank formulas, create candidates, change strategy parameters, submit to a broker, execute orders, or authorize trading.

## Diagnostic Summary

- `robustness_diagnostic_performed_now=True`
- `model_training_performed_now=False`
- `validation_rerun_performed_now=False`
- `oos_rerun_performed_now=False`
- `candidate_comparison_rerun_performed_now=False`
- `winner_declared=False`
- `candidate_decision_allowed=False`
- `trading_allowed=False`
- `production_effect=none`

## Key Results

- Joined rows: `98` across `5` symbols and `23` date groups.
- Fixed formula hashes: `6`; all are reported together with no formula selection.
- Chronological split: train rows `74`, validation rows `20`, embargo date groups `2025-12-30`.
- Rolling-origin label diagnostic: `positive=4;negative=8;min_class_count=4;min_class_share=0.3333`.
- Blocked-time-fold label diagnostic: `positive=16;negative=18;min_class_count=16;min_class_share=0.4706`.
- PIT/cutoff failures: `pit_failures=0;post_cutoff_label_failures=0;bad_feature_safety_flags=0`.
- Status counts: `{'PASS': 9, 'WARN': 2}`.

## Interpretation Boundary

Warnings, including small validation sample or label-balance warnings, are research-packet evidence only. They do not select a model, tune a threshold, change candidate status, or change production readiness.

Next safe checkpoint: analyze these robustness diagnostics without selecting a winner.
