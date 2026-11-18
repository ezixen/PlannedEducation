# PlannedEducation — Architecture Markdown (AMD)

> **Canonical architectural specification for the PlannedEducation codebase.**
> This document defines the internal structural mechanics: how the code is organized into files, module boundaries, components, interfaces, data models, and interfaces.
>
> **Audience:** Developers, AI agents, security reviewers, and operators.
> **Status:** Living document — must be updated with every edit, new module, or function.
> **Version:** 0.8.8 (matches `VERSION` file)
> **Canonical source:** `ARCHITECTURE.md` (this file). Kept in sync with `AGENTS.md`.

---

## 1. Project Overview

### 1.1 Product Purpose

PlannedEducation is a **free, open-source, local-first teacher's aid, grading software, and secure test-taking environment**. It provides teachers with powerful classroom management and automated grading without compromising student privacy or test integrity.

**Core mission:** Teachers should not spend evenings and weekends buried in grading. The platform is 100% free to operate indefinitely — no paid services, no vendor lock-in.

### 1.2 Key Characteristics

| Attribute | Value |
|-----------|-------|
| **License** | MIT |
| **Architecture** | Local-first, client-server (React SPA + FastAPI API) |
| **Database** | SQLite (dev/test), PostgreSQL (production) |
| **Authentication** | Google SSO (primary), password fallback, TOTP 2FA, WebAuthn/Passkeys |
| **AI** | External-only via pluggable provider API (no internal LLM) |
| **Privacy** | PII scrubbing via Microsoft Presidio before any AI boundary |
| **Exam Security** | Safe Exam Browser (SEB) integration, server-enforced deadlines |
| **Offline** | PWA with IndexedDB sync for offline exam taking |
| **i18n** | 38+ locales via numbered key system |

### 1.3 Environments

| Stage | Frontend URL | API URL | Database |
|-------|-------------|---------|----------|
| Local Development | `http://127.0.0.1:5173` (or `:5175`) | `http://127.0.0.1:8000` (or `:8002`) | SQLite |
| Self-Hosted / Production | Static SPA / Nginx / Cloudflare Pages / Vercel Free | FastAPI / Uvicorn (Docker / K3s) | PostgreSQL |

### 1.4 Free-Tier Policy (MANDATORY)

The project MUST NEVER use or enable any paid services. All functionality must use free/open-source software, self-hosted infrastructure, genuinely free tiers, or local-first architecture.

**FORBIDDEN:** Paid cloud databases, paid auth providers, paid email/SMS, paid AI/ML APIs, paid monitoring, paid CI/CD beyond free tier, any service requiring a credit card.

**ALLOWED:** GitHub free tier, Google OAuth, Let's Encrypt, Cloudflare free tier, Vercel/Netlify free hobby tiers, Supabase/Neon/ElephantSQL free tiers, Sentry/Grafana/PostHog free tiers, local dev tools.

---

## 2. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PlannedEducation Platform                          │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│     Frontend (PWA)       │      Backend (FastAPI)   │     Infrastructure    │
│  React 18 + TypeScript   │     Python 3.12+         │   Docker Compose      │
│  Vite build tool         │     SQLAlchemy ORM       │   PostgreSQL          │
│  React Router            │     Pydantic v2          │   Redis               │
│  Workbox Service Worker  │     Presidio (PII scrub) │   nginx (prod)        │
│  IndexedDB (offline)     │     Fernet (field enc)   │   Let's Encrypt (TLS) │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

### 2.1 Data Flow

1. **Client → API:** HTTPS requests with Bearer JWT in `Authorization` header; tokens stored in `sessionStorage` (never `localStorage`)
2. **API → Database:** SQLAlchemy ORM with parameterized queries; field-level Fernet encryption for sensitive columns
3. **API → External AI:** Teacher's API key (encrypted at rest) → PII scrubbed via Presidio → external provider (Gemini, Ollama, OpenRouter, etc.)
4. **API → Client:** Server-sent events / WebSocket for secure chat (digital hand raise), proctoring events batched every 5s
5. **Offline:** IndexedDB caches exam package and answers; syncs on reconnect

---

## 3. Directory Structure

