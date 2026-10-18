# PlannedEducation — Agent Instructions

Root operational guardrail contract for AI agents and human contributors.
Canonical source: `AGENTS.md`. Copilot mirror (when present): `.github/copilot-instructions.md`.

Product: **PlannedEducation** — free, open-source teacher's aid, grading software, and secure test-taking environment designed to provide teachers with powerful classroom management and automated grading without compromising student privacy or test integrity.

---

## 1. Project Overview & Environments

PlannedEducation operates on a 100% free/open-source and local-first architecture.

| Stage | Purpose | Frontend | API |
|---|---|---|---|
| **Local Development** | Day-to-day development & testing | `http://127.0.0.1:5173` (or `:5175`) | `http://127.0.0.1:8000` (or `:8002`) |
| **Self-Hosted / Production** | Production deployment (free-tier/self-hosted) | Static SPA / Nginx / Cloudflare Pages / Vercel Free | FastAPI / Uvicorn (Docker / K3s) |

- **Frontend Client**: React + TypeScript + Vite (`web/apps/portal`)
- **Backend API**: FastAPI (`src/plannededucation`), SQLite for dev/testing, PostgreSQL for production
- **Python venv**: `C:/.venv/Scripts/python.exe` (**always** use `C:/.venv` — do not create a project-local venv)
- **Path convention**: Use repository-relative paths (`web/apps/...`, `src/...`, `plans/...`, `docs/...`).
- **No Internal LLM**: This project has **NO internal LLMs**. All core assessment, grading algorithms, rule evaluation, and proctoring logic are deterministic, local-first, and privacy-preserving.

---

## 2. Core Principles & Free-Tier Policy (MANDATORY)

### 🚫 NO PAID SERVICES - EVER
This project MUST NEVER use or enable any paid services. All functionality must be implemented using:
- Free / open-source software
- Self-hosted infrastructure
- Genuinely free tiers of services (not trials)
- Local-first architecture

**Explicitly FORBIDDEN:**
- Paid cloud databases (AWS RDS, Azure SQL, Google Cloud SQL paid tiers)
- Paid authentication providers (Auth0, Clerk, Okta paid tiers)
- Paid email/SMS services (SendGrid, Twilio, Mailgun paid tiers)
- Paid AI/ML APIs (OpenAI, Anthropic, Google Vertex AI paid tiers)
- Paid monitoring/observability (Datadog, New Relic paid tiers)
- Paid CI/CD (GitHub Actions beyond free tier, CircleCI paid)
- Any service requiring a credit card for production use

**ALLOWED Free Services:**
- GitHub (free tier for repo, Actions: 2000 min/mo for private repos, Pages) — **Policy: `docs/GITHUB_FREE_TIER.md`**
- Google OAuth (free)
- Let's Encrypt (free TLS certificates)
- Cloudflare (free tier for DNS, Workers, Pages)
- Vercel / Netlify (free hobby tiers for frontend hosting)
- Supabase / Neon / ElephantSQL (free tiers only)
- Sentry / Grafana / PostHog (free tiers only)
- Local development tools (Docker, SQLite, PostgreSQL, Redis)

### GitHub Free-Tier Policy
**MANDATORY:** All GitHub usage must comply with `docs/GITHUB_FREE_TIER.md`.
- **Allowed:** GitHub Actions (free tier), Dependabot version updates/alerts, `pip-audit`/`npm audit` in Actions, gitleaks OSS CLI.
- **FORBIDDEN on private repos:** GitHub Secret Protection, GitHub Code Security (CodeQL, dependency review requiring Code Security, custom Dependabot auto-triage), Copilot Autofix.
- **Gitleaks:** Use upstream OSS binary only — NOT `gitleaks/gitleaks-action`.
- **Branches:** Security checks run on `main` and `dev`.

### Enforcement
Any PR introducing a paid service dependency MUST be rejected.
Any configuration enabling a paid tier MUST be reverted.
The project must remain 100% free to operate indefinitely.

---

## 3. Approvals & Guardrails (MUST ASK FIRST)

Stop and get **explicit user approval in the same turn** before running commands for:

