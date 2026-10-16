<#>
.SYNOPSIS
    PlannedEducation Windows Installer
    Run with: powershell -ExecutionPolicy Bypass -File install.ps1
    Or download and run: powershell -ExecutionPolicy Bypass -File install.ps1

.DESCRIPTION
    Installs PlannedEducation on Windows Server with Docker Desktop.
    Supports Windows Server 2016/2019/2022 and Windows 10/11 Pro/Enterprise.
    Compatible with PowerShell 5.1+ (Windows Server 2016+)

.NOTES
    Requires: Administrator privileges, Docker Desktop, Git, PowerShell 5.1+
#>

param(
    [string]$InstallDir = "C:\PlannedEducation",
    [switch]$SkipDockerCheck,
    [switch]$AutoConfirm
)

# Colors - using Write-Host with -ForegroundColor for compatibility
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"
$BLUE = "Blue"
$CYAN = "Cyan"
$MAGENTA = "Magenta"
$WHITE = "White"
$GRAY = "Gray"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $CYAN
    Write-Host $Text -ForegroundColor $CYAN
    Write-Host ("=" * 60) -ForegroundColor $CYAN
    Write-Host ""
}

function Write-Step {
    param([int]$Step, [int]$Total, [string]$Text)
    Write-Host "[Step $Step/$Total] $Text" -ForegroundColor $BLUE
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

function Check-Command {
    param([string]$Name, [string]$Command)
    try {
        $output = & $Command 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -eq 0) {
            $trimmed = $output.Trim()
            Write-Success "$Name: $trimmed"
            return $true
        }
    } catch {
        Write-Error "$Name: NOT FOUND"
        return $false
    }
}

# Check for Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator. Some operations may fail."
    if (-not $AutoConfirm) {
        $confirm = Read-Host "Continue anyway? (y/N)"
        if ($confirm -notmatch '^[Yy]$') { exit 1 }
    }
}

Write-Header "PlannedEducation Windows Installer"

# Choose deployment mode
Write-Header "Deployment Mode Selection"
Write-Host "${BOLD}Choose deployment mode:${RESET}"
Write-Host "  ${GREEN}1)${RESET} Native (no Docker) - PostgreSQL, Redis, and app run directly on Windows"
Write-Host "  ${GREEN}2)${RESET} Docker Compose - All services in containers (current default)"
Write-Host ""
$deployMode = Read-Host "Select mode [1/2] [1]"
if (-not $deployMode) { $deployMode = "1" }
$deployNative = ($deployMode -eq "1")

if ($deployNative) {
    Write-Success "Native deployment selected"
} else {
    Write-Success "Docker Compose deployment selected"
}

# Check requirements
Write-Step 1 8 "Checking requirements..."

$checksPassed = $true
$useSqlite = $false

if ($deployNative) {
    # Native deployment requirements
    # Python and Git are mandatory
    $reqChecks = @(
        @{Name="Git"; Command="git --version"},
        @{Name="Python"; Command="python --version"}
    )
    foreach ($check in $reqChecks) {
        if (Check-Command $check.Name $check.Command) {
            # success
        } else {
            Write-Error "$($check.Name): NOT FOUND"
            $checksPassed = $false
        }
    }

    # Optional services (PostgreSQL, Redis, Node.js)
    $hasPsql = Check-Command "PostgreSQL" "psql --version"
    $hasRedis = Check-Command "Redis" "redis-cli --version"
    Check-Command "Node.js" "node --version" | Out-Null
    Check-Command "npm" "npm --version" | Out-Null

    if (-not $hasPsql -or -not $hasRedis) {
        Write-Warning "PostgreSQL or Redis CLI not found. Falling back to Native SQLite mode (zero-configuration standalone mode)."
        $useSqlite = $true
    } else {
        # Check PostgreSQL service
        try {
            $svc = Get-Service postgresql* -ErrorAction SilentlyContinue
            if ($svc -and $svc.Status -eq 'Running') {
                Write-Success "PostgreSQL: running"
            } else {
                Write-Warning "PostgreSQL: not running (will attempt to start or fall back to SQLite)"
            }
        } catch {
            Write-Warning "PostgreSQL: service not found"
        }
    }
} else {
    # Docker deployment requirements
    $checks = @(
        @{Name="Docker"; Command="docker --version"},
        @{Name="Git"; Command="git --version"},
        @{Name="Python"; Command="python --version"}
    )
    
    foreach ($check in $checks) {
        if (Check-Command $check.Name $check.Command) {
            # success
        } else {
            Write-Error "$($check.Name): NOT FOUND"
            $checksPassed = $false
        }
    }
    
    # Check Docker Compose
    $composeOk = $false
    foreach ($cmd in @("docker compose version", "docker-compose --version")) {
        try {
            $output = & $cmd 2>&1 | Select-Object -First 1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker Compose: ${output.Trim()}"
                $composeOk = $true
                break
            }
        } catch {}
    }
    if (-not $composeOk) {
        Write-Error "Docker Compose: NOT FOUND"
        Write-Warning "Install Docker Desktop (includes Compose): https://www.docker.com/products/docker-desktop/"
        $checksPassed = $false
    }
}

