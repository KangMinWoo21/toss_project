# Report Storage Policy

`data/reports/` is the default output location for generated research, validation, readiness, and paper-operation reports.

## Current Constraint

Many CLI defaults, scripts, tests, and archived notes still reference flat paths such as:

```text
data/reports/monthly_validation_scenarios_pit_universe.csv
data/reports/monthly_deployment_gate_pit_universe.csv
data/reports/production_readiness.csv
```

Do not bulk-move existing report files until those references are migrated together.

## Target Organization

Use this structure for new cleanup work when a command explicitly supports a custom output path:

```text
data/reports/
  current/       latest human-facing status packets and review bundles
  monthly/       monthly validation, deployment, attribution, and paper-operation outputs
  ml_v2/         fixed-spec ML v2 datasets, diagnostics, and research packets
  archive/       dated historical report batches
```

## Tracking Policy

- Most report files are generated artifacts and should stay ignored.
- Commit only durable evidence packets, hand-authored summaries, and small manifests that are needed to reproduce decisions.
- Use `git add -f` intentionally when committing a report under this ignored directory.
- Never commit `.env`, credentials, brokerage tokens, or private downloaded market data.

## Migration Approach

1. Add explicit `--output`, `--report-dir`, or equivalent options where missing.
2. Update tests to use temporary output directories for generated files.
3. Move one report family at a time.
4. Keep compatibility aliases or documented legacy paths for operational scripts.
