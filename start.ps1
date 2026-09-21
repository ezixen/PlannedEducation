#!/usr/bin/env pwsh
<#
.SYNOPSIS
Start PlannedEducation local stack: API + Portal + Chrome Canary
#>

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$PortalUrl = "http://localhost:5173"
$ApiUrl = "http://localhost:8000"
$LauncherDir = Join-Path $RepoRoot "artifacts\local-launchers"
$CanaryUserData = Join-Path $env:TEMP "plannededucation-canary-profile"

if (-not (Test-Path $LauncherDir)) { New-Item -ItemType Directory -Path $LauncherDir | Out-Null }

function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        if ($ok -and $client.Connected) { return $true }
        return $false
    } catch { return $false } finally { $client.Close() }
}

# 1. Start API if not running
if (-not (Test-LocalPort 8000)) {
    Write-Host "Starting API (Port 8000) in new window..." -ForegroundColor Cyan
    $ApiLauncher = Join-Path $LauncherDir "start_api.ps1"
    Set-Content -Path $ApiLauncher -Value @"
`$env:DATABASE_URL="sqlite:///./plannededucation.db"
Set-Location "$RepoRoot"
Write-Host "Starting FastAPI Backend..." -ForegroundColor Green
C:/.venv/Scripts/python.exe -m uvicorn src.plannededucation.api.main:app --reload --port 8000
"@
    Start-Process pwsh -ArgumentList "-NoExit","-File","`"$ApiLauncher`""
} else {
    Write-Host "API already listening on 8000." -ForegroundColor Yellow
}

# 2. Start Portal if not running
if (-not (Test-LocalPort 5173)) {
    Write-Host "Starting Portal (Port 5173) in new window..." -ForegroundColor Cyan
    $PortalLauncher = Join-Path $LauncherDir "start_portal.ps1"
    Set-Content -Path $PortalLauncher -Value @"
Set-Location "$RepoRoot\web\apps\portal"
Write-Host "Starting React Portal..." -ForegroundColor Green
npm.cmd run dev
"@
    Start-Process pwsh -ArgumentList "-NoExit","-File","`"$PortalLauncher`""
} else {
    Write-Host "Portal already listening on 5173." -ForegroundColor Yellow
}

# 3. Wait for services
Write-Host "Waiting for services to become available..."
$retries = 60
while (-not (Test-LocalPort 8000) -or -not (Test-LocalPort 5173)) {
    Start-Sleep -Seconds 1
    $retries--
    if ($retries -le 0) {
        Write-Host "Timeout waiting for services!" -ForegroundColor Red
        exit 1
    }
}

# 4. Launch Canary
Write-Host "Launching Chrome Canary..." -ForegroundColor Cyan
$CanaryPath = "${env:LOCALAPPDATA}\Google\Chrome SxS\Application\chrome.exe"
if (-not (Test-Path $CanaryPath)) {
    Write-Host "Canary not found at $CanaryPath, falling back to standard Chrome..." -ForegroundColor Yellow
    $CanaryPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
}

if (Test-Path $CanaryPath) {
    Start-Process $CanaryPath -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=`"$CanaryUserData`"", "--no-first-run", "--no-default-browser-check", "`"$PortalUrl/login`""
    Write-Host "Stack is up! Services and browser running." -ForegroundColor Green
} else {
    Write-Host "Could not find Chrome. Services are running, please open $PortalUrl/login manually." -ForegroundColor Red
}
