# Goal Mode Checkpoint

Last updated: 2026-06-30

## Current State

- Latest commit before structure cleanup: `07914db Harden paper operation safety checks`.
- Previous final ML v2 packet commit: `4b5fc74 Add final ML v2 fixed-spec research packet`.
- The trading toolkit remains Python/stdlib-test based, with source in `backtester/` and tests in `tests/`.
- Generated reports still default to `data/reports/`; do not bulk-move existing report files without updating CLI defaults, scripts, tests, and documentation references.

## Latest Verified Commands

These were verified before this structure cleanup:

```powershell
python -m compileall -q backtester
python -m unittest discover -s tests
```

Result at that time: syntax check passed and the unittest suite passed with 754 tests.

## Structure Cleanup Notes

- The previous long checkpoint was archived at `docs/archive/checkpoints/GOAL_MODE_CHECKPOINT_2026-06-30_pre_structure_cleanup.md`.
- The previous full project snapshot was archived at `docs/archive/snapshots/GPT_PROJECT_SNAPSHOT_FULL_2026-06-30.md`.
- `.tmp/` is reserved for local security-scan and agent scratch artifacts and is ignored by Git.
- `data/reports/README.md` documents the report storage policy.
- `docs/superpowers/plans/2026-06-30-monthly-rebalance-decomposition.md` records the safer path for splitting the large monthly rebalance module.

## Next Safe Work

1. Keep `docs/` root focused on current status, operating notes, and durable research plans.
2. Keep generated report output paths stable until the codebase has an explicit report path migration.
3. Split `backtester/monthly_rebalance.py` only in small, tested slices, starting with pure reporting and validation helpers.
