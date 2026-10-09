# PlannedEducation - Manual Testing Requirements

## Overview
This document lists all features that **cannot be fully automated** and require manual testing, along with the rationale and test procedures.

---

## Features Requiring Manual Testing

### 1. Safe Exam Browser (SEB) Integration
**Why not automated**: SEB is a native desktop application that launches a separate kiosk-mode browser process. Playwright cannot control or inspect the SEB client.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **SEB Config Download** | Teacher creates exam → Clicks "Download SEB Config" | `.seb` file downloads with correct `examKey` and `startURL` |
| **SEB Launch** | Double-click `.seb` file → SEB launches in kiosk mode | SEB opens in fullscreen, no address bar, no tabs |
| **SEB Navigation** | SEB loads exam start page → Student clicks "Start Exam" | Exam loads in SEB, timer starts |
| **SEB Restrictions** | Try Alt+Tab, Ctrl+Esc, Win+D, F12, Ctrl+Shift+I | All blocked, violation recorded |
| **SEB Exit** | Student clicks "Submit Exam" → SEB closes | Returns to normal OS, exam submitted |
| **SEB Crash Recovery** | Kill SEB process mid-exam → Restart SEB → Reopen `.seb` | Exam resumes from last saved answer |

**Why not automated**: SEB runs as separate OS process with kiosk mode; no WebDriver support.

---

### 2. Real-Time Student ↔ Teacher Sync

**Why not automated**: Requires two simultaneous browser sessions (student + teacher) with WebSocket connections.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Heartbeat Visibility** | 1. Teacher opens Dashboard → Exam → Monitor<br>2. Student starts exam in SEB<br>3. Teacher watches "Real-time Student Monitoring" panel | Teacher sees student status update every 10s: time remaining, current question, violations |
| **Violation Alert** | Student triggers violation (Alt+Tab) | Teacher sees violation badge immediately |
| **Auto-Submit Sync** | Student timer expires → Auto-submit | Teacher sees "Completed" status instantly |
| **Teacher Offline** | Teacher closes dashboard → Reopens | Missed heartbeats caught up on reconnect |

**Why not automated**: Requires two authenticated browser sessions with WebSocket connections.

---

### 3. SEB Kiosk Mode Lockdown

**Why not automated**: Tests OS-level restrictions (task manager, alt-tab, etc.)

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Task Manager Block** | In SEB, press Ctrl+Shift+Esc | Task Manager does not open |
| **Alt+Tab Block** | Press Alt+Tab in SEB | No app switcher appears |
| **Win+D Block** | Press Win+D | Desktop not shown |
| **Print Screen Block** | Press Print Screen | Screenshot blocked/captured blank |
| **Right-Click Block** | Right-click in SEB | Context menu disabled |
| **DevTools Block** | Press F12 or Ctrl+Shift+I | DevTools blocked |
| **Window Resize** | Try to resize SEB window | Fixed size, non-resizable |

---

### 4. Passkeys/WebAuthn Biometric Authentication

**Why not automated**: Requires physical authenticator (fingerprint sensor, Face ID, Windows Hello, YubiKey).

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Passkey Registration** | Settings → Passkeys → "Register Passkey" → Touch ID / Face ID / Windows Hello | Passkey created, appears in list |
| **Passkey Login** | Logout → Login page → "Use Passkey" → Biometric | Logged in without password |
| **Cross-Device Sync** | Register on iPhone → Login on Mac (iCloud Keychain) | Passkey available on both |
| **Passkey Deletion** | Settings → Passkeys → Delete → Confirm | Passkey removed, cannot login with it |

**Why not automated**: Requires physical biometric hardware; no WebDriver support for `navigator.credentials.create()`.

---

### 5. SEB Config Generation & Validation

**Why partially automated**: Config generation is testable, but SEB client validation is not.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Config Generation** | Teacher creates exam → Sets SEB key → Downloads `.seb` | `.seb` file valid XML with correct `examKey` and `startURL` |
| **Key Validation** | Student opens `.seb` with wrong key | SEB rejects with "Invalid exam key" |
| **Key Rotation** | Teacher regenerates key → New `.seb` | Old key rejected, new key works |

