# PlannedEducation - Install Log & Version Compatibility Matrix

## Generated: 2026-10-17

## ⚠️ WARNING: Version Compatibility Assumptions

This project was updated to use newer dependency versions. The following assumptions were made:

1. **Compatibility is assumed but not guaranteed** for versions newer than the tested minimum.
2. **Anything newer than the tested version MIGHT work** - but has not been verified.
3. **Anything older than the minimum version WILL NOT work** - do not use older versions.
4. **Breaking changes may exist** between minor versions of dependencies.
5. **Test thoroughly** before deploying to production with newer versions.

## Python Version
- **Tested with**: Python 3.14.6
- **Minimum**: Python 3.12.0
- **Note**: `requires-python = ">=3.12"` in pyproject.toml

## Dependency Version Matrix

| Package | Minimum Version | Tested Version | Latest Available | Status |
|---------|----------------|----------------|------------------|--------|
| fastapi | >=0.110.0 | 0.143.2 | 0.143.2 | ✅ Tested |
| uvicorn | >=0.28.0 | 0.54.0 | 0.54.0 | ✅ Tested |
| websockets | >=14.0 | 17.2 | 17.2 | ✅ Tested |
| sqlalchemy | >=2.0.27 | 2.1.4 | 2.1.4 | ✅ Tested |
| psycopg2-binary | >=2.9.9 | 2.9.13 | 2.9.13 | ✅ Tested |
| pydantic | >=2.6.3 | 2.14.1 | 2.14.1 | ✅ Tested |
| pydantic-settings | >=2.0.0 | 2.16.0 | 2.16.0 | ✅ Tested |
| PyJWT | >=2.13.0 | 2.15.1 | 2.15.1 | ✅ Tested |
| argon2-cffi | >=23.1.0 | 25.1.0 | 25.1.0 | ✅ Tested |
| pyotp | >=2.9.0 | 2.10.0 | 2.10.0 | ✅ Tested |
| cryptography | >=48.0.1 | 48.0.1 | 48.0.1 | ✅ Tested |
| google-auth | >=2.28.0 | 2.62.0 | 2.62.0 | ✅ Tested |
| google-auth-oauthlib | >=1.2.0 | 1.5.0 | 1.5.0 | ✅ Tested |
| slowapi | >=0.1.9 | 0.1.10 | 0.1.10 | ✅ Tested |
| aiosmtplib | >=3.0.0 | 5.1.3 | 5.1.3 | ✅ Tested |
| redis | >=5.0.0 | 8.1.0 | 8.1.0 | ✅ Tested |
| pytesseract | >=0.3.10 | 0.3.13 | 0.3.13 | ✅ Tested |
| pillow | >=10.0.0 | 12.3.0 | 12.3.0 | ✅ Tested |
| presidio-analyzer | >=2.2.355 | 2.2.364 | 2.2.364 | ✅ Tested |
| presidio-anonymizer | >=2.2.355 | 2.2.364 | 2.2.364 | ✅ Tested |
| httpx | >=0.28.0 | 0.28.1 | 0.28.1 | ✅ Tested |
| python-multipart | >=0.0.6 | 0.0.32 | 0.0.32 | ✅ Tested |
| webauthn | >=2.5.0 | 2.8.0 | 2.8.0 | ✅ Tested |
| zstandard | >=0.23.0 | 0.25.0 | 0.25.0 | ✅ Tested |
| prometheus-client | >=0.20.0 | 0.26.0 | 0.26.0 | ✅ Tested |
| opentelemetry-api | >=1.25.0 | 1.45.1 | 1.45.1 | ✅ Tested |
| opentelemetry-sdk | >=1.25.0 | 1.45.1 | 1.45.1 | ✅ Tested |
| opentelemetry-exporter-prometheus | >=0.46b0 | 0.66b1 | 0.66b1 | ✅ Tested |
| opentelemetry-instrumentation-fastapi | >=0.46b0 | 0.66b1 | 0.66b1 | ✅ Tested |
| opentelemetry-instrumentation-requests | >=0.46b0 | 0.66b1 | 0.66b1 | ✅ Tested |
| opentelemetry-instrumentation-sqlalchemy | >=0.46b0 | 0.66b1 | 0.66b1 | ✅ Tested |

