# PlannedEducation Security & Logic Audit
- Date/time: 2026-11-06 20:45 (Europe/Budapest)
- Auditor: gpt-5.6-luna-max generalPurpose agent
- Repo path / branch note: `D:\Dev\PlannedEducation`, branch `dev`. The working tree already contained portal changes before this audit; this audit did not modify application source, tests, configuration, or deployment files.
- Method summary:
  - Read the repository instructions, active security/messaging plans, backend API modules, models, schemas, crypto/event wiring, portal authentication/layout/exam/messaging/settings/admin paths, installers, deployment helpers, Docker/monitoring configuration, CI workflows, and security-relevant tests.
  - Traced request flows from browser or script entry point through authentication, role/ownership checks, database/file access, outbound service calls, and response rendering.
  - Used OWASP ASVS 5.0 / OWASP Top 10:2025 categories, FERPA/GDPR privacy expectations, secure exam integrity requirements, and the repository's free-tier/no-paid-services policy as review lenses.
  - No tests, deployment, database migration, external service, or destructive command was run for this report. Existing tests were read as evidence of intended behavior and coverage gaps.
  - Secrets, tokens, passwords, key material, local credentials, and environment values are intentionally redacted below.

## Executive summary

The repository contains substantial security work—Argon2id password hashing, explicit CORS lists, Fernet event hooks, ownership checks on several exam paths, encrypted direct-message fields, PII-scrubbing intent, and structured logging—but the controls are not consistently connected to the execution paths. Several high-impact protections are present only as comments, UI assumptions, or unused dependencies.

Finding counts:

- Critical: 4
- High: 30
- Medium: 16
- Low: 1
- Info: 1

Top five risks:

1. Production requests can bypass Safe Exam Browser by sending the literal `dev-bypass` header because the unconditional bypass sits outside the development/test gate.
2. Archive administration and parts of the admin lifecycle do not use the declared admin dependency. Depending on the route, any authenticated user—or an unauthenticated caller for alerts—can read, mutate, delete, or trigger sensitive operations.
3. AI/OCR/submission routes contain ownership gaps. A caller can grade, download, return, or attach data to another user's submission, exposing student answers and educational records.
4. TOTP and WebAuthn are not authentication factors: password login never challenges for TOTP, passkey authentication requires an already-authenticated bearer token, and passkey start challenges are not committed.
5. The offline exam “sealed/encrypted” path is internally inconsistent: answers are stored in plaintext IndexedDB, the seal verification/decryption arguments are wrong, the client receives incomplete exam metadata, and the server does not enforce the time limit.

The fastest safe remediation is to fail closed on exam/security boundaries, centralize RBAC/ownership dependencies, remove browser/localStorage and log secret leakage, repair migrations and encryption coverage, and only then repair the UI/API contract and i18n/documentation drift.

## Findings

### F-001 — Production Safe Exam Browser bypass remains reachable
- Severity / Confidence: **Critical / High**
- Location: `src/plannededucation/api/seb_security.py:24-60`
- Evidence / current behavior:
  - The development bypass correctly checks `PLANNED_EDUCATION_ENV` and `ALLOW_DEV_SEB_BYPASS` at lines 24-30.
  - Later, after reading the request header, the code returns `True` whenever `seb_header.lower() == "dev-bypass"` at lines 52-54, without rechecking the environment.
  - Both `POST /exams/{exam_id}/start` and `POST /exams/{exam_id}/submit` depend on `verify_seb_request` (`routes_exam.py:263-273` and `441-449`).
- Logic tree (related files read):
  - Portal/offline exam start → `apiClient.post('/exams/{id}/start')` → FastAPI dependency `verify_seb_request` → header comparison → exam submission creation.
  - Portal submit → `/exams/{id}/submit` → the same dependency → answer persistence.
  - Installer production mode writes `ALLOW_DEV_SEB_BYPASS=false` (`install.ps1:480-490`, `install.sh:378-386`), but that setting does not protect the unconditional header branch.
- Impact:
  - An attacker who can send a request with `X-SafeExamBrowser-RequestHash: dev-bypass` can start and submit an exam without a valid SEB request hash in production. This directly defeats a stated test-integrity control (OWASP A01/A05; secure-exam integrity).
- Recommended fix (step-by-step, preserve behavior):
  1. Remove the unconditional branch, or make it nested inside the same explicit `environment in {"development", "test"}` and `ALLOW_DEV_SEB_BYPASS == "true"` condition.
  2. Reject the bypass configuration at startup when `PLANNED_EDUCATION_ENV` is `production` or `staging`; do not rely only on operator discipline.
  3. Normalize the expected request URL at the trusted reverse-proxy boundary, and bind the SEB check to the authenticated student/submission as well as the exam.
  4. Keep the current no-SEB-config `409` and invalid-hash `403` user journeys.
- Verification:
  - Add tests proving `dev-bypass` is accepted only in development/test with the flag enabled.
  - In production-mode tests, assert both start and submit return `403` for the header and succeed only with the computed hash.
  - Test reverse-proxy URL normalization and an already-completed submission.

### F-002 — Archive “admin-only” routes never apply `require_admin`
- Severity / Confidence: **Critical / High**
- Location: `src/plannededucation/api/routes_archive.py:30-39`, `112-378`, `531-592`
- Evidence / current behavior:
  - `require_admin` is defined at lines 30-39 but no route in this module uses `Depends(require_admin)`.
  - Statistics, archive listing, job creation/listing/details/start, restore, and delete routes depend only on `get_current_user`.
  - The `/archive/admin/create`, `/archive/admin/list`, and `/archive/admin/{user_id}` routes likewise depend only on `get_current_user`.
- Logic tree (related files read):
  - Authenticated bearer → `get_current_user` → archive route → database/file operation; the intended admin gate is dead code.
  - `AdminDashboard.tsx:160-250` calls these endpoints for archive management, while `routes_admin.py` uses a separate, correctly wired `require_admin`; the two administrative surfaces therefore have different security behavior.
