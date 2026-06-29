# Goal Mode Checkpoint

Last updated: 2026-06-30 ML baseline validation report

Purpose: keep this file small enough to read on every resume. Full historical
context is archived at:

- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_pre_token_trim.md`
- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-24_readiness_evidence_loops.md`
- `docs/archive/GOAL_MODE_CHECKPOINT_2026-06-29_safety_status_reports.md`
- Future short goal prompt: `docs/goal-mode-minimal-prompt.md`

## Objective

Build a safe paper-operation trading research and monitoring system. Do not
build or enable live order execution.

## Hard Safety Rules

- No real orders, Toss API calls, broker submission, or order execution work.
- Keep `PRODUCTION_TRADING_ENABLED` disabled by default.
- Never open, print, summarize, commit, or copy `.env` secrets.
- Do not rerun OOS, fetch data, rerun candidate comparison, create candidates,
  regenerate the monthly plan, or change strategy parameters unless explicitly
  requested for a new approved goal.
- Do not modify, tune, promote, or replace the protected `PAPER_REVIEW`
  candidate.
- Treat production/readiness/risk `BLOCK` as a hard stop.
- Push only with explicit user approval.

## Resume Protocol

After compaction or a fresh resume:

1. Read `docs/goal-mode-minimal-prompt.md`.
2. Read this checkpoint.
3. Run `git status --short`.
4. Use existing local reports first.
5. Keep work to one narrow Goal loop.

## Current Safety Status

Source of truth:

- `data/reports/paper_operation_safety_status_index.csv`
- `data/reports/paper_operation_safety_status_index.md`
- `data/reports/protected_candidate_oos_review_eligibility_guard.csv`
- `data/reports/monthly_paper_operation_consistency_audit.csv`
- `data/reports/monthly_paper_operation_review_packet.csv`
- `data/reports/health_warn_classification.csv`

Latest status:

- Production is not live-ready: `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- OOS review eligibility is `REVIEW_NOT_ALLOWED`.
- `trading_allowed=False`.
- `review_allowed=False`.
- `production_effect=none`.
- Monthly order-plan actionable rows remain `0`.
- All current monthly order rows are blocked.
- Promoted candidates count remains `0`.
- Current recommended action:
  `keep_observing_no_tuning_no_promotion`.
- Scalper stale `WARN` is separated from monthly paper review/OOS.
- Production remains not live-ready.

## Current Best Candidate

`proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244` is the
protected paper-review candidate.

- Decision/status: `PAPER_REVIEW`, not adopt/promote.
- It resolved the previous required failures in pre-cutoff validation, but it
  relaxes the fixed point-in-time history safety gate to `244`.
- OOS review is not allowed yet; continue observing without tuning or
  promotion.

## Latest Local Report Additions

- ML baseline validation report:
  `data/reports/ml_baseline_validation_report.csv` and `.md`. Phase 3 is
  `paper_only_validation_complete` with leakage/PIT/feature checks `PASS`,
  `post_cutoff_data_used_for_validation=False`, `oos_rerun=False`,
  benchmark-relative performance, drawdown, hit-rate, and turnover recorded,
  `trading_allowed=False`, `production_effect=none`, and protected candidate
  unchanged.
- ML baseline model training scaffold:
  `data/reports/ml_baseline_model_training_report.csv` and `.md`. Phase 2 is
  `paper_only_baseline_trained` with `model_type=logistic_regression_sgd`,
  `train_cutoff=2026-06-18`, pre-cutoff train/validation split `PASS`,
  `post_cutoff_data_used_for_train=False`, `oos_data_used=False`,
  `production_artifact_linked=False`, `trading_allowed=False`,
  `production_effect=none`, and protected candidate unchanged.
- ML baseline feature/label dataset audit:
  `data/reports/ml_baseline_feature_label_dataset_audit.csv`, `.md`, and
  sample CSV. Phase 1 is `ready_for_training_scaffold` with
  `train_cutoff=2026-06-18`, `label_row_count=69915`,
  `post_cutoff_data_used_for_train=False`, `training_ran=False`,
  `trading_allowed=False`, `production_effect=none`, and protected candidate
  unchanged.
- Paper-only ML model completion roadmap checkpoint:
  `docs/ml_model_completion_checkpoint.md`. This is a doc-only roadmap for
  completing baseline-to-final-packet ML research loops; it does not train
  models, rerun OOS, fetch data, compare candidates, alter protected
  `PAPER_REVIEW` status, or change production readiness.
- ML external feature readiness plan:
  `data/reports/ml_external_feature_readiness_plan.csv` and `.md`.
  This is plan-only and not ready for training:
  `PLAN_ONLY_NOT_READY_FOR_TRAINING`. OpenDART is
  `planned_high_priority`, news is `planned_after_financials`, sentiment is
  `planned_after_news_schema`, and SNS/community is `later_stage_not_ready`.
  Every row keeps `fetch_allowed_now=False`, `training_allowed_now=False`,
  `trading_allowed=False`, `production_effect=none`, and requires PIT-safe
  timestamps plus `usable_from`.
- Paper-only ML data readiness audit:
  `data/reports/ml_data_readiness_audit.csv` and `.md`.
  Current local data is ready to start baseline tabular ML ranking research
  only; no model training was run. Train cutoff remains `2026-06-18`,
  post-cutoff data used for train is `False`, PIT universe is available,
  fundamentals/news/sentiment are `not_ready`, deep learning is `not_ready`,
  `trading_allowed=False`, and `production_effect=none`.
- Monthly paper operation consistency audit:
  `data/reports/monthly_paper_operation_consistency_audit.csv` and `.md`.
- Protected candidate OOS review eligibility guard:
  `data/reports/protected_candidate_oos_review_eligibility_guard.csv` and
  `.md`.
- Paper operation safety status index:
  `data/reports/paper_operation_safety_status_index.csv` and `.md`.
- Minimal resume prompt refreshed:
  `docs/goal-mode-minimal-prompt.md`.
- GPT project context refreshed:
  `docs/GPT_PROJECT_CONTEXT.md`.
- Project context consistency audit added:
  `data/reports/project_context_consistency_audit.csv` and `.md`.

## Verification Baseline

Recent completed loops verified:

- Full `unittest`: latest recorded `691` tests passing.
- `python -m compileall -q backtester`: passing.
- Safe production-check: `BLOCK` retained.
- Safe health-check with `--scalper-mode warn`: `WARN` only for stale scalper
  data.

For future code changes, use test-first work and finish with focused tests,
full `unittest`, `compileall`, production-check, health-check, checkpoint
update, commit, and push only with explicit approval. For doc-only changes, a
targeted document check plus `compileall` is enough.
