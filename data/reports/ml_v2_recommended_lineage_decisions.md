# ML v2 Recommended Lineage Decisions

This report records conservative recommended decisions for the 23 dependency
groups from the manual lineage review. It does not train ML v2, validate ML v2,
evaluate formulas, calculate effective trial count, calculate Deflated Sharpe,
or compute performance metrics.

## Recommendation Summary

- dependency groups reviewed: `23`
- same_dependency_family: `11`
- not_selection_trial: `12`
- manual_review_unresolved: `0`
- independent_trial: `0`
- selection_trial_allowed: `False`
- effective_trial_count_allowed_now: `False`
- deflated_sharpe_allowed_now: `False`
- training_allowed_now: `False`
- validation_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Decision Policy

- Formulaic alpha sample rows are `not_selection_trial` because they were not
  evaluated, ranked, or linked to model training.
- Overlay, schema, inventory, concentration, cost, and comparison report rows
  are `not_selection_trial`.
- ML baseline and ML v1 report families are `same_dependency_family`, not
  independent ML v2 selection trials.
- Monthly baseline/candidate diagnostic variants are `same_dependency_family`
  and should not be counted as independent ML v2 trials.
- No dependency group is recommended as `independent_trial`.

## Training Implication

These recommendations clarify lineage treatment, but they do not reopen ML v2
training. Effective trial count remains uncalculated, Deflated Sharpe remains
blocked, and ML v2 training/validation remain disallowed.
