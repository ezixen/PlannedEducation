# PlannedEducation - Comprehensive Deployment Guide

## Overview

PlannedEducation is a free, open-source exam platform designed for schools. It runs entirely on your school's infrastructure with no external dependencies or paid services.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    School Network                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Nginx     │  │  Backend    │  │   PostgreSQL        │  │
│  │  (Port 80)  │──│  (Port 8000)│──│   (Port 5432)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │              │                   │                 │
│         │         ┌────┴────┐      ┌──────┴──────┐         │
│         │         │  Redis  │      │   Prometheus │         │
│         │         │(Port 6379)     │  (Port 9090) │         │
│         │         └─────────┘      └─────────────┘         │
│         │                                                    │
│  ┌──────┴──────────────────────────────────────────────┐   │
│  │              Frontend (Nginx + React)                │   │
│  │                    Port 80/443                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (Linux Server)

### Prerequisites
- Ubuntu 22.04+ / Debian 12+ / RHEL 9+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space
- Docker & Docker Compose installed
- Domain name pointed to server IP (for HTTPS)

### 1. Install Docker & Docker Compose
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt-get update && sudo apt-get install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

### 2. Clone & Configure
```bash
git clone https://github.com/ezixen/PlannedEducation.git
cd PlannedEducation

# Copy environment template
cp .env.example .env

# Generate secure keys
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(64))"
python3 -c "from cryptography.fernet import Fernet; print('AI_KEY_MASTER_SECRET=' + Fernet.generate_key().decode())"

# Edit .env with your values
nano .env
```

### 3. Required .env Configuration
```env
# REQUIRED - Change these!
JWT_SECRET_KEY=your-64-char-key
AI_KEY_MASTER_KEY=your-44-char-fernet-key
POSTGRES_PASSWORD=secure-db-password

# Your school domain
CORS_ORIGINS=https://yourschool.edu
ALLOWED_HOSTS=yourschool.edu
WEBAUTHN_RP_ID=yourschool.edu
WEBAUTHN_ORIGIN=https://yourschool.edu

# Optional: Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 4. Deploy
```bash
# Build and start
docker compose up -d --build

# Wait for services
sleep 30

# Initialize database
docker compose exec -T backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"

# Create admin user
docker compose exec -T backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(
    email='admin@yourschool.edu',
    username='admin',
    full_name='School Admin',
    hashed_password=get_password_hash('ChangeMe123!'),
    role='admin', is_admin=True, is_active=True
)
db.add(admin); db.commit()
print('Admin created: admin@yourschool.edu / ChangeMe123!')
"
```

### 5. Verify
```bash
# Check services
docker compose ps

# Test endpoints
curl http://localhost:8000/health
curl http://localhost/health
```

### 6. SSL with Let's Encrypt (Production)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificates
sudo certbot --nginx -d yourschool.edu -d www.yourschool.edu

# Auto-renewal
sudo systemctl enable certbot.timer
```

## Windows Development Deployment

For local development on Windows:

```powershell
# Prerequisites: Docker Desktop, Git, Python 3.12+
git clone https://github.com/ezixen/PlannedEducation.git
cd PlannedEducation

# Copy and configure .env
copy .env.example .env
# Edit .env with your values (use localhost for domain)

# Start
docker compose up -d --build

# Initialize
docker compose exec backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"

# Access at http://localhost:5173 (frontend) or http://localhost:8000/docs (API)
```

## Module System

### Creating Modules (Teachers)
1. Teacher Dashboard → Create Exam
2. Add questions (multiple choice, essay, math, coding)
3. Exam Editor → "Export Package" → Download `.pepkg.json`

### Module Structure
```json
{
  "metadata": {
    "id": "uuid",
    "name": "Algebra I - Quadratic Equations",
    "version": "1.0.0",
    "subject": "mathematics",
    "grade_level": "9",
    "tags": ["algebra", "quadratic"],
    "license": "CC-BY-4.0"
  },
  "exam": { "title": "...", "duration_minutes": 60, ... },
  "questions": [...],
  "rubrics": [...]
}
```

### Sharing Modules
1. **Local**: Share `.pepkg.json` via email/USB
2. **Central Repository** (planned): Upload to plannededucation.org/modules
3. **Custom School Repository**: Configure `MODULE_SOURCES` in `.env`

```env
# Add custom module sources
MODULE_SOURCES=https://modules.yourschool.edu,https://mathdept.yourschool.edu
```

## Customization Strategy

### Platform vs School Customizations

```
PlannedEducation Platform (upstream)
├── Core: backend/, frontend/, database/
├── Config: docker-compose.yml, .env.example
└── Docs: DEPLOY.md, ARCHITECTURE.md

School Customizations (downstream)
├── .env                    # School-specific config
├── nginx.conf              # Custom nginx rules
├── custom_css/             # School branding
├── custom_modules/         # School-specific modules
└── scripts/                # School-specific scripts
```

### Update Strategy (GitHub-based)
```bash
# School's fork workflow
git remote add upstream https://github.com/ezixen/PlannedEducation.git
git fetch upstream
git merge upstream/main  # Merge platform updates
# Resolve conflicts in customizations only
git push origin main
docker compose build --no-cache
docker compose up -d
```

## Maintenance

### Daily (Automated via cron)
```bash
# Backup database
docker compose exec -T postgres pg_dump -U postgres plannededucation | gzip > /backups/pe_$(date +%Y%m%d).sql.gz

# Cleanup old backups (keep 30 days)
find /backups -name "pe_*.sql.gz" -mtime +30 -delete
```

### Weekly
```bash
# Update containers
docker compose pull
docker compose up -d

# Clean up
docker system prune -f
```

### Monthly
```bash
# Test restore
docker compose exec -T postgres pg_dump -U postgres plannededucation > test_backup.sql
docker compose exec -T postgres psql -U postgres -d test_db < test_backup.sql

# Update platform
git pull origin main
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | `docker compose logs backend` - check DB connection, env vars |
| Frontend not loading | `docker compose logs frontend` - check build, port conflicts |
| DB connection failed | Verify `DATABASE_URL`, check postgres health |
| SEB won't launch | Install SEB 3.4+, verify `.seb` file association |
| AI grading fails | Check teacher's AI key in Settings → AI Keys |
| Passkeys not working | Must use HTTPS; check `WEBAUTHN_RP_ID` matches domain |

## Security Checklist

- [ ] Change default admin password immediately
- [ ] Enable HTTPS (Let's Encrypt via Certbot)
- [ ] Configure firewall (only 80, 443, 22 open)
- [ ] Enable fail2ban for SSH
- [ ] Set up monitoring alerts (Grafana)
- [ ] Configure automated backups
- [ ] Test disaster recovery
- [ ] Document admin credentials securely
- [ ] Schedule monthly security updates

## Support

- **Documentation**: `docs/DEPLOY.md`, `docs/ARCHITECTURE.md`
- **Issues**: https://github.com/ezixen/PlannedEducation/issues
- **Security**: security@plannededucation.org
- **Community**: GitHub Discussions

## License

MIT License - Free for educational use forever. See `LICENSE` file.