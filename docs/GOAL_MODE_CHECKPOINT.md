# Goal Mode Checkpoint

Last updated: 2026-06-30 final ML research packet

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

- codebase-memory-mcp project setup preparation:
  `.cbmignore` and `docs/codebase_memory_mcp_project_setup.md` were added for
  future Codex code exploration, impact-scope analysis, and token savings. This
  is tooling preparation only: no installation, network download, MCP/Codex
  configuration change, indexing, fetch, API call, data CSV summarization, ML
  output change, trading feature change, protected candidate change, production
  readiness change, or push was performed. The setup excludes secrets, API
  keys, account information, `data/`, generated reports, large artifacts,
  caches, and local codebase-memory outputs. Production remains `BLOCK`,
  `trading_allowed=False`, and `production_effect=none`.
- codebase-memory-mcp binary-only installation:
  after explicit installation approval, upstream release version `0.8.1` was
  installed to
  `C:\Users\KangMinWoo\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe`
  with checksum verification. Agent configuration, MCP/Codex configuration,
  PATH modification, indexing, project cache generation, trading/ML behavior
  changes, protected candidate changes, production readiness changes, and push
  were not performed. The project root still has no `.codebase-memory/` or
  `graphify-out/` output.
- codebase-memory-mcp safe fast index:
  after explicit safe init/index approval, `codebase-memory-mcp 0.8.1` indexed
  the project through local junction `C:\tmp\toss-cbm-project` pointing to
  `C:\Users\KangMinWoo\Documents\토스증권`, because direct Korean-path CLI JSON
  failed before indexing. The recorded project is `C-tmp-toss-cbm-project`
  with `2440` nodes and `10175` edges in local cache
  `C:\Users\KangMinWoo\.cache\codebase-memory-mcp\C-tmp-toss-cbm-project.db`.
  `.cbmignore` was retained and read-only graph checks found zero indexed
  `File` rows for `data/`, `.env`, and large/report extensions including CSV,
  PDF, XLSX, ZIP, PARQUET, PKL, and JOBLIB. No MCP/Codex configuration, PATH
  change, network download, reinstall, OOS rerun, fetch/API call, candidate
  compare, monthly plan regeneration, trading/broker work, protected candidate
  change, production readiness change, or push was performed. No
  `.codebase-memory/` or `graphify-out/` directory was created in the project
  root.
- ML model final research packet:
  `data/reports/ml_model_research_packet.csv` and `.md`. Phase 14 is complete
  as a paper-only final packet consolidating local Phase 1-13 artifacts:
  `model_completion_status=paper_only_complete_not_live_ready`, data lineage,
  baseline dataset/training/validation, feature importance/failure analysis,
  external readiness, model v1, shadow scoring, observation status, leakage
  checks, overfit/data-snooping risk, and final recommendation are documented.
  OpenDART/news/sentiment/external features remain `not_ready` unless an
  existing readiness report explicitly says otherwise. Production `BLOCK` is
  retained, protected candidate is unchanged, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, `trading_allowed=False`,
  and `production_effect=none`. No fetch, API call, OOS rerun, candidate
  compare, new candidate, monthly plan regeneration, strategy change, broker
  work, production readiness change, or trading authorization was performed.
- ML model observation status report:
  `data/reports/ml_model_observation_status.csv` and `.md`. Phase 13 is
  complete using explicitly requested historical backfill from existing local
  baseline feature/label rows: `observation_basis=historical_backfill`,
  `observation_months=101`, `sufficient_observation_months=True`,
  `performance_stability=historical_backfill_stable`, drawdown `-0.6520`,
  turnover `turnover=0.1700`, `coverage=symbols=5;months=101`,
  `post_cutoff_train_leakage=PASS`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No fetch, OOS rerun,
  candidate compare, order output, broker work, monthly plan regeneration,
  candidate promotion, strategy change, or production change was performed.
  Earliest incomplete phase is Phase 14.
