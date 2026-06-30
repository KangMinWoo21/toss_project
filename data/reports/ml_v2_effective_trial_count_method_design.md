# ML v2 Effective Trial Count Method Design

This report designs a future method for deriving an effective trial count from
the candidate trial ledger. It does not calculate the effective trial count,
Deflated Sharpe, Sharpe, PnL, ranking, or any model-selection metric.

## Result

- calculation_allowed_now: `False`
- training_allowed_now: `False`
- production_effect: `none`
- trading_allowed: `False`

## Method Principles

1. A ledger row is not automatically an independent trial.
2. Trials sharing candidate lineage, formula lineage, model lineage, scenario
   set, or parameter family should be treated as dependent unless evidence
   proves otherwise.
3. Unknown raw counts remain `not_available`; they are not imputed as zero.
4. Numeric raw counts may be used only as lower-bound evidence until exact
   trial inventory is complete.
5. Effective trial count must be no greater than raw trial count.
6. Deflated Sharpe remains blocked unless raw Sharpe, skew, kurtosis, sample
   length, raw trial count, and effective trial count are all available from an
   approved validation source.

## Proposed Grouping Keys

- `method_family`
- `candidate_id`
- `formula_hash`
- `model_hash`
- `scenario_set`
- `parameter_summary`
- `source_report`

## Missing Evidence Policy

When lineage fields are `not_available`, classify the row conservatively as
dependent or unresolved. Do not count it as an independent alpha/model attempt
until the source report provides enough detail.

## Next Safe Action

Create a dependency group manifest from the existing candidate trial ledger.
That manifest should still be report-only and should not calculate Deflated
Sharpe, train ML v2, validate ML v2, evaluate formulas, or select a model.
