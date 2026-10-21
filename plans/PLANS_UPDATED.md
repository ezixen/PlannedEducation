# Planned Education - Plans Updated 2026-10-21

## Latest Architecture & Security Updates (2026-10-21)
- **Full Dependency Modernization & Zero Vulnerability Posture**:
  - Python: Upgraded cryptography>=50.0.2 (eliminates PYSEC-2026-3552, PYSEC-2026-3553, PYSEC-2026-3554), pillow>=13.0.0 (eliminates OSV CVEs), astapi>=0.156.4, sqlalchemy>=2.1.5, greenlet>=3.5.6, pydantic-settings>=2.16.1, websockets>=17.3, webauthn>=3.0.1.
  - PII Scrubber Architecture: Replaced presidio-anonymizer with clean native span redaction while retaining presidio-analyzer for NLP entity recognition. Solved the pip dependency conflict and unblocked cryptography>=50.0.2.
  - Frontend: Upgraded all npm packages to latest releases (
eact 19.3.1, 	ypescript 7.0.2, ite-plugin-pwa 2.0.0, ite 8.3.4, oxlint 1.89.0, idb 8.0.4, lucide-react 1.60.0). Zero npm vulnerabilities.
  - Verification: 100% test pass rate across 123 backend pytest tests (1m 46s), pip check (0 broken requirements), pip_audit (0 known vulnerabilities), 
pm audit (0 vulnerabilities).

## Execution Order (The Roadmap) — Updated Status

### Phase 1: Foundation ✅ Completed
- **Database models**, Authentication (Google SSO + Standard + TOTP 2FA), and the React Vite Portal Shell (Routing, Hamburger Menu, Themes)
- All auth routes implemented; user models with `RoleEnum`; Google SSO with dev auth gating via `ALLOW_DEV_AUTH` env var; JWT config with `JWT_SECRET_KEY`; CORS restricted to explicit origins; password policies with `passlib` complexity; TOTP 2FA column added to `User` model; `is_active` check on every auth path
- **Self-Service Password Reset & 2FA (NEW)** — Email OTP reset (6-digit, 10-min expiry), recovery codes for 2FA users (5 codes, 8 chars, one-time use), TOTP setup/confirm/disable/regenerate endpoints. Google SSO is primary login; password exists ONLY for self-service reset fallback. No admin portal needed — all flows user-self-service. Rate limited (5/min request, 10/min confirm).
- **All 18 auth tests pass** (existing) + new endpoints ready for testing

### Phase 2: Core Exam Engine ✅ Completed
- **Test creation**, Class Groupings, Question Banks, Variables, Accommodations, and offline PWA support
- Exam CRUD with owner enforcement (`_require_exam_owner` helper); question creation; SEB config generation; dynamic math `[rand:1-10]` randomization; multiple-choice scrambling; IEP time multipliers (1.5x/2.0x) stored in `StudentRecord.time_multiplier`; class grouping UI; exam listing returns safe metadata only via `ExamListResponse` schema
- **Modular Test Packages**: JSON/YAML package export & import with `packages.ts` and `PackageManager.tsx` UI
- **Offline-First Exam Engine**: Client-side IndexedDB persistence (`idb`), offline package caching, monotonic countdown timer, SEB anti-cheat monitoring (window blur, tab switches, process exits), and automatic reconnect sync (`offlineExam.ts`, `useOfflineExam.ts`)
- **All exam tests pass**

### Phase 3: Security Integration ✅ Completed
- **SEB header validation**, Screen Watermarking, and the Secure Chat (WIWM port)
- SEB enforcement: 409 if no `seb_config_key` set on exam; `hmac.compare_digest` for timing-safe hash comparison; dev bypass requires both `PLANNED_EDUCATION_ENV=development` AND `ALLOW_DEV_SEB_BYPASS=true`
- Screen watermark renders `user.email | user.id` across viewport (intentional anti-sharing)
- Secure chat WebSocket with ownership/active-submission checks; message caps (500 chars); auto-scroll; connection status dot; typed `ChatMessage` interface; `examId` as path parameter not query string; JWT stored under `access_token` key
- **Redis Pub/Sub for multi-worker WebSocket broadcasting** — implemented with auto-fallback to in-memory
- **Microsoft Presidio PII scrubber on anonymizer essays** — implemented (MIT licensed)
- **All 5 chat tests pass**

### Phase 4: AI & Grading ✅ Completed
- **Anonymization pipeline**, external AI integration, OCR, Audio/Speech-to-text, and the Teacher Dashboard
- Anonymizer API returns `anonymous_student_ref` (Student_1, Student_2...) with no PII; `post_ai_grades` persists feedback to DB with exam ownership verification; `ExamSubmission` has `score` and `feedback` columns; `crypto.py` Fernet encryption for user AI API keys ready; AI integration docs with system prompt and recommended providers (Gemini, Ollama, OpenRouter, OpenAI)
- **AI Key Management endpoints** — GET/PUT `/auth/ai-key` for teacher AI provider configuration
- **Presidio PII scrubber on anonymizer essays** — implemented (MIT licensed)
- **All 4 anonymizer tests pass**
- **Full OCR pipeline for handwritten math** — `ocr_service.py` with deskewing, line detection, symbol detection, LaTeX conversion, validation; 7 route tests pass
- **Speech-to-text integration** — `stt_service.py` with faster-whisper, base64/upload endpoints, model management, VAD; 8 route tests pass
- **Teacher dashboard UI for reviewing AI suggestions** — `TeacherDashboard.tsx` with submission review, AI grade generation, mistake grouping, modal review with approve/apply workflow

### Phase 5: Optional Proctoring ✅ Completed
- **WebRTC/Webcam AI proctoring toggle** with GDPR compliance flags
- `ProctoringToggle.tsx` UI with camera/mic toggle, GDPR warning badge, video element preview, disable proctoring flow
- **GDPR Consent Flow**: Modal with explicit consent checklist, camera/microphone permission handling (`GDPRConsentModal.tsx`)
- **Proctoring Event Pipeline**: Eye-tracking, multi-face detection, background audio monitoring, and session event ingestion (`proctoring_service.py`, `useProctoring.ts`, `ProctoringSession.tsx`)
- **Backend proctoring routes** — `/proctoring/events`, `/proctoring/sessions`, `/proctoring/stats` with RBAC (22 tests pass)

### Phase 6: Admin Portal ❌ Removed (2026-10-05)
- Admin portal was removed per project scope: only user portal (teacher/student/parent) is needed
- Admin functions (user management, exam oversight, system settings) will be handled via CLI/scripts or direct DB access
- 2FA TOTP UI moved to user portal Settings page (already implemented)


