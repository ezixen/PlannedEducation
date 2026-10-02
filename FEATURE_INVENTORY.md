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