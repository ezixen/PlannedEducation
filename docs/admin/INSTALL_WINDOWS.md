# Windows Installation & Deployment Guide 🪟

PlannedEducation is a **100% free and open-source**, local-first educational platform designed for schools, classrooms, and independent educators.

This guide provides complete, step-by-step instructions for installing and running PlannedEducation on Windows (Windows 10, Windows 11, and Windows Server 2016/2019/2022).

---

## 📋 System Prerequisites

| Component | Minimum Required | Recommended | Notes |
|:---|:---:|:---:|:---|
| **Operating System** | Windows 10 (64-bit) / Server 2016 | Windows 11 / Server 2022 | 64-bit architecture |
| **Python** | `3.12+` | `3.12` or `3.13` | Add Python to `PATH` during installation |
| **Node.js** | `20+ LTS` | `20.x` or `22.x LTS` | Required for building the portal frontend |
| **Git** | `2.25+` | Latest Git for Windows | Enables version control and package sharing |
| **PowerShell** | `5.1+` | `7+` or built-in PowerShell 5.1 | Run as Administrator |
| **Docker (Optional)** | Docker Desktop 24+ | Latest Docker Desktop | Only required if choosing containerized mode |

---

## ⚡ Quick Start: Automated PowerShell Installer (Recommended)

PlannedEducation includes a native PowerShell deployment script (`install.ps1`) that automatically checks prerequisites, clones or updates the repository, generates cryptographically secure keys, and configures the environment.

### Step 1: Open PowerShell as Administrator
Right-click on the Windows Start menu button and select **Terminal (Admin)** or **Windows PowerShell (Admin)**.

### Step 2: Run the Installer Script
Execute the following command in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1
```

Or specify a custom installation directory:
```powershell
.\install.ps1 -InstallDir "C:\PlannedEducation"
```

### Step 3: Choose Your Deployment Mode
When prompted by the installer:
1. **Mode 1: Single-Server / Local (SQLite + In-Memory Cache)** *(Fastest, zero external database setup)*
2. **Mode 2: Production Server (PostgreSQL + Redis)** *(High-concurrency campus deployment)*
3. **Mode 3: Docker Compose** *(Full containerized isolation)*

---

## 🤖 AI Agent Deployment & Uninstallation (Windows)

You can ask any AI coding agent (GitHub Copilot, Antigravity, Claude Code, Cursor) to deploy or uninstall PlannedEducation on Windows using `install.ps1` and `uninstall.ps1`.

### Mandatory Human-in-the-Loop Questions for AI Agents
Before an AI agent runs `install.ps1 -AutoConfirm`, it **must stop and ask you** to confirm:
1. **Target Installation Directory** (`-InstallDir`, e.g. `C:\PlannedEducation` or `D:\dev\PEtest`)
2. **Deployment Mode** (`-DeployMode`: `1` = SQLite, `2` = PostgreSQL + Redis, `3` = Docker)
3. **School & Superadmin Identity** (`-SchoolName`, `-AdminEmail`, `-AdminName`, `-AdminPassword`)
4. **Ports** (`-ApiPort` default `8000`, `-FrontendPort` default `5173`, with automatic fallback if in use)

Example command after human confirmation:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 `
  -InstallDir "D:\dev\PEtest" `
  -DeployMode "1" `
  -SchoolName "Springfield High School" `
  -AdminEmail "admin@springfield.edu" `
  -AdminName "Principal Skinner" `
  -AdminPassword "<your-strong-password>" `
  -AutoConfirm
```

### Diagnostic & Error Logs (`<InstallDir>\logs\`)
Both human operators and AI agents can inspect separated standard and error logs under `<InstallDir>\logs\`:
- `logs\install.log` & `logs\install_error.log` — installation progress and any errors/warnings
- `logs\backend.log` & `logs\backend_error.log` — structured JSON API logs and isolated error/warning logs (with tracebacks)
- `logs\backend_stdout.log` & `logs\backend_stderr.log` — raw console capture; check these if the backend fails to start
- `logs\frontend.log` & `logs\frontend_error.log` — frontend server output and error logs

### Uninstalling (`uninstall.ps1`)
```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1 -InstallDir "C:\PlannedEducation"
```
- Stops running PlannedEducation processes/services and removes the installation directory.
- Lists all external dependencies (`Python`, `Node.js`, `PostgreSQL`, `Redis`, `Docker`, `Git`) with their status and asks whether you want to review them **one by one** (there is intentionally **no "remove all dependencies"** option).

---

## 🧙 Option B: Interactive Python Deployment Wizard

If you already have Python installed, you can use the cross-platform interactive wizard:

```powershell
python scripts\deploy\deploy_wizard.py
```

The wizard will:
1. Detect system environment, Python version, and available database engines.
2. Prompt you to choose between **Native** or **Docker Compose** mode.
3. Automatically generate secure random secrets:
   - 64-byte hexadecimal `JWT_SECRET_KEY`
   - Fernet 32-byte URL-safe base64 `AI_KEY_MASTER_SECRET`
4. Guide you through domain setup (`localhost` for single-PC or your school IP / hostname).
5. Build the frontend and initialize database tables.

---

## 🛠️ Option C: Manual Installation (Step-by-Step)

If you prefer full control over every component without using automated scripts, follow these manual steps.

### 1. Clone the Repository
```powershell
git clone https://github.com/ezixen/PlannedEducation.git C:\PlannedEducation
cd C:\PlannedEducation
```

### 2. Set Up Python Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install core backend dependencies
python -m pip install --upgrade pip
pip install -r src/requirements.txt
```