1. **Instructions & Config**: Modifying `AGENTS.md`, `.github/copilot-instructions.md`, hosting config (`firebase.json`, headers/rewrites), or CI deploy workflows.
2. **Auth & Database**: Altering auth flows, session rules, database schemas, migrations, or security rules.
3. **Cloud Cost & Hosting**: Any cloud resource provisioning, tier changes, secret mutations, or external service binds.
4. **Deployments**: Online promotes, production deployments, or remote infrastructure changes.
5. **Data Loss**: Removing or overwriting user data, broad file deletions (`DROP TABLE`, `rm -rf`, deleting production branches).

*Rule Violations:* If a rule prevents fulfilling a request, explicitly cite the rule to the user instead of bypassing it.

---

## 4. Security & Data Protection

- **Best / latest security by default**: When writing or changing code, prefer current best practice for auth, crypto, transport, storage, and dependency hygiene (OWASP ASVS 5.0.0 / Top 10:2025, Web Crypto AES-GCM, Argon2id password hashing, pyotp TOTP RFC 6238, Fernet encryption for sensitive tokens, parameterized ORM, short-lived tokens, least privilege). Do not introduce known-weak schemes (e.g. AES-CBC without MAC, homemade crypto, MD5/SHA1 for secrets, plaintext secrets in logs).
- **No sensitive plaintext at rest or in transit**: Never store or send passwords, refresh tokens, API keys, private keys, TOTP secrets, student PII, exam answers, or session tokens in cleartext in DB, localStorage, logs, artifacts, or API responses. Encrypt at rest (server Fernet or client Web Crypto AES-GCM as appropriate); use TLS for transport.
- **Secrets**: Never commit secrets, tokens, private keys, credential JSONs, or DB files. Use placeholders (`<api-key>`, `<token>`) in docs. Keep local credentials under `local-secrets/` (gitignored). (Check `D:\dev\save\secrets`).
- **SQL Safety**: Parameterize all queries via ORM/expression APIs. Never build SQL with string concatenation, f-strings, or manual escaping. Keep DB error messages generic to clients.
- **Student Privacy & FERPA / GDPR Compliance**: Exam logs, proctoring events, and student records are sensitive educational records. Anonymizer / PII scrubber (Presidio) cleans test packages and submissions. Retention and purge policies are first-class requirements.

### 4.1 Secure coding (apply on every change)

- **Auth on functional routes**: Enforce bearer session, scope, and rate limits.
- **Browser tokens**: Prefer **httpOnly** session cookies for API auth. Mirror bearer in `sessionStorage` or request headers only when needed. **Do not** persist JWT access tokens or refresh tokens in `localStorage`.
- **Password & 2FA**: Argon2id for password hashing; TOTP (RFC 6238) with `pyotp` for 2FA; recovery codes encrypted at rest. WebAuthn/Passkeys (FIDO2) for phishing-resistant auth.
- **Fernet material**: Encryption secrets must be set and must differ from JWT secret in production. Never reuse JWT secret for encryption.
- **Logging**: Never log passwords, refresh tokens, API keys, TOTP secrets, student PII, or OAuth client secrets.
- **CSP**: Third-party scripts require strict Content Security Policy. Avoid `'unsafe-eval'`; `'unsafe-inline'` only where Vite/fonts require it.
- **DB writes**: Validate and normalize user input before persistence using Pydantic schemas. Prefer encrypted columns for sensitive credentials.
- **Critical junctions (ask first)**: Same as §3 — plus changing OAuth redirect URIs, auth token shapes, or encryption models.

---

## 5. Development & UI Conventions

- **Portal Build**: `cd web/apps/portal && npm run build`
- **Terminal Hygiene**: Keep max 1 backend (`:8000` / `:8002`) and 1 portal (`:5173` / `:5175`). Log stopped PIDs/ports.
- **Orphaned Process Prevention (MANDATORY)**: After every test run, server start, or command execution, ALL background processes MUST be terminated. Never leave node, python, vite, uvicorn, or playwright processes running after:
  - Tests complete (pass or fail)
  - You move to a different task
  - A command times out or fails
  - You are done with a session
  
  Before starting any new process, check for and kill existing orphaned processes:
  ```powershell
  # Kill orphaned node processes
  Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
  # Kill orphaned python processes (except current)
  Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {$_.Id -ne $PID} | Stop-Process -Force
  # Kill orphaned uvicorn processes
  Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
  ```
  
  **Process Timeout Rule**: Any background process that has been running for more than 30 minutes without user interaction MUST be terminated. This prevents VS Code "background commands running" counter from growing indefinitely.
  
  **VS Code Background Commands**: If VS Code shows "17 background commands running" or similar, this indicates orphaned processes from previous agent actions. Kill all node/python/uvicorn processes immediately and verify the count returns to 0.
  
  Never claim a task is complete without verifying no orphaned processes remain.