if (-not $checksPassed) {
    Write-Error "Please install missing requirements and try again."
    if ($deployNative) {
        Write-Host "Install PostgreSQL: https://www.postgresql.org/download/windows/"
        Write-Host "Install Redis: https://github.com/microsoftarchive/redis/releases"
        Write-Host "Install Node.js: https://nodejs.org/"
        Write-Host "Then start services: Start-Service postgresql*; Start-Service redis*"
    } else {
        Write-Host "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    }
    exit 1
}

# Get installation directory
Write-Step 2 8 "Setting up installation directory..."
$installDir = "C:\PlannedEducation"
if (-not $AutoConfirm) {
    $input = Read-Host "Installation directory [$installDir]"
    if ($_) { $installDir = $_ }
}

if (Test-Path $installDir) {
    Write-Warning "Directory $installDir already exists"
    if (-not $AutoConfirm) {
        $confirm = Read-Host "Continue anyway? (y/N)"
        if ($confirm -notmatch '^[Yy]$') { exit 1 }
    }
}

# Clone repository
Write-Step 3 8 "Cloning repository..."
if (Test-Path "$installDir\.git") {
    Write-Warning "Repository already exists, pulling latest changes..."
    Set-Location $installDir
    git pull origin main
} else {
    git clone https://github.com/ezixen/PlannedEducation.git $installDir
    Set-Location $installDir
}

# Configure environment
Write-Step 4 8 "Configuring environment..."
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    
    # Generate secure keys
    $jwtKey = [System.Convert]::ToBase64String((1..64 | ForEach-Object { Get-Random -Maximum 256 }))
    $fernetKey = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    
    # Get domain
    $domain = Read-Host "School domain (e.g., yourschool.edu) [localhost]"
    if (-not $domain) { $domain = "localhost" }
    
    # Update .env
    $envContent = Get-Content .env -Raw
    $envContent = $envContent -replace 'JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$jwtKey"
    $pgPass = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    $envContent = $envContent -replace 'POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$pgPass"
    
    if ($domain -ne "localhost") {
        $envContent = $envContent -replace 'CORS_ORIGINS=.*', "CORS_ORIGINS=https://$domain"
        $envContent = $envContent -replace 'ALLOWED_HOSTS=.*', "ALLOWED_HOSTS=$domain"
        $envContent = $envContent -replace 'WEBAUTHN_RP_ID=.*', "WEBAUTHN_RP_ID=$domain"
        $envContent = $envContent -replace 'WEBAUTHN_ORIGIN=.*', "WEBAUTHN_ORIGIN=https://$domain"
    }
    
    Set-Content .env -Value $envContent -Encoding UTF8
    Write-Success "Environment configured"
} else {
    Write-Warning ".env already exists, skipping configuration"
}

# Build and start
Write-Step 5 8 "Building and starting platform..."

