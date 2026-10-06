# Project Kickoff Decision Worksheet — PlannedEducation (Completed)

**Version**: 1.0
**Date**: 2026-10-06
**Project**: PlannedEducation — Free/Open-Source Teacher's Aid, Grading Software, Secure Test-Taking Environment

---

## 1. Project Profile

- **Project name**: PlannedEducation
- **Owner**: ezixen (GitHub)
- **Product type**: Web app (React/TypeScript) + API (FastAPI/Python) + PWA
- **Target regions**: Global (i18n planned)
- **Primary languages/locales**: en-US (MVP), es-ES, de-DE, fr-FR, ja-JP, zh-CN (planned)
- **Regulated data**: Moderate (student PII, exam content, grades)
- **Data classes used**: 
  - Public: Documentation, open-source code
  - Internal: Teacher configs, exam metadata
  - Confidential: Student submissions, grades, AI interactions
  - Restricted: AI API keys (encrypted), authentication secrets
- **Launch target date**: Continuous deployment; v1.0 milestone TBD

---

## 2. Goal and Constraints Snapshot

- **Top 3 business outcomes**:
  1. Free, privacy-respecting exam platform for teachers worldwide
  2. External AI integration (BYOK) for grading/test creation without vendor lock-in
  3. Offline-first, secure test-taking with SEB/proctoring
- **Top 3 technical constraints**:
  1. **Zero paid services** — all infrastructure free-tier or self-hosted
  2. **No internal LLM** — AI is external-only via pluggable API system
  3. **Student privacy first** — anonymization, minimal data collection, GDPR/COPPA/FERPA
- **Team size now**: 1 (solo founder) + community contributors
- **Expected users in 3 months**: 50-100 teachers (beta)
- **Expected users in 12 months**: 500-1000 teachers
- **Budget model**: Free-tier first, self-hosted, community-supported

---

## 3. Workload Pattern

**Primary**: CRUD-heavy business workflows (exam management, grading, user management)
**Secondary**: 
- Realtime collaboration (secure chat during exams)
- AI-heavy generation/inference workflows (external AI for grading/test creation)
- Event-driven pipeline (proctoring events, WebSocket broadcasting)

**Why**: Education workflows are primarily CRUD with specific realtime needs during exams. AI is batch/async, not realtime.

---

## 4. Architecture Track Selector

**Selected track**: **Track A — Startup speed (free-tier friendly)**

**Reason**: 
- Solo founder, zero budget, free-tier mandate
- Rapid iteration needed for teacher feedback
- Can evolve to Track B if enterprise adoption requires compliance features

**Defaults adopted**:
- Frontend: React 19 + TypeScript + Vite (not Next.js — SPA + PWA)
- Backend: FastAPI + Python 3.12+ (async, type-safe)
- Data/Auth: PostgreSQL (self-hosted) + Google SSO + TOTP 2FA + Passkeys (planned)
- Hosting: Docker Compose (self-hosted), GitHub Pages/Vercel (frontend), any VPS (backend)
- CI/CD: GitHub Actions (free tier)

---

## 5. Stack and Platform Decisions

### Frontend
- **Choice**: React 19 + TypeScript + Vite + PWA (vite-plugin-pwa)
- **Alternative rejected**: Next.js
- **Rejection reason**: SPA + PWA simpler for offline-first exam engine; no SSR needed; smaller bundle

### Backend
- **Choice**: FastAPI + Python 3.12+ + SQLAlchemy 2.0 + Pydantic v2
- **API style**: REST (OpenAPI auto-generated) + WebSocket for chat/proctoring
- **Alternative rejected**: Node.js/Express, Go, .NET
- **Rejection reason**: Python ecosystem for AI/ML integrations, type safety with Pydantic, async native

### Data Layer
- **Primary DB**: PostgreSQL 16 (self-hosted via Docker)
- **Cache/Message Queue**: Redis 7 (Pub/Sub for WebSocket, caching)
- **Object Storage**: None currently (all in DB); future: Cloudflare R2 / MinIO

### Hosting/Runtime
- **Compute Platform**: Docker Compose (self-hosted VPS), Kubernetes (k3s) for scale
- **Region Strategy**: Single region initially; multi-region via read replicas if needed
- **CDN/Edge**: Cloudflare (free tier) for DNS, CDN, WAF, Workers

---

## 6. Identity and Access Decisions