- **Branches**: Default working branch is **`dev`**. **`main`** is stable release.
- **Product UI Rules**:
  - **Time**: Under 60s → seconds only (`45s`). 60s+ → minutes + seconds (`2m 15s`). Never display milliseconds.
  - **Dates**: Always `dd/mm/yyyy` with timezone offset shown where relevant (local / UTC clearly labeled).
  - **Timeouts**: Max default timeout cap is `600,000 ms` (10 minutes).
  - **Errors/Status**: Render inside the relevant section/card, near submit buttons — not only as global toasts.
  - **Installs (Windows)**: x64 → `C:\Program Files`, x86 → `C:\Program Files (x86)`.

### 5.1 File size & modularity (guideline)

Prefer **short, one-concern files** composed by imports — easier to navigate and review. Split at **logical turning points** (UI section, hook, service topic, route group), not by arbitrary line counting.

Line counts are **guidance**, not a hard ban:

| Band | Lines (editor line count) | Guidance |
|---|---|---|
| **Prefer** | **≤ ~400** | Sweet spot for most new `.py` / `.ts` / `.tsx` implementation files |
| **Fine** | **~401–600** | Normal when a unit is still one clear concern; split when a second concern appears |
| **OK if justified** | **> ~600** | Allowed when keeping one cohesive module is clearer than a forced split (e.g. dense CSS token packs, a tightly coupled panel, a single well-scoped service). Prefer splitting at the next **logical** boundary rather than inventing fake modules |
| **Smell** | **≫ ~800–1000+** | Strongly prefer a split unless the file is excluded (below) or you document why cohesion wins |

**What to split into (patterns when splitting):**

| Kind | Put in | Example |
|---|---|---|
| React page shell | `web/apps/portal/src/pages/FooPage.tsx` | Wire state + layout only |
| UI section | `web/apps/portal/src/components/<domain>/` | `exams/QuestionEditorPanel.tsx` |
| Hook / WS / data load | `web/apps/portal/src/hooks/` | `useOfflineExam.ts`, `useProctoring.ts` |
| Pure helpers | `web/apps/portal/src/lib/` or `src/utils/` | `examStorage.ts`, `sebConfig.ts` |
| FastAPI routes | `src/plannededucation/api/<domain>.py` | Split by domain when a router grows unwieldy |
| Domain services | `src/plannededucation/services/<topic>.py` | One topic per module; import across modules |
| Schemas / models | `src/plannededucation/api/schemas.py` | Topic modules when files grow large |

**Rules of thumb:**

1. **One primary responsibility per file** when practical.
2. **Split at logical seams**, not because a counter crossed 400/600. If extending a long but coherent file is clearer, keep it together and note why if huge.
3. **New feature → new file(s)** when the feature is a distinct concern; small 1–N line fixes may stay in place.
4. **Pages compose**; prefer importing panels over megapage JSX — unless a slightly longer page shell is still the cleanest wiring layer.
5. **Do not** merge small files into a “god file” just for fewer paths; also **do not** over-split into tiny files that hurt readability.
6. **Excluded / looser**: generated code, lockfiles, vendored code, migrations, large CSS skin packs.
7. **Tests**: one focused test module per concern; split mega-suites by feature (`test_routes_*.py`, `test_auth_*.py`).

**Agent checklist before “done”:** if an edited implementation file is very large (**>~800**), briefly say so and whether you kept it for cohesion or plan a logical split next.

---

## 6. Testing & Verification System (MANDATORY)

- **Python interpreter**: Always invoke via `C:/.venv/Scripts/python.exe`.
- **Source-Aware Pytest Cache Helper (`scripts/testing/update_test_cache.py`)**:
  - **MANDATORY FOR EVERY PYTEST RUN**: Every python test invocation MUST run through `scripts/testing/update_test_cache.py`.
  - **No Pointless Retests**: Uses `--skip-if-clean` to skip re-running tests for unmodified suites when the source files and dependencies haven't changed since the last clean test run.
  - Maintains run history, git state, and SHA-256 source file signatures in `artifacts/test_cache/source_test_results.json`.
  - **Standard Invocations**:
    ```powershell
    # Run full test suite with change tracking:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-all" -- C:/.venv/Scripts/python.exe -m pytest tests/ -q

    # Run focused tests with change tracking:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-auth" -- C:/.venv/Scripts/python.exe -m pytest tests/test_auth.py -q

    # Check cache status without running tests:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --status --suite-name "backend-all"
    ```
