<# 
.SYNOPSIS
    PlannedEducation Uninstaller for Windows
    Carefully removes only the PlannedEducation platform from the server.
    Does NOT touch other system files or unrelated applications.

.DESCRIPTION
    This script removes the PlannedEducation platform from d:\Dev\PEserver.
    It will:
    1. Stop any running services/processes
    2. Ask about external dependencies one by one
    3. Remove the platform folder and all its contents
    4. Clean up scheduled tasks, services, and shortcuts

.NOTES
    Run as Administrator for best results.

    AI AGENT CONTRACT: before running with -AutoConfirm, the agent MUST STOP AND ASK the
    human to confirm (1) the exact -InstallDir to delete (data loss!) and (2) whether any
    external dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git) should be removed.
    There is NO "remove all dependencies" option; with -AutoConfirm all dependencies are kept.
    Logs of the installation being removed live in <InstallDir>\logs\ (deleted with it) -
    copy them first if they are needed for diagnosis.
#>

param(
    [string]$InstallDir = "",
    [switch]$AutoConfirm
)

# Auto-detect installation directory if not explicitly provided:
# 1. If running inside an installation folder (contains plannededucation.db, .env, or src\plannededucation), use $PSScriptRoot
# 2. Otherwise default to "C:\PlannedEducation" (matching install.ps1 default)
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $hasDb = Test-Path (Join-Path $PSScriptRoot "plannededucation.db")
    $hasSrc = Test-Path (Join-Path $PSScriptRoot "src\plannededucation")
    $hasEnv = Test-Path (Join-Path $PSScriptRoot ".env")
    if ($hasDb -or $hasSrc -or $hasEnv) {
        $InstallDir = $PSScriptRoot
    } else {
        $InstallDir = "C:\PlannedEducation"
    }
}

$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"
$BLUE = "Blue"
$CYAN = "Cyan"
$WHITE = "White"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $CYAN
    Write-Host $Text -ForegroundColor $CYAN
    Write-Host ("=" * 60) -ForegroundColor $CYAN
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor $GREEN
}

function Write-Warning {
    param([string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Text)
    Write-Host "[ERROR] $Text" -ForegroundColor $RED
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor $BLUE
}

function Confirm-Action {
    param([string]$Message)
    if ($AutoConfirm) { return $true }
    $response = Read-Host "$Message (y/N)"
    return $response -match '^[Yy]$'
}

# Check for Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator. Some operations may fail."
    if (-not $AutoConfirm) {
        $confirm = Read-Host "Continue anyway? (y/N)"
        if ($confirm -notmatch '^[Yy]$') { exit 1 }
    }
}

Write-Header "PlannedEducation Uninstaller (Windows)"

# Verify installation directory exists
if (-not (Test-Path $InstallDir)) {
    Write-Error "Installation directory not found: $InstallDir"
    Write-Info "Please specify the correct path with -InstallDir parameter"
    exit 1
}

Write-Success "Found PlannedEducation at: $InstallDir"

# Step 1: Stop running processes
Write-Header "Step 1: Stopping Running Processes"

$escapedDir = [Regex]::Escape($InstallDir)
$allProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue

# Never kill ourselves or any ancestor (the shell/agent that launched this uninstaller
# usually has the install dir in its own command line).
$protectedPids = New-Object System.Collections.Generic.HashSet[int]
$cursor = $PID
while ($cursor -and $protectedPids.Add([int]$cursor)) {
    $parent = $allProcs | Where-Object { $_.ProcessId -eq $cursor } | Select-Object -First 1
    $cursor = if ($parent) { $parent.ParentProcessId } else { 0 }
}

# Only stop platform runtimes (backend/frontend/helpers), not arbitrary shells or editors.
$runtimeNames = @('python.exe', 'pythonw.exe', 'uvicorn.exe', 'node.exe', 'npm.cmd', 'cmd.exe')
$matchingCimProcs = $allProcs | Where-Object {
    $runtimeNames -contains $_.Name.ToLower() -and
    -not $protectedPids.Contains([int]$_.ProcessId) -and
    (($_.ExecutablePath -and $_.ExecutablePath -match $escapedDir) -or
     ($_.CommandLine -and $_.CommandLine -match $escapedDir))
}

if ($matchingCimProcs) {
    Write-Info "Stopping processes associated with $InstallDir..."
    foreach ($proc in $matchingCimProcs) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
    Write-Success "Stopped all platform processes"
} else {
    Write-Info "No platform processes running from $InstallDir"
}

# Step 2: Remove Windows services and scheduled tasks
Write-Header "Step 2: Removing Services and Scheduled Tasks"

$taskName = "PlannedEducation-Backend"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Info "Removing scheduled task: $taskName"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Success "Removed scheduled task: $taskName"
} else {
    Write-Info "No scheduled task found: $taskName"
}

