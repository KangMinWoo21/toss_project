# ML v2 Quant Hybrid Model Checkpoint

## Purpose

This file is the dedicated roadmap for completing the paper-only ML v2 quant
hybrid model work without carrying the full roadmap in every future prompt. It
organizes the remaining loops into one-checkpoint increments and keeps the
project non-live.

## Global Safety Gates

- Production remains `BLOCK`.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `candidate_promotion=False`.
- `broker_submission=False`.
- `order_execution=False`.
- `production_effect=none`.
- Do not train a model unless the relevant readiness gate explicitly allows it.
- Do not fetch data, call APIs, scrape news/SNS, rerun OOS, rerun candidate
  comparison, create a candidate, regenerate monthly plans, change strategy
  parameters, or modify the protected `PAPER_REVIEW` candidate.
- Do not open, print, summarize, copy, commit, or otherwise expose `.env` or
  secrets.

## Current Completed State

Completed paper-only groundwork through the candidate trial ledger bootstrap:

- ML v1 local technical-feature research packet exists and remains paper-only.
- External source inventory exists for ML v2 hybrid overlays; all external
  inputs remain disabled-by-default risk overlays.
- US quant math model inventory exists and recommends formulaic OHLCV schema
  design before any alpha sweep.
- Formulaic alpha schema plan exists; no formulaic alpha candidates have been
  generated.
- Candidate trial ledger schema plan exists with `raw_trial_count` and
  `effective_trial_count` placeholders.
- Candidate trial ledger bootstrap exists from local reports only; it does not
  calculate Deflated Sharpe and does not promote or demote candidates.

## Final Target

The final target is a paper-only ML v2 quant hybrid model research packet. It
may combine existing local technical features, audited formulaic OHLCV features,
validation controls, cost/concentration/failure analysis, shadow scoring, and a
disabled-by-default hybrid overlay design. It is not live-ready and must not
authorize trading.

## Loop Protocol

1. Read `docs/GOAL_MODE_CHECKPOINT.md` and this file first.
2. Identify the earliest incomplete checkpoint.
3. Complete exactly one checkpoint.
4. Update `docs/GOAL_MODE_CHECKPOINT.md` briefly.
5. Run schema/content checks for generated reports or docs.
6. Run tests only if code changed.
7. Commit only focused files for the completed checkpoint.
8. Do not push.

## Stop Condition

Stop after one checkpoint and one commit. The next loop starts by finding the
earliest incomplete checkpoint again.

## Checkpoints

### CP-01 Deflated Sharpe Placeholder Report

- Goal: reserve data-snooping control fields before model selection.
- Deliverables: `data/reports/deflated_sharpe_placeholder_report.csv` and `.md`.
- Completion conditions: documents required fields for raw Sharpe, skew,
  kurtosis, sample length, `raw_trial_count`, `effective_trial_count`, and
  adjusted score placeholder; does not calculate Deflated Sharpe.
- Forbidden actions: no formula generation, model training, model selection,
  OOS rerun, or candidate promotion/demotion.
- Commit message: `Add Deflated Sharpe placeholder report`.
- Next checkpoint entry condition: placeholder report passes schema/content
  checks and checkpoint is briefly recorded.

### CP-02 Purged / Embargo Validation Schema Plan

- Goal: define leakage-safe validation schema before serious ML v2 training.
- Deliverables: `data/reports/purged_embargo_validation_schema_plan.csv` and
  `.md`.
- Completion conditions: defines label horizon, purge window, embargo window,
  split identifiers, date grouping, and post-cutoff exclusion flags.
- Forbidden actions: no validation rerun, OOS rerun, formula evaluation, or
  training.
- Commit message: `Add purged embargo validation schema plan`.
- Next checkpoint entry condition: schema/content check confirms required
  fields and forbidden-action notes.

### CP-03 Post-Cutoff OOS Proof Inventory

- Goal: inventory existing post-cutoff/OOS proof reports without rerunning OOS.
- Deliverables: `data/reports/post_cutoff_oos_proof_inventory.csv` and `.md`.
- Completion conditions: lists existing proof/readiness artifacts, evidence
  fields, missing fields, and review status using local reports only.
