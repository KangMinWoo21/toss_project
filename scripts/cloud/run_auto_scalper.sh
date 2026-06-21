#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/toss-stock-bot}"
KR_SYMBOLS="${KR_SYMBOLS:-005930,000660}"
US_SYMBOLS="${US_SYMBOLS:-AAPL,NVDA,TSLA,QQQ}"
ITERATIONS_PER_SYMBOL="${ITERATIONS_PER_SYMBOL:-1}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1}"
IDLE_SECONDS="${IDLE_SECONDS:-60}"
MAX_SPREAD_PCT="${MAX_SPREAD_PCT:-0.2}"
VOLUME_SPIKE_MULTIPLIER="${VOLUME_SPIKE_MULTIPLIER:-3.0}"
IMBALANCE_THRESHOLD="${IMBALANCE_THRESHOLD:-1.5}"

cd "$REPO_DIR"
mkdir -p data/scalper

exec python3 -m backtester auto-scalp \
  --kr-symbols "$KR_SYMBOLS" \
  --us-symbols "$US_SYMBOLS" \
  --iterations-per-symbol "$ITERATIONS_PER_SYMBOL" \
  --interval-seconds "$INTERVAL_SECONDS" \
  --idle-seconds "$IDLE_SECONDS" \
  --output-dir data/scalper \
  --max-spread-pct "$MAX_SPREAD_PCT" \
  --volume-spike-multiplier "$VOLUME_SPIKE_MULTIPLIER" \
  --imbalance-threshold "$IMBALANCE_THRESHOLD"