```
PlannedEducation/
├── AGENTS.md                      # Agent guardrails (local, gitignored)
├── AGENTS.local.md                # Local fallback copy of AGENTS.md
├── ARCHITECTURE.md                # THIS FILE — canonical AMD
├── README.md                      # User-facing project overview
├── DEPLOY.md                      # Deployment quick reference
├── VERSION                        # Version number (0.8.8)
├── .env.example                   # Environment variable template (no secrets)
├── .gitignore                     # Git ignore rules
├── .gitleaks.toml                 # Gitleaks configuration
├── Dockerfile.backend             # Backend container image
├── Dockerfile.frontend            # Frontend container image
├── docker-compose.yml             # Multi-service orchestration
├── install.ps1 / install.sh       # Automated installers (Windows/Linux)
├── uninstall.ps1 / uninstall.sh   # Uninstallers
├── pyproject.toml                 # Python project config (ruff, mypy)
├── pytest.ini                     # Pytest configuration
├── run_tests.py                   # Test runner with summary reporting
├── conftest_tracker.py            # Test tracking
├── src/                           # Backend Python package
│   ├── plannededucation/
│   │   ├── api/
│   │   │   ├── main.py            # FastAPI app, middleware, lifespan, routers
│   │   │   ├── models.py          # SQLAlchemy ORM models (all tables)
│   │   │   ├── schemas.py         # Pydantic v2 request/response schemas
│   │   │   ├── database.py        # SQLAlchemy engine, session, Base
│   │   │   ├── db_encryption.py   # Fernet field-level encryption hooks
│   │   │   ├── schema_ensure.py   # Additive schema migrations (versioned)
│   │   │   ├── crypto.py          # Fernet encryption for AI API keys
│   │   │   ├── auth.py            # JWT minting, recovery codes, refresh sessions
│   │   │   ├── authorization.py   # Role-based access policies
│   │   │   ├── limiter.py         # Rate limiting (slowapi)
│   │   │   ├── deployment_config.py # Server-side config (config/deployment.json)
│   │   │   ├── backup_service.py  # Midnight automated DB backups
│   │   │   ├── email_service.py   # Optional SMTP email
│   │   │   ├── home_exam_policy.py # Home-exam platform gate
│   │   │   ├── url_safety.py      # SSRF allowlist + DNS pin
│   │   │   ├── seb_security.py    # Safe Exam Browser hash verification
│   │   │   ├── ocr_service.py     # Tesseract OCR service
│   │   │   ├── stt_service.py     # faster-whisper STT service
│   │   │   ├── handwriting_service.py # Handwriting recognition
│   │   │   ├── archive_utils.py   # Archive compression/encryption
│   │   │   ├── ai_providers.py    # External AI provider abstraction
│   │   │   ├── routes_admin.py    # Admin routes (users, stats, settings)
│   │   │   ├── routes_auth.py     # Auth routes (login, 2FA, reset, WebAuthn)
│   │   │   ├── routes_chat.py     # Secure WebSocket chat (digital hand raise)
│   │   │   ├── routes_exam.py     # Exam CRUD, start, submit, SEB
│   │   │   ├── routes_ai.py       # AI grading with anonymizer + privacy scrub
│   │   │   ├── routes_alerts.py   # Alert management
│   │   │   ├── routes_anonymizer.py # PII scrubbing proxy for AI
│   │   │   ├── routes_archive.py  # Archive/restore sealed submissions
│   │   │   ├── routes_chatgpt.py  # ChatGPT session (device-code OAuth)
│   │   │   ├── routes_notifications.py # In-app notifications
│   │   │   ├── routes_ocr.py      # OCR processing routes
│   │   │   ├── routes_ocr_review.py # OCR teacher review
│   │   │   ├── routes_packages.py # Test package export/import
│   │   │   ├── routes_parent.py   # Parent-child progress
│   │   │   ├── routes_proctoring.py # Proctoring consent, sessions, events
│   │   │   ├── routes_stt.py      # STT processing routes
│   │   │   ├── routes_sync.py     # Sealed offline sync (F-048)
│   │   │   └── chatgpt/           # ChatGPT OAuth client
│   │   │       ├── client.py, crypto.py, history_store.py, models.py, oauth.py, token_store.py
│   │   ├── version.py             # Centralized version from VERSION file
│   │   └── requirements.txt       # Python dependencies
├── web/                           # Frontend
│   └── apps/
│       └── portal/                # React + TypeScript + Vite SPA
│           ├── src/
│           │   ├── main.tsx       # Entry point
│           │   ├── App.tsx        # Route definitions
│           │   ├── api.ts         # Axios client with JWT interceptor
│           │   ├── App.css / index.css
│           │   ├── assets/        # Static assets
│           │   ├── components/    # Reusable UI components
│           │   │   ├── AIKeySettings.tsx, ChatOverlay.tsx, GDPRConsentModal.tsx,
│           │   │   ├── I18nSettings.tsx, LanguageSelector.tsx, Layout.tsx,
│           │   │   ├── NotificationBell.tsx, OCRProcessor.tsx, PackageManager.tsx,
│           │   │   ├── PasskeysSettings.tsx, ProctoringSession.tsx, SecureChat.tsx,
│           │   │   ├── SpecialCharactersPicker.tsx, TeacherChatMonitor.tsx, WatermarkOverlay.tsx, ...
│           │   ├── contexts/      # React context providers
│           │   │   ├── AuthContext.tsx, I18nContext.tsx, ExamContext.tsx,
│           │   │   ├── ThemeContext.tsx, ToastContext.tsx, ChatGptSessionContext.tsx,
│           │   │   └── SpecialCharactersContext.tsx
│           │   ├── hooks/         # Custom React hooks
│           │   │   ├── useKioskMode.ts, useOfflineExam.ts, useOfflineSync.ts,
│           │   │   ├── useProctoring.ts, useQuestionBank.ts
│           │   ├── lib/           # Pure helper modules
│           │   │   ├── dateTime.ts, localFaceGaze.ts, offlineExam.ts,
│           │   │   ├── offlineExamCrypto.ts, offlineExamPlatformKey.ts,
│           │   │   ├── offlineSync.ts, packages.ts, proctoring.ts,
│           │   │   ├── testPackageService.ts, teacherSyncUrl.ts, nameHelper.ts
│           │   ├── pages/         # Route page components
│           │   │   ├── AdminDashboard.tsx, AiIntegration.tsx, AIGradingUpload.tsx,
│           │   │   ├── Dashboard.tsx, ExamEditor.tsx, Help.tsx, Login.tsx,
│           │   │   ├── Messages.tsx, ParentDashboard.tsx, Register.tsx,
│           │   │   ├── ResetPassword.tsx, Settings.tsx, StudentDashboard.tsx,
│           │   │   ├── TakeExam.tsx, TeacherClasses.tsx, TeacherDashboard.tsx,
│           │   │   └── TeacherExams.tsx
│           │   ├── locales/       # i18n translation files (38+ locales)
│           │   │   ├── en/messages.json   # English source of truth (436 keys)
│           │   │   ├── hu/, es/, de/, fr/, ja/, zh/, pt/, uk/, it/, pl/, nl/,
│           │   │   ├── sv/, no/, da/, fi/, pt-BR/, ar, bg, cn, cs, da, el, et,
│           │   │   ├── ga, he, hr, id, ko, lt, lv, mt, ro, ru, sk, sl, th, tr, vi
│           │   │   ├── keyNumbers.ts      # Key number extraction for i18n
│           │   │   └── CONTEXT.md         # Translation context documentation
│           │   ├── utils/         # Utility functions
│           │   │   └── nameHelper.ts
│           │   └── vite-env.d.ts
│           ├── index.html
│           ├── package.json
│           ├── tsconfig.json
│           ├── vite.config.ts
│           └── eslint.config.js
├── plans/                         # Implementation plans & status
│   ├── PLANS_UPDATED.md           # Active plan tracking
│   ├── plans.md                   # Original kickoff plan
│   ├── CURRICULUM_MAPPING.md
│   ├── DEPLOYMENT_ISSUES_LOG.md
│   ├── PROJECT_KICKOFF_COMPLETED.md
│   ├── PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md
│   ├── SECURITY_AUDIT_2026.md
│   ├── TEMP_PROCESS_LOG.md
│   ├── TODO_LIST.md
│   ├── VISUAL_FUNCTION_TESTING.md
│   ├── test-modules/              # Curriculum module packages (.pepkg)
│   │   ├── modules/
│   │   │   ├── australia, austria, belgium, canada, denmark, eu, finland,
│   │   │   ├── germany, hungary, ireland, netherlands, new_zealand, norway,
│   │   │   ├── sweden, switzerland, uk, university, usa
│   │   ├── randomizer-config/
│   │   │   ├── math-randomizer.json, randomizer-guide.md
│   │   └── documentation/
│   │       ├── curriculum-standards.md, deployment-guide.md,
│   │       ├── module-format-spec.md, teacher-guide.md
│   ├── 2026-11-06_2045_SECURITY_LOGIC_AUDIT.md
│   ├── 2026-11-06_AGENT_WORK_STATUS.md
│   ├── 2026-11-06_PENDING_VERIFY.md
│   ├── 2026-11-06_SECURITY_MESSAGING_NOTES.md
│   ├── 2026-11-07_1200_SETTINGS_UX_SECURITY_HELP.md
│   └── 2026-11-07_... (daily status logs)
├── docs/                          # Living documentation (audience-separated)
│   ├── dev/                       # Engineer & security reference
│   │   ├── ARCHITECTURE.md        # System architecture & data models
│   │   ├── SECURITY_ARCHITECTURE.md # Auth, roles, exam integrity, encryption
│   │   ├── MODULE_SYSTEM.md       # .pepkg module format & federation
│   │   ├── I18N_GUIDE.md          # Internationalization guide
│   │   ├── I18N_CONTEXT.md        # Translation key context
│   │   ├── TESTING_GUIDE.md       # Automated test plan & CI/CD
│   │   ├── AI_RISK_GOVERNANCE.md  # NIST AI RMF 1.0 alignment
│   │   ├── NIST_CSF_2_ALIGNMENT.md # NIST CSF 2.0 alignment
│   │   ├── SSDF_COMPLIANCE.md     # NIST SSDF 1.1 alignment
│   │   ├── GITHUB_FREE_TIER.md    # Mandatory free-tier GitHub policy
│   │   ├── HUNGARY_CURRICULUM_RESEARCH.md
│   │   ├── LARGE_TEXT_METHODOLOGY.md
│   │   ├── MARKET_RESEARCH.md
│   │   ├── ORIGIN.md              # Original project prompt
│   │   ├── AUDIT_HISTORY.md       # Audit & fix summary
│   │   └── README.md              # Dev docs index
│   ├── admin/                     # School IT / operator manuals
│   │   ├── DEPLOYMENT_GUIDE.md    # Master deployment reference
│   │   ├── INSTALL_WINDOWS.md     # Windows installation
│   │   ├── INSTALL_LINUX.md       # Linux installation
│   │   ├── INSTALL_COMPATIBILITY.md
│   │   ├── BACKUP_RESTORE.md      # Database backups & disaster recovery
│   │   └── runbooks/              # Incident response runbooks (RB-001 to RB-010)
│   └── user/                      # Teacher, student, parent guides
│       ├── TEACHER_GUIDE.md
│       ├── STUDENT_GUIDE.md
│       ├── PARENT_GUIDE.md
│       └── FAQ.md
├── scripts/                       # Automation scripts
│   ├── testing/                   # Test runners & cache helpers
│   │   ├── update_test_cache.py   # Source-aware pytest cache wrapper
│   │   ├── module_test_runner.py  # Smart caching for visual/module tests
│   │   ├── canary.py, smoke_test.py, run_pip_audit.py, ...
│   ├── dev/                       # Dev server scripts
│   │   ├── start.ps1, start_all.ps1, start_student.ps1, stop.ps1, stop_student.ps1
│   ├── deploy/                    # Deployment scripts
│   │   ├── deploy_wizard.py, deploy_docker.sh, setup_admin.py
│   ├── i18n/                      # Translation helpers
│   │   ├── add_i18n_keys.py, translate_*.py, verify_all_locales.py, ...
│   └── backup/                    # Backup/restore scripts
│       ├── backup_restore.ps1, backup_restore.sh, backup_restore_drill.ps1, backup_restore_drill.sh
├── tests/                         # Backend pytest suites
│   ├── conftest.py                # Per-process SQLite test DB
│   ├── test_auth.py, test_auth_flows.py, test_exams.py, test_chat.py,
│   ├── test_routes_*.py, test_security_*.py, test_teacher_*.py, ...
├── tests/e2e/                     # E2E test suites (local only, gitignored)
├── scratch/                       # Scratch logs, temp files (local only, gitignored)
├── artifacts/                     # Test artifacts, cache (local only, gitignored)
├── local-secrets/                 # Local credentials (gitignored)
├── logs/                          # Runtime logs
├── backups/                       # Database backups
├── data/                          # Runtime data
├── config/                        # Deployment config (deployment.json)
├── curriculum_docs/               # Curriculum documentation
├── pepkg/                         # Test package format
├── united_earth/                  # Related project reference
└── UnitedEarth/                   # Related project reference
```

