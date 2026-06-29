# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python-based trading research and automation toolkit. Core source code lives in `backtester/`, with CLI entry points in `backtester/__main__.py`. Strategy logic, market data adapters, readiness checks, and execution planning are split across modules such as `strategies.py`, `monthly_rebalance.py`, `scalper.py`, `toss.py`, and `pykrx_fetcher.py`.

Tests live in `tests/` and mirror the module names, for example `tests/test_monthly_rebalance.py` and `tests/test_scalper.py`. Sample and generated datasets are under `data/`; reports are commonly written to `data/reports/`. Operational scripts are in `scripts/`, with cloud systemd helpers in `scripts/cloud/`. Design notes and operating plans belong in `docs/`.

## Build, Test, and Development Commands

Run the full test suite:

```powershell
python -m unittest discover -s tests
```

Check Python syntax after broad edits:

```powershell
python -m compileall -q backtester
```

Run a simple strategy comparison:

```powershell
python -m backtester compare --data data/sample_kr_stock.csv
```

Run production readiness checks:

```powershell
python -m backtester production-check --strict --max-report-age-days 45
```

## Coding Style & Naming Conventions

Use standard Python 3 style with 4-space indentation, descriptive snake_case names, and dataclasses for structured configuration or result objects. Keep CLI option names kebab-case and map them to snake_case fields. Prefer small pure functions for strategy rules and risk checks so they can be unit tested without live APIs.

## Testing Guidelines

Tests use the standard library `unittest` framework. Name files `test_<module>.py` and test methods `test_<behavior>`. Add regression tests for every strategy, risk-control, CLI, or data-ingestion change. When changing backtest behavior, include tests that guard against lookahead bias and unsafe live-order behavior.

## Commit & Pull Request Guidelines

The current history uses concise imperative commits, for example `Add trading backtester and guarded monthly workflow`. Keep commits scoped and describe the behavior changed. Pull requests should include a summary, commands run, notable backtest/readiness results, and any operational impact. Never include `.env`, API keys, downloaded secrets, or private brokerage credentials.

## Security & Configuration Tips

Use `.env.example` as the template for local secrets, and keep real values only in `.env`. Treat live trading, cloud services, and scheduled tasks as high-risk changes: document defaults, dry-run behavior, kill switches, and rollback steps before enabling automation.
