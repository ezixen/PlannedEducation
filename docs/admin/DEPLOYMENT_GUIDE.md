# PlannedEducation — Master Deployment & Administration Guide 🚀

> Canonical deployment, infrastructure, and systems administration manual.
> Merges and unifies all deployment modes: Simple School Setup, Native Production, and Docker Containers.

---

## Table of Contents
1. [Architecture & Deployment Modes](#1-architecture--deployment-modes)
2. [Automated Installation (Windows & Linux/WSL)](#2-automated-installation-windows--linuxwsl)
3. [Docker Container Deployment](#3-docker-container-deployment)
4. [Native Production Deployment (PostgreSQL + Systemd)](#4-native-production-deployment-postgresql--systemd)
5. [Server-Side Editable Configuration (`config/deployment.json`)](#5-server-side-editable-configuration-configdeploymentjson)
6. [Database Backups & Automated Midnight Scheduler](#6-database-backups--automated-midnight-scheduler)
7. [Security Safeguards, Brute-Force Lockout & Account Hardening](#7-security-safeguards-brute-force-lockout--account-hardening)
8. [Teacher Verification, Approvals & User Roles](#8-teacher-verification-approvals--user-roles)
9. [Pre-Exam Emergency Classroom Password Reset](#9-pre-exam-emergency-classroom-password-reset)
10. [SSL Certificates, Reverse Proxy & Maintenance](#10-ssl-certificates-reverse-proxy--maintenance)

---

## 1. Architecture & Deployment Modes

PlannedEducation is a 100% free, open-source, local-first assessment platform. It operates in 3 distinct modes depending on school size and infrastructure capabilities:

| Mode | Database | Cache | Best For | Prerequisites |
|---|---|---|---|---|
| **Mode 1: Lightweight / Evaluation** | SQLite (`plannededucation.db`) | In-Memory | Single classrooms, laptop test stations, quick trials | Python 3.12+, Node.js 20+ |
| **Mode 2: Native Self-Hosted** | PostgreSQL (Dedicated) | Redis | Full school networks, multi-grade deployments, bare-metal servers | Python, Node.js, PostgreSQL, Redis |
| **Mode 3: Containerized (Docker)** | PostgreSQL (Container) | Redis (Container) | Production school servers, cloud VMs (Cloudflare/Hobby VPS) | Docker & Docker Compose |

---

## 2. Automated Installation (Windows & Linux/WSL)

PlannedEducation features smart, automated installers that automatically detect dependencies, probe available network ports, configure services, and verify system health.

### Windows Installation
Run from PowerShell (as Administrator):
```powershell
# Interactive installation (prompts for options):
powershell -ExecutionPolicy Bypass -File .\install.ps1

# Automated / AI Agent installation (preserves admin password prompt):
powershell -ExecutionPolicy Bypass -File .\install.ps1 -AutoConfirm
```

### Linux / WSL Installation
Run from Bash (with sudo privileges):
```bash
# Interactive installation:
chmod +x ./install.sh
./install.sh

# Automated / AI Agent installation:
AUTO_CONFIRM=true ./install.sh
```

### AI Agent Deployment Contract & Admin Safeguard
- Even when running in automated `-AutoConfirm` mode, the installer **stops and requires setting a secure administrator password** if left default.
- The installer generates **5 one-time administrator recovery codes**, displays them in the console, and writes them with a critical warning into `ADMIN_CREDENTIALS.txt`:
  > *"Keep these safe (print or write them down). If you lose both your password and recovery codes, you will be locked out and will need to redeploy the whole system, as database injection is not an option."*

---

## 3. Docker Container Deployment

### 1. Copy Environment Template
```bash
cp .env.example .env
```

### 2. Generate Secrets
```bash
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(64))"
python3 -c "from cryptography.fernet import Fernet; print('AI_KEY_MASTER_SECRET=' + Fernet.generate_key().decode())"
```

### 3. Launch Containers
```bash
docker compose up -d --build
```

### 4. Verify Services
```bash
docker compose ps
curl http://localhost:8000/health
```

---

## 4. Native Production Deployment (PostgreSQL + Systemd)

### 1. Backend Service (`/etc/systemd/system/plannededucation-backend.service`)
```ini
[Unit]
Description=PlannedEducation FastAPI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=plannededucation
WorkingDirectory=/opt/plannededucation
ExecStart=/opt/plannededucation/.venv/bin/uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
EnvironmentFile=/opt/plannededucation/.env

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now plannededucation-backend
```

---

## 5. Server-Side Editable Configuration (`config/deployment.json`)

Post-deployment configurations (domains, ports, CORS origins, and SMTP settings) are stored in a dedicated server-side file:
`config/deployment.json`

### Why This Matters
- **No Need to Redeploy:** If your school's domain, hostname, IP address, or network layout changes, you **do not** need to rebuild Docker images or rerun installers.
- **Direct Server Editing:** Server administrators can edit `config/deployment.json` using `nano` or `vim`.
- **Browser-Based Admin Panel:** Administrators can navigate to **Admin Dashboard → ⚙️ Deployment & Network** to update domain names, ports, and email settings.
- **Backup Config File:** The Admin Panel features a **"📁 Backup Config File"** button to export and save a local copy of your configuration.
- **Applying Changes:** Restart backend services (`docker compose restart` or `sudo systemctl restart plannededucation-backend`) to activate modifications.

---

## 6. Database Backups & Automated Midnight Scheduler

### Native Midnight Auto-Backup Scheduler
The backend includes a built-in background scheduler that runs automatically while the server is active:
- **Schedule:** Runs every night at **00:00 UTC**.
- **Retention:** Automatically prunes backup archives older than **30 days**.
- **Transactional Consistency:**
  - SQLite: Uses atomic `sqlite3.connect().backup()` to prevent database locking during backups.
  - PostgreSQL: Uses compressed `pg_dump` with gzip.

### Manual On-Demand Snapshots
Administrators can trigger an instant backup snapshot anytime from **Admin Dashboard → 💾 Database Backups** and download archives directly through the browser.

---

## 7. Security Safeguards, Brute-Force Lockout & Account Hardening

### Brute-Force Account Protection
- **Threshold:** 5 consecutive failed login attempts automatically locks the account for **15 minutes**.
- **Lockout Reset:** Authorized teachers and administrators can unlock locked students instantly.

### Administrator Account Protection
- Administrator accounts are strictly protected against modification, deactivation, or password resets by non-superadmins (returns HTTP 403 Forbidden).
- Database injection is prevented via fully parameterized ORM queries.

---

## 8. Teacher Verification, Approvals & User Roles

### Self-Registration Rules
1. **Students, Teachers, and Parents** can self-register at `/register`.
2. **Administrators CANNOT self-register** (restricted via API and UI).

### Teacher Approval Gate
- To prevent students from registering as teachers and viewing upcoming exams or answer keys, all self-registered teachers are created with `teacher_approved = False`.
- While pending approval, teachers cannot create, edit, or publish exams.
- System administrators receive an **in-platform notification** and can approve or deny requests with **one click** under **Admin Dashboard → 🎓 Teacher Approvals**.

---

## 9. Pre-Exam Emergency Classroom Password Reset

Right before an exam, students who forget their credentials can be unlocked immediately by their teacher:
1. Teacher clicks **"⚡ Reset Pwd for Test"** in their classroom roster or live exam monitoring.
2. Student types their email on `/login`.
3. System detects the teacher reset (`TEACHER_RESET_ACTIVE`), highlights the login card in green, and prompts the student to enter their new password.
4. The student sets their new password, receives authentication tokens instantly, and enters the test without delay.

---

## 10. SSL Certificates, Reverse Proxy & Maintenance

### Nginx Reverse Proxy & Let's Encrypt SSL
```nginx
server {
    listen 80;
    server_name exam.yourschool.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name exam.yourschool.edu;

    ssl_certificate /etc/letsencrypt/live/exam.yourschool.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exam.yourschool.edu/privkey.pem;

    location / {
        root /opt/plannededucation/web/apps/portal/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
Obtain free TLS certificate:
```bash
sudo certbot --nginx -d exam.yourschool.edu
```

