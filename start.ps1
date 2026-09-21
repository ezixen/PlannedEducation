#!/usr/bin/env pwsh
<#
.SYNOPSIS
Start the PlannedEducation local stack: API + Portal + visible Chrome Canary
#>

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$PortalUrl = "http://localhost:5173"
$LauncherDir = Join-Path $RepoRoot "artifacts\local-launchers"
$CanaryUserData = Join-Path $env:TEMP "plannededucation-canary-profile"
$PythonExe = "C:\.venv\Scripts\python.exe"
$NodeDirectory = "C:\Program Files\nodejs"
$JwtSecret = "plannededucation-local-development-secret-only"

if (-not (Test-Path $LauncherDir)) { New-Item -ItemType Directory -Path $LauncherDir | Out-Null }
if (-not (Test-Path $PythonExe)) {
    throw "Required project Python environment was not found at $PythonExe."
}
if (-not (Test-Path (Join-Path $RepoRoot "web\apps\portal\package.json"))) {
    throw "Portal package.json was not found. Run this script from the repository root."
}

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
    Set-Content -Path $ApiLauncher -Encoding utf8 -Value @"
`$env:DATABASE_URL="sqlite:///$($RepoRoot -replace '\\', '/')/plannededucation.db"
`$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/plannededucation"
`$env:PLANNED_EDUCATION_ENV="development"
`$env:ALLOW_DEV_AUTH="true"
`$env:JWT_SECRET_KEY="$JwtSecret"
`$env:CORS_ORIGINS="$PortalUrl"
Set-Location "$RepoRoot"
Write-Host "Starting FastAPI Backend..." -ForegroundColor Green
& "$PythonExe" -m uvicorn src.plannededucation.api.main:app --reload --host 127.0.0.1 --port 8000
"@
    Start-Process pwsh -ArgumentList "-NoExit","-File","`"$ApiLauncher`""
} else {
    Write-Host "API already listening on 8000." -ForegroundColor Yellow
}

# 2. Start Portal if not running
if (-not (Test-LocalPort 5173)) {
    Write-Host "Starting Portal (Port 5173) in new window..." -ForegroundColor Cyan
    $npmCmd = Join-Path $NodeDirectory "npm.cmd"
    if (-not (Test-Path $npmCmd)) {
        $npmCmd = (Get-Command npm.cmd -ErrorAction Stop).Source
    }

    $PortalLauncher = Join-Path $LauncherDir "start_portal.ps1"
    Set-Content -Path $PortalLauncher -Encoding utf8 -Value @"
`$env:PATH = "$NodeDirectory;" + `$env:PATH
`$env:VITE_API_URL="http://localhost:8000"
Set-Location "$RepoRoot\web\apps\portal"
Write-Host "Starting React Portal..." -ForegroundColor Green
& "$npmCmd" run dev -- --host 127.0.0.1 --port 5173
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

if (-not (Test-Path $CanaryPath)) {
    throw "Chrome Canary or Chrome was not found. Services are running at $PortalUrl/login."
}

Start-Process -FilePath $CanaryPath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$CanaryUserData`"",
    "--no-first-run",
    "--no-default-browser-check",
    "`"$PortalUrl/login`""
)
Write-Host "Stack is up. Chrome Canary opened at $PortalUrl/login." -ForegroundColor Green
