# ML v2 Stage 1 Tiny Experiment Protocol

## Purpose

POST-03 designs the tiny paper-only experiment protocol allowed by POST-02. It
does not execute an experiment, train a model, evaluate formulas, merge a
training dataset, or create a candidate.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `formula_evaluation_allowed_now=False`.
- `dataset_merge_allowed_now=False`.
- `candidate_creation=False`.

## Local Evidence Used

- `data/reports/ml_v2_stage1_paper_experiment_gate.md`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1_manifest.csv`
- `data/reports/purged_embargo_validation_schema_plan.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/paper_operation_safety_status_index.md`
- `data/reports/post_cutoff_oos_proof_inventory.md`

## Protocol Boundary

The future tiny experiment, if separately allowed, must be bounded to:

- Stage 1 feature table only;
- existing six CP-06 formulas only;
- existing 50 symbols and 24 feature dates only;
- no external inputs;
- no new formula generation;
- no strategy parameter changes;
- no production or order outputs.

## Disallowed In This Protocol

- Model training.
- Formula evaluation.
- Dataset merge for training.
- Hyperparameter sweep.
- Model selection.
- Sharpe or Deflated Sharpe calculation.
- PnL ranking or candidate comparison.
- Candidate creation or promotion.
- Broker submission or order execution.

## Completion Statement

POST-03 is complete as a design-only protocol. It prepares a future execution
gate while preserving `production_effect=none`.