- Forbidden actions: no OOS rerun, no data fetch, no candidate comparison, no
  protected candidate status change.
- Commit message: `Add post-cutoff OOS proof inventory`.
- Next checkpoint entry condition: inventory check confirms all cited sources
  exist or are marked `not_available`.

### CP-04 min_history244 PIT Universe Safety Review

- Goal: review the protected candidate's `min_history244` PIT universe safety
  constraints without changing them.
- Deliverables: `data/reports/min_history244_pit_universe_safety_review.csv`
  and `.md`.
- Completion conditions: documents PIT universe assumptions, known safeguards,
  known risks, and unresolved evidence gaps.
- Forbidden actions: no parameter change, no candidate modification, no OOS
  rerun, no promotion/demotion.
- Commit message: `Add min_history244 PIT universe safety review`.
- Next checkpoint entry condition: report confirms protected candidate remains
  `PAPER_REVIEW`.

### CP-05 Formulaic Alpha Candidate Inventory, No Generation

- Goal: create an inventory structure for possible formulaic alpha families
  without generating formulas.
- Deliverables: `data/reports/formulaic_alpha_candidate_inventory.csv` and
  `.md`.
- Completion conditions: lists categories, allowed inputs/operators, required
  hashes, trial-ledger links, and rejection reasons; no concrete formula
  candidates are generated.
- Forbidden actions: no formula generation, formula evaluation, alpha sweep, or
  model selection.
- Commit message: `Add formulaic alpha candidate inventory`.
- Next checkpoint entry condition: inventory records zero generated candidates.

### CP-06 Small OHLCV Formulaic Alpha Sample Generation

- Goal: generate a small, bounded, paper-only OHLCV formula sample only after
  CP-01 through CP-05 are complete.
- Deliverables: `data/reports/formulaic_alpha_sample_generation.csv` and `.md`.
- Completion conditions: sample count is explicitly bounded, formulas are
  hashed, ledger rows are added, and no evaluation metrics are computed.
- Forbidden actions: no formula evaluation, model training, OOS rerun,
  candidate creation, or production output.
- Commit message: `Add small formulaic alpha sample`.
- Next checkpoint entry condition: sample-generation report confirms no
  evaluation occurred.

### CP-07 Formulaic Alpha Feature Audit

- Goal: audit generated formulaic features for PIT, missingness, hashes, and
  leakage controls.
- Deliverables: `data/reports/formulaic_alpha_feature_audit.csv` and `.md`.
- Completion conditions: checks PIT availability, lookback metadata, label
  isolation, missingness policy, `feature_hash`, and `formula_hash`.
- Forbidden actions: no model training, no formula selection, no OOS rerun, and
  no strategy changes.
- Commit message: `Add formulaic alpha feature audit`.
- Next checkpoint entry condition: audit marks readiness or blockers without
  training.

### CP-08 ML v2 Formulaic Alpha Merge Readiness

- Goal: decide whether audited formulaic features are ready to merge into an ML
  v2 training dataset.
- Deliverables: `data/reports/ml_v2_formulaic_alpha_merge_readiness.csv` and
  `.md`.
- Completion conditions: documents coverage, missingness, PIT alignment, trial
  ledger linkage, and merge blockers.
- Forbidden actions: no dataset merge for training, no training, no comparison,
  no candidate creation.
- Commit message: `Add ML v2 formulaic alpha merge readiness`.
- Next checkpoint entry condition: readiness report explicitly allows or blocks
  CP-09.

### CP-09 ML v2 Training Readiness Gate

- Goal: gate whether ML v2 paper-only training is allowed.
- Deliverables: `data/reports/ml_v2_training_readiness_gate.csv` and `.md`.
- Completion conditions: evaluates local data readiness, validation readiness,
  cost controls, trial counts, leakage controls, and external overlay status.
- Forbidden actions: no training unless the gate is the deliverable saying a
  future training loop is allowed; no strategy or candidate changes.
