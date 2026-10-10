# Playwright E2E Test Suite - Testing Guide

## Overview
This folder contains all Playwright end-to-end tests for PlannedEducation. Tests are organized by feature area and can be run in different modes.

## Test Structure

```
tests/e2e/playwright/
├── tests/
│   ├── platform-visual.spec.ts          # Visual regression tests
│   ├── comprehensive-interactive.spec.ts # Interactive feature tests
│   ├── advanced-features.spec.ts        # Advanced feature tests
│   ├── simulation-e2e.spec.ts           # Simulation E2E tests
│   └── global-teardown.ts               # Cleanup after tests
├── snapshots/                           # Visual regression baselines
├── playwright.config.ts                 # Playwright configuration
└── TESTING_GUIDE.md                     # This file
```

## Test Categories

### 1. Visual Regression Tests (`platform-visual.spec.ts`)
- Login/Register pages (desktop, mobile, tablet)
- Student/Teacher/Parent/Admin dashboards
- Exam editor, settings pages
- Visual regression against baseline snapshots

### 2. Interactive Feature Tests (`comprehensive-interactive.spec.ts`)
- Full exam taking flow (start, answer, submit)
- Teacher dashboard interactions (AI grading, review)
- Settings page (Passkeys, 2FA, AI keys)
- Exam editor (create exams, questions)
- Parent/Admin dashboards
- Exam taking flow (start, answer, submit)
- Teacher dashboard interactions (AI grading, review)
- Exam editor (create exams, questions)
- Settings page (Passkeys, 2FA, AI keys)

### 3. Advanced Features (`advanced-features.spec.ts`)
- OCR processing
- Speech-to-text
- Proctoring consent flow
- Secure chat
- Package management

### 4. Simulation E2E (`simulation-e2e.spec.ts`)
- Full exam simulation
- Multiple students
- Proctoring events

## Running Tests

### Prerequisites
```bash
cd tests/e2e/playwright
npm install
npx playwright install --with-deps chromium
```

### Run All Tests (Headless - CI Mode)
```bash
npx playwright test
```

### Run with Browser Visible (Headed Mode)
```bash
# Run with Chrome Canary (recommended for debugging)
npx playwright test --project=chromium-canary --headed

# Debug mode with DevTools auto-open
npx playwright test --project=chromium-debug --headed

# Run specific test file
npx playwright test --project=chromium-canary --headed tests/comprehensive-interactive.spec.ts

# Debug mode (step through)
npx playwright test --project=chromium-debug --headed --debug
```

### Run Specific Test
```bash
# Run specific test by name
npx playwright test --project=chromium-canary --headed -g "Full exam flow"

# Run specific file
npx playwright test --project=chromium-canary --headed tests/comprehensive-interactive.spec.ts
```

### Update Snapshots
```bash
npx playwright test --project=chromium-canary --headed --update-snapshots
```

## Test Projects Configuration

| Project | Browser | Use Case |
|---------|---------|----------|
| `chromium` | Chrome stable | Standard testing |
| `chromium-canary` | Chrome Canary | Latest features, debugging |
| `chromium-debug` | Chrome with DevTools auto-open | Debugging |
| `mobile-chrome` | Mobile Chrome | Mobile testing |
| `tablet` | Tablet viewport | Tablet testing |

## Debugging Tips

### 1. Run in Debug Mode
```bash
npx playwright test --project=chromium-debug --headed --debug
```
This opens Chrome with DevTools open and pauses at each step.

### 2. Run Single Test with Trace
```bash
npx playwright test --project=chromium-canary --headed --trace=on tests/comprehensive-interactive.spec.ts
```
Generates trace file you can open at https://trace.playwright.dev/

### 3. Debug Specific Test
```bash
npx playwright test --project=chromium-debug --headed --debug -g "Full exam flow"
```

### 4. Run Headed with Slow Motion
```bash
npx playwright test --project=chromium-canary --headed --slowmo=1000
```

## Test Data Setup

Tests use seeded database with these users:
```javascript
const TEST_USERS = {
  student: { email: 'student@example.com', password: 'password123' },
  teacher: { email: 'teacher@example.com', password: 'password123' },
  parent: { email: 'parent@example.com', password: 'password123' },
  admin: { email: 'admin@yourschool.edu', password: 'ChangeMe123!' },
};
```

Sample exam ID: `e8efa978-a1cd-481c-bd6b-83a1e05d8e00`

## Running Tests in CI/CD

### GitHub Actions (Headless)
```yaml
- name: Run Playwright tests
  run: npx playwright test
```

### Local Development (Headed)
```bash
npx playwright test --project=chromium-canary --headed
```

## Debugging Failed Tests

### 1. View Trace
```bash
npx playwright show-trace trace.zip
```

### 2. Open HTML Report
```bash
npx playwright show-report
```

### 3. Debug with VS Code
1. Install "Playwright Test for VS Code" extension
2. Open test file
3. Click "Run Test" or "Debug Test" above test

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Browser not found | `npx playwright install --with-deps chromium` |
| Port 5175 in use | Kill existing process: `taskkill /F /IM node.exe` |
| Snapshot mismatch | Run with `--update-snapshots` |
| Timeout | Increase timeout in test or config |
| SEB not launching | Install SEB 3.4+ on Windows |

## Test Coverage Areas

| Area | Coverage |
|------|----------|
| Authentication | Login, register, 2FA, Passkeys |
| Exam Management | Create, edit, delete, SEB config |
| Exam Taking | Start, answer, submit, timer |
| AI Grading | Generate, review, approve, apply |
| Archive System | Create, download, restore, verify |
| Proctoring | Consent, sessions, events |
| Settings | 2FA, Passkeys, AI keys, themes |
| Real-time | Heartbeats, chat, violations |

## Running Specific Test Scenarios

### Test SEB Integration
```bash
npx playwright test --project=chromium-canary --headed -g "SEB"
```

### Test AI Grading
```bash
npx playwright test --project=chromium-canary --headed -g "AI Grading"
```

### Test Passkeys
```bash
npx playwright test --project=chromium-canary --headed -g "Passkey"
```

### Test Archive System
```bash
npx playwright test --project=chromium-canary --headed -g "Archive"
```

## Updating Snapshots

When UI changes intentionally:
```bash
npx playwright test --project=chromium-canary --headed --update-snapshots
```

## Debugging Tips

1. **Use `--debug` flag** for step-by-step debugging
2. **Use `--trace=on`** to capture full trace
3. **Use `--headed`** to see browser
4. **Use `--slowmo=1000`** to slow down execution
5. **Check trace at** https://trace.playwright.dev/

## Test Data Management

Tests use seeded database. To reset:
```bash
# Backend will recreate test database on startup
# Or manually:
rm -f test_plannededucation.db
```

## Continuous Integration

Tests run automatically on:
- Push to `main`, `dev`, `develop` branches
- Pull requests to `main`, `dev`, `develop`
- Scheduled weekly runs

See `.github/workflows/ci.yml` for full CI configuration.