---

## 4. Backend Architecture (FastAPI)

### 4.1 Application Entry Point

**File:** `src/plannededucation/api/main.py`

- Creates the FastAPI application instance
- Configures CORS (restricted to explicit origins, never `*` in production)
- Adds `SecurityHeadersMiddleware` (CSP, HSTS, X-Frame-Options, etc.)
- Adds `TrustedHostMiddleware` in production
- Configures OpenTelemetry tracing and Prometheus metrics
- Registers all API routers under `/api/v1` prefix
- Lifespan context: initializes DB schema (`create_all` + `ensure_schema`), starts chat Redis pub/sub, starts midnight backup scheduler

### 4.2 Router Map

| Router | Prefix | Tags | Responsibility |
|--------|--------|------|----------------|
| `routes_auth` | `/auth` | auth | Login, 2FA, password reset, WebAuthn, recovery codes, AI key management |
| `routes_exam` | `/exams` | exams | Exam CRUD, start, submit, SEB config, delivery mode |
| `routes_anonymizer` | `/anonymizer` | anonymizer | PII scrubbing proxy for AI boundary |
| `routes_proctoring` | `/proctoring` | proctoring | GDPR consent, sessions, events, stats |
| `routes_packages` | `/packages` | packages | Test package export/import/validation |
| `routes_ocr` | `/ocr` | ocr | OCR processing (Tesseract) |
| `routes_stt` | `/stt` | speech-to-text | STT processing (faster-whisper) |
| `routes_chat` | `/chat` | chat | Secure WebSocket chat (digital hand raise) |
| `routes_admin` | `/admin` | admin | User management, stats, deployment config |
| `routes_ai` | `/ai` | ai | AI grading with ownership + privacy scrub |
| `routes_archive` | `/archive` | archive | Archive/restore sealed submissions |
| `routes_parent` | `/parents` | parents | Parent-child relationships, progress |
| `routes_notifications` | `/notifications` | notifications | In-app notifications, password reset requests |
| `routes_alerts` | `/alerts` | alerts | Alert management (webhook-gated) |
| `routes_ocr_review` | `/ocr-review` | ocr-review | OCR teacher review workflow |
| `routes_sync` | `/sync` | sync | Sealed offline sync (F-048) |
| `routes_chatgpt` | `/chatgpt` | chatgpt | ChatGPT session (device-code OAuth) |

### 4.3 Database Models (SQLAlchemy ORM)

**File:** `src/plannededucation/api/models.py`

All models inherit from `Base` (declarative base). UUID primary keys (`String(36)`). Timezone-aware `DateTime` UTC timestamps.