- Commit message: `Add ML v2 training readiness gate`.
- Next checkpoint entry condition: gate result is explicit `ALLOW_PAPER_ONLY`
  or `BLOCK`.

### CP-10 ML v2 Paper-Only Training, Only If Gate Allows

- Goal: train ML v2 only if CP-09 explicitly allows paper-only training.
- Deliverables: `data/reports/ml_v2_training_report.csv` and `.md`.
- Completion conditions: records approved feature set, split policy, trial
  counts, leakage checks, and `production_effect=none`.
- Forbidden actions: no training if CP-09 is `BLOCK`; no broker work, monthly
  plan regeneration, candidate creation, or promotion.
- Commit message: `Add ML v2 paper-only training report`.
- Next checkpoint entry condition: training report exists only with CP-09
  approval; otherwise record a blocked report.

### CP-11 ML v2 Validation Report

- Goal: validate the ML v2 paper-only model with approved validation controls.
- Deliverables: `data/reports/ml_v2_validation_report.csv` and `.md`.
- Completion conditions: documents split policy, leakage checks, benchmark
  context, and paper-only status.
- Forbidden actions: no OOS rerun unless explicitly part of approved validation
  source; no candidate promotion, no order output.
- Commit message: `Add ML v2 validation report`.
- Next checkpoint entry condition: validation report records pass/block status
  without production effect.

### CP-12 ML v2 Cost / Concentration / Failure Analysis

- Goal: analyze cost realism, concentration, and failures for ML v2.
- Deliverables: `data/reports/ml_v2_cost_concentration_failure_analysis.csv`
  and `.md`.
- Completion conditions: documents cost assumptions, concentration risks,
  failure modes, missing evidence, and blocked status where applicable.
- Forbidden actions: no strategy tuning, no candidate comparison rerun, no
  promotion/demotion.
- Commit message: `Add ML v2 cost concentration failure analysis`.
- Next checkpoint entry condition: analysis confirms no production output
  changes.

### CP-13 ML v2 Shadow Scoring

- Goal: produce paper-only shadow scoring only after validation and risk checks
  allow it.
- Deliverables: `data/reports/ml_v2_shadow_scoring_report.csv` and `.md`.
- Completion conditions: scores are human-readable research outputs only, no
  order output, no broker submission, and no monthly plan regeneration.
- Forbidden actions: no live scoring path, no trading authorization, no
  candidate promotion.
- Commit message: `Add ML v2 shadow scoring report`.
- Next checkpoint entry condition: report states `order_output=False` and
  `broker_submission=False`.

### CP-14 ML v2 Hybrid Overlay Design

- Goal: design the hybrid overlay combining ML v2 with disabled-by-default risk
  overlays.
- Deliverables: `data/reports/ml_v2_hybrid_overlay_design.csv` and `.md`.
- Completion conditions: documents macro/news/SNS overlay roles, default-off
  gates, manual review controls, and privacy/terms risks.
- Forbidden actions: no external fetch, no news/SNS scrape, no LLM scoring, no
  strategy parameter change.
- Commit message: `Add ML v2 hybrid overlay design`.
- Next checkpoint entry condition: design confirms all overlays are
  risk-overlay-only and disabled by default.

### CP-15 Final ML v2 Research Packet

- Goal: consolidate CP-01 through CP-14 into the final paper-only ML v2 packet.
- Deliverables: `data/reports/ml_v2_final_research_packet.csv` and `.md`.
- Completion conditions: summarizes readiness, blockers, leakage controls,
  costs, validation, shadow scoring, overlay design, and final paper-only
  recommendation.
- Forbidden actions: no production readiness change, no promotion, no broker
  work, no push unless separately approved.
- Commit message: `Add final ML v2 research packet`.
- Next checkpoint entry condition: no next checkpoint; stop with paper-only
  final packet and `production_effect=none`.

## Post-CP-15 Blocker-Resolution Checkpoints

### POST-01 Stage 1 Paper-Only Experiment Gate Design

- Goal: define the gate that decides whether the Stage 1 broader formulaic
  feature table can support a future bounded paper-only experiment.
