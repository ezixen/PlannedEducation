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

# Check requirements
Write-Step 1 8 "Checking requirements..."

$checksPassed = $true
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

if (-not $checksPassed) {
    Write-Error "Please install missing requirements and try again."
    Write-Host "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
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
    $envContent = $envContent -replace 'AI_KEY_MASTER_SECRET=.*', "AI_KEY_MASTER_SECRET=$fernetKey"
    $envContent = $envContent -replace 'POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
    
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

# Create admin user
Write-Step 8 8 "Creating admin user..."
$adminEmail = Read-Host "Admin email [admin@yourschool.edu]"
if (-not $adminEmail) { $adminEmail = "admin@yourschool.edu" }
$adminUser = Read-Host "Admin username [admin]"
if (-not $adminUser) { $adminUser = "admin" }
$adminName = Read-Host "Admin full name [School Administrator]"
if (-not $adminName) { $adminName = "School Administrator" }
$adminPass = Read-Host "Admin password (min 8 chars) [ChangeMe123!]" -AsSecureString
$adminPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass))
if (-not $adminPass) { $adminPass = "ChangeMe123!" }

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

# Verify deployment
Write-Step 8 8 "Verifying deployment..."
$checks = @(
    @{Name="Backend API"; Command="curl -f http://localhost:8000/health"},
    @{Name="Frontend"; Command="curl -f http://localhost/health"},
    @{Name="Database"; Command="docker compose exec -T postgres pg_isready -U postgres"},
    @{Name="Redis"; Command="docker compose exec -T redis redis-cli ping"}
)

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
    Write-Host "  View logs:     docker compose logs -f backend"
    Write-Host "  Update:        git pull && docker compose build --no-cache && docker compose up -d"
    Write-Host "  Backup:        docker compose exec -T postgres pg_dump -U postgres plannededucation | gzip > backup_\$(Get-Date -Format 'yyyyMMdd').sql.gz"
    Write-Host "  Restart:       docker compose restart"
    Write-Host "`n${BOLD}Next Steps:${RESET}"
    Write-Host "  1. Change admin password immediately"
    Write-Host "  2. Configure Google OAuth (optional) in Settings"
    Write-Host "  3. Add AI API keys in Settings → AI Keys"
    Write-Host "  4. Download SEB config for secure exams"
    Write-Host "  5. Set up daily backups (see DEPLOY_SIMPLE.md)"
    Write-Host "`n${CYAN}Need help? Check DEPLOY_SIMPLE.md or GitHub Issues${RESET}"
} else {
    Write-Error "Some services failed to start. Check logs with: docker compose logs -f"
}