# Goal Mode Checkpoint

Last updated: 2026-06-30 POST-20 final blocked status packet

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

- ML v2 POST-20 final blocked status packet:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-20, and
  `data/reports/ml_v2_final_blocked_status_packet.csv` plus `.md` were added.
  Final status is `paper_only_training_validation_blocked`: exact raw count is
  incomplete, recommended lineage decisions authorize 0 independent trials,
  effective trial count is `not_available`, Deflated Sharpe readiness is
  `BLOCK`, and ML v2 training/validation remain blocked. No model training,
  validation run, formula evaluation, effective-trial-count calculation,
  Deflated Sharpe calculation, performance metric computation, data fetch, API
  call, OOS rerun, candidate comparison rerun, candidate creation, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed.
- ML v2 POST-19 training readiness after recommended lineage:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-19, and
  `data/reports/ml_v2_training_readiness_after_recommended_lineage.csv` plus
  `.md` were added. Gate result remains `BLOCK`: recommended lineage decisions
  produce 11 `same_dependency_family`, 12 `not_selection_trial`, and 0
  `independent_trial`; selection-trial permission remains false, effective
  trial count remains unavailable, and Deflated Sharpe readiness remains
  blocked. No model training, validation run, formula evaluation,
  effective-trial-count calculation, Deflated Sharpe calculation, performance
  metric computation, data fetch, API call, OOS rerun, candidate comparison
  rerun, candidate creation, strategy change, protected candidate change,
  broker work, production readiness change, push, or trading authorization was
  performed.
- ML v2 POST-18 recommended lineage decisions:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-18, and
  `data/reports/ml_v2_recommended_lineage_decisions.csv` plus `.md` were
  added. The recommended conservative decisions classify 23 dependency groups
  as 11 `same_dependency_family` and 12 `not_selection_trial`, with 0
  `independent_trial`. No group is allowed as an independent model-selection
  trial; effective trial count, Deflated Sharpe, ML v2 training, and ML v2
  validation remain blocked. No model training, validation run, formula
  evaluation, effective-trial-count calculation, Deflated Sharpe calculation,
  performance metric computation, data fetch, API call, OOS rerun, candidate
  comparison rerun, candidate creation, strategy change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-17 training readiness after manual lineage:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-17, and
  `data/reports/ml_v2_training_readiness_after_manual_lineage.csv` plus `.md`
  were added. Gate result remains `BLOCK`: manual lineage review leaves 19
  groups `manual_review_required`, 3 groups `unresolved`, and 1 group resolved
  only as non-selection overlay. No independent model-selection trial is
  allowed, effective trial count remains unavailable, and Deflated Sharpe
  readiness remains blocked. No model training, validation run, formula
  evaluation, effective-trial-count calculation, Deflated Sharpe calculation,
  performance metric computation, data fetch, API call, OOS rerun, candidate
  comparison rerun, candidate creation, strategy change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-16 manual lineage review:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-16, and
  `data/reports/ml_v2_manual_lineage_review.csv` plus `.md` were added. The
  review classified 23 dependency groups as 19 `manual_review_required`, 3
  `unresolved`, and 1 `resolved_non_selection_overlay`. No group is allowed as
  an independent model-selection trial; effective trial count, Deflated Sharpe,
  ML v2 training, and ML v2 validation remain blocked. No model training,
  validation run, formula evaluation, effective-trial-count calculation,
  Deflated Sharpe calculation, performance metric computation, data fetch, API
  call, OOS rerun, candidate comparison rerun, candidate creation, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed.
- ML v2 POST-15 blocked training report after reopen:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-15, and
  `data/reports/ml_v2_blocked_training_report_after_reopen.csv` plus `.md`
  were added. Because POST-14 returned `BLOCK`, ML v2 training was not run, no
  model artifact was created, no dataset merge was performed, and validation is
  not allowed. No model training, validation run, formula evaluation,
  performance metric computation, data fetch, API call, OOS rerun, candidate
  comparison rerun, candidate creation, strategy change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-14 training readiness gate reopen:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-14, and
  `data/reports/ml_v2_training_readiness_gate_reopen.csv` plus `.md` were
  added. Gate result is `BLOCK`: exact raw count remains lower-bound only,
  lineage has 0 resolved and 23 unresolved groups, effective trial count is
  `not_available`, Deflated Sharpe readiness is blocked, and Stage 1 feature
  merge readiness remains a warning. ML v2 training and validation were not
  run. No formula evaluation, performance metric computation, data fetch, API
  call, OOS rerun, candidate comparison rerun, candidate creation, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed.
- ML v2 POST-13 Deflated Sharpe readiness gate:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-13, and
  `data/reports/ml_v2_deflated_sharpe_readiness_gate.csv` plus `.md` were
  added. Gate result is `BLOCK`: raw Sharpe, skew, kurtosis, sample length,
  complete raw trial count, and effective trial count remain unavailable or not
  calculation-ready. Deflated Sharpe was not calculated, model selection is not
  allowed, and ML v2 training/validation remain blocked. No model training,
  validation run, formula evaluation, Deflated Sharpe calculation, performance
  metric computation, data fetch, API call, OOS rerun, candidate comparison
  rerun, candidate creation, strategy change, protected candidate change,
  broker work, production readiness change, push, or trading authorization was
  performed.