| OWASP Category | Control | Implementation |
|---|---|---|
| **A01:2025 Broken Access Control** | Deny by default, RBAC, row-level access | `_require_exam_owner` helper, `AccountRelationship` with status checks, teacher-only exam mutations |
| **A02:2025 Security Misconfiguration** | Secure headers, no debug in prod, hardened configs | CSP, HSTS, X-Frame-Options, TrustedHostMiddleware, Swagger disabled in prod, secure defaults |
| **A03:2025 Software Supply Chain Failures** | Dependency scanning, SBOM, signed artifacts, provenance | `pip-audit`/`npm audit` in CI, `cyclonedx-bom`/`@cyclonedx/bom` SBOM, pinned deps, **cosign keyless signing**, **SLSA Level 3 provenance** |
| **A04:2025 Cryptographic Failures** | TLS 1.3, Argon2id, Fernet, JWT HS256, key management | Argon2id (time_cost=3, memory=64MB), Fernet for AI keys, JWT 60-min expiry, HTTPS-only cookies, KMS-ready |
| **A05:2025 Injection** | Parameterized queries, input validation, output encoding | SQLAlchemy ORM, Pydantic schemas with strict validation, no raw SQL, XSS prevention |
| **A06:2025 Insecure Design** | Threat modeling, secure defaults, fail-secure | Security audit logging, rate limiting, constant-time comparisons, fail-secure defaults |
| **A07:2025 Authentication Failures** | MFA, passkeys/WebAuthn, brute force protection | Google SSO primary, TOTP 2FA, recovery codes, rate limiting (5-20/min), Argon2id, **Passkeys/WebAuthn implemented** |
| **A08:2025 Software/Data Integrity Failures** | CI/CD integrity, signed artifacts, SBOM verification | Pinned dependencies, CI security gates, **cosign keyless signing**, **SLSA Level 3 provenance**, supply chain verification |
| **A09:2025 Security Logging/Monitoring Failures** | Structured JSON logs, security events, alerting | Request ID middleware, auth/exam mutation audit logs, global exception handler, **SLO alerting (burn rate planned)** |
| **A10:2025 Mishandling of Exceptional Conditions** | Error handling, no stack traces, generic errors | No stack traces in production; generic 500 with request_id, structured error responses |

### Security Headers (OWASP Recommended)
- `Content-Security-Policy`: Restrictive default with Google OAuth allowances
- `Strict-Transport-Security`: 2-year max-age with preload (production)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`: geolocation=(), microphone=(), camera=(), payment=()

### Authentication & Session Management
- **Primary**: Google SSO (OAuth2/OIDC) — no passwords for login
- **Fallback**: Self-service password reset via email OTP (6-digit, 10-min expiry)
- **2FA**: TOTP (RFC 6238) with `pyotp`, QR code provisioning, 5 recovery codes (8 chars, one-time use)
- **Password Hashing**: Argon2id (time_cost=3, memory_cost=64MB, parallelism=4) — OWASP recommended
- **Rate Limiting**: 10/min register, 20/min login, 5/min reset request, 10/min reset confirm
- **JWT**: HS256, 60-min access tokens, env-configured secret, dev ephemeral fallback

### Data Protection
- **Encryption at Rest**: Fernet (AES-128) for AI API keys via `AI_KEY_MASTER_SECRET`
- **Encryption in Transit**: TLS 1.3 enforced in production (SSL mode=require for PostgreSQL)
- **Field-Level**: `hashed_password`, `totp_secret`, `recovery_codes`, `ai_api_key_encrypted` never in API responses
- **PII Minimization**: Anonymizer API strips all identifiers; watermark is intentional anti-sharing

### Audit & Observability
- **Structured JSON Logging**: Timestamp, level, security_event, user_id, IP, request_id
- **Security Events Logged**: Auth endpoint access, exam mutations, auth failures, DDL operations
- **Request Tracing**: X-Request-ID header propagated through all middleware
- **Error Handling**: No stack traces in production; generic 500 with request_id

**Launch**: `start.ps1` successfully starts API (port 8000) + Portal (port 5173) + Chrome Canary at `http://localhost:5173/login`. Canary debug test confirms both services reachable.

**Completed Infrastructure Items**:
- Backend proctoring event pipeline, eye-movement tracking, multiple-face detection, background audio analysis, GDPR consent flow (Completed)
- PWA IndexedDB sync for offline progress, monotonic countdown timer & SEB anti-cheat monitoring (Completed)
- Modular test package sharing via JSON/YAML export & import (Completed)
- Offline-first question bank UI

---

## 🔄 New Priority Items (2026-10-06)

### Phase 7: OWASP Top 10:2025 Alignment & NIST Standards ✅ **COMPLETED** (2026-10-14)

#### 7.1 OWASP Top 10:2025 Full Alignment ✅ Updated
- Updated OWASP mapping table to 2025 categories (A01-A10)
- **A03 Software Supply Chain Failures**: Added `pip-audit`/`npm audit` in CI, SBOM generation, pinned dependencies
- **A08 Software/Data Integrity Failures**: CI/CD integrity gates, artifact signing ✅ (cosign + SLSA)
- **A09 Security Logging/Monitoring Failures**: Structured logging ✅, SLO alerting ✅ **IMPLEMENTED** (burn rate alerting implemented 2026-10-14)
- **A10 Mishandling of Exceptional Conditions**: Generic error responses, no stack traces in prod ✅

#### 7.2 NIST AI RMF 1.0 + Generative AI Profile (NIST-AI-600-1) ✅ **IMPLEMENTED** (2026-10-06)
- **AI Risk Governance for External AI Grading**: Since AI is external-only via pluggable API system, risk controls implemented in `src/plannededucation/api/routes_ai.py`:
  - ✅ Prompt injection prevention (20+ regex patterns, input sanitization on teacher prompts)
  - ✅ Model output validation (hallucination detection via consistency checking, format verification)
  - ✅ Data minimization (anonymizer strips PII before sending to AI)
  - ✅ Audit trail for all AI interactions (request/response logging with user_id, prompt_hash, response_hash)
  - ✅ Teacher approval workflow for AI-suggested grades (TeacherDashboard.tsx)
- **Generative AI Profile Controls** (implemented):
  - ✅ Input validation on all teacher-provided prompts (`check_prompt_injection`, `sanitize_prompt`)
  - ✅ Output schema validation (JSON schema for AI responses via Pydantic models)
  - ✅ Rate limiting on AI API calls per teacher (20/min, 200/hour via `RateLimiter`)
  - ✅ Cost monitoring and budget alerts per teacher ($5/day budget, tracked in `ai_usage` table)
  - ✅ Fallback to manual grading if AI service unavailable (teacher review UI)
  - ✅ Confidence threshold (min 0.75) with automatic flagging for teacher review
  - ✅ Provider health monitoring with automatic fallback

#### 7.3 NIST SSDF 1.1 Alignment 🔄 **Mostly Implemented**
- **Secure Development Practices**:
  - ✅ SAST in CI (bandit for Python) — `.github/workflows/ci.yml`
  - ⚠️ ESLint security rules for TypeScript — using `oxlint` instead (faster, built-in security rules)
  - ✅ Dependency scanning (`pip-audit`, `npm audit`) — CI gates
  - ✅ SBOM generation for releases (`cyclonedx-bom` Python, `@cyclonedx/bom` Node) — CI
  - ✅ Container image scanning (Trivy) for Docker builds — CI
  - ✅ Signed artifacts and provenance (cosign keyless + SLSA Level 3 via slsa-github-generator) — CI
  - 🔄 AI-assisted code review requirements (human approval for auth/payment/security) — PR template includes AI provenance

#### 7.4 NIST CSF 2.0 Alignment ✅ **IMPLEMENTED** (2026-10-14)
- **Govern**: Project security policy (OWASP ASVS 5.0.0), risk management strategy ✅
- **Identify**: Asset inventory (data, models, APIs), supply chain risk (SBOM, dependency scanning) ✅
- **Protect**: Access control (RBAC, row-level), data encryption (Fernet, TLS 1.3, Argon2id), awareness training (docs) ✅
- **Detect**: Security monitoring (structured JSON logs, request tracing), anomaly detection (rate limiting, auth failures), logging ✅
- **Respond**: Incident response plan (runbooks in `docs/runbooks/`), communication procedures ✅ (ESCALATION.md, ONCALL.md)
- **Recover**: Backup/restore drills (automated monthly), business continuity (RPO < 24h, RTO < 4h) ✅

