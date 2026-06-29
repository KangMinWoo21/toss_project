#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/toss-stock-bot}"
MAX_REPORT_AGE_HOURS="${MAX_REPORT_AGE_HOURS:-1080}"
BLOCK_REPORT_AGE_HOURS="${BLOCK_REPORT_AGE_HOURS:-1440}"
MAX_SCALPER_AGE_HOURS="${MAX_SCALPER_AGE_HOURS:-24}"
BLOCK_SCALPER_AGE_HOURS="${BLOCK_SCALPER_AGE_HOURS:-72}"
SCALPER_DIR="${SCALPER_DIR:-data/scalper}"
LOGS_DIR="${LOGS_DIR:-logs}"
JSON_OUTPUT="${JSON_OUTPUT:-data/reports/health_status.json}"
MARKDOWN_OUTPUT="${MARKDOWN_OUTPUT:-data/reports/health_status.md}"

cd "$REPO_DIR"
mkdir -p data/reports

python3 -m backtester health-check \
  --max-report-age-hours "$MAX_REPORT_AGE_HOURS" \
  --block-report-age-hours "$BLOCK_REPORT_AGE_HOURS" \
  --scalper-dir "$SCALPER_DIR" \
  --max-scalper-age-hours "$MAX_SCALPER_AGE_HOURS" \
  --block-scalper-age-hours "$BLOCK_SCALPER_AGE_HOURS" \
  --logs-dir "$LOGS_DIR" \
  --json-output "$JSON_OUTPUT" \
  --markdown-output "$MARKDOWN_OUTPUT"
