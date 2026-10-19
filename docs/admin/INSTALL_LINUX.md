# Linux Installation & Deployment Guide 🐧

PlannedEducation is a **100% free and open-source**, local-first educational platform and grading companion designed for schools, classrooms, and independent educators.

This guide provides complete instructions for installing and running PlannedEducation on Linux (Ubuntu 22.04 / 24.04 LTS, Debian 12, CentOS / RHEL / Rocky Linux, and Windows Subsystem for Linux - WSL2).

---

## 📋 System Prerequisites

| Component | Minimum Required | Recommended | Notes |
|:---|:---:|:---:|:---|
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 | Ubuntu 24.04 LTS / Debian 12 | 64-bit architecture |
| **Python** | `3.12+` | `3.12` or `3.13` | Include `python3-venv` and `python3-pip` |
| **Node.js** | `20+ LTS` | `20.x` or `22.x LTS` | Required for building the portal frontend |
| **Git** | `2.25+` | Latest package from distro | For versioning and module packages |
| **Database** | SQLite 3.35+ (Built-in) | PostgreSQL 16 + Redis 7 | SQLite works out of the box with zero setup |
| **Docker (Optional)** | Docker Engine 24+ | Latest Docker Engine + Compose v2 | Only needed for containerized deployment |

---

## ⚡ Quick Start: Automated Bash Installer (Recommended)

> 💡 **Need a Helping Hand?**
> - **School IT Administrators / Linux Users**: Run the one-line or local Bash commands below; they configure directories, virtual environments, and services cleanly.
> - **Hands-off AI Coding Agent**: Any free coding assistant with shell access (**VS Code**, **Cursor**, **Devin**, **Claude Code**, etc.) can run `install.sh` for you.
> - **Chat AI Companion**: If you're newer to Linux, open **ChatGPT**, **Claude**, or **Gemini**, paste this link (`https://github.com/ezixen/PlannedEducation`), and ask for step-by-step guidance tailored to your specific Linux distribution!

PlannedEducation includes a production-ready Bash installer (`install.sh`) that checks system requirements, sets up directories, creates isolated virtual environments, generates cryptographically strong secrets, and optionally configures Systemd services.

### Option 1: One-Line Installer
Run the installer directly from your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/ezixen/PlannedEducation/main/install.sh | bash
```

### Option 2: Clone and Run Locally
```bash
git clone https://github.com/ezixen/PlannedEducation.git /opt/plannededucation
cd /opt/plannededucation
chmod +x install.sh
./install.sh
```

### Deployment Mode Selection:
When launched, `install.sh` will prompt you to select a deployment mode:
1. **Mode 1: Single-Server / Local (SQLite + In-Memory Cache)** *(Fastest, zero external database setup)*
2. **Mode 2: Production Server (PostgreSQL + Redis + Systemd)** *(High-concurrency campus deployment)*
3. **Mode 3: Docker Compose** *(Containerized isolation)*

---

## 🤖 AI Agent Deployment & Uninstallation (Linux / WSL)

You can ask any AI coding agent (GitHub Copilot, Antigravity, Claude Code, Cursor) to deploy or uninstall PlannedEducation on Linux or WSL using `install.sh` and `uninstall.sh`.

### Mandatory Human-in-the-Loop Questions for AI Agents
Before an AI agent runs `AUTO_CONFIRM=true ./install.sh`, it **must stop and ask you** to confirm:
1. **Target Installation Directory** (`INSTALL_DIR`, e.g. `/opt/plannededucation` or `/tmp/petest`)
2. **Deployment Mode** (`DEPLOY_MODE`: `1` = SQLite, `2` = PostgreSQL + Redis, `3` = Docker)
3. **School & Superadmin Identity** (`SCHOOL_NAME`, `ADMIN_EMAIL`, `ADMIN_NAME`, `ADMIN_PASSWORD`)
4. **Ports** (`API_PORT` default `8000`, `FRONTEND_PORT` default `5173`, with automatic fallback if in use)

Example command after human confirmation:
```bash
INSTALL_DIR="/opt/plannededucation" \
DEPLOY_MODE="1" \
SCHOOL_NAME="Springfield High School" \
ADMIN_EMAIL="admin@springfield.edu" \
ADMIN_NAME="Principal Skinner" \
ADMIN_PASSWORD="<your-strong-password>" \
AUTO_CONFIRM="true" \
bash ./install.sh
```

### Diagnostic & Error Logs (`<INSTALL_DIR>/logs/`)
Both human operators and AI agents can inspect separated standard and error logs under `<INSTALL_DIR>/logs/`:
- `logs/install.log` & `logs/install_error.log` — installation progress and any errors/warnings
- `logs/backend.log` & `logs/backend_error.log` — structured JSON API logs and isolated error/warning logs (with tracebacks)
- `logs/backend_stdout.log` & `logs/backend_stderr.log` — raw console capture; check these if the backend fails to start
- `logs/frontend.log` & `logs/frontend_error.log` — frontend server output and error logs

### Uninstalling (`uninstall.sh`)
```bash
INSTALL_DIR="/opt/plannededucation" bash ./uninstall.sh
```
- Stops running PlannedEducation processes/services and removes the installation directory.
- Lists all external dependencies (`Python`, `Node.js`, `PostgreSQL`, `Redis`, `Docker`, `Git`) with their status and asks whether you want to review them **one by one** (there is intentionally **no "remove all dependencies"** option).

---

## 🧙 Option B: Interactive Python Deployment Wizard

If Python 3.12+ is already installed on your Linux machine, you can run the interactive wizard:

```bash
python3 scripts/deploy/deploy_wizard.py
```

The wizard guides you through:
1. Checking OS packages, Python version, and database status.
2. Choosing between **Native** or **Docker Compose** deployment.
3. Generating secure `JWT_SECRET_KEY` and Fernet `AI_KEY_MASTER_SECRET`.
4. Domain / IP binding configuration.
5. Building the frontend production assets and applying database migrations.

---

## 🛠️ Option C: Manual Installation (Step-by-Step)

Follow these steps for full manual setup on an Ubuntu/Debian server.

### 1. Install System Dependencies
Update your package index and install the base tools:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl nginx
```

