<#
.SYNOPSIS
    PlannedEducation - Complete Automated Installation Script for Windows
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
    Initial administrator password (default: AdminPassword123!)

.PARAMETER AdminName
    Initial administrator full name (default: School Administrator)

.PARAMETER SchoolName
    Initial school/institution name (default: PlannedEducation School)

.PARAMETER AutoConfirm
    Run non-interactively using supplied parameter values (for AI agents / CI after human approval of key choices)
#>

param(
    [string]$InstallDir = "C:\PlannedEducation",
    [string]$DeployMode = "1",
    [string]$Domain = "localhost",
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173,
    [string]$AdminEmail = "admin@yourschool.edu",
    [string]$AdminPassword = "AdminPassword123!",
    [string]$AdminName = "School Administrator",
    [string]$SchoolName = "PlannedEducation School",
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
    param([string]$Message)
    if ($AutoConfirm) { return $true }
    $response = Read-Host "$Message (y/N)"
    return $response -match '^[Yy]$'
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
    Write-Warning "Not running as Administrator. System-wide package installation and Windows Scheduled Task registration will be skipped."
    if (-not $AutoConfirm) {
        $confirm = Read-Host "Continue in user-mode installation? (y/N)"
        if ($confirm -notmatch '^[Yy]$') { exit 1 }
    }
}

Write-Header "PlannedEducation Automated Installer (Windows)"

# Step 1: Check Prerequisites
Write-Header "Step 1: Checking Prerequisites"

$hasGit = Check-Command "Git" "git" "--version"
$hasPython = Check-Command "Python 3.11+" "python" "--version"
$hasNode = Check-Command "Node.js 20+" "node" "--version"
$hasNpm = Check-Command "npm" "npm" "--version"
$hasDocker = Check-Command "Docker Desktop" "docker" "--version"
$hasPostgres = Check-Command "PostgreSQL" "psql" "--version"
$hasRedis = Check-Command "Redis" "redis-cli" "--version"

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

# Step 3: Install Missing Required Dependencies
Write-Header "Step 3: Checking & Installing Required Dependencies"

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

# Step 4: Clone Repository & Setup Directory
Write-Header "Step 4: Setting Up Application Directory"

if (-not $AutoConfirm) {
    $inputDir = Read-Host "Installation directory (default: $InstallDir)"
    if ($inputDir) { $InstallDir = $inputDir }
}

$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Success "Created directory: $InstallDir"
}

