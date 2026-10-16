# PlannedEducation Comprehensive Guide

## Table of Contents

1. [Overview](#overview)
2. [Deployment Guide](#deployment-guide)
   - [Local Development](#local-development)
   - [Docker Deployment](#docker-deployment)
   - [Production Deployment](#production-deployment)
3. [Test Administration Workflow](#test-administration-workflow)
   - [Creating a New Exam](#creating-a-new-exam)
   - [Managing Classes and Students](#managing-classes-and-students)
   - [Running an Exam Session](#running-an-exam-session)
   - [Monitoring with Proctoring](#monitoring-with-proctoring)
4. [AI-Assisted Grading & Correction](#ai-assisted-grading--correction)
   - [Configuring AI Providers](#configuring-ai-providers)
   - [Running AI Grading](#running-ai-grading)
   - [Reviewing and Correcting AI Suggestions](#reviewing-and-correcting-ai-suggestions)
   - [AI Provider Abstraction Layer](#ai-provider-abstraction-layer)
   - [Rate Limiting & Cost Tracking](#rate-limiting--cost-tracking)
5. [Test Creation with Modules](#test-creation-with-modules)
   - [Question Types](#question-types)
   - [Dynamic Math Variables](#dynamic-math-variables)
   - [Question Banks](#question-banks)
   - [Reusable Modules](#reusable-modules)
6. [Test Package Sharing](#test-package-sharing)
   - [Exporting Test Packages](#exporting-test-packages)
   - [Importing Test Packages](#importing-test-packages)
   - [Sharing with Others](#sharing-with-others)
   - [Package Registry (pepkg CLI)](#package-registry-pepkg-cli)
7. [Security & Compliance](#security--compliance)
   - [Passkeys/WebAuthn](#passkeyswebauthn)
   - [NIST AI RMF 1.0 + Generative AI Profile](#nist-ai-rmf-10--generative-ai-profile)
   - [NIST SSDF 1.1 Alignment](#nist-ssdf-11-alignment)
   - [NIST CSF 2.0 Alignment](#nist-csf-20-alignment)
   - [OWASP Top 10:2025 Alignment](#owasp-top-102025-alignment)
8. [Observability & SLOs](#observability--slos)
   - [OpenTelemetry Integration](#opentelemetry-integration)
   - [Prometheus Metrics & Grafana Dashboards](#prometheus-metrics--grafana-dashboards)
   - [SLO Burn-Rate Alerting](#slo-burn-rate-alerting)
9. [Troubleshooting](#troubleshooting)

---

## Overview

PlannedEducation is a free, open-source, privacy-first exam platform designed for teachers. It provides:

- **Secure test-taking** with Secure Exam Browser (SEB) integration
- **AI-assisted grading** with teacher review workflow (BYOK - Bring Your Own Key)
- **Offline-first architecture** with IndexedDB persistence
- **Three-way immutable storage** (student/teacher/server sync)
- **Proctoring** with GDPR-compliant webcam/microphone monitoring
- **Modular test packages** for sharing and reuse
- **Passkeys/WebAuthn** for phishing-resistant authentication
- **External AI only** (BYOK) - no internal LLMs, teacher choice of provider
- **NIST AI RMF 1.0 + Generative AI Profile** compliance for AI risk governance
- **NIST SSDF 1.1 / CSF 2.0 / OWASP Top 10:2025** security alignment
- **SLO-based observability** with OpenTelemetry, Prometheus, Grafana, Alertmanager

**Tech Stack:**
- Backend: FastAPI, Python 3.12+, SQLAlchemy 2.0, PostgreSQL 16, Redis 7
- Frontend: React 19, TypeScript 5.6, Vite 8.3, PWA (vite-plugin-pwa)
- Auth: Google SSO, TOTP 2FA, Passkeys/WebAuthn, Argon2id
- AI: External providers only (Gemini, OpenRouter, Ollama, OpenAI-compatible, ChatGPT session)
- Monitoring: OpenTelemetry, Prometheus, Grafana, Alertmanager
- Package Registry: pepkg CLI for test package management

---

## Deployment Guide

### Local Development

**Prerequisites:**
- Python 3.12+ (use C:/.venv - shared venv)
- Node.js 20+
- PostgreSQL 16 (or SQLite for quick testing)
- Redis 7

**Installation & Deployment Guides:**
- 🪟 [Windows Installation Guide (install.ps1)](INSTALL_WINDOWS.md)
- 🐧 [Linux Installation Guide (install.sh)](INSTALL_LINUX.md)
- 📋 [Compatibility & Requirements Matrix](INSTALL_COMPATIBILITY.md)

**Quick Start:**
```powershell
# 1. Clone and navigate
cd D:\Dev\PlannedEducation

# 2. Start all services (backend + frontend)
.\start.ps1

# Or start individually:
# Backend: .\start.ps1 -BackendOnly
# Frontend: .\start.ps1 -FrontendOnly
`

**Manual Start:**
`powershell
# Backend
cd D:\Dev\PlannedEducation
C:/.venv/Scripts/python.exe -m uvicorn src.plannededucation.main:app --reload --port 8000

# Frontend (new terminal)
cd D:\Dev\PlannedEducation\web\apps\portal
npm install
npm run dev
`

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Deployment

**Development:**
`ash
docker-compose up -d
`

**Production:**
`ash
# Build images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
`

**Environment Variables (create .env):**
`nv
# Required
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
DATABASE_URL=postgresql://user:pass@localhost:5432/plannededucation
REDIS_URL=redis://localhost:6379/0

# Optional
GOOGLE_CLIENT_ID=your-google-oauth-client-id
AI_KEY_MASTER_SECRET=your-fernet-key-for-ai-keys
PLANNED_EDUCATION_ENV=production
ALLOW_DEV_SEB_BYPASS=false
`

### Production Deployment

**Using deploy.sh (recommended):**
`ash
chmod +x deploy.sh
./deploy.sh
`

This script:
1. Generates secure secrets
2. Builds Docker images
3. Runs database migrations
4. Starts all services with health checks

**Manual Production Steps:**
1. Set up PostgreSQL 16 and Redis 7
2. Configure reverse proxy (Nginx/Caddy) with TLS (Let's Encrypt)
3. Set environment variables
4. Run migrations: lembic upgrade head
5. Build frontend: cd web/apps/portal && npm run build
6. Start backend with Gunicorn/Uvicorn workers
7. Serve frontend static files via Nginx

---
---

## Test Administration Workflow

### Creating a New Exam

1. **Login as Teacher** → Navigate to **Teacher Dashboard**
2. Click **\"Create New Exam\"**
3. Fill in exam details:
   - **Title** (required)
   - **Description** (optional)
   - **Duration** (minutes)
   - **Start/End time** (optional scheduling)
   - **SEB Config** (enable for secure exams)
4. Click **\"Save & Continue to Questions\"**

### Adding Questions

**Question Types:**
- **Multiple Choice**: Single or multiple correct answers
- **Essay**: Free-text response
- **Dynamic Math**: Uses [rand:min-max] variables (e.g., What is [rand:1-10] + [rand:5-15]?)

**Dynamic Math Example:**
`
Question: Calculate the area of a rectangle with width [rand:2-10] and height [rand:3-12].
Answer: [rand:2-10] * [rand:3-12] (auto-evaluated)
`

**Question Bank:**
- Click **\"Import from Question Bank\"**
- Filter by subject, difficulty, tags
- Select questions → **\"Add to Exam\"**

### Managing Classes and Students

1. Go to **Teacher Dashboard** → **Classes**
2. **Create Class**: Name, description, academic year
3. **Add Students**:
   - Manual: Enter email/name
   - Bulk: CSV import (email, first_name, last_name)
   - Self-enroll: Share class code
4. **Assign Exam to Class**: Select exam → **\"Assign to Class\"** → Choose class(es)

### Running an Exam Session

1. **Teacher Dashboard** → Select exam → **\"Start Session\"**
2. Students receive notification/link
3. Students click **\"Take Exam\"** → Launches SEB (if enabled)
4. **Real-time monitoring** in Teacher Dashboard:
   - Student progress (heartbeat)
   - SEB violations
   - Proctoring events (if enabled)
5. **Time warnings** at 10min, 5min, 1min (configurable)
6. **Auto-submit** at time expiry or manual submit

### Monitoring with Proctoring

**Enable Proctoring:**
1. Exam settings → **\"Enable Proctoring\"**
2. Students must grant camera/microphone permissions
3. GDPR consent modal appears (required)

**Proctoring Events Tracked:**
- Eye movement (gaze tracking)
- Multiple face detection
- Background audio levels
- Tab/window switches
- SEB violations

**View Events:**
- Teacher Dashboard → **\"Proctoring\"** tab
- Real-time feed + session replay
- Export events for review

---

## AI-Assisted Grading & Correction

### Configuring AI Providers

1. **Settings** → **AI Key Management**
2. Choose provider:
   - **Gemini** (Google): AIza... key
   - **OpenRouter**: sk-or-... key (access to 100+ models)
   - **Ollama** (local): http://localhost:11434 (no key needed)
   - **OpenAI-compatible**: Custom base URL + key
3. Select model (e.g., gemini-1.5-pro, llama3.1:70b)
4. **Save** - keys encrypted with Fernet (AES-128)

### Running AI Grading

1. **Teacher Dashboard** → Select exam → **\"Grade with AI\"**
2. Choose submissions (or **\"Grade All\"**)
3. AI processes each submission:
   - Anonymizes student data (Presidio PII scrubber)
   - Sends to configured provider
   - Returns: score, feedback, confidence, flagged issues
4. Results appear in **\"AI Suggestions\"** column

### Reviewing and Correcting AI Suggestions

**Per-Submission Review:**
1. Click submission → **\"Review AI Grade\"** modal
2. For each question:
   - **AI Score** (0-100%)
   - **AI Feedback** (text)
   - **Confidence** (High/Medium/Low)
   - **Flagged Issues** (hallucination, off-topic, etc.)
3. Teacher actions:
   - **Approve**: Accept AI grade as-is
   - **Edit**: Modify score/feedback
   - **Reject**: Discard AI, grade manually
4. **\"Apply All Approved\"** → Finalizes grades

**Bulk Actions:**
- **\"Approve All High Confidence\"** - One-click for confident grades
- **\"Flag Low Confidence for Review\"** - Queue for manual review
- **Export Grades** → CSV/Excel for gradebook import

---
---

## Test Creation with Modules

### Question Types

| Type | Use Case | Auto-Graded |
|------|----------|-------------|
| Multiple Choice (Single) | Knowledge recall | Yes |
| Multiple Choice (Multiple) | Concept application | Yes |
| Essay | Critical thinking | AI-assisted |
| Dynamic Math | Math/science with variables | Yes (exact match) |
| File Upload | Diagrams, code, documents | Manual/AI |
| Audio Response | Language, music | AI-assisted (STT) |

### Dynamic Math Variables

**Syntax:** [rand:min-max] or [rand:min-max:step]

**Examples:**
`
[rand:1-10]           → Random integer 1-10
[rand:0.5-5.0:0.5]    → Random 0.5, 1.0, 1.5... 5.0
[rand:10-100:10]      → Random 10, 20, 30... 100
`

**In Answers:**
- Use same variable: Answer: [rand:1-10] * 2
- Multiple variables: x = [rand:1-5], y = [rand:6-10] → Answer: x + y

**Validation:** System generates 100 variants to verify answer correctness.

### Question Banks

**Creating a Bank:**
1. **Teacher Dashboard** → **Question Banks** → **\"New Bank\"**
2. Name, subject, tags
3. Add questions (same as exam creation)

**Using Banks:**
- **Exam Editor**: **\"Import from Bank\"** → Select questions
- **Randomized Exams**: **\"Add Random Selection\"** → Pick 10 from 50
- **Shared Banks**: Import .json/.yaml from colleagues

### Reusable Modules

**What are Modules?**
Self-contained question sets with shared context (e.g., a reading passage with 5 questions).

**Creating a Module:**
1. **Exam Editor** → **\"Create Module\"**
2. Add **Context** (passage, image, data table)
3. Add **Questions** linked to context
4. **Save as Module** → Appears in **\"My Modules\"**

**Using Modules:**
- Drag module into exam → All questions + context added
- Module variables randomized per student
- Edit module once → Updates all exams using it

**Module Structure (JSON):**
`json
{
  "id": "module_physics_kinematics",
  "title": "Kinematics Problem Set",
  "context": "A car accelerates from rest at [rand:1-5] m/s²...",
  "questions": [
    {"type": "dynamic_math", "text": "Velocity after [rand:2-10]s?", "answer": "[rand:1-5] * [rand:2-10]"},
    {"type": "dynamic_math", "text": "Distance after [rand:2-10]s?", "answer": "0.5 * [rand:1-5] * [rand:2-10]^2"}
  ],
  "tags": ["physics", "kinematics", "grade-11"],
  "version": "1.0"
}
`

---
---

## Test Package Sharing

### Exporting Test Packages

**From Exam Editor:**
1. Open exam → **\"Export Package\"**
2. Choose format: **JSON** (recommended) or **YAML**
3. Options:
   - Include AI grading config
   - Include SEB settings
   - Anonymize teacher info
4. **Download** → .pepkg.json file

**From Question Bank:**
1. **Question Banks** → Select bank → **\"Export\"**
2. Same format options

**Package Contents:**
`json
{
  "version": "1.0",
  "type": "exam",
  "metadata": {
    "title": "Midterm Physics",
    "author": "Teacher Name (anonymized)",
    "created": "2026-10-11",
    "tags": ["physics", "grade-11", "midterm"]
  },
  "exam": { ... },
  "modules": [ ... ],
  "question_bank_refs": [ ... ]
}
`

### Importing Test Packages

1. **Teacher Dashboard** → **\"Import Package\"**
2. Drag .pepkg.json or .pepkg.yaml file
3. Preview: Shows questions, modules, settings
4. **Import Options:**
   - Create new exam
   - Add to existing exam
   - Import modules to library
   - Import questions to bank
5. **Confirm** → Exam ready to assign

### Sharing with Others

**Direct Sharing:**
- Send .pepkg.json via email, shared drive, USB
- Recipient imports via **\"Import Package\"**

**GitHub/GitLab:**
- Commit packages to a repo
- Others clone/pull → Import
- Version control for collaborative editing

**PlannedEducation Package Registry (Future):**
- Publish to registry: pepkg publish my-exam.pepkg.json
- Search: pepkg search physics grade-11
- Install: pepkg install user/physics-midterm

**Offline Sharing:**
- Export to USB
- Import on air-gapped school network
- No internet required for exam taking

---
---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| SEB won't launch | Check seb_config_key set on exam; verify SEB installed on student device |
| AI grading fails | Verify API key in Settings; check provider status; check rate limits |
| Offline sync fails | Check IndexedDB storage quota; verify service worker registered |
| Proctoring permission denied | Student must allow camera/mic in browser; check GDPR consent |
| Build fails | Run 
pm install in web/apps/portal; check Node.js version (20+) |
| Database migration fails | Check DATABASE_URL; run lembic upgrade head manually |

### Logs

- **Backend**: docker-compose logs -f backend or terminal output
- **Frontend**: Browser DevTools Console
- **Database**: docker-compose exec postgres pg_isready

### Getting Help

- **Documentation**: docs/ folder
- **Runbooks**: docs/runbooks/ for incident response
- **GitHub Issues**: Report bugs/request features
- **FAQ Chatbot**: Click **Help** button (bottom-right) in portal

---

*Last updated: 2026-10-13*
*Version: 1.1*
