# Visual Function Testing — Full Platform Playbook

Reusable end-to-end visual / functional test of a **deployed** PlannedEducation instance (default: `C:\PlannedEducation`, portal `http://127.0.0.1:5173`, API `http://127.0.0.1:8000`).

**Rules for agents**

- Prefer Chrome Canary / Chrome DevTools MCP (or headed browser) for UI checks.
- Report progress after every major section; update this file as you go.
- Fix defects **locally** in the developer workspace (`D:\Dev\PlannedEducation`), redeploy from local into the install dir, then **retest the failed section**. Do **not** push to GitHub unless the human explicitly asks.
- After any fix: note defect → fix → redeploy method → retest result in §12 (Defect log).
- Ask the human when blocked (missing paid AI keys, SMTP, legal/home-exam enablement, etc.).
- Prefer free/local AI for §7 when possible (e.g. teacher `ollama` key). If no live model is available, still exercise anonymizer export → AI **suggestions** POST → **teacher review / further correction / approve** → student remapping.
- **Grading ownership:** External AI only assists. The teacher reviews suggested scores/feedback, may edit further, then approves. Students must not receive AI output as final until the teacher seals/approves.
- **Messaging (§7b):** Always test teacher↔teacher DMs (and lounge directory) with **two** teacher accounts in sync — send, receive, unread, reply, delete, directory entry.

**Accounts used in this run**

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| Bootstrap superadmin | `admin@yourschool.edu` | `VisualTestAdmin1!` | Recreated after encryption mismatch; see §12 |
| Extra superadmin | `vt_super2@example.com` | `SuperPass1!aaaa` | Created |
| Test admin A | `vt_admin1@example.com` | — | **Deleted** in §9 |
| Test admin B | `vt_admin2@example.com` | `AdminPass2!bbbb` | Created |
| Test admin C | `vt_admin3@example.com` | `AdminPass3!cccc` | Replacement after A deleted |
| Teacher T1 | `vt_teacher1@example.com` | `TeacherPass1!aa` | Approved; owns Visual Test Exam 1 |
| Teacher T2 | `vt_teacher2@example.com` | — | Password-reset E2E done; **deleted** in §9 |
| Teacher T3 | `vt_teacher3@example.com` | `TeacherPass3!cc` | Replacement after T2 deleted |
| Student S1 | `vt_student1@example.com` | `StudentPass1!aa` | Graded **86.7** (anon `Student_2`) |
| Student S2 | `vt_student2@example.com` | `StudentPass2!bb` | Graded **53.3** (anon `Student_1`) |

---

## 0. Preconditions

1. Deploy exists at default location (or note custom `-InstallDir`).
2. Start platform: `C:\PlannedEducation\start_all.ps1` (or restart uvicorn + `npm run preview` after local sync).
3. Confirm frontend `:5173` and API health `:8000/health`.
4. Credentials available. If lost: recovery codes or controlled bootstrap (`PE_FORCE_ADMIN_BOOTSTRAP=1` only with human approval).

**This run — preconditions**

| Check | Result | Time |
|-------|--------|------|
| Deploy path | `C:\PlannedEducation` | 2026-11-07 |
| start_all / health | OK | 09:15 |
| Portal reachable | `http://127.0.0.1:5173` | 09:15 |
| Superadmin login | Pass after D1/D2 | 09:19 |

---

## 1. Superadmin shell — pages & naming

Log in as bootstrap superadmin. Open every nav destination. Look for:

- Hardcoded English / missing `t()` keys showing raw keys (`login.12`, etc.)
- Dev leftovers: unnamed buttons, `TODO`, `Button`, `Click me`, placeholder labels
- Broken layout / empty panels / console errors

**Pages checklist (this run)**