- **Primary auth**: Google SSO (OAuth2/OIDC) — no passwords for login
- **Passkeys/WebAuthn**: Planned as phishing-resistant 2FA (OWASP A07:2025)
- **Fallback**: Self-service password reset via email OTP (6-digit, 10-min expiry)
- **2FA**: TOTP (RFC 6238) with `pyotp`, QR code, 5 recovery codes (8 chars, one-time use)
- **Identity provider**: Google (primary), extensible to others via OIDC
- **MFA policy**: Optional for students, required for teachers (grading access)
- **Authorization model**: RBAC (teacher/student/parent) + row-level ownership (`_require_exam_owner`)
- **Tenant isolation model**: Shared schema with ownership columns (single-tenant SaaS)
- **Session/token strategy**: 
  - JWT HS256, 60-min access tokens
  - Refresh tokens (30 days, rotating, hashed in DB)
  - Secure, HttpOnly, SameSite=Strict cookies

---

## 7. Security Baseline (Mandatory)

| Control | Status | Owner |
|---|---|---|
| Input validation at all trust boundaries | ✅ Done | Pydantic schemas, SQLAlchemy ORM |
| TLS 1.3 enforced in transit | ✅ Done | Production: SSL mode=require; Cloudflare |
| Encryption at rest with KMS-managed keys | 🔄 Partial | Fernet for AI keys (AES-128); PostgreSQL TDE planned |
| Secret management (no secrets in repo/client) | ✅ Done | GitHub Environments/Secrets, `.env` gitignored |
| Dependency and container scanning in CI | 🔄 Partial | `pip-audit`, `npm audit` planned; `trivy` planned |
| SBOM generation for releases | ✅ Done | `sbom-python.json`; Node SBOM planned |
| Signed artifacts/provenance | 📋 Planned | cosign, SLSA Level 1 |
| Audit logging for privileged actions | ✅ Done | Structured JSON logs, security events, request IDs |

**Security owner**: ezixen (founder)

---

## 8. Reliability and Operations Baseline

- **SLO targets**: 
  - API latency p95 < 500ms
  - API availability > 99.9%
  - Exam submission success rate > 99.5%
  - AI grading response time < 30s
- **RPO target**: < 24 hours (daily DB backups)
- **RTO target**: < 4 hours (automated restore drills)
- **Backup schedule**: Daily 02:00 UTC (PostgreSQL), continuous (Git), Redis RDB snapshots
- **Restore drill cadence**: Monthly (first Saturday, staging environment)
- **Incident owner/on-call**: ezixen (solo); documented runbooks in `docs/runbooks/`

---

## 9. Internationalization and Accessibility Baseline

- **ICU MessageFormat enabled**: 📋 Planned (react-i18next + ICU)
- **RTL support required**: 📋 Planned (CSS logical properties)
- **Locale fallback strategy**: en-US → browser locale → explicit user preference
- **Accessibility target**: WCAG 2.1 AA
- **Languages included in MVP**: en-US only; i18n infrastructure in Phase 10

---

## 10. Payments and Communications

- **Payments provider**: None (platform is free)
- **Marketplace split payments needed**: No
- **Email provider**: Development = console log; Production = self-hosted Postfix or free tier (Gmail SMTP, SendGrid free 100/day)
- **SMS/OTP provider**: None (email OTP only for password reset)
- **Abuse/rate-limit controls defined**: ✅ Done (slowapi: 5-20/min per endpoint)

---

## 11. AI Usage Governance

- **Approved AI coding tools**: GitHub Copilot, Cursor, local models via Ollama
- **Human review required for security/auth/payment code**: ✅ Yes (mandatory)
- **Prompt data policy (no secrets/PII)**: ✅ Yes (enforced in `AI_RISK_GOVERNANCE.md`)
- **AI-generated code provenance noted in PRs**: ✅ Yes (PR template includes AI provenance)

---

## 12. CI/CD Gate Checklist (Must be enabled)

| Gate | Status | Tool |
|---|---|---|
| Lint/format checks | ✅ Done | oxlint, ruff, black |
| Unit tests | ✅ Done | pytest, vitest |
| Integration tests | ✅ Done | pytest (API), vitest (components) |
| Secret scan | 🔄 Planned | gitleaks OSS binary |
| SAST/dependency scan | 🔄 Planned | bandit, pip-audit, npm audit, eslint-security |
| IaC policy checks | 📋 Planned | checkov/trivy for Docker |
| Contract/schema compatibility checks | ✅ Done | OpenAPI schema validation, Pydantic |

---

## 13. Cost Plan (Free Tier to Scale Path)