if ($deployNative) {
    # Native deployment on Windows
    Write-Step 5 8 "Setting up Python environment..."
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install --upgrade pip setuptools wheel
    pip install -r src\requirements.txt
    
    # Build frontend
    Write-Step 5 8 "Building frontend..."
    Set-Location web\apps\portal
    npm ci
    npm run build
    Set-Location $installDir
    
    # Setup database
    if ($useSqlite) {
        Write-Step 5 8 "Setting up SQLite database..."
        $sqliteDbPath = "$installDir\plannededucation.db".Replace('\', '/')
        $envContent = Get-Content .env -Raw
        $envContent = $envContent -replace 'DATABASE_URL=.*', "DATABASE_URL=sqlite:///$sqliteDbPath"
        Set-Content .env -Value $envContent -Encoding UTF8
        Write-Success "Configured SQLite: sqlite:///$sqliteDbPath"
    } else {
        Write-Step 5 8 "Setting up PostgreSQL database..."
        $dbName = "plannededucation"
        $dbUser = "plannededucation"
        $dbPass = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
        
        # Create database and user
        & psql -U postgres -c "CREATE USER $dbUser WITH PASSWORD '$dbPass';" 2>$null
        & psql -U postgres -c "CREATE DATABASE $dbName OWNER $dbUser;" 2>$null
        & psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;" 2>$null
        
        # Update .env with database URL
        $envContent = Get-Content .env -Raw
        $envContent = $envContent -replace 'DATABASE_URL=.*', "DATABASE_URL=postgresql+psycopg://$dbUser:$dbPass@localhost:5432/$dbName"
        Set-Content .env -Value $envContent -Encoding UTF8
        
        # Start Redis
        Start-Service redis* -ErrorAction SilentlyContinue
    }
    
    # Initialize database
    Write-Step 6 8 "Initializing database..."
    .\.venv\Scripts\Activate.ps1
    python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
    
    # Create Windows service for backend (using NSSM or scheduled task)
    Write-Step 6 8 "Creating Windows service for backend..."
    $serviceScript = @"
@echo off
cd /d $installDir
call .venv\Scripts\activate.bat
uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000
"@
    Set-Content "$installDir\start_backend.bat" -Value $serviceScript -Encoding ASCII
    
    # Create scheduled task for backend service
    $action = New-ScheduledTaskAction -Execute "$installDir\start_backend.bat" -WorkingDirectory $installDir
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "PlannedEducation-Backend" -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest -Force
    
    # Start the service
    Start-ScheduledTask -TaskName "PlannedEducation-Backend"
    
    # Configure IIS or use a simple reverse proxy
    Write-Step 6 8 "Configuring web server..."
    Write-Warning "For native Windows deployment, you'll need to configure IIS or a reverse proxy manually."
    Write-Host "  Frontend files: $installDir\web\apps\portal\dist"
    Write-Host "  Backend API: http://localhost:8000"
    Write-Host "  See DEPLOY_SIMPLE.md for IIS configuration guide"
    
} else {
    # Docker deployment
    docker compose up -d --build

    # Wait for containers
    Write-Step 6 8 "Waiting for services to start..."
    Start-Sleep -Seconds 20

    # Initialize database
    Write-Step 7 8 "Initializing database..."
    docker compose exec -T backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
}

# Create admin user
Write-Step 7 8 "Creating admin user..."
$adminEmail = Read-Host "Admin email [admin@yourschool.edu]"
if (-not $adminEmail) { $adminEmail = "admin@yourschool.edu" }
$adminUser = Read-Host "Admin username [admin]"
if (-not $adminUser) { $adminUser = "admin" }
$adminName = Read-Host "Admin full name [School Administrator]"
if (-not $adminName) { $adminName = "School Administrator" }
$adminPass = Read-Host "Admin password (min 8 chars) [ChangeMe123!]" -AsSecureString
$adminPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass))
if (-not $adminPass) { $adminPass = "ChangeMe123!" }