- ML v2 POST-12 effective trial count estimate:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-12, and
  `data/reports/ml_v2_effective_trial_count_estimate.csv` plus `.md` were
  added. Result is `BLOCK_NO_ESTIMATE`: exact raw-count evidence remains
  lower-bound only at 41, lineage resolved groups are 0, and unresolved groups
  are 23. Effective trial count remains `not_available`; Deflated Sharpe, ML v2
  training, and ML v2 validation remain blocked. No model training, validation
  run, formula evaluation, effective-trial-count calculation, Deflated Sharpe
  calculation, performance metric computation, data fetch, API call, OOS rerun,
  candidate comparison rerun, candidate creation, strategy change, protected
  candidate change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-11 trial lineage resolution audit:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-11, and
  `data/reports/ml_v2_trial_lineage_resolution_audit.csv` plus `.md` were
  added. The audit reviewed 23 dependency groups and classified all 23 as
  unresolved because lineage fields remain incomplete. Effective trial count,
  Deflated Sharpe, ML v2 training, and ML v2 validation remain blocked with
  `training_allowed_now=False`, `validation_allowed_now=False`,
  `trading_allowed=False`, and `production_effect=none`. No model training,
  validation run, formula evaluation, effective-trial-count calculation,
  Deflated Sharpe calculation, performance metric computation, data fetch, API
  call, OOS rerun, candidate comparison rerun, candidate creation, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed.
- ML v2 POST-10 exact raw count inventory:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-10, and
  `data/reports/ml_v2_exact_raw_count_inventory.csv` plus `.md` were added.
  The inventory records 29 source ledger rows, 30 inventory rows including
  summary, 7 exact numeric raw-count rows, 22 rows still `not_available`, and
  exact numeric lower-bound sum 41. Full project-wide exact raw trial count and
  effective trial count remain `not_available`. No model training, validation
  run, formula evaluation, effective-trial-count calculation, Deflated Sharpe
  calculation, performance metric computation, data fetch, API call, OOS rerun,
  candidate comparison rerun, candidate creation, strategy change, protected
  candidate change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-09 training readiness after trial manifest:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-09, and
  `data/reports/ml_v2_training_readiness_after_trial_manifest.csv` plus `.md`
  were added. The refreshed gate remains `BLOCK`: POST-06 and POST-08 improve
  blocker visibility, but raw trial count remains lower-bound only, effective
  trial count is `not_available`, all dependency groups retain incomplete
  lineage warnings, Deflated Sharpe inputs are missing, tiny experiment
  execution remains blocked, and no ML v2 model is available for validation.
  No model training, validation run, formula evaluation, performance metric
  computation, OOS rerun, candidate comparison rerun, candidate creation,
  strategy change, protected candidate change, broker work, production
  readiness change, push, or trading authorization was performed.
- ML v2 POST-08 trial dependency group manifest:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-08, and
  `data/reports/ml_v2_trial_dependency_group_manifest.csv` plus `.md` were
  added. The manifest maps 29 candidate-trial ledger rows into 23 dependency
  groups, with raw-trial lower-bound sum 41 and all groups retaining incomplete
  lineage warnings. It does not calculate effective trial count, Deflated
  Sharpe, Sharpe, PnL, rankings, model-selection metrics, or formula
  performance. ML v2 training and validation remain blocked with
  `training_allowed_now=False`, `trading_allowed=False`, and
  `production_effect=none`.
- ML v2 POST-07 effective trial count method design:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-07, and
  `data/reports/ml_v2_effective_trial_count_method_design.csv` plus `.md` were
  added. The design defines dependency grouping by method family, candidate
  lineage, formula hash, model hash, scenario set, parameter summary, and
  source report. It does not calculate effective trial count, Deflated Sharpe,
  Sharpe, PnL, model ranking, or formula ranking. ML v2 training and validation
  remain blocked with `training_allowed_now=False`, `trading_allowed=False`,
  and `production_effect=none`.
- ML v2 POST-06 trial count and Deflated Sharpe blocker audit:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-06, and
  `data/reports/ml_v2_trial_count_deflated_sharpe_blocker_audit.csv` plus
  `.md` were added. The audit records 29 trial-ledger rows, 7 numeric
  `raw_trial_count` rows, raw-trial lower-bound sum 41, 0 numeric
  `effective_trial_count` rows, and Deflated Sharpe inputs still unavailable.
  Result remains `BLOCK`: ML v2 training and validation are not allowed. No
  model training, formula evaluation, performance metric computation, data
  fetch, API call, SNS/news scrape, OOS rerun, candidate comparison rerun,
  candidate creation, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed.
- ML v2 POST-05 post-CP15 completion packet:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-05, and
  `data/reports/ml_v2_post_cp15_completion_packet.csv` plus `.md` were added.
  Final recommendation is `paper_only_complete_blocked_not_live_ready`. CP-01
  through CP-15 are complete, POST-01 through POST-04 are complete, and the
  remaining safe local post-CP15 loops are resolved as report-only, `BLOCK`,
  `WARN`, or deferred later-stage evidence. ML v2 training, tiny experiment
  execution, model selection, production readiness, broker work, and trading
  remain blocked. No model training, formula evaluation, data fetch, API call,
  SNS/news scrape, OOS rerun, candidate comparison rerun, candidate creation,
  monthly plan regeneration, strategy parameter change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed.