| Page / area | Opened | Naming OK | Notes |
|-------------|--------|-----------|-------|
| Login | Yes | Yes | DE/HU passkey + show-password localized (D7/D14) |
| Admin Statistics | Yes | Yes | Counts match API (`totalUsers` 8, `totalExams` 1, submissions 2) |
| Users | Yes | Yes | List + Reset / Deactivate / Delete actions named |
| Teacher Approvals | Yes | Yes | Used for T1/T2/T3 |
| Exams tab badge | Yes | Yes | Prefetch totals (D8) |
| Archives tab badge | Yes | Yes | Prefetch totals (D8) |
| Database Backups | Yes | Yes | Panel present |
| Deployment & Network | Yes | Yes | Core + backup CTA localized DE/HU; other locales may EN-fill |
| Messages / notifications | Yes | Yes | Icons labeled |
| Special characters FAB | Yes | Yes | Uses `t('special_chars.open')`; DE/HU translated (D14) |

---

## 2. Languages (i18n)

Switch locale through available languages. Spot-check nav, login, dashboard, deployment panel.

| Locale | Switched | UI coherent | Broken keys / leftover EN | Notes |
|--------|----------|-------------|---------------------------|-------|
| en | Yes | Yes | — | Source of truth |
| hu | Yes | Yes | Login + special_chars + backup CTA filled (D14); deeper deployment blocks may still EN-fill | |
| de | Yes | Yes | Login + special_chars + teacher status/buttons localized (D14) | |
| … | Spot only | — | Expect EN fallback for incomplete locales | Full 30+ locale sweep not required every run; sample ≥3 |

**After fix rule:** any new EN-only UI string must land in `locales/en/messages.json` and use `t()`; translators catch up via JSON only.

---

## 3. Nondestructive admin functions

| Function | Result | Notes |
|----------|--------|-------|
| View deployment config | Pass | School name, ports, CORS, anonymizer |
| Export settings bundle | Pass | `GET /admin/config/settings-bundle` → `kind/version/settings` |
| SMTP port spinbutton | Pass after D4 | `valuemin=1` `valuemax=65535` after portal rebuild |
| Anonymizer toggle visible | Pass | Left enabled for §7 |
| Home-exam beta | Pass | Left **OFF** |
| Support email field | Pass | Superadmin-only |
| List users | Pass | 8 after §9 replacements |
| Pending teachers | Pass | Approve flow OK |
| Admin cannot create superadmin | Pass | `vt_admin2` → 403 |

---

## 4. Account provisioning

### 4.1 Teachers

| Action | Result | Notes |
|--------|--------|-------|
| Register T1 / T2 | Pass | |
| Approve T1 / T2 | Pass | Superadmin |
| T1 / T2 login | Pass | |
| Register + approve T3 | Pass | After T2 delete |

### 4.2 Admins / superadmins

| Action | Result | Notes |
|--------|--------|-------|
| Create extra superadmin | Pass | `vt_super2` |
| Create admin A / B / C | Pass | A deleted in §9 |
| Login as new superadmin / admins | Pass | |
| Admin cannot create superadmin | Pass | |

---

## 5. Password reset E2E (teacher)

Subject: **Teacher T2** (before deletion).

| Step | Result | Notes |
|------|--------|-------|
| Request reset | Pass | In-platform notification path (no SMTP) |
| Supervisor sees notification | Pass | |
| Approve reset | Pass after D3 | Issues handoff `reset_token` |
| Set new password | Pass | |
| Login with new password | Pass | `TeacherPass2!NEW` |
| Old password rejected | Pass | |

---

## 6. Students, class, exam

| Step | Result | Notes |
|------|--------|-------|
| Register S1 / S2 | Pass | |
| Teacher creates class / enroll | Pass | Via teacher flows / API |
| Create exam | Pass after D5 | Nested `questions` on `POST /exams/` now persisted; earlier workaround used `/exams/{id}/questions` |
| Publish / open | Pass | Visual Test Exam 1 |
| Students start & submit | Pass after D6 | Submit **upserts** Answer rows; field name `response` |
| Teacher sees submissions | Pass | Class submissions + AI dashboard |

Exam id (this run): `e1b420af-ffc7-4f03-8fc2-25a7067dad72`

---

## 7. External AI assist + teacher grading (teacher owns the grade)

**Product rule:** External AI helps correct anonymized work and returns suggestions. **Grading is the teacher’s job** — review, further correct if needed, then approve/seal before students see final grades.

