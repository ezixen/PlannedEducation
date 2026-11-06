# PlannedEducation — Security Architecture (Developer Reference)

> **Audience:** developers and security reviewers only.
> **Last verified:** 2026-11-07 (security/logic audit remediations + F-019 MediaPipe face/gaze + F-043 CSP3 style split + F-017 PRF wrap).
> Classroom wording for the same topics: [`docs/user/`](../user/).

This document describes **what the code does today**, not aspirational design. Where a control is incomplete, it is marked **Open**.

## Verification evidence (2026-11-06)

Run via `scripts/testing/update_test_cache.py`:

- `backend-proctoring-ocr-parent` — 42 passed (`test_routes_proctoring`, `test_routes_ocr`, `test_routes_parent`)
- `backend-auth-security` battery — 65 passed (`test_auth_flows`, `test_security_f006_015`, `test_exams`, `test_routes_archive_and_ai`, plus the three suites above)
- `backend-security-deferred` — 7 passed (`test_security_deferred_f027_052`)
- `backend-security-backup` — 6 passed (`test_security_backup_aead`)
- `backend-security-f024-migrate` — 1 passed (`test_security_f024_legacy_migrate`)
- `backend-security-f021-024` — 23 passed
- `backend-security-f048` — 16 passed
- `backend-security-f006-049` — 5+ passed (`test_security_f006_049`, `test_security_f006_049_webauthn_sessions`)

Audit trail: `plans/2026-11-06_2045_SECURITY_LOGIC_AUDIT.md`.

---

## 1. Authentication & session tokens

| Control | Behavior | Primary code |
|---------|----------|--------------|
| Access JWT | Claims include `type: "access"`. REST `get_current_user` and chat WebSocket auth reject any other type (refresh tokens cannot call APIs). | `routes_auth.get_current_user`, `routes_chat` WS auth, `auth.create_access_token` |
| Refresh JWT | `type: "refresh"`; validated through `/auth/refresh` with per-device `RefreshSession` rotation/reuse detection. | `auth.issue_refresh_session`, `auth.rotate_refresh_session` |
| Browser storage | Portal keeps access/refresh tokens in **sessionStorage**. Legacy `localStorage` tokens are migrated once then removed. | `AuthContext.tsx` |
| Password hashing | Argon2id via project auth helpers. | `auth.py` / `routes_auth` |
| TOTP 2FA | When `totp_enabled`, password login requires a valid TOTP (`2FA_REQUIRED` if missing). | `routes_auth._verify_user_second_factor` |
| WebAuthn login | Unauthenticated `POST /auth/webauthn/login/start|finish` issues tokens after assertion; portal Login has passkey button. | `routes_auth`, `Login.tsx` |
| Recovery codes | High-entropy codes; stored hashed; single-use for reset/disable flows. | `auth.generate_recovery_codes`, reset/2FA routes |
| Brute-force lockout | Failed logins increment counters; lockout window applies. | `routes_auth` login path |
| Logout / password change | Revokes refresh session(s); password change/reset revokes all families. | `/auth/logout`, settings + reset routes |

**Residual:** CAPTCHA on public auth (intentionally no paid CAPTCHA). Production `style-src` no longer allows `'unsafe-inline'` for stylesheets; React `style={{}}` still needs `style-src-attr 'unsafe-inline'` (CSP3). `Permissions-Policy payment=()` disables the Payment Request API (free/OSS — not a billing feature).

---

## 2. Roles & authorization

| Role | How it is granted | What it can do |
|------|-------------------|----------------|
| Student | Self-register `role=student` | Take exams (student-only start/submit), view own results |
| Teacher | Self-register `role=teacher` with `teacher_approved=False` in production/dev | After admin approval: author exams, grade, class tools |
| Parent | Self-register `role=parent` | Link children (handshake), view progress for **active** relationships only |
| Admin | Created by superadmin (`is_admin=True`, `is_superadmin=False`) | User/ops admin surfaces; **cannot** create other admins/superadmins |
| Superadmin | Bootstrap installer / `require_superadmin` path (`is_admin` + `is_superadmin`) | Create admins/superadmins; highest privilege resets |

