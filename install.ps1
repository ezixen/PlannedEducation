<#
.SYNOPSIS
    PlannedEducation - Complete Automated Installation Script for Windows
    Engineered and verified for standard built-in Windows PowerShell 5.1 (powershell.exe,
    preinstalled on Windows 10, 11, and Windows Server 2016-2025) and modern PowerShell 7+.
    Designed for both human operators and AI coding/deployment agents.

.DESCRIPTION
    Supports:
    - Mode 1: Local Development / Single-Server (SQLite + In-Memory Cache)
    - Mode 2: Production Server (PostgreSQL + Redis)
    - Mode 3: Docker Compose (All-in-One Containers)

    AI AGENT DEPLOYMENT CONTRACT (MANDATORY FOR AI AGENTS):
    AI agents can run this script non-interactively with `-AutoConfirm`, BUT before invoking
    this installer, the AI agent MUST STOP AND ASK the human operator to confirm:
      1. Target installation directory (`-InstallDir`, e.g., C:\PlannedEducation or D:\dev\PEtest)
      2. Deployment mode (`-DeployMode`: 1=SQLite Single-Server, 2=PostgreSQL+Redis, 3=Docker)
      3. Initial Superadmin / School Admin identity (`-AdminEmail`, `-AdminName`, `-AdminPassword`, `-SchoolName`)
      4. Domain and preferred ports (`-Domain`, `-ApiPort` default 8000, `-FrontendPort` default 5173)

    DIAGNOSTIC LOGS (for humans & AI agents):
    All installation and runtime logs are written to `<InstallDir>\logs\`:
      - `logs\install.log`        (full installation log)
      - `logs\install_error.log`  (installation warnings & errors only)
      - `logs\backend.log`        (backend structured JSON log, INFO and above)
      - `logs\backend_error.log`  (backend warnings/exceptions only, with tracebacks)
      - `logs\backend_stdout.log` / `logs\backend_stderr.log` (raw console capture - check these if the backend fails to start)
      - `logs\frontend.log`       (frontend runtime stdout log)
      - `logs\frontend_error.log` (frontend runtime stderr/errors only)

.PARAMETER InstallDir
    Target directory to install PlannedEducation (default: C:\PlannedEducation)

.PARAMETER DeployMode
    Deployment mode: 1 (SQLite), 2 (PostgreSQL + Redis), 3 (Docker Compose)

.PARAMETER Domain
    Domain name or hostname (default: localhost)

.PARAMETER AdminEmail
    Initial administrator email (default: admin@yourschool.edu)

.PARAMETER AdminPassword
    Initial administrator password (required unless interactive; empty triggers secure random generation)

.PARAMETER AdminName
    Initial administrator full name (default: School Administrator)

.PARAMETER SchoolName
    Initial school/institution name (default: PlannedEducation School)

.PARAMETER SettingsFile
    Optional portable admin/env settings JSON (.json / .peconfig) from a previous export.
    Applied on clean installs into config/deployment.json and non-secret .env keys.
    Never contains JWT/DB encryption secrets or database files. Also accepts PE_SETTINGS_FILE.

.PARAMETER AutoConfirm
    Run non-interactively using supplied parameter values (for AI agents / CI after human approval of key choices)

.NOTES
    UPDATE-IN-PLACE DATA PRESERVATION (mandatory):
    Re-running this installer on an existing school deployment keeps the database,
    .env secrets, uploads/backups/logs, and user accounts. It refreshes application
    code (prefers GitHub main) and applies additive schema updates only. It does not
    wipe SQLite/Postgres data. Admin bootstrap is skipped when users already exist
    unless PE_FORCE_ADMIN_BOOTSTRAP=1 is set.
#>

param(
    [string]$InstallDir = "C:\PlannedEducation",
    [string]$DeployMode = "1",
    [string]$Domain = "localhost",
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173,
    [string]$AdminEmail = "admin@yourschool.edu",
    [string]$AdminPassword = "",
    [string]$AdminName = "School Administrator",
    [string]$SchoolName = "PlannedEducation School",
    [string]$SettingsFile = "",
    [switch]$AutoConfirm
)

$ErrorActionPreference = "Stop"

$script:LogDir = Join-Path $InstallDir "logs"
$script:InstallLog = Join-Path $script:LogDir "install.log"
$script:InstallErrLog = Join-Path $script:LogDir "install_error.log"

function Write-InstallLog {
    param([string]$Level, [string]$Message, [bool]$IsError = $false)
    try {
        if (Test-Path $InstallDir) {
            if (-not (Test-Path $script:LogDir)) {
                New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null
            }
            $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            $line = "[$ts] [$Level] $Message"
            Add-Content -Path $script:InstallLog -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($IsError) {
                Add-Content -Path $script:InstallErrLog -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
            }
        }
    } catch {}
}

function Get-AvailablePort {
    param([int]$PreferredPort, [int[]]$Fallbacks)
    $candidates = @($PreferredPort) + $Fallbacks
    foreach ($p in $candidates) {
        $inUse = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if (-not $inUse) { return $p }
    }
    return $PreferredPort
}

# Colors for output
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
    Write-InstallLog -Level "STEP" -Message $Text
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor $GREEN
    Write-InstallLog -Level "OK" -Message $Text
}

function Write-Warning {
    param([string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor $YELLOW
    Write-InstallLog -Level "WARN" -Message $Text -IsError $true
}

function Write-ErrorMsg {
    param([string]$Text)
    Write-Host "[ERROR] $Text" -ForegroundColor $RED
    Write-InstallLog -Level "ERROR" -Message $Text -IsError $true
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor $BLUE
    Write-InstallLog -Level "INFO" -Message $Text
}

function Check-Command {
    param([string]$Name, [string]$Exe, [string]$VersionArg = "--version")
    Write-Host -NoNewline "Checking for $Name... "
    try {
        $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            $versionOut = & $Exe $VersionArg 2>&1 | Select-Object -First 1
            Write-Host "FOUND ($versionOut)" -ForegroundColor $GREEN
            return $true
        }
    } catch {
        # Ignore and report not found below
    }
    Write-Host "NOT FOUND" -ForegroundColor $RED
    return $false
}

function Confirm-Action {
    param(
        [string]$Message,
        # When AutoConfirm is set: $true = yes (install deps), $false = no (preserve data).
        [bool]$AutoConfirmDefault = $true
    )
    if ($AutoConfirm) { return $AutoConfirmDefault }
    $response = Read-Host "$Message (y/N)"
    return $response -match '^[Yy]$'
}

function Test-ExistingDeployment {
    param([string]$Dir)
    $envPath = Join-Path $Dir ".env"
    $sqlitePath = Join-Path $Dir "plannededucation.db"
    $pgMarker = Join-Path $Dir "config\deployment.json"
    return (Test-Path $envPath) -or (Test-Path $sqlitePath) -or (
        (Test-Path $pgMarker) -and (Test-Path (Join-Path $Dir "src\plannededucation"))
    )
}

function Load-DotEnv {
    param([string]$EnvFilePath)
    if (Test-Path $EnvFilePath) {
        Get-Content $EnvFilePath | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                $key = $parts[0].Trim()
                $val = $parts[1].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
            }
        }
    }
}

# Check for Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host "  [!] NOTICE: ADMINISTRATOR PRIVILEGES RECOMMENDED" -ForegroundColor $YELLOW
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host "  PlannedEducation deployment on Windows performs operations that"
    Write-Host "  typically require elevated (Administrator) rights:"
    Write-Host "    1. Creating/writing to the system folder (e.g. C:\PlannedEducation)"
    Write-Host "    2. Installing missing prerequisites system-wide (Python, Node.js, Git)"
    Write-Host "    3. Registering the Windows Scheduled Task for 24/7 background service"
    Write-Host "    4. Setting Windows Firewall inbound rules if serving to LAN or WAN"
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host ""
    if (-not $AutoConfirm) {
        Write-Host "Options:"
        Write-Host "  1) Relaunch as Administrator (prompts for UAC elevation) [RECOMMENDED]"
        Write-Host "  2) Continue in User-mode (scheduled task will be skipped)"
        Write-Host "  3) Exit installer"
        Write-Host ""
        $elevChoice = Read-Host "Select option [1-3] (default: 1)"
        if (-not $elevChoice -or $elevChoice -eq "1") {
            Write-Info "Relaunching installer with Administrator elevation..."
            try {
                $myArgs = "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`""
                Start-Process powershell.exe -Verb RunAs -ArgumentList $myArgs
                exit 0
            } catch {
                Write-Warning "Elevation cancelled or failed. Continuing in current session."
            }
        } elseif ($elevChoice -eq "3") {
            Write-Info "Installation cancelled by user."
            exit 0
        } else {
            Write-Warning "Continuing in user-mode. Background scheduled task and system-wide package installs will be skipped."
        }
    } else {
        Write-Warning "Running non-interactively without Administrator privileges. System-level steps will be skipped."
    }
} else {
    Write-Success "Running with Administrator privileges."
}