- Deliverables:
  `data/reports/ml_v2_stage1_paper_experiment_gate_design.csv` and `.md`.
- Completion conditions: documents required inputs, allowable experiment
  boundaries, required blocker checks, explicit `ALLOW_PAPER_ONLY_EXPERIMENT`
  versus `BLOCK` outcomes, and no-production safety fields.
- Forbidden actions: no model training, formula evaluation, dataset merge,
  candidate creation, OOS rerun, candidate comparison rerun, strategy change,
  protected candidate change, broker work, or production readiness change.
- Checks: schema/content check confirms gate outcomes, safety fields, source
  references, and blocked/deferred handling.
- Commit message: `Add ML v2 stage 1 experiment gate design`.
- Next checkpoint entry condition: gate design exists and a future POST
  checkpoint can execute the gate as a report-only readiness decision.

### POST-02 Stage 1 Paper-Only Experiment Gate Execution

- Goal: execute the POST-01 gate as a report-only readiness decision for a
  future bounded paper-only experiment.
- Deliverables:
  `data/reports/ml_v2_stage1_paper_experiment_gate.csv` and `.md`.
- Completion conditions: returns exactly one of `ALLOW_PAPER_ONLY_EXPERIMENT`,
  `BLOCK`, or `deferred_later_stage`; documents sources, blockers, allowed
  future action, and safety fields.
- Forbidden actions: no model training, formula evaluation, dataset merge,
  candidate creation, OOS rerun, candidate comparison rerun, strategy change,
  protected candidate change, broker work, or production readiness change.
- Checks: schema/content check confirms exact gate result vocabulary, safety
  fields, source references, and no forbidden actions.
- Commit message: `Add ML v2 stage 1 experiment gate`.
- Next checkpoint entry condition: if gate result is
  `ALLOW_PAPER_ONLY_EXPERIMENT`, a future POST checkpoint may design the tiny
  experiment protocol; otherwise future work must address blockers first.

### POST-03 Stage 1 Tiny Experiment Protocol Design

- Goal: design the tiny paper-only experiment protocol allowed by POST-02
  without executing training or evaluation.
- Deliverables:
  `data/reports/ml_v2_stage1_tiny_experiment_protocol.csv` and `.md`.
- Completion conditions: defines input scope, split placeholders, allowed
  outputs, disallowed metrics, failure handling, and safety fields.
- Forbidden actions: no model training, formula evaluation, dataset merge for
  training, candidate creation, OOS rerun, candidate comparison rerun, strategy
  change, protected candidate change, broker work, or production readiness
  change.
- Checks: schema/content check confirms protocol boundaries, safety fields, and
  no training/evaluation authorization.
- Commit message: `Add ML v2 stage 1 tiny experiment protocol`.
- Next checkpoint entry condition: protocol design exists; a future POST
  checkpoint may create a report-only experiment execution gate.

### POST-04 Stage 1 Tiny Experiment Execution Gate

- Goal: decide whether the POST-03 tiny experiment protocol may proceed to
  paper-only execution, without running training, evaluation, scoring, or
  feature selection in this checkpoint.
- Deliverables:
  `data/reports/ml_v2_stage1_tiny_experiment_execution_gate.csv` and `.md`.
- Completion conditions: returns exactly one of
  `ALLOW_PAPER_ONLY_TINY_EXPERIMENT`, `BLOCK`, or `deferred_later_stage`;
  documents source evidence, unresolved blockers, allowed future action,
  blocked action, and all no-production safety fields.
- Forbidden actions: no model training, formula evaluation, dataset merge for
  training, feature selection, performance metric computation, candidate
  creation, OOS rerun, candidate comparison rerun, strategy change, protected
  candidate change, broker work, or production readiness change.
- Checks: schema/content check confirms result vocabulary, source references,
  blocker handling, and safety fields.
- Commit message: `Add ML v2 stage 1 tiny experiment execution gate`.
- Next checkpoint entry condition: if the gate result is
  `ALLOW_PAPER_ONLY_TINY_EXPERIMENT`, a future POST checkpoint may execute the
  bounded paper-only experiment; otherwise future work must resolve or defer
  the blockers before any experiment execution.