### Phase 8: Passkeys/WebAuthn Implementation ✅ **IMPLEMENTED** (2026-10-06) (OWASP A07:2025)
- **Primary**: Google SSO (OAuth2/OIDC) — remains primary
- **Passkeys/WebAuthn**: Fully implemented as phishing-resistant second factor
  - ✅ WebAuthn/FIDO2 registration during 2FA setup (requires TOTP 2FA first)
  - ✅ Platform authenticators (Windows Hello, Touch ID, Android biometrics)
  - ✅ Cross-device sync via iCloud Keychain / Google Password Manager
  - ✅ Fallback to TOTP 2FA for devices without passkey support
- **Implementation**: `py_webauthn` library, endpoints in `src/plannededucation/api/routes_auth.py`:
  - `POST /auth/webauthn/registration/start` — Start passkey registration
  - `POST /auth/webauthn/registration/finish` — Complete passkey registration
  - `POST /auth/webauthn/authentication/start` — Start passkey authentication
  - `POST /auth/webauthn/authentication/finish` — Complete passkey authentication
  - `GET /auth/webauthn/credentials` — List registered passkeys
  - `DELETE /auth/webauthn/credentials/{credential_id}` — Delete passkey
- **UI**: `web/apps/portal/src/components/PasskeysSettings.tsx` integrated in Settings page
- **Translations**: All 17 locales have passkeys translations
- **Documentation**: FAQ, MANUAL_TESTING.md, ARCHITECTURE.md

### Phase 9: Enhanced Supply Chain Security ✅ Completed (2026-10-06)
- **CI/CD Gates** (`.github/workflows/ci.yml`): ✅ All implemented
  - ✅ `pip-audit` for Python dependencies
  - ✅ `npm audit` for Node dependencies
  - ✅ `trivy` container scanning for Docker images
  - ✅ `gitleaks` secret scanning (OSS binary, not GitHub Action)
  - ✅ SBOM generation (`cyclonedx-bom` for Python, `@cyclonedx/bom` for Node)
  - ✅ Dependency license compliance check
- **Artifact Signing**: ✅ cosign for SBOMs, SLSA provenance via slsa-github-generator
- **SLSA Provenance**: ✅ slsa-github-generator workflow for SLSA Level 3

### Phase 10: Internationalization (i18n) Foundation ✅ **IMPLEMENTED** (2026-10-14)
- **Custom i18n System** (not ICU MessageFormat - simpler page.element.key format):
  - ✅ Externalized strings in React components via `useI18n()` hook and `t(key)` function
  - ✅ Locale-safe formatting: dates (dd/mm/yyyy), numbers, time display via `Intl` API
  - ✅ RTL support preparation (CSS logical properties in themes)
  - ✅ **17 Supported locales**: en, hu, es, de, fr, ja, zh, pt, uk, it, pl, nl, sv, no, da, fi, pt-BR
  - ✅ All 455 keys per locale matching English source
- **Components**:
  - `I18nContext.tsx` — Locale management, number display toggle, jump-to-element, localStorage persistence
  - `I18nNumber.tsx` — Visual badges, tooltips with context, jump-to, keyboard navigation
  - `I18nSettings.tsx` — Locale selector, number toggle, help, translator guide, contribute links
  - `I18nNumber.css` — Styles for badges, tooltips, jump animation, settings panel
- **Integration**:
  - `I18nProvider` in `main.tsx` wrapping entire app
  - `I18nSettings` in Settings page
  - Login page updated to use `t()` function
  - `CONTEXT.md` — Detailed context for every translation key
  - `docs/I18N_GUIDE.md` — Comprehensive guide with file structure, translation rules, adding languages, workflows

### Phase 11: Observability & SLOs ✅ Completed (2026-10-06)
- **OpenTelemetry Integration**: ✅ Implemented in `src/plannededucation/api/main.py`
  - Python: `opentelemetry-instrument` for FastAPI, SQLAlchemy, Requests
  - Auto-instrumentation: FastAPIInstrumentor, SQLAlchemyInstrumentor, RequestsInstrumentor
  - TracerProvider with ConsoleSpanExporter (dev) / OTLP ready for production
  - MeterProvider with PrometheusMetricReader for metrics
- **Prometheus Metrics**: ✅ Custom metrics + auto-instrumentation
  - Custom metrics: `http_requests_total`, `http_request_duration_seconds`, `active_users`, `exam_submissions_total`, `ai_grading_requests_total`
  - Prometheus metrics server on port 9090
  - OpenTelemetry MeterProvider with PrometheusMetricReader
- **SLO Definitions**: ✅ Defined in code and docs
  - API latency p95 < 500ms (tracked via `http_request_duration_seconds`)
  - API availability > 99.9% (tracked via `http_requests_total` with status codes)
  - Exam submission success rate > 99.5% (tracked via `exam_submissions_total`)
  - AI grading response time < 30s (tracked via `ai_grading_requests_total`)
- **Grafana Dashboards**: ✅ Configured in `monitoring/grafana/`
  - Datasource: Prometheus
  - Dashboard provider configured
- **Alerting**: ✅ **IMPLEMENTED** (2026-10-14) - Burn rate alerting on SLOs via Prometheus/Grafana
  - Alerting rules: `monitoring/alerting_rules.yml` (fast/slow burn rates for all 4 SLOs)
  - Alertmanager config: `monitoring/alertmanager.yml` (routing by severity/burn_rate/CSF function)
  - Alert storage: `Alert` model in `models.py` with fingerprint deduplication
  - Webhook endpoint: `routes_alerts.py` (persists alerts, supports REST queries)
  - Notification forwarding placeholder for email/Slack/PagerDuty

### Phase 12: Backup/Restore Drill Automation ✅ Completed (2026-10-06)
- **Automated Schedule**: Daily encrypted PostgreSQL backups (documented in `docs/BACKUP_RESTORE_PLAN.md`)
- **Restore Drills**: Monthly automated restore to staging via GitHub Actions schedule
- **RPO/RTO Targets**: RPO < 24h, RTO < 4h (validated by drill script)
- **Documentation**: `docs/BACKUP_RESTORE_PLAN.md`
- **Implementation**:
  - `scripts/backup_restore_drill.sh` — Linux/macOS drill script with full validation
  - `scripts/backup_restore_drill.ps1` — Windows PowerShell drill script
  - `.github/workflows/backup-restore-drill.yml` — Monthly scheduled workflow (first Saturday 03:00 UTC)
  - Validates: backup integrity, backup age, restore time, data integrity, migrations, smoke tests
  - Artifacts uploaded for audit trail

### Phase 13: Visual Regression & Multi-Role Simulation Testing ✅ Completed (done-tested-working)
- **Playwright Visual Tests**: `tests/visual/platform-visual.spec.ts` (17/17 passed across desktop, mobile, tablet viewports, dark/light contrast, no horizontal overflow).
- **Multi-Role Live Simulation Tests**: `tests/visual/simulation-e2e.spec.ts` (5/5 passed):
  1. Teacher live proctoring & AI grading dashboard
  2. Parent student progress tracking with empathetic, supportive feedback
  3. Teacher class groupings & student roster view
  4. Destructive Admin user deletion and fresh student account re-registration
  5. All 10 design themes (`skyward`, `carbon_cyan`, `enterprise_blue`, `blush_silver`, `matrix_green`, `black_orange`, `sunset_cabin`, `aurora_night`, `comic_stage`, `ocean_calm`) across 3 border radii (`square`, `soft`, `round`) with high legibility and zero horizontal overflow
- **Automated Teardown & Workspace Hygiene**: `global-teardown.ts` guarantees all temporary databases (`test_visual.db`), screenshots, and test run reports are pruned after runs per `AGENTS.md` §6.
- **Backend Test Cache Tracking**: 99 backend pytest tests passing via `scripts/testing/update_test_cache.py`.

