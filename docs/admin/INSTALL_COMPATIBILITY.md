# Installation Compatibility & Lowest-Limit Architecture

PlannedEducation is a **100% free and open-source**, local-first educational platform with **zero paid services**.

This document describes the package dependency philosophy, lowest probable limit requirements, forward-compatibility assumptions, and downgrade guidelines.

---

## 1. Compatibility Philosophy

Rather than strictly pinning dependencies to exact version numbers (`==`), PlannedEducation defines **lowest probable limits** (`>=` for Python, `^` for Node.js). 

### Why Lowest-Limit Requirements?
1. **Security & CVE Patching**: Allows administrators to apply security updates and patches immediately without waiting for upstream package bumps.
2. **Platform & Distro Flexibility**: Ensures compatibility across varying OS package repositories (Debian, Ubuntu, Fedora, Alpine Linux, Windows).
3. **Forward Compatibility**: We assume that newer minor and patch releases maintain backward compatibility.

### ⚠️ Forward-Compatibility Warning & Downgrade Instructions
While newer versions are assumed compatible, cutting-edge library releases may occasionally introduce unexpected API changes or breaking behaviors.
- **Tested Baseline**: All automated test suites (102 backend pytest suites, 22 Playwright visual regression and simulation suites) have been validated against the **Tested With** versions listed below.
- **Troubleshooting**: If you experience dependency resolution errors or runtime issues after a generic upgrade, **downgrade** the affected package to the exact tested working version documented below:

```bash
# Python downgrade command example:
pip install "pydantic==2.14.1" "fastapi==0.143.2"

# Node.js downgrade command example:
npm install "react@19.2.8" "react-dom@19.2.8"
```

---

## 2. Tested Environment Specifications

| Component | Tested Version | Supported Range | Notes |
|:---|:---|:---|:---|
| **Python** | `3.14.6` | `>=3.12, <=3.14.x` | Verified in virtualenv `C:/.venv` |
| **Node.js** | `v24.18.0` | `>=20.0.0, <=24.x` | Active LTS or Current |
| **npm** | `11.12.1` | `>=9.0.0` | Package manager |
| **Docker** | `29.8.2` | `>=24.0.0` | Compose v2 plugin (`docker compose`) |
| **Git** | `2.55.0` | `>=2.25.0` | Version control |
| **Operating Systems** | Windows 11, Windows Server 2019/2022, Debian 12, Ubuntu 24.04 LTS | Standard 64-bit OS |

---

## 3. Backend Python Dependency Matrix

| Package Name | Lowest Limit (`>=`) | Tested Working (`==`) | Role & Downgrade Target |
|:---|:---:|:---:|:---|
| `fastapi` | `>=0.110.0` | `0.143.2` | Core web framework & lifespan routing |
| `uvicorn` | `>=0.28.0` | `0.54.0` | High-performance ASGI production server |
| `sqlalchemy` | `>=2.0.27` | `2.1.4` | SQL ORM & DeclarativeBase models |
| `psycopg2-binary` | `>=2.9.9` | `2.9.13` | PostgreSQL driver for production DB |
| `pydantic` | `>=2.6.3` | `2.14.1` | Schema validation (Pydantic v2 `ConfigDict`) |
| `pydantic-settings` | `>=2.0.0` | `2.16.0` | Environment variable parsing from `.env` |
| `PyJWT` | `>=2.8.0` | `2.15.1` | Cryptographic JWT token encoding & verification |
| `argon2-cffi` | `>=23.1.0` | `25.1.0` | Argon2id password hashing (OWASP ASVS recommended) |
| `pyotp` | `>=2.9.0` | `2.10.0` | RFC 6238 TOTP two-factor authentication |
| `cryptography` | `>=50.0.0` | `50.0.0` | Fernet AES encryption for teacher AI keys (CVE patched) |
| `google-auth` | `>=2.28.0` | `2.62.0` | Google OAuth2 identity authentication |
| `google-auth-oauthlib` | `>=1.2.0` | `1.5.0` | OAuth client consent flow |
| `slowapi` | `>=0.1.9` | `0.1.10` | Endpoint rate limiting protection |
| `aiosmtplib` | `>=3.0.0` | `5.1.3` | Async SMTP email dispatch for password reset |
| `redis` | `>=5.0.0` | `8.1.0` | Real-time WebSocket pub/sub message broker |
| `pytesseract` | `>=0.3.10` | `0.3.13` | Python wrapper for Tesseract OCR |
| `pillow` | `>=10.0.0` | `12.3.0` | Image processing for OCR and exam uploads |
| `presidio-analyzer` | `>=2.2.355` | `2.2.364` | PII entity detector (Microsoft Presidio) |
| `presidio-anonymizer` | `>=2.2.355` | `2.2.364` | PII anonymization engine for essays |
| `python-multipart` | `>=0.0.6` | `0.0.32` | Multipart form parsing |
| `httpx` | `>=0.28.0` | `0.28.1` | Async HTTP client for external AI providers |
| `webauthn` | `>=2.5.0` | `2.8.0` | FIDO2 Passkeys authentication standard |
| `zstandard` | `>=0.23.0` | `0.25.0` | Fast exam package and archive compression |
| `prometheus-client` | `>=0.20.0` | `0.26.0` | Prometheus metrics scraping endpoint |
| `opentelemetry-api` | `>=1.25.0` | `1.45.1` | OpenTelemetry tracing API |
| `opentelemetry-sdk` | `>=1.25.0` | `1.45.1` | OpenTelemetry telemetry runtime |
| `opentelemetry-exporter-prometheus` | `>=0.46b0` | `0.66b1` | Prometheus metric exporter |
| `opentelemetry-instrumentation-fastapi` | `>=0.46b0` | `0.66b1` | Automatic request tracing for FastAPI |
| `opentelemetry-instrumentation-requests` | `>=0.46b0` | `0.66b1` | Automatic HTTP client tracing |
| `opentelemetry-instrumentation-sqlalchemy` | `>=0.46b0` | `0.66b1` | Automatic database query telemetry |

---

## 4. Frontend Portal Dependency Matrix

| Package Name | Range Specifier | Tested Working (`==`) | Role |
|:---|:---:|:---:|:---|
| `react` | `^19.2.8` | `19.2.8` | React component UI framework |
| `react-dom` | `^19.2.8` | `19.2.8` | React DOM renderer |
| `react-router-dom` | `^7.18.4` | `7.18.4` | Client-side routing engine |
| `axios` | `^1.20.0` | `1.20.0` | HTTP request client |
| `idb` | `^8.0.3` | `8.0.3` | IndexedDB offline exam persistence |
| `lucide-react` | `^1.47.0` | `1.47.0` | UI vector iconography |
| `@react-oauth/google` | `^0.13.5` | `0.13.5` | Google Identity Services OAuth component |
| `vite` | `^8.3.0` | `8.3.0` | Frontend bundler & dev server |
| `vite-plugin-pwa` | `^1.3.0` | `1.3.0` | Offline PWA service worker |
| `typescript` | `~6.0.2` | `6.0.2` | Static type checker |
| `oxlint` | `^1.81.0` | `1.81.0` | Rust-based linter |
| `@playwright/test` | `^1.63.0` | `1.64.0` | End-to-end and visual regression testing |

---

## 5. Verification Commands

Run these commands to verify installation and health on any server:

```bash
# 1. Check Python dependencies
python -m pip check

# 2. Run backend test suite with source change tracking
python scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-all" -- python -m pytest tests/ -q

# 3. Build frontend portal
cd web/apps/portal && npm run build
```

