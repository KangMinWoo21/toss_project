param(
    [Parameter(Mandatory = $true)]
    [string]$Server,

    [string]$TaskName = "TossScalperDataDownload",
    [string]$RemoteDir = "/home/minwoo0180/toss-stock-bot",
    [string]$LocalDir = "",
    [string]$IdentityFile = ""
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
if (-not $LocalDir) {
    $LocalDir = Join-Path $repo "data\scalper_cloud"
}
$script = Join-Path $repo "scripts\download_scalper_data.ps1"
$args = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Server `"$Server`" -RemoteDir `"$RemoteDir`" -LocalDir `"$LocalDir`""
if ($IdentityFile) {
    $args += " -IdentityFile `"$IdentityFile`""
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Output "registered scheduled task: $TaskName"