- ML shadow scoring report:
  `data/reports/ml_shadow_scoring_report.csv` and `.md`. Phase 12 applies
  paper-only ML model v1 scores as human-readable shadow scores only. It
  records score rows for the latest local feature month with `order_output=False`,
  `broker_submission=False`, `monthly_plan_regenerated=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. No order output, broker work, monthly plan
  regeneration, candidate promotion, strategy change, or production change was
  performed.
- ML model v1 experiment:
  `data/reports/ml_model_v1_training_report.csv`,
  `data/reports/ml_model_v1_validation_report.csv`, and
  `data/reports/ml_model_v1_risk_report.md`. Phase 11 trained and validated a
  paper-only technical-feature model v1 because Phase 10 external readiness is
  `BLOCK`. It records `approved_feature_set=technical_only`,
  `external_features_used=False`, `post_cutoff_data_used_for_train=False`,
  validation leakage `PASS`, benchmark and baseline-technical comparisons,
  overfit/data-snooping risk `WARN`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No external feature
  merge, OOS rerun, candidate compare for promotion, order output, broker work,
  or production change was performed.
- ML external feature readiness re-audit:
  `data/reports/ml_external_feature_readiness_reaudit.csv` and `.md`.
  Phase 10 re-audits financial, news, and sentiment external features from
  existing local reports only. Result: financial `not_ready` with
  `missing_rate=1.0000`, news `not_ready`, sentiment `not_ready`, overall
  `BLOCK`, leakage checks `PASS`, `training_allowed=False`,
  `feature_added_to_training=False`, `post_cutoff_data_used_for_train=False`,
  `trading_allowed=False`, and `production_effect=none`. No fetch, API call,
  scoring, training, OOS rerun, candidate compare, strategy change, or
  production change was performed.
- ML sentiment scoring plan:
  `data/reports/ml_sentiment_scoring_plan.csv` and `.md`. Phase 9 is
  rule/lexicon plan-only; it defines `model_version=rule_lexicon_v1`,
  `sentiment_score` range `-1.0_to_1.0`, `scored_at`, `usable_from`, PIT
  controls, FinBERT/LLM later-stage risk notes, `fetch_allowed_now=False`,
  `training_allowed_now=False`, `model_training_allowed=False`,
  `feature_added_to_training=False`, `trading_allowed=False`, and
  `production_effect=none`. No news fetch, API call, LLM/FinBERT scoring,
  training, OOS rerun, candidate compare, strategy change, or production
  change was performed.
- ML news event schema plan:
  `data/reports/ml_news_event_schema_plan.csv` and `.md`. Phase 8 is
  schema-only and fetch-free; it defines Naver News, GDELT, manual calendar,
  and PIT control rows with `published_at`, `collected_at`, `visible_at`,
  `usable_from`, deterministic `text_hash` de-duplication, source coverage
  risk, `fetch_allowed_now=False`, `training_allowed_now=False`,
  `feature_added_to_training=False`, `trading_allowed=False`, and
  `production_effect=none`. No news API, network fetch, training, OOS rerun,
  candidate compare, strategy change, or production change was performed.
- ML financial feature merge audit:
  `data/reports/ml_financial_feature_merge_audit.csv` and `.md`. Phase 7
  completed a local-only merge audit against the baseline ML sample and limited
  financial observations. The audit records `join_coverage=WARN 0/5`,
  `missing_rate=WARN 1.0000`, `leakage_check=PASS`,
  `post_cutoff_data_used_for_train=False`,
  `feature_added_to_training=False`, `training_allowed_now=False`,
  `trading_allowed=False`, `production_effect=none`, and protected candidate
  unchanged. No fetch, training, OOS rerun, candidate compare, strategy change,
  or production change was performed.
- ML financial PIT audit:
  `data/reports/ml_financial_observations_sample.csv`,
  `data/reports/ml_financial_pit_audit.csv`, and
  `data/reports/ml_financial_feature_readiness_report.md`. Phase 6 completed a
  limited OpenDART sample after explicit approval. The PIT audit records
  `usable_from_presence=PASS`, `post_cutoff_train_leakage=PASS`,
  `correction_lineage=PASS`, readiness `BLOCK`,
  `post_cutoff_data_used_for_train=False`, `training_allowed_now=False`,
  `trading_allowed=False`, and `production_effect=none`.
- ML financial feature schema plan:
  `data/reports/ml_financial_feature_schema_plan.csv` and `.md`. Phase 5 is
  schema-only and fetch-free; it defines OpenDART financial metrics, valuation
  metrics, disclosure correction lineage, PIT controls, `receipt_date`,
  `receipt_time`, `collected_at`, `usable_from`, `api_key_required=True`,
  `fetch_allowed_now=False`, `training_allowed_now=False`,
  `trading_allowed=False`, and `production_effect=none`.
- ML explainability and failure analysis:
  `data/reports/ml_feature_importance_report.csv` and
  `data/reports/ml_failure_analysis_report.csv`. Phase 4 records feature
  importance, regime summaries, failure months, failure symbols, and overfit
  risk notes with leakage/PIT checks `PASS`, `trading_allowed=False`,
  `production_effect=none`, and protected candidate unchanged.
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

- Full `unittest`: latest recorded `742` tests passing.
- `python -m compileall -q backtester`: passing.
- Safe production-check: `BLOCK` retained.
- Safe health-check with `--scalper-mode warn`: `WARN` only for stale scalper
  data.

For future code changes, use test-first work and finish with focused tests,
full `unittest`, `compileall`, production-check, health-check, checkpoint
update, commit, and push only with explicit approval. For doc-only changes, a
targeted document check plus `compileall` is enough.
