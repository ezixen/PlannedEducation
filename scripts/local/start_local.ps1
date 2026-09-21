#!/usr/bin/env pwsh
<#
.SYNOPSIS
Start WIWM local stack: API + HTTPS portal + HTTP admin + one Chrome Canary (CDP).

.USAGE
    .\start-stop\start_local.ps1
    .\start-stop\start_local.ps1 -Path "/"
    .\start-stop\start_local.ps1 -SkipBrowser

.NOTES
  Opens at most three external terminals (API :8000, portal :5173, admin :5174) when needed,
  plus one Canary with portal + admin tabs. Re-running reuses listeners (no duplicate shells).
  Stop with: .\start-stop\stop_local.ps1
#>

[CmdletBinding()]
param(
    [string]$Path = "/",
    [int]$DebugPort = 9222,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
# Native curl failures (connection refused) must not abort Wait-HttpOk loops (PS 7.3+).
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
if ($PSStyle) { $PSStyle.OutputRendering = "PlainText" }

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$PortalUrl = "https://127.0.0.1:5173"
$AdminUrl = "http://127.0.0.1:5174"
$ApiUrl = "http://127.0.0.1:8000"
$OpenUrl = if ($Path.StartsWith("http")) { $Path } else { "$PortalUrl$Path" }
$Py = "C:/.venv/Scripts/python.exe"
$PortalDir = Join-Path $RepoRoot "web\apps\portal"
$AdminDir = Join-Path $RepoRoot "web\apps\admin"
$StatePath = Join-Path $RepoRoot "artifacts\local-stack.json"
$CanaryUserData = Join-Path $env:TEMP "wiwm-canary-debug-profile"
$LauncherDir = Join-Path $RepoRoot "artifacts\local-launchers"

function Resolve-ShellExe {
    # Prefer a real pwsh binary. App Execution Alias stubs under LocalAppData\WindowsApps
    # often report version 0.0.0.0 and can fail when Start-Process spawns -NoExit windows.
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($PSVersionTable.PSEdition -eq 'Core' -and $PSHOME) {
        $candidates.Add((Join-Path $PSHOME 'pwsh.exe'))
    }
    foreach ($p in @(
        "$env:ProgramFiles\PowerShell\7\pwsh.exe",
        "${env:ProgramFiles(x86)}\PowerShell\7\pwsh.exe"
    )) {
        if ($p) { $candidates.Add($p) }
    }
    $storeRoot = Join-Path $env:ProgramFiles 'WindowsApps'
    if (Test-Path -LiteralPath $storeRoot) {
        try {
            $pkgDir = Get-ChildItem -LiteralPath $storeRoot -Directory -Filter 'Microsoft.PowerShell_*' -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                Select-Object -First 1
            if ($pkgDir) {
                $pkgPwsh = Join-Path $pkgDir.FullName 'pwsh.exe'
                if (Test-Path -LiteralPath $pkgPwsh) { $candidates.Add($pkgPwsh) }
            }
        } catch { }
    }
    $cmd = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $candidates.Add([string]$cmd.Source) }
    $cmdPs = Get-Command powershell -ErrorAction SilentlyContinue
    if ($cmdPs -and $cmdPs.Source) { $candidates.Add([string]$cmdPs.Source) }

    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $ver = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($candidate)
            if ($ver -and $ver.FileMajorPart -eq 0 -and $ver.FileMinorPart -eq 0 -and $candidate -match 'WindowsApps\\pwsh\.exe$') {
                continue
            }
        } catch { }
        return $candidate
    }
    return $null
}

$ShellExe = Resolve-ShellExe
if (-not $ShellExe) {
    Write-Host "ERROR: No PowerShell executable found." -ForegroundColor Red
    exit 1
}

function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        if ($ok -and $client.Connected) { return $true }
        return $false
    } catch {
        return $false
    } finally {
        try { $client.Close() } catch { }
    }
}

