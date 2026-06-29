# Research Papers for Validation

This is a practical validation note for the paper-operation trading system. It
is not a literature review and it does not justify live trading. The purpose is
to turn institutional-style validation ideas into small report-oriented tasks
that improve research discipline without changing strategy behavior.

Hard boundaries:

- Do not add new strategy modules.
- Do not enable live trading or real order execution.
- Do not change trading behavior, candidate selection logic, production gates,
  or strategy parameters from this note.
- Do not promote `PAPER_REVIEW` candidates from documentation alone.
- Keep production, readiness, and risk `BLOCK` states as hard stops.
- Treat every future report below as proposed until it exists and is tested.

## 1. Data Snooping and White Reality Check

Reference: White, H. (2000). "A Reality Check for Data Snooping."

Why it matters for this repository:

The monthly validation workflow has many scenarios, sweeps, parameter variants,
candidate comparisons, and rejected experiments. The more candidates are tried,
the easier it becomes to find one that looks good by chance.

Risk addressed:

Data snooping, multiple testing, and overfitting to the current validation
suite. A candidate can appear to fix the latest blockers while simply being the
best survivor of many attempts.

Mapping to the current paper-operation system:

Current reports already separate baseline, sweep results, candidate decisions,
candidate follow-ups, and readiness status. Those artifacts should be treated as
one research family rather than independent proof that the latest winner is
robust.

Implement now:

- Add candidate trial count tracking for baselines, sweeps, diagnostics,
  rejected candidates, and `PAPER_REVIEW` candidates.
- Include candidate id, parameter arguments, source command, source report,
  scenario set, decision, and trial category.
- Surface trial counts in candidate comparison or readiness summaries.

Future work:

- Add a formal White Reality Check or bootstrap-based family-wise comparison.
- Estimate effective trial counts when candidate variants are highly similar.

Must NOT be used to justify live trading:

- A single best candidate after many experiments.
- A reduced failure count without trial-count context.
- A paper-review decision that lacks fresh post-selection evidence.

## 2. Deflated Sharpe Ratio

Reference: Bailey, D. H. and Lopez de Prado, M. (2014). "The Deflated Sharpe
Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality."

Why it matters for this repository:

Raw Sharpe, total return, and excess return can be inflated by repeated
candidate search, short samples, skewed returns, fat tails, and concentrated
winner months.

Risk addressed:

False confidence in a risk-adjusted metric after selection bias and non-normal
return distributions.

Mapping to the current paper-operation system:

The system already has validation scenarios, performance reports, drawdown
checks, concentration reports, and candidate decisions. A deflated-Sharpe field
should be a report-level research control, not a strategy-selection rule.

Implement now:

- Add a placeholder or report columns for `deflated_sharpe_status`,
  `observed_sharpe`, `return_observation_count`, `return_skew`,
  `return_kurtosis`, `raw_trial_count`, and `effective_trial_count`.
- Use `not_computed` until a tested implementation exists.
- Keep existing readiness gates unchanged.

Future work:

- Implement and test the full Deflated Sharpe Ratio calculation.
- Compare DSR against walk-forward, drawdown, concentration, and OOS evidence
  instead of using it as a standalone pass/fail rule.

Must NOT be used to justify live trading:

- Raw Sharpe alone.
- A `not_computed` placeholder.
- A high DSR if production readiness or risk reports remain blocked.

## 3. Purged, Embargoed, and CPCV Validation

Reference: Lopez de Prado, M. (2018). "Advances in Financial Machine Learning."
See the validation chapters on purging, embargoing, and combinatorial purged
cross-validation.

Why it matters for this repository:

Strategy research can accidentally reuse information across train, selection,
and test windows. This is especially important when candidate decisions are made
after reviewing many failure reports.

Risk addressed:

Temporal leakage, overlapping-label leakage, and post-selection reuse of
evidence as if it were fresh out-of-sample validation.

Mapping to the current paper-operation system:

Walk-forward validation and candidate follow-up reports already exist. The next
step is to explicitly prove that each `PAPER_REVIEW` candidate has evidence
after the fixed selection cutoff and that any embargo rule is documented.

Implement now:

- Add a post-cutoff OOS proof report.
- Include candidate id, selection cutoff, OOS start, OOS end, embargo days,
  source command, source report, status, and reason.
- Keep candidates blocked when OOS markers are pending, malformed, or not after
  the cutoff.

Future work:

- Add purged k-fold or combinatorial purged cross-validation for research
  experiments where overlapping labels make ordinary splits unsafe.
- Add automated leakage checks for future event/news features.

Must NOT be used to justify live trading:

- In-sample fixes to known blockers.
- OOS windows that start before or at the selection cutoff.
- CPCV terminology without an actual tested report.

## 4. Trading Cost Realism

Reference: Frazzini, A., Israel, R., and Moskowitz, T. J. (2018). "Trading
Costs."

Why it matters for this repository:

Paper returns can disappear after fees, taxes, slippage, market impact,
turnover, and liquidity constraints. This matters most for high-turnover or
thin-liquidity candidates.

Risk addressed:

Overstated expectancy, underestimated implementation drag, and false confidence
from gross performance.

Mapping to the current paper-operation system:

The codebase already has fee, tax, slippage, slippage stress, estimated trade
cost, liquidity participation, and order-plan cost fields. The missing piece is
a concise expectancy report that makes gross-to-net degradation visible by
scenario and candidate.

Implement now:

- Add a fee/tax/slippage-adjusted expectancy report.
- Include gross return, fee drag, tax drag, slippage drag, estimated impact,
  turnover, net expectancy, win rate, average win, average loss, and breakeven
  cost buffer when available.
- Keep monthly plans review-only and blocked when risk/readiness blocks.

Future work:

- Calibrate impact assumptions from paper execution logs.
- Compare expected cost to realized paper slippage after enough observations.

Must NOT be used to justify live trading:

- Backtests that omit costs.
- Cost assumptions that are not stress tested.
- A positive net expectancy while production or risk status is `BLOCK`.

## 5. Survivorship and Point-in-Time Universe Bias

Reference topic: survivorship bias and point-in-time universe construction.

Why it matters for this repository:

The validation system relies on KRX universe snapshots, data-quality exclusions,
missing OHLCV reports, and history-length gates. Relaxing a gate can improve
results while also changing which symbols were allowed into the historical
universe.

Risk addressed:

Survivorship bias, hindsight universe construction, missing-data bias, and
thin-history selection bias.

Mapping to the current paper-operation system:

The best current paper-review candidate mentions `point_in_time_min_history_days
=244`. That change may resolve validation failures, but it needs a safety
review before any default or gate change is considered.

Implement now:

- Add a PIT universe and `min_history244` safety review.
- List symbols admitted by the relaxed history gate, symbols unavailable under
  the stricter gate, missing OHLCV counts, universe return distribution changes,
  and survivorship or thin-history risk notes.
- Link the review to readiness as evidence, not as automatic approval.

Future work:

- Expand PIT universe history and missing OHLCV coverage.
- Add stronger universe reconstruction checks for earlier market periods.

Must NOT be used to justify live trading:

- A candidate that passes only after a relaxed history gate.
- A PIT label without coverage and missing-data evidence.
- Extreme-winner performance without exclusion and concentration review.

## 6. Technical Analysis Pattern Validation

Reference: Lo, A. W., Mamaysky, H., and Wang, J. (2000). "Foundations of
Technical Analysis: Computational Algorithms, Statistical Inference, and
Empirical Implementation."

Why it matters for this repository:

Technical patterns and regime labels can look persuasive in charts even when
they do not survive formal validation.

Risk addressed:

Chart-reading bias, subjective pattern confirmation, and untested technical
rules being treated as alpha.

Mapping to the current paper-operation system:

Any technical, regime, or breadth rule should pass through the existing
scenario, walk-forward, stress, concentration, and readiness reports. The
documented validation system matters more than a visually appealing pattern.

Implement now:

- Keep technical-pattern conclusions inside existing validation reports.
- Add concentration by month and symbol so pattern-driven gains can be checked
  for one-month or few-symbol dependence.
- Record whether pattern improvements persist outside the blocker that inspired
  the experiment.

Future work:

- Add explicit pattern-family trial tracking if new pattern research begins.
- Add formal pattern validation only after report plumbing and OOS proof exist.

Must NOT be used to justify live trading:

- A visual chart pattern.
- A single improved scenario.
- A pattern rule that fails cost, OOS, concentration, or readiness controls.

## 7. Momentum Research

Reference: Jegadeesh, N. and Titman, S. (1993). "Returns to Buying Winners and
Selling Losers: Implications for Stock Market Efficiency."

Why it matters for this repository:

Momentum is a plausible research prior, but it is sensitive to regime, turnover,
crowding, crash risk, and implementation cost.

Risk addressed:

Assuming that a known anomaly automatically applies to the current Korean stock
universe, current data quality, current holding periods, and current trading
cost assumptions.

Mapping to the current paper-operation system:

Momentum strategies and momentum-like selection should stay inside paper
validation. They should be compared through the same validation suite as monthly
rebalance candidates, including stress slippage, winner exclusion, and
walk-forward windows.