- ML v2 POST-04 Stage 1 tiny experiment execution gate:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-04, and
  `data/reports/ml_v2_stage1_tiny_experiment_execution_gate.csv` and `.md`
  were added. The report-only gate returns `gate_result=BLOCK` because POST-02
  allowed only protocol design, POST-03 did not execute the experiment, Stage 1
  training readiness remains blocked, selection controls are incomplete, and
  Stage 1 merge readiness is still not full readiness evidence.
  `training_allowed_now=False`,
  `paper_only_tiny_experiment_allowed_next=False`,
  `model_training_performed=False`, `formula_evaluation_performed=False`,
  `dataset_merge_performed=False`, `performance_metric_computed=False`,
  `feature_selection_performed=False`, `candidate_creation=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. No model training, formula evaluation, dataset
  merge, performance metric computation, OOS rerun, candidate comparison
  rerun, candidate creation, monthly plan regeneration, strategy parameter
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed. Production remains `BLOCK` and
  protected candidate remains `PAPER_REVIEW`.
- ML v2 POST-03 Stage 1 tiny experiment protocol:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-03, and
  `data/reports/ml_v2_stage1_tiny_experiment_protocol.csv` and `.md` were
  added. The protocol is design-only and bounded to the existing Stage 1
  feature table, existing six CP-06 formulas, 50 symbols, and 24 feature dates.
  It preserves `training_allowed_now=False`,
  `formula_evaluation_allowed_now=False`, `dataset_merge_allowed_now=False`,
  `candidate_creation=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No model training,
  formula evaluation, dataset merge, OOS rerun, candidate comparison rerun,
  candidate creation, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed. Production remains `BLOCK` and
  protected candidate remains `PAPER_REVIEW`.
- ML v2 POST-02 Stage 1 paper-only experiment gate:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-02, and
  `data/reports/ml_v2_stage1_paper_experiment_gate.csv` and `.md` were added.
  The report-only gate returns `gate_result=ALLOW_PAPER_ONLY_EXPERIMENT`, but
  this allows only a future tiny experiment protocol design checkpoint.
  `training_allowed_now=False`, `model_training_performed=False`,
  `formula_evaluation_performed=False`, `dataset_merge_performed=False`,
  `candidate_creation=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No model training,
  formula evaluation, dataset merge, OOS rerun, candidate comparison rerun,
  candidate creation, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed. Production remains `BLOCK` and
  protected candidate remains `PAPER_REVIEW`.
- ML v2 POST-01 Stage 1 paper-only experiment gate design:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was extended with POST-01, and
  `data/reports/ml_v2_stage1_paper_experiment_gate_design.csv` and `.md` were
  added. The design defines future gate outcomes
  `ALLOW_PAPER_ONLY_EXPERIMENT`, `BLOCK`, and `deferred_later_stage`, while
  preserving `training_allowed_now=False`, `dataset_merge_allowed_now=False`,
  `candidate_promotion=False`, `broker_submission=False`,
  `order_execution=False`, `trading_allowed=False`, and
  `production_effect=none`. No model training, formula evaluation, dataset
  merge, OOS rerun, candidate comparison rerun, candidate creation, monthly
  plan regeneration, strategy parameter change, protected candidate change,
  broker work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK` and protected candidate remains
  `PAPER_REVIEW`.
- ML v2 Stage 1 readiness refresh:
  `data/reports/ml_v2_formulaic_alpha_merge_readiness_stage1_refresh.csv` and
  `.md`, plus
  `data/reports/ml_v2_training_readiness_gate_stage1_refresh.csv` and `.md`,
  were added after the broader Stage 1 materialized feature audit. Merge
  readiness improved to `merge_readiness=WARN_STAGE1_NOT_FULL_COVERAGE` with
  7200 audited rows, 50 symbols, 24 feature dates, 6 formulas, PIT `PASS`,
  label isolation `PASS`, and missing rate `0.003333`, but remains not approved
  for dataset merge. Training readiness remains `gate_result=BLOCK`,
  `training_allowed_now=False`, `paper_only_training_allowed_next=False`,
  `model_training_performed=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No dataset merge,
  model training, formula evaluation, candidate creation, OOS rerun, candidate
  comparison rerun, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed. Production remains `BLOCK` and
  protected candidate remains `PAPER_REVIEW`.
- Formulaic alpha broader materialized feature Stage 1:
  `data/reports/formulaic_alpha_broader_materialized_feature_stage1.csv`,
  `.md`, and `_manifest.csv`, plus
  `data/reports/formulaic_alpha_broader_feature_audit_stage1.csv` and `.md`,
  were added as the bounded Stage 1 implementation of the broader
  materialization plan. Stage 1 uses existing local OHLCV only, keeps the
  existing six CP-06 formulas, covers 50 symbols and 24 monthly feature dates
  from `2024-07-31` through `2026-06-18`, creates 7200 feature rows under the
  10000-row cap, materializes 6 feature hashes and 7200 feature row hashes, and
  records 24 missing rows with missing rate `0.003333`. The audit status is
  `PASS_BROADER_SAMPLE_NOT_TRAINING_READY`; `evaluation_performed=False`,
  `training_allowed_now=False`, `merge_ready=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. No formula evaluation, model training, dataset
  merge, OOS rerun, candidate comparison rerun, candidate creation, monthly
  plan regeneration, strategy parameter change, protected candidate change,
  broker work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK` and protected candidate remains
  `PAPER_REVIEW`.
- Formulaic alpha broader materialization coverage plan:
  `data/reports/formulaic_alpha_broader_materialization_coverage_plan.csv` and
  `.md` were added as a paper-only plan for the next staged materialization
  loop. The plan recommends a bounded Stage 1 scope of 50 local OHLCV symbols,
  24 monthly feature dates, and the existing six CP-06 formulas, for an
  estimated 7200 rows with a 10000-row hard cap. It defines chunking, PIT,
  missingness, hashing, audit, and fail-closed stop rules. It is design-only:
  `feature_values_generated_now=False`, `dataset_merge_performed=False`,
  `training_allowed_now=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No feature values,
  formula evaluations, model training, dataset merge, OOS rerun, candidate
  comparison rerun, candidate creation, monthly plan regeneration, strategy
  parameter change, protected candidate change, broker work, production
  readiness change, push, or trading authorization was performed. Production
  remains `BLOCK` and protected candidate remains `PAPER_REVIEW`.
