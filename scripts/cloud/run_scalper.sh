#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/toss-stock-bot}"
SYMBOL="${SYMBOL:-005930}"
ITERATIONS="${ITERATIONS:-23400}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1}"
MAX_SPREAD_PCT="${MAX_SPREAD_PCT:-0.2}"
VOLUME_SPIKE_MULTIPLIER="${VOLUME_SPIKE_MULTIPLIER:-3.0}"
IMBALANCE_THRESHOLD="${IMBALANCE_THRESHOLD:-1.5}"

cd "$REPO_DIR"

DATE="$(TZ=Asia/Seoul date +%F)"
OUTPUT="data/scalper/${SYMBOL}_${DATE}_paper_scalp.csv"

mkdir -p data/scalper

exec python3 -m backtester paper-scalp \
  --symbol "$SYMBOL" \
  --iterations "$ITERATIONS" \
  --interval-seconds "$INTERVAL_SECONDS" \
  --output "$OUTPUT" \
  --append \
  --require-date "$DATE" \
  --max-spread-pct "$MAX_SPREAD_PCT" \
  --volume-spike-multiplier "$VOLUME_SPIKE_MULTIPLIER" \
  --imbalance-threshold "$IMBALANCE_THRESHOLD"
