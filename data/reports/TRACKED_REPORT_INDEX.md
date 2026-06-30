# Tracked Report Index

`data/reports/` is ignored by default because most files are generated during local research and validation runs.

The files that are intentionally tracked here are durable evidence packets or small manifests needed to preserve research decisions.

## Current Tracked Families

Approximate tracked file counts by filename family:

| Family | Count | Purpose |
| --- | ---: | --- |
| `ml_v2` | 95 | Fixed-spec ML v2 research evidence, diagnostics, and final packet |
| `formulaic_alpha` | 19 | Formulaic alpha baseline and feature evidence |
| `ml_baseline` | 7 | Baseline ML comparison artifacts |
| `ml_financial` | 7 | Financial feature readiness and diagnostics |
| `ml_model` | 7 | ML model completion and governance artifacts |
| `ml_external` | 4 | External data readiness context |
| `monthly_paper` | 4 | Paper-operation review artifacts |
| Other small families | 26 | Safety, context, candidate, Sharpe, news, sentiment, and guard evidence |

## Rules

- Do not bulk-move tracked report files without updating every document and CLI path that references them.
- Add new generated reports only when they are durable evidence, not ordinary local output.
- Use `git add -f data/reports/<file>` intentionally because this directory is ignored.
- Prefer adding a short `.md` packet or manifest over committing large batches of raw CSV output.

## Next Migration Step

When report path migration is approved, move one family at a time:

1. Add explicit output path options where missing.
2. Update tests to write to temporary directories.
3. Move the selected family under `data/reports/<family>/`.
4. Update docs that reference the old flat filenames.
5. Run the full test suite before committing.
