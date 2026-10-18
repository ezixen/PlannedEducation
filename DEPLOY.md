# PlannedEducation - Deployment Guide

## Overview
This guide explains how to deploy PlannedEducation on a school server with minimal IT expertise. The platform is designed for **zero-cost operation** using free-tier services and self-hosted infrastructure.

---

## Prerequisites

### Hardware Requirements (Minimum)
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements
- Docker 24+ and Docker Compose v2
- Git
- Domain name (optional, for HTTPS)
- SSL certificates (Let's Encrypt recommended)

### Network Requirements
- Port 80/443 open for HTTP/HTTPS
- Port 5432 for PostgreSQL (internal only)
- Port 6379 for Redis (internal only)
- Outbound internet for AI providers, SEB validation, updates

---

## Quick Start (5 Minutes)

### 1. Clone Repository
```bash
git clone https://github.com/ezixen/PlannedEducation.git
cd PlannedEducation
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit with your settings (see Configuration section below)
nano .env
```

### 3. Start Platform
```bash
docker-compose up -d
```

### 4. Initialize Database
```bash
# Wait for containers to start (10-15 seconds)
sleep 15

# Run database migrations
docker-compose exec backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

### 5. Create First Admin
```bash
docker-compose exec backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash

db = SessionLocal()
admin = User(
    email='admin@yourschool.edu',
    username='admin',
    full_name='School Administrator',
    hashed_password=get_password_hash('ChangeMe123!'),
    role='admin',
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin created: admin@yourschool.edu / ChangeMe123!')
print('CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN')
"
```

### 5. Access Platform
- **Frontend**: http://localhost:5173 (or your domain)
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: Login as admin → "Admin Dashboard" in sidebar

---

## Post-Deployment Configuration & Network Layout (`config/deployment.json`)

PlannedEducation stores post-deployment network configurations in a server-side JSON file:
`config/deployment.json`

### Why This Matters for Administrators
- **No Need to Redeploy:** If your school's domain, hostname, IP address, frontend/backend ports, or network topology changes after deployment, you **do not** need to redeploy the platform or rebuild containers.
- **Direct Server Editing:** Server administrators with shell access can edit `config/deployment.json` directly using `nano`, `vim`, or any text editor.
- **Admin Panel UI Editing:** Administrators can also log in, navigate to **Admin Dashboard → ⚙️ Deployment & Network**, and adjust settings directly in the browser.
- **Applying Changes:** After modifying `config/deployment.json` (or saving in the Admin Panel), simply restart the platform services to apply the new settings:
  ```bash
  # Docker deployment:
  docker-compose restart
  # Systemd / Bare-metal deployment:
  sudo systemctl restart plannededucation-backend
  ```
- **Backup Config File:** The Admin Panel includes a **"📁 Backup Config File"** button allowing administrators to export and save their configuration to a custom folder or local backup location at any time.

---

## User Self-Registration, Roles & Security Safeguards

### Self-Registration Rules
1. **Students, Teachers, and Parents** can self-register directly through the web portal (`/register`).
2. **Administrators CANNOT self-register.** Administrator accounts can only be created by an existing administrator via the Admin Panel or during initial deployment using the CLI creation command.

### Teacher Approval & Exam Security
To prevent students from prank-registering as teachers and gaining access to tomorrow's test questions or exam modules:
- Any self-registered teacher account is created with `teacher_approved = False`.
- While pending approval, the user **cannot create, publish, or view exams, questions, or curriculum modules**.
- When a teacher registers, an **instant In-Platform Notification** is dispatched to all system administrators.
- Administrators can review and approve or deny teacher privileges with **one click** from the Notification Bell or the Admin Dashboard under **🎓 Teacher Approvals**.
- Once approved, the teacher receives an in-app confirmation and full access is granted immediately.

### One-Time Password Reset Recovery Codes (Self-Service)
- Every user is presented with **5 single-use recovery codes** immediately upon registration.
- Users are instructed to print or securely save these codes.
- **Immediate Self-Reset:** If a user forgets their password, the platform prompts them: *"Unless you ran out of codes, you can reset your password immediately without waiting for anyone's help!"* Entering their email and one unused recovery code resets their password instantly.
- **Admin Emergency Backup Codes:** System administrators must print or save emergency backup codes (available in Admin Dashboard → 🛡️ Emergency Backup Codes). This guarantees that administrators never lose access to system oversight even if they lose their password or 2FA authenticator.

### In-Platform Password Reset Requests (No Email Required)
If a user runs out of recovery codes:
- **Students** can submit an in-platform password reset request to their linked **Teacher** or **Parent**.
- **Teachers** can submit an in-platform password reset request to a school **Administrator**.
- The designated supervisor receives a notification in their **Notification Bell** with a one-click button to approve the request and generate a secure temporary password.
- **Optional Outgoing Email (SMTP):** If the school configures SMTP settings, an email notification is also sent. If SMTP is not configured, the platform operates 100% locally with internal notifications.

### Teacher Classroom Emergency Password Reset ("⚡ Reset Pwd for Test")
Right before an exam, students often forget their credentials and cannot log in under time pressure:
- Teachers can unlock the student with a single click: click **"⚡ Reset Pwd for Test"** in the student roster (**Teacher Dashboard → Real-time Monitoring** or **Classes → Manage Students**).
- When the student enters their email on the login screen (`/login`), the system automatically detects the teacher reset (`TEACHER_RESET_ACTIVE`), highlights the form in green, and prompts for a new password right in the login card.
- Upon typing their new password and clicking **"Set Password & Sign In"**, the student is immediately authenticated and admitted directly into the test session without needing to wait for emails or recovery codes.

### Database Backups & Midnight Auto-Backup
- **Immediate Manual Snapshot:** Administrators can trigger an instant database backup snapshot from **Admin Dashboard → 💾 Database Backups**.
- **Automated Midnight Auto-Backup:** The background scheduler runs daily at **00:00 UTC**, taking an atomic snapshot of the database and applying an automatic 30-day retention pruning policy.
- **Safe Transactional Backups:**
  - SQLite mode uses atomic `sqlite3.connect().backup()` to eliminate lock contention.
  - PostgreSQL mode uses compressed `pg_dump` with gzip.
- **Secure File Management:** Backups are protected against path traversal, stored in the server's backup directory, and can be downloaded or purged by authorized administrators with full audit logging.

### Cybersecurity Safeguards & Brute-Force Lockout
- **Brute-Force Account Protection:** 5 consecutive failed login attempts automatically locks the account for 15 minutes to defeat automated password cracking and brute-force attacks.
- **Protected Administrator Accounts:** Administrator accounts cannot be modified, deactivated, or reset by non-superadmins.
- **Installer Admin Password & Recovery Warning:** During installation (`install.ps1` / `install.sh`), even with `-AutoConfirm` / `AUTO_CONFIRM=true`, the installer stops and prompts to set a secure administrator password if default. The installer generates 5 one-time recovery codes, displays them on the console, and writes them with a critical warning banner into `ADMIN_CREDENTIALS.txt`:
  > *"Keep these safe (print or write them down). If you lose both your password and recovery codes, you will be locked out and will need to redeploy the whole system, as database injection is not an option."*

---

## Configuration

### Environment Variables (`.env`)

```bash
# ===========================================
# REQUIRED - Change these for production
# ===========================================

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/plannededucation

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_hex(64))")
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Encryption key for AI API keys (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AI_KEY_MASTER_SECRET=your-fernet-key-change-in-production

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ===========================================
# OPTIONAL - Customize for your school
# ===========================================

# Environment
PLANNED_EDUCATION_ENV=production

# CORS Origins (comma-separated)
CORS_ORIGINS=https://yourschool.edu,https://www.yourschool.edu

# Allowed Hosts (comma-separated)
ALLOWED_HOSTS=yourschool.edu,www.yourschool.edu

# SEB Configuration
WEBAUTHN_RP_ID=yourschool.edu
WEBAUTHN_ORIGIN=https://yourschool.edu

# Archive Storage
ARCHIVE_STORAGE_ROOT=/var/lib/plannededucation/archive

# AI Cost Limits (per teacher per day)
MAX_DAILY_COST_USD=10.0

# Email (for password reset - optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourschool.edu

# Monitoring (optional)
GRAFANA_ADMIN_PASSWORD=admin
PROMETHEUS_RETENTION=30d
```

### Minimal Production `.env` Example
```bash
DATABASE_URL=postgresql://postgres:securepassword@postgres:5432/plannededucation
JWT_SECRET_KEY=abc123... (64 chars)
AI_KEY_MASTER_SECRET=gAAAAABl... (44 chars)
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
PLANNED_EDUCATION_ENV=production
CORS_ORIGINS=https://yourschool.edu
ALLOWED_HOSTS=yourschool.edu
WEBAUTHN_RP_ID=yourschool.edu
WEBAUTHN_ORIGIN=https://yourschool.edu
```

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Schools)

#### `docker-compose.yml` (Production)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: plannededucation
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/plannededucation
      REDIS_URL: redis://redis:6379
      PLANNED_EDUCATION_ENV: production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: ./web/apps/portal
      dockerfile: Dockerfile.frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait \$\${!}; done'"

volumes:
  postgres_data:
  redis_data:
```

#### Nginx Configuration (`nginx.conf`)
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:5173;
    }

    server {
        listen 80;
        server_name yourschool.edu www.yourschool.edu;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name yourschool.edu www.yourschool.edu;

        ssl_certificate /etc/letsencrypt/live/yourschool.edu/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourschool.edu/privkey.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # WebSocket for chat/proctoring
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

### Option 2: Manual Deployment (VPS)

#### Server Setup (Ubuntu 22.04+)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Install Nginx + Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Clone repository
git clone https://github.com/ezixen/PlannedEducation.git /opt/plannededucation
cd /opt/plannededucation

# Configure
cp .env.example .env
nano .env  # Edit with your settings

# Start
docker-compose up -d

# Initialize database
sleep 15
docker-compose exec backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"

# Create admin
docker-compose exec backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(email='admin@yourschool.edu', username='admin', full_name='Admin',
             hashed_password=get_password_hash('ChangeMe123!'), role='admin', is_admin=True, is_active=True)
db.add(admin); db.commit()
print('Admin created: admin@yourschool.edu / ChangeMe123!')
"

# Setup SSL
sudo certbot --nginx -d yourschool.edu -d www.yourschool.edu
```

---

## Post-Deployment Setup

### 1. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID:
   - Authorized JavaScript origins: `https://yourschool.edu`
   - Authorized redirect URIs: `https://yourschool.edu/auth/google/callback`
3. Copy Client ID and Secret to `.env`

### 2. SEB Configuration
1. Download [Safe Exam Browser](https://safeexambrowser.org/download/)
2. Install on student machines
3. Teacher creates exam → "Download SEB Config" → Distribute `.seb` file

### 3. AI Provider Setup (Teachers)
1. Teacher logs in → Settings → AI Keys
2. Choose provider:
   - **Gemini**: Get API key from [Google AI Studio](https://aistudio.google.com/)
   - **OpenRouter**: Get key from [OpenRouter](https://openrouter.ai/)
   - **Ollama**: Install locally → `http://localhost:11434`
   - **OpenAI**: Get key from [OpenAI](https://platform.openai.com/)
2. Enter API key → Save (encrypted automatically)

### 4. Archive Storage Setup
```bash
# Create archive directory
sudo mkdir -p /var/lib/plannededucation/archive
sudo chown -R 1000:1000 /var/lib/plannededucation/archive

# For external backup (USB/Network)
sudo mkdir -p /mnt/backup/plannededucation
sudo chown -R 1000:1000 /mnt/backup/plannededucation
```

---

## Maintenance

### Daily (Automated)
- Database backups (via cron)
- Archive sync (teacher ↔ server)
- AI cost tracking reset (midnight UTC)

### Weekly
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean old containers
docker system prune -f

# Check disk space
df -h /var/lib/plannededucation
```

### Monthly
```bash
# Rotate logs
docker-compose exec backend python -c "
import logging
logging.getLogger().handlers[0].doRollover()
"

# Test backup restore
docker-compose exec postgres pg_dump -U postgres plannededucation > backup_test.sql
docker-compose exec postgres psql -U postgres -d plannededucation_test < backup_test.sql
```

### Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Run migrations
docker-compose exec backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
"
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Backend won't start** | Check `docker-compose logs backend` → Usually DB connection or env vars |
| **Frontend not loading** | Check `docker-compose logs frontend` → Usually build error or port conflict |
| **Database connection failed** | Verify `DATABASE_URL` in `.env`, check postgres container health |
| **SEB won't launch** | Verify `.seb` file has correct `examKey` and `startURL` |
| **AI grading fails** | Check teacher's AI key in Settings → AI Keys; verify provider status |
| **Heartbeats not showing** | Check Redis connection; verify WebSocket proxy in nginx |
| **SEB won't launch** | Install SEB 3.4+; verify `.seb` file association |
| **Passkeys not working** | Ensure HTTPS; check `WEBAUTHN_RP_ID` and `WEBAUTHN_ORIGIN` |

### Logs
```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# Nginx logs
docker-compose logs -f nginx

# Database logs
docker-compose logs -f postgres
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:5173

# Database
docker-compose exec postgres pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping
```

---

## Backup & Recovery

### Automated Backup (Cron)
```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /opt/plannededucation && docker-compose exec -T postgres pg_dump -U postgres plannededucation | gzip > /var/backups/plannededucation_$(date +\%Y\%m\%d).sql.gz
```

### Restore from Backup
```bash
# Stop services
docker-compose stop backend frontend

# Restore database
gunzip -c /var/backups/plannededucation_20260115.sql.gz | docker-compose exec -T postgres psql -U postgres -d plannededucation

# Restart
docker-compose up -d backend frontend
```

### Disaster Recovery
```bash
# Full restore from backup
1. Restore database from backup
2. Restore archive files from /var/lib/plannededucation/archive backup
3. Restore .env file
4. Run docker-compose up -d
4. Verify all services healthy
```

---

## Security Checklist (Post-Deploy)

- [ ] Change default admin password
- [ ] Enable HTTPS (Let's Encrypt via Certbot)
- [ ] Configure firewall (only 80, 443, 22 open)
- [ ] Enable fail2ban for SSH
- [ ] Set up monitoring alerts (Grafana)
- [ ] Configure automated backups
- [ ] Test disaster recovery
- [ ] Document admin credentials securely
- [ ] Train teachers on SEB distribution
- [ ] Schedule monthly security updates

---

## Support

- **Documentation**: `docs/ARCHITECTURE.md`, `docs/DEPLOY.md`
- **Issues**: GitHub Issues
- **Security**: `security@plannededucation.org`
- **Community**: GitHub Discussions

---

## License
MIT License - Free for educational use. See `LICENSE` file.