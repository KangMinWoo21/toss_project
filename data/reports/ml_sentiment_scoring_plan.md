# ML Sentiment Scoring Plan

## Do Not Trade / Sentiment Plan Only

This report is a paper-only rule/lexicon sentiment scoring plan. It does not fetch news, call APIs, run FinBERT or LLM scoring, train models, rerun OOS, compare candidates, change strategy parameters, promote the protected PAPER_REVIEW candidate, call broker APIs, or authorize trading.

- `model_version=rule_lexicon_v1` for the initial scoring contract.
- `sentiment_score` range is `-1.0_to_1.0` for row-level lexicon scoring.
- `fetch_allowed_now=False` for every row.
- `training_allowed_now=False` for every row.
- `feature_added_to_training=False` for every row.
- `trading_allowed=False` for every row.
- `production_effect=none` for every row.
- Required PIT timestamps include `published_at`, `collected_at`, `visible_at`, `scored_at`, and `usable_from`.
- FinBERT and LLM sentiment remain later-stage only because of hallucination, prompt drift, and non-determinism risk.

## Plan Rows

| Component | Model Version | Candidate Features | Timestamp Fields | Score Range | LLM Risk Note | Next Safe Action |
| --- | --- | --- | --- | --- | --- | --- |
| lexicon_scoring | rule_lexicon_v1 | sentiment_score;sentiment_label;positive_keyword_count;negative_keyword_count;importance_score | published_at;collected_at;visible_at;scored_at;usable_from | -1.0_to_1.0 | No FinBERT or LLM scoring in Phase 9; rule_lexicon_v1 only. | Review lexicon categories only; do not score live news or add sentiment to training. |
| monthly_aggregation | rule_lexicon_v1 | sentiment_count_1m;negative_sentiment_share_1m;mean_sentiment_score_1m;max_negative_importance_1m | published_at;collected_at;visible_at;scored_at;usable_from;feature_generated_at | -1.0_to_1.0_aggregated | No LLM-generated labels or summaries may enter aggregation in Phase 9. | Use aggregation contract only for readiness review; keep feature_added_to_training=False. |
| pit_controls | rule_lexicon_v1 | sentiment_observation_id;source_revision;quality_status;excluded_reason | published_at;collected_at;visible_at;scored_at;usable_from;feature_generated_at | not_applicable_controls | Block uncontrolled LLM outputs, prompt revisions, or regenerated scores without versioned lineage. | Use these controls in Phase 10 external feature readiness re-audit. |
| later_stage_models | later_stage_not_ready | finbert_sentiment_score;llm_sentiment_label;llm_importance_reason | published_at;collected_at;visible_at;scored_at;usable_from;model_released_at;prompt_approved_at | not_defined_for_phase_9 | FinBERT and LLM sentiment are later-stage only due to hallucination, prompt drift, vendor changes, and non-deterministic outputs. | Keep FinBERT/LLM as later-stage; do not train, score, or merge in this phase. |