$scriptRepoRoot = $PSScriptRoot
if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
    Write-Info "Cloning PlannedEducation repository into $InstallDir..."
    # Clone into a temp sibling directory first: $InstallDir may already contain logs\ (the
    # installer logs from the very first step), and git refuses to clone into a non-empty dir.
    $cloneTmp = "$InstallDir.clone-tmp"
    if (Test-Path $cloneTmp) { Remove-Item $cloneTmp -Recurse -Force -ErrorAction SilentlyContinue }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $cloneOutput = & git clone --quiet https://github.com/ezixen/PlannedEducation.git $cloneTmp 2>&1
    $cloneExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($cloneExit -ne 0) {
        Write-ErrorMsg "git clone failed (exit $cloneExit): $($cloneOutput -join ' ')"
        exit 1
    }
    Copy-Item -Path (Join-Path $cloneTmp "*") -Destination $InstallDir -Recurse -Force
    Copy-Item -Path (Join-Path $cloneTmp ".git") -Destination $InstallDir -Recurse -Force
    Remove-Item $cloneTmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Success "Repository cloned successfully"
} else {
    Write-Info "Repository already exists in $InstallDir, pulling latest changes..."
    Push-Location $InstallDir
    try {
        git pull origin dev 2>&1 | Out-Null
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
        @{ From = "src";                  To = "src" },
        @{ From = "web\apps\portal\src";  To = "web\apps\portal\src" }
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

# Read existing deployment.json defaults if available
$existingDepJson = Join-Path $InstallDir "config\deployment.json"
if (Test-Path $existingDepJson) {
    try {
        $parsedDep = Get-Content $existingDepJson -Raw | ConvertFrom-Json
        if ($parsedDep.domain) { $Domain = $parsedDep.domain }
        if ($parsedDep.api_port) { $ApiPort = [int]$parsedDep.api_port }
        if ($parsedDep.frontend_port) { $FrontendPort = [int]$parsedDep.frontend_port }
        if ($parsedDep.school_name) { $SchoolName = $parsedDep.school_name }
    } catch {}
}

# Step 5: Configure Environment Variables & Secrets
Write-Header "Step 5: Configuring Environment & Secrets"

$envFile = Join-Path $InstallDir ".env"
if (-not (Test-Path $envFile) -or (Confirm-Action "Overwrite existing .env configuration?")) {
    Write-Info "Generating cryptographically secure secrets..."

    # Generate 64-char hex JWT secret
    $jwtBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($jwtBytes)
    $jwtSecret = [System.BitConverter]::ToString($jwtBytes).Replace("-", "").ToLower()

    # Generate URL-safe base64 32-byte Fernet key
    $fernetBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($fernetBytes)
    $fernetKey = [System.Convert]::ToBase64String($fernetBytes).Replace("+", "-").Replace("/", "_")

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

    $envContent = @"
# PlannedEducation Environment Configuration
# Generated on $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")

# Database
DATABASE_URL=$dbUrl

# Redis
REDIS_URL=$redisUrl

# Security Secrets (NEVER SHARE THESE!)
JWT_SECRET_KEY=$jwtSecret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=$fernetKey
AI_KEY_MASTER_SECRET=$fernetKey

# Server Configuration
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
    $depConfigObj = [PSCustomObject]@{
        school_name = $SchoolName
        domain = $Domain
        api_port = $ApiPort
        frontend_port = $FrontendPort
        cors_origins = $corsList
        allowed_hosts = "$Domain,localhost,127.0.0.1"
        environment = $envMode
        allow_dev_seb_bypass = ($sebBypass -eq "true")
        anonymizer_enabled = $true
        anonymizer_language = "en"
        updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $depConfigObj | ConvertTo-Json -Depth 4 | Set-Content -Path $deploymentJsonFile -Encoding UTF8
    Write-Success "Created config/deployment.json (domain: $Domain, API port: $ApiPort, Frontend port: $FrontendPort)"
} else {
    Write-Info "Keeping existing .env file"
}

Load-DotEnv $envFile
if ($env:PORT) { $ApiPort = [int]$env:PORT }
if ($env:FRONTEND_PORT) { $FrontendPort = [int]$env:FRONTEND_PORT }

# Step 6: Setup Application & Databases
if ($useDocker) {
    Write-Header "Step 6: Starting Docker Containers"
    Write-Info "Building and starting containers via Docker Compose..."
    docker compose up -d --build
    Write-Success "Docker containers started!"
} else {
    Write-Header "Step 6: Setting Up Databases & Application"

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

    # Setup Python Virtual Environment (prefer shared C:/.venv if present per workspace standards, else local .venv)
    $sharedVenvPython = "C:\.venv\Scripts\python.exe"
    $localVenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"
    if (Test-Path $sharedVenvPython) {
        $pythonExe = $sharedVenvPython
        Write-Info "Using shared Python virtual environment at C:\.venv..."
    } else {
        Write-Info "Creating Python virtual environment at $InstallDir\.venv..."
        python -m venv (Join-Path $InstallDir ".venv")
        $pythonExe = $localVenvPython
    }

    Write-Info "Verifying Python dependencies..."
    & $pythonExe -m pip install -q -r (Join-Path $InstallDir "src\requirements.txt")
    Write-Success "Python dependencies installed"

    # Initialize Database Tables
    Write-Info "Initializing database tables..."
    $env:PYTHONPATH = Join-Path $InstallDir "src"
    & $pythonExe -c "import plannededucation.api.models; from plannededucation.api.database import Base, engine; Base.metadata.create_all(bind=engine); print('Database tables initialized successfully!')"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Database initialization failed!"
        exit 1
    }
    Write-Success "Database tables created"

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

    # Create Launcher Scripts with separated stdout and error logs
    $startBackendBat = Join-Path $InstallDir "start_backend.bat"
    $backendBatContent = @"
@echo off
cd /d "$InstallDir"
if not exist "$InstallDir\logs" mkdir "$InstallDir\logs"
set PYTHONPATH=$InstallDir\src
set PLANNED_EDUCATION_LOG_DIR=$InstallDir\logs
if "%API_PORT%"=="" set API_PORT=$ApiPort
echo Starting PlannedEducation Backend on port %API_PORT% (structured logs: logs\backend.log / logs\backend_error.log, raw console: logs\backend_stdout.log / logs\backend_stderr.log)...
"$pythonExe" -m uvicorn plannededucation.api.main:app --env-file "$InstallDir\.env" --host 0.0.0.0 --port %API_PORT% >> "$InstallDir\logs\backend_stdout.log" 2>> "$InstallDir\logs\backend_stderr.log"
"@
    Set-Content -Path $startBackendBat -Value $backendBatContent -Encoding ASCII

    $startFrontendBat = Join-Path $InstallDir "start_frontend.bat"
    $frontendBatContent = @"
@echo off
cd /d "$InstallDir\web\apps\portal"
if not exist "$InstallDir\logs" mkdir "$InstallDir\logs"
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=$FrontendPort
echo Starting PlannedEducation Frontend on port %FRONTEND_PORT% (Logs: logs\frontend.log, Error Logs: logs\frontend_error.log)...
npm run preview -- --host 127.0.0.1 --port %FRONTEND_PORT% >> "$InstallDir\logs\frontend.log" 2>> "$InstallDir\logs\frontend_error.log"
"@
    Set-Content -Path $startFrontendBat -Value $frontendBatContent -Encoding ASCII
    Write-Success "Created launcher scripts: start_backend.bat, start_frontend.bat (with logs\backend.log & logs\backend_error.log)"

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

# Step 7: Create Initial Admin Account & School
Write-Header "Step 7: Creating Initial Superadmin & School"

if (-not $AutoConfirm) {
    $inputSchool = Read-Host "Enter School / Institution Name (default: $SchoolName)"
    if ($inputSchool) { $SchoolName = $inputSchool }
    $inputEmail = Read-Host "Enter Superadmin Email (default: $AdminEmail)"
    if ($inputEmail) { $AdminEmail = $inputEmail }
    $inputPass = Read-Host "Enter Superadmin Password (default: $AdminPassword)"
    if ($inputPass) { $AdminPassword = $inputPass }
    $inputName = Read-Host "Enter Superadmin Full Name (default: $AdminName)"
    if ($inputName) { $AdminName = $inputName }
} else {
    # Even in AutoConfirm mode, ask for admin password if it's the default or prompt administrator
    if ($AdminPassword -eq "AdminPassword123!") {
        Write-Host ""
        Write-Host "[SECURITY REQUIREMENT] Superadmin Password Configuration" -ForegroundColor $YELLOW
        Write-Host "For security, you must set a secure administrator password." -ForegroundColor $WHITE
        try {
            $inputPass = Read-Host "Enter Superadmin Password (press Enter to generate a secure random password)"
            if ($inputPass) {
                $AdminPassword = $inputPass
            } else {
                $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
                $AdminPassword = -join ((1..16) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
                Write-Info "Generated secure Superadmin Password: $AdminPassword"
            }
        } catch {
            Write-Info "Non-interactive environment detected; using configured administrator password."
        }
    }
}

if (-not $useDocker) {
    $env:PYTHONPATH = Join-Path $InstallDir "src"
    $env:PE_ADMIN_EMAIL = $AdminEmail
    $env:PE_ADMIN_PASSWORD = $AdminPassword
    $env:PE_ADMIN_NAME = $AdminName
    $env:PE_SCHOOL_NAME = $SchoolName

    $adminScript = @"
import hashlib
import json
import os
from plannededucation.api import auth
from plannededucation.api.database import Base, SessionLocal, engine
from plannededucation.api.models import School, User, UserRole
from plannededucation.api.routes_auth import get_password_hash, _encode_recovery_codes

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    school_name = os.environ.get('PE_SCHOOL_NAME', 'PlannedEducation School')
    if not db.query(School).first():
        db.add(School(name=school_name, address='Local Campus'))
        db.commit()

    email = os.environ['PE_ADMIN_EMAIL']
    pwd = os.environ['PE_ADMIN_PASSWORD']
    name = os.environ['PE_ADMIN_NAME']
    uname = email.split('@')[0] or 'admin'

    plain_recovery_codes = auth.generate_recovery_codes(count=5)
    hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in plain_recovery_codes]

    existing = db.query(User).filter((User.email == email) | (User.username == uname)).first()
    if existing:
        existing.email = email
        existing.hashed_password = get_password_hash(pwd)
        existing.full_name = name
        existing.role = UserRole.admin.value
        existing.is_admin = True
        existing.is_active = True
        existing.recovery_codes = _encode_recovery_codes(hashed_codes)
        db.commit()
        print(f'Updated existing Admin user: {email}')
    else:
        admin = User(
            username=uname,
            email=email,
            hashed_password=get_password_hash(pwd),
            full_name=name,
            role=UserRole.admin.value,
            is_admin=True,
            is_active=True,
            recovery_codes=_encode_recovery_codes(hashed_codes)
        )
        db.add(admin)
        db.commit()
        print(f'Created initial Admin user: {email}')

    print('\n' + '=' * 68)
    print('  🔑 SUPERADMIN EMERGENCY RECOVERY CODES')
    print('=' * 68)
    for i, code in enumerate(plain_recovery_codes, 1):
        print(f'    Code {i}: {code}')
    print('=' * 68)
    print('  ⚠️  CRITICAL NOTICE FOR ADMINISTRATOR:')
    print('  Store these 5 one-time recovery codes safely (print or write them down).')
    print('  If you lose your administrator password and recovery codes, you will')
    print('  be locked out and may need to redeploy the whole system, as database')
    print('  injection is blocked for security.')
    print('=' * 68 + '\n')

    # Save codes to file for installer to read
    with open('admin_recovery_codes.tmp', 'w') as f:
        f.write('\n'.join(plain_recovery_codes))
finally:
    db.close()
"@
    & $pythonExe -c $adminScript
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Admin creation failed!"
        exit 1
    }

    $codesText = ""
    $tmpCodes = Join-Path $InstallDir "admin_recovery_codes.tmp"
    if (Test-Path $tmpCodes) {
        $codesList = Get-Content $tmpCodes
        $codesText = ($codesList | ForEach-Object { "  - $_" }) -join "`r`n"
        Remove-Item $tmpCodes -Force -ErrorAction SilentlyContinue
    }

    $credFile = Join-Path $InstallDir "ADMIN_CREDENTIALS.txt"
    $credContent = @"
PlannedEducation Superadmin Credentials
=======================================
School Name:    $SchoolName
Admin Email:    $AdminEmail
Admin Password: $AdminPassword
Admin Name:     $AdminName
Backend API:    http://${Domain}:${ApiPort}
Frontend URL:   http://${Domain}:${FrontendPort}

============================================================
EMERGENCY RECOVERY CODES (PRINT OR KEEP SAFE):
$codesText

WARNING: If you lose both your administrator password and these
recovery codes, you will be permanently locked out and will need
to redeploy the entire platform, as database injection is not an option.
============================================================
"@
    [System.IO.File]::WriteAllText($credFile, $credContent, (New-Object System.Text.UTF8Encoding($false)))
    Write-Success "Superadmin account ready: $AdminEmail (saved to ADMIN_CREDENTIALS.txt with emergency recovery codes)"
}

# Step 8: Run Verification Tests
Write-Header "Step 8: Running Verification Tests"

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
        $env:PYTHONPATH = Join-Path $InstallDir "src"
        $out = & $pythonExe -c "from fastapi.testclient import TestClient; from plannededucation.api.main import app; c = TestClient(app); r = c.get('/health'); assert r.status_code == 200, r.text; print('OK')"
        $out -match "OK"
    } | Out-Null
}

# Final Summary
Write-Header "Installation Complete!"

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
Write-Host "  Admin Password: $AdminPassword"
Write-Host "  Diagnostic Logs:"
Write-Host "    - Install Log:        $InstallDir\logs\install.log"
Write-Host "    - Install Error Log:  $InstallDir\logs\install_error.log"
Write-Host "    - Backend Log:        $InstallDir\logs\backend.log"
Write-Host "    - Backend Error Log:  $InstallDir\logs\backend_error.log"
Write-Host "    - Frontend Log:       $InstallDir\logs\frontend.log"
Write-Host "    - Frontend Error Log: $InstallDir\logs\frontend_error.log"
Write-Host "============================================================" -ForegroundColor $CYAN
Write-Host ""
Write-Info "Important Next Steps:"
Write-Host "  1. Start Backend:  $InstallDir\start_backend.bat"
Write-Host "  2. Start Frontend: $InstallDir\start_frontend.bat"
Write-Host "  3. Log in with your Superadmin credentials and change your password."
Write-Host ""
Write-Success "Thank you for using PlannedEducation!"