Implement now:

- Use the fee/tax/slippage-adjusted expectancy report for momentum-like
  candidates.
- Use month/symbol concentration reports to show whether momentum performance
  depends on a small number of winners.
- Include candidate trial counts for momentum parameter sweeps.

Future work:

- Add longer OOS windows when more PIT data is available.
- Compare momentum results across multiple market regimes without changing
  production gates.

Must NOT be used to justify live trading:

- The existence of momentum in academic literature.
- A high full-period return with weak walk-forward margins.
- A candidate that fails winner-exclusion, cost, or readiness checks.

## 8. LLM, News, and Agentic Trading Research Limitations

Later-stage references only: Lopez-Lira/Tang, FINSABER, and TradingAgents.

Why it matters for this repository:

LLM/news/agentic trading research may be useful later for event interpretation,
news summarization, disclosure triage, or research-assistant workflows. It is
not mature enough in this project to affect current production gates.

Risk addressed:

Narrative overconfidence, hallucinated rationale, weak reproducibility,
lookahead leakage from news timestamps, and agentic systems making unreviewed
trading decisions.

Mapping to the current paper-operation system:

Existing event/news work should remain a small research and risk-context overlay
unless broader coverage, timestamp controls, and validation reports are added.
Agentic tools should not place orders or bypass readiness gates.

Implement now:

- Document LLM/news/agentic research as deferred.
- Keep event/news features behind timestamp and `available_date` controls.
- Require any future LLM-derived signal to produce auditable source records and
  validation reports before it is considered in strategy research.

Future work:

- Review Lopez-Lira/Tang, FINSABER, and TradingAgents after the statistical
  validation reports above exist.
- Build reproducible news/disclosure datasets before testing LLM-derived
  signals.

Must NOT be used to justify live trading:

- LLM explanations, summaries, or agent recommendations.
- News sentiment without timestamp, coverage, and OOS controls.
- Any agentic workflow that can bypass production/readiness/risk `BLOCK`
  states.

## Minimal Implementation Plan

These tasks are ordered to add research evidence without changing trading
behavior. Each task should add focused tests and should leave live trading
disabled.

1. Fee/tax/slippage-adjusted expectancy report

   Create a report from existing validation and order-cost fields. Include
   scenario, candidate id, gross return, fee drag, tax drag, slippage drag,
   estimated impact cost, turnover, net expectancy, win rate, average win,
   average loss, and breakeven cost buffer where available.

2. Candidate trial count tracking

   Add an append-only candidate research ledger under `data/reports/`. Include
   candidate id, parameter arguments, source command, source report, scenario
   set, decision, trial category, and timestamp. Count baseline, sweep,
   diagnostic, rejected, and `PAPER_REVIEW` rows.

3. Deflated Sharpe placeholder or report column

   Add report columns for `deflated_sharpe_status`, `observed_sharpe`,
   `return_observation_count`, `return_skew`, `return_kurtosis`,
   `raw_trial_count`, and `effective_trial_count`. Use `not_computed` until the
   DSR calculation is implemented and verified.

4. Post-cutoff OOS proof report

   Add a candidate OOS proof report with candidate id, selection cutoff, OOS
   start, OOS end, embargo days, source command, source report, status, and
   reason. Pending, malformed, or pre-cutoff OOS evidence should keep a
   candidate blocked from promotion.

5. Concentration by month and symbol

   Extend attribution or concentration reporting so candidate decisions show
   top-month contribution share, top-symbol contribution share,
   extreme-winner-exclusion result, and whether performance depends on a small
   number of names.

6. PIT universe and `min_history244` safety review

   Add a focused safety report for the `min_history244` paper-review candidate.
   Include newly admitted symbols, stricter-gate exclusions, missing OHLCV
   counts, universe return distribution changes, and survivorship/thin-history
   risk notes.

## References

- White, H. (2000). "A Reality Check for Data Snooping." Econometrica.
- Bailey, D. H. and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting and Non-Normality." The
  Journal of Portfolio Management.
- Lopez de Prado, M. (2018). "Advances in Financial Machine Learning." Wiley.
- Lo, A. W., Mamaysky, H., and Wang, J. (2000). "Foundations of Technical
  Analysis: Computational Algorithms, Statistical Inference, and Empirical
  Implementation." The Journal of Finance.
- Jegadeesh, N. and Titman, S. (1993). "Returns to Buying Winners and Selling
  Losers: Implications for Stock Market Efficiency." The Journal of Finance.
- Frazzini, A., Israel, R., and Moskowitz, T. J. (2018). "Trading Costs."