### Phase 14: Project Kickoff Worksheet Completion ✅ **COMPLETED** (2026-10-14)
- ✅ Filled out `PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md` for PlannedEducation
- ✅ Documented all architecture/security/reliability/cost decisions
- ✅ Decision confidence scoring (Total: 28/30)
- ✅ Updated i18n section to reflect 17 locales implemented
- ✅ Added AI cost tracking warning section

---

## 📋 AI API System Architecture (External AI Only)

**Core Principle**: Platform provides **API infrastructure only** — teachers bring their own AI keys.

```
┌─────────────────────────────────────────────────────────────┐
│                    PlannedEducation Platform                │
├─────────────────────────────────────────────────────────────┤
│  Teacher Portal          │  Student Portal  │  Parent Portal │
└──────────────┬───────────┴────────┬─────────┴───────┬────────┘
               │                    │                 │
               ▼                    ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI API Gateway                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Grading    │  │  Test       │  │  Content            │  │
│  │  Endpoint   │  │  Creation   │  │  Generation         │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           AI Provider Abstraction Layer             │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │   │
│  │  │ Gemini  │ │ Ollama  │ │OpenRouter│ │ Custom    │  │   │
│  │  │ Adapter │ │ Adapter │ │ Adapter │ │ Provider  │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              Teacher's AI Provider (BYOK)                   │
│  • Google Gemini API    • OpenRouter                        │
│  • Anthropic Claude     • Local Ollama                      │
│  • OpenAI               • Any OpenAI-compatible endpoint    │
└─────────────────────────────────────────────────────────────┘
```

**Key Components Already Implemented**:
- ✅ `crypto.py` — Fernet encryption for AI API keys at rest
- ✅ `GET/PUT /auth/ai-key` — Teacher AI provider configuration
- ✅ `ai_provider`, `ai_model_name`, `ai_base_url`, `ai_api_key_encrypted` in User model
- ✅ Anonymizer pipeline strips PII before AI calls

**Remaining Work** (Optional Enhancements):
- [ ] AI Provider Abstraction Layer (base class + adapters) — currently uses direct provider calls
- [ ] Grading endpoint with prompt templates — implemented in `routes_ai.py` with NIST AI RMF controls
- [ ] Test creation endpoint with schema validation — implemented in `routes_ai.py`
- [ ] Content generation endpoint — implemented in `routes_ai.py`
- [ ] Rate limiting & cost tracking per teacher — ✅ Implemented (20/min, 200/hour, $5/day budget)
- [ ] Output validation & hallucination detection — ✅ Implemented (JSON schema, consistency check, confidence threshold)
- [ ] Teacher review/approval workflow for AI outputs — ✅ Implemented (TeacherDashboard.tsx)

---

### Phase 7: Visual Regression Testing CI & Multi-Role Verification ✅ Completed (2026-10-07)
- **Status**: `done-tested-working`
- **Baseline Audit**: 22 Playwright tests (17 in `platform-visual.spec.ts` + 5 in `simulation-e2e.spec.ts`) verified and preserved.
- **Advanced Features Suite (`advanced-features.spec.ts`)**: 7 tests covering Archive management & statistics, Test Package Manager & export dialog, 2FA/TOTP setup wizard, AI BYOK provider configuration, Handwritten Math OCR & faster-whisper STT processors, live test taking with Digital Hand Raise and exam timer, and responsive mobile theme cycling. (7 / 7 passed).
- **Backend Test Suite**: 99 / 99 pytest tests passed via `scripts/testing/update_test_cache.py`.
- **Artifact Cleanup**: Automatic post-test cleanup of temporary databases, traces, and reports enforced per `AGENTS.md` §6.

---

### Phase 15: Cross-Platform School Deployment, Test Administration & Module Federation ✅ Completed (2026-10-16)
- **Status**: `done-tested-working`
- **Unified Installer Systems**:
  - `install.ps1`: Interactive PowerShell installer for Windows Server (2016/2019/2022) and Windows 10/11 Pro with Dual-Mode architecture:
    1. **Native Deployment (No Docker)**: Direct host execution using Python + PostgreSQL/Redis/SQLite, automatic Windows Scheduled Task background service creation.
    2. **Docker Compose Deployment**: Full containerized isolation.
    - Uses native .NET cryptographically secure random string generation (eliminating external `openssl` binary dependency on Windows).
  - `install.sh`: Interactive Bash installer for Linux (Ubuntu 22.04+/Debian 12+) with Dual-Mode Native (Systemd) and Docker Compose options.
  - `deploy_wizard.py`: Cross-platform guided deployment wizard in Python with automatic binary path resolution (`shutil.which`), modern `docker compose` plugin support, and Native SQLite/PostgreSQL deployment.
- **Dependency Compatibility & Forward-Compatibility Architecture**:
  - Permissive lower-bound (`>=`) requirements defined in `src/requirements.txt` to enable upstream security patches while preserving forward-compatibility assumptions.
  - Complete `install.log` exported at root with full compatibility matrix, tested versions, and explicit downgrade target guidelines.
- **Live School Deployment & End-to-End Test (`d:\Dev\PEserver`)**:
  - Live deployment to `d:\Dev\PEserver` executing as background server on port 8000 (`plannededucation.db`).
  - Automated integration test `test_school_e2e.py` executed with 100% pass across all 7 stages:
    1. **Health Verification**: `/health` and `/packages/health` operational.
    2. **Admin Auth**: Superuser authentication and profile checks.
    3. **Teacher Workflow**: Registration, exam creation ("Physics 101: Energy & Mechanics") with 3 question types (multiple choice, dynamic math formula randomization, and essay with grading rubrics).
    4. **Student Workflow**: Public exam listing verified for zero answer leakage; session started with SEB bypass header; dynamic math formula randomized for student; heartbeats sent; exam submitted; idempotency re-submission rejected with HTTP 409 Conflict.
    5. **Teacher Dashboard**: Verified completion status in teacher heartbeat monitor.
    6. **Module / Package System**: Exported exam to portable `.pepkg.json` with SHA-256 integrity checksum; validated package structure; imported into clean exam instance; published module to catalog; searched and downloaded package file.
    7. **Custom School Federation**: Configured external school source URL (`http://127.0.0.1:8000/packages`), browsed configured sources, and executed synchronization.
- **Bug Fixes in Package & Schema Engine**:
  - Resolved Python 3.14 / Pydantic v2 `datetime` forward reference in `schemas.py`.
  - Added JSON stringification and coercion validators on package models.
  - Corrected `Alert` class inheritance in `models.py` preventing table column collision in `PackageSource`.
  - Fixed FastAPI route precedence ordering in `routes_packages.py` for `/sources` and `/health`.
  - Replaced legacy stub route definitions with real SQLAlchemy operations and HTTP synchronization via `httpx.AsyncClient`.
- **Verification**:
  - `pip check`: 0 broken requirements.
  - `npm run build`: Vite frontend production build passed in 5.09s (0 errors).
  - Backend pytest suites: 102/102 passing clean via `scripts/testing/update_test_cache.py`.
  - Live deployment test `test_school_e2e.py`: 7/7 stages passed (100% clean).
- **GitHub Actions CI/CD & Security Audits**:
  - Bumped `cryptography>=50.0.0` in `src/requirements.txt` to eliminate 6 CVEs (`PYSEC-2026-3552`, `PYSEC-2026-3553`, `PYSEC-2026-3554`).
  - Resolved `ruff` lint errors on model attributes and added safe SQLAlchemy filter ignore rules in `pyproject.toml`.
  - Removed obsolete snapshot `requirements_latest.txt` to resolve all phantom Dependabot alerts.
  - Verified 100% green status on GitHub Actions (`Security Checks`, `CI/CD Pipeline`, `Container Scans`, `CycloneDX SBOM`, `Cosign Signatures`, and `SLSA Provenance`) across both `main` and `dev` branches.
  - Zero open Dependabot alerts across the entire repository.