### MVP Phase (Current)
- **Services expected to stay in free tier**:
  - GitHub (repo, Actions 2000 min/mo, Pages, Packages)
  - PostgreSQL (self-hosted on VPS ~$5/mo or free tier Neon/Supabase)
  - Redis (self-hosted)
  - Cloudflare (DNS, CDN, WAF, Workers free tier)
  - Vercel/Netlify (frontend hosting free tier)
  - Grafana Cloud (metrics/logs/traces free tier)
  - Sentry (developer plan free tier)
- **Hard monthly budget cap**: $10 (VPS for PostgreSQL/Redis if not free tier)

### Growth Phase
- **First paid services likely needed**:
  - Managed PostgreSQL (Neon Pro ~$25/mo or Supabase Pro ~$25/mo) if self-hosting burden too high
  - Grafana Cloud paid tier if metrics volume exceeds free tier
  - Sentry paid tier if event volume exceeds free tier
- **Trigger metrics for upgrade**:
  - > 1000 daily active teachers
  - > 100k exam submissions/month
  - > 1M AI grading calls/month
  - Metrics/logs retention > 30 days needed
- **Approximate monthly budget at growth stage**: $50-100/mo

---

## 14. Decision Confidence Score

| Area | Score (1-5) | Notes |
|---|---|---|
| Product scope clarity | 5 | Clear: free exam platform + external AI |
| Architecture fit | 5 | Track A matches constraints perfectly |
| Security readiness | 4 | Strong baseline; passkeys, supply chain, SBOM signing pending |
| Reliability readiness | 3 | Backups done; restore drills, SLOs, alerting pending |
| Cost predictability | 5 | Free-tier first, clear scale path |
| Team execution readiness | 4 | Solo founder; community can help with docs/testing |

**Total score (out of 30): 25**

**Interpretation**: 20-25 → Proceed with explicit risk register

---

## 15. Risks and Mitigations

### 1. Risk: AI Provider API Changes / Deprecation
- **Impact**: Grading/test creation features break
- **Mitigation**: Multi-provider abstraction layer; version pinning; fallback providers
- **Owner**: ezixen

### 2. Risk: Student Data Privacy Violation (PII to AI)
- **Impact**: Legal (FERPA/COPPA/GDPR), trust loss
- **Mitigation**: Anonymizer pipeline (Presidio), data minimization, teacher approval required
- **Owner**: ezixen

### 3. Risk: Supply Chain Compromise (Malicious Dependency)
- **Impact**: Code execution, data exfiltration
- **Mitigation**: `pip-audit`/`npm audit` in CI, pinned versions, SBOM, gitleaks, Dependabot
- **Owner**: ezixen

### 4. Risk: Database Loss / Corruption
- **Impact**: Complete data loss (exams, grades, users)
- **Mitigation**: Daily encrypted backups, monthly restore drills, PITR capability
- **Owner**: ezixen

### 5. Risk: Single Founder Bus Factor
- **Impact**: Project stalls if founder unavailable
- **Mitigation**: Comprehensive docs (`PLANS_UPDATED.md`, runbooks), open-source, bus-factor-friendly architecture
- **Owner**: ezixen

---

## 16. Final Sign-off

- **Architecture lead**: ezixen ✅
- **Security lead**: ezixen ✅
- **Product owner**: ezixen ✅
- **Date**: 2026-10-06

---

## Appendix: Key Architectural Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-28 | FastAPI + React + PostgreSQL | Type safety, async, Python AI ecosystem |
| 2026-09-28 | Google SSO primary, no passwords | Security, simplicity, free |
| 2026-09-28 | TOTP 2FA + recovery codes | OWASP recommended, free |
| 2026-10-01 | External AI only (BYOK) | Zero cost, no vendor lock-in, teacher choice |
| 2026-10-01 | Anonymizer + Presidio for PII | FERPA/COPPA/GDPR compliance |
| 2026-10-04 | Offline-first exam engine (IndexedDB) | Equity (no internet during exam), integrity |
| 2026-10-04 | SEB + Proctoring optional | Teacher choice, GDPR consent |
| 2026-10-05 | Admin portal removed | Scope reduction, user portal only |
| 2026-10-06 | OWASP Top 10:2025 alignment | Current security baseline |
| 2026-10-06 | NIST AI RMF + Generative AI Profile | AI risk governance for external AI |
| 2026-10-06 | NIST SSDF 1.1 compliance | Secure SDLC |
| 2026-10-06 | NIST CSF 2.0 alignment | Organizational cybersecurity |
| 2026-10-06 | Passkeys/WebAuthn planned | Phishing-resistant auth (A07:2025) |