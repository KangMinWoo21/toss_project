param(
    [Parameter(Mandatory = $true)]
    [string]$Server,

    [string]$RemoteDir = "/home/ubuntu/toss-stock-bot",
    [string]$LocalDir = "",
    [string]$RemotePattern = "data/scalper/*.csv",
    [string]$IdentityFile = ""
)

$ErrorActionPreference = "Stop"

if (-not $LocalDir) {
    $repo = Split-Path -Parent $PSScriptRoot
    $LocalDir = Join-Path $repo "data\scalper_cloud"
}

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$remote = "${Server}:${RemoteDir}/${RemotePattern}"

if ($IdentityFile) {
    scp -i $IdentityFile $remote $LocalDir
} else {
    scp $remote $LocalDir
}

if ($LASTEXITCODE -ne 0) {
    throw "scp failed with exit code $LASTEXITCODE"
}

Write-Output "downloaded scalper data to $LocalDir"