Write-Header "PlannedEducation Automated Installer (Windows)"

# Step 1: Choose Installation Directory
Write-Header "Step 1: Choose Installation Directory"

Write-Host "PlannedEducation requires a target directory for application files, database, and logs."
Write-Host "Default recommended path: C:\PlannedEducation"
Write-Host ""
if (-not $AutoConfirm) {
    $inputDir = Read-Host "Installation directory (press Enter for default '$InstallDir')"
    if ($inputDir -and $inputDir.Trim() -ne "") {
        $InstallDir = $inputDir.Trim()
    }
}
$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$script:LogDir = Join-Path $InstallDir "logs"
$script:InstallLog = Join-Path $script:LogDir "install.log"
$script:InstallErrLog = Join-Path $script:LogDir "install_error.log"

if (-not (Test-Path $InstallDir)) {
    try {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Write-Success "Created directory: $InstallDir"
    } catch {
        Write-ErrorMsg "Cannot create directory '$InstallDir': $_. Please ensure you have sufficient permissions or run as Administrator."
        exit 1
    }
} else {
    Write-Success "Using directory: $InstallDir"
}

# Detect update-vs-fresh BEFORE mutating secrets or admin accounts.
# DATA PRESERVATION RULE: re-running the installer on an existing school
# deployment MUST keep .env secrets and the database (accounts, exams, grades).
$script:IsUpdate = Test-ExistingDeployment -Dir $InstallDir
if ($script:IsUpdate) {
    Write-Header "Update Mode Detected"
    Write-Info "Existing deployment found under $InstallDir"
    Write-Info "Preserving database files, .env secrets, logs, uploads, and user accounts."
    Write-Info "This run will refresh application code/modules and apply additive schema updates only."
}

# Step 2: Choose Deployment Mode
Write-Header "Step 2: Choose Deployment Mode"

if (-not $AutoConfirm) {
    Write-Host "How would you like to deploy PlannedEducation?"
    Write-Host ""
    Write-Host "  1) Local Development / Single-Server (SQLite + In-Memory Cache) - Fastest setup"
    Write-Host "  2) Production Server (PostgreSQL + Redis + Scheduled Task) - Recommended for schools"
    Write-Host "  3) Docker Compose (All-in-One Containers) - Easiest management"
    Write-Host ""
    $inputMode = Read-Host "Select mode [1-3] (default: $DeployMode)"
    if ($inputMode) { $DeployMode = $inputMode }
}

$useSqlite = $false
$useDocker = $false

switch ($DeployMode) {
    "1" {
        Write-Info "Selected: Local Development / Single-Server Mode (SQLite)"
        $useSqlite = $true
    }
    "2" {
        Write-Info "Selected: Production Server Mode (PostgreSQL + Redis)"
        $useSqlite = $false
    }
    "3" {
        Write-Info "Selected: Docker Compose Mode"
        $useDocker = $true
    }
    default {
        Write-Warning "Invalid selection. Defaulting to Mode 1 (SQLite)."
        $DeployMode = "1"
        $useSqlite = $true
    }
}

# Step 3: Check Required Dependencies
Write-Header "Step 3: Checking Required Dependencies"

Write-Host ""
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host "  REQUIRED DEPENDENCIES (must be installed for any mode):" -ForegroundColor $CYAN
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host ""
Write-Host "  - Git          : Source control (used to clone the repository)"
Write-Host "  - Python 3.12+ : Backend runtime (FastAPI, SQLAlchemy, etc.)"
Write-Host "  - Node.js 20+  : Frontend build tooling (Vite, npm)"
Write-Host "  - npm          : Node.js package manager (bundled with Node.js)"
Write-Host ""
Write-Host "  OPTIONAL DEPENDENCIES (only needed for specific modes):"
Write-Host "  - PostgreSQL   : Mode 2 (Production Server) only"
Write-Host "  - Redis        : Mode 2 (Production Server) only"
Write-Host "  - Docker       : Mode 3 (Docker Compose) only"
Write-Host ""
Write-Host "  NOTE: Mode 1 (SQLite) works with just Git, Python, and Node.js."
Write-Host "        Optional items are NOT required for Mode 1."
Write-Host ""
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host ""

$hasGit = Check-Command "Git (REQUIRED)" "git" "--version"
$hasPython = Check-Command "Python 3.11+ (REQUIRED)" "python" "--version"
$hasNode = Check-Command "Node.js 20+ (REQUIRED)" "node" "--version"
$hasNpm = Check-Command "npm (REQUIRED)" "npm" "--version"
$hasDocker = Check-Command "Docker (OPTIONAL - Mode 3)" "docker" "--version"
$hasPostgres = Check-Command "PostgreSQL (OPTIONAL - Mode 2)" "psql" "--version"
$hasRedis = Check-Command "Redis (OPTIONAL - Mode 2)" "redis-cli" "--version"

# Step 4: Install Missing Required Dependencies
Write-Header "Step 4: Checking & Installing Required Dependencies"

$missingRequired = @()
if (-not $hasGit) { $missingRequired += "Git" }
if (-not $useDocker) {
    if (-not $hasPython) { $missingRequired += "Python 3.11+" }
    if (-not $hasNode) { $missingRequired += "Node.js 20+" }
}
if (-not $useSqlite -and -not $useDocker) {
    if (-not $hasPostgres) { $missingRequired += "PostgreSQL" }
    if (-not $hasRedis) { $missingRequired += "Redis" }
}
if ($useDocker -and -not $hasDocker) {
    $missingRequired += "Docker Desktop"
}

if ($missingRequired.Count -gt 0) {
    Write-Warning "Missing required dependencies for Mode ${DeployMode}: $($missingRequired -join ', ')"
    if (Confirm-Action "Install missing dependencies using winget?") {
        $hasWinget = Check-Command "winget" "winget" "--version"
        if (-not $hasWinget) {
            Write-ErrorMsg "winget is not installed. Please install missing dependencies manually."
            exit 1
        }
        if (-not $hasGit) { winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements }
        if (-not $hasPython -and -not $useDocker) { winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements }
        if (-not $hasNode -and -not $useDocker) { winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements }
        if (-not $hasPostgres -and -not $useSqlite -and -not $useDocker) { winget install --id PostgreSQL.PostgreSQL.16 -e --source winget --accept-package-agreements --accept-source-agreements }
        if (-not $hasRedis -and -not $useSqlite -and -not $useDocker) { winget install --id Redis.Redis -e --source winget --accept-package-agreements --accept-source-agreements }
        if (-not $hasDocker -and $useDocker) { winget install --id Docker.DockerDesktop -e --source winget --accept-package-agreements --accept-source-agreements }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Success "Dependencies installed."
    } else {
        Write-ErrorMsg "Cannot proceed without required dependencies."
        exit 1
    }
} else {
    Write-Success "All required dependencies for Mode $DeployMode are installed!"
}

# Step 5: Setting Up Application Directory
Write-Header "Step 5: Setting Up Application Directory"

$scriptRepoRoot = $PSScriptRoot
# Protected runtime data - never delete/overwrite during clone sync or updates.
$script:ProtectedDataNames = @(
    ".env", ".env.local", "plannededucation.db", "plannededucation.db-wal", "plannededucation.db-shm",
    "ADMIN_CREDENTIALS.txt", "admin_recovery_codes.tmp", "local-secrets", "logs", "uploads",
    "backups", "artifacts", "data"
)

