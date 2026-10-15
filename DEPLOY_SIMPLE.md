# PlannedEducation - Simple Deploy Guide for Schools

**Target**: IT teachers with basic computer skills  
**Time**: ~15 minutes  
**Requirements**: Windows 10/11, 8GB RAM, 20GB free space

---

## 🎯 What You'll Get
A complete exam platform running on your school server with:
- Teacher dashboard (create exams, grade with AI)
- Student portal (take exams offline/online)
- Parent portal (view progress)
- Secure Exam Browser (SEB) support
- AI grading (bring your own API key)
- Module sharing (math, chemistry, biology, etc.)

---

## 📋 Before You Start

### Minimum Hardware
- **CPU**: 2 cores (Intel i3 / AMD Ryzen 3 or better)
- **RAM**: 8 GB (4 GB absolute minimum)
- **Storage**: 20 GB free SSD space
- **OS**: Windows 10/11 Pro (for Docker)

### Required Software (Install These First)
1. **Docker Desktop** - https://www.docker.com/products/docker-desktop/
   - Download → Install → Restart computer
   - Open Docker Desktop once to accept license
2. **Git** - https://git-scm.com/download/win
   - Default options are fine
3. **Text Editor** - Notepad++ or VS Code (optional but helpful)

### Network
- Port 80, 443, 5173, 8000 open on firewall
- Internet access for AI providers, updates, Let's Encrypt SSL

---

## 🚀 Quick Deploy (3 Steps)

### Step 1: Get the Code
```powershell
# Open PowerShell as Administrator
cd D:\dev
git clone https://github.com/ezixen/PlannedEducation.git PEserver
cd PEserver
```

### Step 2: Configure (Run Once)
```powershell
# Copy config template
copy .env.example .env

# Generate secure keys (run these commands)
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(64))"
python -c "from cryptography.fernet import Fernet; print('AI_KEY_MASTER_SECRET=' + Fernet.generate_key().decode())"
```

**Edit `.env` with Notepad** and fill in:
```env
# REQUIRED - Change these!
JWT_SECRET_KEY=your-64-char-key-from-above
AI_KEY_MASTER_SECRET=your-44-char-key-from-above
GOOGLE_CLIENT_ID=your-google-oauth-id (or leave blank for email-only login)
GOOGLE_CLIENT_SECRET=your-google-oauth-secret

# School settings
CORS_ORIGINS=https://yourschool.edu
ALLOWED_HOSTS=yourschool.edu
WEBAUTHN_RP_ID=yourschool.edu
WEBAUTHN_ORIGIN=https://yourschool.edu

# Optional: Email for password reset
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourschool.edu
```

> **Tip**: For testing without Google OAuth, leave `GOOGLE_CLIENT_ID` blank - email/password login will work.

### Step 3: Start Platform
```powershell
# Build and start (first time takes 3-5 minutes)
docker-compose up -d --build

# Wait 15 seconds for containers to start
Start-Sleep 15

# Initialize database
docker-compose exec backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"

# Create admin user (CHANGE PASSWORD!)
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

---

## ✅ Verify It Works

| Service | URL | What to Check |
|---------|-----|---------------|
| **Frontend** | http://localhost:5173 | Login page loads |
| **API Docs** | http://localhost:8000/docs | Swagger UI loads |
| **Health** | http://localhost:8000/health | Returns `{"status":"healthy"}` |

**First Login**: 
1. Go to http://localhost:5173
2. Login: `admin@yourschool.edu` / `ChangeMe123!`
3. **Immediately change password** in Settings → Security

---

## 🌐 Make It Accessible on School Network

### Option A: Quick LAN Access (No Domain)
1. Find server IP: `ipconfig` → IPv4 Address (e.g., `192.168.1.50`)
2. Edit `.env`:
   ```env
   CORS_ORIGINS=http://192.168.1.50:5173
   ALLOWED_HOSTS=192.168.1.50
   WEBAUTHN_RP_ID=192.168.1.50
   WEBAUTHN_ORIGIN=http://192.168.1.50:5173
   ```
3. Restart: `docker-compose restart`
4. Access from any school computer: `http://192.168.1.50:5173`