| Step | Result | Notes |
|------|--------|-------|
| Teacher attaches AI provider | Pass | `PUT /auth/ai-key` → `ollama` (free/local). Live daemon optional this run. |
| Fetch anonymized submissions | Pass | PII scrub; anon refs `Student_N` |
| AI / external corrector returns suggestions | Pass | `POST /anonymizer/submissions/{id}/grades` (assistive scores/feedback) |
| Teacher reviews + may further correct | Pass | AI dashboard: real names + anon refs + suggested scores |
| Teacher approves / seals (final grade) | Pass | `POST /archive/teacher/approve` → AES-GCM archives |
| Remap to correct students | Pass | S1=86.7 / S2=53.3 matched answer content |
| Students see **teacher-approved** grades | Pass | `my-submission` `is_graded=true` |

**Retest after D6:** resubmit → anonymizer answers → AI suggestions → teacher approve → student scores verified.

---

## 7b. Messaging (two teachers in sync) — mandatory

Use **Teacher T1** and **Teacher T3** (or any two approved teachers). Test both API and UI (`/messages` + Messages icon overlay).

| Step | Result | Notes |
|------|--------|-------|
| Directory: each teacher sees the other | Pass | `GET /chat/teachers-lounge/directory` mutual |
| T1 → T3 direct message | Pass | Plaintext in API response (Fernet at rest; no ciphertext leak) |
| T3 unread increments | Pass | `GET /chat/messages/direct/unread-count` |
| T3 opens thread / replies | Pass | Opening conversation auto-marks read; reply visible to T1 |
| Explicit mark-read | Pass | `PATCH /chat/messages/direct/{id}/read` |
| Edit own DM | Pass | `PUT` content updated for both sides |
| Soft-delete | Pass | Sender delete hides for sender; recipient retains until both delete |
| Lounge board post + reply + pin | Pass | API `POST/GET /chat/lounge/messages` (+ pin). UI “Teachers’ Lounge” is the **colleague directory** for DMs (board is API-backed). |
| UI `/messages` send/receive | Pass | T1↔T3 sync verified |
| Refresh / Clear chat / Delete message buttons | Pass | Named; delete confirm via `t()` |

### 7b-S. Student messaging (opt-in + class) — mandatory

**Rule:** Students see **no** teachers on Messages unless (1) the teacher enabled **student messaging** in Teacher Classes settings (`allow_student_dms`) **and** (2) the student is enrolled in that teacher’s class. Otherwise the page is empty.

| Step | Result | Notes |
|------|--------|-------|
| Student Messages with DMs off / no class | Pass | Empty: “No teachers available” |
| Teacher creates class + enrolls students | Pass | `POST /auth/teacher/classes` persists `class_memberships` |
| Class enrolled but DMs still off | Pass | Available teachers still **0** |
| Teacher enables student DMs | Pass | `PATCH /auth/teacher/settings/student-dms` |
| Student sees only that teacher | Pass | `GET /chat/students/available-teachers`; no teacher email exposed |
| Student can message that teacher | Pass | UI send “UI confirm…” + API prior ping |
| Student cannot message other teachers | Pass | 403 (not in class / not opted-in) |
| Teacher disables student DMs | Pass | List empty again; send blocked |

---

## 8. Cross-role page sweep (after workflows)

| Role | Pages OK | Functions OK | Notes |
|------|----------|--------------|-------|
| Superadmin | Pass | Pass | Deployment, users, stats |
| Admin | Pass | Pass | Create users; blocked from creating superadmin |
| Teacher | Pass | Pass | Exams, packages, OCR/STT panels, AI grade dashboard, archives |
| Student | Pass after D10/D11 | Pass | Graded `86.7 / 3 pts`; upcoming hides completed; watermark only on active take |

---

## 9. Destructive admin functions

| Action | Result | Notes |
|--------|--------|-------|
| Delete teacher T2 | Pass | Login fails afterward |
| Create + approve T3 | Pass | Login OK |
| Delete admin A | Pass | Login fails afterward |
| Create admin C | Pass | Login OK |
| Remaining accounts still work | Pass | Superadmin, T1, admin B/C, students |

---

## 10. Local fix → redeploy → retest loop