- ML v2 readiness refresh after formulaic feature sample:
  `data/reports/ml_v2_formulaic_alpha_merge_readiness_refresh.csv` and `.md`,
  plus `data/reports/ml_v2_training_readiness_gate_refresh.csv` and `.md`,
  were added as paper-only readiness refresh reports after the 30-row
  materialized feature sample. Merge readiness improved from no materialized
  values to audited sample evidence, but remains
  `merge_readiness=BLOCK_PARTIAL_SAMPLE_ONLY` because coverage is limited to 5
  symbols and one feature date. Training readiness remains
  `gate_result=BLOCK`, `training_allowed_now=False`,
  `paper_only_training_allowed_next=False`, `model_training_performed=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. No dataset merge, model training, formula
  evaluation, candidate creation, OOS rerun, candidate comparison rerun,
  monthly plan regeneration, strategy parameter change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed. Production remains `BLOCK` and protected
  candidate remains `PAPER_REVIEW`.
- Formulaic alpha materialized feature sample and audit refresh:
  `data/reports/formulaic_alpha_materialized_feature_sample.csv` and `.md`,
  plus `data/reports/formulaic_alpha_feature_audit_refresh.csv` and `.md`,
  were added as a narrow paper-only implementation of the post-CP-15
  materialization blocker. The sample materializes the six CP-06 formula
  strings for 5 local symbols on `2026-06-18`, creating 30 feature rows, 6
  final feature hashes, and 30 feature row hashes from existing local OHLCV
  only. The audit refresh records PIT status `PASS`, label isolation `PASS`,
  missing rows `0`, and
  `audit_status=PASS_SAMPLE_ONLY_NOT_TRAINING_READY`. It remains sample-only:
  `evaluation_performed=False`, `training_allowed_now=False`,
  `merge_ready=False`, `candidate_promotion=False`, `trading_allowed=False`,
  and `production_effect=none`. No model training, formula evaluation,
  candidate scoring, OOS rerun, candidate comparison rerun, new trading
  candidate creation, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed. Production remains `BLOCK` and
  protected candidate remains `PAPER_REVIEW`.
- Formulaic alpha feature materialization plan:
  `data/reports/formulaic_alpha_feature_materialization_plan.csv` and `.md`
  were added as the first post-CP-15 blocker-resolution artifact. The plan
  defines the future feature table contract, PIT fields, label-isolation
  controls, missingness policy, operator versioning, and final `feature_hash`
  requirements for the six CP-06 formula samples. It is design-only:
  `feature_values_generated_now=False`, `evaluation_performed_now=False`,
  `training_allowed_now=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. It does not unblock
  CP-08/CP-09 yet; a future paper-only materialization implementation and audit
  are still required. No feature values were generated, no formula was
  evaluated, no model was trained, no data was fetched, no API was called, no
  news/SNS was scraped, no OOS was rerun, no candidate comparison was rerun, no
  candidate was created, no monthly plan was regenerated, no strategy parameter
  was changed, no protected candidate was modified, no broker work occurred, no
  production readiness changed, no push occurred, and no trading authorization
  was performed. Production remains `BLOCK` and protected candidate remains
  `PAPER_REVIEW`.
- ML v2 CP-15 Final Research Packet:
  `data/reports/ml_v2_final_research_packet.csv` and `.md` were added as the
  final paper-only ML v2 packet consolidating CP-01 through CP-14. Final status
  is `paper_only_complete_blocked_not_live_ready`,
  `training_allowed_now=False`, `model_available=False`,
  `shadow_scores_created=0`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, `trading_allowed=False`,
  and `production_effect=none`. The packet recommends no training, trading,
  promotion, demotion, or deployment until a future paper-only gate resolves
  formulaic feature materialization, PIT, label-isolation, missingness,
  `feature_hash`, effective-trial-count, OOS proof, and training-readiness
  blockers. No model training, data fetch, API call, news/SNS scrape, OOS
  rerun, candidate comparison rerun, new trading candidate creation, monthly
  plan regeneration, strategy parameter change, protected candidate change,
  broker work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK` and protected candidate remains
  `PAPER_REVIEW`. ML v2 checkpoint roadmap CP-01 through CP-15 is complete as
  blocked paper-only research.
- ML v2 CP-14 Hybrid Overlay Design:
  `data/reports/ml_v2_hybrid_overlay_design.csv` and `.md` were added as a
  paper-only disabled-by-default overlay design. Macro/regime, disclosure/event,
  news/event, CEO/official SNS, and sentiment-model references are all default
  off; `direct_buy_alpha_allowed=False`, `training_allowed_now=False`,
  `external_fetch_performed=False`, `llm_scoring_performed=False`,
  `strategy_parameter_change=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No external fetch,
  news/SNS scrape, LLM/FinBERT scoring, data fetch, API call, model training,
  candidate comparison rerun, candidate creation, monthly plan regeneration,
  strategy parameter change, protected candidate change, broker work,
  production readiness change, push, or trading authorization was performed.
  Production remains `BLOCK` and protected candidate remains `PAPER_REVIEW`.
  Next ML v2 checkpoint: CP-15 Final ML v2 Research Packet.
