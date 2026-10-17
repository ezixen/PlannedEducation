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
#>

param(
    [string]$InstallDir = "d:\Dev\PEserver",
    [switch]$RemoveAllDeps,
    [switch]$AutoConfirm
)

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

# Stop backend API processes
$apiProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$InstallDir*"
}
if ($apiProcesses) {
    Write-Info "Stopping backend API processes..."
    $apiProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Success "Stopped backend API processes"
} else {
    Write-Info "No backend API processes running"
}

# Stop frontend processes
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$InstallDir*"
}
if ($nodeProcesses) {
    Write-Info "Stopping frontend processes..."
    $nodeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Success "Stopped frontend processes"
} else {
    Write-Info "No frontend processes running"
}

# Stop any uvicorn processes inside the installation directory
$uvicornProcesses = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$InstallDir*"
}
if ($uvicornProcesses) {
    Write-Info "Stopping uvicorn processes..."
    $uvicornProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Success "Stopped uvicorn processes"
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
$serviceScript = Join-Path $InstallDir "start_backend.bat"
if (Test-Path $serviceScript) {
    Remove-Item $serviceScript -Force -ErrorAction SilentlyContinue
    Write-Success "Removed service script: start_backend.bat"
}

# Step 3: Ask about external dependencies
Write-Header "Step 3: External Dependencies"

$removeDeps = $RemoveAllDeps
if (-not $removeDeps -and -not $AutoConfirm) {
    $removeAll = Confirm-Action "Do you want to remove all external dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git)?"
    if ($removeAll) {
        $removeDeps = $true
    }
}

$depsToRemove = @()

if ($removeDeps) {
    $removeOneByOne = if ($AutoConfirm) { $false } else { Confirm-Action "Do you want to decide for each dependency one by one (keep/remove)?" }
    
    $externalDeps = @(
        @{Name="Python"; Check="python --version"; UninstallCmd="winget uninstall Python.Python.3.14"},
        @{Name="Node.js"; Check="node --version"; UninstallCmd="winget uninstall OpenJS.NodeJS"},
        @{Name="PostgreSQL"; Check="psql --version"; UninstallCmd="winget uninstall PostgreSQL.PostgreSQL"},
        @{Name="Redis"; Check="redis-cli --version"; UninstallCmd="winget uninstall Redis.Redis"},
        @{Name="Docker Desktop"; Check="docker --version"; UninstallCmd="winget uninstall Docker.DockerDesktop"},
        @{Name="Git"; Check="git --version"; UninstallCmd="winget uninstall Git.Git"}
    )
    
    foreach ($dep in $externalDeps) {
        $isInstalled = $false
        try {
            $cmdName = ($dep.Check -split ' ')[0]
            if (Get-Command $cmdName -ErrorAction SilentlyContinue) {
                $isInstalled = $true
            }
        } catch {}
        
        if (-not $isInstalled) {
            Write-Info "$($dep.Name): Not installed, skipping"
            continue
        }
        
        if ($removeOneByOne) {
            $keep = Confirm-Action "Keep $($dep.Name)? (y=keep, n=remove)"
            if (-not $keep) {
                $depsToRemove += $dep
            } else {
                Write-Info "Keeping $($dep.Name)"
            }
        } else {
            $depsToRemove += $dep
        }
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
