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
