#!/usr/bin/env pwsh
<#
.SYNOPSIS
Stop WIWM local stack started by start_local.ps1 (shell trees + Canary + ports).

.USAGE
    .\start-stop\stop_local.ps1

.NOTES
  Kills tracked PowerShell host windows (so -NoExit terminals close), then
  Canary, then any leftover listeners on :8000 / :5173 / :5174 / :9222.
#>

$ErrorActionPreference = "Continue"
if ($PSStyle) { $PSStyle.OutputRendering = "PlainText" }

$RepoRoot = Split-Path -Parent $PSScriptRoot
$StatePath = Join-Path $RepoRoot "artifacts\local-stack.json"
$CanaryUserData = Join-Path $env:TEMP "wiwm-canary-debug-profile"

function Stop-ProcessTree([int]$ProcessId, [string]$Label) {
    if ($ProcessId -le 0) { return }
    $alive = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $alive) {
        Write-Host "No process PID $ProcessId ($Label)" -ForegroundColor Gray
        return
    }
    $out = & taskkill.exe /PID $ProcessId /T /F 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Stopped tree PID $ProcessId ($Label)" -ForegroundColor Yellow
    } else {
        Write-Host "taskkill PID $ProcessId ($Label): $out" -ForegroundColor Red
        try {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped PID $ProcessId ($Label) via Stop-Process" -ForegroundColor Yellow
        } catch {
            Write-Host "Could not stop PID ${ProcessId}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

function Get-ListenPids([int]$Port) {
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        foreach ($processId in @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)) {
            if ($processId -gt 0) { [void]$ids.Add([int]$processId) }
        }
    }
    # Fallback when Get-NetTCPConnection is empty/unavailable (some Windows builds).
    if ($ids.Count -eq 0) {
        $lines = & netstat.exe -ano -p tcp 2>$null
        foreach ($line in $lines) {
            if ($line -notmatch 'LISTENING') { continue }
            if ($line -notmatch ":$Port\s+") { continue }
            if ($line -match '\s(\d+)\s*$') {
                $processId = [int]$Matches[1]
                if ($processId -gt 0) { [void]$ids.Add($processId) }
            }
        }
    }
    return @($ids)
}

function Stop-PortListeners([int]$Port, [string]$Label) {
    $ids = @(Get-ListenPids $Port)
    if ($ids.Count -eq 0) {
        Write-Host "No listener on :$Port ($Label)" -ForegroundColor Gray
        return
    }
    foreach ($processId in $ids) {
        Stop-ProcessTree -ProcessId $processId -Label "$Label :$Port"
    }
}

Write-Host ""
Write-Host "=== WIWM local stop ===" -ForegroundColor Cyan

$state = $null
if (Test-Path -LiteralPath $StatePath) {
    try {
        $state = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
    } catch {
        Write-Host "Could not read $StatePath - falling back to ports only." -ForegroundColor Yellow
    }
}

if ($state) {
    if ($state.canaryPid) {
        Stop-ProcessTree -ProcessId ([int]$state.canaryPid) -Label "Canary"
    }
    if ($state.adminShellPid) {
        Stop-ProcessTree -ProcessId ([int]$state.adminShellPid) -Label "admin shell"
    }
    if ($state.portalShellPid) {
        Stop-ProcessTree -ProcessId ([int]$state.portalShellPid) -Label "portal shell"
    }
    if ($state.backendShellPid) {
        Stop-ProcessTree -ProcessId ([int]$state.backendShellPid) -Label "API shell"
    }
} else {
    Write-Host "No artifacts/local-stack.json - stopping by ports only." -ForegroundColor Yellow
}

$debugPort = 9222
if ($state -and $state.debugPort) { $debugPort = [int]$state.debugPort }

Stop-PortListeners -Port $debugPort -Label "Canary CDP"
Stop-PortListeners -Port 5174 -Label "admin"
Stop-PortListeners -Port 5173 -Label "portal"
Stop-PortListeners -Port 8000 -Label "API"

Remove-Item -Force -ErrorAction SilentlyContinue @(
    "$CanaryUserData\SingletonLock",
    "$CanaryUserData\SingletonSocket",
    "$CanaryUserData\SingletonCookie"
)

Start-Sleep -Seconds 1

foreach ($port in @($debugPort, 5174, 5173, 8000)) {
    $left = @(Get-ListenPids $port)
    if ($left.Count -gt 0) {
        Write-Host "Port $port still in use (PIDs: $($left -join ', '))." -ForegroundColor Red
    } else {
        Write-Host "Port $port free." -ForegroundColor Green
    }
}

if (Test-Path -LiteralPath $StatePath) {
    Remove-Item -Force -ErrorAction SilentlyContinue $StatePath
    Write-Host "Cleared $StatePath" -ForegroundColor Gray
}

Write-Host ""
