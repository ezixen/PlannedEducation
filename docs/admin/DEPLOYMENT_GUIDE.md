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

> 💡 **Deployment Options for Every Operator:**
> - **School IT Administrators**: Run the native PowerShell or Bash commands below for an automated deployment in minutes.
> - **Hands-off AI Coding Tools**: Free coding software (**VS Code** with Copilot/Cline/Roo, **Cursor**, **Devin**, **Claude Code**, etc.) can run the automated commands for you.
> - **Free Chat AI Guidance**: Anyone can share this repository link (`https://github.com/ezixen/PlannedEducation`) with **ChatGPT**, **Claude**, or **Gemini** to receive step-by-step guidance in plain English.

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

### Reset Hierarchy (No Email System Required)

| Initiator | Can Reset | Required | Use Case |
|-----------|-----------|----------|----------|
| **Teacher** | Students only | Approved teacher status | Student forgot password right before test |
| **Parent** | Their children only | Active parent-child relationship | Child lost recovery codes or 2FA device |
| **Admin** | Teachers only | Admin privilege | Teacher lost recovery codes or 2FA device |
| **Superadmin** | Teachers + Admins | Superadmin privilege | Admin lost recovery codes or 2FA device |

### How It Works

1. **Initiator** clicks **"⚡ Reset Pwd for Test"** next to the target user's name
2. **Target user** types their email on `/login`
3. System detects the active reset (`PASSWORD_RESET_ACTIVE`), highlights the login card in green, and prompts for a new password
4. **Target user** sets their new password, receives authentication tokens instantly, and enters the test without delay

### Expiration

All password reset links expire **24 hours** after initiation:
- **Email OTP reset**: OTP valid for 24 hours from request time (stated in the email)
- **Teacher/Parent/Admin quick reset**: Reset flag valid for 24 hours from initiation
- After expiration, the reset flag is automatically cleared and a new reset must be requested

### Email-Based Password Reset (When Email System Configured)

If an SMTP email service is configured, users can also use self-service password reset:
1. User clicks **"Forgot password?"** on `/login`
2. Enters their registered email address
3. Receives a 6-digit OTP via email (valid for 24 hours)
4. Enters the OTP on `/login` and sets a new password
5. If email is slow or unavailable, teachers/parents/admins can use the instant quick-reset above as a backup measure

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

---

## 11. School Header Customization (Admin/Superadmin)

Schools can customize the platform header to match their branding. Admins and superadmins can configure:

### Header Display Modes

| Mode | Description |
|------|-------------|
| **text** | Shows the school name as text in the header |
| **image** | Shows a custom header image (URL required) |
| **none** | No header displayed (clean dashboard) |

### API Endpoints

- `GET /admin/school/header` — Get current header settings
- `PUT /admin/school/header` — Update header settings (admin/superadmin only)

### Request Body

```json
{
  "header_display_mode": "text",
  "header_text": "Lincoln High School",
  "header_image_url": null
}
```

or for image mode:

```json
{
  "header_display_mode": "image",
  "header_text": null,
  "header_image_url": "https://school.edu/logo.png"
}
```

---

## 12. Superadmin User Management

Superadmins have one additional function over regular admins: **creating other admins and superadmins**.

### Admin Creation

- **Admins** can create: teachers, students, parents, and other admins
- **Superadmins** can create: everything admins can, plus **other superadmins**

### API Endpoints

- `POST /admin/users` — Create a user (admin or below)
- `POST /admin/users/superadmin` — Create a superadmin (superadmin only)

### Security

Superadmin creation is restricted to existing superadmins only. This prevents privilege escalation by regular admins.

---

## 13. User Password Change (Settings Page)

All users can change their own password from the **Settings** page:

1. Go to **Settings → Personal Details**
2. Enter your **current password**
3. Enter your **new password** twice
4. Click **Save Changes**

The server verifies the current password before accepting the change. This prevents unauthorized password changes if a session is left open.


