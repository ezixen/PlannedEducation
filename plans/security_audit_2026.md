# Security & Architecture Fix Log
**Date:** 2026-09-21 | **Status:** ✅ All items resolved and smoke-tested

---

## Fixes Applied

### Backend

| File | What was fixed |
|---|---|
| `auth.py` | Replaced predictable dev-fallback secret with `secrets.token_hex(64)` ephemeral key. Token lifetime reduced 120→60 min. |
| `routes_auth.py` | Added `slowapi` rate limiting (20/min on token, 10/min on register). Added password complexity enforcement (8+ chars, upper, lower, digit). Fixed timing oracle with dummy bcrypt verify. Fixed Google OAuth username deduplication with loop. Added `is_active` check on every auth path. Normalised emails to lowercase. |
| `main.py` | Added `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, HSTS in prod). Wired slowapi to app state. Restricted CORS allow_methods and allow_headers to explicit lists. Disabled Swagger UI in production. |
| `database.py` | Removed implicit localhost default in production (crash-loud if not set). Added PG pool tuning (pool_size=10, max_overflow=20, pool_pre_ping=True). |
| `crypto.py` | **New file.** Fernet-based symmetric encryption/decryption for user AI API keys. Uses `AI_KEY_MASTER_SECRET` env var. Dev falls back to ephemeral key. |
| `models.py` | Renamed `ai_api_key` → `ai_api_key_encrypted`. Removed `StudentRecord.parent_id` (use `AccountRelationship`). Added `UniqueConstraint` on `account_relationships` and `exam_submissions`. Added `RelationshipStatus` enum. Added `ondelete` cascade on all FK. Added String length limits. Replaced `datetime.utcnow()` with timezone-aware `utcnow()`. |
| `schemas.py` | Added `Field` length/range constraints everywhere. Added `ExamListResponse` (no questions/answers — safe for public listing). Added `RelationshipRequest` + `RelationshipApproval`. Clarified `QuestionResponse` is teacher-only. |
| `routes_exam.py` | **Critical IDOR fix:** `GET /exams/` now returns `ExamListResponse` (metadata only, no answers). Added `GET /exams/mine` (full data, owner-only). Added `_require_exam_owner` helper used on all mutating operations. Added `DELETE` endpoints. Fixed `start_exam` to exclude `correct_answer`/`rubric` from student response. Fixed submit to use `ExamSubmitRequest` schema. Fixed timezone-aware datetimes. Added `flush()` before `commit()`. Fixed bare `except`. |
| `routes_anonymizer.py` | Fixed IDOR in `post_ai_grades` — verifies exam ownership before grade write. Grades are now actually persisted to DB. Removed dead `if False` blocks. |
| `routes_chat.py` | Fixed crash: removed broken `user.role` checks (role was deleted from model). Access now based on exam ownership OR active submission. Fixed dead-connection cleanup. Added 2 KB message truncation. Added `is_active` check. |
| `routes_parent.py` | Replaced old `StudentRecord`-based lookup with `AccountRelationship` (status=active). Implemented full 3-way handshake endpoints: `request_relationship`, `approve_relationship`, `reject_relationship`. |
| `seb_security.py` | Fixed `exam_id` type bug (`int` → `str`). Added `.lower()` normalisation on SEB header. Dev bypass now requires both `PLANNED_EDUCATION_ENV=development` AND `ALLOW_DEV_SEB_BYPASS=true`. |

### Frontend

| File | What was fixed |
|---|---|
| `AuthContext.tsx` | Extracted `fetchUser` into `refreshUser` (now exposed in context). Typed API calls with generics. Wrapped in `useCallback`. `login()` now throws on failure. |
| `Register.tsx` | Added confirm-password field with live mismatch indicator. Added `PasswordStrength` component. Added `maxLength`, `minLength`, `pattern`, `autoComplete` attrs. Added loading state. |
| `Settings.tsx` | Calls `refreshUser()` after save. Populated from user context via `useEffect`. Added password confirm field. Fixed message to use typed colour states. Shows UUID as read-only. |
| `SecureChat.tsx` | Removed `user.role` bubble colouring (crash bug). Added connection status dot. Added auto-scroll. Added 500-char client message cap. Added JSON.parse try/catch. Typed with `ChatMessage` interface. Fixed `examId` prop type `number→string`. |
| `TakeExam.tsx` | Fixed `answers` type `Record<number,string>` → `Record<string,string>`. Removed `parseInt(qId)` (was corrupting UUIDs). Fixed submit payload to wrap in `{ answers: [...] }` matching `ExamSubmitRequest`. Fixed `SecureChat examId` prop. |
| `TeacherExams.tsx` | Changed `/exams/` → `/exams/mine` so teachers see only their own exams with full data. |

---

## Smoke Test Results (all pass ✅)
1. `PASS` register
2. `PASS` weak password rejected (422)
3. `PASS` login
4. `PASS` /auth/me — no `hashed_password` or `ai_api_key` leaked
5. `PASS` create exam
6. `PASS` exam listing (`/exams/`) returns no question/answer data
7. `PASS` `/exams/mine` returns full data for owner
8. `PASS` IDOR protection — non-owner gets 403 on `/exams/{id}`

---

## Remaining / Future Work

| Item | Priority | Notes |
|---|---|---|
| Redis Pub/Sub for chat | Medium | Required for multi-worker/multi-server WebSocket broadcasting |
| Microsoft Presidio PII scrubber on anonymizer essays | Medium | Strip accidental PII before sending text to external LLMs |
| Refresh tokens (short-lived access + long-lived refresh) | Medium | Currently all tokens live 60 min with no server-side revocation |
| 2FA TOTP endpoints | Low | Column exists in DB, UI placeholder exists in Settings |
| AI key encryption wiring | Low | `crypto.py` is ready; needs to hook into AI integration routes when those are built |