---

### 5. Three-Way Archive Sync (Student ↔ Teacher ↔ Server)

**Why not automated**: Requires network simulation (offline/online transitions) and file system access.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Offline Archive** | Student completes exam offline → Exam seals locally | Sealed submission stored in IndexedDB, `localSealed: true` |
| **Teacher Sync (LAN)** | Teacher on same WiFi → Opens dashboard → Auto-sync | Teacher device receives encrypted archive, `teacherSynced: true` |
| **Server Sync** | Internet restored → Background sync | Server receives archive, `serverSynced: true` |
| **Cross-Verification** | Compare hashes on all 3 locations | All 3 `content_hash` and `syncHash` match |
| **Tamper Detection** | Modify local archive → Attempt sync | Sync fails, hash mismatch alerted |

---

### 6. Archive Export/Import (Air-Gapped Schools)

**Why not automated**: Requires file system access, USB transfer simulation.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Export Archive** | Admin Dashboard → Archives → Download | `.zst.enc` file downloads |
| **USB Transfer** | Copy to USB → Move to air-gapped teacher laptop | File transfers successfully |
| **Import Archive** | Teacher Dashboard → Import → Select file | Archive restored, appears in teacher's archive list |
| **Integrity Check** | Import corrupted file | Import fails with "Integrity check failed" |

---

### 6. Admin Dashboard - User Management

**Why partially automated**: UI interactions (modals, confirmations) need human verification.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Create Admin** | Admin Dashboard → Users → "Create Admin" → Enter email | User becomes admin, can access admin panel |
| **Revoke Admin** | Admin Dashboard → Click "Revoke" on admin | User loses admin rights, cannot access admin panel |
| **Deactivate User** | Admin → Users → "Deactivate" | User cannot login, data preserved |
| **Delete User** | Admin → Users → "Delete" → Confirm | User and all data removed (GDPR) |

---

### 6. Teacher Archive Management

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **View Archives** | Teacher Dashboard → Archives tab | Lists all archived submissions for teacher's exams |
| **Filter Archives** | Filter by year/month/student/status | Results filter correctly |
| **Download Archive** | Click "Download" → `.zst.enc` downloads | File downloads, can be imported |
| **Restore Archive** | Click "Restore" → Confirm | Archive restored to server, status `active` |
| **Archive Exam** | Click "Archive" on active submission | Moves to archive, removed from server |

---

### 7. AI Grading - Teacher Review Workflow

**Why partially automated**: AI output varies; teacher judgment required.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Generate Grades** | Teacher Dashboard → "Generate AI Grades" | AI grades appear with confidence scores |
| **Edit Grade** | Click "Review" → Edit score/feedback → "Approve & Save" | Grade updated, `teacher_approved: true` |
| **Reject Grade** | Click "Review" → Uncheck "Approve" | Grade not applied, remains "Pending Review" |
| **Apply All** | Click "Apply Approved Grades" | Only approved grades sent to server |
| **Bulk Apply** | Multiple submissions → "Apply All Approved" | All approved grades applied in batch |

---

### 8. Archive Job Management (Admin)

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Create Job** | Admin → Archives → "Create Job" → Set year/filters | Job created with `pending` status |
| **Start Job** | Click "Start" on pending job | Job runs, processes items, updates progress |
| **View Results** | Click "View Results" on completed job | Shows processed/failed counts, download report |
| **External Archive** | Job config: "Archive to external" + path | Archives copied to USB/network path |
| **Delete After Archive** | Job config: "Delete after archive" = true | Server copies deleted after successful archive |

---

### 8. Teacher Archive Stats

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Stats Cards** | Teacher → Archives → Stats visible | Total archives, total size, space saved, by year |
| **By Year Breakdown** | Click year → Monthly breakdown | Correct counts and sizes per month |

---

