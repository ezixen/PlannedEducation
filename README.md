# Planned Education 🎓

![Planned Education Logo](PElogo_128x128.jpg)

**A free, open-source teacher's aid, grading companion, and secure test-taking environment — built with care for teachers and students alike.**

Planned Education exists for a simple reason: **teachers shouldn't have to spend their evenings and weekends buried in grading.** When educators are well-rested and supported, they can show up with more patience, creativity, and heart for the children who need them most. **Children are our future. Let's give them teachers who are rested, supported, and ready to inspire.** 🌱

---

## ⚡ Quick Installation & Deployment (Human or AI Agent)

Deploy PlannedEducation on your school or personal server in minutes — either **interactively yourself** or by **asking your AI coding agent** (GitHub Copilot, Antigravity, Claude Code, Cursor, etc.) to run the installer for you!

| Platform | Interactive Human Command | Uninstaller | Full Step-by-Step Guide |
|:---|:---|:---|:---:|
| 🪟 **Windows** (10, 11, Server) | `powershell -ExecutionPolicy Bypass -File .\install.ps1` | `powershell -ExecutionPolicy Bypass -File .\uninstall.ps1` | [📖 **Windows Installation Guide**](docs/INSTALL_WINDOWS.md) |
| 🐧 **Linux / WSL** (Ubuntu, Debian, RHEL, Arch) | `bash ./install.sh` | `bash ./uninstall.sh` | [📖 **Linux Installation Guide**](docs/INSTALL_LINUX.md) |
| 🧙 **Cross-Platform Wizard** | `python deploy_wizard.py` | — | [📋 **Requirements & Compatibility**](docs/INSTALL_COMPATIBILITY.md) |

> 💡 **No Docker? No problem!** The installer supports **Mode 1: Single-Server SQLite** (zero external DB setup), **Mode 2: Production PostgreSQL + Redis**, and **Mode 3: Docker Compose**. Default ports are `8000` (API) and `5173` (Frontend), with automatic fallback to free ports if already in use.

### 🤖 AI Agent Deployment & Undeployment Support

You can tell your AI agent: *"Deploy PlannedEducation for me"* or *"Uninstall PlannedEducation from `<folder>`"*.
Our scripts (`install.ps1`, `install.sh`, `uninstall.ps1`, `uninstall.sh`) are purpose-built for both human operators and AI agents:

1. **Mandatory Questions AI Agents Must Ask You First**:
   Before running `install.ps1 -AutoConfirm` or `AUTO_CONFIRM=true ./install.sh`, the AI agent **must stop and ask you** for your key decisions:
   - **Target Installation Folder** (`-InstallDir` / `INSTALL_DIR`, e.g. `C:\PlannedEducation`, `D:\dev\PEtest`, or `/opt/plannededucation`)
   - **Deployment Mode** (`1` = Local/Single-Server SQLite, `2` = Production PostgreSQL + Redis, `3` = Docker Compose)
   - **School & Superadmin Identity** (`-SchoolName` / `SCHOOL_NAME`, `-AdminEmail` / `ADMIN_EMAIL`, `-AdminName` / `ADMIN_NAME`, and `-AdminPassword` / `ADMIN_PASSWORD`)
   - **Port Preferences** (confirm default ports `8000` / `5173` with auto-fallback, or custom `-ApiPort` / `-FrontendPort`)
   - **When Uninstalling (`uninstall.ps1` / `uninstall.sh`)**: Confirm the target directory to remove, and review external dependencies (`Python`, `Node.js`, `PostgreSQL`, `Redis`, `Docker`, `Git`) **one by one** (there is intentionally **no "remove all dependencies"** option).
2. **Separated Diagnostic & Error Logs (`<InstallDir>/logs/`)**:
   Every deployment automatically writes separated standard and error logs so humans and AI agents can diagnose any issue immediately without digging through noisy output:
   - `logs/install.log` & `logs/install_error.log` — step-by-step installation & verification results
   - `logs/backend.log` & `logs/backend_error.log` — structured JSON API logs & isolated warning/exception logs (tracebacks included), plus `logs/backend_stdout.log` / `logs/backend_stderr.log` raw console capture for start-up crashes
   - `logs/frontend.log` & `logs/frontend_error.log` — frontend server stdout & error logs