| Model | Table | Key Fields | Encrypted Fields |
|-------|-------|------------|------------------|
| `User` | `users` | id, username, email, google_id, hashed_password, role, is_admin, is_superadmin, teacher_approved, totp_secret, recovery_codes, ai_api_key_encrypted, refresh_token_hash, webauthn_credentials, failed_login_attempts, locked_until | `totp_secret`, `recovery_codes`, `ai_api_key_encrypted`, `webauthn_credentials`, `refresh_token_hash` |
| `UserSession` | `user_sessions` | id, user_id, token_hash, token_encrypted, device_id_hash, device_info, expires_at, remember_me | `token_encrypted` |
| `RefreshSession` | `refresh_sessions` | id, user_id, token_hash, family_id, device_label, created_at, expires_at, revoked_at, replaced_by | `token_hash` |
| `AccountRelationship` | `account_relationships` | id, student_id, parent_id, teacher_id, student_approved, parent_approved, teacher_approved, status | — |
| `ClassGroup` | `class_groups` | id, name, teacher_id | — |
| `ClassMembership` | `class_memberships` | id, class_group_id, student_id, created_at | — |
| `StudentRecord` | `student_records` | id, student_id, time_multiplier | — |
| `Exam` | `exams` | id, title, description, duration_minutes, teacher_id, seb_config_key, home_exam_enabled, created_at | — |
| `Question` | `questions` | id, exam_id, question_type, text, options_json, correct_answer, rubric, points | `correct_answer`, `rubric` (never returned to students) |
| `ExamSubmission` | `exam_submissions` | id, exam_id, student_id, started_at, deadline_at, completed_at, score, feedback | `feedback` |
| `Answer` | `answers` | id, submission_id, question_id, student_response, generated_question_text, generated_options_json | — |
| `Course` | `courses` | id, name, description, teacher_id | — |
| `ProctoringSession` | `proctoring_sessions` | id, submission_id, student_id, exam_id, consent_given, camera_enabled, microphone_enabled, total_events, violation_count | — |
| `ProctoringEvent` | `proctoring_events` | id, session_id, event_type, timestamp, severity, event_data, screenshot_ref, audio_ref | — |
| `ProctoringConsent` | `proctoring_consents` | id, student_id, exam_id, consent_given, camera_consent, microphone_consent, screen_recording_consent, data_processing_consent, withdrawn | — |
| `Package` | `packages` | id, name, version, description, category, subject, grade_level, tags, license, package_data, checksum, author_id, status, is_public | — |
| `PackageRating` | `package_ratings` | id, package_id, user_id, rating, review | — |
| `PackageDownload` | `package_downloads` | id, package_id, user_id, source_type, downloaded_at, ip_hash | — |
| `School` | `schools` | id, name, domain, address, contact_email, header_image_url, header_text, header_display_mode | — |
| `PackageSource` | `package_sources` | id, name, url, api_key, source_type, is_enabled, school_id | `api_key` |
| `Alert` | `alerts` | id, fingerprint, alertname, status, severity, labels_json, annotations_json, starts_at, ends_at | — |
| `ArchivedSubmission` | `archived_submissions` | id, submission_id, exam_id, student_id, teacher_id, archive_year, archive_month, archive_path, compressed_data, original_size, compressed_size, encryption_algorithm, encryption_iv, encryption_salt, key_id, content_hash, archive_hash, status | `compressed_data` |
| `ArchiveJob` | `archive_jobs` | id, job_type, status, graduation_year, teacher_id, student_id, total_items, processed_items, failed_items, result_summary | — |
| `InAppNotification` | `in_app_notifications` | id, user_id, title, message, type, is_read, link, action_payload, created_at | `message`, `action_payload` |
| `OCRReview` | `ocr_reviews` | id, submission_id, exam_id, student_id, teacher_id, original_text, original_confidence, corrected_text, review_notes, status, anonymized, ai_graded | `original_text`, `corrected_text` |
| `SealedSyncSubmission` | `sealed_sync_submissions` | id, exam_id, student_id, content_hash, sync_hash, payload_json, payload_bytes, created_at, updated_at | `payload_json` |

### 4.4 Enumerations

| Enum | Values |
|------|--------|
| `UserRole` | student, teacher, teacher_aide, parent, admin |
| `QuestionType` | multiple_choice, essay, dynamic_math |
| `RelationshipStatus` | pending, active, rejected |
| `ArchiveStatus` | active, archived, deleted |
| `PackageCategory` | mathematics, chemistry, biology, physics, computer_science, languages, history, geography, literature, arts, health_pe, economics, philosophy, other |
| `PackageStatus` | draft, published, archived |
| `ProctoringEventType` | face_detected, face_lost, multiple_faces, eye_movement, gaze_off_screen, audio_anomaly, tab_switch, window_blur, fullscreen_exit, seb_violation, session_start, session_end |
| `AlertSeverity` | critical, warning, info |
| `AlertStatus` | firing, resolved |
| `OCRReviewStatus` | pending, reviewing, approved, rejected, corrected |

### 4.5 Schema Assurance (Additive Migrations)

**File:** `src/plannededucation/api/schema_ensure.py`

- Versioned migration ledger stored in `schema_migrations` table
- 6 migrations: user columns, exam deadlines/answer fields, password reset columns, refresh sessions, sealed sync submissions, home exam flag
- `create_all` creates missing tables; `ensure_schema` applies additive column/table migrations
- Fails closed on schema drift (missing required tables/columns)
- Never destructive — no `DROP` or data-wiping migrations

### 4.6 Field-Level Encryption

**File:** `src/plannededucation/api/db_encryption.py`

- Fernet (AES-128 CBC + HMAC) for sensitive database columns
- Controlled by `DATABASE_ENCRYPTION=true` + `DB_ENCRYPTION_MASTER_KEY` env vars
- Required in production/staging (fail closed if missing)
- Versioned envelope prefix `pe-db-v1$` for new encrypted values
- SQLAlchemy event listeners: `before_insert`/`before_update` encrypt, `load`/`refresh`/`after_insert`/`after_update` decrypt
- `register_encrypted_model(model_class, fields)` registers models with encrypted fields

### 4.7 Authentication & Authorization

**Files:** `src/plannededucation/api/auth.py`, `src/plannededucation/api/routes_auth.py`, `src/plannededucation/api/authorization.py`

#### Authentication Flow

1. **Google SSO (primary):** OAuth2/OIDC via Google; no passwords stored for login
2. **Password fallback:** Argon2id hash (time_cost=3, memory_cost=64MB, parallelism=4); used only for self-service reset
3. **JWT tokens:** HS256, 60-minute access tokens, `type: "access"` claim
4. **Refresh tokens:** 30-day (365-day with "remember me"), per-device `RefreshSession` with rotation families (F-049)
5. **TOTP 2FA:** RFC 6238 via `pyotp`, 30-second window, 5 one-time recovery codes
6. **WebAuthn/Passkeys:** FIDO2 phishing-resistant second factor (platform authenticators)

#### Authorization Model

| Role | Can Create | Can Approve | Can Manage Exams | Can View |
|------|-----------|-------------|------------------|----------|
| Student | — | — | — | Own submissions, own results |
| Teacher | Exams, questions, packages | — | Own exams (after approval) | Own classes, own submissions |
| Teacher Aide | — | — | Shared exams only | Shared exams |
| Parent | Relationship requests | Children (own) | — | Children's progress (active links only) |
| Admin | Users, exams, settings | Teachers | All exams | All system data |
| Superadmin | Admins, superadmins | Teachers | All exams | All system data |

**Key authorization helpers:**
- `require_exam_author(user)` — approved teacher or admin (F-014)
- `require_admin(user)` — `is_admin=True`
- `require_superadmin(user)` — `is_admin AND is_superadmin` (only role that can create admins/superadmins)
- `_require_exam_owner(exam, user)` — exam owner or admin (IDOR protection)

