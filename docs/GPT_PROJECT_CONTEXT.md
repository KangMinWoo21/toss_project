# GPT Project Context

Last updated: 2026-06-30

## Purpose

This repository is for domestic-stock paper-operation research, local reports,
and safety monitoring. It is not live-ready, and this file does not authorize
trading, broker submission, order execution, candidate promotion, or production
readiness changes.

## Read First

1. `docs/GOAL_MODE_CHECKPOINT.md`
2. `docs/goal-mode-minimal-prompt.md`
3. `data/reports/paper_operation_safety_status_index.md`
4. `data/reports/paper_operation_safety_status_index.csv`
5. `data/reports/protected_candidate_oos_review_eligibility_guard.csv`
6. `data/reports/monthly_paper_operation_consistency_audit.csv`
7. `data/reports/monthly_paper_operation_review_packet.csv`
8. `data/reports/health_warn_classification.csv`

## Current Safety Status

- Production is not live-ready: `BLOCK`.
- Safety index: `overall_status=OBSERVE`.
- Protected candidate remains `PAPER_REVIEW`.
- OOS review eligibility is `REVIEW_NOT_ALLOWED`.
- `trading_allowed=False`.
- `review_allowed=False`.
- `production_effect=none`.
- Actionable rows: `0`.
- Promoted candidates: `0`.
- Recommended action: `keep_observing_no_tuning_no_promotion`.
- Scalper stale `WARN` is separate from monthly paper review/OOS.

## Protected Candidate

`proxy_guard_exit_short_minus5_neutral_loss_guard55 + min_history244`

- Keep as paper-review evidence only.
- Do not modify, tune, promote, replace, or adopt it.
- OOS review is not allowed yet because observed trading days remain below the
  required trading-day threshold and remaining trading days are still positive.

## Latest Verification Baseline

- Full `unittest`: latest recorded `684` tests passing.
- `python -m compileall -q backtester`: passing.
- Safe production-check: `BLOCK` retained.
- Safe health-check with `--scalper-mode warn`: `WARN` only for stale scalper
  data.

## Hard Stops

- Do not rerun OOS.
- Do not fetch data or call network services.
- Do not run candidate compare.
- Do not create new candidates.
- Do not regenerate monthly plans.
- Do not change strategy parameters.
- Do not open, print, summarize, or commit `.env` or secrets.
- Do not work on live trading, Toss API, broker submission, or order execution.
- Do not push unless the user explicitly approves it.

## Next Work Style

Use a narrow Goal loop. Read the required local files first, use existing local
reports only, keep checkpoint updates short, and commit only the files directly
related to the requested document/report change.