- Impact:
  - Any active account can enumerate archived educational records, create/start jobs over completed submissions, restore records, delete archive files/rows, list admins, promote another account to admin, or revoke another admin (subject to the individual route's limited checks). This is unauthorized disclosure, modification, and destruction of FERPA-sensitive data.
- Recommended fix (step-by-step, preserve behavior):
  1. Add `current_user: models.User = Depends(require_admin)` to every route documented as admin-only.
  2. Replace the local helper with one shared dependency from an authorization module so archive/admin routes cannot silently drift.
  3. Add explicit ownership/tenant checks for job filters and archive records even for non-superadmin admins if the product later supports scoped schools.
  4. Preserve teacher-only archive download by using a separate `require_archive_reader` policy that permits the owning approved teacher or an admin, rather than weakening the admin routes.
- Verification:
  - Add negative tests using student, parent, pending teacher, and ordinary teacher tokens for every archive admin endpoint.
  - Test that an admin can perform the existing dashboard journey and that a teacher can still download only their own archive.
  - Test deletion/restore authorization and database/file consistency after a failed job.

### F-003 — Admin/superadmin separation is not represented or enforced
- Severity / Confidence: **Critical / High**
- Location: `src/plannededucation/api/models.py:48-56`, `src/plannededucation/api/routes_admin.py:35-59`, `282-410`, `src/plannededucation/api/routes_auth.py:872-939`, `src/plannededucation/api/routes_archive.py:531-592`
- Evidence / current behavior:
  - The model has `is_admin` and a string `role`; there is no distinct `is_superadmin` or immutable administrator level.
  - `routes_admin.require_admin` treats every `is_admin=True` account as a “superadmin”.
  - `/admin/users` allows any such account to create a role=`admin` account (`routes_admin.py:282-348`).
  - `/admin/users/superadmin` also checks only `current_user.is_admin` and accepts the broad `AdminCreateUserRequest.role` field (`350-410`).
  - The quick-reset condition `if target_user.is_admin and not current_user.is_admin` can never protect an admin target after the outer `if not current_user.is_admin` check (`routes_auth.py:872-900`).
  - The archive admin create/revoke endpoints are even less restrictive (`routes_archive.py:531-592`).
- Logic tree (related files read):
  - Admin login → JWT subject → `get_current_user` → boolean `is_admin` → all admin/superadmin operations; no principal-level distinction exists.
  - The frontend labels the account “superadmin” in several places, but server authorization is the actual security boundary.
- Impact:
  - Any administrator can create or reset another administrator, and archive-route authorization can let any authenticated user grant/revoke administrative power. This violates the repository policy that only superadmins may create admins/superadmins and creates direct privilege escalation.
- Recommended fix (step-by-step, preserve behavior):
  1. Add an explicit, migrated `is_superadmin`/`admin_level` invariant, or a documented immutable bootstrap principal if the intended model is different.
  2. Centralize `require_admin` and `require_superadmin`; never infer superadmin from `is_admin`.
  3. Validate target role and username/email before persistence; only superadmins may create admin-level accounts.
  4. Require superadmin for administrator password resets, deactivation, deletion, promotion, demotion, backup-code generation policy changes, and support-email changes as specified.
  5. Invalidate all sessions after role changes and prevent self-demotion/self-deletion.
- Verification:
  - Matrix-test admin vs superadmin for create-admin, create-superadmin, reset, activate/deactivate, delete, revoke, archive, and support-email operations.
  - Assert ordinary teachers/students cannot reach any administrative route even if they manipulate the role-bearing client state.
  - Add a migration test from a pre-level schema with an explicit documented mapping.

### F-004 — AI grading and submission endpoints have cross-user IDORs
- Severity / Confidence: **Critical / High**
- Location: `src/plannededucation/api/routes_ai.py:476-630`, `1235-1348`
- Evidence / current behavior:
  - `/ai/grade` accepts a `submission_id` but never loads or verifies it; any authenticated user can invoke the grading provider with arbitrary question/rubric/response data.
  - `/ai/grade/{submission_id}` loads a submission by ID and writes suggested grades without checking the exam owner, student owner, teacher role, or OCR review state (`1235-1285`).
  - `/ai/submissions/{submission_id}/download` returns another user's student name, exam title, feedback, and score to any authenticated caller (`1292-1328`).
  - `/ai/submissions/{submission_id}/return` performs no owner or role check (`1330-1348`).
  - Bulk upload accepts an arbitrary `exam_id` without checking `exam.teacher_id == current_user.id` (`routes_ai.py:1015-1023`) and allows client-provided roster IDs to become submission owners (`1075-1085`, `1135-1144`).
- Logic tree (related files read):
  - Browser AI grading page → `/ai/submissions`, `/ai/grade/{id}`, download/return → database submission lookup → response or mutation.
  - Teacher archive routes correctly join submissions to owned exams (`routes_archive.py:750-830`), but the separate AI routes bypass that policy.
- Impact:
  - Students or other teachers can alter grading feedback, download educational records, mark submissions returned, or attach uploaded answers to another teacher's exam/student. This is FERPA disclosure and grade-integrity failure.
- Recommended fix (step-by-step, preserve behavior):
  1. Create a shared `_get_submission_for_teacher` dependency that joins `Exam` and requires current user to be the owner or an explicitly authorized share.
  2. Require approved teacher/admin role for grading mutations and owner/student role for self-read only.
  3. For direct AI grading, derive question/rubric/response from the verified submission instead of trusting request copies; reject mismatched `submission_id`.
  4. For bulk upload, verify the target exam owner and validate every roster ID as an active student in an authorized class; never accept arbitrary client identity mappings.
  5. Keep teacher review/staging and student self-review journeys intact.
- Verification:
  - Use two teachers, two students, an admin, and a parent; assert cross-owner GET/download/mutate/return all fail.
  - Assert bulk uploads reject a foreign exam and a roster ID outside the teacher's scope.
  - Test OCR-review-pending submissions cannot be graded before teacher approval.

### F-005 — Refresh tokens are accepted as bearer access tokens
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_auth.py:244-261`, `src/plannededucation/api/routes_chat.py:184-197`
- Evidence / current behavior:
  - `get_current_user` decodes the JWT with the correct algorithm and checks `sub`, but never requires `payload["type"] == "access"`.
  - The WebSocket helper repeats the same subject-only validation.
  - `auth.create_refresh_token` creates tokens valid for 30 days or 365 days (`src/plannededucation/api/auth.py:61-95`), while access tokens are intended to be 60 minutes.
- Logic tree (related files read):
  - Password login → access/refresh pair → browser or attacker supplies refresh token in `Authorization: Bearer` → `get_current_user` accepts it → all protected REST/WebSocket routes.
- Impact:
  - A stolen refresh token becomes a long-lived full API bearer token, bypassing the intended short-lived access-token boundary and increasing replay impact.
- Recommended fix (step-by-step, preserve behavior):
  1. Require `type == "access"` in `get_current_user` and the WebSocket helper.
  2. Keep refresh tokens accepted only by `/auth/refresh`; centralize JWT verification so REST and WebSocket cannot diverge.
  3. Add issuer/audience and a server-side refresh-session identifier if practical; continue rotating refresh tokens.
- Verification:
  - Generate both token types and assert every protected HTTP/WebSocket route rejects the refresh token with 401/1008.
  - Assert `/auth/refresh` rejects an access token.

### F-006 — TOTP and WebAuthn do not protect login
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_auth.py:397-505`, `1112-1230`, `1324-1530`
- Evidence / current behavior:
  - Password login verifies only the password, lockout, and `is_active`; it never checks `user.totp_enabled` or a second-factor challenge.
  - WebAuthn authentication start/finish both require `get_current_user`, so a caller must already hold a valid bearer token to “authenticate”.
  - Registration/authentication start assigns `webauthn_challenge` and expiry but does not commit them; the dependency session is closed after the request, so the next request can see no challenge.
  - Recovery-code regeneration explicitly comments that TOTP confirmation is required but does not request or verify a code (`1212-1230`).
- Logic tree (related files read):
  - Settings → `/auth/2fa/setup`/confirm → `totp_enabled=True` → normal `/auth/token` password login → no challenge.
  - Settings → passkey registration start → uncommitted user challenge → finish in a new request → “no active challenge”; passkey authentication is never a login route.
- Impact:
  - Enabling 2FA provides no login protection; a password compromise remains a full account compromise. A stolen authenticated bearer can also regenerate recovery codes or delete passkeys without an additional factor.
- Recommended fix (step-by-step, preserve behavior):
  1. Add a two-step login state: password verification returns a short-lived, single-use 2FA transaction, not an access token, when TOTP/passkey is enabled.
  2. Add unauthenticated WebAuthn authentication start/finish bound to a login transaction and issue tokens only after verified user presence/verification.
  3. Commit challenge state transactionally, bind it to a session/device and expiry, and prevent concurrent challenge overwrite.
  4. Require TOTP/recovery confirmation for recovery-code regeneration, passkey deletion, and disabling TOTP.
  5. Preserve password-only accounts and explicit recovery flows for users without 2FA.
- Verification:
  - Test password login for TOTP-enabled users returns a pending challenge and protected routes reject the intermediate token.
  - Test valid/invalid/replayed/expired TOTP and WebAuthn assertions.
  - Test passkey registration start/finish across separate requests and concurrent browser sessions.

### F-007 — Internal password-reset requests are unauthenticated and replayable
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_notifications.py:124-204`, `210-304`
- Evidence / current behavior:
  - `request_password_reset_internal` has no `current_user` dependency, CAPTCHA, or rate limiter.
  - An anonymous caller can choose any identifier and target role; the endpoint sends notifications to all active teachers, all related parents (including relationships without `active` filtering), or all admins.
  - Approval accepts a custom password without calling `_validate_password` (`258-267`), does not verify an active parent relationship (`250-257` only checks any row), and does not consume/invalidate the notification action payload. The same notification can be approved repeatedly.
  - Approval does not clear `password_reset_otp`, `reset_token`, or `force_password_reset` state.
- Logic tree (related files read):
  - Login forgot-password UI → unauthenticated `/notifications/request-password-reset` → notifications containing requester PII → supervisor approval → password hash + temporary password notification/email.
- Impact:
  - Attackers can spam supervisors, disclose requester PII to unrelated recipients, and repeatedly reset a victim's password. A teacher/parent relationship in a non-active state can be abused to approve a reset.
- Recommended fix (step-by-step, preserve behavior):
  1. Keep a generic unauthenticated request only if required, but enforce a strict IP/account rate limit, CAPTCHA, generic recipient routing, and no user-specific data in the response.
  2. Resolve recipients only through active, role-valid relationships and approved teacher ownership; do not broadcast every teacher.
  3. Make the notification action single-use with a consumed timestamp/nonce and a compare-and-set transaction.
  4. Apply the same password policy as normal login and clear all reset/refresh/session state on success.
  5. Require a force-change flag for generated temporary passwords and never place them in a reusable notification.
- Verification:
  - Anonymous spam, nonexistent identifiers, pending/rejected relationships, replayed notification IDs, weak custom passwords, and cross-role approvals must all fail or remain generic.
  - Test that successful approval invalidates all previous reset and refresh credentials.

### F-008 — Password-reset links expose bearer tokens through URL and trust unvalidated origins
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_auth.py:603-699`, `src/plannededucation/api/email_service.py:155-195`
- Evidence / current behavior:
  - A reset token is stored directly in `password_reset_otp` and compared directly (`routes_auth.py:620-665`).
  - The reset link places `token` and email in the query string (`636`).
  - The base URL is taken from an unvalidated `Origin` or `Referer` header before falling back to `FRONTEND_URL` (`627-636`).
  - The reset page reads the token from `window.location` (`ResetPassword.tsx:14-22`), leaving it exposed to browser history, extensions, analytics/referrer mistakes, and copied URLs.
  - Password reset completion issues an access token but does not clear an existing refresh-token hash (`routes_auth.py:687-699`).
- Logic tree (related files read):
  - Public request → request headers → generated link → email service HTML/text → browser query string → confirm endpoint → new password/access token.
- Impact:
  - A leaked URL or referrer can reset an account. An attacker can also continue using a previously issued refresh token after a successful password reset.
- Recommended fix (step-by-step, preserve behavior):
  1. Use a single-use random reset token stored only as a keyed hash (or encrypted field), with a short expiry and atomic consume.
  2. Build links only from a configured, validated HTTPS frontend origin; ignore arbitrary `Origin`/`Referer` for password-reset links.
  3. Prefer a fragment or POST handoff that removes the token from browser history immediately; set a restrictive referrer policy on the reset page.
  4. Rotate/invalidate all refresh sessions and other reset mechanisms when the password changes.
- Verification:
  - Send requests with hostile origins/referers and assert the email link uses the configured origin.
  - Assert a consumed token, expired token, and pre-reset refresh token are all rejected.

### F-009 — Recovery codes have low entropy and fast unsalted hashes
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/auth.py:50-58`, `src/plannededucation/api/routes_auth.py:320-326`, `1112-1147`, `1212-1230`, `src/plannededucation/api/routes_admin.py:557-575`
- Evidence / current behavior:
  - The default eight-character recovery code is generated with `token_hex(length // 2)`, giving roughly 32 bits of entropy.
  - Values are stored as unsalted SHA-256 hashes and used for password reset, TOTP disable, and administrator recovery.
- Logic tree (related files read):
  - Registration/2FA/admin backup-code generation → random code → SHA-256 string in encrypted/plain column → unauthenticated recovery/password-reset comparison.
- Impact:
  - A database reader can brute-force the small code space rapidly. A recovered code can reset a password or disable 2FA, making this an account takeover path after database exposure.
- Recommended fix (step-by-step, preserve behavior):
  1. Generate at least 128 bits from a CSPRNG and display a human-friendly, sufficiently long representation.
  2. Store an Argon2id hash with a per-code salt, or an HMAC keyed with a separate server secret if high-volume comparison is required.
  3. Consume codes atomically and rate-limit recovery attempts by account and IP.
  4. Keep the current one-time display/copy/print journey.
- Verification:
  - Assert code length/entropy policy, single-use behavior under concurrent requests, and resistance to offline test vectors.

### F-010 — Student answer records are not field-encrypted
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/models.py:288-322`, `880-907`
- Evidence / current behavior:
  - `Answer.student_response`, `generated_question_text`, and `generated_options_json` contain student answers and individualized exam data.
  - `register_encrypted_model(ExamSubmission, [])` registers an empty field set; `Answer` is not registered at all.
  - The model comments describe submission encryption, but the actual answer rows remain plaintext whenever database field encryption is enabled.
- Logic tree (related files read):
  - Student submit → `routes_exam.submit_exam` updates `Answer.student_response` (`routes_exam.py:441-486`) → SQLAlchemy flush → no encryption listener for `Answer` → database/backup/archive inputs.
- Impact:
  - A database/backup reader can obtain student exam answers even when `DATABASE_ENCRYPTION=true`. This contradicts FERPA/privacy claims and undermines secure exam storage.
- Recommended fix (step-by-step, preserve behavior):
  1. Register `Answer` with the sensitive fields and test insert/update/load/refresh/flush paths.
  2. Keep queryable identifiers (`submission_id`, `question_id`) plaintext; encrypt only answer/free-text fields.
  3. Ensure archive/export code decrypts only inside authorized teacher/student services and never serializes ciphertext to an API response.
  4. Add a versioned migration/re-encryption process for existing rows.
- Verification:
  - Inspect raw database values after submitting plaintext and assert they are Fernet tokens.
  - Assert authorized API responses remain plaintext while unauthorized/database-only reads do not.

### F-011 — Database encryption is optional and its legacy fallback can fail open
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/db_encryption.py:28-60`, `78-110`, `140-220`, `src/plannededucation/api/database.py:35-59`
- Evidence / current behavior:
  - Field encryption defaults to disabled when `DATABASE_ENCRYPTION` is absent.
  - `encrypt_field` skips any plaintext beginning with `gAAAA`; a legitimate message beginning with that prefix is stored unchanged.
  - `decrypt_field` treats a Fernet token that fails authentication as legacy plaintext and returns it unchanged.
  - SQLite “SQLCipher” support adds a `key` connect argument while the SQLAlchemy URL still uses the normal SQLite dialect; the code does not prove that the SQLCipher DBAPI is actually selected.
- Logic tree (related files read):
  - Environment → module import → one global Fernet → SQLAlchemy model listeners → raw DB load/save.
  - A rotated/wrong key or malformed ciphertext is converted into application-visible plaintext rather than a hard failure/quarantine.
- Impact:
  - Production can silently store sensitive records unencrypted; wrong-key ciphertext can be returned or re-encrypted as if it were plaintext; prefix collisions bypass encryption. This risks data disclosure and integrity loss during key rotation.
- Recommended fix (step-by-step, preserve behavior):
  1. Fail closed in production when sensitive field encryption is not configured; allow an explicit test-only plaintext mode.
  2. Replace prefix heuristics with a versioned envelope/column marker and authenticated decrypt result; distinguish legacy plaintext during a controlled migration only.
  3. On invalid ciphertext, raise a controlled storage error and alert—never return it as plaintext.
  4. Implement SQLCipher through a verified SQLAlchemy dialect/driver or document that SQLite file encryption is not enabled; do not pass unsupported connect arguments.
  5. Maintain separate JWT, AI, DB, and archive keys and document rotation.
- Verification:
  - Test values beginning with `gAAAA`, wrong keys, rotated keys, legacy rows, refresh/load, and production startup without a DB key.

### F-012 — Additive schema assurance does not cover the model/security drift
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/schema_ensure.py:17-60`, `src/plannededucation/api/main.py:185-194`, `install.ps1:605-610`, `install.sh:490-497`
- Evidence / current behavior:
  - `ensure_schema` only adds five columns to `users`; it does not migrate renamed `ai_api_key` fields, removed `StudentRecord.parent_id`, new encrypted columns, indexes, constraints, or other existing-table changes.
  - `create_all` does not alter existing tables.
  - The installer and application both call only `create_all` plus this narrow helper.
- Logic tree (related files read):
  - Existing deployment DB → startup/install → `create_all` (tables only) → `ensure_schema` (five user columns) → current ORM models/query paths.
- Impact:
  - Upgrading a real deployment can fail at startup, retain obsolete plaintext columns/data, miss unique constraints, or run with a schema that does not enforce current security invariants. The “upgrade-safe” claim is not reliable.
- Recommended fix (step-by-step, preserve behavior):
  1. Adopt versioned, transactional migrations (Alembic or a carefully controlled equivalent) for every model change.
  2. Add explicit preflight checks and stop startup when a required migration fails; do not log and continue.
  3. Include data transforms for AI-key renames, parent relationships, encrypted-field backfill, indexes, and constraints.
  4. Test SQLite and PostgreSQL upgrade fixtures from each supported prior schema.
- Verification:
  - Run migrations against a copy of each historical schema, inspect columns/constraints/indexes, and assert rollback/backup behavior.

### F-013 — PII anonymization fails open before external AI use
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_anonymizer.py:14-80`, `src/plannededucation/api/routes_ai.py:520-550`, `1035-1090`
- Evidence / current behavior:
  - If Presidio is unavailable, `scrub_pii` returns the original text (`routes_anonymizer.py:69-75`).
  - If analysis throws, the exception handler explicitly returns the original text (`76-80`).
  - Direct `/ai/grade` sends request text to the configured provider without invoking `scrub_pii`.
  - Bulk OCR stores `recognized_text` and only sends a best-effort scrubbed copy to the staged workflow; the fallback also fabricates content when OCR is unavailable.
- Logic tree (related files read):
  - Student answer/OCR → `scrub_pii` → external provider or staged feedback. Failure returns the original PII-bearing value.
  - The FAQ/UI advertises a zero-PII guarantee, but the direct AI route and fail-open helper do not enforce it.
- Impact:
  - Names, emails, phone numbers, and educational-record text can leave the school server. This is a direct FERPA/GDPR violation and contradicts the stated privacy boundary.
- Recommended fix (step-by-step, preserve behavior):
  1. Fail closed for external providers when Presidio is unavailable or analysis fails; offer an explicitly local/manual grading path.
  2. Make every external-AI entry point call one privacy gateway, including direct grading/content paths where student data may be included.
  3. Log only a redacted failure reason and a request identifier, never original text.
  4. Treat OCR fallback as “unavailable/needs review”, not a fabricated high-confidence answer.
- Verification:
  - Disable Presidio and assert external calls are not made.
  - Inject representative PII, analyzer exceptions, and OCR failures; assert no raw value appears in provider payloads, logs, or staged outbound data.

### F-014 — Any authenticated user can create/manage exams through the normal and package paths
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_exam.py:27-40`, `106-116`, `176-210`, `src/plannededucation/api/routes_packages.py:443-540`, `790-905`
- Evidence / current behavior:
  - `create_exam` calls `_require_approved_teacher`, but that helper only rejects a pending `role == "teacher"`; it does not require teacher/admin role. A student can create an exam and becomes its `teacher_id`.
  - The same owner helper then lets that student add/delete questions.
  - Package import, curriculum import, and repository import create exams for `current_user.id` without an approved teacher/admin check.
- Logic tree (related files read):
  - Student bearer → `POST /exams/` or package import → exam row with student owner → owner-only question routes and full `/exams/mine` answer response.
- Impact:
  - Students can create answer-bearing exams, access owner APIs, poll/monitor their own submissions, and bypass the intended teacher approval boundary. This also makes downstream “owner” checks trust an invalid principal.
- Recommended fix (step-by-step, preserve behavior):
  1. Make a single `require_exam_author` dependency require approved teacher, aide permission where explicitly intended, or admin.
  2. Apply it to direct create, AI create, package/curriculum/repository imports, question mutations, and export.
  3. Keep student exam-taking on separate routes; do not infer authority from `exam.teacher_id` alone.
  4. Add ownership tests for students, parents, pending teachers, aides, and admins.
- Verification:
  - Attempt each create/import/question/export path with a student and pending teacher token; assert 403.
  - Confirm approved teachers/admins retain their existing workflows.

### F-015 — Exam duration and student-role constraints are client-enforced only
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_exam.py:263-437`, `441-486`
- Evidence / current behavior:
  - `start_exam` allows any authenticated user to create a submission and does not require `current_user.role == "student"` or an authorized exam assignment.
  - `submit_exam` checks only that a submission exists and is incomplete; it never compares `completed_at` with `started_at + exam.duration_minutes`.
  - The portal timer (`useOfflineExam.ts:210-260`) is the only visible duration control.
- Logic tree (related files read):
  - Bearer → start → `ExamSubmission.started_at` → arbitrary client pause/clock/late request → submit → answer persistence with no server deadline.
- Impact:
  - A student can submit after the time limit by modifying the client, pausing the page, or making a late HTTP request. Teachers/admins can also create student submissions, and any authenticated role can start an exam.
- Recommended fix (step-by-step, preserve behavior):
  1. Require an approved student/student-role or an explicit teacher preview permission; isolate `test_mode` behind an owner/teacher policy.
  2. Store the authoritative deadline at start, including approved accommodation multiplier, and enforce it server-side on submit.
  3. Define a narrow grace/clock-skew policy; reject late writes while preserving already-completed submissions.
  4. Keep the client timer for UX only and display server status/errors inline.
- Verification:
  - Submit before, exactly at, and after the deadline; alter client clocks and query flags.
  - Assert teacher preview works only for an owner and cannot create a student record.

### F-016 — Offline exam initialization loses server metadata and disables protections
- Severity / Confidence: **High / High**
- Location: `web/apps/portal/src/hooks/useOfflineExam.ts:78-150`, `web/apps/portal/src/services/offlineExam.ts:439-447`, `src/plannededucation/api/routes_exam.py:263-330`
- Evidence / current behavior:
  - The backend start response is `{submission_id, questions}`; it does not return `exam_package`.
  - The hook therefore enters the fallback package at lines 100-122 with a hardcoded title, 60-minute duration, and `require_seb: false`.
  - The backend's authoritative exam duration, SEB requirement, settings, and server timestamps are discarded.
- Logic tree (related files read):
  - `TakeExam` → `useOfflineExam.initializeExam` → `/exams/{id}/start` → missing `exam_package` → client-generated fallback → timer/SEB behavior.
- Impact:
  - Exams can display/use the wrong duration and silently skip client SEB monitoring. If the server remains the only authority, the UI still misleads students and teachers; if offline submission is accepted, integrity fails.
- Recommended fix (step-by-step, preserve behavior):
  1. Define one versioned `ExamStartResponse` and return the real safe package, duration, settings, server start/deadline, and submission ID.
  2. Validate the response schema client-side; never silently manufacture security settings on a missing field.
  3. Cache packages per authenticated student/exam/attempt, with an expiry and server revalidation.
  4. Preserve teacher test previews as a separate response type.
- Verification:
  - Test an exam with non-default duration, SEB required, time multiplier, and custom settings; assert the client reflects all values.
  - Assert malformed/missing package metadata blocks the exam rather than falling back insecurely.

### F-017 — Offline sealing/verification is broken and runtime answers are plaintext
- Severity / Confidence: **High / High**
- Status: **Fixed (2026-11-06)** — `offlineExamCrypto.ts` + `offlineExam.ts`: real AES-GCM `{ciphertext,iv,version,aad}` envelope + per-answer payloads; recursive canonical JSON `contentHash`; verify/decrypt fail closed on missing ciphertext; answers encrypted at rest in IndexedDB; session keys wrapped by master (non-extractable in memory). Residual: device-local master wrapping material still in IDB (no platform keystore / server-bound recovery yet). Vitest: `npm test` in `web/apps/portal`.
- Location: `web/apps/portal/src/services/offlineExam.ts`, `web/apps/portal/src/services/offlineExamCrypto.ts`
- Evidence / current behavior (pre-fix):
  - `OfflineExamState.answers` is plaintext and is written directly to IndexedDB (`saveOfflineExamState`).
  - Generated AES keys are exported as raw, extractable strings into the same IndexedDB database (`getMasterKey`/`getSessionKey`); the master key is not used to wrap the session key.
  - `sealExamSubmission` discards the ciphertext for the full submission and stores only the IV as `encryption.iv` (`960-990`).
  - `verifySealedSubmission` and `decryptSealedSubmission` pass IV values as ciphertext and IV (`1014-1019`, `1050-1070`), so successful verification/decryption cannot work.
- Logic tree (related files read):
  - Exam answers → IndexedDB plaintext state → seal on submit → malformed seal → local/teacher/server sync queue.
- Impact:
  - Any same-profile script/extension or local profile reader can obtain answers; the claimed tamper-evident three-way seal cannot be verified or decrypted. Offline grading/sync may fail or silently fall back to raw submission.
- Recommended fix (step-by-step, preserve behavior):
  1. Design a real key hierarchy: user/session secret from an authenticated server or platform keystore, non-extractable Web Crypto keys, and a documented offline recovery policy.
  2. Encrypt persisted state—not only the final seal—and avoid storing the wrapping key beside ciphertext.
  3. Store `{ciphertext, iv, version, aad}` for every encrypted payload and pass the correct ciphertext/IV pair to decrypt.
  4. Hash exactly the canonical plaintext structure actually sealed; use a recursive canonical serializer.
  5. Fail closed when verification fails; never submit a “sealed” object with missing ciphertext.
- Verification:
  - Round-trip encrypt/decrypt and tamper tests for names, answers, metadata, and nested JSON.
  - Inspect IndexedDB after typing an answer and assert no plaintext response/key is present.
  - Test offline queue/restart/browser reload and a wrong-key verification failure.

### F-018 — Proctoring trusts untrusted clients and has an access bypass
- Severity / Confidence: **High / High**
- Status: **done-tested-working** (2026-11-06)
- Location: `src/plannededucation/api/routes_proctoring.py:390-410`, `140-177`, `414-491`
- Evidence / current behavior (pre-fix):
  - `get_session_by_submission` only rejects mismatched `student` and `teacher` roles; parents, aides, and other non-student/non-teacher roles bypass the check and receive any session by ID.
  - `_get_session_and_verify` handles parent relationships for other routes, but this endpoint does not call it.
  - Authenticated students can submit arbitrary event type/severity/data, including `violation`, face counts, screenshot/audio references, and batch volumes; server increments violation counters based solely on request fields.
- Fix applied:
  1. `get_session_by_submission` delegates to `_get_session_and_verify` (student/teacher/parent/admin; deny-by-default).
  2. Event types/severities validated; payloads bounded (`MAX_BATCH_EVENTS=50`, `MAX_EVENT_DATA_BYTES=4096`, `MAX_FACE_COUNT=10`); post-ended sessions rejected.
  3. Client events stamped `event_source=client_telemetry`; severity clamped per type; `violation_count` only increments for allowlisted types within a per-request budget.
- Verification:
  - `tests/test_routes_proctoring.py` covers unknown types, huge face counts, oversized batches, telemetry stamp, severity clamp, violation budget, post-ended sessions.

### F-019 — Proctoring UI can never enter the intended real monitoring workflow
- Severity / Confidence: **High / High**
- Status: **done-tested-working** (2026-11-06) — state machine + labeled manual-review mode; real ML face detector still deferred
- Location: `web/apps/portal/src/components/ProctoringSession.tsx`, `web/apps/portal/src/hooks/useProctoring.ts`
- Evidence / current behavior (pre-fix):
  - `onConsentGiven` sets `sessionStarted(true)` immediately after consent, before the user clicks “Start Session”.
  - Checkbox `onChange` handlers call `startSession` directly instead of only changing option state.
  - `startEventRecording` checks stale `state.cameraEnabled` immediately after an async `setState`.
  - The `<video>` element is rendered only when `proctoring.videoRef.current` is already non-null (circular).
  - Face detection is explicitly simulated with `Math.random()`, not actual face/gaze detection.
- Fix applied:
  1. `sessionStarted` set only in `onSessionStarted` after backend create; consent alone does not flip it.
  2. Checkboxes update local option state only; Start Session button calls `startSession`.
  3. Video always rendered when camera selected; stream attached in hook `useEffect`.
  4. `startEventRecording(sessionId, options)` takes explicit options (no stale state).
  5. Removed `Math.random` face/gaze simulation; labeled unavailable/manual-review mode; no fake face/gaze violation evidence.
- Residual:
  - Real local face/gaze detector integration remains future work; UI/API now honestly advertise manual-review mode.
- Verification:
  - Backend event validation covered by `tests/test_routes_proctoring.py`; UI state machine verified by code review of consent → options → start → stream attach path.

### F-020 — OCR review routes permit unauthorized read and mutation
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_ocr_review.py:45-90`, `96-110`, `116-249`
- Evidence / current behavior:
  - List filtering treats any unrecognized role as a student lookup, but `get_ocr_review`, create, update, approve, and delete only restrict a caller when `current_user.role == "teacher"` and the exam owner differs.
  - A parent, aide, or arbitrary non-teacher can therefore access/update/delete a review by ID.
  - Create accepts caller-supplied `submission_id`, `exam_id`, and `student_id` without verifying the submission belongs to that exam/student or that the caller owns the exam.
- Logic tree (related files read):
  - Authenticated caller → review ID/body → SQLAlchemy row → original/corrected OCR text or state mutation.
  - Encrypted `OCRReview` fields protect storage but do not replace row-level authorization.
- Impact:
  - Student handwritten answers, OCR text, review notes, and PII can be disclosed or altered by unrelated users; an attacker can attach forged OCR to another student's submission.
- Recommended fix (step-by-step, preserve behavior):
  1. Centralize `require_ocr_teacher_owner`/`require_ocr_student_self`/`require_admin`.
  2. Permit students only to view their own approved result if that is an intended journey; deny parents unless an active relationship is verified.
  3. Derive exam/student from the verified submission instead of trusting three independent IDs.
  4. Enforce status transitions and prevent edits after AI/teacher approval without an auditable reopen action.
- Verification:
  - Negative matrix for every route and role, including forged IDs in create payloads.
  - Assert encrypted response text is returned only to authorized principals.

### F-021 — AI upload paths allow traversal and image/submission disclosure
- Status: **FIXED** (2026-11-06) — opaque UUID names under per-teacher dirs; size/count caps; image GET ownership via OCRReview/exam owner/admin. Covered by `tests/test_security_f021_024.py`.
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_ai.py:889-950`, `960-975`, `1045-1058`
- Evidence / current behavior:
  - Upload paths concatenate `file.filename` into a filesystem path (`UPLOAD_DIR / f"{current_user.id}_{file.filename}"`) without `Path.name`/containment validation.
  - Bulk upload repeats this with a UUID prefix but still includes the unsanitized filename.
  - Image download uses only `Path(image_filename).name` for traversal protection but does not check ownership, exam ownership, or role; any authenticated user who learns/guesses a filename can read it.
  - Files are read fully with no size/dimension/count cap.
- Logic tree (related files read):
  - Multipart upload → filename-derived path → disk write → staged feedback contains public-looking `image_url` → any authenticated GET returns file.
- Impact:
  - An authenticated user can attempt arbitrary relative file writes within reachable parent paths, overwrite predictable files, exhaust disk/memory, or retrieve another classroom's handwritten submissions.
- Recommended fix (step-by-step, preserve behavior):
  1. Generate server-side opaque filenames; ignore client path components and store the original name only as metadata.
  2. Resolve and enforce containment under a per-teacher directory; use restrictive file permissions.
  3. Authorize image/download by verified submission/exam owner and return a short-lived authenticated response.
  4. Enforce request body, file count, file size, image dimensions, and processing time limits.
- Verification:
  - Test filenames containing `../`, absolute paths, Unicode separators, symlinks, oversized files, and foreign image IDs.
  - Assert files cannot be created outside the per-teacher upload root.

### F-022 — User-controlled AI endpoints and package sources create SSRF and key exfiltration
- Status: **FIXED** (2026-11-06) — `url_safety.py` allowlist/blocklist; schema+route fail-closed; Gemini key in header; package sync re-validates URL. Residual: DNS rebinding / redirect IP pinning not fully implemented (follow_redirects=False on sync). Covered by `tests/test_security_f021_024.py`.
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/schemas.py:350-359`, `src/plannededucation/api/ai_providers.py:60-85`, `228-250`, `src/plannededucation/api/routes_packages.py:912-1087`
- Evidence / current behavior:
  - Users can store arbitrary `ai_base_url`; the OpenAI-compatible provider posts to it with the user's bearer API key.
  - Gemini places the API key in a URL query parameter (`ai_providers.py:60-68`), increasing exposure in proxy/access logs.
  - Admin-configured package sources accept arbitrary URLs and `sync_package_source` performs server-side HTTP GETs, optionally attaching the stored source API key.
  - `PackageSource.api_key` is plaintext in the database model (`models.py:600-621`).
- Logic tree (related files read):
  - Settings/source form → URL/API key persisted → backend outbound HTTP request → response/package import; no scheme/host allowlist or response-size policy.
- Impact:
  - A compromised admin or malicious source configuration can probe internal services/cloud metadata or exfiltrate source/API credentials to an attacker-controlled endpoint. Custom AI URLs can also receive student prompts.
- Recommended fix (step-by-step, preserve behavior):
  1. Separate local Ollama from remote providers and allowlist exact schemes/hosts; block loopback, link-local, private, metadata, and Unix/socket targets unless explicitly enabled by deployment policy.
  2. Never send an API key to a URL unless it was validated and explicitly trusted; prefer provider-specific secret handling.
  3. Store source keys encrypted with a dedicated key and redact them from all errors/logs.
  4. Add DNS re-resolution/IP pinning, redirect restrictions, response-size/content-type/time limits, and outbound network egress controls.
- Verification:
  - SSRF test matrix for loopback/private/metadata/redirect/IPv6 forms and malicious DNS.
  - Assert API keys are absent from URLs, logs, error payloads, and untrusted outbound requests.

### F-023 — Curriculum and package import paths are insufficiently contained
- Status: **FIXED** (2026-11-06) — `Path.resolve().is_relative_to(MODULES_DIR)`; upload/decompress/question caps. Residual: symlink policy still OS-dependent (resolve follows symlinks then containment rejects escape). Covered by `tests/test_security_f021_024.py`.
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_packages.py:140-178`, `790-810`, `443-540`
- Evidence / current behavior:
  - Path checks use `str(target).startswith(str(root))` rather than `Path.is_relative_to`.
  - `import_curriculum_module` accepts a caller-supplied relative path, resolves it, reads JSON, and creates an exam.
  - Package/gzip/YAML uploads are read and decompressed without size or expansion limits.
  - Package imports create exams without the author-role guard described in F-014.
- Logic tree (related files read):
  - Authenticated teacher/student → path or multipart package → filesystem read/decompression → package parse → exam/question creation.
- Impact:
  - Prefix-collision paths or symlink/expanded archive scenarios can read unintended files or exhaust resources; malicious package fields can create invalid/large records and answer-bearing student-owned exams.
- Recommended fix (step-by-step, preserve behavior):
  1. Use `root_resolved` and `target.is_relative_to(root_resolved)` after resolving; reject symlinks unless explicitly allowed.
  2. Accept only server-issued module IDs rather than arbitrary paths, or map IDs to an index.
  3. Enforce upload, decompressed-size, question-count, string-length, and recursion limits before parsing/persistence.
  4. Apply the shared approved-teacher authorization and use a transaction with rollback on any invalid question.
- Verification:
  - Test `..`, prefix-collision, symlink, malformed, gzip-bomb, huge, and invalid-enum packages.

### F-024 — Archive route claims encryption but writes unencrypted data and stores the wrong DB value
- Status: **FIXED** (2026-11-06) — approve always AES-GCM via `ARCHIVE_MASTER_KEY`; `compressed_data` stores ciphertext hex; restore decrypts with IV/salt. Residual: migrate/re-encrypt any pre-fix archives that used `encryption_algorithm=none`; set `ARCHIVE_MASTER_KEY` in production `.env`. Covered by `tests/test_security_f021_024.py`.
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_archive.py:840-970`, `src/plannededucation/api/archive_utils.py:137-225`
- Evidence / current behavior:
  - `archive_submission` encrypts only when `master_key` is passed (`archive_utils.py:174-180`), but the approval route calls it without a key (`routes_archive.py:910-918`).
  - The route reports “encrypted storage”, but metadata will be `encryption_algorithm="none"` and empty IV/salt.
  - The database row stores `compressed_data=meta["archive_hash"]` rather than the actual archived payload (`routes_archive.py:928-948`).
  - `restore_archive` only flips the status; `ArchiveManager.restore_submission` cannot decrypt encrypted data and has a `pass` branch (`archive_utils.py:207-225`).
- Logic tree (related files read):
  - Teacher approve → sealed submission → zstd archive → optional AES-GCM branch not given a key → file/hash metadata → DB row → restore/download.
- Impact:
  - Student answers and PII are stored in a reversible compressed hex file without the claimed encryption, while the DB record cannot reconstruct/restore the file. Integrity/retention claims are false.
- Recommended fix (step-by-step, preserve behavior):
  1. Load a dedicated archive master key from secret storage; fail closed if encryption is required but absent.
  2. Persist the actual ciphertext or a secure file reference plus authenticated metadata; never substitute a hash for content.
  3. Implement authenticated decrypt/restore using stored IV/salt/version and validate content/archive hashes.
  4. Make approval/file/DB updates transactional or compensating: do not mark graded if archiving fails.
  5. Re-encrypt/migrate existing unencrypted archives under an audited process.
- Verification:
  - Raw-file inspection must show ciphertext, not compressed plaintext.
  - Round-trip archive/restore, wrong-key, tamper, missing-file, and DB/file mismatch tests.

### F-025 — Alert ingestion and alert data are unauthenticated
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_alerts.py:62-190`
- Evidence / current behavior:
  - Webhook, list, and detail routes have no bearer dependency, shared secret, mTLS, or signature validation.
  - The webhook merges arbitrary payloads into the alerts table and logs labels/annotations.
  - Public list/detail responses expose infrastructure metadata, annotations, generator URLs, and group keys.
- Logic tree (related files read):
  - Internet/internal caller → `/api/alerts/webhook` → database/logs; any caller → `/api/alerts` → monitoring data.
  - Alertmanager config calls the same endpoint internally (`monitoring/alertmanager.yml:55-90`) but supplies no authentication.
- Impact:
  - Attackers can poison monitoring, flood the database/logs, trigger downstream notifications when added, or learn infrastructure details.
- Recommended fix (step-by-step, preserve behavior):
  1. Require an internal authentication mechanism on the webhook (signed body, secret header, or mTLS) and configure Alertmanager to send it.
  2. Protect list/detail routes with admin/observability scope; bound alert count, annotation lengths, and retention.
  3. Validate timestamps, fingerprint, enum values, and idempotency before `merge`.
- Verification:
  - Unsigned/invalid/replayed webhook tests, large payload tests, and non-admin list/detail tests.

### F-026 — Email fallback logs reset links and temporary passwords
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/email_service.py:145-153`, `155-195`, `src/plannededucation/api/routes_notifications.py:273-296`
- Evidence / current behavior:
  - When no provider is configured, the service logs the full `text_content`.
  - Password-reset text includes the bearer reset URL/token.
  - Internal approval email text includes the generated temporary password.
  - Backend log files are explicitly created by `main.py:80-99`.
- Logic tree (related files read):
  - Reset/approval → optional email dispatch → no SMTP/Brevo → `[EMAIL LOG] ... Content: ...` → persistent backend log.
- Impact:
  - Anyone with log access can reset accounts or log in as users. Logs and diagnostic artifacts violate the no-secret/PII policy.
- Recommended fix (step-by-step, preserve behavior):
  1. Replace fallback content logging with a redacted event: recipient hash/opaque ID, template name, request ID, and delivery status only.
  2. Never log reset URLs, tokens, temporary passwords, or message bodies; also redact upstream exception text before logging.
  3. Use an out-of-band one-time display for offline operators if email is absent, with forced change and explicit acknowledgement.
- Verification:
  - Capture logs for reset-link and temporary-password flows and assert no token/password/body appears.

### F-027 — Rate limits, CAPTCHA, and AI budgets are declarative rather than protective
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_auth.py:274-280`, `397-405`, `508-515`, `1055-1108`; `src/plannededucation/api/routes_ai.py:63-119`, `780-830`; `src/plannededucation/api/limiter.py:24-33`
- Evidence / current behavior:
  - Login and registration limits are `500/minute`, allowing substantial Argon2 CPU/memory work and account-lockout abuse.
  - CAPTCHA endpoints exist but login/register/reset never require a verified CAPTCHA token; portal search found no CAPTCHA integration.
  - AI grading/test creation use an in-memory per-process limiter; content generation has no limiter.
  - `MAX_DAILY_COST_USD` is only reported; no endpoint rejects calls after the budget, and provider pricing includes paid services.
- Logic tree (related files read):
  - Public login/register/reset/AI calls → slowapi or local dict (often no effective challenge/budget) → Argon2/provider outbound call.
- Impact:
  - Attackers can exhaust CPU, lock out accounts, spam reset notifications, or consume user/provider quotas. The implementation does not satisfy the documented free-tier/no-paid-service guardrail.
- Recommended fix (step-by-step, preserve behavior):
  1. Use strict per-account and per-IP limits with a distributed backend for multi-worker deployments; distinguish login failures from legitimate traffic.
  2. Enforce CAPTCHA as a dependency only where configured, fail closed in production if the configured provider is unavailable.
  3. Rate-limit all AI operations and persist atomic usage/budget counters; reject once the configured daily limit is reached.
  4. Restrict provider choices to explicitly allowed free/local/BYOK policies and clearly label user-owned external calls.
- Verification:
  - Load tests for login/reset/AI across workers, budget-boundary tests, and CAPTCHA absent/invalid/replayed tests.

### F-028 — Browser token handling retains insecure localStorage fallback and logout is incomplete
- Severity / Confidence: **High / High**
- Location: `web/apps/portal/src/api.ts:16-47`, `web/apps/portal/src/contexts/AuthContext.tsx:39-100`, `web/apps/portal/src/components/Layout.tsx:40-59`
- Evidence / current behavior:
  - Every client path reads `sessionStorage` **or** `localStorage`.
  - `refreshUser` migrates a legacy localStorage access token into sessionStorage.
  - `logout` removes only sessionStorage tokens (`AuthContext.tsx:90-94`), leaving any legacy localStorage access/refresh token usable by the next mount.
  - Refresh tokens are stored in JavaScript-readable sessionStorage and no frontend refresh flow is implemented.
- Logic tree (related files read):
  - Login → session token write → API interceptor/fetch fallback → logout → stale localStorage token → `refreshUser` silently restores account.
- Impact:
  - XSS or stale legacy storage can survive logout; a user may believe they signed out while a token remains active. The architecture does not achieve the preferred httpOnly-cookie session boundary.
- Recommended fix (step-by-step, preserve behavior):
  1. Remove localStorage fallback and perform a one-time explicit migration that immediately deletes the legacy value.
  2. Clear all access/refresh storage on logout and revoke the server refresh session.
  3. Prefer an httpOnly, Secure, SameSite cookie for refresh/session state; keep only a short-lived access token in memory if necessary.
  4. Add a centralized authenticated request helper rather than duplicating raw `fetch` token reads.
- Verification:
  - Seed both storages, logout, reload, and assert no authenticated request is made.
  - XSS/storage tests must not find refresh tokens in localStorage/sessionStorage.

### F-029 — Secure exam WebSocket contract and Redis lifecycle are inconsistent
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/routes_chat.py:47-119`, `184-260`; `web/apps/portal/src/components/SecureChat.tsx:22-60`
- Evidence / current behavior:
  - Backend broadcasts `{"sender": ..., "message": ...}` without a `type` field (`routes_chat.py:106-118`).
  - Frontend parses JSON but only appends messages when `data.type === 'message'`; valid backend messages are silently ignored (`SecureChat.tsx:39-50`).
  - With a relative `API_URL` (`api.ts:3-7`), frontend constructs `ws:///api/...`, which has no host.
  - `manager.start()` is never called in `main.py` lifespan; Redis mode publishes but does not establish the cross-worker listener.
  - WebSocket auth repeats the refresh-token type omission and admits completed submissions (`routes_chat.py:228-245`).
- Logic tree (related files read):
  - `TakeExam` → `SecureChat` URL/first-frame auth → backend room access → manager broadcast/Redis → frontend message parser.
- Impact:
  - Exam “raise hand” chat is broken in common production/relative-URL and normal JSON cases; multi-worker rooms diverge; completed students can rejoin old rooms.
- Recommended fix (step-by-step, preserve behavior):
  1. Define a shared message schema with `type`, sender ID/name, timestamp, and message; validate server input and render escaped text.
  2. Build the WebSocket URL with `new URL(API_URL, window.location.origin)` and use `ws/wss` from the resolved URL.
  3. Start/stop the manager in application lifespan and fail/alert when Redis is configured but unavailable instead of silently splitting workers.
  4. Require an active submission and access token type `access`.
- Verification:
  - Browser and TestClient broadcast tests for relative and absolute API URLs, multi-worker Redis, completed submissions, and invalid token types.

### F-030 — Teacher grading UI swallows a failed approval and reports success
- Severity / Confidence: **High / High**
- Location: `web/apps/portal/src/pages/AIGradingUpload.tsx:176-210`, `src/plannededucation/api/routes_archive.py:841-970`
- Evidence / current behavior:
  - The portal calls `/archive/teacher/approve-staged/{id}`.
  - No such backend route exists; the implemented endpoint is `POST /archive/teacher/approve` with a list payload.
  - The catch block intentionally treats the failed call as a mocked endpoint and shows success (`AIGradingUpload.tsx:180-188`).
- Logic tree (related files read):
  - Teacher review → nonexistent endpoint → catch → success toast/local close → no score/archive database update.
- Impact:
  - Teachers can believe a grade was approved/sealed when it was not, causing silent data-integrity failures and possible missed feedback.
- Recommended fix (step-by-step, preserve behavior):
  1. Call the real batch approval contract with the current override data, or add a properly authorized single-submission route.
  2. Remove the success fallback; surface the server error inline and keep the review modal open.
  3. Refresh the submission and archive state from the server after approval.
- Verification:
  - Mock 404/500 and assert no success state is shown.
  - Assert a successful approval changes score, feedback, archive row, and UI status.

### F-031 — Installers retain predictable admin defaults and print/store credentials
- Severity / Confidence: **High / High**
- Location: `install.ps1:39-68`, `install.sh:39-50`, `install.sh:760-870`, `install.ps1:1020-1145`, `scripts/deploy/setup_admin.py:35-80`
- Evidence / current behavior:
  - PowerShell and Bash expose a predictable default admin password; `setup_admin.py` has the same fallback if environment input is absent.
  - The Linux installer prints the admin password in the final summary and always writes a plaintext `ADMIN_CREDENTIALS.txt`.
  - Windows prints generated credentials and may write the same file if clipboard copy fails, without applying an ACL.
  - `setup_admin.py` also installs a predictable temporary JWT setup secret if no JWT secret is found.
- Logic tree (related files read):
  - Installer parameters/env → admin setup script → database admin hash → terminal/log/credential file.
- Impact:
  - A headless/default installation can be taken over with public/default credentials; CI/terminal logs or local files can expose credentials and recovery codes.
- Recommended fix (step-by-step, preserve behavior):
  1. Refuse startup when an explicit strong admin password/secret is absent; generate into a secure operator channel only.
  2. Remove predictable fallbacks from installers/setup scripts and fail closed when JWT/DB keys are missing.
  3. Never print passwords/tokens; if a file fallback is unavoidable, create it with restrictive ACLs/mode and require explicit operator confirmation.
  4. Force password change on first login and record an audit event without the secret.
- Verification:
  - Run noninteractive installs with missing/default credentials and assert a safe failure or one-time secure handoff.
  - Scan stdout, install logs, generated files, and clipboard fallback for secret values.

### F-032 — Deployment helpers execute interpolated shell/Python and omit DB encryption
- Severity / Confidence: **High / High**
- Location: `install.sh:136-146`, `880-910`; `scripts/backup/backup_restore.ps1:70-185`; `scripts/deploy/deploy_wizard.py:230-340`
- Evidence / current behavior:
  - Bash sources the generated `.env`; user-controlled domain/values are inserted without shell quoting.
  - The PowerShell backup tool builds commands from `DATABASE_URL`, database paths, and backup filenames and executes them with `Invoke-Expression`.
  - `deploy_wizard.py` uses `shell=True` for composed command strings and interpolates user input into a Python `-c` program; escaping handles quotes but not all Python/string/control cases.
  - The wizard generates JWT and AI keys but never generates `DB_ENCRYPTION_MASTER_KEY` or sets `DATABASE_ENCRYPTION=true`.
  - Its generated admin Python imports `hash_password`, while the current auth module exposes `get_password_hash`, so the native admin creation path is broken.
- Logic tree (related files read):
  - Operator input/env → shell source/eval or generated command → privileged installer/backup/database operation.
  - Wizard → `.env` with only two keys → production database → field encryption default remains off.
- Impact:
  - Malicious installation paths/domains/backup filenames can become local command execution; backup scripts can execute hostile environment/path content. A wizard deployment silently omits the required DB encryption key and may fail to create the first admin.
- Recommended fix (step-by-step, preserve behavior):
  1. Never source untrusted `.env` text; parse key/value data without evaluation and quote all generated values.
  2. Invoke subprocesses as argument arrays with `shell=False`; use `ProcessStartInfo.ArgumentList`/safe PowerShell invocation rather than string evaluation.
  3. Use parameterized database tools and validate identifiers/paths.
  4. Make the wizard generate distinct JWT/AI/DB/archive keys and call the current password-hash helper.
  5. Add installer smoke tests for custom paths, domains, passwords, and backup filenames.
- Verification:
  - Fuzz inputs with shell metacharacters, newlines, quotes, traversal, and spaces; assert no extra process/file is created.
  - Run native wizard end-to-end and inspect encryption env values and admin creation.

### F-033 — Backups can contain database credentials and are not encrypted
- Severity / Confidence: **High / High**
- Location: `src/plannededucation/api/backup_service.py:107-137`, `30-50`; `src/plannededucation/api/routes_admin.py:584-626`
- Evidence / current behavior:
  - When `pg_dump` is absent/fails, the service writes a fallback gzip containing the full `DATABASE_URL` (`backup_service.py:124-134`), which can include the database password.
  - Normal SQLite/PostgreSQL backups are gzip/compressed dumps, not encrypted with the DB/archive key.
  - Admin-configurable `backup_location` is an arbitrary path and backup responses expose filesystem paths (`backup_service.py:139-148`).
- Logic tree (related files read):
  - Admin/config → backup directory → pg_dump/native dump → gzip artifact → admin list/download/delete APIs.
- Impact:
  - Backup artifacts contain student records, exam answers, and potentially connection credentials in recoverable form. A filesystem reader or a misconfigured path can obtain all school data.
- Recommended fix (step-by-step, preserve behavior):
  1. Never write connection URLs/passwords into fallback artifacts or logs; fail the backup instead of creating a misleading metadata dump.
  2. Encrypt backups with a dedicated archive/backup key using authenticated encryption and store key IDs, not keys.
  3. Restrict backup paths to an approved root and validate `is_relative_to`; enforce file permissions/ACLs.
  4. Return logical filenames only, not absolute server paths.
- Verification:
  - Inspect backup contents for secrets/PII, test wrong-key restore, path traversal, permission checks, and failed `pg_dump`.

### F-034 — Docker production configuration disables the intended DB/Redis protections
- Severity / Confidence: **High / High**
- Location: `docker-compose.yml:40-70`
- Evidence / current behavior:
  - Backend environment includes `DATABASE_URL`, JWT, CORS, and AI key variables but not `DATABASE_ENCRYPTION` or `DB_ENCRYPTION_MASTER_KEY`.
  - `REDIS_URL` and `USE_REDIS_CHAT` are not set even though a password-protected Redis service exists; the application defaults to `redis://localhost:6379/0` and in-memory chat.
  - Image/service tags are mutable or not digest-pinned.
- Logic tree (related files read):
  - `.env` → Compose interpolation → backend process → `db_encryption` defaults false / Redis points inside backend container → security/availability behavior differs from native installers.
- Impact:
  - A production Docker deployment stores configured sensitive fields plaintext and silently loses cross-worker chat/pub-sub behavior. Mutable image tags weaken reproducibility/supply-chain guarantees.
- Recommended fix (step-by-step, preserve behavior):
  1. Require and pass distinct DB encryption/archive keys; fail Compose startup if absent.
  2. Set `REDIS_URL=redis://:<password>@redis:6379/0` and `USE_REDIS_CHAT=true`, with a safe secret-file mechanism.
  3. Pin images by digest or controlled immutable release tags and scan the exact built images.
  4. Add a production Compose smoke test for encryption, Redis auth, WebSocket broadcast, and health.
- Verification:
  - Inspect container env (without printing secrets), query raw DB fields, and test two backend workers using Redis.

### F-035 — Parent relationship endpoints do not enforce parent/student roles or target type
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/routes_parent.py:93-140`, `20-90`
- Evidence / current behavior:
  - `request_relationship` does not require `current_user.role == "parent"` and does not verify the target is a student.
  - `children-progress` likewise has no parent-role check; it trusts `parent_id` rows.
  - Existing tests use the default registration role for both “parent” and “student” (`tests/test_routes_parent.py:13-20`), so the missing role invariant is not detected.
- Logic tree (related files read):
  - Any authenticated account → relationship request with arbitrary target/teacher IDs → student approval → active row → score/feedback retrieval.
- Impact:
  - A student, teacher, or arbitrary account can impersonate the parent side and obtain another user's progress after target approval; a non-student target can expose unrelated exam records.
- Recommended fix (step-by-step, preserve behavior):
  1. Validate requester role, target role, optional teacher role/approval, and relationship status in a schema-backed request.
  2. Require an explicit parent/student/teacher handshake policy; do not make “no teacher supplied” an automatic bypass unless product requirements say so.
  3. Require `current_user.role == "parent"` in progress and parent-reset paths.
- Verification:
  - Add negative tests for student-as-parent, teacher target, admin target, foreign teacher ID, pending/rejected relationships, and active-only progress access.

### F-036 — Direct-message unread-count route is shadowed by the partner route
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/routes_chat.py:545-580`, `820-830`; `web/apps/portal/src/components/Layout.tsx:44-55`
- Evidence / current behavior:
  - `GET /messages/direct/{partner_id}` is registered before `GET /messages/direct/unread-count`.
  - FastAPI matches `unread-count` as `partner_id`, calls `_get_user_or_404`, and returns 404 instead of the unread count.
  - Layout polls that exact URL every 30 seconds, so the header badge remains stale/zero.
- Logic tree (related files read):
  - Layout interval → `/chat/messages/direct/unread-count` → dynamic route → user lookup for ID `unread-count` → 404.
- Impact:
  - The intentional header Messages placement works visually, but the unread badge and polling journey do not.
- Recommended fix (step-by-step, preserve behavior):
  1. Register static routes before dynamic routes, or constrain `partner_id` to a UUID path converter.
  2. Use one typed API helper for unread counts in Layout and Messages.
  3. Return a stable zero count for transient polling failures without masking authorization errors.
- Verification:
  - Route-resolution test must return 200 for unread count and still resolve a real partner conversation.

### F-037 — Teacher-aide role/approval state is internally inconsistent
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/routes_auth.py:1625-1660`, `1739-1812`; `src/plannededucation/api/models.py:48-56`; `src/plannededucation/api/routes_chat.py:264-280`
- Evidence / current behavior:
  - Approval sets `is_teacher_aide=True` but does not change the user's `role` to `teacher_aide`.
  - Lounge access checks role strings, not `is_teacher_aide`; a nominated student remains unable to access the lounge.
  - Revoke allows only `current_user.role == "admin"` as the admin override, excluding `is_admin=True` records with a non-admin role.
  - Lounge message listing is unbounded and performs per-message/per-reply user queries.
- Logic tree (related files read):
  - Teacher nominate/approve → boolean flag → UI reports success → role-based lounge/share routes reject or omit the aide.
- Impact:
  - The advertised aide journey is dead or inconsistent; an aide may be shown in DM data but lack permissions, while query volume can grow without bounds.
- Recommended fix (step-by-step, preserve behavior):
  1. Choose one source of truth: role plus approval record, or a dedicated grant table; derive effective permissions centrally.
  2. Require approved, active aide status on lounge/exam-share routes and permit the documented admin override.
  3. Add pagination and eager loading for lounge messages.
- Verification:
  - Test nomination, approval, lounge access, share/correct permissions, revoke by approver/admin, and pending/unapproved users.

### F-038 — OCR/STT endpoints allow unbounded CPU/memory work in async handlers
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/routes_ocr.py:22-230`, `251-320`; `src/plannededucation/api/routes_stt.py:17-200`; `src/plannededucation/api/ocr_service.py:96-170`; `src/plannededucation/api/stt_service.py:90-180`
- Evidence / current behavior:
  - Base64 fields, batch lists, multipart files, and bulk file lists have no byte/count/dimension/duration limits.
  - CPU-heavy PIL/Tesseract/EasyOCR/Whisper work runs directly inside `async def` routes.
  - Health/model endpoints are public and expensive model loading is lazy per process.
- Logic tree (related files read):
  - Authenticated request → base64/file read into memory → synchronous OCR/STT in event loop → response with full text/boxes.
- Impact:
  - A single account can block the event loop, exhaust memory/CPU/GPU, or create a multi-worker availability incident; large student media is also sensitive.
- Recommended fix (step-by-step, preserve behavior):
  1. Enforce request/body/file count, byte, pixel, audio-duration, and output limits at middleware/schema/service layers.
  2. Offload CPU-bound work to a bounded worker pool or background job with per-user quotas.
  3. Validate actual file signatures, not only MIME prefixes, and return generic errors.
  4. Require auth for operational health/model metadata where it is not needed by a load balancer.
- Verification:
  - Oversized, decompression-bomb, malformed, concurrent, and long-running media tests with event-loop latency assertions.

### F-039 — Portal API contracts leave roster and classroom reset journeys broken
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/pages/TeacherClasses.tsx:78-108`, `158-181`; `web/apps/portal/src/pages/Login.tsx:75-100`; `src/plannededucation/api/routes_auth.py:942-1048`
- Evidence / current behavior:
  - TeacherClasses requests `/auth/users/students`, but the backend exposes `/auth/teacher/students`; the roster silently remains empty.
  - Login's teacher-reset completion posts `identifier` and `new_password` but omits required `reset_token`; backend requires it at `routes_auth.py:1007-1012`.
  - The login field is `type="email"` even though the backend supports email or username.
- Logic tree (related files read):
  - Teacher classes → wrong path → empty roster → no quick-reset targets.
  - Teacher quick-reset response → reset token returned to teacher → student login reset UI → token never collected/sent → 422.
- Impact:
  - The documented emergency reset and roster journeys fail or appear to succeed only partially; support staff may repeat resets or share credentials insecurely.
- Recommended fix (step-by-step, preserve behavior):
  1. Correct the roster endpoint or add a stable compatibility route.
  2. Add a reset-token input/secure handoff to the login flow, or design a one-time server transaction that does not require manual token copying.
  3. Use a text identifier field with server-side email/username validation.
- Verification:
  - Browser test from teacher roster through student reset completion, including wrong/expired token.

### F-040 — AI key UI does not load key state and offers unsupported providers
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/components/AIKeySettings.tsx:20-60`, `90-170`; `src/plannededucation/api/ai_providers.py:340-380`
- Evidence / current behavior:
  - The component reads `user.ai_api_key_encrypted`, but `UserResponse` intentionally excludes that field (`schemas.py:31-49`); it never calls `/auth/ai-key` to obtain `has_api_key`.
  - After saving, the component does not update `hasKey`, so remove-key controls and “configured” state are stale.
  - The UI offers Anthropic, DeepSeek, Groq, Cohere, Mistral, and custom, while the provider factory only implements Gemini, OpenRouter, Ollama, and OpenAI-compatible.
- Logic tree (related files read):
  - Settings load `/auth/me` → absent encrypted key → `hasKey=false` → save provider/key → provider factory later rejects unsupported provider.
- Impact:
  - Teachers cannot reliably tell whether a key is stored or remove it, and selecting advertised providers leads to runtime failures.
- Recommended fix (step-by-step, preserve behavior):
  1. Load the redacted `/auth/ai-key` response on mount and update state after save/delete.
  2. Align the provider enum/UI with implemented adapters, or implement adapters with provider-specific validation.
  3. Validate custom base URLs under F-022 and never expose ciphertext.
- Verification:
  - Save, reload, rotate, remove, and use every advertised provider; assert state and errors match reality.

### F-041 — Deployment UI can erase SMTP credentials and header settings are not persisted
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/components/DeploymentConfigPanel.tsx:30-90`, `230-300`; `src/plannededucation/api/deployment_config.py:20-80`, `230-290`
- Evidence / current behavior:
  - Backend response intentionally excludes `smtp_password`, but the UI replaces its config state with the response and later submits `smtp_password: ''` from its initial/empty state.
  - `DeploymentConfigSchema` has no `header_mode` or `header_image_url`, although the UI sends them and `Layout.tsx` expects them.
  - `save_deployment_config` writes `deployment.json` before reconstructing the CORS string (`230-260`), so the file and `.env` can diverge.
- Logic tree (related files read):
  - Admin loads config → secret omitted → UI state empty → unrelated save → `.env` SMTP password overwritten.
  - Header form → schema extra fields ignored → Layout never receives persisted header values.
- Impact:
  - A harmless network/config change can break password-reset email; school branding appears saved but disappears after restart; runtime config sources disagree.
- Recommended fix (step-by-step, preserve behavior):
  1. Use patch semantics for secrets: omit `smtp_password` when unchanged and preserve the existing env value server-side.
  2. Put header fields in a separate validated school-header endpoint or add them consistently to deployment schema/model.
  3. Compute all derived CORS data before writing either file and write atomically.
- Verification:
  - Save unrelated config with an existing SMTP secret and assert it remains unchanged; reload header config after restart.

### F-042 — Prometheus metrics are exposed without an application auth boundary
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/main.py:103-146`, `380-408`
- Evidence / current behavior:
  - `start_http_server(9090)` starts a separate metrics server without authentication or documented network binding.
  - Request metrics label `endpoint` with the raw URL path, potentially including IDs and high-cardinality values.
  - Docker Compose does not expose 9090 publicly, but native deployments can bind it to the host; the main API also has a `/metrics` scrape target in `monitoring/prometheus.yml:20-35` without an observed route/auth configuration.
- Logic tree (related files read):
  - Request path → metrics labels → Prometheus endpoint/network → monitoring or any reachable caller.
- Impact:
  - Route IDs/traffic patterns and operational status can be disclosed; high cardinality can exhaust Prometheus memory and logging.
- Recommended fix (step-by-step, preserve behavior):
  1. Bind metrics to loopback/internal network and restrict at firewall/reverse proxy.
  2. Use templated route names or redacted labels, never raw IDs.
  3. Add a dedicated scrape credential/mTLS and verify the configured endpoint.
- Verification:
  - Native network scan/bind test, unauthenticated scrape test, and high-cardinality route test.

### F-043 — CSP/CORS defaults weaken browser isolation
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/main.py:228-249`, `270-310`; `web/apps/portal/nginx.conf:10-17`
- Evidence / current behavior:
  - Both CSPs permit `'unsafe-inline'` and `'unsafe-eval'`.
  - `img-src` permits arbitrary HTTPS/data sources; `CORS_ORIGINS` is parsed as a string list without URL/scheme/wildcard validation while credentials are enabled.
  - Admin deployment config allows arbitrary CORS/host strings and automatically adds HTTP origins (`deployment_config.py:250-270`).
- Logic tree (related files read):
  - Installer/admin input → `.env`/JSON → CORS/CSP middleware and Nginx → browser trust boundary.
- Impact:
  - XSS impact is larger with eval/inline allowances; a misconfigured credentialed origin can expose bearer-authenticated responses cross-origin.
- Recommended fix (step-by-step, preserve behavior):
  1. Replace unsafe CSP directives with nonces/hashes or a narrowly justified Vite policy; remove eval in production.
  2. Validate origins as exact `https`/approved local origins; reject `*`, credentials with wildcard, and untrusted HTTP in production.
  3. Validate custom image URLs and use a school-controlled origin where possible.
- Verification:
  - CSP report-only/enforcement tests, credentialed cross-origin matrix, and hostile config input tests.

### F-044 — Mandatory i18n and date/time requirements are still violated
- Severity / Confidence: **Medium / High**
- Location examples: `web/apps/portal/src/pages/Login.tsx:55-70`, `Settings.tsx:99-131`, `TakeExam.tsx:55-65`, `TwoFASettings.tsx:35-100`, `PasskeysSettings.tsx:115-270`, `NotificationBell.tsx:55-170`, `TeacherClasses.tsx:140-215`, `SpecialCharactersPicker.tsx:280-500`
- Evidence / current behavior:
  - Many button labels, errors, headings, placeholders, aria labels, confirmation strings, and status messages are literal English or use `t(...) || 'English fallback'`.
  - Notification/teacher/admin/AI pages contain literals such as “Failed to…”, “Approving…”, “Delete”, “Create Passkey”, and “Optional”.
  - Several dates/times use locale-dependent `toLocaleDateString()`/`toLocaleTimeString()` without the required `dd/mm/yyyy` and timezone labeling (`NotificationBell.tsx:503-509`, `TeacherApprovalPanel.tsx:164-168`, `AIGradingUpload.tsx:567-571`).
- Logic tree (related files read):
  - Component string → direct render/toast/ARIA → locale cannot translate; browser locale formats date inconsistently.
- Impact:
  - Accessibility and teacher/student comprehension regress across supported locales; sensitive status times can be misread across time zones. This also contradicts the claimed Phase 27 completion.
- Recommended fix (step-by-step, preserve behavior):
  1. Add keys to English source and replace every user-facing literal, including fallbacks/ARIA/tooltips and FAQ data.
  2. Use shared locale/time helpers with explicit `dd/mm/yyyy` and local/UTC labels where relevant.
  3. Run key extraction against all TS/TSX and compare every key to `en/messages.json` and supported locale files.
- Verification:
  - Static scan for JSX/user-facing literals, missing keys, and locale snapshots for dates/times/ARIA labels.

### F-045 — Special-character insertion mutates controlled DOM without updating React state
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/components/SpecialCharactersPicker.tsx:88-180`
- Evidence / current behavior:
  - The picker directly assigns `target.value` and dispatches native `input`/`change` events.
  - React-controlled inputs may have a value tracker that does not treat this assignment as a user change; component state can remain unchanged while the DOM displays the symbol.
  - Exam save handlers use React state, not the DOM value.
- Logic tree (related files read):
  - Focused controlled textarea → picker → direct DOM mutation → submit handler reads stale React state → inserted symbol disappears or is not graded.
- Impact:
  - The intentional Symbols picker can silently lose characters in exam answers, rubrics, or questions.
- Recommended fix (step-by-step, preserve behavior):
  1. Expose an insertion callback from editor/exam components and update their state via selection ranges.
  2. Use a controlled insertion hook for generic inputs, with a narrowly tested fallback for uncontrolled/native fields.
  3. Preserve cursor position and selection after state update.
- Verification:
  - Insert into every supported controlled input, submit/reload, and assert the symbol is persisted at the expected cursor position.

### F-046 — CI security checks can pass while failing the intended analysis
- Severity / Confidence: **Medium / High**
- Location: `.github/workflows/ci.yml:45-70`, `100-120`, `170-210`; `.github/workflows/security-checks.yml:20-95`
- Evidence / current behavior:
  - Mypy is `continue-on-error` and explicitly `|| true`; Bandit uses `--exit-zero`.
  - The frontend command `npx oxlint -A security` does not act as a deny-on-security gate as the project documentation claims; verify the exact CLI semantics and use an explicit deny flag.
  - CI uses raw pytest instead of the repository-mandated cache/log wrapper.
  - Actions and downloaded scanners are referenced by mutable tags/URLs rather than immutable commit/digest pins; CI includes hardcoded throwaway token-like environment values (redacted here).
- Logic tree (related files read):
  - Push/PR → workflow → non-blocking static/security commands → green summary even when findings exist.
- Impact:
  - The repository can claim green security checks while type/security failures are ignored; mutable tool/action supply chains can change CI behavior.
- Recommended fix (step-by-step, preserve behavior):
  1. Make security/type checks fail on actionable findings, with a documented baseline for accepted issues.
  2. Use the required source-aware test cache wrapper in CI or explicitly document the controlled CI exception.
  3. Pin third-party actions/scanners to commit SHAs and verify downloaded checksums.
  4. Remove hardcoded token-shaped values from workflow env; generate test-only values at runtime.
- Verification:
  - Inject a deliberate Bandit/TypeScript/security finding and assert the workflow fails.
  - Review workflow dependency pinning and secret-scan output.

### F-047 — Demo roster PII and localStorage roster data ship in the public portal
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/pages/TeacherClasses.tsx:24-44`, `49-60`, `120-130`
- Evidence / current behavior:
  - The default class data contains named student records and school-style email addresses in the frontend bundle.
  - The roster/classes state is persisted to `localStorage` under `pe_teacher_classes`.
- Logic tree (related files read):
  - Public SPA bundle → demo names/emails; teacher UI → roster merge → browser localStorage.
- Impact:
  - The bundle exposes hardcoded person-like PII and shared/browser profiles retain roster data outside the encrypted backend. Demo rows also risk being mistaken for real class membership.
- Recommended fix (step-by-step, preserve behavior):
  1. Replace defaults with empty state or unmistakable non-person placeholders.
  2. Do not persist roster PII in localStorage; load server-authoritative, scoped rosters and clear legacy keys.
  3. If offline roster support is required, encrypt it under the offline key hierarchy and apply retention.
- Verification:
  - Search production bundle/localStorage after logout and assert no roster names/emails remain.

### F-048 — Offline sync queue cannot reliably submit queued exams
- Severity / Confidence: **Medium / High**
- Location: `web/apps/portal/src/services/offlineSync.ts:240-350`, `web/apps/portal/src/services/offlineExam.ts:1130-1200`, backend route inventory
- Evidence / current behavior:
  - `queueExamSubmission` stores only `{submissionId}` in the sync operation payload, while `processSyncQueue` reads `op.payload.examId` and `op.payload.studentId`.
  - The dedicated sealed sync calls `/sync/submission`, but no `/sync` router exists in the backend files reviewed.
  - Teacher-device sync uses a URL read from localStorage without validation.
- Logic tree (related files read):
  - Offline submit → IndexedDB queue → online transition → missing IDs/absent endpoint → retry/failure; sealed copy may remain local only.
- Impact:
  - Offline student answers can remain unsent indefinitely while the UI says they were queued; a user-configured sync URL can receive encrypted educational records.
- Recommended fix (step-by-step, preserve behavior):
  1. Store complete, schema-versioned queue payloads and use one sync service.
  2. Implement an authenticated, ownership-checked server sync endpoint or remove the dead three-way sync claim.
  3. Validate teacher sync URL against an explicit school-network allowlist and use authenticated transport.
  4. Surface durable pending/failed status and provide a retry/export path.
- Verification:
  - Offline submit, reload, reconnect, server outage, retry exhaustion, and foreign submission tests.

### F-049 — Refresh rotation and password changes do not fully revoke sessions
- Severity / Confidence: **Medium / High**
- Location: `src/plannededucation/api/routes_auth.py:497-553`, `557-596`, `687-699`
- Evidence / current behavior:
  - Only one refresh-token hash is stored per user; concurrent refresh requests can race and one new token overwrites another.
  - Password change updates the password but leaves the current refresh-token hash.
  - Password-reset confirmation issues an access token but does not clear/rotate the existing refresh token.
  - There is no logout/revoke endpoint; the frontend only deletes browser storage.
- Logic tree (related files read):
  - Password/session mutation → single user hash/timestamp → existing device token remains valid or concurrent rotations become ambiguous.
- Impact:
  - A stolen refresh token can survive a password reset/change, and concurrent refresh behavior can permit replay or unexpectedly invalidate the other device.
- Recommended fix (step-by-step, preserve behavior):
  1. Store per-device refresh sessions with token family, rotation/reuse detection, revocation, and expiry.
  2. Revoke all or selected sessions on password/2FA/reset changes.
  3. Add authenticated logout/revoke-all endpoints and use them from the portal.
- Verification:
  - Multi-device concurrent refresh, password-change, reset, deactivation, and logout tests.

### F-050 — Security plans/tests overstate coverage and leave negative paths untested
- Severity / Confidence: **Medium / High**
- Location: `plans/PLANS_UPDATED.md:35-120`, `plans/2026-11-06_AGENT_WORK_STATUS.md:80-140`, `tests/test_routes_parent.py:13-20`, `tests/test_chat.py:70-123`, `tests/test_routes_archive_and_ai.py:15-170`
- Evidence / current behavior:
  - Plans describe Google SSO, TOTP enforcement, AES-GCM archive encryption, Presidio zero-PII guarantees, and complete i18n as implemented, while the current code paths above do not provide those guarantees.
  - Parent tests label default-role accounts as parent/student without setting roles.
  - Chat tests check connection acceptance but not message schema delivery, refresh-token rejection, completed-submission access, or Redis lifecycle.
  - Archive tests exercise teacher routes only and do not cover missing admin guards, raw archive encryption, or restore.
- Logic tree (related files read):
  - Plan claim → agent assumes control exists → tests cover happy path only → regressions reach deployment.
- Impact:
  - Later fixes may be incorrectly skipped, and green tests provide false assurance for the highest-risk authorization/privacy cases.
- Recommended fix (step-by-step, preserve behavior):
  1. Mark stale plan claims as conditional until independently verified.
  2. Add negative/security regression suites for every finding in this report.
  3. Make role fixtures explicit and use the mandatory test-cache/logging system.
  4. Add contract tests generated from route schemas for frontend/backend pairs.
- Verification:
  - Require a security test matrix and evidence link before marking each plan item done.

### F-051 — Public health/model endpoints disclose operational details
- Severity / Confidence: **Low / High**
- Location: `src/plannededucation/api/routes_ocr.py:174-184`, `312-320`; `routes_stt.py:174-200`; `routes_proctoring.py:590-600`; `routes_packages.py:704-728`; `routes_alerts.py:127-130`
- Evidence / current behavior:
  - Several health endpoints are intentionally unauthenticated and disclose service availability, model names, feature lists, and versions.
- Impact:
  - This is low-risk reconnaissance and can expose installed capabilities to unauthenticated callers; it also gives attackers an unbounded probe surface.
- Recommended fix:
  - Keep a minimal unauthenticated liveness endpoint for the load balancer, but protect detailed readiness/version/model endpoints behind internal network or an observability scope.
- Verification:
  - Public endpoint response-minimization tests and internal authenticated readiness tests.

### F-052 — The repository contains meaningful configuration/policy drift
- Severity / Confidence: **Info / High**
- Location examples: `.env.example:1-90`, `config/deployment.json:1-25`, `src/plannededucation/api/auth.py:35-64`, `src/plannededucation/api/routes_ai.py:63-66`, `plans/PLANS_UPDATED.md:100-180`
- Evidence / current behavior:
  - Installer/config values, auth constants, AI budget documentation, Docker env, plans, FAQ, and current code disagree on token lifetime, DB encryption, provider support, Google SSO, archive encryption, and i18n completeness.
  - The repository contains placeholder/default credential strings and token-shaped CI values; they are not printed in this report.
- Impact:
  - Operators and later agents can deploy an unsafe configuration or assume a control is present when it is only documented.
- Recommended fix:
  - Make one versioned security/config contract authoritative; generate docs from validated settings where possible, add startup diagnostics that report enabled controls without secrets, and require plan/test evidence before “done” status.
- Verification:
  - Configuration contract tests comparing installer, Compose, `.env.example`, runtime settings, and plan claims.

## Cross-cutting themes

1. **Authorization is duplicated and role strings are treated as policy.** Several routes hand-write `if role == ...` checks, some use `is_admin`, some mention an unsupported `superadmin` string, and some define but never apply a dependency. Introduce centralized principal capabilities and row-level policy helpers.
2. **The browser/client is trusted for exam integrity.** Duration, proctoring events, offline state, and sealed submissions are all client-influenced. Server deadlines, state transitions, and review/audit rules must be authoritative.
3. **Encryption claims exceed implementation.** At-rest encryption is optional, answer rows are not registered, archive keys are not passed, offline keys are colocated, and invalid ciphertext is treated as plaintext. Establish key/version/envelope contracts before further feature work.
4. **Sensitive data is still present in logs, backups, browser storage, and public responses.** Reset tokens/passwords, student answers, roster data, source keys, DB URLs, and monitoring metadata need explicit classification and redaction.
5. **Frontend success/error handling can hide backend failures.** The AI approval fallback is the clearest example; the roster and reset path also have URL/schema drift. Generate typed API clients or add contract tests.
6. **The free-tier policy is not enforced by provider/config boundaries.** Paid-provider names and arbitrary outbound URLs are accepted, and the daily cost limit is informational. “BYOK” does not by itself satisfy a project-wide no-paid-services policy.
7. **Operational claims are not synchronized with code.** Plans and FAQ state that several controls are complete while current route and UI traces show otherwise. Security status should be evidence-backed and versioned.

## Suggested fix order (dependency-aware)

1. **Immediate containment**
   - Remove the production SEB bypass.
   - Deploy route-level admin/authz guards for archive, AI submission, OCR review, proctoring lookup, alerts, and exam creation.
   - Disable external AI/proctoring/archive workflows when their privacy/encryption prerequisites are unavailable.
   - Rotate any credentials that may have appeared in logs/backups and invalidate refresh/reset sessions.
2. **Central security primitives**
   - Introduce explicit admin levels, principal capability dependencies, access-token type validation, per-device refresh sessions, reset-token envelopes, and recovery-code hashing.
   - Add centralized ownership helpers for exams, submissions, OCR reviews, archives, packages, and proctoring.
3. **Data protection and migrations**
   - Build versioned migrations for the current model; encrypt `Answer` and other sensitive fields; repair legacy/plaintext handling; implement archive key management and encrypted backups.
   - Remove secret/PII logging and browser/localStorage secret fallbacks.
4. **Exam/proctoring integrity**
   - Enforce server deadlines/role/state transitions; return a complete typed exam-start package; repair offline crypto/sync or explicitly reduce offline claims.
   - Rebuild proctoring state transitions and distinguish telemetry from authoritative evidence.
5. **Outbound and file boundaries**
   - Add upload limits, opaque per-owner storage, path containment, package size limits, SSRF egress controls, encrypted source keys, and provider allowlists.
6. **Frontend contract repair**
   - Fix WebSocket message/URL/Redis lifecycle, roster/reset routes, AI approval endpoint, AI-key state, unread route ordering, and special-character state updates.
   - Remove success fallbacks that mask server failures.
7. **Deployment/CI hardening**
   - Make installers fail closed without explicit secrets, remove string-evaluated commands, generate all distinct keys, pass DB encryption/Redis settings in Compose, and make CI gates blocking/pinned.
8. **Quality/documentation**
   - Complete i18n/date/time migration, remove demo PII, add negative security tests via the mandated cache wrapper, and reconcile plans/FAQ with verified runtime behavior.

## Out of scope / accepted risks

- No application source was changed by this audit; the only requested write is this Markdown report.
- No external deployment, Git push, database migration, or destructive backup/restore operation was performed.
- The report does not treat intentional UI placement of Help, Symbols, Messages, or the hamburger/back controls as a defect.
- Direct messages are described as encrypted at rest, not end-to-end encrypted between devices; this is an architectural limitation to document, not an automatic finding by itself.
- Browser-only SEB/proctoring signals cannot provide OS-level anti-cheat guarantees. The finding is that the current implementation overstates or trusts those signals; an explicit threat-model decision is still required.
- Public exam metadata listing may be intentional, but assignment/visibility policy should be explicitly confirmed before changing it.
- Provider-specific free-tier availability changes over time. The concrete finding is that the current code accepts paid-provider identifiers/arbitrary endpoints and does not enforce the repository's no-paid-services policy.

## Fix progress (agent F-006–015)

Implemented:

- **F-006:** Password login now requires a valid TOTP code for enabled accounts; WebAuthn registration/authentication challenges are committed across requests; recovery-code regeneration requires second-factor proof.
- **F-007:** Internal reset requests are rate-limited, generically routed, limited to active role-valid relationships, and approval actions are single-use/atomic with password-policy and credential invalidation checks.
- **F-008:** Reset tokens are stored as digests, reset links use the configured HTTPS frontend origin and URL fragments, and password reset invalidates refresh credentials.
- **F-009:** Recovery codes now use 128-bit CSPRNG values and keyed digests, while legacy hashes remain verifiable for migration.
- **F-010:** Answer response, randomized-question, randomized-options, and submission-feedback fields are registered for database field encryption.
- **F-011:** Production/staging fail closed without database encryption, new ciphertext uses a versioned envelope, invalid ciphertext raises a storage error, and unsupported production SQLite encryption is rejected.
- **F-012:** Startup/install schema assurance now uses a transactional migration ledger, known security/data transforms, and required-model preflight validation.
- **F-013:** External-AI paths use a fail-closed privacy gateway; OCR no longer fabricates recognized text when unavailable, and local deterministic archive grading may continue without an external boundary.
- **F-014:** Exam authoring/import/export paths require an approved teacher or administrator through a shared policy.
- **F-015:** Exam start/submit require student role for real attempts, owner-only teacher previews, and server-authoritative deadlines with accommodation multipliers.

Deferred/residual:

- Full unauthenticated WebAuthn login transactions, device/session-bound challenges, passkey deletion re-authentication, and a complete per-device refresh-session model remain future work.
- Historical plaintext recovery/reset/AI-key rows require an operator-managed re-encryption/cleanup migration; schema preflight still intentionally refuses unknown indexes/constraints rather than guessing destructive changes.
- SQLCipher production support, Presidio model availability/operational deployment, assignment/tenant authorization, and broad outbound-provider/SSRF controls remain outside this fix slice.
- Existing legacy tests that create exams with default student fixtures and file-based SQLite tests that run isolated without the shared setup fixture need fixture cleanup/update; focused security regressions and the portal build were run through the mandated verification paths.

## Appendix: files reviewed (grouped)

### Backend security, auth, and application core

- `src/plannededucation/api/auth.py`
- `src/plannededucation/api/routes_auth.py`
- `src/plannededucation/api/main.py`
- `src/plannededucation/api/database.py`
- `src/plannededucation/api/db_encryption.py`
- `src/plannededucation/api/crypto.py`
- `src/plannededucation/api/models.py`
- `src/plannededucation/api/schemas.py`
- `src/plannededucation/api/schema_ensure.py`
- `src/plannededucation/api/limiter.py`
- `src/plannededucation/api/seb_security.py`
- `src/plannededucation/api/deployment_config.py`
- `src/plannededucation/api/email_service.py`
- `src/plannededucation/api/backup_service.py`
- `src/plannededucation/api/archive_utils.py`

### Backend routes and services

- `routes_exam.py`
- `routes_chat.py`
- `routes_parent.py`
- `routes_notifications.py`
- `routes_admin.py`
- `routes_archive.py`
- `routes_alerts.py`
- `routes_anonymizer.py`
- `routes_ai.py`
- `routes_packages.py`
- `routes_ocr.py`
- `routes_ocr_review.py`
- `routes_stt.py`
- `routes_proctoring.py`
- `routes_chatgpt.py`
- `ai_providers.py`
- `ocr_service.py`
- `handwriting_service.py`
- `stt_service.py`
- `chatgpt/token_store.py`, `chatgpt/crypto.py`, `chatgpt/history_store.py`

### Portal authentication, shell, exams, messaging, and privacy-sensitive UI

- `web/apps/portal/src/api.ts`
- `contexts/AuthContext.tsx`
- `contexts/I18nContext.tsx`
- `contexts/ExamContext.tsx`
- `contexts/SpecialCharactersContext.tsx`
- `contexts/ToastContext.tsx`
- `App.tsx`
- `components/ProtectedRoute.tsx`
- `components/Layout.tsx`
- `components/MessageIcon.tsx`
- `components/ChatOverlay.tsx`
- `components/SecureChat.tsx`
- `components/NotificationBell.tsx`
- `pages/Messages.tsx`
- `pages/Login.tsx`
- `pages/Register.tsx`
- `pages/ResetPassword.tsx`
- `components/ForgotPasswordModal.tsx`
- `pages/TakeExam.tsx`
- `hooks/useOfflineExam.ts`
- `services/offlineExam.ts`
- `services/offlineSync.ts`
- `hooks/useOfflineSync.ts`
- `components/ProctoringSession.tsx`
- `components/GDPRConsentModal.tsx`
- `hooks/useProctoring.ts`
- `services/proctoring.ts`
- `pages/Settings.tsx`
- `components/TwoFASettings.tsx`
- `components/PasskeysSettings.tsx`
- `components/AIKeySettings.tsx`
- `components/ChatGptPanel.tsx`
- `pages/TeacherClasses.tsx`
- `pages/TeacherExams.tsx`
- `pages/ExamEditor.tsx`
- `pages/AIGradingUpload.tsx`
- `pages/ParentDashboard.tsx`
- `pages/AdminDashboard.tsx`
- `components/TeacherApprovalPanel.tsx`
- `components/CreateUserModal.tsx`
- `components/DatabaseBackupPanel.tsx`
- `components/DeploymentConfigPanel.tsx`
- `components/FAQChatbot.tsx`
- `components/SpecialCharactersPicker.tsx`
- `components/StudentSubmissionReview.tsx`
- `components/WatermarkOverlay.tsx`
- `locales/en/messages.json`

### Install, deployment, backup, Docker, monitoring, and CI

- `install.ps1`
- `install.sh`
- `scripts/deploy/deploy_wizard.py`
- `scripts/deploy/deploy_docker.sh`
- `scripts/deploy/setup_admin.py`
- `scripts/backup/backup_restore.ps1`
- `scripts/backup/backup_restore.sh`
- `scripts/backup_restore_drill.sh`
- `scripts/backup_restore_drill_deployed.yml`
- `scripts/dev/start.ps1`
- `scripts/dev/start_student.ps1`
- `scripts/dev/stop_student.ps1`
- `config/deployment.json`
- `.env.example`
- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `web/apps/portal/nginx.conf`
- `monitoring/prometheus.yml`
- `monitoring/alertmanager.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/security-checks.yml`
- `.gitleaks.toml`

### Tests read as behavior evidence and coverage evidence

- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_auth_flows.py`
- `tests/test_admin_password_reset.py`
- `tests/test_teacher_quick_reset_and_backups.py`
- `tests/test_teacher_aide_and_messaging.py`
- `tests/test_chat.py`
- `tests/test_routes_parent.py`
- `tests/test_notifications_and_teacher_approval.py`
- `tests/test_routes_admin.py`
- `tests/test_routes_archive_and_ai.py`
- `tests/test_routes_exam.py`
- `tests/test_exams.py`
- `tests/test_routes_ocr.py`
- `tests/test_routes_proctoring.py`
- `tests/test_routes_stt.py`
- `tests/test_routes_anonymizer.py`
- `tests/test_chatgpt.py`

### Plans and policy documents read

- `AGENTS.md`
- `.copilot/skills/README.md`
- `.copilot/skills/code-review.md`
- `.copilot/skills/universal-tester.md`
- `plans/security_audit_2026.md`
- `plans/2026-11-06_SECURITY_MESSAGING_NOTES.md`
- `plans/2026-11-06_PENDING_VERIFY.md`
- `plans/2026-11-06_AGENT_WORK_STATUS.md`
- `plans/PLANS_UPDATED.md`
- `docs/GITHUB_FREE_TIER.md`

## Fix progress (parent agent — Critical + containment)

Updated: 2026-11-06 ~22:00 Europe/Budapest

### Fixed (verified in pytest cache suites)
- **F-001** SEB: removed unconditional `dev-bypass` header accept (`seb_security.py`)
- **F-002** Archive admin routes: `Depends(require_admin)` on admin surfaces
- **F-003** `is_superadmin` column + schema_ensure; `require_superadmin`; create-admin gates; setup_admin bootstrap
- **F-004** AI submission ownership + teacher/admin gates on grade/download/return/bulk
- **F-005** Access-token `type==access` required in REST + WebSocket auth
- **F-006** (TOTP login): password login challenges when `totp_enabled` (`2FA_REQUIRED`)
- **F-007** (partial): rate-limit internal reset; active parent links; single-use consume
- **F-013** Privacy scrubber fails closed before external AI
- **F-014** Exam authoring requires approved teacher / admin (`authorization.require_exam_author`); model default `teacher_approved=False`
- **F-015** Student-only start/submit + server `deadline_at` enforcement (UTC-normalized)
- **localStorage JWT**: portal uses sessionStorage only; legacy localStorage purged on auth init
- **Bulk OCR roster FK**: materialize real student rows when roster IDs are placeholders

### Documentation (audience-separated)
- User: `docs/user/{TEACHER,STUDENT,PARENT}_GUIDE.md`, `docs/user/FAQ.md`
- Admin: `docs/admin/DEPLOYMENT_GUIDE.md`
- Developer: `docs/dev/README.md`, `docs/dev/SECURITY_ARCHITECTURE.md`
- Index note in `docs/FULL_DOCUMENTATION.md`

### Tests (2026-11-06 evening)
- `backend-proctoring-ocr-parent`: **42 passed**
- Combined auth/security/exam/archive + above: **65 passed**

### Still open (do not document as complete)
- Remaining deferred High/Medium items in the F-016+ table below
- **F-044**: bulk i18n / dd/mm/yyyy sweep (in progress)
- **F-017 further residual**: OS platform keystore / server-bound master recovery (non-extractable IDB CryptoKey ships)
- **F-019 further residual**: gaze tracking / non-Chrome face ML (Shape Detection live mode ships)

---

## Fix progress (agent F-016+)

Updated: 2026-11-06 ~22:05 Europe/Budapest

### Fixed

| Finding | Severity | File(s) changed | Notes |
|---------|----------|-----------------|-------|
| **F-025** (alert auth) | High | `routes_alerts.py` | Added `_require_admin` dep on list/detail; `_verify_webhook_secret` shared-secret Depends on webhook; configurable via `ALERT_WEBHOOK_SECRET` env var. |
| **F-026** (credential logging) | High | `email_service.py`, `routes_notifications.py` | Fallback log now emits `recipient_hash + subject` only; temp password removed from in-app notification message and from API response body. |
| **F-028** (localStorage JWT fallback) | High | `web/apps/portal/src/contexts/AuthContext.tsx` | Fixed dead migration code (moved before sessionStorage gate); `logout()` now clears both sessionStorage AND localStorage; `api.ts` already read-only sessionStorage. |
| **F-018** (proctoring auth + client telemetry) | High | `routes_proctoring.py`, `tests/test_routes_proctoring.py` | Session-by-submission via `_get_session_and_verify`; event type/severity validation; payload/batch/face_count bounds; `event_source=client_telemetry`; violation_count server policy + per-request budget. |
| **F-019** (proctoring UI state machine) | High | `ProctoringSession.tsx`, `useProctoring.ts`, `locales/en/messages.json` | Consent ≠ session start; checkboxes update options only; video always rendered + stream in effect; explicit options to `startEventRecording`; no Math.random face/gaze; labeled manual-review mode. |
| **F-020** (OCR review unauthorized mutation) | High | `routes_ocr_review.py` | All five routes (list/get/create/update/approve/delete) now deny-by-default; only teacher (exam owner), student (own result), admin/superadmin allowed. |
| **F-035** (parent relationship role check) | Medium | `routes_parent.py` | `request_relationship` requires `role=="parent"` and target `role=="student"`; `get_children_progress` requires `role=="parent"`. |
| **F-036** (unread-count route shadow) | Medium | `routes_chat.py` | Registered `/messages/direct/unread-count` static route BEFORE `/messages/direct/{partner_id}` dynamic route. Old duplicate retained as comment. |
| **F-030** (AI approval wrong endpoint) | High | `web/apps/portal/src/pages/AIGradingUpload.tsx` | `handleSaveAndApprove` now calls `POST /archive/teacher/approve` with correct payload; catch block surfaces server errors instead of swallowing as success; `handleApproveAll` uses single batch call. |
| **F-039 partial** (roster URL wrong + reset token missing) | Medium | `web/apps/portal/src/pages/TeacherClasses.tsx`, `Login.tsx`, `locales/en/messages.json` | Fixed `apiClient.get('/auth/teacher/students')`; added `teacherResetToken` state and UI field to teacher-reset form; backend requires `reset_token` which is now sent. |
| **F-040** (AI key state loading) | Medium | `web/apps/portal/src/components/AIKeySettings.tsx`, `locales/en/messages.json` | `useEffect` now calls `GET /auth/ai-key`; `hasKey` updated after save; unimplemented providers (Anthropic, DeepSeek, Groq, Cohere, Mistral, Custom) removed from dropdown. |
| **F-017** (offline seal crypto) | High | `offlineExam.ts`, `offlineExamCrypto.ts`, `offlineExamCrypto.test.ts` | Real AES-GCM ciphertext+iv+aad; answers at rest encrypted; wrapped session keys; fail-closed verify/decrypt; canonical JSON hash. |
| **F-021** (AI upload traversal / image disclosure) | High | `routes_ai.py` | Opaque UUID names under per-teacher dirs; `Path.name` only; size/count caps; image GET authorizes via OCRReview/exam owner/admin. |
| **F-022** (SSRF via AI/package URLs) | High | `url_safety.py`, `schemas.py`, `routes_auth.py`, `ai_providers.py`, `routes_packages.py` | HTTPS public-host allowlist; block private/loopback/link-local/metadata/`file://`; reject credential-exfil patterns; Ollama loopback exception; Gemini key in header; sync fail-closed. |
| **F-023** (package path traversal) | High | `routes_packages.py` | `Path.resolve().is_relative_to(MODULES_DIR)`; upload/decompress/question caps. |
| **F-024** (archive encryption gaps) | High | `archive_utils.py`, `routes_archive.py`, `.env.example` | Always AES-GCM via `ARCHIVE_MASTER_KEY`; `compressed_data` stores ciphertext hex (not hash); restore decrypts with IV/salt. |

### Tests updated

| File | Change |
|------|--------|
| `tests/test_routes_parent.py` | Updated `_register_and_token` to accept `role`; all parent/student fixtures use explicit roles; added `test_non_parent_role_cannot_request_relationship` and `test_non_student_target_rejected` regression tests. |
| `tests/test_routes_ocr.py` | `auth_headers` fixture now registers an approved teacher (was: default student). |
| `tests/test_routes_proctoring.py` | `teacher_headers` approves teacher; F-018 event validation tests (unknown type, huge face_count, oversized batch, telemetry stamp, severity clamp, violation budget). |
| `tests/test_security_f021_024.py` | New focused suite for F-021–F-024 (**18 passed**, suite `backend-security-f021-024`). |

### Deferred residuals — status after residual wave (2026-11-06 ~22:54)

| Finding | Status | Notes |
|---------|--------|-------|
| F-017 residual (platform keystore) | **Fixed (scoped)** | Master stored as non-extractable `CryptoKey` via IDB structured clone (legacy base64 migrated). Still device-local — no OS keystore / server-bound recovery. |
| F-019 residual (real face ML) | **Fixed (scoped)** | Chrome Shape Detection `FaceDetector` when available (`live` mode); else honest `manual_review`. No Math.random / no cloud ML. Gaze still unavailable. |
| F-022 residual (DNS rebinding / IP pin) | **Fixed** | `assert_resolution_still_safe` + `make_pinned_async_client`; package/AI consumers pin IPs |
| F-024 residual (legacy archive migrate) | **Fixed** | `POST /admin/archives/migrate-legacy-encryption` + `reencrypt_legacy_plaintext_row` |
| F-006 residual (WebAuthn login) | **Fixed** | `/auth/webauthn/login/start|finish` + Login passkey button |
| F-033 residual (backup AEAD) | **Fixed** | PEBAK1 AES-GCM via `BACKUP_MASTER_KEY` (`.db.gz.enc`) |
| F-043 residual (script CSP) | **Fixed (scoped)** | Prod script-src drops `'unsafe-inline'`/`'unsafe-eval'`; style-src still needs inline CSS |
| F-044 (i18n literals) | **Fixed (scoped)** | `lib/dateTime.ts` dd/mm/yyyy helpers; audited pages (Login/Settings/TakeExam/2FA/Passkeys/NotificationBell/TeacherClasses/SpecialChars/TeacherApproval/AIGrading) use `t()` + helpers. Broader app surfaces (Admin/Chat) still have leftover locale dates. |
| F-046 (CI pass-through) | **Fixed** | Bandit `-ll` fail-closed; oxlint `-D correctness -D suspicious`; mypy fail-closed (URL validator overloads cleared last 2 errors) |
| F-048 residual (`/sync`) | **Fixed** | `routes_sync` + teacher LAN URL allowlist |
| F-049 residual (per-device refresh) | **Fixed** | `RefreshSession` table + rotate/reuse revoke + logout |
| F-050 (test coverage gaps) | **Partial** | New focused suites; full negative matrix still ongoing |
| F-052 residual (plan/FAQ claim drift) | **Partial** | Dev SECURITY_ARCHITECTURE updated to verified truth |

---

## Fix progress (residual wave — 2026-11-06 ~22:54 Europe/Budapest)

| Finding | Evidence |
|---------|----------|
| Deferred suite import fix | `tests/test_security_deferred_f027_052.py` uses `src.plannededucation` — **7 passed** |
| F-033 backup AEAD | `backend-security-backup` — **6 passed** |
| F-024 legacy migrate | `backend-security-f024-migrate` — **1 passed** |
| F-006 + F-048 + F-049 | `backend-security-f006-048-049` — **19 passed** |
| F-043 CSP | `main.py` + `nginx.conf` production script-src hardened |
| F-046 CI | `.github/workflows/ci.yml` Bandit/oxlint fail-closed |

---

## Fix progress (F-027..F-052 deferred batch) — 2026-11-06 ~22:15 Europe/Budapest

| Finding | Status | Notes |
|---------|--------|-------|
| **F-006** (WebAuthn remainder) | **Fixed (scoped)** | Passkey deletion requires TOTP when enabled |
| **F-027** | **Fixed** | Stricter slowapi on auth (60/min login+register vs prior 500); AI slowapi + daily budget; no paid CAPTCHA (documented) |
| **F-029** | **Fixed** | WS `type` contract; SecureChat URL resolve; lifespan Redis start/stop fail-closed; active submission only |
| **F-031** | **Fixed** | No predictable admin/JWT defaults; password omitted from disk credential files |
| **F-032** | **Fixed** | deploy_wizard argv-only; DB encryption keys; setup_admin; backup_restore no Invoke-Expression |
| **F-033** | **Fixed (partial)** | No credential fallback dumps; filename-only API paths |
| **F-034** | **Fixed** | Compose requires DB encryption + Redis chat env |
| **F-037** | **Fixed** | Lounge/`is_teacher_aide`; admin revoke via `is_admin`; lounge pagination |
| **F-038** | **Fixed** | OCR/STT size/batch caps + thread-pool offload + slowapi |
| **F-041** | **Fixed** | SMTP patch semantics; header fields; CORS before write |
| **F-042** | **Fixed** | Metrics disabled by default; loopback bind; low-cardinality labels |
| **F-043** | **Fixed (partial)** | Prod drops `unsafe-eval`; CORS rejects `*` / hostile prod HTTP |
| **F-045** | **Fixed** | Native value setter for React-controlled insert |
| **F-047** | **Fixed** | Demo roster removed; no localStorage roster PII |
| **F-048** | **Fixed (partial)** | Queue payload includes examId/studentId |
| **F-049** | **Fixed (partial)** | Password change + `/auth/logout` clear refresh hash |
| **F-051** | **Fixed** | Minimal public `/health`; detail health auth-gated |
| **F-052** | **Fixed (partial)** | `.env.example` cost/Redis/metrics aligned; compose network drift fixed |

---

## Fix progress (parent — remaining deferred wave, 2026-11-06 ~22:08)

### Fixed this wave
- **F-016**: `routes_exam._exam_start_response` / `_build_exam_package` return authoritative `exam_package` + `server_time`. Portal `useOfflineExam` fails closed if package missing/malformed (no more invented `require_seb: false` / 60-minute fallback). Verified with `test_start_and_submit_exam_dev_bypass` + deadline security test.

### Fixed this wave (continued)
- **F-017**: `offlineExamCrypto.ts` + `offlineExam.ts` — AES-GCM `{ciphertext,iv,version,aad}` envelope + answers; recursive canonical `contentHash`; fail-closed verify/decrypt; answers encrypted at rest; session keys wrapped (non-extractable in memory). Vitest under `web/apps/portal`.

### In progress (parallel agents)
- F-018 remainder + F-019 proctoring UI
- F-021–F-024 file/SSRF/archive
- F-027+ remaining Medium/High batch
