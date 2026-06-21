param(
    [string]$Symbol = "005930",
    [int]$Iterations = 23400,
    [double]$IntervalSeconds = 1
)

$ErrorActionPreference = "Stop"

$repo = "C:\Users\KangMinWoo\Documents\토스증권"
$python = "C:\Users\KangMinWoo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$date = Get-Date -Format "yyyy-MM-dd"
$output = Join-Path $repo "data\scalper\${Symbol}_${date}_paper_scalp.csv"

Set-Location $repo

& $python -m backtester paper-scalp `
    --symbol $Symbol `
    --iterations $Iterations `
    --interval-seconds $IntervalSeconds `
    --output $output `
    --append `
    --require-date $date