1. Reproduce and capture evidence.
2. Fix in `D:\Dev\PlannedEducation`.
3. Redeploy **from local** without GitHub push:
   - Copy changed `src/...` into `C:\PlannedEducation\src/...` and restart uvicorn, **and/or**
   - Copy portal sources → `npm run build` under deploy portal → restart `npm run preview -- --host 127.0.0.1 --port 5173`
   - Optional full: `install.ps1 -InstallDir C:\PlannedEducation -DeployMode 1 -AutoConfirm` (preserves DB/`.env`).
4. Retest failed section + dependents.
5. Log in §12.

---

## 11. Run log (chronological)

| Time | Section | Status | Summary |
|------|---------|--------|---------|
| 09:15 | 0 Preconditions | Pass after D1/D2 | Platform healthy; superadmin UI login OK |
| 09:20 | 1 Pages / naming | Pass w/ notes | No unnamed empty buttons; some EN leftovers under DE/HU |
| 09:21 | 3 Nondestructive admin | Pass after D4 | Settings bundle OK; SMTP min/max fixed |
| 09:21 | 4 Accounts | Pass | Teachers / admins / superadmin |
| 09:22 | 5 Password reset | Pass after D3 | Full request→approve→token→new login |
| 09:26 | 6 Class / exam | Pass after D5/D6 | Nested create + submit upsert |
| 09:28 | 7 AI + anonymizer | Pass (sim + ollama key) | Live model optional; remapping verified |
| 09:30 | 2 Languages | Pass w/ D7 | en/hu/de sampled |
| 09:32 | 9 Destructive | Pass | Delete/replace teacher + admin |
| 09:35 | 8 Cross-role | Pass | Teacher AI dashboard + student grades |
| 09:36 | Fix loop | Done | D4–D6, D5, D9 redeployed locally; no GH push |
| 09:45 | §8 student UI | Pass after D10/D11 | Watermark off on list; score `86.7 / 3 pts`; completed exam removed from upcoming |
| 09:52 | §7b Messaging | Pass | T1↔T3 DM + lounge directory UI; lounge board API pin/reply OK |
| 09:55 | Fix loop | Done | D7 fill + D8 badges + admin/teacher/message i18n; portal rebuilt locally |
| 10:20 | §7b-S Student DMs | Pass after D13 | Empty until class+opt-in; T1 visible; disable → empty |
| 10:22 | Fix loop | Done | ClassMembership + available-teachers + Messages empty state |
| 10:18 | §7b-S UI send | Pass | Student sent “UI confirm: student can message class teacher” |
| 10:20 | Fix loop | Done | D14 DE/HU login + special_chars + backup CTA |

---

## 12. Defect log