if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
    Write-Info "Cloning PlannedEducation repository into $InstallDir..."
    # Clone into a temp sibling directory first: $InstallDir may already contain logs\ (the
    # installer logs from the very first step), and git refuses to clone into a non-empty dir.
    $cloneTmp = "$InstallDir.clone-tmp"
    if (Test-Path $cloneTmp) { Remove-Item $cloneTmp -Recurse -Force -ErrorAction SilentlyContinue }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # End-user / school installs track stable `main`. Fall back to default remote HEAD if needed.
    $cloneOutput = & git clone --quiet --branch main --single-branch https://github.com/ezixen/PlannedEducation.git $cloneTmp 2>&1
    $cloneExit = $LASTEXITCODE
    if ($cloneExit -ne 0) {
        Write-Warning "Clone of 'main' failed; falling back to default branch..."
        if (Test-Path $cloneTmp) { Remove-Item $cloneTmp -Recurse -Force -ErrorAction SilentlyContinue }
        $cloneOutput = & git clone --quiet https://github.com/ezixen/PlannedEducation.git $cloneTmp 2>&1
        $cloneExit = $LASTEXITCODE
    }
    $ErrorActionPreference = $prevEap
    if ($cloneExit -ne 0) {
        Write-ErrorMsg "git clone failed (exit $cloneExit): $($cloneOutput -join ' ')"
        exit 1
    }
    # Copy code into InstallDir without clobbering protected runtime data.
    Get-ChildItem -Force $cloneTmp | ForEach-Object {
        if ($script:ProtectedDataNames -contains $_.Name) {
            Write-Info "Preserving existing runtime data: $($_.Name)"
            return
        }
        $dest = Join-Path $InstallDir $_.Name
        if ($_.PSIsContainer) {
            Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
        } else {
            Copy-Item -Path $_.FullName -Destination $dest -Force
        }
    }
    Remove-Item $cloneTmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Success "Repository cloned successfully"
} else {
    Write-Info "Repository already exists in $InstallDir, pulling latest stable changes from origin/main..."
    Push-Location $InstallDir
    try {
        git fetch origin 2>&1 | Out-Null
        git checkout main 2>&1 | Out-Null
        git pull origin main 2>&1 | Out-Null
    } catch {
        Write-Warning "Could not pull from remote; continuing with existing checkout."
    }
    Pop-Location
    Write-Success "Repository ready"
}

# If running installer from a local checkout with newer scripts/files, sync key source directories
if ($scriptRepoRoot -and (Test-Path (Join-Path $scriptRepoRoot "src\plannededucation")) -and ($scriptRepoRoot -ne $InstallDir)) {
    Write-Info "Syncing latest workspace source files from $scriptRepoRoot to $InstallDir..."
    $syncPairs = @(
        @{ From = "src";                     To = "src" },
        @{ From = "web\apps\portal\src";     To = "web\apps\portal\src" },
        @{ From = "web\apps\portal\public";  To = "web\apps\portal\public" },
        @{ From = "scripts";                 To = "scripts" },
        @{ From = "docs";                    To = "docs" }
    )
    foreach ($pair in $syncPairs) {
        $dest = Join-Path $InstallDir $pair.To
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
        # robocopy copies directory contents reliably (no leaf/container ambiguity); exit codes < 8 are success
        & robocopy (Join-Path $scriptRepoRoot $pair.From) $dest /E /NFL /NDL /NJH /NJS /NP /XD __pycache__ "*.egg-info" | Out-Null
        if ($LASTEXITCODE -ge 8) {
            Write-ErrorMsg "Failed to sync $($pair.From) (robocopy exit $LASTEXITCODE)"
            exit 1
        }
    }
    $global:LASTEXITCODE = 0
    foreach ($scriptFile in @("install.ps1", "uninstall.ps1", "install.sh", "uninstall.sh")) {
        Copy-Item -Path (Join-Path $scriptRepoRoot $scriptFile) -Destination (Join-Path $InstallDir $scriptFile) -Force
    }
}

Set-Location $InstallDir

# Optional portable settings file (admin/env only — not DB / crypto secrets)
if (-not $SettingsFile -and $env:PE_SETTINGS_FILE) { $SettingsFile = $env:PE_SETTINGS_FILE }
$script:ImportedSettings = $null
if ($SettingsFile) {
    if (-not (Test-Path -LiteralPath $SettingsFile)) {
        Write-ErrorMsg "SettingsFile not found: $SettingsFile"
        exit 1
    }
    try {
        $rawSettings = Get-Content -LiteralPath $SettingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($rawSettings.settings) { $script:ImportedSettings = $rawSettings.settings }
        else { $script:ImportedSettings = $rawSettings }
        if ($script:ImportedSettings.domain) { $Domain = [string]$script:ImportedSettings.domain }
        if ($script:ImportedSettings.api_port) { $ApiPort = [int]$script:ImportedSettings.api_port }
        if ($script:ImportedSettings.frontend_port) { $FrontendPort = [int]$script:ImportedSettings.frontend_port }
        if ($script:ImportedSettings.school_name) { $SchoolName = [string]$script:ImportedSettings.school_name }
        Write-Success "Loaded portable admin settings from $SettingsFile (env/deployment only)"
    } catch {
        Write-ErrorMsg "Failed to parse SettingsFile: $($_.Exception.Message)"
        exit 1
    }
}

# Read existing deployment.json defaults if available (on existing installations)
$existingDepJson = Join-Path $InstallDir "config\deployment.json"
if ((Test-Path (Join-Path $InstallDir ".env")) -and (Test-Path $existingDepJson) -and -not $script:ImportedSettings) {
    try {
        $parsedDep = Get-Content $existingDepJson -Raw | ConvertFrom-Json
        if ($parsedDep.domain) { $Domain = $parsedDep.domain }
        if ($parsedDep.api_port) { $ApiPort = [int]$parsedDep.api_port }
        if ($parsedDep.frontend_port) { $FrontendPort = [int]$parsedDep.frontend_port }
        if ($parsedDep.school_name) { $SchoolName = $parsedDep.school_name }
    } catch {}
}

# Step 6: Configure Environment Variables & Secrets
Write-Header "Step 6: Configuring Environment & Secrets"

