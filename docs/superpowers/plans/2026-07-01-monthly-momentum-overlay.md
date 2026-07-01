# Monthly Momentum Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a paper-only research report that evaluates capped momentum overlay candidates against the protected `neutral_loss_guard55_min_history244` champion without changing or promoting the champion.

**Architecture:** Add a focused report module that reads existing monthly validation CSVs, applies deterministic overlay adjustments from supplied scenario-level overlay assumptions, and emits comparison/performance/gate rows. Keep the first implementation report-only so it can be tested without running the full monthly engine.

**Tech Stack:** Python standard library, `csv`, `dataclasses`, `unittest`.

---

### Task 1: Report API And Safety Tests

**Files:**
- Create: `tests/test_monthly_momentum_overlay.py`
- Create: `backtester/monthly_momentum_overlay.py`

- [ ] **Step 1: Write failing tests**

Create tests for:
- Champion metrics are loaded from `monthly_performance_audit_candidate_proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244.csv`.
- A candidate with higher median walk-forward excess and no worse MDD/concentration is accepted as `PAPER_DIAGNOSTIC_PASS`.
- A candidate with worse MDD is rejected.
- Every output row has `trading_allowed=False` and `production_effect=none`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_monthly_momentum_overlay
```

Expected: import failure for `backtester.monthly_momentum_overlay`.

- [ ] **Step 3: Implement minimal report module**

Create:
- `ChampionMetrics`
- `OverlayTrial`
- `OverlayEvaluation`
- `load_champion_metrics`
- `evaluate_overlay_trial`
- `build_monthly_momentum_overlay_report`
- `save_monthly_momentum_overlay_report`

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m unittest tests.test_monthly_momentum_overlay
```

Expected: PASS.

### Task 2: CLI Integration

**Files:**
- Modify: `backtester/__main__.py`
- Test: `tests/test_cli.py` or a new focused CLI test if needed

- [ ] **Step 1: Add failing CLI test**

Test that `python -m backtester monthly-momentum-overlay-report --help` exposes the command and default output path.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_cli
```

- [ ] **Step 3: Add command**

Add a paper-only command that reads:
- champion performance audit CSV
- scenario validation CSV
- overlay trial CSV

and writes:
- `data/reports/monthly_momentum_overlay_report.csv`
- `data/reports/monthly_momentum_overlay_report.md`

- [ ] **Step 4: Run CLI test**

Run:

```powershell
python -m unittest tests.test_cli
```

### Task 3: First Bounded Research Trial

**Files:**
- Create: `data/reports/monthly_momentum_overlay_trial_v0.csv`
- Create: `data/reports/monthly_momentum_overlay_report.csv`
- Create: `data/reports/monthly_momentum_overlay_report.md`

- [ ] **Step 1: Create a small trial input**

Use four overlay caps only: `0.10`, `0.15`, `0.20`, `0.25`.

- [ ] **Step 2: Generate report**

Run:

```powershell
python -m backtester monthly-momentum-overlay-report
```

- [ ] **Step 3: Verify success criteria**

Compare against:
- required failures `0`
- worst MDD `>= -21.7069`
- median walk-forward excess `> 4.4114`
- concentration ratio `<= 27.2132`

### Self-Review

- Scope is report-only and paper-only.
- The protected champion remains read-only.
- No broker, order, production, or trading authorization path is introduced.
- The first implementation is deliberately small; full engine integration comes only after a report candidate passes.
