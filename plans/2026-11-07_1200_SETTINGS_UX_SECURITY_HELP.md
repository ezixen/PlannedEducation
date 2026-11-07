# Settings UX, Security, Help & Info Icons — Task Plan

**Created:** 2026-11-07 12:00 (UTC+1)  
**Updated:** 2026-11-07 12:30 (UTC+1)  
**Status:** done-tested-working (local deploy + Canary windowed sweep)  

### Follow-up — recovery codes policy
Recovery / emergency codes are **one-time** (registration or first 2FA enroll). No Admin Dashboard “Generate Fresh Emergency Codes” UI; `/admin/backup-codes*` removed; 2FA regenerate returns 410. Lost codes → supervisor password / 2FA reset.

---
**Source:** Visual follow-ups after local deploy testing (admin / settings / 2FA / help).

Statuses: `ready` | `in progress` | `blocked` | `done-tested-working`

---

## 0. Answers to clarify (research first)

### 0.1 Does PlannedEducation work “100% offline”?

| Claim in UI | Reality |
|-------------|---------|
| SMTP / outbound email is optional | **True** — password reset via supervisor approval or recovery codes works without SMTP. |
| “Works 100% offline” | **Misleading as absolute.** Core app can run on a **LAN / air-gapped school network** with local SQLite/Postgres, no cloud required. Optional AI keys, OAuth/Google login, and SMTP need outbound network when enabled. |

**Decision (product copy):** Soften wording — avoid “100% offline” as a blanket claim.

| Task | Status |
|------|--------|
| Soften DeploymentConfig SMTP / offline copy (en + i18n keys) | done-tested-working |

### 0.2 Is username used?

| Use | Notes |
|-----|-------|
| DB column + uniqueness | Yes — auto-derived from email local-part on register if omitted |
| Login | Email **or** username accepted on some flows |
| Settings field | Was a **mislabeled phone field** — removed from Personal Details |

| Task | Status |
|------|--------|
| Remove username/phone field from Settings personal form | done-tested-working |
| Confirm login still prefers email; leave API username intact | done-tested-working |

---

## 1. Security settings IA

| Task | Status | Notes |
|------|--------|-------|
| Move **Passkeys** under **Security** (sibling section after 2FA) | done-tested-working | Top-level Passkeys tab removed |
| Keep 2FA + Passkeys as subsections of Security | done-tested-working | Verified Canary screenshot |

---

## 2. 2FA QR + recovery codes layout

| Task | Status | Notes |
|------|--------|-------|
| QR encodes real `otpauth://totp/...` | done-tested-working | Frontend `qrcode` package |
| Recovery codes wrap in windowed mode | done-tested-working | Flex-wrap |
| Windowed-mode visual sweep | done-tested-working | §8 |

---

## 3. Privileged reset: password vs 2FA (separate)

| Task | Status | Notes |
|------|--------|-------|
| API `POST /admin/users/{id}/reset-2fa` | done-tested-working | No schema migration |
| UI separate Reset Password + Reset 2FA buttons | done-tested-working | Admin Users row |
| Tests pwd-only leaves 2FA; 2FA-only leaves password | done-tested-working | `tests/test_admin_password_reset.py` (7 passed) |
| Audit log / notification to target user | ready | Optional follow-up |

---

## 4. Help opens in a new page/tab

| Task | Status | Notes |
|------|--------|-------|
| Dedicated `/help` route | done-tested-working | `pages/Help.tsx` |
| Hamburger Help → new tab | done-tested-working | `target=_blank` |
| Remove Layout FAQ overlay | done-tested-working | |

---

## 5. Info “i” icons (admin + teacher)

| Task | Status | Notes |
|------|--------|-------|
| `<InfoTip>` component | done-tested-working | |
| Admin Deployment (email, SMTP, anonymizer, home-exam, support email) | done-tested-working | 5 tips counted on Config tab |
| Teacher Classes DM tip | done-tested-working | |
| Packages + ExamEditor SEB / home-exam tips | done-tested-working | |
| i18n `info.*` + fill_missing | done-tested-working | 1697 keys |

---

## 6. Copy / i18n follow-ups

| Task | Status |
|------|--------|
| Soften offline claim keys | done-tested-working |
| New info.* / help.* keys filled across locales | done-tested-working |

---

## 6b. Language selector (windowed mode)

| Task | Status | Notes |
|------|--------|-------|
| Shorten English menu label to `EN - UK/US English` | done-tested-working | |
| Shorten other locale labels | done-tested-working | |
| Closed trigger shows compact code (`EN`) in header/login pill | done-tested-working | Full name remains in open list |
| Open menu viewport-clamped (fixed + measured coords) | done-tested-working | Canary: 900×700, 1024×768, 1280×720, 1366×768 — `clipped=false`, ~16px right gutter |

---

## 7. Visual / windowed-mode regression (§8 log)

Chrome Canary CDP `:9222` against `C:\PlannedEducation` preview `:5173` + API `:8000`.

---

## 8. Defect / run log

| When | Area | Result | Notes |
|------|------|--------|-------|
| 2026-11-07 12:00 | Plan created | — | From screenshots 1–4 |
| 2026-11-07 12:15–12:40 | Core UX batch | coded | Settings / QR / Help / resets / offline copy |
| 2026-11-07 12:16 | Lang menu (absolute) | still clipped in IDE browser | Switched to fixed+clamp |
| 2026-11-07 12:18 | Canary lang sizes | pass | 4 sizes, no clip |
| 2026-11-07 12:20 | Authed windowed sweep | pass | Settings personal/security/AI, admin, classes — overflowX=0; no username; no Passkeys top tab |
| 2026-11-07 12:22 | Admin users | pass | Reset Password + Reset 2FA both present |
| 2026-11-07 12:24 | Admin config InfoTips | pass | 5 `.pe-info-tip-btn` |
| 2026-11-07 12:25 | Compact header trigger | pass | Trigger `EN`; menu `EN - UK/US English` |

Artifacts: `artifacts/visual-lang-sizes/`, `artifacts/visual-windowed-sweep/`.

---

## 9. Done criteria

- [x] Offline copy accurate (no false “100% offline”)
- [x] Settings personal: name + email only (no username field)
- [x] Passkeys nested under Security with 2FA
- [x] TOTP QR works in Google Authenticator; recovery codes wrap
- [x] Separate password reset vs 2FA reset for privileged operators
- [x] Help opens as dedicated page in new tab
- [x] Info tips on key admin/teacher controls, i18n’d
- [x] Windowed visual check logged; blockers fixed
- [x] Local redeploy to `C:\PlannedEducation` (preview + API); GH push only if requested
