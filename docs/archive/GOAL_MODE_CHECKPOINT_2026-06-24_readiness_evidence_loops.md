# Goal Mode Checkpoint Archive: Readiness Evidence Loops

Archived from `docs/GOAL_MODE_CHECKPOINT.md` on 2026-06-24 to keep the active
checkpoint short.

## Safety And Freshness Gates

- `925f9e1`: candidate `ACCEPT/APPROVE` requires marker proof plus post-cutoff
  OOS end date after `2026-06-18`; marker-only proof blocks readiness/monthly
  risk.
- Candidate decision CSV now has explicit `post_cutoff_oos_start_date` and
  `post_cutoff_oos_end_date` fields for that proof.
- `84f0999`: `monthly-plan --max-data-stale-days` blocks stale included OHLCV
  before strategy selection or paper order planning.
- Monthly-plan now blocks stale point-in-time universe snapshots, low universe
  price coverage, and missing point-in-time universe evidence before
  paper-operation planning.
- Candidate decisions gate monthly plans and production readiness;
  `PAPER_REVIEW`, missing decisions, proofless `ACCEPT`, and inconsistent
  `ACCEPT/APPROVE` decisions block.

## Readiness Schema Evidence

- Production readiness blocks monthly risk reports that omit required
  paper-operation gate rows or detail evidence.
- Production readiness blocks performance audit, concentration, and drawdown
  attribution reports that omit required evidence columns or detail evidence.
- Production readiness blocks validation failure, remediation, sweep
  plan/result, comparison, scenario delta, failure pattern/drilldown,
  deployment gate, and all-pass validation scenario reports that omit required
  evidence columns.
- Candidate follow-up and candidate decision readiness block reports that omit
  required command, artifact, adoption, decision, comparison, diagnostic,
  reason, recommendation, or risk-note evidence columns.

## Readiness Value Evidence

- Validation failure readiness blocks action reports that include required
  columns but omit required failure, metric, severity, or action values.
- Validation remediation readiness blocks experiment reports that include
  required columns but omit priority, action, failure, affected-scenario,
  metric, hint, or next-experiment values.
- Validation sweep plan readiness blocks experiment plans that include required
  columns but omit priority, action, experiment, target, expected effect, or
  risk-note values.
- Validation sweep results readiness blocks result reports that include required
  columns but omit experiment, status, scenario, candidate args, adoption,
  result summary, or risk-note values.
- Validation failure pattern readiness blocks reports that include required
  columns but omit scenario, baseline, count, diagnostic, action, or note
  values.
- Validation failure drilldown readiness blocks reports that include required
  columns but omit scenario, period, metric, diagnostic, or next-action values.