Shared helpers:

- `authorization.require_exam_author` — approved teacher or admin
- `routes_admin.require_admin` / `require_superadmin`
- Archive admin routes use `Depends(require_admin)` (F-002)
- AI grade/download/return/bulk check exam ownership (F-004)

Teacher approval defaults are **fail closed** on the `User` model (`teacher_approved` default/server_default false). Registration sets approval explicitly; in `PLANNED_EDUCATION_ENV=test`, non-`pending` teachers are auto-approved for legacy unit tests only.

---

## 3. Exam integrity

| Control | Behavior | Status |
|---------|----------|--------|
| SEB request hash | `X-SafeExamBrowser-RequestHash` must match `SHA256(url + seb_config_key)`. Literal `dev-bypass` is **not** accepted. | Fixed (F-001) |
| SEB dev bypass | Allowed only when `PLANNED_EDUCATION_ENV ∈ {development,test}` **and** `ALLOW_DEV_SEB_BYPASS=true`. | Fixed |
| Who may start/submit | Server requires `role == "student"` (teacher preview uses explicit `test_mode` + owner checks). | Fixed (F-015) |
| Time limit | `deadline_at` stored at start (duration × accommodation multiplier). Submit rejects after deadline (UTC-normalized comparisons for SQLite). | Fixed (F-015) |
| Offline package metadata | Start returns authoritative `exam_package` (duration, `require_seb`, timestamps). Client fails closed if package missing/malformed. | **Fixed (F-016)** |
| Offline seal crypto | AES-GCM `{ciphertext, iv, version, aad}` seal; answers encrypted at rest in IndexedDB; session keys wrapped; master stored as non-extractable `CryptoKey` in IDB (structured clone); optional WebAuthn **PRF** wrap (`master-prf-wrap`) for platform-authenticator recovery when the passkey supports PRF. | **Fixed (F-017)** |

---

## 4. Field encryption & privacy

| Control | Behavior | Status |
|---------|----------|--------|
| Fernet field encryption | When `DATABASE_ENCRYPTION=true` + `DB_ENCRYPTION_MASTER_KEY`, sensitive columns encrypt via SQLAlchemy hooks (`pe-db-v1$` envelope). Must differ from JWT secret. | Enabled path fixed; production requires encryption on |
| Direct messages | DM bodies encrypted at rest; API returns plaintext to authorized participants after decrypt. | Working |
| External AI boundary | Text sent toward external AI is scrubbed with Presidio; scrubber **fails closed** (`PrivacyScrubbingError` → HTTP 503) when unavailable. | Fixed (F-013) |
| Bulk OCR roster IDs | Fake roster IDs are resolved or materialized as real student user rows before FK insert. | Hardened 2026-11-06 |

---

## 5. Messaging, alerts, OCR review & portal UX

| Area | Status |
|------|--------|
| Messages / Help placement | Messages beside notifications; Help in hamburger; hidden on login |
| Unread-count route | Static `/messages/direct/unread-count` registered before dynamic partner id (**F-036**) |
| Alerts admin/webhook | List/detail require admin; webhook gated by shared secret (**F-025**) |
| OCR review routes | Deny-by-default ownership/role checks (**F-020**) |
| Parent relationship/progress | Parent role + student target + active links (**F-035**) |
| Notification/email fallbacks | No temp passwords or reset secrets in API bodies / fallback logs (**F-026**) |
| AI grading approve UI | Calls real archive approve endpoint; surfaces errors (**F-030**) |

## 5b. Uploads, SSRF, packages, archive & backups

