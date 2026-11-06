# PlannedEducation — Todo List (updated 2026-11-06)

**Sources:** VS Code + Antigravity chat history; verified against codebase (no fresh deploy / no test runs this pass).  
**Detail reports:** [`2026-11-06_AGENT_WORK_STATUS.md`](./2026-11-06_AGENT_WORK_STATUS.md), [`2026-11-06_PENDING_VERIFY.md`](./2026-11-06_PENDING_VERIFY.md)

---

## Still open (real residuals)

| # | Request | Status | Notes |
|---|---------|--------|-------|
| R1 | Commit today’s aide/lounge/messaging/special-chars finish pass | ✅ DONE | Committed on `dev` (push not requested) |
| R2 | Untrack/remove root one-offs from GitHub | ✅ DONE | Removed `extract_faq.py`, `hungarian_university_contacts.md`; backed up under `scratch/one_off_backup_2026-11-06/` |
| R3 | Untrack gitignored-but-still-tracked docs | ✅ DONE | `git rm --cached` for `docs/dev/` + `docs/admin/runbooks/` (26 files); local copies kept; backup under `scratch/tracked_ignored_backup_2026-11-06/` |
| R4 | Problems-tab screenshot fixes (F7) | ⏸️ BLOCKED | No screenshot in plans; provide image if still needed |
| R5 | Deep scripts/docs/FAQ/modules audit report (H2) | ⏸️ DEFERRED | Light verify done; full content audit optional |

---

## Explicitly skipped for now (your call)

- Fresh GH install / uninstall / WSL matrix (G1, G5–G7)
- Visual overlap testing (J4)
- Merge to `main` / alert wait cycles

---

## Verified DONE (was listed pending — already in code)

### A–E, K (today’s feature stream)
Teacher aide nominate/approve/share · Teachers’ lounge directory DMs · Special characters picker (+ module sets) · Encrypted direct messaging UI · SMTP/admin support email config

### F. Security & Compliance
| # | Status |
|---|--------|
| F1 pip-audit in CI | ✅ |
| F2 No plaintext secrets / no hardcoded paths in AGENTS.md | ✅ |
| F3 Rate limits only on auth-sensitive routes | ✅ |
| F4 Crypto vuln handling (upgrade; no CI ignore) | ✅ |
| F6 Docs updates from Oct work | ✅ |

### G. Deployment UI (not re-tested)
| # | Status |
|---|--------|
| G2 Editable deployment.json | ✅ |
| G3 Admin deployment config panel | ✅ |
| G4 Backup config button | ✅ |

### H. I18n & local agent files
| # | Status |
|---|--------|
| H1 Portal i18n migration (Phase 27 + later) | ✅ |
| H3 AGENTS.local.md backup synced to AGENTS.md | ✅ (fixed 2026-11-06) |
| H4 Local file protection rules | ✅ |

### I. Auth & Notifications
| # | Status |
|---|--------|
| I1–I7 Teacher self-reg + approval, admin notifs, Google/2FA, password reset, in-app + email, OTP/recovery | ✅ |

### J. Other
| # | Status |
|---|--------|
| J1 Separate backend error log | ✅ |
| J2/J3 Historical push/backup ops | ✅ / N/A (ops) |
| J5/J6 Temp cleanup / close files | ✅ / N/A |

---

## Legend
- ✅ DONE — verified in codebase this pass  
- ⏳ WAITING / NEEDS OK — needs your go-ahead  
- ⏸️ BLOCKED / DEFERRED — cannot finish without input or explicitly postponed  
