# PlannedEducation — Deployment Quick Reference 🚀

PlannedEducation provides a 100% free, open-source, and local-first architecture for school test-taking and grading.

For the complete, detailed deployment manual, see the **[Master Deployment Guide](docs/admin/DEPLOYMENT_GUIDE.md)**.

---

## ⚡ Quick Start: Automated Installers

### Windows
Run from PowerShell (as Administrator):
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### Linux / Ubuntu / WSL
Run from Bash:
```bash
chmod +x ./install.sh
./install.sh
```

---

## 🐳 Quick Start: Docker

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start containers
docker compose up -d --build

# 3. Access the portal
http://localhost:5173
```

---

## ⚙️ Post-Deployment Configuration (`config/deployment.json`)

If your school's domain, hostname, ports, or network layout change after deployment, you **do not** need to redeploy or rebuild containers:
1. Edit `config/deployment.json` directly on the server, or
2. Open **Admin Dashboard → ⚙️ Deployment & Network** in your browser to update domain names, ports, and optional SMTP settings.
3. Restart backend services to apply changes immediately.

---

## 📚 Complete Documentation Index
- **[Master Deployment & Administration Guide](docs/admin/DEPLOYMENT_GUIDE.md)**: Full production setup, systemd, reverse proxy, SSL, and backup configuration.
- **[Windows Installation Guide](docs/admin/INSTALL_WINDOWS.md)**: Detailed step-by-step Windows setup.
- **[Linux Installation Guide](docs/admin/INSTALL_LINUX.md)**: Detailed step-by-step Linux setup.
- **[Database Backups & Disaster Recovery](docs/admin/BACKUP_RESTORE.md)**: Midnight auto-backup and snapshot management.
- **[Teacher Guide](docs/user/TEACHER_GUIDE.md)**: Exam authoring, question banks, AI grading, and emergency classroom student unlocks.
- **[Student Guide](docs/user/STUDENT_GUIDE.md)**: Safe Exam Browser (SEB), 5 recovery codes, and password resets.
- **[Parent Guide](docs/user/PARENT_GUIDE.md)**: Child progress tracking and account recovery approvals.
- **[Developer & Contributor Guide](docs/dev/ARCHITECTURE.md)**: Complete system architecture and testing.