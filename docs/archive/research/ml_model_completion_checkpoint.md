# Paper-Only ML Model Completion Checkpoint

## Technical Summary

This checkpoint is a doc-only roadmap for completing a paper-only ML research
model through Goal mode loops. It is not a training run, not an OOS rerun, not a
candidate review, and not a production-readiness change.

Current status:

- `production=BLOCK / not live-ready`
- `protected_candidate=PAPER_REVIEW`
- `OOS review eligibility=REVIEW_NOT_ALLOWED`
- `trading_allowed=False`
- `review_allowed=False`
- `production_effect=none`
- Current local data is ready only for `baseline_tabular_ml`.
- Phase 6 limited OpenDART PIT audit is complete and remains
  `training_allowed_now=False`.
- Phase 7 financial feature merge audit is complete. The limited financial
  sample did not join to the current baseline sample (`join_coverage=WARN 0/5`,
  `missing_rate=WARN 1.0000`), but leakage and safety checks passed and
  `feature_added_to_training=False`.
- Phase 8 news event schema plan is complete and remains fetch-free with
  `fetch_allowed_now=False` and `feature_added_to_training=False`.
- Phase 9 sentiment scoring plan is complete. It is rule/lexicon-only with
  `model_version=rule_lexicon_v1`, `training_allowed_now=False`, and
  FinBERT/LLM kept later-stage.
- Phase 10 external feature readiness re-audit is complete. Financial, news,
  and sentiment features remain `not_ready`; overall readiness is `BLOCK` and
  `training_allowed=False`.
- Phase 11 ML model experiment v1 is complete as a technical-only paper model.
  External features remain excluded because Phase 10 readiness is `BLOCK`.
- Phase 12 shadow scoring report is complete. Scores are human-readable
  paper-only tables with no order output, broker submission, monthly plan
  regeneration, or candidate promotion.
- Phase 13 observation status is complete using explicitly requested
  historical backfill from existing local baseline feature/label rows:
  `observation_basis=historical_backfill`, `observation_months=101`,
  `sufficient_observation_months=True`, `post_cutoff_train_leakage=PASS`, and
  `performance_stability=historical_backfill_stable`.
- Phase 14 final paper-only ML research packet is complete in
  `data/reports/ml_model_research_packet.csv` and `.md`:
  `model_completion_status=paper_only_complete_not_live_ready`,
  `trading_allowed=False`, `production_effect=none`,
  `candidate_promotion=False`, `broker_submission=False`,
  `order_execution=False`, `production_readiness_change=False`, production
  `BLOCK` retained, and protected candidate unchanged.
- Financial features have only a limited PIT-audited sample and are not ready
  for training; news and sentiment features remain plan-only.
- Deep learning is `not_ready`.

Model completion means the paper-only ML research model has dataset lineage,
training, validation, explanation, and observation reports. It does not mean
the model is live-tradable. Production readiness changes, candidate promotion,
broker submission, and order execution remain forbidden unless a separate
explicit approval authorizes a new goal.

## Global Safety Gates

These gates apply to every phase below:

- No real trading, Toss API calls, broker submission, or order execution.
- No strategy parameter changes.
- No protected `PAPER_REVIEW` candidate modification, promotion, tuning, or
  replacement.
- No OOS rerun unless a future goal explicitly authorizes it.
- No data fetch or API call unless a future goal explicitly authorizes the
  specific limited fetch.
- No candidate compare, new candidate generation, or monthly plan regeneration.
- Never open, print, summarize, or commit `.env` or API keys.
- Keep `trading_allowed=False` and `production_effect=none`.
- Keep production `BLOCK` until a separate approved readiness process says
  otherwise.

## Phase 0. Safety Base 유지

Goal:

- Confirm every ML task remains paper-only and research-only.

Deliverables:

- Safety status stays documented in the current checkpoint and local reports.

Completion conditions:

- Production `BLOCK` is retained.
- Protected candidate remains `PAPER_REVIEW`.
- `trading_allowed=False`.
- `production_effect=none`.

Forbidden in this phase:

- Model training, OOS rerun, fetch, candidate changes, broker work, or
  production enablement.

Next phase entry condition:

- Proceed only to ML feature/label dataset scaffold.

## Phase 1. Baseline Feature/Label Dataset

Goal:

- Build a baseline tabular ML dataset from existing local OHLCV/PIT data.

Deliverables:

- `data/reports/ml_baseline_feature_label_dataset_audit.csv`
- `data/reports/ml_baseline_feature_label_dataset_audit.md`
- Optional sample: `data/reports/ml_baseline_feature_label_sample.csv`

Completion conditions:

- `train_cutoff=2026-06-18`.
- `post_cutoff_data_used_for_train=False`.
- Feature missing rates are recorded.
- Label distribution is recorded.
- `training_ran=False`.
- `trading_allowed=False`.

Forbidden in this phase:

- Model training, post-cutoff train usage, OOS rerun, fetch, candidate compare,
  or strategy parameter changes.

Next phase entry condition:

- Dataset audit confirms deterministic baseline features, PIT universe
  availability, label generation, and no post-cutoff train leakage.

## Phase 2. Baseline Model Training Scaffold

Goal:

- Train the simplest paper-only baseline among Logistic Regression, Random
  Forest, or LightGBM candidates, starting conservatively.

Deliverables:

- `data/reports/ml_baseline_model_training_report.csv`
- `data/reports/ml_baseline_model_training_report.md`

Completion conditions:

- Train/validation split uses only pre-cutoff data.
- No post-cutoff OOS data is used.
- Any model artifact remains disconnected from production.
- `trading_allowed=False`.
- `production_effect=none`.

Forbidden in this phase:

- Candidate promotion, broker integration, production linkage, protected
  candidate changes, or post-cutoff leakage.

Next phase entry condition:

- Training report proves the scaffold is paper-only, deterministic, and
  separated from production.

## Phase 3. ML Validation Report

Goal:

- Evaluate the baseline ML model using a monthly walk-forward-style validation
  report.

Deliverables:

- `data/reports/ml_baseline_validation_report.csv`
- `data/reports/ml_baseline_validation_report.md`

Completion conditions:

- Leakage check `PASS`.
- PIT universe check `PASS`.
- Feature availability check `PASS`.
- Benchmark-relative performance, drawdown, hit-rate, and turnover are recorded.
- Existing protected candidate may be used as a read-only comparison reference,
  but candidate modification or promotion is not performed.

Forbidden in this phase:

- OOS rerun, candidate tuning, candidate promotion, monthly plan regeneration,
  or production changes.

Next phase entry condition:

- Validation report is complete enough to support feature importance and failure
  analysis without changing candidate status.

## Phase 4. ML Explainability & Failure Analysis

Goal:

- Analyze which features the model depends on and where it fails.

Deliverables:

- `data/reports/ml_feature_importance_report.csv`
- `data/reports/ml_failure_analysis_report.csv`

Completion conditions:

- Feature importance is recorded.
- Regime-level performance is recorded.
- Failure months and failure symbols are recorded.
- Overfit risk note is written.

Forbidden in this phase:

- Strategy parameter edits, candidate tuning, promotion, production linkage, or
  trading authorization.

Next phase entry condition:

- Failure analysis identifies what can be learned from the baseline before any
  external data is introduced.

## Phase 5. OpenDART Financial Feature Schema

Goal:

- Design a PIT-safe schema for OpenDART financial and disclosure features.
- Do not fetch data in this phase.

Deliverables:

- `data/reports/ml_financial_feature_schema_plan.csv`
- `data/reports/ml_financial_feature_schema_plan.md`

Completion conditions:

- `receipt_date`, `receipt_time`, `collected_at`, and `usable_from` are defined.
- Correction filing lineage is defined.
- `api_key_required` is recorded.
- `fetch_allowed_now=False`.
- `training_allowed_now=False`.

Forbidden in this phase:

- API calls, fetch, `.env` access, training, candidate compare, or production
  changes.

Next phase entry condition:

- Proceed to limited OpenDART fetch only after the user explicitly approves that
  specific future goal.

## Phase 6. Limited OpenDART Fetch & PIT Audit

Goal:

- After explicit user approval, collect a limited OpenDART sample and verify
  PIT-safe `usable_from` handling.

Deliverables:

- `data/reports/ml_financial_observations_sample.csv`
- `data/reports/ml_financial_pit_audit.csv`
- `data/reports/ml_financial_feature_readiness_report.md`

Completion conditions:

- API key is not printed, summarized, or committed.
- `usable_from` exists.
- Correction filings are handled.
- `training_allowed_now=False` until readiness passes.

Forbidden in this phase:

- Unapproved fetch, key exposure, training, candidate changes, broker work, or
  production changes.

Next phase entry condition:

- PIT audit confirms the sample can be safely evaluated for merge readiness.

## Phase 7. Financial Feature Merge Audit

Goal:

- Verify whether financial features can be merged into the baseline ML dataset.
- Do not judge model improvement yet.

Deliverables:

- `data/reports/ml_financial_feature_merge_audit.csv`
- `data/reports/ml_financial_feature_merge_audit.md`

Completion conditions:

- Join coverage is recorded.
- Missing rate is recorded.
- Leakage check `PASS`.
- No post-cutoff train usage.
- `feature_added_to_training=False` unless a future explicit approval says
  otherwise.
- Completed 2026-06-30 in
  `data/reports/ml_financial_feature_merge_audit.csv` and `.md`.
  Actual result: `join_coverage=WARN 0/5`, `missing_rate=WARN 1.0000`,
  `leakage_check=PASS`, `post_cutoff_data_used_for_train=False`,
  `feature_added_to_training=False`, `training_allowed_now=False`,
  `trading_allowed=False`, `production_effect=none`.

Forbidden in this phase:

- Model improvement claims, candidate promotion, strategy parameter changes,
  OOS rerun, or production changes.

Next phase entry condition:

- Merge audit shows whether financial features are technically ready for a
  future approved experiment.

## Phase 8. News Event Schema Plan

Goal:

- Design the news event feature schema.
- Clarify Naver News, GDELT, and manual calendar candidates.
- Do not fetch data in this phase.

Deliverables:

- `data/reports/ml_news_event_schema_plan.csv`
- `data/reports/ml_news_event_schema_plan.md`

Completion conditions:

- `published_at`, `collected_at`, `visible_at`, and `usable_from` are defined.
- `text_hash` duplicate removal rule is defined.
- Source coverage risk is recorded.
- `fetch_allowed_now=False`.
- Completed 2026-06-30 in `data/reports/ml_news_event_schema_plan.csv` and
  `.md`. Actual result: Naver News, GDELT, manual calendar, and PIT control
  schema rows define PIT timestamps, deterministic `text_hash` de-duplication,
  source coverage risk, `fetch_allowed_now=False`,
  `training_allowed_now=False`, `feature_added_to_training=False`,
  `trading_allowed=False`, and `production_effect=none`.

Forbidden in this phase:

- API calls, network fetch, training, candidate compare, or production changes.

Next phase entry condition:

- Proceed to limited news fetch only after the user explicitly approves that
  specific future goal.

## Phase 9. Sentiment Scoring Plan

Goal:

- Plan rule/lexicon-based sentiment scores after the news schema exists.
- Keep FinBERT and LLM sentiment as later-stage work.

Deliverables:

- `data/reports/ml_sentiment_scoring_plan.csv`
- `data/reports/ml_sentiment_scoring_plan.md`

Completion conditions:

- `model_version` is defined.
- `sentiment_score` range is defined.
- `scored_at` and `usable_from` are defined.
- Hallucination and LLM risk note is written.
- `training_allowed_now=False`.
- Completed 2026-06-30 in `data/reports/ml_sentiment_scoring_plan.csv` and
  `.md`. Actual result: `model_version=rule_lexicon_v1`, `sentiment_score`
  range `-1.0_to_1.0`, `published_at`, `collected_at`, `visible_at`,
  `scored_at`, and `usable_from` required, FinBERT/LLM marked later-stage,
  `training_allowed_now=False`, `model_training_allowed=False`,
  `feature_added_to_training=False`, `trading_allowed=False`, and
  `production_effect=none`.

Forbidden in this phase:

- LLM scoring production use, FinBERT/LLM training, feature training merge,
  candidate promotion, or production changes.

Next phase entry condition:

- Sentiment plan is ready to be evaluated as part of external feature readiness.

## Phase 10. External Feature Readiness Re-Audit

Goal:

- Reassess whether financial, news, and sentiment features are ready to enter
  baseline ML research.

Deliverables:

- `data/reports/ml_external_feature_readiness_reaudit.csv`
- `data/reports/ml_external_feature_readiness_reaudit.md`

Completion conditions:

- Financial, news, and sentiment readiness are each classified as
  `ready` or `not_ready`.
- Leakage risk is evaluated.
- Missing rate is evaluated.
- `training_allowed=False` until explicit approval.
- Completed 2026-06-30 in
  `data/reports/ml_external_feature_readiness_reaudit.csv` and `.md`.
  Actual result: financial `not_ready` with `missing_rate=1.0000`, news
  `not_ready`, sentiment `not_ready`, overall `BLOCK`, leakage checks `PASS`,
  `training_allowed=False`, `feature_added_to_training=False`,
  `post_cutoff_data_used_for_train=False`, `trading_allowed=False`, and
  `production_effect=none`.

Forbidden in this phase:

- Training without approval, OOS rerun, candidate compare, production linkage, or
  broker work.

Next phase entry condition:

- Only approved external features may move into a paper-only model experiment.

## Phase 11. ML Model Experiment v1

Goal:

- Train and validate paper-only ML model v1 using only approved features.

Deliverables:

- `data/reports/ml_model_v1_training_report.csv`
- `data/reports/ml_model_v1_validation_report.csv`
- `data/reports/ml_model_v1_risk_report.md`

Completion conditions:

- No post-cutoff train usage.
- Benchmark comparison is recorded.
- Baseline technical-only model comparison is recorded.
- Overfit and data-snooping risk are recorded.
- Candidate promotion is forbidden.
- `trading_allowed=False`.
- Completed 2026-06-30 in `data/reports/ml_model_v1_training_report.csv`,
  `data/reports/ml_model_v1_validation_report.csv`, and
  `data/reports/ml_model_v1_risk_report.md`. Actual result:
  `approved_feature_set=technical_only`, `external_features_used=False`,
  `post_cutoff_data_used_for_train=False`, validation leakage `PASS`,
  benchmark and baseline-technical comparisons recorded,
  overfit/data-snooping risk `WARN`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`.

Forbidden in this phase:

- Protected candidate changes, production readiness changes, order output, broker
  submission, or strategy parameter changes.

Next phase entry condition:

- Model v1 risk report supports shadow scoring without allowing trading.

## Phase 12. Shadow Scoring Report

Goal:

- Apply model scores to monthly candidates as shadow scoring only, with no real
  orders.

Deliverables:

- `data/reports/ml_shadow_scoring_report.csv`
- `data/reports/ml_shadow_scoring_report.md`

Completion conditions:

- No order output.
- No broker submission.
- Protected candidate is unchanged.
- Only human-readable score tables are produced.
- `trading_allowed=False`.
- Completed 2026-06-30 in `data/reports/ml_shadow_scoring_report.csv` and
  `.md`. Actual result: latest local feature-month score table only,
  `order_output=False`, `broker_submission=False`,
  `monthly_plan_regenerated=False`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`.

