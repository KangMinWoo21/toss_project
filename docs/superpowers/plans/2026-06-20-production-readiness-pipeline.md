# Production Readiness Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an operational readiness pipeline that keeps the trading system in paper/live-blocked mode unless data, validation, and risk gates all pass.

**Architecture:** Add a focused readiness module that reads local data artifacts, deployment gates, validation scenario CSVs, and risk reports, then emits a single PASS/BLOCK report. Wire it into the CLI without changing the strategy itself. Keep live execution disabled by default.

**Tech Stack:** Python standard library, existing CSV reports, existing `monthly-validate` and `monthly-plan` outputs.

---

### Task 1: Readiness Report Core

**Files:**
- Create: `backtester/readiness.py`
- Test: `tests/test_readiness.py`

- [ ] Write a failing test that a missing required artifact produces a blocking row.
- [ ] Implement `evaluate_readiness(...)` with artifact checks.
- [ ] Add CSV/Markdown save helpers.
- [ ] Run `python -m unittest tests.test_readiness`.

### Task 2: Validation Gate Integration

**Files:**
- Modify: `backtester/readiness.py`
- Test: `tests/test_readiness.py`

- [ ] Write a failing test that a non-deployable deployment gate blocks readiness.
- [ ] Implement deployment gate loading through existing monthly gate format.
- [ ] Add validation scenario failure counting.
- [ ] Run readiness tests.

### Task 3: CLI Command

**Files:**
- Modify: `backtester/__main__.py`
- Test: `tests/test_cli.py`

- [ ] Add `production-check` CLI command.
- [ ] Wire output paths for CSV and Markdown reports.
- [ ] Ensure the command exits nonzero when readiness is blocked unless `--allow-blocked-exit-zero` is used.
- [ ] Run CLI tests.

### Task 4: Documentation And Verification

**Files:**
- Modify: `data/reports/monthly_deployment_review.md`
- Create/Update: `data/reports/production_readiness_report.md`

- [ ] Run `production-check` against current project data.
- [ ] Update deployment review with latest readiness result.
- [ ] Run `python -m unittest discover -s tests`.
- [ ] Run `python -m py_compile backtester\readiness.py backtester\__main__.py`.
