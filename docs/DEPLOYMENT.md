# PlannedEducation — Deployment & Administration Guide

Complete guide to deploying, configuring, and administering PlannedEducation for schools.

## Table of Contents

1. [Overview](#1-overview)
2. [Deployment Modes](#2-deployment-modes)
3. [Prerequisites](#3-prerequisites)
4. [Installation (Windows & Linux)](#4-installation-windows--linux)
5. [Docker Deployment](#5-docker-deployment)
6. [Post-Installation Configuration](#6-post-installation-configuration)
7. [School Header Customization](#7-school-header-customization)
8. [User Management & Roles](#8-user-management--roles)
9. [Password Reset System](#9-password-reset-system)
10. [Database Backups](#10-database-backups)
11. [Security & SSL](#11-security--ssl)
12. [Maintenance & Troubleshooting](#12-maintenance--troubleshooting)

---

## 1. Overview

PlannedEducation is a **100% free, open-source, local-first** assessment platform for schools. It operates entirely in the browser — students, teachers, and parents access it via any modern web browser at your school's domain. No client software installation is required.

The platform consists of:
- **Backend API** (FastAPI, Python) — port 8000
- **Frontend Portal** (React, Vite) — port 5173
- **Database** — SQLite (Mode 1) or PostgreSQL (Mode 2/3)
- **Cache** — In-memory (Mode 1) or Redis (Mode 2/3)

---

## 2. Deployment Modes

| Mode | Database | Cache | Best For | Prerequisites |
|------|----------|-------|----------|---------------|
| **Mode 1: Lightweight / Evaluation** | SQLite | In-Memory | Single classrooms, laptop test stations, quick trials | Git, Python 3.12+, Node.js 20+ |
| **Mode 2: Native Self-Hosted** | PostgreSQL | Redis | Full school networks, multi-grade deployments | Git, Python, Node.js, PostgreSQL, Redis |
| **Mode 3: Containerized (Docker)** | PostgreSQL (Container) | Redis (Container) | Production school servers, cloud VMs | Docker & Docker Compose |

**Mode 1** is recommended for most schools — it requires zero database server setup and works out of the box.

---

## 3. Prerequisites

### Required (all modes)

| Dependency | Purpose |
|------------|---------|
| **Git** | Source control (clone repository) |
| **Python 3.12+** | Backend runtime (FastAPI, SQLAlchemy) |
| **Node.js 20+** | Frontend build tooling (Vite, npm) |
| **npm** | Bundled with Node.js |

### Optional (mode-specific)

| Dependency | Required For | Notes |
|------------|--------------|-------|
| **PostgreSQL** | Mode 2 only | Production database server |
| **Redis** | Mode 2 only | Production cache & WebSocket pub/sub |
| **Docker Desktop** | Mode 3 only | Containerized deployment |

**Mode 1 works with just Git, Python, and Node.js** — no database server needed.

---

## 4. Installation (Windows & Linux)

### Windows (PowerShell)

```powershell
# Clone the repository
git clone https://github.com/ezixen/PlannedEducation.git C:\PlannedEducation
cd C:\PlannedEducation

# Run the installer (as Administrator)
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### Linux / WSL (Bash)

```bash
# Clone the repository
git clone https://github.com/ezixen/PlannedEducation.git /opt/plannededucation
cd /opt/plannededucation

# Make executable and run
chmod +x ./install.sh
./install.sh
```

### Automated / AI Agent Installation

Both installers support non-interactive mode:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\install.ps1 -AutoConfirm
```

```bash
# Linux
AUTO_CONFIRM=true ./install.sh
```

**AI Agent Contract**: When running with `-AutoConfirm`, the installer stops and requires you to confirm:
1. Target installation directory
2. Deployment mode (1=SQLite, 2=PostgreSQL+Redis, 3=Docker)
3. Initial superadmin identity (email, name, password, school name)
4. Domain and ports

### Security: Credentials Not Saved to Disk

For security, the superadmin password and 5 emergency recovery codes are **copied to your clipboard** during installation — they are NOT saved to any file on disk. Paste them into a password manager or print them immediately. If lost, you will be permanently locked out.

---

## 5. Docker Deployment

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Generate secrets
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(64))"
python3 -c "from cryptography.fernet import Fernet; print('AI_KEY_MASTER_SECRET=' + Fernet.generate_key().decode())"

# 3. Launch containers
docker compose up -d --build

# 4. Verify
docker compose ps
curl http://localhost:8000/health
```

---

## 6. Post-Installation Configuration

After installation, access the platform at:
- **Frontend**: `http://<your-school-domain>:5173`
- **Backend API**: `http://<your-school-domain>:8000`
- **API Docs**: `http://<your-school-domain>:8000/docs` (development only)

### Domain Setup

Configure your school's domain or subdomain (e.g., `exam.yourschool.edu`) to point to the server IP. Use Let's Encrypt for free HTTPS certificates.

### Configuration File

Edit `config/deployment.json` directly on the server, or use **Admin Dashboard → ⚙️ Deployment & Network** to update domain names, ports, and optional SMTP settings. Restart backend services to apply changes.

---

## 7. School Header Customization

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

### Example Request

```json
{
  "header_display_mode": "text",
  "header_text": "Lincoln High School",
  "header_image_url": null
}
```

Or for image mode:

```json
{
  "header_display_mode": "image",
  "header_text": null,
  "header_image_url": "https://school.edu/logo.png"
}
```

---

## 8. User Management & Roles

### Roles

| Role | Can Create | Can Reset Passwords | Notes |
|------|------------|---------------------|-------|
| **Student** | — | — | Takes exams |
| **Teacher** | Exams, classes | Students only | Requires admin approval |
| **Parent** | — | Their children only | Requires active parent-child relationship |
| **Admin** | Users, exams | Teachers only | Admin privilege |
| **Superadmin** | Users, admins, superadmins | Teachers + Admins | Superadmin privilege |

### Creating Users

- **Admins** can create: teachers, students, parents, and other admins (`POST /admin/users`)
- **Superadmins** can create: everything admins can, plus **other superadmins** (`POST /admin/users/superadmin`)

Superadmin creation is restricted to existing superadmins only to prevent privilege escalation.

### Teacher Approval

Self-registered teachers require one-click administrator approval before gaining exam creation rights. Admins approve/deny under **Admin Dashboard → 🎓 Teacher Approvals**.

---

## 9. Password Reset System

PlannedEducation offers multiple password reset paths — no email server required:

### Reset Hierarchy

| Initiator | Can Reset | Required | Expiration |
|-----------|-----------|----------|------------|
| **Teacher** | Students only | Approved teacher | 24 hours |
| **Parent** | Their children only | Active parent-child relationship | 24 hours |
| **Admin** | Teachers only | Admin privilege | 24 hours |
| **Superadmin** | Teachers + Admins | Superadmin privilege | 24 hours |
| **Self (Email)** | Own account | Registered email + OTP | 24 hours |

### How Quick Reset Works

1. **Initiator** clicks **"⚡ Reset Pwd for Test"** next to the target user's name
2. **Target user** types their email on `/login`
3. System detects the active reset, highlights the login card in green, and prompts for a new password
4. **Target user** sets their new password and enters the test immediately

### Email-Based Reset (Optional)

If SMTP email is configured:
1. User clicks **"Forgot password?"** on `/login`
2. Enters their registered email address
3. Receives a 6-digit OTP via email (valid for 24 hours)
4. Enters the OTP and sets a new password

Email is 100% optional. If unconfigured, the platform operates in offline mode and logs OTP codes safely.

### User Password Change (Settings Page)

All users can change their own password from **Settings → Personal Details**:
1. Enter your **current password**
2. Enter your **new password** twice
3. Click **Save Changes**

The server verifies the current password before accepting the change.

---

## 10. Database Backups

### Native Auto-Backup (Built-In)

PlannedEducation includes a background backup scheduler:
- **Automated Schedule**: Daily at 00:00 UTC while the server is active
- **Automated Retention**: Archives older than 30 days are automatically pruned
- **Admin Dashboard**: Create instant snapshots anytime via **Admin Dashboard → 💾 Database Backups**

### Supported Engines

- **SQLite**: Uses atomic `sqlite3.connect().backup()` (no table locks)
- **PostgreSQL**: Uses compressed `pg_dump`

### Manual Backup

```bash
# Trigger via API
curl -X POST http://localhost:8000/admin/database/backup \
  -H "Authorization: Bearer <token>"

# List backups
curl http://localhost:8000/admin/database/backups \
  -H "Authorization: Bearer <token>"
```

---

## 11. Security & SSL

### Security Features

- **Argon2id** password hashing (OWASP recommended)
- **Rate limiting** on auth endpoints (10/min register, 20/min login, 5/min reset)
- **Brute-force lockout** (5 failed attempts = 15 min lockout)
- **JWT** with 30-minute expiry and refresh tokens
- **Fernet encryption** for AI API keys at rest
- **Microsoft Presidio** PII scrubbing for anonymizer
- **Security headers** (CSP, HSTS, X-Frame-Options, etc.)
- **CORS** with explicit allow-list (no wildcard)

### SSL/TLS

Use Let's Encrypt for free HTTPS certificates:

```nginx
server {
    listen 443 ssl http2;
    server_name exam.yourschool.edu;
    ssl_certificate /etc/letsencrypt/live/exam.yourschool.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exam.yourschool.edu/privkey.pem;
    # ... proxy config to backend:8000 and frontend:5173
}
```

```bash
sudo certbot --nginx -d exam.yourschool.edu
```

---

## 12. Maintenance & Troubleshooting

### Service Management

```powershell
# Windows
.\start_all.ps1    # Start platform
.\stop_all.ps1     # Stop platform
.\verify.ps1       # Verify health
```

```bash
# Linux
./start_all.sh
./stop_all.sh
./verify.sh
```

### Logs

All logs are written to `<InstallDir>/logs/`:
- `install.log` / `install_error.log` — Installation
- `backend.log` / `backend_error.log` — Backend API
- `frontend.log` / `frontend_error.log` — Frontend

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Installer auto-detects and uses alternative free ports |
| Redis not found | Mode 1 works without Redis; install Redis only for Mode 2 |
| Admin locked out | Use one of 5 emergency recovery codes |
| Frontend not loading | Check that backend is running on port 8000 |

---

## Support

- **School IT Administrators**: Run the automated installer directly
- **AI Coding Agents**: Can run `install.ps1` / `install.sh` for you
- **Free Chat AI**: Share the GitHub repository link with ChatGPT, Claude, or Gemini for step-by-step guidance