### POST-05 Post-CP-15 Completion Packet

- Goal: consolidate CP-01 through CP-15 and POST-01 through POST-04 into a
  final post-CP-15 paper-only completion packet.
- Deliverables:
  `data/reports/ml_v2_post_cp15_completion_packet.csv` and `.md`.
- Completion conditions: summarizes checkpoints, commits, blockers, gates,
  feature coverage, PIT/leakage, trial ledger, Deflated Sharpe, cost,
  concentration, failure analysis, overlay, and final recommendation. Final
  recommendation must be one of `paper_only_complete_not_live_ready`,
  `paper_only_complete_blocked_not_live_ready`, or
  `paper_only_incomplete_blocked`.
- Forbidden actions: no model training, formula evaluation, data fetch, API
  call, SNS/news scrape, OOS rerun, candidate comparison rerun, candidate
  creation, monthly plan regeneration, strategy change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization.
- Checks: schema/content check confirms packet coverage, final recommendation
  vocabulary, source references, blocked/deferred handling, and safety fields.
- Commit message: `Add ML v2 post-CP15 completion packet`.
- Next checkpoint entry condition: no next checkpoint unless a user explicitly
  authorizes a new research goal; stop with paper-only blocked-not-live-ready
  status.

### POST-06 Trial Count And Deflated Sharpe Blocker Audit

- Goal: audit whether existing local reports are sufficient to unblock ML v2
  training with trial-count and Deflated Sharpe controls, without calculating
  performance metrics or running training.
- Deliverables:
  `data/reports/ml_v2_trial_count_deflated_sharpe_blocker_audit.csv` and
  `.md`.
- Completion conditions: documents ledger row counts, numeric raw-trial
  lower-bound evidence, unavailable effective-trial counts, Deflated Sharpe
  required inputs, blocked/deferred status, and the next safe action.
- Forbidden actions: no model training, formula evaluation, performance metric
  computation, data fetch, API call, SNS/news scrape, OOS rerun, candidate
  comparison rerun, candidate creation, monthly plan regeneration, strategy
  change, protected candidate change, broker work, production readiness change,
  push, or trading authorization.
- Checks: schema/content check confirms count evidence, missing-input handling,
  final gate result, and no-production safety fields.
- Commit message: `Add ML v2 trial count Deflated Sharpe blocker audit`.
- Next checkpoint entry condition: if blocker status remains `BLOCK`, future
  work may only design a dependency-adjusted effective-trial-count method or a
  blocked training-readiness refresh.

### POST-07 Effective Trial Count Method Design

- Goal: design a paper-only method for deriving a future effective trial count
  from the candidate trial ledger without calculating the count yet.
- Deliverables:
  `data/reports/ml_v2_effective_trial_count_method_design.csv` and `.md`.
- Completion conditions: defines grouping keys, dependency rules,
  non-independent trial families, lower-bound and upper-bound policies,
  missing-evidence handling, audit fields, and blocked training status.
- Forbidden actions: no effective-trial-count calculation, Deflated Sharpe
  calculation, model training, formula evaluation, performance metric
  computation, data fetch, API call, OOS rerun, candidate comparison rerun,
  candidate creation, strategy change, protected candidate change, broker work,
  production readiness change, push, or trading authorization.
- Checks: schema/content check confirms method fields, no calculated effective
  count, blocked training status, and no-production safety fields.
- Commit message: `Add ML v2 effective trial count method design`.
- Next checkpoint entry condition: method design exists; a future checkpoint may
  apply it as a report-only count estimate before any training gate is reopened.

### POST-08 Trial Dependency Group Manifest

- Goal: apply the POST-07 grouping method to the existing candidate trial
  ledger as a report-only dependency group manifest, without calculating
  effective trial count or Deflated Sharpe.
- Deliverables:
  `data/reports/ml_v2_trial_dependency_group_manifest.csv` and `.md`.
