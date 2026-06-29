param(
    [Parameter(Mandatory = $true)]
    [string]$Server,

    [string]$RemoteDir = "/home/minwoo0180/toss-stock-bot",
    [string]$LocalDir = "",
    [string]$IdentityFile = "",
    [string[]]$RequiredFiles = @(
        "data/reports/monthly_order_plan_cloud.csv",
        "data/reports/monthly_order_plan_summary_cloud.md",
        "data/reports/monthly_decision_cloud.csv",
        "data/reports/monthly_risk_report_cloud.csv"
    ),
    [string[]]$OptionalFiles = @(
        "data/reports/monthly_deployment_gate_pit_universe.csv",
        "data/reports/monthly_performance_audit.csv",
        "data/reports/monthly_validation_scenarios_pit_universe.csv",
        "data/reports/production_readiness.csv",
        "data/reports/production_readiness_report.md"
    )
)

$ErrorActionPreference = "Stop"

if (-not $LocalDir) {
    $repo = Split-Path -Parent $PSScriptRoot
    $LocalDir = Join-Path $repo "data\reports_cloud"
}

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

function Copy-CloudReport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RemotePath,

        [Parameter(Mandatory = $true)]
        [bool]$Required
    )

    $remote = "${Server}:${RemoteDir}/${RemotePath}"
    if ($IdentityFile) {
        scp -i $IdentityFile $remote $LocalDir
    } else {
        scp $remote $LocalDir
    }

    if ($LASTEXITCODE -ne 0) {
        if ($Required) {
            throw "scp failed with exit code $LASTEXITCODE for $RemotePath"
        }
        Write-Warning "optional cloud report not downloaded: $RemotePath"
    }
}

foreach ($file in $RequiredFiles) {
    Copy-CloudReport -RemotePath $file -Required $true
}

foreach ($file in $OptionalFiles) {
    Copy-CloudReport -RemotePath $file -Required $false
}

Write-Output "downloaded cloud reports to $LocalDir"