Forbidden in this phase:

- Monthly order plan regeneration, broker work, candidate promotion, production
  linkage, or automated order decisions.

Next phase entry condition:

- Shadow score report is stable enough to observe over time without changing
  paper operation status.

## Phase 13. Paper-Only Observation Loop

Goal:

- Observe model scores over a defined period and record performance and risk.

Deliverables:

- `data/reports/ml_model_observation_status.csv`
- `data/reports/ml_model_observation_status.md`

Completion conditions:

- Sufficient observation months are recorded.
- Performance stability is recorded.
- Drawdown, turnover, and coverage are recorded.
- No promotion occurs.
- `production_effect=none`.
- Status artifact created 2026-06-30 in
  `data/reports/ml_model_observation_status.csv` and `.md`. Actual current
  result after explicit historical backfill approval:
  `observation_basis=historical_backfill`, `observation_months=101`,
  `sufficient_observation_months=True`,
  `performance_stability=historical_backfill_stable`, drawdown `-0.6520`,
  turnover `turnover=0.1700`, `coverage=symbols=5;months=101`,
  `post_cutoff_train_leakage=PASS`, `candidate_promotion=False`,
  `trading_allowed=False`, and `production_effect=none`. No fetch, OOS rerun,
  candidate compare, order output, broker work, monthly plan regeneration,
  candidate promotion, strategy change, or production change was performed.

Forbidden in this phase:

- Promotion, production enablement, protected candidate edits, broker work, or
  trading authorization.

Next phase entry condition:

- Observation evidence is sufficient to assemble the final research packet.

## Phase 14. Final Paper-Only ML Research Packet

Goal:

- Consolidate paper-only ML research results into one final packet.

Deliverables:

- `data/reports/ml_model_research_packet.md`
- `data/reports/ml_model_research_packet.csv`

Completion conditions:

- Data lineage is documented.
- Feature list is documented.
- Leakage checks are summarized.
- Validation results are summarized.
- Failure cases are summarized.
- `trading_allowed=False`.
- `production_effect=none`.
- Production `BLOCK` is retained.
- Completed 2026-06-30 in `data/reports/ml_model_research_packet.csv` and
  `.md`. Actual result:
  `model_completion_status=paper_only_complete_not_live_ready`, OpenDART
  financial/news/sentiment/external features remain `not_ready` unless an
  existing readiness report explicitly says ready, leakage checks `PASS`,
  overfit/data-snooping risk `WARN`, final recommendation
  `keep_paper_only_do_not_trade`, `candidate_promotion=False`,
  `broker_submission=False`, `order_execution=False`,
  `production_readiness_change=False`, `trading_allowed=False`,
  `production_effect=none`, production `BLOCK` retained, and protected
  candidate unchanged. No fetch, API call, OOS rerun, candidate compare, new
  candidate, monthly plan regeneration, strategy change, broker work,
  production readiness change, or trading authorization was performed.

Forbidden in this phase:

- Production readiness change, candidate promotion, live trading, broker
  submission, or order execution.

Next phase entry condition:

- No automatic next phase. Any production, promotion, or live-readiness work
  requires a separate explicit approval and a separate safety review goal.

## Completion Definition

The roadmap is complete as a paper-only research track when the paper-only ML
research model has:

- A PIT-safe feature/label dataset lineage.
- A documented baseline training report.
- A documented validation report.
- Explainability and failure analysis.
- External feature readiness decisions where applicable.
- Shadow scoring and observation reports.
- A final research packet.

The roadmap is not complete if it relies on unapproved fetches, post-cutoff
train leakage, hidden API keys, protected candidate changes, or production
effects.

Completion never implies live trading readiness. The final state remains
paper-only and not live-ready unless a separate explicitly approved process
changes that.