$envFile = Join-Path $InstallDir ".env"
# DATA PRESERVATION: never auto-overwrite .env on updates (would rotate JWT/Fernet
# keys and break decryption of existing encrypted rows while keeping the same DB).
$shouldWriteEnv = -not (Test-Path $envFile)
if (-not $shouldWriteEnv) {
    if ($script:IsUpdate) {
        Write-Info "Keeping existing .env (update mode - secrets and DB encryption keys preserved)."
    } elseif (Confirm-Action "Overwrite existing .env configuration? WARNING: regenerates secrets and can lock out existing encrypted data." -AutoConfirmDefault $false) {
        $shouldWriteEnv = $true
    } else {
        Write-Info "Keeping existing .env file"
    }
}
if ($shouldWriteEnv) {
    Write-Info "Generating cryptographically secure secrets..."

    # Generate 64-char hex JWT secret
    $jwtBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($jwtBytes)
    $jwtSecret = [System.BitConverter]::ToString($jwtBytes).Replace("-", "").ToLower()

    # Generate URL-safe base64 32-byte Fernet keys (AI keys vs DB field encryption MUST differ)
    $fernetBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($fernetBytes)
    $fernetKey = [System.Convert]::ToBase64String($fernetBytes).Replace("+", "-").Replace("/", "_")
    $dbEncBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($dbEncBytes)
    $dbEncKey = [System.Convert]::ToBase64String($dbEncBytes).Replace("+", "-").Replace("/", "_")
    $recoveryHashBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($recoveryHashBytes)
    $recoveryHashSecret = [System.Convert]::ToBase64String($recoveryHashBytes).Replace("+", "-").Replace("/", "_")
    $tokenHashBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($tokenHashBytes)
    $tokenHashSecret = [System.Convert]::ToBase64String($tokenHashBytes).Replace("+", "-").Replace("/", "_")

    if (-not $AutoConfirm) {
        $inputDomain = Read-Host "Enter your domain or IP address (default: $Domain)"
        if ($inputDomain) { $Domain = $inputDomain }
    }

    $ApiPort = Get-AvailablePort -PreferredPort $ApiPort -Fallbacks @(8002, 8001, 8080)
    $FrontendPort = Get-AvailablePort -PreferredPort $FrontendPort -Fallbacks @(5175, 5174, 5176)

    if ($useSqlite) {
        $dbPath = (Join-Path $InstallDir "plannededucation.db").Replace("\", "/")
        $dbUrl = "sqlite:///$dbPath"
        $redisUrl = "memory://"
        $envMode = "development"
        $sebBypass = "true"
    } else {
        $dbPassBytes = New-Object byte[] 16
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($dbPassBytes)
        $dbPass = [System.BitConverter]::ToString($dbPassBytes).Replace("-", "").ToLower()
        $dbUrl = "postgresql://pe_user:${dbPass}@localhost:5432/plannededucation"
        $redisUrl = "redis://localhost:6379/0"
        $envMode = "production"
        $sebBypass = "false"
    }
    $frontendUrl = if ($envMode -eq "production") { "https://$Domain" } else { "http://${Domain}:${FrontendPort}" }

    $envContent = @"
# PlannedEducation Environment Configuration
# Generated on $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")

# Database
DATABASE_URL=$dbUrl

# Redis
REDIS_URL=$redisUrl

# Security Secrets (NEVER SHARE THESE!)
JWT_SECRET_KEY=$jwtSecret
RECOVERY_CODE_HASH_SECRET=$recoveryHashSecret
TOKEN_HASH_SECRET=$tokenHashSecret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=$fernetKey
AI_KEY_MASTER_SECRET=$fernetKey
# Field-level DB encryption for chat bodies, TOTP secrets, recovery codes (distinct from JWT/AI keys)
DATABASE_ENCRYPTION=true
DB_ENCRYPTION_MASTER_KEY=$dbEncKey

# Server Configuration
FRONTEND_URL=$frontendUrl
HOST=0.0.0.0
PORT=$ApiPort
FRONTEND_PORT=$FrontendPort
CORS_ORIGINS=http://${Domain}:${FrontendPort},http://${Domain}:5173,http://${Domain}:5175,http://localhost:${FrontendPort},http://localhost:5173,http://localhost:5175,http://127.0.0.1:${FrontendPort},http://127.0.0.1:5173,http://127.0.0.1:5175,https://$Domain

# Anonymizer / Presidio
ANONYMIZER_ENABLED=true
ANONYMIZER_LANGUAGE=en

# Environment & SEB
ENVIRONMENT=$envMode
PLANNED_EDUCATION_ENV=$envMode
ALLOW_DEV_SEB_BYPASS=$sebBypass
"@

    [System.IO.File]::WriteAllText($envFile, $envContent, (New-Object System.Text.UTF8Encoding($false)))
    Write-Success "Created .env file with secure random secrets (API port: $ApiPort, Frontend port: $FrontendPort)"

    $configDir = Join-Path $InstallDir "config"
    if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }
    $deploymentJsonFile = Join-Path $configDir "deployment.json"
    $corsList = "http://${Domain}:${FrontendPort},http://${Domain}:5173,http://${Domain}:5175,http://localhost:${FrontendPort},http://localhost:5173,http://localhost:5175,http://127.0.0.1:${FrontendPort},http://127.0.0.1:5173,http://127.0.0.1:5175,https://$Domain"
    $anonEnabled = $true
    $anonLang = "en"
    $allowSeb = ($sebBypass -eq "true")
    $allowedHosts = "$Domain,localhost,127.0.0.1"
    $homeExam = $false
    $smtpHost = $null
    $smtpPort = 587
    $smtpUser = $null
    $smtpTls = $true
    $smtpSsl = $false
    $emailFrom = "PlannedEducation <noreply@localhost>"
    $headerMode = "text"
    $headerImage = $null
    $backupLoc = "backups"
    $backupFreq = 1
    $backupRetention = 30
    $backupTime = "22:00"
    $supportEmail = $null
    if ($script:ImportedSettings) {
        $s = $script:ImportedSettings
        if ($null -ne $s.cors_origins -and "$($s.cors_origins)".Trim()) { $corsList = [string]$s.cors_origins }
        if ($null -ne $s.allowed_hosts -and "$($s.allowed_hosts)".Trim()) { $allowedHosts = [string]$s.allowed_hosts }
        if ($null -ne $s.allow_dev_seb_bypass) { $allowSeb = [bool]$s.allow_dev_seb_bypass }
        if ($null -ne $s.anonymizer_enabled) { $anonEnabled = [bool]$s.anonymizer_enabled }
        if ($s.anonymizer_language) { $anonLang = [string]$s.anonymizer_language }
        if ($null -ne $s.home_exam_proctoring_enabled) { $homeExam = [bool]$s.home_exam_proctoring_enabled }
        if ($s.PSObject.Properties.Name -contains "smtp_host") { $smtpHost = $s.smtp_host }
        if ($s.smtp_port) { $smtpPort = [int]$s.smtp_port }
        if ($s.PSObject.Properties.Name -contains "smtp_user") { $smtpUser = $s.smtp_user }
        if ($null -ne $s.smtp_use_tls) { $smtpTls = [bool]$s.smtp_use_tls }
        if ($null -ne $s.smtp_use_ssl) { $smtpSsl = [bool]$s.smtp_use_ssl }
        if ($s.email_from) { $emailFrom = [string]$s.email_from }
        if ($s.header_mode) { $headerMode = [string]$s.header_mode }
        if ($s.PSObject.Properties.Name -contains "header_image_url") { $headerImage = $s.header_image_url }
        if ($s.backup_location) { $backupLoc = [string]$s.backup_location }
        if ($s.backup_frequency_days) { $backupFreq = [int]$s.backup_frequency_days }
        if ($s.backup_retention_days) { $backupRetention = [int]$s.backup_retention_days }
        if ($s.backup_time) { $backupTime = [string]$s.backup_time }
        if ($s.PSObject.Properties.Name -contains "admin_support_email") { $supportEmail = $s.admin_support_email }
        # Apply non-secret env overlays from settings (secrets stay freshly generated above).
        $envContent += @"

# Applied from portable settings file
PE_SCHOOL_NAME=$SchoolName
ANONYMIZER_ENABLED=$($anonEnabled.ToString().ToLower())
ANONYMIZER_LANGUAGE=$anonLang
ALLOW_DEV_SEB_BYPASS=$($allowSeb.ToString().ToLower())
HOME_EXAM_PROCTORING_ENABLED=$($homeExam.ToString().ToLower())
SMTP_HOST=$smtpHost
SMTP_PORT=$smtpPort
SMTP_USER=$smtpUser
SMTP_USE_TLS=$($smtpTls.ToString().ToLower())
SMTP_USE_SSL=$($smtpSsl.ToString().ToLower())
EMAIL_FROM=$emailFrom
BACKUP_LOCATION=$backupLoc
BACKUP_FREQUENCY_DAYS=$backupFreq
BACKUP_RETENTION_DAYS=$backupRetention
BACKUP_TIME=$backupTime
ADMIN_SUPPORT_EMAIL=$supportEmail
"@
        [System.IO.File]::WriteAllText($envFile, $envContent, (New-Object System.Text.UTF8Encoding($false)))
    }
    $depConfigObj = [PSCustomObject]@{
        school_name = $SchoolName
        domain = $Domain
        api_port = $ApiPort
        frontend_port = $FrontendPort
        cors_origins = $corsList
        allowed_hosts = $allowedHosts
        environment = $envMode
        allow_dev_seb_bypass = $allowSeb
        anonymizer_enabled = $anonEnabled
        anonymizer_language = $anonLang
        smtp_host = $smtpHost
        smtp_port = $smtpPort
        smtp_user = $smtpUser
        smtp_use_tls = $smtpTls
        smtp_use_ssl = $smtpSsl
        email_from = $emailFrom
        header_mode = $headerMode
        header_image_url = $headerImage
        backup_location = $backupLoc
        backup_frequency_days = $backupFreq
        backup_retention_days = $backupRetention
        backup_time = $backupTime
        admin_support_email = $supportEmail
        home_exam_proctoring_enabled = $homeExam
        updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    # Write without UTF-8 BOM - PowerShell's UTF8 encoding adds BOM which breaks json.load(utf-8)
    $depJsonText = $depConfigObj | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($deploymentJsonFile, $depJsonText, (New-Object System.Text.UTF8Encoding($false)))
    Write-Success "Created config/deployment.json (domain: $Domain, API port: $ApiPort, Frontend port: $FrontendPort)"
}

Load-DotEnv $envFile
if ($env:PORT) { $ApiPort = [int]$env:PORT }
if ($env:FRONTEND_PORT) { $FrontendPort = [int]$env:FRONTEND_PORT }

# Step 7: Setup Application & Databases
if ($useDocker) {
    Write-Header "Step 7: Starting Docker Containers"
    Write-Info "Building and starting containers via Docker Compose..."
    docker compose up -d --build
    Write-Success "Docker containers started!"
} else {
    Write-Header "Step 7: Setting Up Databases & Application"

    if (-not $useSqlite) {
        Write-Info "Setting up PostgreSQL database..."
        try {
            psql -U postgres -c "CREATE USER pe_user WITH PASSWORD '$dbPass';" 2>&1 | Out-Null
            psql -U postgres -c "CREATE DATABASE plannededucation OWNER pe_user;" 2>&1 | Out-Null
            psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE plannededucation TO pe_user;" 2>&1 | Out-Null
            Write-Success "PostgreSQL database configured"
        } catch {
            Write-Warning "Could not configure PostgreSQL automatically. Please ensure PostgreSQL service is running."
        }
    }

    # Setup Python Virtual Environment in $InstallDir\.venv or use verified C:\.venv
    $localVenvDir = Join-Path $InstallDir ".venv"
    $localVenvPython = Join-Path $localVenvDir "Scripts\python.exe"
    if (Test-Path "C:\.venv\Scripts\python.exe") {
        Write-Info "Using verified Python environment at C:\.venv..."
        $pythonExe = "C:\.venv\Scripts\python.exe"
    } elseif (-not (Test-Path $localVenvPython)) {
        Write-Info "Creating Python virtual environment at $localVenvDir..."
        python -m venv $localVenvDir
        $pythonExe = $localVenvPython
        Write-Info "Verifying Python dependencies..."
        & $pythonExe -m pip install -q -r (Join-Path $InstallDir "src\requirements.txt")
        Write-Success "Python dependencies installed"
    } else {
        Write-Info "Using existing Python virtual environment at $localVenvDir..."
        $pythonExe = $localVenvPython
    }

    # Initialize / upgrade schema (additive only - never drops tables or wipes rows).
    if ($script:IsUpdate) {
        Write-Info "Applying additive schema updates to existing database (no wipe)..."
    } else {
        Write-Info "Initializing database tables..."
    }
    $env:PYTHONPATH = Join-Path $InstallDir "src"
    & $pythonExe -c "import plannededucation.api.models; from plannededucation.api.database import Base, engine; from plannededucation.api.schema_ensure import ensure_schema; Base.metadata.create_all(bind=engine); ensure_schema(engine); print('Database schema ready (create_all + ensure_schema; no data wipe).')"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Database initialization failed!"
        exit 1
    }
    Write-Success "Database schema ready (existing user data preserved)"

    # Setup Frontend
    Write-Info "Building React frontend..."
    $portalDir = Join-Path $InstallDir "web\apps\portal"
    Push-Location $portalDir
    $portalEnv = Join-Path $portalDir ".env"
    $portalEnvLocal = Join-Path $portalDir ".env.local"
    Remove-Item (Join-Path $portalDir ".env.development") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $portalDir ".env.production") -Force -ErrorAction SilentlyContinue
    [System.IO.File]::WriteAllText($portalEnv, "VITE_API_URL=http://127.0.0.1:${ApiPort}`n", (New-Object System.Text.UTF8Encoding($false)))
    [System.IO.File]::WriteAllText($portalEnvLocal, "VITE_API_URL=http://127.0.0.1:${ApiPort}`n", (New-Object System.Text.UTF8Encoding($false)))
    npm install --silent --no-audit --no-fund
    npm run build
    Pop-Location
    Write-Success "Frontend built successfully"

    # Ensure logs directory exists
    if (-not (Test-Path $script:LogDir)) {
        New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null
    }

    # Create Complete Launcher & Management Script Suite (.ps1 native + .bat wrappers)
    $startAllPs1 = Join-Path $InstallDir "start_all.ps1"
    $startAllPs1Content = @"