---

## 🌟 What Makes Planned Education Special

### For Teachers — Your Time Matters
- **AI Grading Assistant**: Let AI draft grades and feedback for you to review and approve — one click to apply. You stay in control; the AI just does the heavy lifting.
- **Smart Mistake Grouping**: Instantly see patterns across the class. "These 5 students all struggled with the same concept" — now you can reteach efficiently.
- **Modular Test Packages**: Export your exams as JSON/YAML packages and share them with colleagues. Import packages from others. Build a library once, use it forever.
- **IEP & Accessibility Built-In**: Assign time multipliers (1.5x, 2x) per student globally. No more manual adjustments per exam.
- **OCR & Speech-to-Text**: Handwritten math? Audio responses? Upload and let the system transcribe — you grade the content, not the handwriting.

### For Students — Fair, Secure, Stress-Free
- **Safe Exam Browser Lockdown**: Cryptographically verified. No tab-switching, no screen-sharing, no unauthorized help. Just the exam.
- **Dynamic Randomization**: Every student gets a unique variation. `[rand:1-10]` tags shuffle numbers, options, and question order automatically.
- **Digital Hand Raise**: Stuck? Raise your hand in the secure chat overlay — your teacher sees it instantly without breaking the exam lock.
- **Optional Proctoring (Your Choice, Your Consent)**: Webcam/mic for remote exams — **only with your explicit GDPR consent**. You decide what you're comfortable with. Eye-tracking, multi-face detection, and audio monitoring run locally; only event metadata leaves your device.

### For Parents — Transparency Without Surveillance
- **Read-Only Portal**: See your child's progress, scores, and teacher feedback. No grades are hidden, no data is sold.

### For Everyone — Privacy First, Always
- **Anonymizer API Gateway**: Student names and emails are stripped **before** any AI sees the work. The AI grades the answer, not the child.
- **Zero Paid Services**: Everything runs on free tiers, self-hosted infrastructure, or local models (Ollama). No surprise bills. No vendor lock-in.
- **Google SSO + TOTP 2FA**: Secure, familiar login. Recovery codes for when life happens.

---

## 🛠️ Core Features at a Glance

| Area | What You Get |
|------|--------------|
| **Exam Creation** | Dynamic variables, randomization, rubrics, IEP time multipliers |
| **AI Grading** | Anonymized submissions → AI drafts grades → Teacher reviews → One-click apply |
| **Mistake Analytics** | Automatic grouping of similar errors across the class |
| **Test Packages** | Export/import exams as JSON or YAML (compressed optional). Share, version, reuse. |
| **Secure Exam Mode** | SEB cryptographic lock, digital hand raise, offline PWA support |
| **Proctoring (Opt-In)** | GDPR consent flow → Face detection → Eye-gaze tracking → Multi-face alerts → Audio anomaly detection → All events timestamped & auditable |
| **OCR & STT** | Tesseract math OCR + faster-whisper speech-to-text |
| **Auth & Recovery** | Google SSO + email login, TOTP 2FA, 5 printable single-use recovery codes, offline in-platform supervisor reset |
| **Teacher Verification** | Self-registration for students/teachers/parents; teacher verification required by admin before exam creation |
| **In-App Notifications** | Floating notification bell (60s polling) with 1-click teacher & password reset approvals |
| **Deployment Config** | Post-deploy editable `config/deployment.json` via file or Admin Panel (no redeploy needed) + backup button |
| **Database** | PostgreSQL (prod) / SQLite (dev) via SQLAlchemy |

---

## 🚀 Quick Start (Local Development)