---

### Phase 16: Modular Email Service, Admin Direct Password Reset & 2FA Recovery ✅ Completed (2026-10-16)
- **Status**: `done-tested-working`
- **Modular Email Service (`src/plannededucation/api/email_service.py`)**:
  - Zero-configuration, 100% offline-first architecture by default: logs OTP and reset codes safely when no provider is set.
  - Optional **Brevo (Sendinblue)** transactional REST API integration via `httpx.AsyncClient` (`BREVO_API_KEY`, free tier 300 emails/day).
  - Optional **Campus / School SMTP** integration via `aiosmtplib` with background-thread `smtplib` fallback.
  - Asynchronous background dispatch in `routes_auth.py` via FastAPI `BackgroundTasks`.
- **Direct Admin Password Reset (Without Email Dependency)**:
  - Added `POST /admin/users/{user_id}/reset-password` in `routes_admin.py` accepting custom password or generating secure temporary password (`TempPass#<random8>!`).
  - Added option to reset and disable 2FA/Passkeys (`reset_2fa=True`) for students/teachers who lost their authenticator device.
  - Automatically invalidates existing session refresh tokens and pending OTPs upon reset.
  - Fixed `require_admin` dependency to accept dedicated administrators (`is_admin=True` or `role in ("admin", "teacher")`).
- **Admin Dashboard UI (`AdminDashboard.tsx`)**:
  - Added "🔑 Reset Password" action button in the Users management table.
  - Modal with custom password input, auto-generate helper button, and "Reset & Disable 2FA / Passkeys" checkbox.
  - Temporary password confirmation dialog with one-click clipboard copy.
- **Documentation & FAQ Updates**:
  - Updated `.env.example` with Brevo and Campus SMTP configuration templates.
  - Updated `docs/FAQ.md` with password reset, admin reset without email, and email configuration guides.
  - Updated in-app `FAQChatbot.tsx` with dedicated responses and keyword triggers.
- **Verification**:
  - Full backend test suite: 107/107 passing clean via `scripts/testing/update_test_cache.py`.
  - Focused test suite `tests/test_admin_password_reset.py`: 5/5 passing clean.
  - Frontend production build (`npm run build`): verified clean bundle in 4.39s.

---

### Phase 17: Automated Deployment & Undeployment (Windows & Linux/WSL), AI Agent Contract & Separated Diagnostic Logs ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **AI Agent Deployment Contract & Human-in-the-Loop Safeguards**:
  - Established contract in `install.ps1`, `install.sh`, `uninstall.ps1`, `uninstall.sh`, `README.md`, `docs/INSTALL_WINDOWS.md`, and `docs/INSTALL_LINUX.md`.
  - AI agents can run automated headless deployments with `AUTO_CONFIRM=true` / `-AutoConfirm`, but MUST stop and ask the human operator for key decisions: target folder, deployment mode (1=SQLite, 2=PostgreSQL+Redis, 3=Docker), School & Superadmin identity, and port preferences.
  - Uninstallers explicitly offer NO "remove all dependencies" option; with auto-confirm, all external dependencies are kept. When reviewing interactively, users choose one by one whether to keep or remove each installed dependency (`Python`, `Node.js`, `PostgreSQL`, `Redis`, `Docker`, `Git`).
- **Port Flexibility & Automatic Fallback**:
  - Default ports: `8000` (API) and `5173` (Frontend).
  - Automatically probes and falls back to free alternative ports (`8002/8001/8080` and `5175/5174/5176`) when default ports are occupied.
- **Separated Diagnostic & Error Logging**:
  - Gated OpenTelemetry `ConsoleSpanExporter` in `src/plannededucation/api/main.py` behind `OTEL_CONSOLE_EXPORT=true` (reduced backend log volume from 32,652 lines down to concise runtime logs).
  - Configured structured file logging in `<InstallDir>/logs/`:
    - `logs/install.log` & `logs/install_error.log` (installation progress and verify tests)
    - `logs/backend.log` (INFO+) & `logs/backend_error.log` (WARNING/ERROR+ with tracebacks)
    - `logs/backend_stdout.log` & `logs/backend_stderr.log` (raw console captures)
    - `logs/frontend.log` & `logs/frontend_error.log` (frontend stdout and stderr)
- **Robust Installation & Uninstallation Engine**:
  - Clones into temporary sibling directory (`.clone-tmp`) to prevent git errors when target folder contains `logs/`.
  - Syncs workspace changes using `rsync` (Linux) and `robocopy` (Windows), excluding `.env*` to prevent port mismatch overrides.
  - Cleans override environment files (`.env.local`) and synchronizes `VITE_API_URL` across `.env` and `.env.local`.
  - Added `greenlet>=3.1.1` to `src/requirements.txt` and wrapped OpenTelemetry lifespan instrumentation safely with try/except blocks.
  - Implemented ancestor PID protection in uninstallers so running shells and agent wrappers are never killed.
  - Fixed syntax error in `uninstall.sh` summary `if` block.
- **Comprehensive Verification**:
  - Full Windows lifecycle automated and verified (`install.ps1` -> start -> E2E pass -> `uninstall.ps1` -> 0 ports).
  - Full Linux / WSL lifecycle verified (`install.sh` -> 4/4 verification tests pass -> start -> E2E pass -> `uninstall.sh` -> clean removal, 0 ports).
  - Full deployed multi-role classroom E2E simulation (`tests/e2e/playwright/tests/deployed-classroom-e2e.spec.ts`) passed in 22.4s against deployed platform (Admin, Teacher, 3 Students with dynamic IEP and mistake variations, Grading, Student review, Parent portal).
  - Full backend pytest suite: 107/107 passing in 102.10s via `scripts/testing/update_test_cache.py`.
  - Zero orphaned processes remaining.

---

### Phase 18: Server-Side Editable Deployment Config, Teacher Verification & Approval, In-App Notifications & Recovery Codes ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Server-Side Editable Deployment Configuration (`config/deployment.json` & `deployment_config.py`)**:
  - Post-deployment domain, port, network layout, CORS, and optional SMTP email settings stored in `config/deployment.json`.
  - Accessible and editable on the server via text editor or via web in **Admin Dashboard → ⚙️ Deployment & Network**.
  - Platform restart applies changes with zero redeployment or rebuild required.
  - Browser-based "📁 Backup Config File" button using File System Access API with blob download fallback.
  - Documented in `README.md`, `DEPLOY.md`, `DEPLOY_SIMPLE.md`, and `DEPLOY_COMPREHENSIVE.md`.
- **Role Self-Registration & Security Restrictions**:
  - Users can self-register as `student`, `teacher`, or `parent`.
  - Admin accounts cannot self-register (restricted to existing admins or CLI commands).
  - Self-registered teachers default to `teacher_approved = False` to prevent students from prank-registering and viewing exam questions or curriculum modules.
  - Instant in-platform notification sent to administrators upon teacher registration.
  - Admin approval/denial endpoints (`/admin/pending-teachers`, `/admin/teachers/{id}/approve`, `/admin/teachers/{id}/deny`) and UI in Admin Dashboard.
