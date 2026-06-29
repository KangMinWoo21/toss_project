#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/toss-stock-bot}"
DATA_DIR="${DATA_DIR:-data/krx_expanded}"
AS_OF="${AS_OF:-$(TZ=Asia/Seoul date +%F)}"
CASH="${CASH:-10000000}"
POINT_IN_TIME_UNIVERSE="${POINT_IN_TIME_UNIVERSE:-data/krx_metadata/krx_universe_monthly.csv}"
PERFORMANCE_REPORT="${PERFORMANCE_REPORT:-data/reports/monthly_performance_audit.csv}"
DEPLOYMENT_GATE_FILE="${DEPLOYMENT_GATE_FILE:-data/reports/monthly_deployment_gate_pit_universe.csv}"
VALIDATION_SCENARIOS="${VALIDATION_SCENARIOS:-data/reports/monthly_validation_scenarios_pit_universe.csv}"
COVERAGE_REPORT="${COVERAGE_REPORT:-data/reports/monthly_universe_price_coverage.csv}"
MAX_REPORT_AGE_DAYS="${MAX_REPORT_AGE_DAYS:-45}"
STATE_FILE="${STATE_FILE:-data/reports/monthly_rebalance_state_cloud.csv}"
OUTPUT="${OUTPUT:-data/reports/monthly_order_plan_cloud.csv}"
SUMMARY_OUTPUT="${SUMMARY_OUTPUT:-data/reports/monthly_order_plan_summary_cloud.md}"
DECISION_OUTPUT="${DECISION_OUTPUT:-data/reports/monthly_decision_cloud.csv}"
RISK_OUTPUT="${RISK_OUTPUT:-data/reports/monthly_risk_report_cloud.csv}"
READINESS_OUTPUT="${READINESS_OUTPUT:-data/reports/production_readiness.csv}"
READINESS_MARKDOWN_OUTPUT="${READINESS_MARKDOWN_OUTPUT:-data/reports/production_readiness_report.md}"
EVENTS="${EVENTS:-}"
EVENT_SOURCE_WEIGHTS="${EVENT_SOURCE_WEIGHTS:-}"
EVENT_LOOKBACK_DAYS="${EVENT_LOOKBACK_DAYS:-20}"
MIN_ENTRY_EVENT_SCORE="${MIN_ENTRY_EVENT_SCORE:--0.4}"
EVENT_WEIGHT="${EVENT_WEIGHT:-0.25}"
POSITIONS="${POSITIONS:-}"
DAY_START_EQUITY="${DAY_START_EQUITY:-}"

cd "$REPO_DIR"
mkdir -p data/reports

for required in "$DATA_DIR" "$POINT_IN_TIME_UNIVERSE" "$PERFORMANCE_REPORT" "$DEPLOYMENT_GATE_FILE" "$VALIDATION_SCENARIOS" "$COVERAGE_REPORT"; do
  if [[ ! -e "$required" ]]; then
    echo "missing required monthly plan input: $required" >&2
    exit 2
  fi
done

if [[ -n "$EVENTS" && ! -e "$EVENTS" ]]; then
  echo "missing optional monthly event input: $EVENTS" >&2
  exit 2
fi

if [[ -n "$POSITIONS" && ! -e "$POSITIONS" ]]; then
  echo "missing optional monthly positions input: $POSITIONS" >&2
  exit 2
fi

args=(
  -m backtester monthly-plan
  --data-dir "$DATA_DIR"
  --as-of "$AS_OF"
  --cash "$CASH"
  --point-in-time-universe "$POINT_IN_TIME_UNIVERSE"
  --performance-report "$PERFORMANCE_REPORT"
  --require-performance-report
  --max-report-age-days "$MAX_REPORT_AGE_DAYS"
  --deployment-gate-file "$DEPLOYMENT_GATE_FILE"
  --require-deployment-gate
  --state-file "$STATE_FILE"
  --output "$OUTPUT"
  --summary-output "$SUMMARY_OUTPUT"
  --decision-output "$DECISION_OUTPUT"
  --risk-output "$RISK_OUTPUT"
)

if [[ -n "$EVENTS" ]]; then
  args+=(--events "$EVENTS")
  args+=(--event-lookback-days "$EVENT_LOOKBACK_DAYS")
  args+=(--min-entry-event-score "$MIN_ENTRY_EVENT_SCORE")
  args+=(--event-weight "$EVENT_WEIGHT")
fi

if [[ -n "$EVENT_SOURCE_WEIGHTS" ]]; then
  args+=(--event-source-weights "$EVENT_SOURCE_WEIGHTS")
fi

if [[ -n "$POSITIONS" ]]; then
  args+=(--positions "$POSITIONS")
fi

if [[ -n "$DAY_START_EQUITY" ]]; then
  args+=(--day-start-equity "$DAY_START_EQUITY")
fi

monthly_status=0
python3 "${args[@]}" || monthly_status=$?

python3 -m backtester production-check \
  --required-artifact "$POINT_IN_TIME_UNIVERSE" \
  --required-artifact "$VALIDATION_SCENARIOS" \
  --required-artifact "$DEPLOYMENT_GATE_FILE" \
  --required-artifact "$RISK_OUTPUT" \
  --required-artifact "$COVERAGE_REPORT" \
  --required-artifact "$PERFORMANCE_REPORT" \
  --deployment-gate-file "$DEPLOYMENT_GATE_FILE" \
  --validation-scenarios "$VALIDATION_SCENARIOS" \
  --risk-report "$RISK_OUTPUT" \
  --coverage-report "$COVERAGE_REPORT" \
  --performance-report "$PERFORMANCE_REPORT" \
  --max-report-age-days "$MAX_REPORT_AGE_DAYS" \
  --as-of "$AS_OF" \
  --output "$READINESS_OUTPUT" \
  --markdown-output "$READINESS_MARKDOWN_OUTPUT" \
  --allow-blocked-exit-zero

exit "$monthly_status"
