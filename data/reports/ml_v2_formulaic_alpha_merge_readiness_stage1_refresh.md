# ML v2 Formulaic Alpha Merge Readiness Stage 1 Refresh

## Purpose

This paper-only refresh re-evaluates formulaic alpha merge readiness after the
Stage 1 broader materialized feature table and audit.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `training_allowed_now=False`.
- `dataset_merge_performed=False`.
- `model_training_performed=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.md`
- `data/reports/formulaic_alpha_broader_feature_audit_stage1.csv`
- `data/reports/formulaic_alpha_broader_feature_audit_stage1.md`
- `data/reports/deflated_sharpe_placeholder_report.md`
- `data/reports/candidate_trial_ledger.md`
- `data/reports/post_cutoff_oos_proof_inventory.md`
- `data/reports/paper_operation_safety_status_index.md`

## Result

`merge_readiness=WARN_STAGE1_NOT_FULL_COVERAGE`

Stage 1 materially improves feature evidence: 7200 rows, 50 symbols, 24 feature
dates, 6 formulas, 6 feature hashes, 7200 row hashes, PIT `PASS`, label
isolation `PASS`, and missing rate `0.003333`. However, it is still a bounded
sample and not a full feature matrix. Selection controls also remain incomplete.

## Remaining Blockers

- Effective trial count remains `not_available`.
- Deflated Sharpe remains placeholder-only.
- No formula evaluation was performed.
- OOS proof does not authorize review, promotion, or production.
- A future explicit gate must decide whether Stage 1 coverage is enough for a
  paper-only model experiment.

## Recommendation

Do not merge into an ML v2 training dataset yet. Next work should create a
paper-only experiment gate that decides whether Stage 1 coverage can support a
small, explicitly bounded experiment without promotion or production effects.

## Completion Statement

This Stage 1 merge-readiness refresh is complete as a paper-only report. No
dataset merge, model training, formula evaluation, candidate creation, or
production change occurred.
