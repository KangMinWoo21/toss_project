#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/toss-stock-bot}"
DATE="${1:-$(TZ=Asia/Seoul date +%F)}"

cd "$REPO_DIR"
mkdir -p backups

if compgen -G "data/scalper/*_${DATE}_paper_scalp.csv" > /dev/null; then
  zip -j "backups/scalper_${DATE}.zip" data/scalper/*_"${DATE}"_paper_scalp.csv
  echo "created backups/scalper_${DATE}.zip"
else
  echo "no scalper files found for ${DATE}"
fi
