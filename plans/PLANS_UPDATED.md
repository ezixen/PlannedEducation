# Planned Education - Plans Updated 2026-09-28

## Execution Order (The Roadmap) — Updated Status

### Phase 1: Foundation ✅ Completed
- **Database models**, Authentication (Google SSO + Standard + TOTP 2FA), and the React Vite Portal Shell (Routing, Hamburger Menu, Themes)
- All auth routes implemented; user models with `RoleEnum`; Google SSO with dev auth gating via `ALLOW_DEV_AUTH` env var; JWT config with `JWT_SECRET_KEY`; CORS restricted to explicit origins; password policies with `passlib` complexity; TOTP 2FA column added to `User` model; `is_active` check on every auth path
- **Self-Service Password Reset & 2FA (NEW)** — Email OTP reset (6-digit, 10-min expiry), recovery codes for 2FA users (5 codes, 8 chars, one-time use), TOTP setup/confirm/disable/regenerate endpoints. Google SSO is primary login; password exists ONLY for self-service reset fallback. No admin portal needed — all flows user-self-service. Rate limited (5/min request, 10/min confirm).
- **All 18 auth tests pass** (existing) + new endpoints ready for testing

### Phase 2: Core Exam Engine ✅ Completed / 🟡 Incremental
- **Test creation**, Class Groupings, Question Banks, Variables, Accommodations, and offline PWA support
- Exam CRUD with owner enforcement (`_require_exam_owner` helper); question creation; SEB config generation; dynamic math `[rand:1-10]` randomization; multiple-choice scrambling; IEP time multipliers (1.5x/2.0x) stored in `StudentRecord.time_multiplier`; class grouping UI; exam listing returns safe metadata only via `ExamListResponse` schema
- **All 11 exam tests pass**
- **Remaining**: Full PWA IndexedDB sync for offline progress, modular test package sharing, offline-first question bank UI

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

### Phase 5: Optional Proctoring 🟡 Incremental
- **WebRTC/Webcam AI proctoring toggle** with GDPR compliance flags
- `ProctoringToggle.tsx` UI with camera/mic toggle, GDPR warning badge, video element preview, disable proctoring flow
- **Backend proctoring routes** — `/proctoring/events`, `/proctoring/sessions`, `/proctoring/stats` with RBAC (22 tests pass)
- **Remaining**: Backend proctoring event pipeline, eye-movement tracking, multiple-face detection, background audio analysis, GDPR consent flow

### Phase 6: Admin Portal ✅ Completed (2026-10-04)
- **Admin Dashboard** — System stats (users, exams, submissions, active exams)
- **User Management** — List, search, filter, activate/deactivate, delete users with role badges
- **Exam Management** — List, search, filter by status, delete exams with teacher info
- **System Settings** — Environment status, security/compliance overview, maintenance actions
- **Admin Settings** — 2FA TOTP UI (QR code setup, verification, recovery codes, disable/regenerate)
- **Admin Context** — React context for state management with stats, users, exams
- **Admin Layout** — Collapsible sidebar navigation with Dashboard, Users, Exams, System, Settings
- **Toast Notifications** — Ported from portal for consistent UX
- **All 12 admin route tests pass**


| OWASP Category | Control | Implementation |
|---|---|---|
| **A01: Broken Access Control** | Deny by default, RBAC, row-level access | `_require_exam_owner` helper, `AccountRelationship` with status checks, teacher-only exam mutations |
| **A02: Cryptographic Failures** | TLS 1.3, Argon2id, Fernet, JWT HS256 | Argon2id (time_cost=3, memory=64MB), Fernet for AI keys, JWT 60-min expiry, HTTPS-only cookies |
| **A03: Injection** | Parameterized queries, input validation | SQLAlchemy ORM, Pydantic schemas with strict validation, no raw SQL |
| **A04: Insecure Design** | Threat modeling, secure defaults | Security audit logging, rate limiting, constant-time comparisons, fail-secure defaults |
| **A05: Security Misconfiguration** | Secure headers, no debug in prod | CSP, HSTS, X-Frame-Options, TrustedHostMiddleware, Swagger disabled in prod |
| **A06: Vulnerable Components** | Dependency scanning, locked versions | `requirements.txt` pinned, `slowapi` for rate limiting, `argon2-cffi` for hashing |
| **A07: Authentication Failures** | MFA, passkeys-ready, brute force protection | Google SSO primary, TOTP 2FA, recovery codes, rate limiting (5-20/min), Argon2id |
| **A08: Software Integrity Failures** | SBOM, signed artifacts, CI gates | Pinned dependencies, CI security gates (planned), artifact signing (planned) |
| **A09: Logging/Monitoring Failures** | Structured JSON logs, security events | Request ID middleware, auth/exam mutation audit logs, global exception handler |
| **A10: SSRF** | Input validation, allow-lists | Explicit CORS origins, allowed hosts, no user-controlled URLs |

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

**Remaining Infrastructure Items**:
- Backend proctoring event pipeline, eye-movement tracking, multiple-face detection, background audio analysis, GDPR consent flow
- PWA IndexedDB sync for offline progress
- Modular test package sharing
- Offline-first question bank UI