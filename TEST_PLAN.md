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