**Teacher approval:** Fail-closed. Self-registered teachers have `teacher_approved=False`; admin must approve before exam authoring.

### 4.8 Rate Limiting

**File:** `src/plannededucation/api/limiter.py`

- `slowapi` Limiter, disabled in test environment
- Key function: client IP (with fallback to `127.0.0.1`)
- Route-level limits: 10/min register, 20/min login, 5/min reset request, 10/min reset confirm, 30/min OCR, 10/min STT, 20/min AI, 200/hour AI

### 4.9 Security Controls

| Control | Implementation | File |
|---------|---------------|------|
| SEB hash verification | `X-SafeExamBrowser-RequestHash` = SHA256(url + seb_config_key) | `seb_security.py` |
| SEB dev bypass | Requires `PLANNED_EDUCATION_ENV ∈ {development,test}` AND `ALLOW_DEV_SEB_BYPASS=true` | `seb_security.py` |
| Timing-safe comparison | `hmac.compare_digest` | `seb_security.py`, `auth.py` |
| PII scrubbing | Microsoft Presidio Analyzer + native span redaction; fail-closed | `routes_anonymizer.py` |
| Prompt injection detection | 20+ regex patterns on teacher prompts | `routes_ai.py` |
| SSRF protection | URL allowlist + DNS pin / rebind check | `url_safety.py` |
| Path containment | `Path.is_relative_to()` for module/package paths | `routes_packages.py` |
| Upload size caps | 5 MiB upload, 20 MiB decompressed (gzip bomb protection) | `routes_packages.py` |
| CSP | Production omits `unsafe-inline`/`unsafe-eval` for scripts | `main.py` |
| Security headers | HSTS, X-Frame-Options: DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy | `main.py` |
| Structured JSON logging | Security events, request IDs, user IDs, IPs | `main.py` |

---

## 5. Frontend Architecture (React + TypeScript + Vite)

### 5.1 Application Entry

**File:** `web/apps/portal/src/main.tsx`

- React 18 with `BrowserRouter`
- Providers: `AuthProvider`, `ThemeProvider`, `ToastProvider`, `ChatGptSessionProvider`, `ExamProvider`, `SpecialCharactersProvider`
- Route definitions in `App.tsx`

### 5.2 Route Map

| Path | Component | Access |
|------|-----------|--------|
| `/login` | `Login` | Public |
| `/register` | `Register` | Public |
| `/reset-password` | `ResetPassword` | Public |
| `/help` | `Help` | Public |
| `/` | `Dashboard` | Authenticated |
| `/settings` | `Settings` | Authenticated |
| `/exam` | `StudentDashboard` | Student |
| `/exam/:id` | `TakeExam` | Student |
| `/teacher-exams` | `TeacherExams` | Teacher |
| `/teacher-exams/:id` | `ExamEditor` | Teacher |
| `/teacher-dashboard/:examId` | `TeacherDashboard` | Teacher |
| `/teacher-classes` | `TeacherClasses` | Teacher |
| `/parent-dashboard` | `ParentDashboard` | Parent |
| `/ai-integrations` | `AiIntegration` | Teacher/Admin |
| `/ai-grading` | `AIGradingUpload` | Teacher |
| `/messages` | `Messages` | Authenticated |
| `/admin` | `AdminDashboard` | Admin/Superadmin |

### 5.3 Context Providers

| Context | Responsibility |
|---------|---------------|
| `AuthContext` | User session, JWT in sessionStorage, login/logout, `refreshUser()` |
| `I18nContext` | Locale management, `t()` translation function, `showNumbers` toggle |
| `ExamContext` | Current exam state, questions, submission data |
| `ThemeContext` | UI theme (light/dark) |
| `ToastContext` | Toast notifications |
| `ChatGptSessionContext` | ChatGPT OAuth session |
| `SpecialCharactersContext` | Special characters picker state |

### 5.4 Key Components

| Component | Purpose |
|-----------|---------|
| `Layout.tsx` | Main shell with header, sidebar, navigation |
| `ProtectedRoute.tsx` | Route guard for authenticated pages |
| `Login.tsx` | Google SSO + password login, passkey button |
| `Register.tsx` | User registration with password strength validation, recovery codes |
| `Dashboard.tsx` | Role-based dashboard (student/teacher/parent/admin) |
| `ExamEditor.tsx` | Full CRUD for exams and questions, dynamic math variables |
| `TakeExam.tsx` | Secure exam taking interface, SEB integration, offline support |
| `TeacherDashboard.tsx` | Submission review, AI grading, mistake grouping |
| `TeacherExams.tsx` | Exam list, publish, SEB config |
| `StudentDashboard.tsx` | Upcoming exams, results |
| `ParentDashboard.tsx` | Children's progress, relationship management |
| `Settings.tsx` | User settings, 2FA, passkeys, AI keys, appearance |
| `AdminDashboard.tsx` | User management, system stats, deployment config |
| `PackageManager.tsx` | Test package export/import, catalog browsing |
| `ProctoringSession.tsx` | Proctoring UI with camera/mic toggle, GDPR consent |
| `SecureChat.tsx` | WebSocket chat for digital hand raise during exams |
| `SpecialCharactersPicker.tsx` | Math/chemistry/physics/Greek/accents picker |
| `OCRProcessor.tsx` / `OCRReview.tsx` | OCR processing and teacher review |
| `GDPRConsentModal.tsx` | Proctoring consent flow |
| `WatermarkOverlay.tsx` | Screen watermark (anti-sharing, intentional PII display) |
| `NotificationBell.tsx` | In-app notification badge (60s polling) |
| `I18nSettings.tsx` / `LanguageSelector.tsx` | Locale selection |
| `PasskeysSettings.tsx` / `TwoFASettings.tsx` | WebAuthn/TOTP management |
| `AIKeySettings.tsx` | AI provider API key configuration |
| `ChatOverlay.tsx` | Compact chat dock during exam |
| `TeacherChatMonitor.tsx` | Teacher view of student chat messages |
| `DatabaseBackupPanel.tsx` | Admin backup management |
| `DeploymentConfigPanel.tsx` | Server-side deployment configuration |
| `FAQChatbot.tsx` | In-app FAQ assistant |
| `CreateUserModal.tsx` | Admin user creation |
| `TeacherApprovalPanel.tsx` | Teacher approval workflow |
| `AdminBackupCodesModal.tsx` | Admin recovery code management |
| `ForgotPasswordModal.tsx` | Password reset request |
| `InfoTip.tsx` | Contextual help tips |
| `MessageIcon.tsx` | Messages navigation icon |

### 5.5 Custom Hooks

| Hook | Purpose |
|------|---------|
| `useOfflineExam.ts` | Offline exam engine, IndexedDB persistence, auto-sync |
| `useOfflineSync.ts` | Offline sync logic |
| `useProctoring.ts` | Proctoring event pipeline, consent management |
| `useQuestionBank.ts` | Question bank management |
| `useKioskMode.ts` | Kiosk/exam lockdown mode |