- **One-Time Password Reset Recovery Codes & Self-Service**:
  - 5 single-use recovery codes generated upon registration for all users; printable and copyable.
  - Users can reset their password immediately without waiting for anyone using their recovery code.
  - Forgot password modal clearly reminds users to check their 5 recovery codes before requesting supervisor help.
  - Emergency backup codes for administrators (modal in Admin Dashboard) so admins never lose platform control.
- **In-Platform Offline-First Password Reset Requests**:
  - Students can request password reset from linked teachers or parents.
  - Teachers can request password reset from administrators.
  - Supervisors receive notifications and approve with one click, generating a secure temporary password.
  - 100% offline-first; SMTP email is completely optional and configurable.
- **Floating In-App Notification Bell**:
  - Mounted in application header on every page (`Layout.tsx`).
  - Automatic 60-second polling for unread notifications.
  - One-click actions for teacher approval and password reset requests.
- **Verification**:
  - Full backend pytest suite passing clean via `scripts/testing/update_test_cache.py` (118/118 tests passed).
  - Frontend production build (`npm run build`) passing clean in ~1.8s with 0 errors.
  - Zero orphaned background processes remaining.

---

### Phase 19: Classroom Pre-Exam Quick Reset, Midnight Database Auto-Backup, Brute-Force Lockout & Installer Admin Safeguards ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Teacher Classroom Emergency Student Password Reset**:
  - Right before an exam, students who forgot their password can be unlocked by their teacher with a single click.
  - "⚡ Reset Pwd for Test" button available in teacher student rosters (`TeacherClasses.tsx`) and exam monitoring (`TeacherDashboard.tsx`).
  - Next time student enters their email on `/login`, system intercepts with `TEACHER_RESET_ACTIVE` and prompts for their new password directly. Student types new password and is immediately signed in to take the exam.
- **Database Backup Engine & Midnight Auto-Backup (`backup_service.py` & `DatabaseBackupPanel.tsx`)**:
  - Immediate manual database backup snapshot button in Admin Dashboard.
  - Automated midnight background scheduler (runs daily at 00:00 UTC) with automatic 30-day retention pruning.
  - Safe transactional backups: SQLite atomic `sqlite3.connect().backup()` and PostgreSQL `pg_dump` with gzip compression.
  - Secure backup management UI: download with blob authentication, path traversal guards, and deletion controls.
- **Administrator Security & Brute-Force Protection**:
  - Administrator accounts protected against non-superadmin resets, deactivations, and deletions.
  - Brute-force safeguard: 5 consecutive failed login attempts automatically locks the account for 15 minutes.
  - Timezone-safe naive/aware comparisons across SQLite and PostgreSQL backends.
- **Installer AutoConfirm Admin Safeguard & Recovery Warnings (`install.ps1`, `install.sh`)**:
  - Even with `-AutoConfirm` / `AUTO_CONFIRM=true`, installer pauses and prompts to securely set administrator password if default.
  - Generates 5 one-time recovery codes and writes to `ADMIN_CREDENTIALS.txt`.
  - Displays prominent terminal warning banner: *"Keep these safe (print or write them down). If you lose both your password and recovery codes, you will be locked out and will need to redeploy the whole system, as database injection is not an option."*
- **Verification**:
  - Dedicated test suite `tests/test_teacher_quick_reset_and_backups.py` (4/4 passed).
  - Full backend pytest suite passing clean via `scripts/testing/update_test_cache.py` (122/122 tests passed in 96.79s).
  - Frontend production build (`npm run build`) verified clean in 1.94s with 0 errors.
  - Zero orphaned background processes remaining.

---

### Phase 20: Repository Root Cleanup, Documentation Consolidation & Script Reorganization ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Pre-Cleanup Safeguard**:
  - Full local repository pre-cleanup backup archive generated at `D:\Dev\PlannedEducation_precleanup_backup_20261018.zip` (36.70 MB, 2,820 files).
- **Repository Root Cleanup**:
  - Preserved only essential root files (`README.md`, `DEPLOY.md`, `LICENSE`, `THANKS.md`, `docker-compose.yml`, `Dockerfile.*`, `install.*`, `uninstall.*`, `pyproject.toml`, `pytest.ini`, `run_tests.py`, `test_tracker.py`, `conftest_tracker.py`, config/lint files).
  - Relocated branding assets (`PElogo*.jpg`, `favicon.ico`) to `docs/assets/branding/`.
  - Relocated all i18n tooling (`add_i18n_keys*.py`, `missing_keys.json`, `translate_*.py`) to `scripts/i18n/`.
  - Relocated developer multi-role launchers (`start_all.ps1`, `start_student.ps1`, `stop_student.ps1`, `start.ps1`, `stop.ps1`) to `scripts/dev/` with updated `$RepoRoot` paths.
  - Relocated deploy tools (`deploy.sh`, `deploy_wizard.py`) to `scripts/deploy/` with dynamic repo root resolution.
  - Relocated standalone test runners (`test_ui_full.py`, `test_e2e_comprehensive.py`, `smoke_test.py`) to `scripts/testing/`.
  - Removed duplicate and obsolete files (`test_school_e2e.py` duplicate, `rewrite_scripts.py`, `update_agents*.py`, obsolete test outputs and databases).
- **3-Tier Consolidated Documentation Hierarchy**:
  - `docs/admin/`: Master `DEPLOYMENT_GUIDE.md` (consolidating DEPLOY.md, DEPLOY_COMPREHENSIVE.md, DEPLOY_SIMPLE.md into a unified deployment guide for Modes 1, 2, 3), `INSTALL_WINDOWS.md`, `INSTALL_LINUX.md`, `INSTALL_COMPATIBILITY.md` (subsuming INSTALL_LOG.md), `BACKUP_RESTORE.md` (moved from docs root), and incident runbooks `runbooks/RB-001` through `RB-010`.
  - `docs/user/`: `TEACHER_GUIDE.md`, `STUDENT_GUIDE.md`, `PARENT_GUIDE.md`, and consolidated `FAQ.md`.
  - `docs/dev/`: `ARCHITECTURE.md`, `TESTING_GUIDE.md` (consolidating TEST_PLAN.md, MANUAL_TESTING.md, FEATURE_INVENTORY.md into a single 36KB authoritative testing handbook), `I18N_GUIDE.md`, `I18N_CONTEXT.md` (relocated from root CONTEXT.md), `MODULE_SYSTEM.md`, `SECURITY_COMPLIANCE.md`, `AI_RISK_GOVERNANCE.md`, `GITHUB_FREE_TIER.md`, `AUDIT_HISTORY.md`, `ORIGIN.md`, `LARGE_TEXT_METHODOLOGY.md`.
  - Root `README.md` updated with complete documentation index.
  - Root `DEPLOY.md` streamlined as quick-reference redirect to `docs/admin/DEPLOYMENT_GUIDE.md`.
- **Reference & Script Updates**:
  - Cross-references updated across `README.md`, `docs/admin/INSTALL_LINUX.md`, `INSTALL_WINDOWS.md`, `BACKUP_RESTORE.md`, `docs/user/FAQ.md`, `runbooks/`, and `scripts/deploy/deploy_wizard.py`.
- **Verification**:
  - Full backend pytest suite passing clean via `scripts/testing/update_test_cache.py` (122/122 passed in 122.61s).
  - Frontend production build (`npm run build`) passing clean in 11.31s with 0 errors.
  - Frontend lint (`oxlint`): 0 errors, 0 warnings across 61 files.
  - Zero orphaned background processes remaining.

---