function Test-ProcessAlive([int]$ProcessId) {
    if ($ProcessId -le 0) { return $false }
    return [bool](Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Stop-ProcessTree([int]$ProcessId, [string]$Label) {
    if ($ProcessId -le 0) { return }
    if (-not (Test-ProcessAlive $ProcessId)) { return }
    $null = & taskkill.exe /PID $ProcessId /T /F 2>&1
    Write-Host "Cleared stale $Label (PID $ProcessId)." -ForegroundColor Yellow
}

function Get-ListenPids([int]$Port) {
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        foreach ($processId in @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)) {
            if ($processId -gt 0) { [void]$ids.Add([int]$processId) }
        }
    }
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
    foreach ($processId in @(Get-ListenPids $Port)) {
        Stop-ProcessTree -ProcessId $processId -Label "$Label :$Port"
    }
}

function Get-HttpCode([string]$Url, [switch]$SkipCertCheck) {
    try {
        if ($SkipCertCheck) {
            return [string](& curl.exe -sk -o NUL -w "%{http_code}" --max-time 3 $Url 2>$null)
        }
        return [string](& curl.exe -s -o NUL -w "%{http_code}" --max-time 3 $Url 2>$null)
    } catch {
        return "000"
    }
}

function Test-HttpUp([string]$Url, [switch]$SkipCertCheck) {
    # Any HTTP answer means the server accepted TCP+TLS and spoke HTTP (not just a random listener).
    $code = Get-HttpCode -Url $Url -SkipCertCheck:$SkipCertCheck
    return ($code -match '^\d{3}$' -and $code -ne '000')
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 90, [switch]$SkipCertCheck) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = "000"
    while ((Get-Date) -lt $deadline) {
        $last = Get-HttpCode -Url $Url -SkipCertCheck:$SkipCertCheck
        if ($last -match '^\d{3}$' -and $last -ne '000') { return $true }
        Start-Sleep -Milliseconds 800
    }
    Write-Host "Last HTTP code for $Url was '$last'." -ForegroundColor Yellow
    return $false
}

