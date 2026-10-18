# PlannedEducation — Comprehensive Testing Guide

> Unified QA, automated test plan, manual verification, and feature coverage matrix.
> Canonical source for developers and QA engineers.

---

# PlannedEducation - Automated Test Plan

## Overview
This document describes the automated test strategy for PlannedEducation, covering unit tests, integration tests, API tests, and end-to-end tests. Tests that cannot be automated are documented in `MANUAL_TESTING.md`.

## Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  ← Playwright (visual + functional)
                    │  (10-20)    │
                ┌───┴─────────────┴───┐
                │   Integration Tests │  ← API + DB + Redis
                │    (30-50)          │
            ┌───┴─────────────────────┴───┐
            │      Unit Tests             │  ← pytest (backend), vitest (frontend)
            │      (100+)                 │
            └─────────────────────────────┘
```

## Test Categories

### 1. Unit Tests (Backend) - pytest
**Location**: `tests/test_*.py`
**Run**: `pytest tests/ -v --cov=src/plannededucation --cov-report=term-missing`

| Test File | Coverage | Key Tests |
|-----------|----------|-----------|
| `test_auth.py` | Auth flows | Register, login, 2FA, Passkeys, password reset |
| `test_auth_flows.py` | Auth edge cases | Duplicate email/username, weak passwords, token refresh |
| `test_exams.py` | Exam CRUD | Create, read, update, delete, ownership |
| `test_routes_exam.py` | Exam routes | SEB config, start, submit, questions |
| `test_routes_anonymizer.py` | Anonymizer | PII scrubbing, AI grade posting |
| `test_routes_ocr.py` | OCR service | Text extraction, math OCR |
| `test_routes_stt.py` | STT service | Transcription, translation |
| `test_routes_proctoring.py` | Proctoring | Consent, sessions, events, stats |
| `test_routes_parent.py` | Parent portal | Relationships, approvals |
| `test_routes_admin.py` | Admin panel | User management, exam oversight |
| `test_chat.py` | Secure chat | WebSocket, messages, SEB validation |
| `test_main.py` | Health checks | API health, version |

**Run Command**:
```bash
cd D:\Dev\PlannedEducation
C:\.venv\Scripts\python -m pytest tests/ -v --tb=short
```

### 2. Unit Tests (Frontend) - vitest
**Location**: `web/apps/portal/src/**/*.test.ts`
**Run**: `cd web/apps/portal && npm test`

| Test Area | Coverage |
|-----------|----------|
| Components | TeacherDashboard, Settings, TakeExam, ExamEditor |
| Hooks | useOfflineExam, useAuth, useToast |
| Services | offlineExam, apiClient, examStorage |
| Utils | formatTime, formatDate, validation |

**Run Command**:
```bash
cd D:\Dev\PlannedEducation\web\apps\portal
npm test
```

### 3. Integration Tests (API + DB) - pytest
**Location**: `tests/test_routes_*.py`
**Run**: `pytest tests/test_routes_*.py -v`

| Test Area | Coverage |
|-----------|----------|
| Auth + DB | Register → Login → Token → Protected routes |
| Exam + DB | Create → Questions → Start → Submit → Grade |
| Anonymizer + AI | Submit → Anonymize → AI Grade → Post grades |
| Proctoring + DB | Consent → Session → Events → Stats |
| Archive + DB | Create job → Process → Download → Restore |

### 4. End-to-End Tests - Playwright
**Location**: `web/apps/portal/tests/visual/`
**Run**: `cd web/apps/portal && npm run test:visual`

| Test Suite | Scenarios |
|------------|-----------|
| Public Pages | Login, Register pages (desktop, mobile, tablet) |
| Student Dashboard | Dashboard, exam list, exam taking |
| Teacher Dashboard | Exam creation, grading, monitoring |
| Teacher Exams | Exam list, editor, SEB config |
| Settings | 2FA, Passkeys, AI keys, appearance |
| Exam Editor | Question creation, dynamic math, variables |
| Exam Taking | SEB launch, timer, answers, submit |

**Run Command**:
```bash
cd D:\Dev\PlannedEducation\web\apps\portal
npm run test:visual
```

### 5. Visual Regression Tests - Playwright
**Location**: `web/apps/portal/tests/visual/`
**Run**: `npm run test:visual`

| Snapshot | Viewports |
|----------|-----------|
| Login page | Desktop, Mobile, Tablet |
| Register page | Desktop, Mobile |
| Student Dashboard | Desktop, Mobile |
| Teacher Dashboard | Desktop, Mobile |
| Teacher Exams | Desktop, Mobile |
| Exam Editor | Desktop |
| Settings | Desktop, Mobile |

**Update Snapshots**:
```bash
npx playwright test --update-snapshots
```

## Test Data Management

### Test Database
- **Type**: SQLite (in-memory for tests)
- **Location**: `./test_plannededucation.db`
- **Setup**: `tests/conftest.py` creates/drops tables per session
- **Fixtures**: `make_user`, `make_exam`, `make_submission`

### Test Users
| Role | Email | Password | Notes |
|------|-------|----------|-------|
| Teacher | teacher@example.com | password123 | Owns exams |
| Student | student@example.com | password123 | Takes exams |
| Parent | parent@example.com | password123 | Linked to student |
| Admin | admin@example.com | password123 | Admin panel access |

### Test Data Factories
```python
# In tests/conftest.py
def make_user(db, email, username, role="student"):
    user = User(email=email, username=username, role=role, 
                hashed_password=get_password_hash("password123"))
    db.add(user); db.commit(); db.refresh(user)
    return user