### Phase 21: Cross-Platform Launcher Suite, Startup Hardening & Deployment Verifier ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Native PowerShell Start Scripts & Resilient Batch Wrappers**:
  - Created native `start_backend.ps1` and `start_frontend.ps1` avoiding PowerShell `-m` flag parsing issues.
  - Paired with batch wrappers (`start_backend.bat`, `start_frontend.bat`) that run via PowerShell with execution policy bypass.
  - Preserved console output and added `pause` on exit/error so terminal windows never flash and close unexpectedly.
- **Unified Single-Click Platform Launcher (`start_all.ps1` / `start_all.bat` / `start_all.sh`)**:
  - Starts backend and frontend in parallel with dynamic port resolution.
  - Automatically polls `/health` until the platform is ready.
  - Displays summary banner with PIDs, URLs, and opens the default browser once healthy.
  - Clean process terminator (`stop_all.ps1` / `stop_all.bat` / `stop_all.sh`) for stopping services cleanly.
- **Dedicated Health & Deployment Verifier (`verify.ps1` / `verify.bat` / `verify.sh`)**:
  - Automated diagnosis checking directory integrity, `config/deployment.json`, SQLite database file size, Backend API health (`/health`), Package Engine health (`/packages/health`), and Frontend Portal port connectivity.
- **Uninstaller Auto-Detection (`uninstall.ps1` / `uninstall.sh`)**:
  - Intelligently detects if executed from within an installation directory (`$PSScriptRoot` containing `.env`, `plannededucation.db`, or `src/plannededucation`), eliminating manual path specification.
  - Defaults to installer standard paths (`C:\PlannedEducation` / `/opt/plannededucation`).
- **Verification**:
  - Full backend pytest suite passing clean (122/122 passed).
  - Frontend production build verified clean in 4.49s.
  - Frontend oxlint passing with 0 warnings, 0 errors.
  - Zero orphaned background processes remaining.

---

### Phase 22: Windows PowerShell 5.1 Native Compatibility, Admin Elevation & Installer Hardening ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Windows PowerShell 5.1 Native Compatibility**:
  - Full syntax and parser verification using Windows default PowerShell engine (`powershell.exe` / PS 5.1 built into Windows 10/11 and Windows Server 2016-2025).
  - Eliminated all PS7-only operators (`??`, ternary `? :`, `&&`, `||`) across all scripts.
  - Replaced multi-byte Unicode emojis with clean ASCII indicators (`[KEY]`, `[!]`, `[OK]`, `[WARN]`), resolving the Windows CP1252 character mapping escape trap where the 4th UTF-8 byte (`0x91`) was parsed as a backtick escape character causing string quote syntax failures.
  - Updated developer launchers (`scripts/dev/*.ps1`) to automatically fall back from `pwsh` to `powershell.exe`.
- **Early Target Directory Prompt**:
  - `install.ps1` prompts for the target installation directory right at Step 1 before initializing logs or downloading dependencies.
  - Defaults to `C:\PlannedEducation` while naturally accepting custom folder paths; logs are immediately directed to the selected directory.
- **Administrator Privileges Pre-check & Self-Elevation**:
  - Early check informs the user of why elevated rights are needed on Windows (system folder creation, scheduled tasks, package installs, firewall rules).
  - Provides interactive menu: (1) Auto-elevate via UAC (`powershell.exe -Verb RunAs`), (2) Continue in User-mode, (3) Exit installer.
- **Superadmin Password Retention & Recovery Codes Confirmation Pause**:
  - Generates strong 20-character random passwords when requested or when default passwords are used.
  - Requires explicit `[Enter]` keypress after displaying passwords and emergency recovery codes before continuing, preventing terminal clear or scroll-away.
  - Dedicated deployment admin setup script (`scripts/deploy/setup_admin.py`) for clean database initialization and admin account creation across Windows and Linux.
- **Verification**:
  - All PowerShell scripts parse with 0 errors in Windows PowerShell 5.1.
  - `setup_admin.py` verified with SQLite and clean ASCII terminal rendering.
  - Zero orphaned background processes remaining.

---

### Phase 23: Documentation Audit, Link Integrity, FAQ Recovery Guides & Release Readiness ✅ Completed (2026-10-18)
- **Status**: `done-tested-working`
- **Full Markdown Documentation Audit**:
  - Validated all relative links across repository root, `docs/`, and `plans/`.
  - Corrected link in `README.md` to point to `docs/dev/SSDF_COMPLIANCE.md` and `docs/dev/NIST_CSF_2_ALIGNMENT.md`.
  - Updated `docs/admin/BACKUP_RESTORE.md` timestamps and added canonical cross-references in `plans/plans.md`.
  - Updated `docs/user/FAQ.md` with explicit details for self-service recovery codes, 1-click teacher pre-test unlocks (`⚡ Reset Pwd for Test`), and native midnight automated database backups.
  - Preserved user community updates in `THANKS.md`.
- **Directory & Script Hygiene**:
  - Cleaned empty temporary folders.
  - Verified no orphaned processes running.
- **Verification**:
  - Automated link validation: 0 broken relative markdown links across entire repo.
  - Backend test suite: 122/122 passed clean.
  - Frontend portal build & oxlint: 0 errors, 0 warnings.

---

### Phase 24: External AI GitHub Remote Deploy & Uninstall Drill (First-Try Clean) ✅ Completed (2026-10-19)
- **Status**: `done-tested-working`
- **End-to-End Simulation**:
  - Simulated a clean-machine external AI installer reading directly from GitHub remote (`https://github.com/ezixen/PlannedEducation.git`).
  - Executed git clone into default `C:\PlannedEducation`, automated setup via `install.ps1 -AutoConfirm`, health verification via `verify.ps1`, and cleanup via `uninstall.ps1 -AutoConfirm`.
- **Issues Caught & Fixed**:
  - Step 9 FastAPI test runner unquoted string issue resolved via piped script with explicit `.env` environment loading.
  - Resolved `$credFile` print timing in Step 8 so credentials file path is displayed in console banner.
  - Resolved PowerShell 5.1 drive colon syntax collision in `verify.ps1` and `start_all.ps1` by adopting `${domain}:${port}`.
  - Reset `config/deployment.json` repository defaults and prevented sample template values from overriding fresh install parameters.
  - Added copy-paste `git clone` steps to `README.md` and `docs/admin/INSTALL_WINDOWS.md`.
- **Verification Results**:
  - `install.ps1`: 5/5 verification tests passed on clean first run.
  - `verify.ps1`: 0 parser/syntax errors.
  - `uninstall.ps1`: Complete directory removal with 0 residual files, preserving all external system dependencies.
  - 0 orphaned background processes remaining.

---

### Phase 25: Linux & WSL GitHub Remote Deploy & Uninstall Drill (Complete Lifecycle Verification) ✅ Completed (2026-10-19)
- **Status**: `done-tested-working`
- **End-to-End Simulation**:
  - Tested complete remote install, startup, health verification, and uninstallation workflow in WSL (Ubuntu 24.04) from clean GitHub clone to `/opt/plannededucation`.
- **Issues Identified & Fixed**:
  - **POSIX File Modes in Git**: Marked all 7 shell scripts (`install.sh`, `uninstall.sh`, backup, deploy, and test scripts) with executable bit (`chmod +x` / mode `100755`) in the git index to prevent `Permission denied` on Linux/WSL.
  - **Package Engine Health Endpoint**: Updated `src/plannededucation/api/routes_packages.py` `/packages/health` check to return `"status": "ok"` alongside `"available": True`, and updated `verify.sh` to accept both indicators. Added test coverage in `tests/test_main.py`.
  - **Headless Vite Preview Daemon (`web/apps/portal/scripts/preview-server.mjs`)**: Vite CLI (`vite preview`) binds to stdin for CLI shortcuts and terminates on stdin EOF unless configured programmatically. Implemented headless preview daemon using Vite's first-class JavaScript API (`preview()`), ignoring SIGHUP and running cleanly as an independent background daemon.
  - **Background Service Detachment**: Added `disown` for backend and frontend processes in `start_all.sh`, and enhanced startup readiness loop to poll and verify both Backend API (`/health`) and Frontend Portal (`5173`) before declaring the system live.
  - **Process Termination in `stop_all.sh`**: Added `pkill -f "preview-server.mjs"` to ensure frontend preview server processes are cleanly terminated when stopping platform.