if ($deployNative) {
    .\.venv\Scripts\Activate.ps1
    python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(
    email='$adminEmail',
    username='$adminUser',
    full_name='$adminName',
    hashed_password=get_password_hash('$adminPass'),
    role='admin',
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin created: $adminEmail')
print('CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN')
"
} else {
    docker compose exec -T backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(
    email='$adminEmail',
    username='$adminUser',
    full_name='$adminName',
    hashed_password=get_password_hash('$adminPass'),
    role='admin',
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin created: $adminEmail')
print('CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN')
"
}

# Verify deployment
Write-Step 8 8 "Verifying deployment..."

if ($deployNative) {
    $checks = @(
        @{Name="Backend API"; Command="curl -f http://localhost:8000/health"},
        @{Name="Frontend"; Command="curl -f http://localhost/health"},
        @{Name="Database"; Command="psql -U postgres -c 'SELECT 1'"},
        @{Name="Redis"; Command="redis-cli ping"},
        @{Name="Backend Service"; Command="Get-ScheduledTask -TaskName 'PlannedEducation-Backend' -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Ready'}"}
    )
} else {
    $checks = @(
        @{Name="Backend API"; Command="curl -f http://localhost:8000/health"},
        @{Name="Frontend"; Command="curl -f http://localhost/health"},
        @{Name="Database"; Command="docker compose exec -T postgres pg_isready -U postgres"},
        @{Name="Redis"; Command="docker compose exec -T redis redis-cli ping"}
    )
}

$allOk = $true
foreach ($check in $checks) {
    $name = $check.Name
    $cmd = $check.Command
    try {
        $result = Invoke-Expression $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$name: OK"
        } else {
            Write-Error "$name: FAILED"
            $allOk = $false
        }
    } catch {
        Write-Error "$name: FAILED"
        $allOk = $false
    }
}

# Show results
if ($allOk) {
    $protocol = "http"
    $port = ""
    if ($domain -ne "localhost") { $protocol = "https" }
    $url = "${protocol}://${domain}${port}"
    
    Write-Host "`n${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
    Write-Host "${CYAN}${BOLD}║                    DEPLOYMENT SUCCESSFUL!                    ║${RESET}"
    Write-Host "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
    Write-Host "`n${BOLD}Access your platform:${RESET}"
    Write-Host "  🌐 Frontend:  $url"
    Write-Host "  📚 API Docs:  ${protocol}://${domain}:8000/docs"
    Write-Host "  ❤️  Health:    ${protocol}://${domain}:8000/health"
    Write-Host "`n${BOLD}First Login:${RESET}"
    Write-Host "  1. Open $url in your browser"
    Write-Host "  2. Login with your admin credentials"
    Write-Host "  3. ${RED}IMMEDIATELY change your password${RESET} in Settings → Security"
    Write-Host "`n${BOLD}Useful Commands:${RESET}"
    if ($deployNative) {
        Write-Host "  View logs:     Get-ScheduledTask -TaskName 'PlannedEducation-Backend' | Get-ScheduledTaskInfo"
        Write-Host "  Update:        cd $installDir && git pull && .\.venv\Scripts\Activate.ps1 && pip install -r src\requirements.txt && cd web\apps\portal && npm ci && npm run build && Restart-ScheduledTask -TaskName 'PlannedEducation-Backend'"
        Write-Host "  Backup:        pg_dump -U postgres plannededucation | gzip > backup_\$(Get-Date -Format 'yyyyMMdd').sql.gz"
        Write-Host "  Restart:       Restart-ScheduledTask -TaskName 'PlannedEducation-Backend'"
    } else {
        Write-Host "  View logs:     docker compose logs -f backend"
        Write-Host "  Update:        git pull && docker compose build --no-cache && docker compose up -d"
        Write-Host "  Backup:        docker compose exec -T postgres pg_dump -U postgres plannededucation | gzip > backup_\$(Get-Date -Format 'yyyyMMdd').sql.gz"
        Write-Host "  Restart:       docker compose restart"
    }
    Write-Host "`n${BOLD}Next Steps:${RESET}"
    Write-Host "  1. Change admin password immediately"
    Write-Host "  2. Configure Google OAuth (optional) in Settings"
    Write-Host "  3. Add AI API keys in Settings → AI Keys"
    Write-Host "  4. Download SEB config for secure exams"
    Write-Host "  5. Set up daily backups (see DEPLOY_SIMPLE.md)"
    Write-Host "`n${CYAN}Need help? Check DEPLOY_SIMPLE.md or GitHub Issues${RESET}"
} else {
    if ($deployNative) {
        Write-Error "Some services failed to start. Check Task Scheduler for PlannedEducation-Backend"
    } else {
        Write-Error "Some services failed to start. Check logs with: docker compose logs -f"
    }
}