- ML v2 CP-13 Shadow Scoring Report:
  `data/reports/ml_v2_shadow_scoring_report.csv` and `.md` were added as a
  blocked paper-only shadow scoring report. Because no trained or validated ML
  v2 model exists, the report records
  `shadow_scoring_status=BLOCK_NO_VALIDATED_MODEL`, `score_rows_created=0`,
  `order_output=False`, `broker_submission=False`,
  `monthly_plan_regenerated=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No score rows, order
  output, broker submission, monthly plan regeneration, candidate promotion,
  OOS rerun, data fetch, API call, news/SNS scrape, strategy parameter change,
  protected candidate change, production readiness change, push, or trading
  authorization was performed. Production remains `BLOCK` and protected
  candidate remains `PAPER_REVIEW`. Next ML v2 checkpoint: CP-14 ML v2 Hybrid
  Overlay Design.
- ML v2 CP-12 Cost / Concentration / Failure Analysis:
  `data/reports/ml_v2_cost_concentration_failure_analysis.csv` and `.md` were
  added as a blocked paper-only risk analysis. Because CP-10 did not train a
  model and CP-11 is `BLOCK_NO_MODEL`, the report records
  `analysis_status=BLOCK_NO_MODEL_OUTPUTS`,
  `ml_v2_model_outputs_available=False`, `strategy_tuning_performed=False`,
  `candidate_comparison_rerun=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No cost or
  concentration metric was invented, no strategy tuning, candidate comparison
  rerun, promotion/demotion, OOS rerun, data fetch, API call, news/SNS scrape,
  monthly plan regeneration, protected candidate change, broker work,
  production readiness change, push, or trading authorization was performed.
  Production remains `BLOCK` and protected candidate remains `PAPER_REVIEW`.
  Next ML v2 checkpoint: CP-13 ML v2 Shadow Scoring.
- ML v2 CP-11 Validation Report:
  `data/reports/ml_v2_validation_report.csv` and `.md` were added as a blocked
  paper-only validation report because CP-10 did not train an ML v2 model.
  `model_available=False`, `validation_status=BLOCK_NO_MODEL`,
  `oos_rerun_performed=False`, `candidate_promotion=False`,
  `order_output=False`, `broker_submission=False`, `trading_allowed=False`,
  and `production_effect=none`. No validation metrics, benchmark comparison,
  shadow score, order output, OOS rerun, data fetch, API call, news/SNS scrape,
  candidate comparison rerun, candidate creation, monthly plan regeneration,
  strategy parameter change, protected candidate change, broker work,
  production readiness change, push, or trading authorization was performed.
  Production remains `BLOCK` and protected candidate remains `PAPER_REVIEW`.
  Next ML v2 checkpoint: CP-12 ML v2 Cost / Concentration / Failure Analysis.
- ML v2 CP-10 Paper-Only Training Report:
  `data/reports/ml_v2_training_report.csv` and `.md` were added as a blocked
  paper-only training report because CP-09 returned `gate_result=BLOCK`.
  `model_training_performed=False`, `model_artifact_created=False`,
  `dataset_merge_performed=False`, `candidate_creation=False`,
  `candidate_promotion=False`, `broker_submission=False`,
  `order_execution=False`, `trading_allowed=False`, and
  `production_effect=none`. No model was trained, no feature matrix was merged,
  no score was produced, no candidate was created, no monthly plan was
  regenerated, no strategy parameter was changed, no protected candidate change
  occurred, no broker work occurred, no production readiness changed, no push
  occurred, and no trading authorization was performed. Production remains
  `BLOCK` and protected candidate remains `PAPER_REVIEW`. Next ML v2
  checkpoint: CP-11 ML v2 Validation Report.
- ML v2 CP-09 Training Readiness Gate:
  `data/reports/ml_v2_training_readiness_gate.csv` and `.md` were added as the
  explicit ML v2 paper-only training gate. The result is `gate_result=BLOCK`
  and `training_allowed_now=False` because CP-08 formulaic alpha merge
  readiness is `BLOCK`, feature values and final `feature_hash` values are not
  materialized, effective trial count is `not_available`, Deflated Sharpe is
  placeholder-only, `min_history244` PIT universe evidence is incomplete,
  post-cutoff OOS proof does not authorize review/promotion/production, and
  external overlays remain disabled-by-default risk overlays. No model
  training, dataset merge, formula evaluation, OOS rerun, data fetch, API call,
  news/SNS scrape, candidate comparison rerun, candidate creation, monthly plan
  regeneration, strategy parameter change, protected candidate change, broker
  work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `candidate_promotion=False`, `broker_submission=False`,
  `order_execution=False`, and `production_effect=none`. Next ML v2 checkpoint:
  CP-10 ML v2 Paper-Only Training blocked report.