*(Optional for PostgreSQL + Redis):*
```bash
sudo apt install -y postgresql postgresql-contrib redis-server
```

*(Install Node.js 20+ LTS via NodeSource if building the frontend portal on the server):*
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

### 2. Clone the Repository
```bash
sudo git clone https://github.com/ezixen/PlannedEducation.git /opt/plannededucation
sudo chown -R $USER:$USER /opt/plannededucation
cd /opt/plannededucation
```

---

### 3. Set Up Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r src/requirements.txt
```

---

### 4. Build the Frontend Portal
```bash
cd web/apps/portal
npm install
npm run build
cd ../../..
```

---

### 5. Configure Environment Variables (`.env`)
Create your configuration file from the template:

```bash
cp .env.example .env
```

Generate secure cryptographic secrets:
```bash
# Generate 64-byte JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(64))")

# Generate Fernet 32-byte key
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Replace secrets in .env
sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
sed -i "s|AI_KEY_MASTER_SECRET=.*|AI_KEY_MASTER_SECRET=$FERNET_KEY|" .env
```

Edit `.env` to match your network settings:
```env
APP_ENV=production
DEBUG=false
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# SQLite (Zero-config standalone):
DATABASE_URL=sqlite:///./plannededucation.db

# Or PostgreSQL (Multi-user production):
# DATABASE_URL=postgresql://pe_user:yourpassword@localhost:5432/plannededucation

# School domain or server IP
ALLOWED_HOSTS=192.168.1.150,localhost,127.0.0.1
CORS_ORIGINS=http://192.168.1.150:8000,http://localhost:8000
```

---

### 6. Initialize the Database
```bash
source .venv/bin/activate
python3 -m src.plannededucation.db_init
```

---

### 7. Configure Systemd Service (Background Daemon)
To keep PlannedEducation running permanently and restart automatically after system reboots:

Create a systemd service file:
```bash
sudo tee /etc/systemd/system/plannededucation.service > /dev/null << 'EOF'
[Unit]
Description=PlannedEducation School Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/plannededucation
Environment="PATH=/opt/plannededucation/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/plannededucation/.venv/bin/python -m uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

Ensure permissions and enable the service:
```bash
sudo chown -R www-data:www-data /opt/plannededucation
sudo systemctl daemon-reload
sudo systemctl enable --now plannededucation
```

Check service status:
```bash
sudo systemctl status plannededucation
```

---

### 8. Configure Nginx Reverse Proxy (Optional, Recommended for Port 80 / SSL)

Create an Nginx server block:
```bash
sudo tee /etc/nginx/sites-available/plannededucation > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/plannededucation /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🏫 School Local Network (LAN) & Firewall Configuration

1. **Find your server's LAN IP**:
   ```bash
   ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1'
   ```

2. **Open firewall ports**:
   If using UFW (Ubuntu Firewall):
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 8000/tcp
   sudo ufw reload
   ```

3. **Verify from Student / Teacher devices**:
   Open a web browser on any school device connected to the same Wi-Fi or LAN:
   `http://<SERVER_IP>:8000` (or `http://<SERVER_IP>` if Nginx is configured).

---

## ❓ Troubleshooting Common Linux Issues

### 1. `Permission denied` on `/opt/plannededucation`
- **Fix**: Run `sudo chown -R $USER:$USER /opt/plannededucation` during setup, or assign ownership to the service user (`www-data`).

### 2. Python Virtual Environment `ensurepip` Missing
- **Fix**: On Debian/Ubuntu minimal installations, install the venv package:
  ```bash
  sudo apt install -y python3-venv python3-full
  ```

### 3. PostgreSQL Peer Authentication Error
- **Symptom**: `FATAL: Peer authentication failed for user "pe_user"`
- **Fix**: Either use MD5/scram password auth in `/etc/postgresql/16/main/pg_hba.conf`, or switch to Native SQLite mode by setting `DATABASE_URL=sqlite:///./plannededucation.db` in `.env`.

### 4. WebSocket Disconnections during Exams
- **Fix**: Ensure your reverse proxy configuration includes WebSocket upgrade headers (`Upgrade $http_upgrade; Connection "upgrade";`).

---

## 📚 Related Documentation
- [Windows Installation Guide](INSTALL_WINDOWS.md)
- [Installation Compatibility & Requirements Matrix](INSTALL_COMPATIBILITY.md)
- [Master Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Module System & School Federation](../dev/MODULE_SYSTEM.md)
- [Frequently Asked Questions (FAQ)](../user/FAQ.md)