### 5.6 Service Modules

| Module | Purpose |
|--------|---------|
| `api.ts` | Axios client with JWT interceptor, 401 handling |
| `offlineExam.ts` | Offline exam storage and retrieval |
| `offlineExamCrypto.ts` | Offline exam encryption (AES-GCM) |
| `offlineExamPlatformKey.ts` | Platform key management for offline exams |
| `offlineSync.ts` | Offline data synchronization |
| `packages.ts` | Test package service (export/import/validate) |
| `proctoring.ts` | Proctoring API client |
| `testPackageService.ts` | Test package validation |
| `teacherSyncUrl.ts` | LAN teacher sync URL allowlist validation |
| `localFaceGaze.ts` | Local face/gaze detection (MediaPipe fallback) |
| `dateTime.ts` | Date/time formatting utilities |
| `nameHelper.ts` | Name formatting helpers |

### 5.7 i18n System

**File:** `web/apps/portal/src/contexts/I18nContext.tsx`

- **Key format:** `page.element` (e.g., `login.1`, `dashboard.3`, `settings.12.3`)
- **Translation files:** `web/apps/portal/src/locales/<locale>/messages.json`
- **English source:** `en/messages.json` (436 keys, source of truth)
- **Supported locales (38+):** en, ar, bg, cn, cs, da, de, el, es, et, fi, fr, ga, he, hr, hu, id, it, ja, ko, lt, lv, mt, nl, no, pl, pt, pt-BR, ro, ru, sk, sl, sv, th, tr, uk, vi
- **Usage:** `const { t } = useI18n(); t("login.1")`
- **No hardcoded user-facing text** — all strings must go through `t()`
- **`showNumbers` toggle:** Displays `[key]` badges on UI elements for translator context
- **`jumpToElement(key)`:** Scrolls to element with `data-i18n-key` attribute

---

## 6. Module System (.pepkg)

**Reference:** `docs/dev/MODULE_SYSTEM.md`, `plans/test-modules/`

### 6.1 Module Format

A PlannedEducation Module is a portable, self-contained educational package (`.pepkg.json` or `.pepkg.yaml`) containing:

- **Metadata:** Title, version, author, subject, category, grade level, license (CC-BY-4.0 default)
- **Questions:** Multiple choice, dynamic math (`[rand:2-10]`), essay with rubrics
- **Integrity:** SHA-256 checksum for tamper detection
- **No student data:** Modules contain only questions, rubrics, and curriculum metadata

### 6.2 Supported Categories

Mathematics, Physics, Chemistry, Biology, Computer Science, Languages, History, Geography, Literature, Arts, Health & PE, Economics, Philosophy, Other

### 6.3 Teacher Workflow

1. **Create Exam** → **Export Package** → Download `.pepkg.json`
2. **Import Package** → Validate structure + checksum → Create new exam
3. **Publish to Catalog** → Share with colleagues on school server
4. **School Federation** → Configure partner school sources → Sync modules across schools

### 6.4 Module Storage

- **Local modules:** `plans/test-modules/modules/<country>/`
- **Countries:** australia, austria, belgium, canada, denmark, eu, finland, germany, hungary, ireland, netherlands, new_zealand, norway, sweden, switzerland, uk, university, usa
- **Hungary:** 52 modules across 12 grades (STEM focus)
- **Randomizer config:** `plans/test-modules/randomizer-config/math-randomizer.json`

---

## 7. Security Architecture

**Reference:** `docs/dev/SECURITY_ARCHITECTURE.md`

### 7.1 Authentication & Session Tokens

| Control | Behavior |
|---------|----------|
| Access JWT | `type: "access"` claim; REST and WebSocket auth reject other types |
| Refresh JWT | `type: "refresh"`; validated through `/auth/refresh` with per-device rotation/reuse detection |
| Browser storage | Tokens in `sessionStorage`; legacy `localStorage` tokens migrated once then removed |
| Password hashing | Argon2id (time_cost=3, memory_cost=64MB, parallelism=4) |
| TOTP 2FA | `pyotp` RFC 6238; required when `totp_enabled` |
| WebAuthn login | Unauthenticated start/finish issues tokens after assertion |
| Recovery codes | High-entropy, stored hashed, single-use |
| Brute-force lockout | 5 failed attempts → 15-minute lockout |
| Logout / password change | Revokes refresh session(s) |

### 7.2 Roles & Authorization

| Role | Granted By | Can Do |
|------|-----------|--------|
| Student | Self-register | Take exams, view own results |
| Teacher | Self-register + admin approval | Author exams, grade, class tools |
| Parent | Self-register | Link children, view progress (active links only) |
| Admin | Superadmin creates | User/ops admin; cannot create other admins |
| Superadmin | Bootstrap installer | Create admins/superadmins; highest privilege |

### 7.3 Exam Integrity

| Control | Status |
|---------|--------|
| SEB request hash verification | Fixed (F-001) |
| SEB dev bypass (dev+test only, with flag) | Fixed |
| Student-only start/submit | Fixed (F-015) |
| Server-enforced deadline (UTC-normalized) | Fixed (F-015) |
| Offline package metadata (authoritative) | Fixed (F-016) |
| Offline seal crypto (AES-GCM) | Fixed (F-017) |

### 7.4 Field Encryption & Privacy

| Control | Status |
|---------|--------|
| Fernet field encryption (DB_ENCRYPTION_MASTER_KEY) | Enabled path fixed; production requires encryption on |
| Direct messages encrypted at rest | Working |
| External AI boundary (Presidio scrub, fail-closed) | Fixed (F-013) |
| Archive at-rest encryption (AES-GCM, ARCHIVE_MASTER_KEY) | Fixed (F-024) |
| Database backups (PEBAK1 AES-GCM, BACKUP_MASTER_KEY) | Fixed (F-033) |

### 7.5 OWASP Top 10:2025 Alignment

| Category | Control | Implementation |
|----------|---------|----------------|
| A01 Broken Access Control | Deny by default, RBAC, row-level | `_require_exam_owner`, `AccountRelationship`, teacher-only mutations |
| A02 Cryptographic Failures | TLS 1.3, Argon2id, Fernet, JWT HS256 | Argon2id, Fernet for AI keys, JWT 60-min expiry |
| A03 Injection | Parameterized queries, input validation | SQLAlchemy ORM, Pydantic schemas, no raw SQL |
| A04 Insecure Design | Threat modeling, secure defaults | Security audit logging, rate limiting, constant-time comparisons |
| A05 Security Misconfiguration | Secure headers, no debug in prod | CSP, HSTS, TrustedHostMiddleware, Swagger disabled in prod |
| A06 Vulnerable Components | Dependency scanning, locked versions | `pip-audit`, `npm audit`, pinned deps |
| A07 Authentication Failures | MFA, passkeys, brute force | Google SSO, TOTP 2FA, recovery codes, rate limiting |
| A08 Software/Data Integrity | CI/CD integrity, signed artifacts, SBOM | Pinned deps, cosign signing, SLSA Level 3 |
| A09 Logging/Monitoring | Structured JSON logs, security events | Request ID middleware, audit logs, global exception handler |
| A10 Exceptional Conditions | Generic errors, no stack traces | Generic 500 with request_id |

