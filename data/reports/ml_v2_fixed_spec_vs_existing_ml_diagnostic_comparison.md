# ML v2 Fixed-Spec vs Existing ML Diagnostic Comparison

This is a paper-only diagnostic comparison built from existing local reports. It
does not train a model, rerun validation, rerun OOS, compare candidates for
promotion, tune parameters, write production artifacts, submit to a broker, or
authorize trading.

## Summary

| Model family | Training status | Validation status | Train rows | Validation rows | Train accuracy | Validation accuracy |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| ML baseline | `paper_only_baseline_trained` | `paper_only_validation_complete` | 111 | 88 | 0.5946 | 0.5335 |
| ML model v1 | `paper_only_model_v1_trained` | `paper_only_model_v1_validated` | 111 | 88 | 0.5946 | `not_available` |
| ML v2 fixed-spec | `paper_only_ml_v2_fixed_spec_trained` | `paper_only_ml_v2_fixed_spec_validated` | 74 | 20 | 0.6486 | 0.5500 |

## Interpretation

ML v2 fixed-spec has a higher reported training accuracy than the baseline/v1
training report and a 0.5500 validation diagnostic in its bounded fixed-spec
split. This is not a head-to-head model-selection result because the sample
sizes, feature scopes, and validation methods differ.

The safest reading is:

- ML v2 fixed-spec training/validation pipeline is now runnable on local data.
- The result is bounded and paper-only.
- No model winner is declared.
- No candidate decision is allowed.
- No production effect is allowed.

## Safety State

- `selection_allowed=False`
- `candidate_decision_allowed=False`
- `candidate_promotion=False`
- `broker_submission=False`
- `order_execution=False`
- `trading_allowed=False`
- `production_effect=none`