- ML v2 CP-08 Formulaic Alpha Merge Readiness:
  `data/reports/ml_v2_formulaic_alpha_merge_readiness.csv` and `.md` were
  added as a paper-only readiness gate for merging CP-06 formulaic alpha
  samples into ML v2. The report records `merge_readiness=BLOCK`,
  materialized feature values `0`, materialized `feature_hash` values `0`, PIT
  aligned samples `0`, missingness-audited samples `0`, label-isolated samples
  `0`, `training_allowed_now=False`, `dataset_merge_performed=False`,
  `model_training_performed=False`, `candidate_creation=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. No dataset merge, model training, comparison,
  candidate creation, formula evaluation, OOS rerun, data fetch, API call,
  news/SNS scrape, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, production readiness change, push,
  or trading authorization was performed. Production remains `BLOCK`,
  protected candidate remains `PAPER_REVIEW`, `broker_submission=False`, and
  `order_execution=False`. Next ML v2 checkpoint: CP-09 ML v2 Training
  Readiness Gate.
- ML v2 CP-07 Formulaic Alpha Feature Audit:
  `data/reports/formulaic_alpha_feature_audit.csv` and `.md` were added as a
  paper-only audit of the six CP-06 formula samples. The audit confirms formula
  hashes and lookback metadata exist, but records `audit_status=BLOCK`,
  `feature_values_generated=False`, `merge_ready=False`,
  `training_allowed_now=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none` because PIT
  availability fields, assigned label horizons, concrete missingness policies,
  and materialized `feature_hash` values are not available. No formula
  evaluation, model training, formula selection, OOS rerun, data fetch, API
  call, news/SNS scrape, candidate comparison rerun, candidate creation,
  monthly plan regeneration, strategy parameter change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed. Production remains `BLOCK`, protected candidate
  remains `PAPER_REVIEW`, `broker_submission=False`, and
  `order_execution=False`. Next ML v2 checkpoint: CP-08 ML v2 Formulaic Alpha
  Merge Readiness.
- ML v2 CP-06 Small OHLCV Formulaic Alpha Sample Generation:
  `data/reports/formulaic_alpha_sample_generation.csv` and `.md` were added,
  and six `formulaic_alpha_sample` rows were appended to
  `data/reports/candidate_trial_ledger.csv` with `sample_only_no_eval`,
  deterministic formula hashes, `entered_comparison=False`,
  `candidate_promotion=False`, `trading_allowed=False`, and
  `production_effect=none`. The sample is bounded to 6 OHLCV-only formula
  strings and creates no feature values, evaluation metrics, model training,
  trading candidate, comparison result, order output, broker submission, or
  production effect. No OOS rerun, data fetch, API call, news/SNS scrape,
  monthly plan regeneration, strategy parameter change, protected candidate
  change, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `broker_submission=False`, and `order_execution=False`. Next
  ML v2 checkpoint: CP-07 Formulaic Alpha Feature Audit.
  Next ML v2 checkpoint: CP-07 Formulaic Alpha Feature Audit.
- ML v2 CP-05 Formulaic Alpha Candidate Inventory:
  `data/reports/formulaic_alpha_candidate_inventory.csv` and `.md` were added
  as a no-generation inventory of possible OHLCV-only formulaic alpha families.
  The inventory has 10 category rows, records `generated_candidate_count=0`,
  keeps `evaluation_performed=False`, `training_allowed_now=False`,
  `direct_buy_alpha_allowed=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`, and requires future
  formulas to have deterministic hashes plus candidate trial ledger rows before
  any bounded sample or sweep. External text/news/SNS/event inputs are rejected
  from formula generation and kept as risk-overlay-only. No formula generation,
  formula evaluation, model training, OOS rerun, data fetch, API call,
  news/SNS scrape, candidate comparison rerun, candidate creation, monthly plan
  regeneration, strategy parameter change, protected candidate change, broker
  work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `broker_submission=False`, and `order_execution=False`. Next
  ML v2 checkpoint: CP-06 Small OHLCV Formulaic Alpha Sample Generation.
  Next ML v2 checkpoint: CP-06 Small OHLCV Formulaic Alpha Sample Generation.
- ML v2 CP-04 min_history244 PIT Universe Safety Review:
  `data/reports/min_history244_pit_universe_safety_review.csv` and `.md` were
  added as a paper-only review of the protected candidate's relaxed
  `min_history244` PIT universe gate. Existing local reports show the protected
  candidate remains `PAPER_REVIEW`, `protected_from_tuning=True`,
  `promotion_allowed=False`, and `promoted_count=0`. The review records
  `safety_status=evidence_incomplete`, 1972 min-history-only eligible symbols,
  11 actually used symbols, 5 contribution-available symbols, and an empty
  post-cutoff universe filter evidence file, so it does not support promotion
  or production readiness. No parameter change, OOS rerun, data fetch, API
  call, news/SNS scrape, candidate comparison rerun, candidate creation,
  monthly plan regeneration, protected candidate change, broker work,
  production readiness change, push, or trading authorization was performed.
  Production remains `BLOCK`, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. Next ML v2 checkpoint: CP-05 Formulaic Alpha
  Candidate Inventory, No Generation.
- ML v2 CP-03 Post-Cutoff OOS Proof Inventory:
  `data/reports/post_cutoff_oos_proof_inventory.csv` and `.md` were added as a
  local-report-only inventory of existing post-cutoff/OOS/readiness evidence.
  The inventory records 12 source rows, all found locally, and keeps
  `oos_rerun_performed=False`, `data_fetch_performed=False`,
  `candidate_comparison_rerun=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. It preserves the
  protected candidate OOS state as `REVIEW_NOT_ALLOWED` and records missing
  evidence such as an approved post-cutoff OOS review result, complete
  protected-candidate observation window, complete effective trial count, and
  production readiness approval. No OOS rerun, data fetch, API call,
  news/SNS scrape, candidate comparison rerun, candidate creation, monthly plan
  regeneration, strategy parameter change, protected candidate change, broker
  work, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. Next ML v2 checkpoint: CP-04 min_history244 PIT
  Universe Safety Review.