## Node.js / Frontend Dependencies

| Package | Minimum Version | Tested Version | Latest Available | Status |
|---------|----------------|----------------|------------------|--------|
| node | >=20.0.0 | 24.18.0 | 24.18.0 | ✅ Tested |
| npm | >=10.0.0 | 10.0.0 | 10.0.0 | ✅ Tested |
| vite | ^8.3.0 | 8.3.0 | 8.3.4 | ✅ Tested |
| react | ^19.2.8 | 19.2.8 | 19.2.8 | ✅ Tested |
| react-dom | ^19.2.8 | 19.2.8 | 19.2.8 | ✅ Tested |
| react-router-dom | ^7.18.4 | 7.18.4 | 7.18.4 | ✅ Tested |
| typescript | ~6.0.2 | 6.0.2 | 6.0.2 | ✅ Tested |
| @vitejs/plugin-react | ^6.1.1 | 6.1.1 | 6.1.1 | ✅ Tested |
| playwright | ^1.63.0 | 1.64.0 | 1.64.1 | ✅ Tested |

## Test Results

### Backend Tests (pytest)
- **Result**: 107 passed
- **Command**: `C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-all" -- C:/.venv/Scripts/python.exe -m pytest tests/ -q`
- **Database**: SQLite (`test_visual.db`)
- **Environment**: `PLANNED_EDUCATION_ENV=test`

### Comprehensive E2E Test (test_e2e_comprehensive.py)
- **Result**: ALL 13 STEPS PASSED
- **Steps verified**:
  1. Teacher login ✅
  2. Student login ✅
  3. Parent login ✅
  4. Teacher creates exam with 5 questions ✅
  5. Student starts exam ✅
  6. Student answers questions ✅
  7. Student submits exam ✅
  8. Teacher views anonymized submissions ✅
  9. Teacher generates AI grades ✅
  10. Teacher approves grades ✅
  11. Parent requests relationship ✅
  12. Parent views children progress ✅
  13. Teacher views exam results ✅

### Playwright E2E & Visual Regression Tests
- **Result**: 57 passed out of 57 tests (100% pass rate)
- **Specs verified**:
  - `advanced-features.spec.ts` (7/7 passed) ✅
  - `comprehensive-interactive.spec.ts` (27/27 passed) ✅
  - `platform-visual.spec.ts` (17/17 visual regression & responsive overflow tests passed across desktop, tablet, and mobile) ✅
  - `simulation-e2e.spec.ts` (5/5 multi-role live simulation & theme tests passed) ✅
  - `visual-math-correction-deploy.spec.ts` (1/1 dual-browser live math exam & teacher side-by-side correction test passed) ✅

## Installation Instructions

### Prerequisites
- Python 3.12+ (tested with 3.14.6)
- Node.js 20+ (tested with 24.18.0)
- npm 10+ (tested with 10.0.0)
- Git
- PostgreSQL 16+ (for production) or SQLite (for development/testing)
- Redis (for WebSocket Pub/Sub in production)

### Backend Installation
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r src\requirements.txt

# Or install from requirements_latest.txt for newest versions
pip install -r requirements_latest.txt
```

### Frontend Installation
```powershell
cd web\apps\portal
npm ci
npm run build
```

### Deployment
See `DEPLOY_SIMPLE.md` for simple deployment guide.
See `DEPLOY_COMPREHENSIVE.md` for comprehensive deployment guide.
See `install.ps1` for Windows installer.

## Downgrade Instructions

If you encounter issues with newer versions, downgrade to the minimum tested versions:

```powershell
# Example: downgrade fastapi
pip install "fastapi>=0.110.0,<0.143.0"

# Example: downgrade pydantic
pip install "pydantic>=2.6.3,<2.14.0"

# Or reinstall from original requirements.txt
pip install -r src\requirements.txt
```

## Files Modified

- `src/requirements.txt` - Updated with version ranges
- `pyproject.toml` - Updated Python version requirement
- `requirements_latest.txt` - Exported from pip freeze (latest versions)
- `test_e2e_comprehensive.py` - Updated API_URL and passwords for testing
- `scratch/temp_log.md` - Progress tracking log