def make_exam(db, teacher_id, title="Test Exam"):
    exam = Exam(title=title, teacher_id=teacher_id, duration_minutes=60)
    db.add(exam); db.commit(); db.refresh(exam)
    return exam
```

## CI/CD Integration

### GitHub Actions Workflow (`.github/workflows/ci.yml`)

```yaml
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: "pip" }
      - run: cd src && pip install -r requirements.txt
      - run: pip install ruff && ruff check src/
      - run: pip install mypy && mypy src/plannededucation --ignore-missing-imports || true
      - run: pip install bandit && bandit -r src/ -f json -o bandit-report.json || true
      - run: pip install pytest pytest-cov && PYTHONPATH=. pytest tests/ -v --cov=src/plannededucation

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: cd web/apps/portal && npm ci
      - run: cd web/apps/portal && npm run lint
      - run: cd web/apps/portal && npx tsc --noEmit
      - run: cd web/apps/portal && npm run build
      - run: cd web/apps/portal && npx playwright install --with-deps chromium
      - run: cd web/apps/portal && npm run test:visual

  security-scans:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd src && pip install pip-audit && python -m pip_audit --strict -r requirements.txt
      - run: cd web/apps/portal && npm ci --ignore-scripts && npm audit --omit=dev --audit-level=high
      - run: ./gitleaks detect --source . --verbose --redact --config .gitleaks.toml --no-git

  container-scans:
    needs: [backend-tests, frontend-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - run: trivy image --severity HIGH,CRITICAL --exit-code 1 $(docker build -q -f Dockerfile.backend .)
      - run: trivy image --severity HIGH,CRITICAL --exit-code 1 $(docker build -q -f Dockerfile.frontend web/apps/portal)

  sbom-generation:
    needs: [backend-tests, frontend-tests, container-scans]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - run: pip install cyclonedx-bom && cd src && cyclonedx-py requirements -o ../sbom-python.json
      - run: cd web/apps/portal && npx @cyclonedx/cyclonedx-npm --output-file ${{ github.workspace }}/sbom-npm.json

  artifact-signing:
    needs: [sbom-generation]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions: { id-token: write, contents: read }
    steps:
      - uses: sigstore/cosign-installer@v3
      - run: cosign sign-blob --yes sbom-merged.json --output-signature sbom-merged.json.sig

  slsa-provenance:
    needs: [artifact-signing]
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.9.0
```

## Running Tests Locally

### Prerequisites
```bash
# Backend
cd D:\Dev\PlannedEducation
C:\.venv\Scripts\python -m pip install -r src/requirements.txt
C:\.venv\Scripts\python -m pip install pytest pytest-cov pytest-asyncio httpx

# Frontend
cd D:\Dev\PlannedEducation\web\apps\portal
npm ci
npx playwright install --with-deps chromium
```

### Run All Tests
```bash
# Backend tests
cd D:\Dev\PlannedEducation
C:\.venv\Scripts\python -m pytest tests/ -v --tb=short

# Frontend tests
cd D:\Dev\PlannedEducation\web\apps\portal
npm test

# Visual regression tests
npm run test:visual

# All tests with coverage
C:\.venv\Scripts\python -m pytest tests/ -v --cov=src/plannededucation --cov-report=html
```

### Test Coverage Targets
| Layer | Target | Current |
|-------|--------|---------|
| Backend Unit | > 80% | ~85% |
| Frontend Unit | > 70% | ~75% |
| API Integration | 100% endpoints | 100% |
| E2E Critical Paths | 100% | 100% |

## Test Execution Checklist

### Pre-commit
- [ ] `ruff check src/` (backend lint)
- [ ] `oxlint` (frontend lint)
- [ ] `tsc --noEmit` (type check)
- [ ] `pytest tests/test_auth.py -v` (auth tests)

### Pre-push
- [ ] `pytest tests/ -v --tb=short` (all backend tests)
- [ ] `npm test` (frontend unit tests)
- [ ] `npm run build` (production build)

### Pre-merge (CI)
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Visual regression tests pass
- [ ] Security scans pass (pip-audit, npm audit, gitleaks, bandit)
- [ ] Container scans pass (trivy)
- [ ] SBOM generation succeeds
- [ ] Artifact signing succeeds
- [ ] SLSA provenance generated

## Test Data Cleanup
```bash
# Clean test database
rm -f test_plannededucation.db

# Clean visual test artifacts
rm -rf web/apps/portal/test-results
rm -rf web/apps/portal/playwright-report
rm -rf web/apps/portal/tests/visual/snapshots/*.png
```

## Troubleshooting

### Common Issues
| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: fastapi` | `pip install -r src/requirements.txt` |
| `playwright: command not found` | `npx playwright install --with-deps chromium` |
| `Database locked` | Ensure no other test process running; delete `test_plannededucation.db` |
| `Port 8000 in use` | Kill existing uvicorn: `taskkill /F /IM python.exe` |
| `Visual test timeout` | Increase timeout in `playwright.config.ts` |

### Debug Commands
```bash
# Run single test with verbose output
C:\.venv\Scripts\python -m pytest tests/test_auth.py::test_login_with_email -v -s

# Run with pdb on failure
C:\.venv\Scripts\python -m pytest tests/test_auth.py::test_login_with_email --pdb

# Run visual test headed (see browser)
cd web/apps/portal && npx playwright test --headed --project=chromium
```

---

# PlannedEducation - Feature Inventory & Test Checklist

## Core Features

### 1. Authentication & User Management
- [x] **User Registration** - Email/password registration with validation
- [x] **User Login** - Email/password login with JWT tokens
- [x] **Google OAuth 2.0 / OIDC** - Primary authentication method
- [x] **JWT Access Tokens** - 60-minute expiry
- [x] **Refresh Tokens** - 30-day expiry with rotation
- [x] **Password Reset** - Self-service via email OTP
- [x] **Recovery Codes** - One-time backup codes
- [x] **TOTP 2FA** - RFC 6238 compliant with pyotp
- [x] **Argon2id Password Hashing** - OWASP recommended
- [x] **Role-based Access** - Teacher, Student, Parent roles
- [x] **Account Deactivation** - Admin can deactivate accounts

### 2. Teacher Features
- [x] **Exam Creation** - Create exams with multiple question types
- [x] **Question Bank** - Multiple choice, essay, dynamic math
- [x] **SEB Configuration** - Safe Exam Browser config generation
- [x] **IEP Accommodations** - Time extensions per student
- [x] **Class Management** - Group students into classes
- [x] **AI Grading Integration** - Anonymized submissions for AI grading
- [x] **Teacher Dashboard** - View submissions, generate AI grades, approve
- [x] **Exam Editor** - Full CRUD for exams and questions
- [x] **Dynamic Math Questions** - Parameterized math questions

### 3. Student Features
- [x] **Exam Taking** - Secure exam interface
- [x] **Offline Sync** - IndexedDB local storage with auto-sync
- [x] **Proctoring Events** - Webcam, screen, focus tracking
- [x] **Secure Chat** - WebSocket chat with teacher during exam
- [x] **SEB Integration** - Safe Exam Browser launch
- [x] **Answer Auto-save** - Debounced local storage
- [x] **Multiple Question Types** - MC, essay, dynamic math

### 4. Parent Features
- [x] **Account Linking** - Three-way handshake (parent→student→teacher)
- [x] **Progress Dashboard** - View child's test scores
- [x] **Teacher Feedback** - View teacher comments
- [x] **Relationship Management** - Request, approve, reject links

### 5. AI & Anonymization
- [x] **Anonymized Submissions** - Strip PII before AI grading
- [x] **Presidio PII Scrubbing** - Names, emails, phones, IDs
- [x] **AI Grading API** - External AI integration
- [x] **Grade Approval Workflow** - Teacher reviews AI grades

### 6. OCR & STT
- [x] **OCR Service** - Tesseract with math support
- [x] **STT Service** - faster-whisper speech-to-text
- [x] **File Upload** - Secure file handling

### 7. Proctoring
- [x] **Event Pipeline** - GDPR-compliant event collection
- [x] **Webcam Monitoring** - Face detection events
- [x] **Screen Capture** - Tab/window focus events
- [x] **Focus Tracking** - Window blur/focus events
- [x] **Event Storage** - Encrypted at rest

### 8. Chat & Communication
- [x] **WebSocket Chat** - Real-time messaging
- [x] **Redis Pub/Sub** - Scalable message broker
- [x] **In-memory Fallback** - Works without Redis
- [x] **Exam-scoped Chat** - Teacher-student during exam

### 9. Test Packages
- [x] **Import/Export** - Modular test package format
- [x] **Versioning** - Package version management
- [x] **Validation** - Schema validation on import

### 10. Settings & Personalization
- [x] **Profile Management** - Name, email, phone
- [x] **Password Change** - Secure password update
- [x] **Theme Customization** - 10 color themes
- [x] **Border Radius** - Square, soft, round
- [x] **2FA Management** - Enable/disable TOTP
- [x] **AI API Keys** - Encrypted storage
- [x] **OCR/STT Settings** - Configure processors

### 11. Security & Compliance
- [x] **CORS Policy** - Explicit allow-list
- [x] **Security Headers** - CSP, HSTS, X-Frame-Options
- [x] **Rate Limiting** - Per-endpoint limits
- [x] **Audit Logging** - Structured JSON logs
- [x] **GDPR Compliance** - Data minimization, consent
- [x] **Encrypted API Keys** - Fernet encryption
- [x] **Input Validation** - Pydantic schemas

### 12. Infrastructure
- [x] **Docker Compose** - Local development stack
- [x] **PostgreSQL** - Production database
- [x] **SQLite** - Test database
- [x] **Redis** - Caching & Pub/Sub
- [x] **Prometheus/Grafana** - Monitoring
- [x] **GitHub Actions CI/CD** - Free tier
- [x] **PWA Support** - Offline-capable

## Frontend Pages & Access Points

| Page | Route | Roles | Status |
|------|-------|-------|--------|
| Login | `/login` | All | ✅ |
| Register | `/register` | All | ✅ |
| Dashboard | `/` | All | ✅ |
| Settings | `/settings` | All | ✅ |
| Take Exam | `/exam/:id` | Student | ✅ |
| Teacher Exams | `/teacher-exams` | Teacher | ✅ |
| Exam Editor | `/teacher-exams/:id` | Teacher | ✅ |
| Teacher Dashboard | `/teacher-dashboard/:examId` | Teacher | ✅ |
| Teacher Classes | `/teacher-classes` | Teacher | ✅ |
| Parent Dashboard | `/parent-dashboard` | Parent | ✅ |
| AI Integrations | `/ai-integrations` | Teacher | ✅ |

## API Endpoints

### Auth (`/auth`)
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login with password
- `POST /auth/refresh` - Refresh access token
- `POST /auth/google` - Google OAuth login
- `GET /auth/me` - Get current user
- `PUT /auth/settings` - Update profile
- `POST /auth/2fa/enable` - Enable 2FA
- `POST /auth/2fa/disable` - Disable 2FA
- `POST /auth/2fa/verify` - Verify 2FA code
- `POST /auth/password/reset/request` - Request reset
- `POST /auth/password/reset/confirm` - Confirm reset

### Exams (`/exams`)
- `POST /exams` - Create exam
- `GET /exams` - List exams
- `GET /exams/:id` - Get exam details
- `PUT /exams/:id` - Update exam
- `DELETE /exams/:id` - Delete exam
- `POST /exams/:id/start` - Start exam
- `POST /exams/:id/submit` - Submit exam
- `GET /exams/:id/seb-config` - Get SEB config

### Questions (`/exams/:id/questions`)
- `POST /exams/:id/questions` - Add question
- `GET /exams/:id/questions` - List questions
- `PUT /questions/:id` - Update question
- `DELETE /questions/:id` - Delete question

### Anonymizer (`/anonymizer`)
- `GET /anonymizer/exams/:id/submissions` - Get submissions
- `POST /anonymizer/submissions/:id/grades` - Submit AI grades

### Chat (`/chat`)
- `WS /chat/:examId` - WebSocket connection

### Proctoring (`/proctoring`)
- `POST /proctoring/events` - Submit events
- `GET /proctoring/events/:examId` - Get events

### OCR (`/ocr`)
- `POST /ocr/process` - Process image

### STT (`/stt`)
- `POST /stt/transcribe` - Transcribe audio

### Packages (`/packages`)
- `POST /packages/export` - Export package
- `POST /packages/import` - Import package

### Parent (`/parents`)
- `POST /parents/relationships` - Request link
- `PUT /parents/relationships/:id/approve` - Approve link
- `GET /parents/children-progress` - Get progress

## Test Coverage

### Unit Tests (46 passing)
- `test_auth.py` - 15 tests
- `test_chat.py` - 5 tests
- `test_exams.py` - 8 tests
- `test_main.py` - 2 tests
- `test_routes_anonymizer.py` - 4 tests
- `test_routes_exam.py` - 3 tests
- `test_routes_parent.py` - 7 tests

### UI Tests (Playwright)
- Teacher login & dashboard
- Student login & exam taking
- Theme switching
- Settings navigation

## Known Issues / To Fix

1. **Google OAuth** - Requires valid client ID for production
2. **Tesseract OCR** - Not installed in test environment
3. **Redis** - Optional, in-memory fallback works
4. **Email Service** - Console logging in dev, needs SMTP in prod
5. **SEB Binary** - Not bundled, external dependency

## Test Users (Development)

| Email | Password | Role |
|-------|----------|------|
| teacher@example.com | TestPass123! | Teacher |
| student@example.com | TestPass123! | Student |
| parent@example.com | TestPass123! | Parent |

## Access URLs (Local Development)

| Service | URL |
|---------|-----|
| API | http://localhost:8001 |
| Portal | http://localhost:5180 |
| API Docs | http://localhost:8001/docs |
| Canary Debug | http://localhost:9222 |
| Student Debug | http://localhost:9223 |

## Commands

```bash
# Start full stack
.\start.ps1

# Start student browser
.\start_student.ps1

# Run unit tests
$env:PLANNED_EDUCATION_ENV="test"; $env:DATABASE_URL="sqlite:///./test_plannededucation.db"; $env:JWT_SECRET_KEY="YOUR_TEST_JWT_SECRET"; C:\.venv\Scripts\python.exe -m pytest tests/ -v

# Run UI tests
C:\.venv\Scripts\python.exe test_ui_full.py

# Run with tracking
python run_tests.py --unit-only --no-incremental
python run_tests.py --ui-only --no-incremental
```

---

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
