# Formulaic Alpha Broader Feature Audit Stage 1

## Purpose

This audit checks the Stage 1 broader formulaic alpha feature table for PIT availability, label isolation, missingness policy, `formula_hash`, final `feature_hash`, and feature row hashes.

## Safety Status

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- `evaluation_performed=False`.
- `training_allowed_now=False`.
- `merge_ready=False`.

## Local Evidence Used

- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1.md`
- `data/reports/formulaic_alpha_broader_materialized_feature_stage1_manifest.csv`

## Audit Summary

- Feature rows audited: `7200`.
- Symbols audited: `50`.
- Feature dates audited: `24`.
- Formula samples audited: `6`.
- Materialized feature hashes: `6`.
- Feature row hashes: `7200`.
- Missing rows: `24`.
- Missing rate: `0.003333`.
- PIT status: `PASS`.
- Label isolation status: `PASS`.
- Audit status: `PASS_BROADER_SAMPLE_NOT_TRAINING_READY`.

## Interpretation

Stage 1 expands coverage from the previous 30-row sample to 7200 rows while staying under the 10000-row cap. This improves feature materialization evidence, but it remains a paper-only sample and is not automatically merge-ready or training-ready.

## Remaining Blockers

- No formula evaluation was performed.
- No effective trial count was calculated.
- No Deflated Sharpe calculation was performed.
- Merge readiness must be refreshed separately before any dataset merge.
- Training readiness remains blocked until a future gate explicitly returns `ALLOW_PAPER_ONLY`.

## Completion Statement

The Stage 1 broader feature audit is complete as paper-only evidence. It does not train a model, score a candidate, create orders, or change production readiness.
