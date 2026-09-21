# PlannedEducation - Agent Instructions

Root operational guardrail contract for AI agents and human contributors.
Canonical source: `AGENTS.md`. Copilot mirror (when present): `.github/copilot-instructions.md`.

Product: **PlannedEducation** — a teacher's aid/grader software and locked-down test-taking environment, eventually providing job statistics and inspiration. Open source, cross-platform (Windows, Linux, Apple later) executable locking the computer to prevent cheating.

---

## 1. Project Overview & Environments

- **User Portal / App**: React + TypeScript + Vite (`web/apps/portal`).
- **Admin Portal**: React + TypeScript + Vite (`web/apps/admin`).
- **Menu & UI Style**: Follows the WIWM menu system style (Vite, hamburger menu style, theming support via `theme_mode` / `skin_id`). Place every setting into submenus under Settings.
- **Desktop Executable**: Wrapped via Electron/Tauri/capacitor to run on PC (Windows/Linux) to lock the window and monitor running apps to prevent cheating.
- **Backend API**: Python FastAPI (`src/plannededucation/api`).
- **Python venv**: `C:/.venv/Scripts/python.exe` (**always** use `C:/.venv` — do not create a project-local venv).
- **Path convention**: Use repository-relative paths (`web/apps/...`, `src/...`, `plans/...`, `docs/...`).

---

## 2. Approvals & Guardrails (MUST ASK FIRST)

Stop and get **explicit user approval in the same turn** before running commands for:

1. **Instructions & Config**: Modifying `AGENTS.md`, `.github/copilot-instructions.md`, hosting config (`firebase.json`, CSP headers/rewrites), or CI deploy workflows.
2. **Auth & Database**: Altering auth flows, session rules, database schemas, migrations, or security rules.
3. **Cloud Cost & Hosting**:
   - Deploys / rollbacks / clones
   - Managed DB always-on policies, tier changes, start/stop
   - Secret Manager writes or IAM mutations
4. **GitHub Paid Features (Strictly Forbidden)**: Do not use any GitHub paid features. Free path only. Never automatically enable anything that is a paid feature.
5. **Deployments**: Online promotes, CI/CD deploys.
6. **Data Loss**: Removing or overwriting user data, broad file deletions.

*Rule Violations:* If a rule prevents fulfilling a request, explicitly cite the rule to the user instead of bypassing it.

---

## 3. Deployment & Promotion Workflow

Canonical runbook: `docs/DEPLOYMENT_PROMOTION_RUNBOOK.md`

- **Build once, promote the same release ID** — portal ZIP (+ optional backend digest) in Artifact Registry.
- **Pipeline:** local tests → AR build → promote **smoke env** → human OK → promote **same** release to **production**.
- **Post-Deploy Verification**: Always hard-refresh browser tabs after deployment.
- **Dependabot (mandatory)**: Run Dependabot wait/fix whenever a push or promote can trigger it.

---

## 4. Security & Data Protection

- **Best / latest security by default**: When writing or changing code, prefer current best practice for auth, crypto, transport, storage, and dependency hygiene (OWASP ASVS / Top 10 current, Web Crypto AES-GCM, parameterized ORM, hashed API keys, short-lived tokens, least privilege). Do not introduce known-weak schemes.
- **No sensitive plaintext at rest or in transit**: Never store or send passwords, refresh tokens, API keys, private keys, or TOTP secrets in cleartext in DB, Drive app folders, localStorage, logs, artifacts, or API responses. Encrypt at rest; use TLS for transport.
- **Secrets**: Never commit secrets, tokens, private keys, credential JSONs, or DB files. Use placeholders (`<api-key>`) in docs.
- **Auth Boundaries**: Functional endpoints must enforce auth, scope, and rate limits.
- **SQL Safety**: Parameterize all queries via ORM/expression APIs. Never build SQL with string concatenation or manual escaping.
- **App Lockdown & Monitoring**: The exam taking application must run natively and forcefully lock out task switching, prevent cheating, detect virtual machines/screen sharing, and require teacher/admin passwords for accidental restarts.
- **Logging**: Never log passwords, refresh tokens, API keys, TOTP secrets, or OAuth client secrets.

---

## 5. Development & UI Conventions

- **Portal Build**: `cd web/apps/portal && npm run build`
- **Terminal Hygiene**: Keep max 1 backend and 1 portal preview.
- **Product UI Rules**:
  - **Time**: Under 60s → seconds only (`45s`). 60s+ → minutes + seconds (`2m 15s`).
  - **Dates**: Always `dd/mm/yyyy`.
  - **Errors/Status**: Render inside the relevant section/card, near submit buttons.

### 5.1 File size & modularity (guideline)

Prefer **short, one-concern files** composed by imports. Split at **logical turning points** (UI section, hook, service topic, route group).

| Band | Lines | Guidance |
|---|---|---|
| **Prefer** | **≤ ~400** | Sweet spot for most new `.py` / `.ts` / `.tsx` implementation files |
| **Fine** | **~401–600** | Normal when a unit is still one clear concern; split when a second concern appears |
| **OK if justified** | **> ~600** | Allowed when keeping one cohesive module is clearer than a forced split |
| **Smell** | **≫ ~800–1000+** | Strongly prefer a split unless justified |

### 5.2 English-first in development (code, paths, docs, chat)

- **English is the default language for development work**: source identifiers, folder/file names, scripts, comments, commit messages, and agent↔human chat.

---

## 6. i18n Rules

- **English First**: Add all user-facing strings to English locales first.
- **No Hardcoded UI Text**: Never write user-visible text directly in JSX, Python templates, or API error messages.
- **No Full Locale Re-sort**: For small string adds, insert/update only the needed keys. Do **not** rewrite locale JSON via alphabetical full-file reordering. Preserve existing key order.

---

## 7. Testing & Verification

- **Python**: Always invoke via `C:/.venv/Scripts/python.exe`.
- **Frontend**: Prefer Vitest + Playwright smoke.
- **Never claim “done”** without stating what was run and the observed result.

---

## 8. Documentation & Plan Discipline

- **Audience separation (mandatory)** — every new or changed doc/copy belongs in exactly one corpus (derived from ELA methodology):

  | Corpus | Where | Content |
  |---|---|---|
  | **Users + FAQ** | Portal Help/FAQ, `docs/public-user/` | Product English only — what end users (students/teachers) can do |
  | **Admins + admin FAQ** | Admin Help, `docs/admin-user/` | Operator English only |
  | **Dev / Plan** | `docs/` root, `docs/ai-internal-functional/`, `plans/` | How it works / wiring / local scripts / plans |

- **Never** put eng/ops/debug wording into Users or Admins corpora, portal UI strings, or Help/FAQ.
- **How-it-works** stays in **Dev / Plan** only.
- **Plan Tracking**: Maintain plans in `plans/` (like `plans/plans.md`).
- **Git Hygiene**: Commit cleanly. Main branch is reserved for production releases.