### 9. Passkeys/WebAuthn Management

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Register Passkey** | Settings → Passkeys → "Register Passkey" → Biometric | Passkey added to list |
| **List Passkeys** | Shows all registered with created/last used dates | Correct dates, transports listed |
| **Delete Passkey** | Click "Delete" → Confirm | Passkey removed, cannot login with it |
| **Passkey Login** | Logout → Login → "Use Passkey" → Biometric | Logged in without password |

---

### 9. AI Key Management

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Add AI Key** | Settings → AI Keys → Enter key → Save | Key encrypted, shows "Configured" |
| **Update AI Key** | Change key → Save | New key used for subsequent calls |
| **Remove AI Key** | Clear key → Save | AI features disabled |
| **Provider Switch** | Change provider (Gemini → OpenRouter) | New provider used for subsequent calls |

---

### 10. OCR & STT Processors

**Why partially automated**: Requires audio/image files.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **OCR Upload** | Upload handwritten math image → Process | Text/LaTeX extracted |
| **OCR Math** | Upload equation image → Process | LaTeX output correct |
| **STT Upload** | Upload audio file → Transcribe | Text output accurate |
| **STT Translate** | Upload foreign audio → Transcribe + Translate | English translation |

---

### 10. Package Manager (Test Sharing)

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Export Package** | Teacher → Exam Editor → "Export Package" | `.yaml` file downloads with exam + questions |
| **Import Package** | Teacher → "Import Package" → Select file | New exam created with imported questions |
| **Version Compatibility** | Import v1.0 package in v1.2 | Backward compatible |

---

### 11. Proctoring Consent Flow

**Why partially automated**: Requires camera/mic permissions.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Give Consent** | Student → Exam → "Give Consent" → Allow camera/mic | Consent recorded, exam can start |
| **Partial Consent** | Allow camera only | Only camera enabled, mic disabled |
| **Withdraw Consent** | During exam → "Withdraw Consent" | Exam pauses, data collection stops |
| **Consent Versioning** | Update consent form → Students re-consent | Old consent invalidated |

---

### 12. Secure Chat (WebSocket)

**Why partially automated**: Requires two browser sessions.

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Student → Teacher** | Student in SEB → "Raise Hand" → Teacher sees notification | Teacher receives message instantly |
| **Teacher → Student** | Teacher → Chat → Send message → Student sees in SEB | Message appears in chat panel |
| **Message Cap** | Send 600-char message | Rejected with "Max 500 characters" |
| **Auto-Scroll** | New message arrives | Chat scrolls to bottom automatically |

---

### 12. Dynamic Math Questions

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Variable Substitution** | Question: `x + [rand:1-10] = 15` → Student sees `x + 7 = 15` | Different random value per student |
| **Answer Validation** | Student enters `8` → Submit | Correct (15-7=8) |
| **Scrambled Options** | Multiple choice → Options shuffled per student | Different order per student |

---

### 13. Accommodations (IEP/Time Multipliers)

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Time Multiplier** | Student has 1.5x → 60-min exam → 90 min timer | Timer shows 90:00 |
| **Extra Time Warning** | 5 min warning at 85 min (not 55 min) | Warning at correct adjusted time |

---

### 14. Theme & Appearance Settings

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Theme Switch** | Settings → Theme → Select "Matrix Green" | UI updates immediately |
| **Border Radius** | Settings → "Round Edges" | All cards/buttons rounded |
| **Persistence** | Refresh page → Theme/Radius preserved | Settings saved to localStorage |

---

### 14. AI Usage & Cost Tracking

| Test Case | Steps | Expected |
|-----------|-------|----------|
| **Usage Dashboard** | Settings → AI Keys → "Usage" tab | Shows calls, tokens, cost, by provider |
| **Budget Warning** | Set $5/day limit → Exceed → Warning at 80% | Warning banner at 80%, blocked at 100% |
| **Cost Summary** | Admin → Archive → Teacher stats | Shows total cost, by provider, by teacher |

---

## Summary: Manual vs Automated Coverage

