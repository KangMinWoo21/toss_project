# Monthly Rebalance Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the structural risk of `backtester/monthly_rebalance.py` by extracting focused monthly modules without changing CLI behavior.

**Architecture:** Keep `backtester/monthly_rebalance.py` as the public compatibility facade while moving pure helpers into a new `backtester/monthly/` package. Each extraction must preserve existing function signatures or re-export compatibility wrappers until callers are migrated.

**Tech Stack:** Python standard library, `unittest`, existing `backtester` CLI.

---

## File Structure

- Create: `backtester/monthly/__init__.py`
  - Package marker and future stable exports.
- Create: `backtester/monthly/reporting.py`
  - Pure report row formatting, CSV-safe report value helpers, summary table helpers.
- Create: `backtester/monthly/validation.py`
  - Validation gate helpers and decision classification helpers.
- Create: `backtester/monthly/paper_orders.py`
  - Paper order plan row construction and dry-run safety helpers.
- Modify: `backtester/monthly_rebalance.py`
  - Import extracted helpers and keep existing public entry points.
- Modify: `tests/test_monthly_rebalance.py`
  - Keep behavior tests on the public facade.
- Create as needed: `tests/test_monthly_reporting.py`, `tests/test_monthly_validation.py`, `tests/test_monthly_paper_orders.py`
  - Unit tests for extracted pure helpers.

### Task 1: Inventory Stable Extraction Candidates

- [ ] **Step 1: List top-level functions and classes**

Run:

```powershell
python - <<'PY'
import ast
from pathlib import Path
tree = ast.parse(Path("backtester/monthly_rebalance.py").read_text(encoding="utf-8"))
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        print(f"{node.lineno}: {node.name}")
PY
```

Expected: a line-numbered list of public and private symbols.

- [ ] **Step 2: Mark candidates**

Create a short local note grouping only helpers with no network, file-system, or broker side effects into:

```text
reporting:
validation:
paper_orders:
leave_in_facade:
```

Expected: no code changes yet.

### Task 2: Extract Reporting Helpers First

- [ ] **Step 1: Write focused tests**

Add tests in `tests/test_monthly_reporting.py` for one or two pure formatting helpers selected from the inventory. Import through the old facade first if the helper is currently public.

Run:

```powershell
python -m unittest tests.test_monthly_reporting
```

Expected before implementation: tests fail only because the new module or import does not exist.

- [ ] **Step 2: Create `backtester/monthly/reporting.py`**

Move the selected helper implementation exactly, including any small constants it directly needs. Do not move CLI code or file-writing orchestration in this task.

- [ ] **Step 3: Re-export or delegate from `monthly_rebalance.py`**

Keep existing import paths working. If callers currently use `backtester.monthly_rebalance.some_helper`, leave a wrapper or imported alias.

- [ ] **Step 4: Verify**

Run:

```powershell
python -m unittest tests.test_monthly_reporting
python -m unittest tests.test_monthly_rebalance
```

Expected: both commands pass.

### Task 3: Extract Validation Helpers

- [ ] **Step 1: Write focused tests**

Add `tests/test_monthly_validation.py` for pure validation classification helpers only. Use small in-memory rows or dataclasses; do not depend on generated report files.

- [ ] **Step 2: Move helpers into `backtester/monthly/validation.py`**

Move only helpers already covered by the focused tests. Keep file IO, CLI argument parsing, and backtest orchestration in `monthly_rebalance.py`.

- [ ] **Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_monthly_validation
python -m unittest tests.test_monthly_rebalance
```

Expected: both commands pass.

### Task 4: Extract Paper Order Helpers

- [ ] **Step 1: Write focused tests**

Add `tests/test_monthly_paper_orders.py` covering dry-run row construction and blocked-order representation. Include at least one blocked order case.

- [ ] **Step 2: Move pure helpers into `backtester/monthly/paper_orders.py`**

Move only helpers that do not submit orders, read credentials, or call brokerage APIs.

- [ ] **Step 3: Verify safety behavior**

Run:

```powershell
python -m unittest tests.test_monthly_paper_orders
python -m unittest tests.test_monthly_rebalance
python -m unittest tests.test_cloud_scripts
```

Expected: all commands pass and cloud script expectations remain unchanged.

### Task 5: Full Verification and Commit

- [ ] **Step 1: Compile**

Run:

```powershell
python -m compileall -q backtester
```

Expected: exit code 0.

- [ ] **Step 2: Full tests**

Run:

```powershell
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 3: Review diff**

Run:

```powershell
git diff --stat
git diff -- backtester/monthly_rebalance.py backtester/monthly tests
```

Expected: only mechanical helper extraction and focused tests.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backtester/monthly backtester/monthly_rebalance.py tests
git commit -m "Decompose monthly rebalance helpers"
```