---

## 8. API Design

### 8.1 Base URL

- Development: `http://127.0.0.1:8000/api`
- Production: `https://<school-domain>/api`
- Configured via `VITE_API_URL` env var (frontend) and `CORS_ORIGINS` (backend)

### 8.2 Authentication

All protected endpoints require `Authorization: Bearer <access_token>` header. Tokens obtained via:
- `POST /auth/token` (password login)
- Google SSO callback
- WebAuthn login start/finish

### 8.3 Key Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/auth/token` | Password login (returns access+refresh tokens) | No |
| `POST` | `/auth/refresh` | Refresh token rotation | Refresh token |
| `POST` | `/auth/logout` | Revoke refresh session | Access token |
| `GET` | `/auth/me` | Get current user | Access token |
| `POST` | `/auth/2fa/setup` | TOTP setup (secret + QR + recovery codes) | Access token |
| `POST` | `/auth/2fa/confirm` | Verify TOTP to enable | Access token + TOTP |
| `POST` | `/auth/password-reset/request` | Request email OTP reset | No |
| `POST` | `/auth/password-reset/confirm` | Confirm OTP reset | No |
| `GET` | `/exams/` | List exams (metadata only, no answers) | Access token |
| `POST` | `/exams/` | Create exam | Approved teacher |
| `GET` | `/exams/{id}` | Get exam details | Owner or admin |
| `PUT` | `/exams/{id}` | Update exam | Owner or admin |
| `DELETE` | `/exams/{id}` | Delete exam | Owner or admin |
| `POST` | `/exams/{id}/start` | Start exam (returns package + deadline) | Student |
| `POST` | `/exams/{id}/submit` | Submit exam (server-enforced deadline) | Student |
| `POST` | `/anonymizer/scrub` | PII scrubbing for AI boundary | Access token |
| `POST` | `/proctoring/consent` | GDPR consent for proctoring | Student |
| `POST` | `/proctoring/sessions` | Start proctoring session | Student |
| `POST` | `/proctoring/events` | Batch proctoring events | Student |
| `GET` | `/packages/` | List available packages | Access token |
| `POST` | `/packages/import` | Import test package | Approved teacher |
| `GET` | `/ocr/process` | OCR processing | Access token |
| `POST` | `/stt/transcribe` | Speech-to-text | Access token |
| `WS` | `/chat/{exam_id}` | Secure WebSocket chat | Access token + exam access |
| `GET` | `/admin/stats` | System statistics | Admin |
| `GET` | `/parents/children-progress` | Children's progress | Parent |

### 8.4 Response Conventions

- All timestamps are ISO 8601 UTC
- UUIDs as strings
- Paginated list responses where applicable
- Error responses: `{"detail": "human-readable message"}` with appropriate HTTP status
- Never return `correct_answer`, `rubric`, `hashed_password`, `totp_secret`, `recovery_codes`, `ai_api_key_encrypted` to students

---

## 9. Data Flow Diagrams

### 9.1 Exam Creation Flow

```
Teacher → ExamEditor (UI) → POST /exams/ → API validates ownership → 
SQLAlchemy creates Exam + Questions → DB (encrypted fields) → 
201 Created → Teacher sees exam in TeacherExams
```

### 9.2 Exam Taking Flow (with SEB)

```
Student → TakeExam (UI) → POST /exams/{id}/start → 
SEB hash verification → Server creates ExamSubmission + deadline_at → 
Returns exam_package (questions, no answers) → 
Student answers → IndexedDB auto-save → 
POST /exams/{id}/submit → Server checks deadline → 
Score calculated → Submission stored
```

### 9.3 AI Grading Flow (with Privacy)

```
Teacher → TeacherDashboard → POST /ai/grade → 
API fetches submission → scrub_pii() (Presidio, fail-closed) → 
External AI provider (teacher's encrypted API key) → 
AI returns suggested score/feedback → 
Teacher reviews → Approve/Edit/Reject → 
POST /ai/grades → Save to ExamSubmission.score/feedback
```

### 9.4 Proctoring Flow (GDPR Consent)

```
Student → GDPRConsentModal → POST /proctoring/consent → 
Consent record stored → POST /proctoring/sessions → 
Session started → Client sends events (batched every 5s) → 
POST /proctoring/events → Server validates types/severities → 
Stored in ProctoringEvent → Teacher views stats
```

---

## 10. Deployment Architecture

### 10.1 Deployment Modes

| Mode | Database | Cache | Best For |
|------|----------|-------|----------|
| Mode 1: Lightweight | SQLite | In-memory | Single classrooms, trials |
| Mode 2: Native Self-Hosted | PostgreSQL | Redis | Full school networks |
| Mode 3: Docker Compose | PostgreSQL (container) | Redis (container) | Production servers, cloud VMs |

### 10.2 Installation

- **Windows:** `powershell -ExecutionPolicy Bypass -File .\install.ps1`
- **Linux:** `bash ./install.sh`
- **Docker:** `docker compose up -d --build`
- **Cross-platform wizard:** `python scripts/deploy/deploy_wizard.py`

### 10.3 Configuration

**File:** `config/deployment.json` (server-side editable, no redeploy needed)

Settings: school_name, domain, api_port, frontend_port, cors_origins, allowed_hosts, environment, smtp settings, backup config, admin_support_email, home_exam_proctoring_enabled

**Environment variables (`.env`):** DATABASE_URL, JWT_SECRET_KEY, AI_KEY_MASTER_SECRET, DB_ENCRYPTION_MASTER_KEY, ARCHIVE_MASTER_KEY, BACKUP_MASTER_KEY, etc.

### 10.4 Update-in-Place Policy

Re-running installers on an existing deployment MUST:
- Keep existing database, `.env` secrets, logs, uploads, backups
- Only refresh application code and apply additive schema updates
- Never `DROP` or wipe the live database

---

## 11. Testing Strategy

**Reference:** `docs/dev/TESTING_GUIDE.md`

### 11.1 Test Categories

| Layer | Tool | Location | Coverage Target |
|-------|------|----------|-----------------|
| Backend Unit | pytest | `tests/test_*.py` | > 80% |
| Frontend Unit | vitest | `web/apps/portal/src/**/*.test.ts` | > 70% |
| API Integration | pytest | `tests/test_routes_*.py` | 100% endpoints |
| E2E / Visual | Playwright | `web/apps/portal/tests/visual/` | 100% critical paths |

### 11.2 Test Execution (MANDATORY)

All Python test invocations MUST use the cache wrapper:

```powershell
C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "<suite>" -- C:/.venv/Scripts/python.exe -m pytest <test-path> -q
```

Never run raw `pytest` directly.

### 11.3 Test Database

- Per-process SQLite file: `test_plannededucation_<pid>.db`
- `tests/conftest.py` creates/drops tables per session
- Never leave `next(get_db())` generators open (SQLite lock source)

### 11.4 CI/CD Pipeline

**File:** `.github/workflows/ci.yml`

Jobs: backend-tests, frontend-tests, security-scans, container-scans, sbom-generation, artifact-signing, slsa-provenance, summary

**Security Checks:** `.github/workflows/security-checks.yml`

Jobs: python-pip-audit, npm-audit-portal, gitleaks (OSS binary only)

---

## 12. Development Conventions

### 12.1 File Size & Modularity

| Band | Lines | Guidance |
|------|-------|----------|
| Prefer | ≤ ~400 | Sweet spot for most files |
| Fine | ~401–600 | One clear concern |
| OK if justified | > ~600 | Cohesive module, document why |
| Smell | ≫ ~800–1000+ | Strongly prefer split |

**Split patterns:**
- React page shell → `web/apps/portal/src/pages/FooPage.tsx`
- UI section → `web/apps/portal/src/components/<domain>/`
- Hook / WS / data load → `web/apps/portal/src/hooks/`
- Pure helpers → `web/apps/portal/src/lib/` or `src/utils/`
- FastAPI routes → `src/plannededucation/api/<domain>.py`
- Domain services → `src/plannededucation/services/<topic>.py`
- Schemas / models → `src/plannededucation/api/schemas.py`

### 12.2 i18n (MANDATORY)

No hardcoded user-facing text in frontend. All strings via `t()` from `I18nContext`.

### 12.3 Security (apply on every change)

- No plaintext secrets; use environment variables
- Parameterized queries only (SQLAlchemy ORM)
- Fernet encryption for sensitive fields
- Argon2id for password hashing
- Rate limiting on auth routes
- CSP headers; no `unsafe-eval`
- Never log PII, passwords, tokens, API keys

### 12.4 Branch & Git

- Default branch: `dev`; `main` is stable release
- Do NOT push to `main` without explicit user request
- Clean working tree before finishing
- No dev/test artifacts in GitHub or deployments (see AGENTS.md §14)

### 12.5 Process Management

- Kill orphaned node/python/uvicorn processes after every command
- Max 30 minutes for background processes without interaction
- All long-running processes must show progress output

---

## 13. Documentation Map

| Document | Audience | Location |
|----------|----------|----------|
| ARCHITECTURE.md (this file) | Developers, agents | Repository root |
| AGENTS.md | AI agents, contributors | Repository root (local, gitignored) |
| README.md | Users, contributors | Repository root |
| DEPLOY.md | Operators | Repository root |
| SECURITY_ARCHITECTURE.md | Security reviewers | `docs/dev/` |
| MODULE_SYSTEM.md | Module developers | `docs/dev/` |
| I18N_GUIDE.md | Translators, developers | `docs/dev/` |
| TESTING_GUIDE.md | QA engineers | `docs/dev/` |
| AI_RISK_GOVERNANCE.md | AI safety reviewers | `docs/dev/` |
| NIST_CSF_2_ALIGNMENT.md | Compliance auditors | `docs/dev/` |
| SSDF_COMPLIANCE.md | Secure SDLC auditors | `docs/dev/` |
| GITHUB_FREE_TIER.md | CI/CD operators | `docs/dev/` |
| DEPLOYMENT_GUIDE.md | School IT admins | `docs/admin/` |
| INSTALL_WINDOWS.md / INSTALL_LINUX.md | Installers | `docs/admin/` |
| BACKUP_RESTORE.md | Operators | `docs/admin/` |
| Runbooks (RB-001 to RB-010) | Incident responders | `docs/admin/runbooks/` |
| TEACHER_GUIDE.md | Teachers | `docs/user/` |
| STUDENT_GUIDE.md | Students | `docs/user/` |
| PARENT_GUIDE.md | Parents | `docs/user/` |
| FAQ.md | All users | `docs/user/` |

---

## 14. AMD Maintenance

This AMD file is the **canonical architectural specification**. It must be:

1. **Updated with every edit** — new modules, functions, routes, models, or components
2. **Kept in sync with AGENTS.md** — AGENTS.md references this file for logic
3. **Reviewed before merges** — ensure no architectural drift
4. **Versioned** — version matches `VERSION` file

**Update trigger:** Any change to:
- Backend routes, models, schemas, or services
- Frontend pages, components, hooks, contexts, or services
- Database schema or migrations
- Authentication or authorization logic
- Security controls or headers
- Deployment configuration or installers
- i18n keys or locales
- Module format or randomizer config

---

## 15. Appendix: Key Files Quick Reference

| Concern | File(s) |
|---------|---------|
| App entry (backend) | `src/plannededucation/api/main.py` |
| ORM models | `src/plannededucation/api/models.py` |
| Pydantic schemas | `src/plannededucation/api/schemas.py` |
| Database engine | `src/plannededucation/api/database.py` |
| Field encryption | `src/plannededucation/api/db_encryption.py` |
| Schema migrations | `src/plannededucation/api/schema_ensure.py` |
| Auth (JWT, 2FA, refresh) | `src/plannededucation/api/auth.py` |
| Auth routes | `src/plannededucation/api/routes_auth.py` |
| Authorization policies | `src/plannededucation/api/authorization.py` |
| Rate limiting | `src/plannededucation/api/limiter.py` |
| SEB security | `src/plannededucation/api/seb_security.py` |
| PII scrubbing | `src/plannededucation/api/routes_anonymizer.py` |
| AI grading | `src/plannededucation/api/routes_ai.py` |
| OCR service | `src/plannededucation/api/ocr_service.py` |
| STT service | `src/plannededucation/api/stt_service.py` |
| Backup service | `src/plannededucation/api/backup_service.py` |
| Deployment config | `src/plannededucation/api/deployment_config.py` |
| Frontend entry | `web/apps/portal/src/main.tsx` |
| Routes | `web/apps/portal/src/App.tsx` |
| API client | `web/apps/portal/src/api.ts` |
| Auth context | `web/apps/portal/src/contexts/AuthContext.tsx` |
| i18n context | `web/apps/portal/src/contexts/I18nContext.tsx` |
| English translations | `web/apps/portal/src/locales/en/messages.json` |
| Version | `VERSION` |
| Env template | `.env.example` |
| CI pipeline | `.github/workflows/ci.yml` |
| Security scans | `.github/workflows/security-checks.yml` |
| Test cache helper | `scripts/testing/update_test_cache.py` |
| Module test runner | `scripts/testing/module_test_runner.py` |
| Installer (Windows) | `install.ps1` |
| Installer (Linux) | `install.sh` |

---

*End of Architecture Markdown (AMD). This file is the canonical structural specification for PlannedEducation and must be kept updated with every code change.*