> For production or school server deployment, refer directly to our [Windows Installation Guide](docs/INSTALL_WINDOWS.md) or [Linux Installation Guide](docs/INSTALL_LINUX.md).
>
> **Dev Prerequisites**: Docker Desktop, Node.js 20+, Python 3.12+

```powershell
# 1. Start the database & cache
docker compose up -d postgres redis

# 2. Launch the backend API + frontend portal
.\start.ps1
```

- **Backend API docs**: http://localhost:8001/docs
- **Frontend portal**: http://localhost:5175

**Verify everything's healthy:**
```powershell
python scripts\testing\canary.py
```

**When you're done:**
```powershell
Stop-Process -Name python,node -ErrorAction SilentlyContinue
```

---

## 📦 Test Packages — Share & Reuse

Create an exam once. Export it as a package. Share with your department. Import a colleague's package and adapt it.

```bash
# Export (from Teacher Dashboard → Package Manager)
# → JSON or YAML, with/without answers, gzip optional

# Import (drag & drop in Package Manager)
# → Validates structure, checksums, creates new exam with all questions & rubrics
```

Packages include:
- Exam metadata (title, duration, settings, IEP config)
- All questions (multiple choice, essay, dynamic math with variables)
- Rubrics with criteria & keywords
- SHA-256 checksum for integrity

---

## 🔒 Proctoring — Transparent & Consent-Driven

We believe proctoring should be **opt-in, transparent, and privacy-respecting**.

1. **Student sees a clear GDPR consent modal** explaining exactly what data is collected (face presence, gaze coordinates, face count, audio volume levels — no video/audio recordings stored).
2. **Student chooses** which sensors to enable (camera, microphone, screen monitoring).
3. **During the exam**, events are recorded locally and batched to the server every 5 seconds.
4. **Teachers see only aggregated stats**: violation counts, max faces detected, event timeline — never raw video.

**Event types recorded**: `face_detected`, `face_lost`, `multiple_faces`, `eye_movement`, `gaze_off_screen`, `audio_anomaly`, `tab_switch`, `window_blur`, `fullscreen_exit`, `seb_violation`.

---

## 🏗️ Architecture (For the Curious)

```
┌─────────────────────────────────────────────────────────────┐
│                    Planned Education                        │
├─────────────────────┬─────────────────────┬─────────────────┤
│   Frontend (PWA)    │   Backend (FastAPI) │  Infrastructure │
│   React 18 + Vite   │   Python 3.12       │  Docker Compose │
│   TypeScript        │   SQLAlchemy        │  PostgreSQL     │
│   React Router      │   Pydantic          │  Redis          │
│   Workbox SW        │   Presidio (PII)    │  nginx (prod)   │
└─────────────────────┴─────────────────────┴─────────────────┘
```

**Key backend modules:**
- `routes_auth.py` — Google SSO, TOTP 2FA, password reset
- `routes_exam.py` — Exam lifecycle, SEB config, submissions
- `routes_anonymizer.py` — PII stripping proxy for AI
- `routes_proctoring.py` — Consent, sessions, events, stats (22 tests!)
- `routes_packages.py` — Export/import/validate test packages
- `routes_ocr.py` / `routes_stt.py` — Math OCR & speech-to-text
- `routes_chat.py` — Secure WebSocket hand-raise
- `ocr_service.py` / `stt_service.py` — Local ML pipelines

---

## 🤝 Contributing

We welcome contributions! Whether it's:
- 🐛 Bug fixes
- ✨ New features (especially accessibility improvements)
- 📝 Documentation & translations
- 🧪 Tests
- 💡 Ideas for reducing teacher workload

Please see `docs/` for coding standards, guidelines, and architecture guides.

**Our promise**: No paid dependencies. Ever. If it can't run free, it doesn't go in.

---

## 📜 License

MIT License — use it, modify it, share it. Just keep it free forever.

---

## 💬 A Personal Note

If Planned Education gives even one teacher an extra hour with their family, or one student a fairer exam experience, it's worth every line of code, i think.💡

---

*Built with ☕ and ❤️ for the future and equitable education.*