# Remove service scripts
foreach ($scriptName in @("start_backend.bat", "start_frontend.bat")) {
    $serviceScript = Join-Path $InstallDir $scriptName
    if (Test-Path $serviceScript) {
        Remove-Item $serviceScript -Force -ErrorAction SilentlyContinue
        Write-Success "Removed launcher script: $scriptName"
    }
}

# Step 3: Ask about external dependencies (one-by-one only, no remove-all)
Write-Header "Step 3: External Dependencies"

$externalDeps = @(
    @{Name="Python"; Check="python --version"; UninstallCmd="winget uninstall Python.Python.3.12"},
    @{Name="Node.js"; Check="node --version"; UninstallCmd="winget uninstall OpenJS.NodeJS.LTS"},
    @{Name="PostgreSQL"; Check="psql --version"; UninstallCmd="winget uninstall PostgreSQL.PostgreSQL"},
    @{Name="Redis"; Check="redis-cli --version"; UninstallCmd="winget uninstall Redis.Redis"},
    @{Name="Docker Desktop"; Check="docker --version"; UninstallCmd="winget uninstall Docker.DockerDesktop"},
    @{Name="Git"; Check="git --version"; UninstallCmd="winget uninstall Git.Git"}
)

Write-Info "The following external dependencies may be used by PlannedEducation or other applications:"
$installedDeps = @()
foreach ($dep in $externalDeps) {
    $cmdName = ($dep.Check -split ' ')[0]
    if (Get-Command $cmdName -ErrorAction SilentlyContinue) {
        Write-Host "  - $($dep.Name) [INSTALLED]" -ForegroundColor $GREEN
        $installedDeps += $dep
    } else {
        Write-Host "  - $($dep.Name) [Not installed]" -ForegroundColor $YELLOW
    }
}
Write-Host ""
Write-Info "Note: There is NO 'remove all' option. If you choose Yes below, you will be asked ONE BY ONE for each installed dependency whether to remove or keep it."

$depsToRemove = @()

if (-not $AutoConfirm -and $installedDeps.Count -gt 0) {
    $reviewOneByOne = Confirm-Action "Do you want to review these external dependencies one by one to choose whether to remove any of them?"
    if ($reviewOneByOne) {
        foreach ($dep in $installedDeps) {
            $removeThis = Confirm-Action "Remove $($dep.Name)? (y=remove, N=keep)"
            if ($removeThis) {
                $depsToRemove += $dep
            } else {
                Write-Info "Keeping $($dep.Name)"
            }
        }
    } else {
        Write-Info "Keeping all external dependencies"
    }
} else {
    Write-Info "Keeping all external dependencies"
}

# Step 4: Confirm removal of platform
Write-Header "Step 4: Confirm Platform Removal"

Write-Warning "This will PERMANENTLY DELETE the following:"
Write-Host "  [DIR] $InstallDir"
Write-Host "  [DB]  All databases (plannededucation.db, test_*.db, etc.)"
Write-Host "  [SEC] All secrets and environment files"
Write-Host "  [LOG] All logs and cache files"
Write-Host ""
Write-Warning "This action CANNOT be undone!"

if (-not (Confirm-Action "Do you want to proceed with removing PlannedEducation from $InstallDir?")) {
    Write-Info "Uninstall cancelled by user"
    exit 0
}

# Step 5: Remove the platform
Write-Header "Step 5: Removing PlannedEducation Platform"

try {
    # Stop any remaining processes executing from inside the installation directory
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($InstallDir, [System.StringComparison]::OrdinalIgnoreCase)
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Remove the directory
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction Stop
    Write-Success "Successfully removed: $InstallDir"
} catch {
    Write-Error "Failed to remove ${InstallDir}: $_"
    Write-Info "You may need to close applications using files in this directory and try again"
    exit 1
}

# Step 6: Remove external dependencies (if requested)
if ($depsToRemove.Count -gt 0) {
    Write-Header "Step 6: Removing External Dependencies"
    
    foreach ($dep in $depsToRemove) {
        Write-Info "Removing $($dep.Name)..."
        try {
            Invoke-Expression $dep.UninstallCmd 2>&1 | Out-Null
            Write-Success "Removed $($dep.Name)"
        } catch {
            Write-Warning "Failed to remove $($dep.Name) automatically"
            Write-Info "Please remove $($dep.Name) manually using: $($dep.UninstallCmd)"
        }
    }
}

# Step 7: Summary
Write-Header "Uninstall Complete"

Write-Success "PlannedEducation has been removed from: $InstallDir"
if ($depsToRemove.Count -gt 0) {
    Write-Success "Removed $($depsToRemove.Count) external dependency(ies)"
} else {
    Write-Info "All external dependencies were kept"
}

Write-Host ""
Write-Host "To reinstall PlannedEducation, run: install.ps1"
Write-Host ""