### Option B: With Domain + HTTPS (Recommended)
1. Point domain `yourschool.edu` to server IP
2. Edit `.env` with your domain
3. Run: `docker-compose up -d certbot` (gets Let's Encrypt SSL)
4. Access: `https://yourschool.edu`

---

## 📦 Module System - How It Works

### For Teachers: Create & Share Modules
1. **Create Exam** → Teacher Dashboard → "Create Exam"
2. **Add Questions** (multiple choice, essay, math, coding)
3. **Export Module**: Exam Editor → "Export Package" → Download `.pepkg.json`
4. **Share**: Send file via email, USB, or upload to Central Repository

### Module Categories (Built-in)
- 📐 **Mathematics** - Algebra, Calculus, Geometry, Statistics
- 🧪 **Chemistry** - Organic, Inorganic, Physical, Lab Safety
- 🧬 **Biology** - Cell Biology, Genetics, Ecology, Anatomy
- 🌍 **Physics** - Mechanics, Thermodynamics, Electromagnetism, Quantum
- 💻 **Computer Science** - Programming, Algorithms, Data Structures
- 📚 **Languages** - English, Spanish, French, German, etc.
- 🎨 **Arts & Humanities** - History, Geography, Literature, Art
- 🏥 **Health & PE** - First Aid, Nutrition, Sports Science

### Central Repository (plannededucation.org/modules)
- Browse by category, grade level, language
- Download → Import in Exam Editor → "Import Package"
- Rate & review modules
- Teachers can upload their own (moderated)

### Custom School Repository
Each school can host their own module server:
```env
# In .env - add custom module sources
MODULE_SOURCES=https://modules.yourschool.edu,https://mathdept.yourschool.edu
```
Teachers see modules from all configured sources in Exam Editor → "Import Package" → "Browse Sources"

---

## 👨‍🏫 First-Time Setup Wizard (Auto-Runs on First Login)

When admin logs in first time, a guided wizard appears:

1. **School Info** → Name, address, timezone, language
2. **Admin Account** → Confirm email, set strong password
3. **Google OAuth** (optional) → Paste Client ID/Secret
4. **AI Provider** → Choose default (Gemini, Ollama, OpenRouter)
5. **SEB Config** → Download SEB config template
6. **Module Sources** → Add central + custom repositories
6. **Backup Schedule** → Set daily backup time (default 2 AM)
7. **Done!** → Dashboard ready

---

## 🔧 Common Tasks

### Update Platform
```powershell
cd D:\dev\PEserver
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### Backup (Run Daily via Task Scheduler)
```powershell
# Save as backup.ps1 and schedule daily at 2 AM
cd D:\dev\PEserver
docker-compose exec -T postgres pg_dump -U postgres plannededucation | gzip > "D:\backups\plannededucation_$(Get-Date -Format 'yyyyMMdd').sql.gz"
# Keep last 30 days
Get-ChildItem D:\backups\plannededucation_*.sql.gz | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item
```

### Restore from Backup
```powershell
docker-compose stop backend frontend
gunzip -c D:\backups\plannededucation_20260115.sql.gz | docker-compose exec -T postgres psql -U postgres -d plannededucation
docker-compose up -d backend frontend
```

### View Logs
```powershell
docker-compose logs -f backend    # Backend API
docker-compose logs -f frontend   # Frontend
docker-compose logs -f postgres   # Database
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Docker won't start** | Enable Hyper-V / WSL2 in Windows Features; restart |
| **Port 5173/8000 in use** | Close other apps; or change ports in `docker-compose.yml` |
| **Database connection failed** | Check `docker-compose logs postgres`; verify `.env` DATABASE_URL |
| **Frontend blank page** | Clear browser cache; check `docker-compose logs frontend` |
| **AI grading fails** | Teacher: Settings → AI Keys → verify API key; check provider status |
| **SEB won't launch** | Install SEB 3.4+; verify `.seb` file association |
| **Passkeys not working** | Must use HTTPS; check `WEBAUTHN_RP_ID` matches domain |

### Quick Health Check
```powershell
curl http://localhost:8000/health
curl http://localhost:5173
docker-compose exec postgres pg_isready -U postgres
docker-compose exec redis redis-cli ping
```

---

## 📞 Support

- **Documentation**: `docs/DEPLOY.md`, `docs/ARCHITECTURE.md`
- **Issues**: https://github.com/ezixen/PlannedEducation/issues
- **Security**: security@plannededucation.org
- **Community**: GitHub Discussions

---

## 📄 License
MIT License - Free for educational use forever. See `LICENSE` file.

---

**You're ready!** 🎉 Your school now has a professional exam platform. Start by creating your first exam in the Teacher Dashboard.