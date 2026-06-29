# ML Shadow Scoring Report

## Do Not Trade / Shadow Scoring Only

This report applies paper-only ML model v1 scores as human-readable shadow scores. It does not generate order output, submit to a broker, regenerate the monthly plan, promote candidates, change strategy parameters, call broker APIs, or authorize trading.

- No order output.
- No broker submission.
- Monthly plan regenerated: `False`.
- Candidate promotion: `False`.
- Trading allowed: `False`.
- Production effect: `none`.
- Protected candidate unchanged.

## Score Rows

| Rank | Symbol | Feature Date | Score | Bucket |
| --- | --- | --- | --- | --- |
| 1 | 000080 | 2026-05-29 | 0.476057 | low |
| 2 | 000020 | 2026-05-29 | 0.470016 | low |
| 3 | 000050 | 2026-05-29 | 0.332913 | low |
| 4 | 000070 | 2026-05-29 | 0.331665 | low |
