# Planned Education - Plans Updated 2026-09-28

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
| **A03:2025 Software Supply Chain Failures** | Dependency scanning, SBOM, signed artifacts, provenance | `pip-audit`/`npm audit` in CI, `sbom-python.json`, pinned dependencies, SLSA provenance (planned) |
| **A04:2025 Cryptographic Failures** | TLS 1.3, Argon2id, Fernet, JWT HS256, key management | Argon2id (time_cost=3, memory=64MB), Fernet for AI keys, JWT 60-min expiry, HTTPS-only cookies, KMS-ready |
| **A05:2025 Injection** | Parameterized queries, input validation, output encoding | SQLAlchemy ORM, Pydantic schemas with strict validation, no raw SQL, XSS prevention |
| **A06:2025 Insecure Design** | Threat modeling, secure defaults, fail-secure | Security audit logging, rate limiting, constant-time comparisons, fail-secure defaults |
| **A07:2025 Authentication Failures** | MFA, passkeys/WebAuthn, brute force protection | Google SSO primary, TOTP 2FA, recovery codes, rate limiting (5-20/min), Argon2id, **Passkeys planned** |
| **A08:2025 Software/Data Integrity Failures** | CI/CD integrity, signed artifacts, SBOM verification | Pinned dependencies, CI security gates, artifact signing (planned), supply chain verification |
| **A09:2025 Security Logging/Monitoring Failures** | Structured JSON logs, security events, alerting | Request ID middleware, auth/exam mutation audit logs, global exception handler, SLO alerting (planned) |
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

### Phase 7: OWASP Top 10:2025 Alignment & NIST Standards 🔄 In Progress

#### 7.1 OWASP Top 10:2025 Full Alignment ✅ Updated
- Updated OWASP mapping table to 2025 categories (A01-A10)
- **A03 Software Supply Chain Failures**: Added `pip-audit`/`npm audit` in CI, SBOM generation, pinned dependencies
- **A08 Software/Data Integrity Failures**: CI/CD integrity gates, artifact signing (planned)
- **A09 Security Logging/Monitoring Failures**: Structured logging, SLO alerting (planned)
- **A10 Mishandling of Exceptional Conditions**: Generic error responses, no stack traces in prod

#### 7.2 NIST AI RMF 1.0 + Generative AI Profile (NIST-AI-600-1) 🔄 Planned
- **AI Risk Governance for External AI Grading**: Since AI is external-only via pluggable API system, risk controls focus on:
  - Prompt injection prevention (input sanitization on teacher prompts)
  - Model output validation (hallucination detection, format verification)
  - Data minimization (anonymizer strips PII before sending to AI)
  - Audit trail for all AI interactions (request/response logging)
  - Teacher approval workflow for AI-suggested grades
- **Generative AI Profile Controls**:
  - Input validation on all teacher-provided prompts
  - Output schema validation (JSON schema for AI responses)
  - Rate limiting on AI API calls per teacher
  - Cost monitoring and budget alerts per teacher
  - Fallback to manual grading if AI service unavailable

#### 7.3 NIST SSDF 1.1 Alignment 🔄 Planned
- **Secure Development Practices**:
  - [ ] SAST in CI (bandit for Python, ESLint security rules for TypeScript)
  - [ ] Dependency scanning (`pip-audit`, `npm audit`) - partially done
  - [ ] SBOM generation for releases (`sbom-python.json` exists)
  - [ ] Container image scanning (Trivy/Snyk) for Docker builds
  - [ ] Signed artifacts and provenance (cosign/SLSA) - planned
  - [ ] AI-assisted code review requirements (human approval for auth/payment/security)

#### 7.4 NIST CSF 2.0 Alignment 🔄 Planned
- **Govern**: Project security policy, risk management strategy
- **Identify**: Asset inventory (data, models, APIs), supply chain risk
- **Protect**: Access control, data encryption, awareness training
- **Detect**: Security monitoring, anomaly detection, logging
- **Respond**: Incident response plan, communication procedures
- **Recover**: Backup/restore drills, business continuity

### Phase 8: Passkeys/WebAuthn Implementation 🔄 Planned (OWASP A07:2025)
- **Primary**: Google SSO (OAuth2/OIDC) — remains primary
- **Passkeys/WebAuthn**: Add as phishing-resistant second factor
  - WebAuthn/FIDO2 registration during 2FA setup
  - Platform authenticators (Windows Hello, Touch ID, Android biometrics)
  - Cross-device sync via iCloud Keychain / Google Password Manager
  - Fallback to TOTP 2FA for devices without passkey support
- **Implementation**: `py_webauthn` library, new endpoints `/auth/webauthn/*`
- **UI**: Settings page integration alongside existing TOTP 2FA

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

### Phase 10: Internationalization (i18n) Foundation 🔄 Planned
- **ICU MessageFormat** for all user-facing strings
- **Externalized strings** in React components (`useTranslation` hook)
- **Locale-safe formatting**: dates, numbers, currencies via `Intl` API
- **RTL support** preparation (CSS logical properties)
- **Supported locales**: en-US (default), es-ES, de-DE, fr-FR, ja-JP, zh-CN

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
- **Alerting**: 🔄 Planned - Burn rate alerting on SLOs via Prometheus/Grafana

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

### Phase 14: Project Kickoff Worksheet Completion 📋 Planned
- Fill out `PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md` for PlannedEducation
- Document all architecture/security/reliability/cost decisions
- Decision confidence scoring

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

**Remaining Work**:
- [ ] AI Provider Abstraction Layer (base class + adapters)
- [ ] Grading endpoint with prompt templates
- [ ] Test creation endpoint with schema validation
- [ ] Content generation endpoint
- [ ] Rate limiting & cost tracking per teacher
- [ ] Output validation & hallucination detection
- [ ] Teacher review/approval workflow for AI outputs