function Wait-LocalPort([int]$Port, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort $Port) { return $true }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Find-ChromeCanary {
    foreach ($p in @(
        "$env:LOCALAPPDATA\Google\Chrome SxS\Application\chrome.exe",
        "$env:PROGRAMFILES\Google\Chrome SxS\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome SxS\Application\chrome.exe"
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    return $null
}

function Read-StackState {
    if (-not (Test-Path -LiteralPath $StatePath)) { return $null }
    try {
        return Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Write-StackState($State) {
    New-Item -ItemType Directory -Force -Path (Split-Path $StatePath) | Out-Null
    ($State | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $StatePath -Encoding utf8
}

function New-LauncherScript([string]$Name, [string]$Content) {
    New-Item -ItemType Directory -Force -Path $LauncherDir | Out-Null
    $path = Join-Path $LauncherDir $Name
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $Content, $utf8NoBom)
    return $path
}

function Start-ShellWindow([string]$Title, [string]$LauncherPath) {
    $proc = Start-Process -FilePath $ShellExe -PassThru -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-File', $LauncherPath
    )
    Write-Host ("{0} shell PID {1}" -f $Title, $proc.Id) -ForegroundColor Gray
    return $proc
}

function Get-CanaryPageUrls([int]$Port) {
    try {
        $raw = & curl.exe -s "http://127.0.0.1:$Port/json/list" 2>$null
        if (-not $raw) { return @() }
        $tabs = $raw | ConvertFrom-Json
        return @($tabs | Where-Object { $_.type -eq 'page' } | ForEach-Object { $_.url })
    } catch {
        return @()
    }
}

function Open-CanaryTab([int]$Port, [string]$Url) {
    $existing = Get-CanaryPageUrls $Port
    $base = $Url.TrimEnd('/')
    $already = $existing | Where-Object { $_ -and ($_.TrimEnd('/') -eq $base -or $_.StartsWith("$base/")) }
    if ($already) {
        Write-Host "Canary already has tab for $Url - not opening another." -ForegroundColor Yellow
        return
    }
    $encoded = [uri]::EscapeDataString($Url)
    # Chrome 144+: /json/new requires PUT (GET returns "unsafe HTTP verb").
    & curl.exe -s -X PUT "http://127.0.0.1:$Port/json/new?$encoded" | Out-Null
}

function Ensure-NpmDeps([string]$AppDir, [string]$Label, [string]$Npm, [string]$NodeDir) {
    if (Test-Path -LiteralPath (Join-Path $AppDir "node_modules")) { return }
    Write-Host "$Label node_modules missing - running npm ci..." -ForegroundColor Yellow
    Push-Location $AppDir
    try {
        if ($NodeDir) { $env:PATH = "$NodeDir;$env:PATH" }
        & $Npm ci
        if ($LASTEXITCODE -ne 0) { throw "$Label npm ci failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}

Write-Host ""
Write-Host "=== WIWM local start ===" -ForegroundColor Cyan
Write-Host "API:    $ApiUrl" -ForegroundColor Green
Write-Host "Portal: $PortalUrl  (mkcert HTTPS)" -ForegroundColor Green
Write-Host "Admin:  $AdminUrl  (Vite HTTP + API proxy)" -ForegroundColor Green
Write-Host "Canary: remote debugging :$DebugPort" -ForegroundColor Green
Write-Host "Shell:  $ShellExe" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path -LiteralPath $Py)) {
    Write-Host "ERROR: $Py not found. Use C:/.venv per AGENTS.md" -ForegroundColor Red
    exit 1
}
foreach ($pair in @(@{ Dir = $PortalDir; Name = 'Portal' }, @{ Dir = $AdminDir; Name = 'Admin' })) {
    if (-not (Test-Path -LiteralPath $pair.Dir)) {
        Write-Host "ERROR: $($pair.Name) not found at $($pair.Dir)" -ForegroundColor Red
        exit 1
    }
}

$npmCmd = $null
$nodeDir = $null
foreach ($dir in @(
    'C:\Program Files\nodejs',
    "${env:ProgramFiles}\nodejs",
    "${env:ProgramFiles(x86)}\nodejs",
    "$env:LOCALAPPDATA\Programs\nodejs"
)) {
    if ($dir -and (Test-Path -LiteralPath (Join-Path $dir 'node.exe'))) {
        $nodeDir = $dir
        $candNpm = Join-Path $dir 'npm.cmd'
        if (Test-Path -LiteralPath $candNpm) { $npmCmd = $candNpm }
        break
    }
}
if (-not $nodeDir) {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd -and $nodeCmd.Source) {
        $nodeDir = Split-Path -Parent $nodeCmd.Source
        $candNpm = Join-Path $nodeDir 'npm.cmd'
        if (Test-Path -LiteralPath $candNpm) { $npmCmd = $candNpm }
    }
}
if (-not $npmCmd) {
    $npmFromPath = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmFromPath -and $npmFromPath.Source) {
        $maybeDir = Split-Path -Parent $npmFromPath.Source
        $candNpm = Join-Path $maybeDir 'npm.cmd'
        if (Test-Path -LiteralPath $candNpm) {
            $npmCmd = $candNpm
            if (-not $nodeDir) { $nodeDir = $maybeDir }
        } else {
            $npmCmd = [string]$npmFromPath.Source
        }
    }
}
if (-not $npmCmd -or -not $nodeDir) {
    Write-Host "ERROR: Node.js/npm not found. Install Node and ensure C:\Program Files\nodejs is on PATH." -ForegroundColor Red
    exit 1
}
$nodePathPrefix = $nodeDir
Write-Host "Node:   $(Join-Path $nodeDir 'node.exe')" -ForegroundColor Gray
Write-Host "npm:    $npmCmd" -ForegroundColor Gray

$prev = Read-StackState
$backendShellPid = 0
$portalShellPid = 0
$adminShellPid = 0
$canaryPid = 0
if ($prev) {
    if ($prev.PSObject.Properties.Name -contains 'backendShellPid') { $backendShellPid = [int]$prev.backendShellPid }
    if ($prev.PSObject.Properties.Name -contains 'portalShellPid') { $portalShellPid = [int]$prev.portalShellPid }
    if ($prev.PSObject.Properties.Name -contains 'adminShellPid') { $adminShellPid = [int]$prev.adminShellPid }
    if ($prev.PSObject.Properties.Name -contains 'canaryPid') { $canaryPid = [int]$prev.canaryPid }
}

if ($backendShellPid -gt 0 -and -not (Test-LocalPort 8000) -and (Test-ProcessAlive $backendShellPid)) {
    Stop-ProcessTree -ProcessId $backendShellPid -Label 'API shell'
    $backendShellPid = 0
}
if ($portalShellPid -gt 0 -and -not (Test-LocalPort 5173) -and (Test-ProcessAlive $portalShellPid)) {
    Stop-ProcessTree -ProcessId $portalShellPid -Label 'portal shell'
    $portalShellPid = 0
}
if ($adminShellPid -gt 0 -and -not (Test-LocalPort 5174) -and (Test-ProcessAlive $adminShellPid)) {
    Stop-ProcessTree -ProcessId $adminShellPid -Label 'admin shell'
    $adminShellPid = 0
}

function Save-StackState {
    Write-StackState ([pscustomobject]@{
        backendShellPid = [int]$script:backendShellPid
        portalShellPid  = [int]$script:portalShellPid
        adminShellPid   = [int]$script:adminShellPid
        canaryPid       = [int]$script:canaryPid
        debugPort       = [int]$DebugPort
        startedAt       = (Get-Date).ToString('o')
    })
}

# --- Backend ---
$apiHealthy = (Test-LocalPort 8000) -and (Test-HttpUp "$ApiUrl/health")
if ($apiHealthy) {
    Write-Host "Backend already healthy on :8000 - reusing." -ForegroundColor Yellow
} else {
    if (Test-LocalPort 8000) {
        Write-Host "Port :8000 is up but /health failed - recycling listeners." -ForegroundColor Yellow
        Stop-PortListeners -Port 8000 -Label 'API'
        Start-Sleep -Seconds 1
    }
    Write-Host "Starting backend (1 terminal)..." -ForegroundColor Gray
    New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "artifacts") | Out-Null
    $backendLauncher = New-LauncherScript "wiwm-api.ps1" @"
`$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    `$PSNativeCommandUseErrorActionPreference = `$false
}
Set-Location -LiteralPath '$RepoRoot'
try { `$Host.UI.RawUI.WindowTitle = 'WIWM API :8000' } catch {}
`$env:PYTHONPATH = '$(Join-Path $RepoRoot 'src')'
if (-not `$env:WIWM_JWT_SECRET) { `$env:WIWM_JWT_SECRET = 'dev-only-change-me-wiwm' }
Write-Host 'WIWM API http://127.0.0.1:8000/health' -ForegroundColor Cyan
& '$Py' -m uvicorn wiwm.main:app --reload --host 127.0.0.1 --port 8000
"@
    $backendProc = Start-ShellWindow -Title "Backend" -LauncherPath $backendLauncher
    $backendShellPid = [int]$backendProc.Id
}

# --- Portal ---
$portalHealthy = (Test-LocalPort 5173) -and (Test-HttpUp "$PortalUrl/" -SkipCertCheck)
if ($portalHealthy) {
    Write-Host "Portal already healthy on :5173 - reusing." -ForegroundColor Yellow
} else {
    if (Test-LocalPort 5173) {
        Write-Host "Port :5173 is up but HTTPS check failed - recycling listeners." -ForegroundColor Yellow
        Stop-PortListeners -Port 5173 -Label 'portal'
        Start-Sleep -Seconds 1
    }
    Write-Host "Starting portal (1 terminal)..." -ForegroundColor Gray
    Ensure-NpmDeps -AppDir $PortalDir -Label "Portal" -Npm $npmCmd -NodeDir $nodePathPrefix
    $portalLauncher = New-LauncherScript "wiwm-portal.ps1" @"
`$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    `$PSNativeCommandUseErrorActionPreference = `$false
}
Set-Location -LiteralPath '$PortalDir'
try { `$Host.UI.RawUI.WindowTitle = 'WIWM Portal :5173' } catch {}
`$env:PATH = '$nodePathPrefix;' + `$env:PATH
`$env:BROWSER = 'none'
# Never inherit APK/smoke Hosting API base into local Vite (breaks CORS login).
`$env:VITE_API_BASE_URL = ''
`$env:VITE_WS_BASE_URL = ''
Write-Host 'WIWM Portal https://127.0.0.1:5173' -ForegroundColor Cyan
Write-Host ("node=" + (Get-Command node -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)) -ForegroundColor Gray
& '$npmCmd' run dev -- --host 127.0.0.1 --port 5173
"@
    $portalProc = Start-ShellWindow -Title "Portal" -LauncherPath $portalLauncher
    $portalShellPid = [int]$portalProc.Id
    if (-not (Wait-LocalPort -Port 5173 -TimeoutSec 45)) {
        Write-Host "ERROR: Portal shell started but nothing is listening on :5173." -ForegroundColor Red
        Write-Host "Check the 'WIWM Portal :5173' window (node/npm/vite error)." -ForegroundColor Yellow
        exit 1
    }
}