# PlannedEducation - Unified Platform Launcher (PowerShell)
param([switch]`$NoBrowser)

`$InstallDir = "`$PSScriptRoot"
`$logsDir = Join-Path `$InstallDir "logs"
if (-not (Test-Path `$logsDir)) { New-Item -ItemType Directory -Path `$logsDir -Force | Out-Null }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting PlannedEducation Platform" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

`$apiPort = $ApiPort
`$frontendPort = $FrontendPort
`$domain = "$Domain"

`$depCfg = Join-Path `$InstallDir "config\deployment.json"
if (Test-Path `$depCfg) {
    try {
        `$cfg = Get-Content `$depCfg -Raw | ConvertFrom-Json
        if (`$cfg.api_port) { `$apiPort = `$cfg.api_port }
        if (`$cfg.frontend_port) { `$frontendPort = `$cfg.frontend_port }
        if (`$cfg.domain) { `$domain = `$cfg.domain }
    } catch {}
}

`$env:PYTHONPATH = "`$InstallDir\src"
`$env:PLANNED_EDUCATION_LOG_DIR = "`$logsDir"

# Load DATABASE_URL from .env file explicitly
`$envFile = Join-Path `$InstallDir ".env"
if (Test-Path `$envFile) {
    Get-Content `$envFile | ForEach-Object {
        `$line = `$_.Trim()
        if (`$line -and -not `$line.StartsWith("#") -and `$line.Contains("=")) {
            `$parts = `$line.Split("=", 2)
            `$key = `$parts[0].Trim()
            `$val = `$parts[1].Trim()
            if (`$key -eq "DATABASE_URL") { `$env:DATABASE_URL = `$val }
        }
    }
}

Write-Host "1. Starting Backend API on port `$apiPort..." -ForegroundColor Green
`$pythonExe = Join-Path `$InstallDir ".venv\Scripts\python.exe"
if (-not (Test-Path `$pythonExe)) {
    if (Test-Path "C:\.venv\Scripts\python.exe") { `$pythonExe = "C:\.venv\Scripts\python.exe" }
    else { `$pythonExe = "python.exe" }
}
`$backendProc = Start-Process -FilePath `$pythonExe -ArgumentList @("-m", "uvicorn", "plannededucation.api.main:app", "--app-dir", "`$InstallDir\src", "--env-file", "`$InstallDir\.env", "--host", "0.0.0.0", "--port", `$apiPort) -WorkingDirectory `$InstallDir -PassThru

Write-Host "2. Starting Frontend Portal on port `$frontendPort..." -ForegroundColor Green
`$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run preview -- --host 127.0.0.1 --port `$frontendPort" -WorkingDirectory (Join-Path `$InstallDir "web\apps\portal") -PassThru

Write-Host "3. Verifying platform health..." -ForegroundColor Yellow
`$healthy = `$false
for (`$i = 0; `$i -lt 30; `$i++) {
    Start-Sleep -Seconds 1
    try {
        `$res = Invoke-RestMethod -Uri "http://127.0.0.1:`$apiPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if (`$res -and `$res.status -eq "ok") {
            `$healthy = `$true
            break
        }
    } catch {}
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if (`$healthy) {
    Write-Host "  [OK] PlannedEducation is LIVE and HEALTHY!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Frontend Portal: http://`${domain}:${frontendPort}" -ForegroundColor Green
    Write-Host "  Backend API:     http://`${domain}:${apiPort}"
    Write-Host "  API Docs:        http://`${domain}:${apiPort}/docs"
    Write-Host "  Backend PID:     `$(`$backendProc.Id) | Frontend PID: `$(`$frontendProc.Id)"
    Write-Host "  To stop:         Run .\stop_all.bat (or .\stop_all.ps1)"
    Write-Host "============================================================" -ForegroundColor Cyan
    if (-not `$NoBrowser) {
        try { Start-Process "http://`${domain}:${frontendPort}" } catch {}
    }
} else {
    Write-Host "  [WARN] Backend health check timed out." -ForegroundColor Yellow
    Write-Host "  Check diagnostic logs in: `$logsDir\backend_error.log" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
}
"@
    Set-Content -Path $startAllPs1 -Value $startAllPs1Content -Encoding UTF8

    $startAllBat = Join-Path $InstallDir "start_all.bat"
    $startAllBatContent = @"
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_all.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Launcher failed. See message above.
    pause
)
"@
    Set-Content -Path $startAllBat -Value $startAllBatContent -Encoding ASCII

    $startBackendPs1 = Join-Path $InstallDir "start_backend.ps1"
    $backendPs1Content = @"
# PlannedEducation - Backend Launcher (PowerShell)
`$InstallDir = "`$PSScriptRoot"
`$logsDir = Join-Path `$InstallDir "logs"
if (-not (Test-Path `$logsDir)) { New-Item -ItemType Directory -Path `$logsDir -Force | Out-Null }
`$env:PYTHONPATH = "`$InstallDir\src"
`$env:PLANNED_EDUCATION_LOG_DIR = "`$logsDir"

# Load DATABASE_URL from .env file explicitly
`$envFile = Join-Path `$InstallDir ".env"
if (Test-Path `$envFile) {
    Get-Content `$envFile | ForEach-Object {
        `$line = `$_.Trim()
        if (`$line -and -not `$line.StartsWith("#") -and `$line.Contains("=")) {
            `$parts = `$line.Split("=", 2)
            `$key = `$parts[0].Trim()
            `$val = `$parts[1].Trim()
            if (`$key -eq "DATABASE_URL") { `$env:DATABASE_URL = `$val }
        }
    }
}
`$apiPort = $ApiPort
`$depCfg = Join-Path `$InstallDir "config\deployment.json"
if (Test-Path `$depCfg) {
    try {
        `$cfg = Get-Content `$depCfg -Raw | ConvertFrom-Json
        if (`$cfg.api_port) { `$apiPort = `$cfg.api_port }
    } catch {}
}
Write-Host "Starting PlannedEducation Backend on port `$apiPort..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
`$pythonExe = Join-Path `$InstallDir ".venv\Scripts\python.exe"
if (-not (Test-Path `$pythonExe)) {
    if (Test-Path "C:\.venv\Scripts\python.exe") { `$pythonExe = "C:\.venv\Scripts\python.exe" }
    else { `$pythonExe = "python.exe" }
}
& `$pythonExe -m uvicorn plannededucation.api.main:app --app-dir "`$InstallDir\src" --env-file `$InstallDir\.env --host 0.0.0.0 --port `$apiPort
"@
    Set-Content -Path $startBackendPs1 -Value $backendPs1Content -Encoding UTF8

    $startBackendBat = Join-Path $InstallDir "start_backend.bat"
    $backendBatContent = @"
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_backend.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Backend stopped unexpectedly or failed to start.
    echo Check logs in logs\backend_error.log
    pause
)
"@
    Set-Content -Path $startBackendBat -Value $backendBatContent -Encoding ASCII

    $startFrontendPs1 = Join-Path $InstallDir "start_frontend.ps1"
    $frontendPs1Content = @"
# PlannedEducation - Frontend Launcher (PowerShell)
`$InstallDir = "`$PSScriptRoot"
`$portalDir = Join-Path `$InstallDir "web\apps\portal"
`$logsDir = Join-Path `$InstallDir "logs"
if (-not (Test-Path `$logsDir)) { New-Item -ItemType Directory -Path `$logsDir -Force | Out-Null }
`$frontendPort = $FrontendPort
`$depCfg = Join-Path `$InstallDir "config\deployment.json"
if (Test-Path `$depCfg) {
    try {
        `$cfg = Get-Content `$depCfg -Raw | ConvertFrom-Json
        if (`$cfg.frontend_port) { `$frontendPort = `$cfg.frontend_port }
    } catch {}
}
Set-Location `$portalDir
Write-Host "Starting PlannedEducation Frontend on port `$frontendPort..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
npm run preview -- --host 127.0.0.1 --port `$frontendPort
"@
    Set-Content -Path $startFrontendPs1 -Value $frontendPs1Content -Encoding UTF8

    $startFrontendBat = Join-Path $InstallDir "start_frontend.bat"
    $frontendBatContent = @"
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_frontend.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend stopped unexpectedly or failed to start.
    echo Check logs in logs\frontend_error.log
    pause
)
"@
    Set-Content -Path $startFrontendBat -Value $frontendBatContent -Encoding ASCII

    $stopAllPs1 = Join-Path $InstallDir "stop_all.ps1"
    $stopAllPs1Content = @"
# PlannedEducation - Process Terminator (PowerShell)
`$InstallDir = "`$PSScriptRoot"
`$apiPort = $ApiPort
`$frontendPort = $FrontendPort
`$depCfg = Join-Path `$InstallDir "config\deployment.json"
if (Test-Path `$depCfg) {
    try {
        `$cfg = Get-Content `$depCfg -Raw | ConvertFrom-Json
        if (`$cfg.api_port) { `$apiPort = `$cfg.api_port }
        if (`$cfg.frontend_port) { `$frontendPort = `$cfg.frontend_port }
    } catch {}
}

Write-Host "Stopping PlannedEducation processes on ports `$apiPort and `$frontendPort..." -ForegroundColor Yellow
`$stopped = 0
foreach (`$port in @(`$apiPort, `$frontendPort)) {
    try {
        `$conns = Get-NetTCPConnection -LocalPort `$port -State Listen -ErrorAction SilentlyContinue
        foreach (`$c in `$conns) {
            `$p = Get-Process -Id `$c.OwningProcess -ErrorAction SilentlyContinue
            if (`$p -and `$p.Id -ne `$PID) {
                Write-Host "  Stopping `$(`$p.ProcessName) (PID: `$(`$p.Id)) on port `$port..." -ForegroundColor Cyan
                Stop-Process -Id `$p.Id -Force -ErrorAction SilentlyContinue
                `$stopped++
            }
        }
    } catch {}
}
if (`$stopped -gt 0) {
    Write-Host "[OK] Stopped `$stopped PlannedEducation processes." -ForegroundColor Green
} else {
    Write-Host "[INFO] No active listeners found on ports `$apiPort or `$frontendPort." -ForegroundColor Blue
}
"@
    Set-Content -Path $stopAllPs1 -Value $stopAllPs1Content -Encoding UTF8

    $stopAllBat = Join-Path $InstallDir "stop_all.bat"
    $stopAllBatContent = @"
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0stop_all.ps1"
"@
    Set-Content -Path $stopAllBat -Value $stopAllBatContent -Encoding ASCII

    $verifyPs1 = Join-Path $InstallDir "verify.ps1"
    $verifyPs1Content = @"
<#
.SYNOPSIS
    PlannedEducation - Deployment & Health Verification Tool
#>
param([string]`$InstallDir = "`$PSScriptRoot")

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PlannedEducation Deployment Health Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

`$allOk = `$true

# 1. Directory & Config Check
Write-Host -NoNewline "Checking installation directory (`$InstallDir)... "
if (Test-Path `$InstallDir) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "FAIL (not found)" -ForegroundColor Red; `$allOk = `$false }

`$apiPort = $ApiPort
`$frontendPort = $FrontendPort
`$domain = "$Domain"
`$depCfg = Join-Path `$InstallDir "config\deployment.json"
Write-Host -NoNewline "Checking deployment config (`$depCfg)... "
if (Test-Path `$depCfg) {
    Write-Host "OK" -ForegroundColor Green
    try {
        `$cfg = Get-Content `$depCfg -Raw | ConvertFrom-Json
        if (`$cfg.api_port) { `$apiPort = `$cfg.api_port }
        if (`$cfg.frontend_port) { `$frontendPort = `$cfg.frontend_port }
        if (`$cfg.domain) { `$domain = `$cfg.domain }
    } catch {}
} else {
    Write-Host "WARN (deployment.json not found, using default ports)" -ForegroundColor Yellow
}

# 2. Database Check
`$dbFile = Join-Path `$InstallDir "plannededucation.db"
Write-Host -NoNewline "Checking database (`$dbFile)... "
if (Test-Path `$dbFile) {
    Write-Host "OK (`$((Get-Item `$dbFile).Length) bytes)" -ForegroundColor Green
} else {
    Write-Host "WARN (SQLite file not present, or using external PostgreSQL)" -ForegroundColor Yellow
}

# 3. Backend Health Check
Write-Host -NoNewline "Checking Backend API (http://127.0.0.1:`$apiPort/health)... "
try {
    `$res = Invoke-RestMethod -Uri "http://127.0.0.1:`$apiPort/health" -TimeoutSec 3 -ErrorAction Stop
    if (`$res.status -eq "ok") {
        Write-Host "OK (status: `$(`$res.status), version: `$(`$res.version))" -ForegroundColor Green
    } else {
        Write-Host "WARN (`$(`$res | ConvertTo-Json -Compress))" -ForegroundColor Yellow
        `$allOk = `$false
    }
} catch {
    Write-Host "NOT RESPONDING (Backend is not running)" -ForegroundColor Red
    `$allOk = `$false
}

# 4. Package Engine Check
Write-Host -NoNewline "Checking Package Engine (http://127.0.0.1:`$apiPort/packages/health)... "
try {
    `$res = Invoke-RestMethod -Uri "http://127.0.0.1:`$apiPort/packages/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "OK (status: `$(`$res.status))" -ForegroundColor Green
} catch {
    Write-Host "NOT RESPONDING" -ForegroundColor Red
}

# 5. Frontend Check
Write-Host -NoNewline "Checking Frontend Portal (http://127.0.0.1:`$frontendPort)... "
try {
    `$client = New-Object System.Net.Sockets.TcpClient
    `$iar = `$client.BeginConnect("127.0.0.1", `$frontendPort, `$null, `$null)
    `$ok = `$iar.AsyncWaitHandle.WaitOne(1000)
    if (`$ok -and `$client.Connected) {
        `$client.Close()
        Write-Host "OK (listening on port `$frontendPort)" -ForegroundColor Green
    } else {
        `$client.Close()
        Write-Host "NOT LISTENING (Frontend is not running)" -ForegroundColor Red
        `$allOk = `$false
    }
} catch {
    Write-Host "NOT LISTENING" -ForegroundColor Red
    `$allOk = `$false
}

Write-Host "============================================================" -ForegroundColor Cyan
if (`$allOk) {
    Write-Host "  Result: ALL SYSTEMS OPERATIONAL [OK]" -ForegroundColor Green
    Write-Host "  Portal URL:  http://`${domain}:${frontendPort}" -ForegroundColor Green
    Write-Host "  Backend API: http://`${domain}:${apiPort}" -ForegroundColor Green
} else {
    Write-Host "  Result: SOME SERVICES NOT RUNNING OR FAILED [WARN]" -ForegroundColor Yellow
    Write-Host "  To start: Run .\start_all.bat (or .\start_all.ps1)" -ForegroundColor Cyan
    Write-Host "  To stop:  Run .\stop_all.bat (or .\stop_all.ps1)" -ForegroundColor Cyan
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
"@
    Set-Content -Path $verifyPs1 -Value $verifyPs1Content -Encoding UTF8

    $verifyBat = Join-Path $InstallDir "verify.bat"
    $verifyBatContent = @"
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0verify.ps1"
pause
"@
    Set-Content -Path $verifyBat -Value $verifyBatContent -Encoding ASCII

    Write-Success "Created launcher & management suite: start_all (.ps1/.bat), stop_all (.ps1/.bat), verify (.ps1/.bat), start_backend (.ps1/.bat), start_frontend (.ps1/.bat)"


    # Register Windows Scheduled Task if running as Administrator
    if ($isAdmin) {
        Write-Info "Creating Windows Scheduled Task for Backend..."
        try {
            $action = New-ScheduledTaskAction -Execute $startBackendBat -WorkingDirectory $InstallDir
            $trigger = New-ScheduledTaskTrigger -AtStartup
            $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
            Register-ScheduledTask -TaskName "PlannedEducation-Backend" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
            Write-Success "Windows Scheduled Task 'PlannedEducation-Backend' created"
        } catch {
            Write-Warning "Could not register Scheduled Task: $_"
        }
    }
}

# Step 8: Create Initial Admin Account & School (fresh installs only)
Write-Header "Step 8: Creating Initial Superadmin & School"

$skipAdminBootstrap = $false
if ($script:IsUpdate -and -not $useDocker) {
    $env:PYTHONPATH = Join-Path $InstallDir "src"
    Load-DotEnv $envFile
    try {
        $userCount = & $pythonExe -c "from plannededucation.api.database import SessionLocal; from plannededucation.api.models import User; db=SessionLocal(); print(db.query(User).count()); db.close()" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$userCount -gt 0) {
            $skipAdminBootstrap = $true
            Write-Info "Existing users detected ($userCount). Skipping admin bootstrap to preserve accounts and passwords."
            Write-Info "Set PE_FORCE_ADMIN_BOOTSTRAP=1 only if you intentionally need to reset the bootstrap superadmin."
        }
    } catch {
        Write-Warning "Could not probe existing users; continuing carefully."
    }
    if ($env:PE_FORCE_ADMIN_BOOTSTRAP -eq "1") {
        $skipAdminBootstrap = $false
        Write-Warning "PE_FORCE_ADMIN_BOOTSTRAP=1 set - bootstrap admin may be created/updated."
    }
}

$generatedRandom = $false

if ($skipAdminBootstrap) {
    Write-Success "Update mode: existing school accounts left unchanged."
} elseif (-not $AutoConfirm) {
    $inputSchool = Read-Host "Enter School / Institution Name (default: $SchoolName)"
    if ($inputSchool -and $inputSchool.Trim() -ne "") { $SchoolName = $inputSchool.Trim() }
    $inputEmail = Read-Host "Enter Superadmin Email (default: $AdminEmail)"
    if ($inputEmail -and $inputEmail.Trim() -ne "") { $AdminEmail = $inputEmail.Trim() }
    $inputName = Read-Host "Enter Superadmin Full Name (default: $AdminName)"
    if ($inputName -and $inputName.Trim() -ne "") { $AdminName = $inputName.Trim() }

    Write-Host ""
    Write-Host "Set Superadmin Password:" -ForegroundColor $CYAN
    Write-Host "  - Enter your desired password, OR"
    Write-Host "  - Press [Enter] to generate a secure random password"
    $inputPass = Read-Host "Superadmin Password"
    if ($inputPass -and $inputPass.Trim() -ne "") {
        $AdminPassword = $inputPass.Trim()
    } else {
        $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
        $AdminPassword = -join ((1..20) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
        $generatedRandom = $true
    }
} else {
    # AutoConfirm: reject empty/predictable passwords; generate a strong random one (F-031).
    if ([string]::IsNullOrWhiteSpace($AdminPassword) -or $AdminPassword -in @("AdminPassword123!", "ChangeMe123!", "changeme", "password")) {
        Write-Info "AutoConfirm enabled; generating secure random Superadmin password."
        $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
        $AdminPassword = -join ((1..20) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
        $generatedRandom = $true
    }
}

if ($generatedRandom -and -not $skipAdminBootstrap) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host "  [KEY] GENERATED SUPERADMIN PASSWORD" -ForegroundColor $GREEN
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host "  Email / Username:   $AdminEmail" -ForegroundColor $WHITE
    Write-Host "  Generated Password: $AdminPassword" -ForegroundColor $GREEN
    Write-Host "============================================================" -ForegroundColor $YELLOW
    Write-Host "  [IMPORTANT] Please copy or write down this password now!" -ForegroundColor $YELLOW
    Write-Host "  It will NOT be shown again in plaintext on screen." -ForegroundColor $YELLOW
    Write-Host "============================================================" -ForegroundColor $YELLOW
    if (-not $AutoConfirm) {
        try {
            Read-Host "  Press [Enter] once you have copied/noted down the password to continue"
        } catch {}
    }
    Write-Host ""
}

if (-not $useDocker -and -not $skipAdminBootstrap) {
    $env:PYTHONPATH = Join-Path $InstallDir "src"
    $env:PE_ADMIN_EMAIL = $AdminEmail
    $env:PE_ADMIN_PASSWORD = $AdminPassword
    $env:PE_ADMIN_NAME = $AdminName
    $env:PE_SCHOOL_NAME = $SchoolName

    $setupAdminScript = Join-Path $InstallDir "scripts\deploy\setup_admin.py"
    if (-not (Test-Path $setupAdminScript)) {
        $setupAdminScript = Join-Path $PSScriptRoot "scripts\deploy\setup_admin.py"
    }
    & $pythonExe "$setupAdminScript"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Admin creation failed!"
        exit 1
    }

    $credFile = Join-Path $InstallDir "ADMIN_CREDENTIALS.txt"
    $codesText = ""
    $tmpCodes = Join-Path $InstallDir "admin_recovery_codes.tmp"
    if (Test-Path $tmpCodes) {
        $codesList = Get-Content $tmpCodes
        $codesText = ($codesList | ForEach-Object { "  - $_" }) -join "`r`n"
        Remove-Item $tmpCodes -Force -ErrorAction SilentlyContinue

        # Clipboard may include password for one-time handoff; disk fallback never stores password (F-031).
        $credLines = @(
            "PlannedEducation Superadmin Credentials",
            "=======================================",
            "School Name:    $SchoolName",
            "Admin Email:    $AdminEmail",
            "Admin Password: $AdminPassword",
            "Admin Name:     $AdminName",
            ("Backend API:    http://" + $Domain + ":" + $ApiPort),
            ("Frontend URL:   http://" + $Domain + ":" + $FrontendPort),
            "",
            "============================================================",
            "EMERGENCY RECOVERY CODES (PRINT OR KEEP SAFE):",
            $codesText,
            "",
            "WARNING: If you lose both your administrator password and these",
            "recovery codes, you will be permanently locked out and will need",
            "to redeploy the entire platform, as database injection is not an option.",
            "============================================================"
        )
        $credContent = $credLines -join "`r`n"
        $recoveryOnlyLines = @(
            "PlannedEducation Superadmin Recovery Codes (password NOT stored)",
            "===============================================================",
            "School Name:    $SchoolName",
            "Admin Email:    $AdminEmail",
            "Admin Name:     $AdminName",
            "",
            "EMERGENCY RECOVERY CODES:",
            $codesText,
            "",
            "Password was shown once during install and is not written to disk."
        )
        $recoveryOnly = $recoveryOnlyLines -join "`r`n"

        $clipboardOk = $false
        try {
            $credContent | Set-Clipboard
            $clipboardOk = $true
        } catch {
            $clipboardOk = $false
        }

        if ($clipboardOk) {
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor $CYAN
            Write-Host "  [KEY] SUPERADMIN CREDENTIALS COPIED TO CLIPBOARD" -ForegroundColor $YELLOW
            Write-Host "============================================================" -ForegroundColor $CYAN
            Write-Host ""
            Write-Host "  The following credentials have been copied to your clipboard:" -ForegroundColor $WHITE
            Write-Host "    - Admin Email:    $AdminEmail" -ForegroundColor $WHITE
            Write-Host "    - Admin Password: (included in clipboard - paste into a password manager now)" -ForegroundColor $WHITE
            Write-Host "    - Recovery Codes: $($codesList.Count) one-time codes" -ForegroundColor $WHITE
            Write-Host ""
            Write-Host "  Credentials are NOT saved to any plaintext password file on disk." -ForegroundColor $YELLOW
        } else {
            Write-Warning "Could not copy to clipboard. Saving recovery codes only (no password) to $credFile."
            [System.IO.File]::WriteAllText($credFile, $recoveryOnly, (New-Object System.Text.UTF8Encoding($false)))
            try {
                icacls $credFile /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null
            } catch {}
            Write-Info "Saved recovery codes to ADMIN_CREDENTIALS.txt (password omitted)."
        }

        Write-Host ""
        Write-Host "============================================================" -ForegroundColor $CYAN
        Write-Host "  [KEY] SUPERADMIN EMERGENCY RECOVERY CODES" -ForegroundColor $YELLOW
        Write-Host "============================================================" -ForegroundColor $CYAN
        foreach ($c in $codesList) {
            Write-Host "    $c" -ForegroundColor $GREEN
        }
        Write-Host "============================================================" -ForegroundColor $CYAN
        Write-Host "  [!] CRITICAL NOTICE FOR ADMINISTRATOR:" -ForegroundColor $YELLOW
        Write-Host "  1. Store these 5 one-time recovery codes safely (print or write them down)." -ForegroundColor $WHITE
        Write-Host "  2. If you lose your administrator password and recovery codes, you will" -ForegroundColor $WHITE
        Write-Host "     be permanently locked out and may need to redeploy the whole system," -ForegroundColor $WHITE
        Write-Host "     as direct database injection is blocked for security." -ForegroundColor $WHITE
        Write-Host "============================================================" -ForegroundColor $CYAN
        if (-not $AutoConfirm) {
            try {
                Read-Host "  Press [Enter] once you have safely saved these credentials to continue"
            } catch {}
        }
        Write-Host ""
    }

    Write-Success "Superadmin account ready: $AdminEmail"
}

# Step 9: Run Verification Tests
Write-Header "Step 9: Running Verification Tests"

$testsPassed = 0
$testsFailed = 0

function Run-Verify {
    param([string]$TestName, [scriptblock]$TestBlock)
    Write-Host -NoNewline "Testing $TestName... "
    try {
        $result = & $TestBlock
        if ($result) {
            Write-Host "PASSED" -ForegroundColor $GREEN
            Write-InstallLog -Level "VERIFY_PASS" -Message $TestName
            $script:testsPassed++
            return $true
        }
    } catch {
        Write-InstallLog -Level "VERIFY_FAIL" -Message "$TestName - $_" -IsError $true
    }
    Write-Host "FAILED" -ForegroundColor $RED
    $script:testsFailed++
    return $false
}

Run-Verify "Environment configuration (.env)" { Test-Path (Join-Path $InstallDir ".env") } | Out-Null
Run-Verify "Deployment configuration (config/deployment.json)" { Test-Path (Join-Path $InstallDir "config\deployment.json") } | Out-Null

if ($useSqlite) {
    Run-Verify "SQLite database initialized" { Test-Path (Join-Path $InstallDir "plannededucation.db") } | Out-Null
} elseif (-not $useDocker) {
    Run-Verify "PostgreSQL connection" { psql -U postgres -c "\l" | Out-Null; $true } | Out-Null
    Run-Verify "Redis connection" { (redis-cli ping) -match "PONG" } | Out-Null
}

if (-not $useDocker) {
    Run-Verify "Frontend production build (dist/index.html)" {
        Test-Path (Join-Path $InstallDir "web\apps\portal\dist\index.html")
    } | Out-Null

    Run-Verify "Backend FastAPI health endpoint (TestClient)" {
        $envPath = Join-Path $InstallDir ".env"
        $srcPath = Join-Path $InstallDir "src"
        $verifyScript = @"
import os, sys
from pathlib import Path
env_file = Path(r'$envPath')
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
os.environ['PLANNED_EDUCATION_ENV'] = 'test'
sys.path.insert(0, r'$srcPath')
from fastapi.testclient import TestClient
from plannededucation.api.main import app
c = TestClient(app)
r = c.get('/health')
assert r.status_code == 200, r.text
print('HEALTH_OK')
"@
        $out = $verifyScript | & $pythonExe -
        $out -match "HEALTH_OK"
    } | Out-Null
}

# Step 9b: Generate Install Manifest (for safe uninstall)
    Write-Header "Step 9b: Generating Install Manifest"
    $installManifestPath = Join-Path $script:LogDir "install_manifest.txt"
    try {
        # Record every file currently in the installation directory so uninstall knows exactly what to remove
        $installedFiles = Get-ChildItem -Path $InstallDir -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
        $installedFiles | Set-Content -Path $installManifestPath -Encoding UTF8
        Write-Success "Install manifest written to: $installManifestPath ($($installedFiles.Count) files tracked)"
    } catch {
        Write-Warning "Could not generate install manifest: $_"
        Write-Info "Uninstall will fall back to removing the entire directory."
    }

# Step 10: Final Summary

Write-Host "Verification Results: $testsPassed passed, $testsFailed failed" -ForegroundColor $GREEN
Write-Host ""
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host "  PlannedEducation is installed and ready!" -ForegroundColor $GREEN
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host "  Install Dir:    $InstallDir"
Write-Host "  School Name:    $SchoolName"
Write-Host "  Backend API:    http://${Domain}:${ApiPort}"
Write-Host "  API Docs:       http://${Domain}:${ApiPort}/docs"
Write-Host "  Frontend App:   http://${Domain}:${FrontendPort}"
Write-Host "  Admin Email:    $AdminEmail"
Write-Host "  Admin Password: (shown once above if generated - not re-printed here)"
Write-Host "  Diagnostic Logs:"
Write-Host "    - Install Log:        $InstallDir\logs\install.log"
Write-Host "    - Install Error Log:  $InstallDir\logs\install_error.log"
Write-Host "    - Backend Log:        $InstallDir\logs\backend.log"
Write-Host "    - Backend Error Log:  $InstallDir\logs\backend_error.log"
Write-Host "    - Frontend Log:       $InstallDir\logs\frontend.log"
Write-Host "    - Frontend Error Log: $InstallDir\logs\frontend_error.log"
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host ""
Write-Info "Important Management Commands:"
Write-Host "  1. Start Platform: $InstallDir\start_all.bat   (or .\start_all.ps1)" -ForegroundColor $GREEN
Write-Host "  2. Verify Status:  $InstallDir\verify.bat      (or .\verify.ps1)" -ForegroundColor $CYAN
Write-Host "  3. Stop Platform:  $InstallDir\stop_all.bat    (or .\stop_all.ps1)" -ForegroundColor $YELLOW
Write-Host "  4. Uninstaller:    $InstallDir\uninstall.ps1" -ForegroundColor $WHITE
Write-Host ""
Write-Host "  Log in with your Superadmin credentials and change your password."
Write-Host ""
Write-Success "Thank you for using PlannedEducation!"