- ML v2 CP-02 Purged / Embargo Validation Schema Plan:
  `data/reports/purged_embargo_validation_schema_plan.csv` and `.md` were
  added as a paper-only schema/design checkpoint before serious ML v2 training.
  The plan defines split identifiers, monthly-compatible date grouping, label
  horizon fields, purge window fields, embargo window fields, post-cutoff
  exclusion fields, PIT feature visibility fields, and leakage audit fields.
  Existing local baseline evidence is referenced only as design context; no
  validation rerun, OOS rerun, formula evaluation, model training, data fetch,
  API call, news/SNS scrape, candidate comparison rerun, candidate creation,
  monthly plan regeneration, strategy parameter change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization was performed. Production remains `BLOCK`, protected candidate
  remains `PAPER_REVIEW`, `trading_allowed=False`,
  `candidate_promotion=False`, `broker_submission=False`,
  `order_execution=False`, and `production_effect=none`. Next ML v2 checkpoint:
  CP-03 Post-Cutoff OOS Proof Inventory.
  Next ML v2 checkpoint: CP-03 Post-Cutoff OOS Proof Inventory.
- ML v2 CP-01 Deflated Sharpe placeholder report:
  `data/reports/deflated_sharpe_placeholder_report.csv` and `.md` were added
  as a paper-only data-snooping control placeholder before model selection or
  formulaic alpha sweeps. The report reserves required fields for raw Sharpe,
  skew, kurtosis, sample length, `raw_trial_count`, `effective_trial_count`,
  and a Deflated Sharpe adjusted-score placeholder, while explicitly recording
  that no Deflated Sharpe calculation, formula generation, formula evaluation,
  model training, model selection, OOS rerun, candidate comparison rerun,
  candidate creation, monthly plan regeneration, strategy parameter change,
  protected candidate change, broker work, data fetch, API call, news/SNS
  scrape, production readiness change, push, or trading authorization was
  performed. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. Next ML v2 checkpoint: CP-02 Purged / Embargo
  Validation Schema Plan.
- ML v2 quant hybrid model checkpoint roadmap:
  `docs/ml_v2_quant_hybrid_model_checkpoint.md` was added as the dedicated
  paper-only model checkpoint roadmap, and `docs/goal-mode-minimal-prompt.md`
  was simplified to reference it instead of carrying the full roadmap in every
  prompt. The roadmap starts at CP-01 Deflated Sharpe placeholder report and
  ends at CP-15 final ML v2 research packet, with one-checkpoint loop protocol,
  focused commits, no push, and stop-after-one-checkpoint guidance. Production
  remains `BLOCK`, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No model training, formula generation, formula
  evaluation, data fetch, API call, news/SNS scrape, OOS rerun, candidate
  comparison rerun, candidate creation, monthly plan regeneration, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization was performed.
- Candidate trial ledger bootstrap:
  `data/reports/candidate_trial_ledger.csv` and `.md`. This narrow
  ledger/bootstrap-only loop uses existing local `data/reports` artifacts and
  the candidate trial ledger schema plan to index known report/trial families:
  monthly baseline reports, protected `PAPER_REVIEW` candidate reports,
  rejected/blocked diagnostics where locally supported, monthly comparison
  reports, ML baseline dataset/training/validation reports, ML v1 reports, ML
  vs original comparison, fee/tax/slippage expectancy, month/symbol
  concentration, external source inventory, US quant math inventory, formulaic
  alpha schema plan, and trial ledger schema plan. The bootstrap ledger has 23
  rows, keeps source commands/dates/hashes as `not_available` where missing,
  reserves `raw_trial_count` and `effective_trial_count` placeholders, uses the
  explicit sourced `total_candidates_tested=5` only from
  `monthly_candidate_research_trial_summary.csv`, and does not calculate
  Deflated Sharpe. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No formula generation, formula evaluation,
  training, fetch, API call, news/SNS scrape, OOS rerun, candidate comparison
  rerun, new candidate, monthly plan regeneration, strategy parameter change,
  protected candidate modification, broker work, commit, or push was performed.