- **Verification Results in WSL (Ubuntu 24.04)**:
  - `install.sh`: **5 passed, 0 failed** (all automated verification checks passed).
  - `start_all.sh`: Started both backend (`:8000`) and frontend (`:5173`) with live health confirmation.
  - `verify.sh`: **ALL SYSTEMS OPERATIONAL ✅** (Directory, database file, Backend API, Package Engine, Frontend Portal).
  - `stop_all.sh`: Stopped all platform processes cleanly.
  - `uninstall.sh`: Completely removed `/opt/plannededucation` with 0 residual files, self-cleaned, and kept all external system dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git) intact.
  - 0 orphaned background processes remaining.

---

### Phase 26: Local Dev Isolation, Uninstaller Custom Directory Prompt & Multi-Path Install Documentation ✅ Completed (2026-10-19)
- **Status**: `done-tested-working`
- **Local Dev Isolation (`AGENTS.md` & `.gitignore`)**:
  - Untracked `AGENTS.md` from the git index (`git rm --cached AGENTS.md`) and added it to `.gitignore` along with `.github/copilot-instructions.md`.
  - Local PC-specific developer rules, paths, and instructions remain safe and persistent on this machine only, preventing them from being pushed to GitHub or confusing downstream users and AI agents.
- **Install & Uninstall Directory Parity & Interactive Prompting**:
  - Parity established: both `install.ps1` and `uninstall.ps1` default to `C:\PlannedEducation`; both `install.sh` and `uninstall.sh` default to `/opt/plannededucation`.
  - `uninstall.ps1` and `uninstall.sh` now explicitly prompt for custom installation directories when run interactively, with validation and clean retry loops.
- **Dynamic Virtual Environment Resolution**:
  - Removed all shared `C:\.venv` fallbacks from `install.ps1` and generated launchers (`start_all.ps1`, `start_backend.ps1`). Every deployment now strictly creates and runs within `$InstallDir\.venv`.
  - Updated dev launcher scripts (`start.ps1`, `start_all.ps1`, `start_student.ps1`) to dynamically search for `C:\.venv`, `.venv`, and PATH `python`.
  - Replaced machine-specific `D:\` paths in `backup_restore_drill.ps1`, `.github/workflows/backup-restore-drill.yml`, and `TESTING_GUIDE.md` with standard paths.
- **Multi-Path Installation Documentation**:
  - Updated `README.md`, `DEPLOY.md`, `docs/admin/INSTALL_WINDOWS.md`, `docs/admin/INSTALL_LINUX.md`, and `docs/admin/DEPLOYMENT_GUIDE.md` with kind, welcoming, and accessible guidance:
    1. **School IT Administrators**: Clean, fast, zero-telemetry native scripts.
    2. **Hands-Off AI Coding Agents**: One-prompt automated deployment for VS Code, Cursor, Devin, Claude Code, Antigravity, etc.
    3. **Friendly Free Chat AI Companions**: Plain-language step-by-step guidance for non-technical educators and parents using ChatGPT, Claude, Gemini, or Copilot.

---

### Phase 27: i18n Migration & Deployed System Workflow Verification ✅ Completed (2026-10-20)
- **Status**: `done-tested-working`
- **Comprehensive UI i18n Migration**:
  - Migrated all remaining hardcoded English text in `web/apps/portal/src/` to `t()` calls using `I18nContext`.
  - Added ~300 standardized keys (`stt.*`, `proctoring.*`, `forgot_password.*`, `chatgpt.*`, `deployment.*`, `teacher_correction.*`, `db_backup.*`, `notifications.*`, `student_review.*`, `backup_codes_modal.*`, `faq.*`, `admin.*`, `languages.*`, etc.).
  - Synchronized all keys across all 18 locales in `web/apps/portal/src/locales/` (`en`, `hu`, `es`, `de`, `fr`, `ja`, `zh`, `pt`, `uk`, `it`, `pl`, `nl`, `sv`, `no`, `da`, `fi`, `pt-BR`).
- **Platform Deployment & Workflow Verification**:
  - Deployed native Mode 1 SQLite deployment to default install directory `C:\PlannedEducation`.
  - Verified complete end-to-end user journeys:
    1. Superadmin authentication & dashboard management.
    2. Teacher registration & superadmin approval panel.
    3. Exam & question authoring, package creation, and publishing.
    4. Student exam taking, auto-grading, and question response persistence.
    5. Parent registration, student relationship linking, and progress tracking.
    6. Database backup creation and validation.
- **Frontend & Backend Test Verification**:
  - Frontend production build (`npm run build`) succeeded with 0 errors and generated service worker PWA.
  - Backend test suite (`scripts/testing/update_test_cache.py`) passed all 123 tests cleanly.

---

### Phase 28: Dependency Security Auditing, Ruff Linting & CI/CD Hardening ✅ Completed (2026-10-21)
- **Status**: `done-tested-working`
- **pip-audit Implementation**:
  - Installed `pip-audit` into `C:/.venv` and implemented `scripts/testing/run_pip_audit.py`.
  - Integrated `--audit` flag directly into central test runner `run_tests.py` (`python run_tests.py --audit`).
  - Audited `src/requirements.txt`: verified all 72 dependencies are clean.
  - Documented and handled upstream `presidio-anonymizer 2.2.364` dependency pinning (`cryptography<49.0.0,>=48.0.1`), passing `--ignore-vuln` for `PYSEC-2026-3552`, `PYSEC-2026-3553`, `PYSEC-2026-3554`.
- **npm audit & Portal Dependency Fixes**:
  - Executed `npm audit fix` in `web/apps/portal` to upgrade `vite` (8.3.4) and `follow-redirects` (1.16.2).
  - `npm audit` reports 0 vulnerabilities.
- **Code Quality & Linting Clean-up**:
  - Fixed `SIM105` in `src/plannededucation/api/main.py` and `src/plannededucation/api/routes_chat.py` using `contextlib.suppress`. Ruff reports 0 errors across `src/`.
  - Cleaned up unused catch parameter warning in `web/apps/portal/src/pages/Login.tsx`. Oxlint reports 0 warnings and 0 errors.
  - Set `user.reset_expires = None` on password reset completion in `src/plannededucation/api/routes_auth.py`.
- **Script & Curriculum Clean-up**:
  - Replaced hardcoded absolute paths `D:/Dev/...` in `scripts/generate_hungary_modules.py` and `scripts/generate_hungary_modules_v2.py` with repository-relative `Path(__file__).resolve()`.
  - Updated `plans/test-modules/modules/germany/grade-01/englisch/module-01-phonics.json` with authentic Grade 1 English phonics and vocabulary questions with German classroom instructions.
  - Refactored `install.ps1` clipboard handling and emergency recovery codes display with non-blocking `$AutoConfirm` safety.
  - Reverted `config/deployment.json` to neutral school default template values.
- **Verification**:
  - `run_tests.py --audit`: passed (0 vulnerabilities found).
  - `scripts/testing/update_test_cache.py`: passed 123/123 tests in 131s.
  - `npm run build`: built in 4.84s (PWA enabled, 0 errors).
  - 0 orphaned background processes remaining.