# --- Admin ---
$adminHealthy = (Test-LocalPort 5174) -and (Test-HttpUp "$AdminUrl/")
if ($adminHealthy) {
    Write-Host "Admin already healthy on :5174 - reusing." -ForegroundColor Yellow
} else {
    if (Test-LocalPort 5174) {
        Write-Host "Port :5174 is up but HTTP check failed - recycling listeners." -ForegroundColor Yellow
        Stop-PortListeners -Port 5174 -Label 'admin'
        Start-Sleep -Seconds 1
    }
    Write-Host "Starting admin (1 terminal)..." -ForegroundColor Gray
    Ensure-NpmDeps -AppDir $AdminDir -Label "Admin" -Npm $npmCmd -NodeDir $nodePathPrefix
    $adminLauncher = New-LauncherScript "wiwm-admin.ps1" @"
`$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    `$PSNativeCommandUseErrorActionPreference = `$false
}
Set-Location -LiteralPath '$AdminDir'
try { `$Host.UI.RawUI.WindowTitle = 'WIWM Admin :5174' } catch {}
`$env:PATH = '$nodePathPrefix;' + `$env:PATH
`$env:BROWSER = 'none'
`$env:VITE_API_BASE_URL = ''
`$env:VITE_WS_BASE_URL = ''
Write-Host 'WIWM Admin http://127.0.0.1:5174' -ForegroundColor Cyan
Write-Host ("node=" + (Get-Command node -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)) -ForegroundColor Gray
& '$npmCmd' run dev -- --host 127.0.0.1 --port 5174
"@
    $adminProc = Start-ShellWindow -Title "Admin" -LauncherPath $adminLauncher
    $adminShellPid = [int]$adminProc.Id
    if (-not (Wait-LocalPort -Port 5174 -TimeoutSec 45)) {
        Write-Host "ERROR: Admin shell started but nothing is listening on :5174." -ForegroundColor Red
        Write-Host "Check the 'WIWM Admin :5174' window (node/npm/vite error)." -ForegroundColor Yellow
        exit 1
    }
}

Save-StackState

Write-Host "Waiting for API..." -ForegroundColor Gray
if (-not (Wait-HttpOk "$ApiUrl/health" -TimeoutSec 90)) {
    Write-Host "ERROR: API did not become ready at $ApiUrl/health" -ForegroundColor Red
    Write-Host "Tip: confirm local Postgres :5433 is up (WIWM_DATABASE_URL in .env)." -ForegroundColor Yellow
    exit 1
}
Write-Host "API ready." -ForegroundColor Green

Write-Host "Waiting for portal HTTPS..." -ForegroundColor Gray
if (-not (Wait-HttpOk "$PortalUrl/" -TimeoutSec 90 -SkipCertCheck)) {
    Write-Host "ERROR: Portal did not become ready at $PortalUrl/" -ForegroundColor Red
    Write-Host "Check the 'WIWM Portal :5173' window for vite/mkcert errors." -ForegroundColor Yellow
    exit 1
}
Write-Host "Portal ready." -ForegroundColor Green

Write-Host "Waiting for admin..." -ForegroundColor Gray
if (-not (Wait-HttpOk "$AdminUrl/" -TimeoutSec 90)) {
    Write-Host "ERROR: Admin did not become ready at $AdminUrl/" -ForegroundColor Red
    Write-Host "Check the 'WIWM Admin :5174' window for vite errors." -ForegroundColor Yellow
    exit 1
}
Write-Host "Admin ready." -ForegroundColor Green

$cssCode = Get-HttpCode -Url "$PortalUrl/src/styles.css" -SkipCertCheck
if ($cssCode -ne "200") {
    Write-Host "WARNING: portal CSS returned HTTP $cssCode (UI may be blank)." -ForegroundColor Yellow
} else {
    Write-Host "Portal CSS OK." -ForegroundColor Green
}

if ($SkipBrowser) {
    Write-Host "SkipBrowser set - open $OpenUrl and $AdminUrl yourself." -ForegroundColor Yellow
    exit 0
}

$canary = Find-ChromeCanary
if (-not $canary) {
    Write-Host "WARNING: Chrome Canary not found. Open $OpenUrl and $AdminUrl manually." -ForegroundColor Yellow
    exit 0
}

if (Test-LocalPort $DebugPort) {
    Write-Host "Canary CDP already on :$DebugPort - opening portal + admin tabs." -ForegroundColor Yellow
    Open-CanaryTab -Port $DebugPort -Url $OpenUrl
    Open-CanaryTab -Port $DebugPort -Url $AdminUrl
} else {
    New-Item -ItemType Directory -Force -Path $CanaryUserData | Out-Null
    Remove-Item -Force -ErrorAction SilentlyContinue @(
        "$CanaryUserData\SingletonLock",
        "$CanaryUserData\SingletonSocket",
        "$CanaryUserData\SingletonCookie"
    )

    Write-Host "Launching Canary (CDP :$DebugPort) with portal + admin..." -ForegroundColor Gray
    $canaryProc = Start-Process -FilePath $canary -PassThru -ArgumentList @(
        "--remote-debugging-port=$DebugPort",
        "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=*",
        "--user-data-dir=$CanaryUserData",
        "--no-first-run",
        "--no-default-browser-check",
        $OpenUrl,
        $AdminUrl
    )
    $canaryPid = [int]$canaryProc.Id
    Save-StackState
    Write-Host "Canary PID $canaryPid" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done. External windows: API + portal + admin terminals (only if newly started) + 1 Canary." -ForegroundColor Green
Write-Host "  Portal: $OpenUrl" -ForegroundColor Cyan
Write-Host "  Admin:  $AdminUrl" -ForegroundColor Cyan
Write-Host "  CDP:    http://127.0.0.1:$DebugPort" -ForegroundColor Cyan
Write-Host "  Stop:   .\start-stop\stop_local.ps1" -ForegroundColor Gray
Write-Host ""