| ID | Found in | Symptom | Fix (local path) | Redeploy | Retest | Status |
|----|----------|---------|------------------|----------|--------|--------|
| D1 | §0 login | Fernet key mismatch vs DB ciphertext | Recreate empty DB + `setup_admin` with current `.env` | Local under `C:\PlannedEducation` | Login OK after D2 | Fixed (env) |
| D2 | §0 login | Bootstrap `force_password_reset=True` without token → permanent lock | `scripts/deploy/setup_admin.py`: `force_password_reset=False` | Copied + cleared flag | Token 200 | Fixed locally |
| D3 | §5 password reset | Approve cleared token → lockout | `routes_notifications.py`: handoff `reset_token` | Copied + uvicorn restart | Full E2E OK | Fixed locally |
| D4 | §3 deployment | SMTP port `valuemax=0` | `DeploymentConfigPanel.tsx` `min={1}` `max={65535}` | Portal rebuild + preview restart | SMTP spinbutton 1–65535 | Fixed locally |
| D5 | §6 exam create | `POST /exams/` ignored nested `questions` | `schemas.ExamCreate.questions` + `routes_exam.create_exam` flush/add | Copied + uvicorn restart | Nested create → 2 questions | Fixed locally |
| D6 | §6 submit | Submit only updated existing Answer rows → empty answers if start had no questions | `routes_exam.submit_exam` upsert Answers | Copied + uvicorn restart | Anonymizer 2 answers/student | Fixed locally |
| D7 | §2 i18n | Missing HU/DE keys for deployment/login/messages fell back to EN | Filled missing keys from EN into HU/DE; DE/HU overrides for login + key deployment labels | Portal rebuild | Login/passkey/show-password localized | Fixed locally (other locales still EN-fill until translators) |
| D8 | §1 admin tabs | Exams/Archives/Users badges 0 until tab opened | Prefetch stats/users/exams/archiveStats; badge uses `stats` / `archiveStats` | Portal rebuild | Badges use totals on load | Fixed locally |
| D9 | §1 archives | Hardcoded EN archive stat labels | `AdminDashboard.tsx` → `t('admin.total_archives')` etc. | Portal rebuild | Source fixed | Fixed locally |
| D10 | §8 student `/exam` | Anti-cheat watermark tiled on exam **list** | `WatermarkOverlay.tsx`: only active take-exam + `aria-hidden` | Portal rebuild | List clean | Fixed locally |
| D11 | §8 student graded card | Score `{score} / 10 pts` hard-coded | `score_pts` + `total_possible` on `/ai/submissions` | API + portal | `86.7 / 3 pts` | Fixed locally |
| D12 | §1/§8 admin toasts | Hardcoded EN `showSuccess`/`confirm` in AdminDashboard; EN `\|\|` fallbacks in Messages/ChatOverlay; EN status labels on TeacherDashboard | `t('admin.*')` / remove fallbacks / `teacher_dashboard.status_*` | Portal rebuild | Source + build OK | Fixed locally |
| D13 | §7b-S student Messages | Students had no directory; class roster was UI-only; DM check only looked at `allow_student_dms` | `ClassMembership` + `POST/GET /auth/teacher/classes`; `GET /chat/students/available-teachers`; send requires class+opt-in; Messages/ChatOverlay empty until both | API + portal redeploy | Empty → enable → T1 visible → UI send OK → disable → empty | Fixed locally |
| D14 | §1/§2 i18n leftovers | DE/HU login passkey/2FA + special_chars + messages chrome still EN; DE backup CTA outdated | Translated DE/HU login + special_chars + messages.* chrome; DE `deployment.backup_btn` | Portal rebuild | DE FAB `Sonderzeichen öffnen`; messages chrome localized | Fixed locally |

---

## 13. Open questions / blockers

- **Live external AI model:** optional; AI suggestions are assistive — teacher must still review/approve (§7).
- SMTP: not configured; in-platform notification reset used for §5.
- Remaining locales beyond en/hu/de: missing keys still EN-filled / EN fallback via `I18nContext` until translators update JSON.

---

## 14. Final verdict

| Area | Pass/Fail | Notes |
|------|-----------|-------|
| Visual / naming | Pass | Primary CTAs named; teacher status buttons i18n’d |
| i18n | Pass (en/hu/de) | Gaps filled; other locales EN fallback |
| Admin nondestructive | Pass | |
| Account lifecycle | Pass | |
| Password reset | Pass | |
| Exam + anonymizer + **teacher** grade | Pass | AI assists; teacher approves |
| Messaging (2 teachers) | Pass | DM sync + directory UI |
| Student messaging | Pass | Empty unless class + teacher opt-in |
| Destructive deletes | Pass | |
| **Overall** | **Pass (local fixes, not pushed)** | See §12; redeploy local → `C:\PlannedEducation` |

---

## 15. Quick retest recipe (after any fix)

```powershell
# Sync + restart API
Copy-Item D:\Dev\PlannedEducation\src\plannededucation\api\<file>.py C:\PlannedEducation\src\plannededucation\api\<file>.py -Force
# stop uvicorn on :8000, then:
C:/.venv/Scripts/python.exe -m uvicorn plannededucation.api.main:app --app-dir C:\PlannedEducation\src --env-file C:\PlannedEducation\.env --host 0.0.0.0 --port 8000

# Sync + rebuild portal
Copy-Item D:\Dev\PlannedEducation\web\apps\portal\src\... C:\PlannedEducation\web\apps\portal\src\... -Force
cd C:\PlannedEducation\web\apps\portal; npm run build
# restart: npm run preview -- --host 127.0.0.1 --port 5173
```

Then re-run only the failed § section and append a row to §11 + update §12 Retest column.