- Completion conditions: lists dependency groups, group keys, member counts,
  raw-count lower-bound evidence, unresolved lineage flags, and blocked
  training status.
- Forbidden actions: no effective-trial-count calculation, Deflated Sharpe
  calculation, model training, formula evaluation, performance metric
  computation, data fetch, API call, OOS rerun, candidate comparison rerun,
  candidate creation, strategy change, protected candidate change, broker work,
  production readiness change, push, or trading authorization.
- Checks: schema/content check confirms manifest rows, group counts, no
  effective-count calculation, blocked training status, and no-production
  safety fields.
- Commit message: `Add ML v2 trial dependency group manifest`.
- Next checkpoint entry condition: manifest exists; a future checkpoint may
  produce a blocked training-readiness refresh or an exact raw-count inventory.

### POST-09 Training Readiness Refresh After Trial Manifest

- Goal: refresh the ML v2 training-readiness gate using POST-06 and POST-08
  trial-count evidence, without training or validating ML v2.
- Deliverables:
  `data/reports/ml_v2_training_readiness_after_trial_manifest.csv` and `.md`.
- Completion conditions: states whether training is allowed, references the
  blocker audit and dependency manifest, preserves safety fields, and documents
  the next safe blocker-resolution action.
- Forbidden actions: no model training, validation run, formula evaluation,
  performance metric computation, data fetch, API call, OOS rerun, candidate
  comparison rerun, candidate creation, strategy change, protected candidate
  change, broker work, production readiness change, push, or trading
  authorization.
- Checks: schema/content check confirms gate vocabulary, source references,
  blocked training status, and no-production safety fields.
- Commit message: `Refresh ML v2 training readiness after trial manifest`.
- Next checkpoint entry condition: if still `BLOCK`, stop unless the user
  explicitly asks for exact raw-count inventory or another paper-only blocker
  analysis.

### POST-10 Exact Raw Count Inventory

- Goal: inventory exact raw-trial-count evidence from the existing candidate
  trial ledger and referenced local reports without inferring counts from report
  row counts.
- Deliverables:
  `data/reports/ml_v2_exact_raw_count_inventory.csv` and `.md`.
- Completion conditions: records ledger rows, source existence, source row-count
  audit evidence, exact numeric raw-count rows, missing exact-count rows,
  lower-bound total, blocked training/validation status, and next safe action.
- Forbidden actions: no model training, validation run, formula evaluation,
  effective-trial-count calculation, Deflated Sharpe calculation, performance
  metric computation, data fetch, API call, OOS rerun, candidate comparison
  rerun, candidate creation, strategy change, protected candidate change,
  broker work, production readiness change, push, or trading authorization.
- Checks: schema/content check confirms exact-count evidence, lower-bound
  handling, missing-count handling, source references, and no-production safety
  fields.
- Commit message: `Add ML v2 exact raw count inventory`.
- Next checkpoint entry condition: inventory exists; the next checkpoint should
  resolve lineage warnings or keep training blocked.

### POST-11 Trial Lineage Resolution Audit

- Goal: classify trial dependency groups as resolved, unresolved, or
  manual-review-required using the exact raw-count inventory and dependency
  manifest.
- Deliverables:
  `data/reports/ml_v2_trial_lineage_resolution_audit.csv` and `.md`.
- Completion conditions: records dependency group resolution status, missing
  lineage fields, exact raw-count status, lower-bound evidence, blocked
  effective-count status, blocked training/validation status, and next safe
  action.
- Forbidden actions: no model training, validation run, formula evaluation,
  effective-trial-count calculation, Deflated Sharpe calculation, performance
  metric computation, data fetch, API call, OOS rerun, candidate comparison
  rerun, candidate creation, strategy change, protected candidate change,
  broker work, production readiness change, push, or trading authorization.
- Checks: schema/content check confirms resolution counts, no effective-count
  calculation, blocked training/validation status, and no-production safety
  fields.
- Commit message: `Add ML v2 trial lineage resolution audit`.
- Next checkpoint entry condition: if lineage remains unresolved, create a
  BLOCK effective-trial-count estimate report or require manual review.