| Control | Status |
|---------|--------|
| AI image uploads / GET | **Fixed (F-021)**: opaque owned filenames, size/count caps, ownership on download |
| Custom AI / package URLs | **Fixed (F-022)**: `url_safety` allowlist/SSRF blocks + connect-time IP pin / rebind check (`make_pinned_async_client`) |
| Package/curriculum paths | **Fixed (F-023)**: `Path.is_relative_to` containment + size caps |
| Archive at-rest encryption | **Fixed (F-024)**: AES-GCM encrypt on approve; admin `POST /admin/archives/migrate-legacy-encryption` re-encrypts `encryption_algorithm=none` rows |
| Database backups | **Fixed (F-033)**: PEBAK1 AES-GCM via `BACKUP_MASTER_KEY`; no credential fallback dumps |
| Offline sealed sync | **Fixed (F-048)**: `POST/GET /sync/submission` with ownership; teacher LAN URL allowlist validation |

## 5c. Browser / CI hardening

| Control | Status |
|---------|--------|
| CSP script-src | Production omits `'unsafe-inline'`/`'unsafe-eval'` for scripts (Vite hashed modules). |
| CSP style-src | Production `style-src 'self' fonts` (no unsafe-inline on stylesheets); `style-src-attr 'unsafe-inline'` for React inline style attributes; `worker-src 'self' blob:` for MediaPipe. |
| CI Bandit / oxlint | Bandit fails on Medium+ (`-ll`); oxlint `-D correctness -D suspicious`; mypy fail-closed on typed packages. |

---

## 6. Proctoring (honest status)

| Control | Status |
|---------|--------|
| Session lookup by submission | **Fixed (F-018)**: shared `_get_session_and_verify`. |
| Client event pipeline | **Fixed (F-018 remainder)**: allowlisted types/severities, batch/face_count bounds, `event_source=client_telemetry`, violation budget; still telemetry—not sole disciplinary proof. |
| Portal session UI | **Fixed (F-019)**: consent ≠ start; checkboxes only set options; video+stream attach effect; local MediaPipe Face Landmarker (WASM) for face count + iris/head-pose gaze; Shape Detection fallback (face count only); labeled `manual_review` if neither loads; no `Math.random` / no cloud ML. |
| Real local face/gaze ML | **Fixed (F-019)** — `src/lib/localFaceGaze.ts` + `public/ml` assets via `npm run ensure-ml`. |
| Home-exam separation | **Classroom default OFF.** Webcam/mic/gaze require (1) superadmin `home_exam_proctoring_enabled` in deployment config and (2) per-exam `home_exam_enabled`. Labeled **beta** with country-law warning; GDPR consent required. Routes fail closed when gates are off. |

---

## 7. Test database isolation (developers)

`tests/conftest.py` uses a **per-process** SQLite file (`test_plannededucation_<pid>.db`) so parallel pytest processes do not drop each other's schema. Prefer `database.SessionLocal()` with explicit `close()` in tests; never leave `next(get_db())` generators open (SQLite lock source).

---

## 8. Key modules (quick map)

| Module | Responsibility |
|--------|----------------|
| `src/plannededucation/api/seb_security.py` | SEB hash verification / gated bypass |
| `src/plannededucation/api/authorization.py` | Exam author policy |
| `src/plannededucation/api/auth.py` | JWT minting, recovery codes, hashing |
| `src/plannededucation/api/routes_auth.py` | Login, 2FA, resets, `get_current_user` |
| `src/plannededucation/api/routes_exam.py` | Exam CRUD, start/submit, deadlines |
| `src/plannededucation/api/routes_ai.py` | AI/OCR grading with ownership + privacy scrub |
| `src/plannededucation/api/db_encryption.py` | Field encrypt/decrypt hooks |
| `src/plannededucation/api/schema_ensure.py` | Additive schema / `is_superadmin` / refresh_sessions / sealed_sync migrations |
| `src/plannededucation/api/routes_sync.py` | Authenticated sealed offline sync |
| `src/plannededucation/api/backup_service.py` | PEBAK1 encrypted DB backups |
| `src/plannededucation/api/url_safety.py` | SSRF allowlist + DNS pin helpers |
| `web/apps/portal/src/contexts/AuthContext.tsx` | sessionStorage token lifecycle |
| `web/apps/portal/src/lib/teacherSyncUrl.ts` | LAN/allowlist teacher sync URL validation |
