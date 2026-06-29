# Cloud Always-On Operation Plan

This plan keeps data collection and monthly paper planning alive even when the
notebook is powered off. It intentionally keeps live trading blocked until the
local readiness gates pass.

## Target Architecture

```text
Google Cloud VM or Oracle Always Free VM
  - systemd: Toss API tick collector
  - systemd timer or cron: daily backup
  - systemd timer or cron: monthly paper plan
  - local disk: data/scalper, data/reports, backups

Notebook
  - scheduled scp download when Windows starts
  - heavier backtests and report review
  - manual approval before any live order executor exists
```

## VM Responsibilities

1. Run `toss-scalper.service` continuously.
2. Store raw paper tick data under `data/scalper`.
3. Create backup zip files at least once per market day.
4. Run `monthly-plan` in paper mode near the start of each month.
5. Never place live orders unless a separate future executor passes strict risk
   gates.

## Notebook Responsibilities

1. Pull VM data with `scripts/download_scalper_data.ps1`.
2. Run heavy walk-forward validation locally when needed.
3. Inspect `production-check --strict` output before any action.
4. Keep API keys and SSH keys out of git.

## Safety Gates

Before any future live executor is allowed, it must check all of these:

```bash
python -m backtester production-check --strict --max-report-age-days 45
```

The current expected state is `WARN`, which means normal-size live trading must
remain blocked. `WARN` should allow paper planning and data collection only.

Additional required live-executor gates:

- no `data/KILL_SWITCH` file
- deployment gate is present and deployable
- performance guard is `PASS`
- risk report is `PASS`
- order plan has no `SKIP` orders unless explicitly allowed
- max daily loss and max order values are within limits
- deployment, validation, risk, coverage, and performance reports are not stale
- all orders are dry-run by default

## Monthly Paper Plan Command

Example cloud command:

```bash
cd ~/toss-stock-bot
python3 -m backtester monthly-plan \
  --data-dir data/krx_expanded \
  --as-of "$(date +%F)" \
  --cash 10000000 \
  --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv \
  --performance-report data/reports/monthly_performance_audit.csv \
  --max-report-age-days 45 \
  --require-performance-report \
  --require-deployment-gate \
  --output data/reports/monthly_order_plan_cloud.csv \
  --summary-output data/reports/monthly_order_plan_summary_cloud.md \
  --decision-output data/reports/monthly_decision_cloud.csv \
  --risk-output data/reports/monthly_risk_report_cloud.csv
```

If news, SNS, or disclosure event data is available:

```bash
python3 -m backtester merge-events \
  --input data/events/005930_google_news.csv \
  --input data/events/005930_sns.csv \
  --input data/events/krx15_dart_2018_2026.csv \
  --output data/events/combined_events.csv

python3 -m backtester monthly-plan \
  --data-dir data/krx_expanded \
  --as-of "$(date +%F)" \
  --cash 10000000 \
  --point-in-time-universe data/krx_metadata/krx_universe_monthly.csv \
  --events data/events/combined_events.csv \
  --event-source-weights google-news=1.0,sns=0.25,dart=0.5 \
  --event-lookback-days 20 \
  --min-entry-event-score -0.4 \
  --event-weight 0.25
```

## Scheduling Options

Preferred lightweight approach:

- systemd service for continuous tick collection
- cron or systemd timer for backup
- cron or systemd timer for monthly paper plan
- Windows Task Scheduler for notebook download when the notebook starts

Do not rely on the notebook for continuous collection. If cloud cost must be
zero, use the smallest free-tier VM and keep only outbound API calls plus local
storage.

## Install Monthly Paper Plan Timer

On the VM:

```bash
cd ~/toss-stock-bot
chmod +x scripts/cloud/*.sh

sudo cp scripts/cloud/toss-monthly-plan.service /etc/systemd/system/toss-monthly-plan.service
sudo cp scripts/cloud/toss-monthly-plan.timer /etc/systemd/system/toss-monthly-plan.timer
sudo systemctl daemon-reload
sudo systemctl enable --now toss-monthly-plan.timer
systemctl list-timers toss-monthly-plan.timer --no-pager
```

Manual test run:

```bash
cd ~/toss-stock-bot
REPO_DIR="$PWD" AS_OF="$(TZ=Asia/Seoul date +%F)" ./scripts/cloud/run_monthly_plan.sh
```

Expected behavior:

- `monthly_order_plan_cloud.csv` is written.
- `monthly_order_plan_summary_cloud.md` is written.
- `monthly_decision_cloud.csv` is written.
- `monthly_risk_report_cloud.csv` is written.
- `production_readiness.csv` and `production_readiness_report.md` are written
  after the monthly plan, using the cloud risk output.
- If KRX price data, PIT universe snapshots, performance audit, or deployment
  gate files are missing, the script exits before planning and prints the
  missing path.
- If deployment/performance reports are older than `MAX_REPORT_AGE_DAYS`, the
  generated risk report blocks execution.
- If the risk status is `WARN`, orders remain blocked but the plan still
  records what would have been considered.
- If the risk status is `BLOCK`, the service should fail and be visible in
  `journalctl -u toss-monthly-plan`.

## Data Sync

Scalper tick data is optional once the monthly strategy is the primary paper
workflow. Keep it only if short-term replay research is still useful.

Scalper tick pull command:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\download_scalper_data.ps1" `
  -Server "minwoo0180@35.225.105.114" `
  -RemoteDir "/home/minwoo0180/toss-stock-bot" `
  -IdentityFile "$env:USERPROFILE\.ssh\gcp_toss_scalper"
```

Monthly paper-plan report pull command:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\download_cloud_reports.ps1" `
  -Server "minwoo0180@35.225.105.114" `
  -RemoteDir "/home/minwoo0180/toss-stock-bot" `
  -IdentityFile "$env:USERPROFILE\.ssh\gcp_toss_scalper"
```

The monthly report command writes files into `data\reports_cloud`, including:

- `monthly_order_plan_cloud.csv`
- `monthly_order_plan_summary_cloud.md`
- `monthly_decision_cloud.csv`
- `monthly_risk_report_cloud.csv`
- optional validation/readiness reports when they exist on the VM

Register the monthly report download at Windows logon:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\register_cloud_reports_download_task.ps1" `
  -Server "minwoo0180@35.225.105.114" `
  -IdentityFile "$env:USERPROFILE\.ssh\gcp_toss_scalper"
```

The local scheduled task can run without an open PowerShell window as long as
the notebook is powered on and connected to the network.

## Current Recommendation

Keep cloud collection and paper planning enabled. Keep live execution disabled
until the performance audit no longer reports thin walk-forward margin,
drawdown pressure, or full-period return concentration.