- **Pytest Configuration (`pytest.ini`)**:
  - Logging enabled by default: `log_cli = true`, `log_cli_level = INFO`
  - Log file output to `artifacts/test_run.log` with DEBUG level
  - Test markers for categorization (tracked, slow, integration, unit, ui, auth, exam, ai, proctoring, chat, ocr, stt, archive, anonymizer, parent, admin, chatgpt)
  - Filterwarnings to suppress known deprecation warnings
- **Logged Testing Enforcement (MANDATORY)**:
  - **ALWAYS** use `scripts/testing/update_test_cache.py --skip-if-clean` wrapper for pytest runs
  - **NEVER** run raw `pytest` directly -- always wrap with the cache helper
  - Check cache status first: `scripts/testing/update_test_cache.py --status --suite-name "backend-all"`
  - If suite is clean, tests are skipped automatically -- no wasted time
  - After changes, only affected suites re-run based on SHA-256 source file signatures
  - Cache stores: run history, git state, SHA-256 source file signatures in `artifacts/test_cache/source_test_results.json`
- **Test Tracker Logger (`run_tests.py` / `test_tracker.py` / `conftest_tracker.py`)**:
  - Project test runner integrating incremental test skipping with summary reporting:
    ```powershell
    C:/.venv/Scripts/python.exe run_tests.py --summary
    ```
- **Visual Testing & Artifact Cleanup Rule**:
  - All visual testing workflows (Playwright, visual regression tests) must automatically clean up temporary files, screenshots, traces, and test databases (`test-results/`, `playwright-report/`, `artifacts/visual-test-screenshots/`, `test_visual.db`) via `globalTeardown` and cleanup scripts after runs are complete and all issues are fixed, preserving a clean workspace.
- **Never claim "done"** without stating what was run and the observed result.

---## 7. Documentation & Plan Discipline

- **Audience separation (mandatory)**:
  - Living docs in `docs/`.
  - Implementation plans in `plans/`.
  - Never put eng/ops/debug wording (scripts, `.env`, SHA fingerprints, stub tokens) into teacher/student-facing UI strings, portal help, or documentation.
- **Plan Tracking**: After substantial work, update the active plan file in `plans/` (e.g. `plans/PLANS_UPDATED.md`). Statuses: `ready`, `in progress`, `blocked`, `done-tested-working`.
- **Git Hygiene**: Check `git status --short --branch`. Day-to-day commits go on **`dev`**. Clean working tree before finishing.

---

## 8. Default Agent Workflow

1. Read this file (especially **§3 approvals**, **§4 secure coding**, **§5.1 file size**, and **§6 testing system**), and the active plan under `plans/`.
2. Prefer smallest vertical slice that ships a testable user journey.
3. TDD where practical: failing test → implement → pass → commit (when user asks for commits).
4. Prefer modular files (§5.1); split at logical seams when a file becomes hard to handle — longer cohesive files are OK when justified.

## 9. Self-Monitoring & Loop Prevention (MANDATORY)

**Monitor yourself and do not allow yourself to be stuck in a loop.**

- **Track your steps**: Before each action, log what you're about to do in a progress file (e.g., `scratch/progress_log.md`).
- **Save progress every 30 seconds**: Write intermediate state to a temp file so you can resume if interrupted.
- **Detect loops**: If you find yourself repeating the same action 3+ times with the same error, STOP. Analyze the error, change approach, or ask for clarification.
- **Break large tasks into small steps**: Each step should be completable in one tool call. If a step fails, you know exactly where.
- **Use the todo list**: Update `manage_todo_list` after each completed step to maintain visibility.
- **Verify before claiming done**: Run tests, build, or verify the actual output — never assume success.
- **If stuck**: Explicitly state what you tried, what failed, and what you'll try next. Don't silently retry the same thing.
5. Run tests via `scripts/testing/update_test_cache.py --skip-if-clean`.
6. Update plan files when finishing a chunk of work.
7. Ask before anything in §3.
8. Clean up all test artifacts/temporary files.