# Pending-item verification — 2026-11-06

Scope: older `TODO_LIST.md` F–J items. **No fresh deploys / no test runs** (per user).

## Verified DONE (already implemented)

| ID | Item | Evidence |
|----|------|----------|
| F1 | pip-audit | `.github/workflows/ci.yml` + `security-checks.yml` |
| F2 | No plaintext secrets / no hardcoded paths in AGENTS.md | `AGENTS.md` §1 bullets present |
| F3 | Rate limits only on auth-sensitive routes | Only `routes_auth.py` uses `@limiter.limit` (register/login/refresh/password-reset/teacher-reset). No limits on general API routes. |
| F4 | Cryptography vuln ignore | No `--ignore-vuln` in CI; `cryptography>=50.0.2` upgrade documented in `PLANS_UPDATED.md` |
| F6 | Update documents | Phase docs + `PLANS_UPDATED.md` reflect 2026-10 work |
| G2 | Editable `config/deployment.json` | Implemented |
| G3 | Admin deployment config UI | `DeploymentConfigPanel.tsx` in Admin Dashboard |
| G4 | Backup config button | `handleBackupConfig` in DeploymentConfigPanel |
| H1 | i18n migration | Phase 27 completed; ongoing new strings use `t()` (incl. 2026-11-06 finish pass) |
| H3 | AGENTS.local.md backup | **Fixed this pass** — copied from current `AGENTS.md` (was stale/smaller) |
| I1–I7 | Teacher approval, notifications, Google/2FA, password reset, email, OTP | Present in `routes_auth.py` / `routes_admin.py` / `email_service.py` |
| J1 | Separate backend error log | `main.py` writes `backend_error.log` |
| A–E, K | Aide / lounge / special chars / DMs | Done (see `2026-11-06_AGENT_WORK_STATUS.md`) |

## Intentionally skipped (user: no testing / no fresh deploys)

| ID | Item |
|----|------|
| G1, G5–G7 | Fresh GH install / uninstall / WSL matrix |
| J4 | Visual overlap testing |
| — | Fresh default-folder install + merge-to-main after alerts |

## Residual / needs your OK (not auto-done)

| ID | Item | Notes |
|----|------|-------|
| F5 | Root one-off cleanup | Still **tracked** on GitHub: `extract_faq.py`, `hungarian_university_contacts.md`. Backed up to `scratch/one_off_backup_2026-11-06/`. Also **26 tracked+gitignored** files under `docs/dev/` + `docs/admin/runbooks/` (should be `git rm --cached` per §11 — needs your approval). |
| F7 | Problems-tab screenshot fixes | No screenshot available in plans; cannot action. |
| H2 | Full scripts/docs/FAQ/modules audit MD | Light verify done in this file; deep content audit deferred. |
| — | Commit today’s WT finish pass | Still uncommitted until you ask. |

## Rate-limit note (F3)

Current limits are only on auth routes (good). Values are generous on login/register (`500/minute`). If you want stricter login-only numbers later, say so — that touches auth policy (§3).