| Category | Automated | Manual | Reason |
|----------|-----------|--------|--------|
| Auth (register, login, 2FA, passkeys) | 90% | 10% (biometric) | Biometric hardware needed |
| Exam CRUD | 100% | 0% | Full API coverage |
| SEB Integration | 20% | 80% | OS-level kiosk mode |
| Student↔Teacher Sync | 10% | 90% | Dual-browser WebSocket |
| AI Grading | 70% | 30% | Teacher review subjective |
| Archive System | 80% | 20% | File system/USB |
| Archive Jobs | 90% | 10% | External storage paths |
| Passkeys | 50% | 50% | Biometric hardware |
| SEB Kiosk | 10% | 90% | OS-level restrictions |
| Visual Regression | 100% | 0% | Playwright snapshots |
| Unit/Integration | 100% | 0% | pytest/vitest/Playwright |

---

## Manual Testing Checklist (Pre-Release)

### Pre-Release Checklist
- [ ] SEB config generation & validation
- [ ] SEB kiosk mode restrictions (all shortcuts blocked)
- [ ] Student exam flow: start → answer → submit → auto-submit
- [ ] Teacher monitoring: heartbeats, violations, auto-submit
- [ ] AI grading: generate → review → edit → approve → apply
- [ ] Archive: create job → run → download → restore → verify hashes
- [ ] Archive job: create → start → monitor → verify results
- [ ] Passkeys: register → login → delete → cross-device sync
- [ ] Passkeys: cross-device sync (iCloud/Google Password Manager)
- [ ] Admin: create admin, revoke admin, deactivate user
- [ ] Teacher: archive management (view, filter, download, restore, archive)
- [ ] AI grading: generate → review → edit → approve → apply
- [ ] AI usage: cost tracking, budget alerts, provider health
- [ ] SEB: config generation, key validation, kiosk restrictions
- [ ] SEB: violation detection (minimize, tab switch, shortcuts)
- [ ] SEB: auto-fail on exit, crash recovery
- [ ] Archive: export/import (USB), integrity verification
- [ ] Archive jobs: create, start, monitor, restore, external storage
- [ ] Admin: create/revoke admin, deactivate/delete users
- [ ] Teacher: archive management (view, filter, download, restore)
- [ ] AI grading: generate, review, edit, approve, apply
- [ ] AI usage: cost tracking, budget alerts, provider health
- [ ] Proctoring: consent, sessions, events, stats
- [ ] OCR/STT: upload, process, results
- [ ] Packages: export/import, version compatibility
- [ ] Dynamic math: variable substitution, answer validation
- [ ] Accommodations: time multipliers, warnings
- [ ] Themes: persistence, border radius, color schemes
- [ ] AI usage: dashboard, budget alerts, provider status
- [ ] Secure chat: student↔teacher, message caps, auto-scroll
- [ ] Dynamic math: variable substitution, scrambling
- [ ] Accommodations: time multipliers, adjusted warnings
- [ ] Themes: persistence, border radius, color schemes
- [ ] AI usage: dashboard, budget alerts, provider status

---

## Test Environment Requirements

### Hardware
- [ ] Windows 10/11 machine (for SEB testing)
- [ ] macOS machine (for Safari/WebKit testing)
- [ ] iOS device (for Passkeys iCloud sync)
- [ ] Android device (for Passkeys Google sync)
- [ ] YubiKey or similar (for Passkeys hardware key)
- [ ] Two physical machines (for student↔teacher sync)

### Software
- [ ] SEB 3.4+ installed on Windows test machine
- [ ] Chrome, Firefox, Edge latest
- [ ] Playwright browsers installed (`npx playwright install --with-deps`)
- [ ] Docker + Docker Compose (for container tests)
- [ ] Node.js 20+, Python 3.12+

### Network
- [ ] Local network (for LAN sync testing)
- [ ] Internet access (for AI providers, SEB validation)
- [ ] Ability to disconnect internet (offline testing)

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | | | |
| Dev Lead | | | |
| Security Officer | | | |
| Product Owner | | | |