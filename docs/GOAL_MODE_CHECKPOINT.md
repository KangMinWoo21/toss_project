# Goal Mode Checkpoint

Last updated: 2026-06-30

## Current State

- Latest structure cleanup commit: `0b82a28 Extract CLI common helpers`.
- Previous safety hardening commit: `07914db Harden paper operation safety checks`.
- Previous final ML v2 packet commit: `4b5fc74 Add final ML v2 fixed-spec research packet`.
- The trading toolkit remains Python/stdlib-test based, with source in `backtester/` and tests in `tests/`.
- Generated reports still default to `data/reports/`; tracked report families are documented in `data/reports/TRACKED_REPORT_INDEX.md`.

## Latest Verified Commands

These were verified before this structure cleanup:

```powershell
python -m compileall -q backtester
python -m unittest discover -s tests
```

Latest verified result after structure cleanup: syntax check passed and the unittest suite passed with 778 tests.

## Structure Cleanup Notes

- The previous long checkpoint was archived at `docs/archive/checkpoints/GOAL_MODE_CHECKPOINT_2026-06-30_pre_structure_cleanup.md`.
- The previous full project snapshot was archived at `docs/archive/snapshots/GPT_PROJECT_SNAPSHOT_FULL_2026-06-30.md`.
- `.tmp/` is reserved for local security-scan and agent scratch artifacts and is ignored by Git.
- `data/reports/README.md` documents the report storage policy.
- `data/reports/TRACKED_REPORT_INDEX.md` documents intentionally tracked report families under the ignored report directory.
- `docs/reference/tossinvest-openapi.json` stores the large Toss OpenAPI spec outside the docs root.
- Older research planning docs were moved under `docs/archive/research/`.
- `backtester/monthly/` now contains reporting, validation, paper order, and universe helper modules extracted from `monthly_rebalance.py`.
- `backtester/cli/common.py` contains small CLI parsing helpers extracted from `__main__.py`.
- `docs/superpowers/plans/2026-06-30-monthly-rebalance-decomposition.md` records the safer path for splitting the large monthly rebalance module.

## Next Safe Work

1. Keep generated report output paths stable until a family-by-family report path migration is approved.
2. Continue splitting `backtester/monthly_rebalance.py` only in small, tested slices.
3. Split `backtester/__main__.py` by CLI command family only after pure helper extraction stays stable.
