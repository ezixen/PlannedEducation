# PlannedEducation — Todo List: All User Requests (VS Code Chat History)

**Source:** VS Code agent chat history (transcript.jsonl), Oct 3 2026 – Nov 6 2026  
**Most recent request:** Nov 6 2026 — "check vs code chat history and state of code... finish any that are missing or fix mistakes the other agent might have made"

---

## A. Teacher's Aide Nomination System (in progress — from progress_log.md)

| # | Request | Status | Details |
|---|---------|--------|---------|
| A1 | TeacherAideRequest schema | ✅ DONE | Added to `schemas.py` |
| A2 | POST /teacher-aide/request endpoint | ✅ DONE | Added to `routes_auth.py` — creates InAppNotification for admins |
| A3 | Teacher's aide model fields | ✅ DONE | `is_teacher_aide`, `aide_approved_by`, `aide_approved_at`, `aide_approved_by_teacher_id` already on User model |
| A4 | Teacher's aide approve/revoke/list/share routes | ✅ DONE | Already in `routes_auth.py` |

---

## B. Teacher's Lounge Messaging System

| # | Request | Status | Details |
|---|---------|--------|---------|
| B1 | TeacherLoungeMessage model | ✅ DONE | Added to `models.py` |
| B2 | Lounge message schemas | ✅ DONE | Added to `schemas.py` |
| B3 | Louse message routes | ✅ DONE | Added REST endpoints to `routes_chat.py` |

---

## C. Admin Email Configuration

| # | Request | Status | Details |
|---|---------|--------|---------|
| C1 | Admin email config (SMTP settings) | ✅ DONE | Already in `deployment_config.py` + `/config` API endpoints in `routes_admin.py` |
| C2 | Email config schemas | ✅ DONE | `DeploymentConfigSchema` already includes SMTP fields |
| C3 | Email config routes | ✅ DONE | GET/PUT `/config` in `routes_admin.py` |
| C4 | Email service | ✅ DONE | `email_service.py` supports Brevo, SMTP, and console mock |

---

## D. Special Characters Picker (Frontend)

| # | Request | Status | Details |
|---|---------|--------|---------|
| D1 | Special characters picker component | ✅ DONE | Created `SpecialCharactersPicker.tsx` in `web/apps/portal/src/components/` with i18n keys |

---

## E. Testing & Commit (from progress_log.md)

| # | Request | Status | Details |
|---|---------|--------|---------|
| E1 | Test all features | ⏳ IN PROGRESS | Verify all features work correctly (ruff + tsc passed) |
| E2 | Commit and push | ⏳ PENDING | Commit changes and push to dev branch |

---

## F. Security & Compliance (from chat history)

| # | Request | Status | Details |
|---|---------|--------|---------|
| F1 | pip audit implementation | ❌ PENDING | Implement pip audit as requested (Oct 21) |
| F2 | No plaintext secrets / no hardcoded paths in AGENTS.md | ❌ PENDING | Add rule to AGENTS.md (Oct 20) |
| F3 | No rate limits except login/password/email resend | ❌ PENDING | (Oct 21) |
| F4 | Cryptography vuln ignore temporarily | ❌ PENDING | (Oct 21) |
| F5 | Clean up root folder and one-off scripts | ❌ PENDING | Don't upload dev-testing scripts to GH (Oct 21) |
| F6 | Update all documents | ❌ PENDING | (Oct 21) |
| F7 | Fix problems from problem tab on screenshot | ❌ PENDING | (Oct 21) |

---

## G. Deployment & Installer (from chat history)

| # | Request | Status | Details |
|---|---------|--------|---------|
| G1 | Deploy from GH — users only have what's on GH, should work | ❓ NEEDS CHECK | (Oct 18) |
| G2 | Editable deployment config file (config/deployment.json) | ✅ DONE | Already implemented |
| G3 | Admin panel page to edit deployment config | ❓ NEEDS CHECK | (Oct 18) |
| G4 | Backup config file button | ❓ NEEDS CHECK | (Oct 18) |
| G5 | Install/uninstall from GH, log every step, fix issues | ❓ NEEDS CHECK | (Oct 18-19) |
| G6 | Linux installer/uninstaller via WSL | ❓ NEEDS CHECK | (Oct 19) |
| G7 | Uninstaller: list dependencies one-by-one, user chooses | ❓ NEEDS CHECK | (Oct 17) |

---

## H. I18n & Documentation (from chat history)

| # | Request | Status | Details |
|---|---------|--------|---------|
| H1 | Migrate hardcoded English user-facing text to i18n t() calls | ❌ PENDING | (Oct 20) |
| H2 | Check all scripts/docs/text/FAQ/modules, report problems to MD | ❌ PENDING | (Oct 20, Oct 30-31) |
| H3 | Update AGENTS.local.md backup | ❓ NEEDS CHECK | (Oct 19) |
| H4 | AGENTS.md rule about local file protection | ✅ DONE | Already in AGENTS.md (§11) |

---

## I. Auth & Notifications (from chat history)

| # | Request | Status | Details |
|---|---------|--------|---------|
| I1 | Teacher self-registration with admin approval | ❓ NEEDS CHECK | (Oct 18) |
| I2 | Admin notification when new teacher registers | ❓ NEEDS CHECK | (Oct 18) |
| I3 | Google register + 2FA | ❓ NEEDS CHECK | (Oct 18) |
| I4 | Admin password reset + backup codes | ❓ NEEDS CHECK | (Oct 18) |
| I5 | In-platform notifications for password reset requests | ❓ NEEDS CHECK | (Oct 18) |
| I6 | Email system for notifications | ❓ NEEDS CHECK | `email_service.py` exists |
| I7 | One-time password reset codes for everyone | ❓ NEEDS CHECK | (Oct 18) |

---

## J. Other Requests (from chat history)

| # | Request | Status | Details |
|---|---------|--------|---------|
| J1 | Backend deploy log — separate error logs, agents stop & ask at key decisions | ❓ NEEDS CHECK | (Oct 17) |
| J2 | Commit and push to GH dev and main | ❓ NEEDS CHECK | (Oct 18) |
| J3 | Mark GH dev/main as backup, delete older backups | ❓ NEEDS CHECK | (Oct 18) |
| J4 | Test visually for overlaps/text outside boxes | ❓ NEEDS CHECK | (Oct 6) |
| J5 | Clean up temp files (visual test screenshots) | ❓ NEEDS CHECK | (Oct 6) |
| J6 | Save and close all open files | ❓ NEEDS CHECK | (Oct 17) |

---

## Legend
- ✅ DONE — Verified in codebase
- ❌ PENDING — Not yet implemented
- ❓ NEEDS CHECK — Need to verify current state

---

**Next action:** Start implementing ❌ PENDING items, beginning with A1 (TeacherAideRequest schema) and A2 (POST /teacher-aide/request endpoint).