### 3. Build the Frontend Portal
```powershell
cd web\apps\portal

# Install NPM dependencies
npm install

# Build production bundle
npm run build

# Return to root directory
cd ..\..\..
```

### 4. Create and Configure the Environment File (`.env`)
Copy the template configuration file:
```powershell
Copy-Item .env.example .env
```

Generate secure cryptographic keys in PowerShell:
```powershell
# Generate JWT Secret
$jwtSecret = [System.Convert]::ToHexString((1..64 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 256) }))

# Generate Fernet Master Secret
$fernetKey = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Write-Host "JWT Secret: $jwtSecret"
Write-Host "Fernet Key: $fernetKey"
```

Edit your `.env` file and set the generated values:
```env
APP_ENV=production
DEBUG=false
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
JWT_SECRET_KEY=<your_generated_jwt_secret>
AI_KEY_MASTER_SECRET=<your_generated_fernet_key>

# For SQLite Standalone (default zero-config):
DATABASE_URL=sqlite:///./plannededucation.db

# Or for PostgreSQL:
# DATABASE_URL=postgresql://pe_user:yourpassword@localhost:5432/plannededucation
```

### 5. Initialize the Database
```powershell
# Apply database schemas
python -m src.plannededucation.db_init
```

### 6. Run the Application Server
```powershell
# Start FastAPI backend server
python -m uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000
```

Access the portal in your browser:
- **Web Portal / Teacher Dashboard**: `http://localhost:8000` (or `http://localhost:5173` in development)
- **API Documentation & Health Check**: `http://localhost:8000/docs` or `http://localhost:8000/health`

---

## 🏫 School Local Network (LAN) Configuration

To allow teachers and students on classroom Wi-Fi or wired Ethernet to access PlannedEducation:

1. **Find your server's local IP address**:
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet' } | Select-Object IPAddress
   ```
   *(Example: `192.168.1.150`)*

2. **Allow inbound traffic in Windows Firewall**:
   Run in PowerShell (Admin):
   ```powershell
   New-NetFirewallRule -DisplayName "PlannedEducation Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

3. **Update `.env` configuration**:
   Set `ALLOWED_HOSTS` and `CORS_ORIGINS`:
   ```env
   ALLOWED_HOSTS=192.168.1.150,localhost,127.0.0.1
   CORS_ORIGINS=http://192.168.1.150:8000,http://localhost:8000
   ```

4. **Connect from Student & Teacher Laptops**:
   Students and teachers simply open their browser and navigate to:
   `http://192.168.1.150:8000`

---

## 🔧 Running as a Windows Background Service

To ensure PlannedEducation stays running in the background and restarts automatically on system boot:

### Using Windows Task Scheduler:
Run in PowerShell (Admin):
```powershell
$action = New-ScheduledTaskAction -Execute "C:\PlannedEducation\.venv\Scripts\python.exe" `
    -Argument "-m uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000" `
    -WorkingDirectory "C:\PlannedEducation"

$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "PlannedEducationServer" -Action $action -Trigger $trigger -Principal $principal
```

To start the task immediately:
```powershell
Start-ScheduledTask -TaskName "PlannedEducationServer"
```

---

## ❓ Troubleshooting Common Windows Issues

### 1. `ExecutionPolicy` Error
- **Symptom**: `File install.ps1 cannot be loaded because running scripts is disabled on this system.`
- **Fix**: Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before executing the script.

### 2. Port 8000 Already in Use
- **Symptom**: `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`
- **Fix**: Check what process is using port 8000:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
  ```
  Change `SERVER_PORT=8002` in `.env` and start again.

### 3. Missing C++ Build Tools for Python Packages
- **Symptom**: `error: Microsoft Visual C++ 14.0 or greater is required.`
- **Fix**: PlannedEducation uses pre-compiled wheels for all core dependencies (`cryptography`, `argon2-cffi`, `psycopg2-binary`). If an issue occurs, make sure you are running a supported Python version (`3.12` or `3.13` 64-bit) and run `python -m pip install --upgrade pip setuptools wheel`.

---

## 📚 Related Documentation
- [Linux Installation Guide](INSTALL_LINUX.md)
- [Installation Compatibility & Requirements Matrix](INSTALL_COMPATIBILITY.md)
- [Master Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Module System & School Federation](../dev/MODULE_SYSTEM.md)
- [Frequently Asked Questions (FAQ)](../user/FAQ.md)