- Formulaic alpha schema and candidate trial ledger schema plan:
  `data/reports/formulaic_alpha_schema_plan.csv` and `.md`, plus
  `data/reports/candidate_trial_ledger_schema_plan.csv` and `.md`. This narrow
  schema/design-only loop defines OHLCV-only formulaic alpha inputs, allowed
  operators, disallowed leakage operators, lookback metadata, label horizon
  metadata, PIT availability checks, missingness policy, `feature_hash`,
  `formula_hash`, `operator_version`, and `parameter_summary`. It also defines
  the candidate trial ledger fields required before any alpha generation,
  sweep, comparison, or model selection, including reserved `raw_trial_count`
  and `effective_trial_count` placeholders for future Deflated Sharpe/data
  snooping controls. It recommends no formula sweep until the ledger exists, no
  model selection without trial counts, no Deflated Sharpe calculation yet, no
  production strategy output changes, and all outputs paper-only. Production
  remains `BLOCK`, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No formula generation, formula evaluation,
  training, fetch, API call, news/SNS scrape, OOS rerun, candidate comparison
  rerun, new candidate, monthly plan regeneration, strategy parameter change,
  protected candidate modification, broker work, commit, or push was performed.
- US quant math model research inventory:
  `data/reports/us_quant_math_model_research_inventory.csv` and `.md`. This
  narrow paper-only loop creates a US quant-style mathematical modeling
  research inventory covering Renaissance-style statistical modeling,
  WorldQuant-style formulaic alphas, cross-sectional ML ranking, factor models
  and timing, tree/ensemble ML, Gaussian process/Bayesian uncertainty,
  purged/embargo/CPCV validation, Deflated Sharpe/data-snooping controls,
  transaction cost/slippage realism, macro/news/SNS risk overlay, and
  LLM/agentic quant research as later-stage only. It recommends not copying
  Renaissance/WorldQuant blindly, starting with an OHLCV-only formulaic alpha
  inventory, adding candidate trial counts before large sweeps, adding a
  Deflated Sharpe placeholder before model selection, using purged/embargo
  validation before serious ML v2 training, keeping macro/news/SNS as
  risk-overlay-only, and keeping all outputs paper-only. Production remains
  `BLOCK`, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No training, fetch, API call, news/SNS scrape, OOS
  rerun, candidate comparison rerun, new candidate, monthly plan regeneration,
  strategy parameter change, protected candidate modification, broker work,
  commit, or push was performed.
- ML v2 external research source inventory:
  `data/reports/ml_v2_external_research_source_inventory.csv` and `.md`. This
  narrow paper-only loop creates a source-candidate inventory for macro data,
  market regime data, disclosure/event data, news data, CEO/related-person SNS
  data, sentiment model/open-source references, and validation/research papers.
  It recommends macro data first, OpenDART/Naver/GDELT event-news second,
  official CEO/company account whitelist third, and FinBERT/LLM/agentic models
  later-stage only. All external inputs remain risk-overlay-only and disabled
  by default. Production remains `BLOCK`, protected candidate remains
  `PAPER_REVIEW`, `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No fetch, API call, SNS/news scrape, scoring,
  training, OOS rerun, candidate comparison rerun, new candidate, monthly plan
  regeneration, strategy parameter change, protected candidate modification,
  broker work, commit, or push was performed.
- Month and symbol concentration report:
  `data/reports/month_symbol_concentration_report.csv` and `.md`. This narrow
  paper-only loop used existing local `data/reports` artifacts only to compare
  the existing monthly baseline, protected `PAPER_REVIEW` candidate, and ML v1
  where compatible. It records that the baseline has month and symbol
  attribution detail, the protected candidate has saved concentration summary
  detail but lacks compatible top-symbol attribution, and ML v1 lacks saved
  month/symbol return-contribution artifacts. Production remains `BLOCK` /
  non-live, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No fetch, OOS rerun, candidate comparison rerun,
  new candidate, monthly plan regeneration, strategy parameter change,
  protected candidate modification, broker work, commit, or push was performed.
- Fee/tax/slippage-adjusted expectancy report:
  `data/reports/fee_tax_slippage_adjusted_expectancy_report.csv` and `.md`.
  This narrow paper-only loop used existing local `data/reports` artifacts only,
  including saved monthly expectancy/performance/gate reports, protected
  candidate blocked order-cost/risk/review reports, paper-operation safety
  status, and ML v1 validation/observation reports as read-only research rows.
  It records unavailable fields explicitly rather than inventing missing
  fee/tax/slippage/true expectancy components. Production remains `BLOCK` /
  non-live, protected candidate remains `PAPER_REVIEW`,
  `trading_allowed=False`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`, and
  `production_effect=none`. No fetch, OOS rerun, candidate comparison rerun,
  new candidate, monthly plan regeneration, strategy parameter change,
  protected candidate modification, broker work, commit, or push was performed.
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
- codebase-memory-mcp Codex MCP connection:
  after explicit connection approval, a minimal
  `[mcp_servers.codebase-memory-mcp]` entry was added to
  `C:\Users\KangMinWoo\.codex\config.toml` pointing at the existing
  binary-only install. The automatic `codebase-memory-mcp install` path was not
  used because dry-run prompted for index deletion. No reinstall, PATH change,
  automatic agent setup, reindex, network download, trading/ML behavior
  change, protected candidate change, production readiness change, or push was
  performed. `auto_index=false` remains set, and the existing indexed project
  remains `C-tmp-toss-cbm-project`.
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
