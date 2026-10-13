# PlannedEducation FAQ - Searchable Reference

This document contains all FAQ entries in a searchable format. Use Ctrl+F to find specific topics.

---

## Getting Started

### How do I create an exam?
To create an exam, go to the Teacher Dashboard, click 'Create New Exam', fill in the exam details, add questions, and save. You can also import questions from a question bank.

### How do students join an exam?
Students receive an exam code or link from their teacher. They can join by visiting the PlannedEducation portal and entering the exam code, or by clicking the direct link provided by the teacher.

### What is the Secure Exam Browser (SEB)?
The Secure Exam Browser is a locked-down browser environment that prevents students from accessing other applications or websites during an exam, ensuring test integrity and preventing cheating.

### How do I create a question bank?
Go to Teacher Dashboard > Question Banks > 'New Bank'. Name it, add subject/tags, then add questions. You can import from existing exams or create new questions.

### What are reusable modules?
Modules are self-contained question sets with shared context (e.g., a reading passage with 5 questions). Create them in the Exam Editor > 'Create Module', add context and questions, then reuse across exams.

---

## Account & Security

### How do I reset my password?
Click 'Forgot Password' on the login page, enter your email address, and follow the instructions sent to your email to reset your password.

### How do I enable two-factor authentication?
Go to Settings > Security, click 'Enable 2FA', scan the QR code with your authenticator app, and enter the verification code to complete setup.

### What are Passkeys and how do I use them?
Passkeys are a passwordless authentication method using biometrics or device PIN. You can set them up in Settings > Passkeys by registering your device's biometric authentication. Passkeys sync across devices via iCloud Keychain or Google Password Manager.

### How do I register a Passkey?
Go to Settings > Passkeys, click 'Register Passkey', and use your device's biometric (fingerprint, face ID) or PIN to create the passkey. It will sync across your devices automatically.

---

## Exams & Grading

### How does AI-assisted grading work?
Teachers can configure their preferred AI provider (Gemini, OpenRouter, Ollama, etc.) in Settings. When grading exams, the AI provides suggestions that teachers can review, edit, or approve before finalizing grades.

### Can I grade exams offline?
Yes! PlannedEducation supports offline-first exam taking. Students can take exams without internet connection, and their answers are saved locally and synced when connection is restored.

### How do I view student submissions?
After students submit exams, go to Teacher Dashboard, select the exam, and click 'View Submissions' to see all student answers and AI-generated feedback.

### Which AI providers are supported?
Gemini (Google), OpenRouter (100+ models), Ollama (local), OpenAI-compatible endpoints, and ChatGPT session (device-code OAuth). Configure in Settings > AI Key Management.

### How does the AI grading review workflow work?
AI provides score, feedback, confidence, and reasoning for each question. Teachers can Approve (accept as-is), Edit (modify score/feedback), or Reject (grade manually). Bulk actions: 'Approve All High Confidence' or 'Flag Low Confidence for Review'.

### What are the AI safety controls?
Prompt injection detection (20+ patterns), hallucination detection via consistency checking, output schema validation, confidence threshold (min 0.75), rate limiting (20/min, 200/hour), cost tracking ($5/day budget), provider health monitoring with automatic fallback.

---

## Test Packages & Sharing

### How do I export a test package?
Open an exam in the Exam Editor, click 'Export Package', choose JSON or YAML format, select options (include answers, rubrics, variables), and download the .pepkg.json file.

### How do I import a test package?
Go to Teacher Dashboard > 'Import Package', drag the .pepkg.json/.yaml file, preview the contents, choose import options (new exam, add to existing, import modules/questions), and confirm.

### What is the pepkg CLI?
The pepkg CLI is a command-line tool for managing test packages: export/import/validate/list/download packages, publish/unpublish, search, and local validation. Install with 'pip install -e ./pepkg'.

### How do I share packages with colleagues?
Send .pepkg.json via email/shared drive/USB, or use the pepkg CLI to publish to the registry. Recipients import via 'Import Package' or 'pepkg install'.

---

## Proctoring & Monitoring

### How do I enable proctoring for an exam?
In exam settings, enable 'Proctoring'. Students will be prompted for camera/microphone permissions and must complete GDPR consent. Events tracked: eye movement, multiple faces, background audio, tab switches, SEB violations.

### What proctoring events are tracked?
Eye movement (gaze tracking), multiple face detection, background audio levels, tab/window switches, SEB violations. View in Teacher Dashboard > Proctoring tab with real-time feed and session replay.

---

## Technical Support

### What browsers are supported?
PlannedEducation works best with modern browsers: Chrome, Firefox, Safari, and Edge. For secure exams, we recommend using the Secure Exam Browser (SEB) or Chrome Canary for development.

### Is my data private and secure?
Yes! PlannedEducation is privacy-first and open-source. All data is stored locally or on your self-hosted server. We use end-to-end encryption for sensitive data and never sell or share your information.

### How do I get help or report issues?
For technical issues, check the documentation in the docs/ folder. For feature requests or bug reports, visit our GitHub repository and open an issue.

### What are the system requirements?
Backend: Python 3.12+, PostgreSQL 16, Redis 7. Frontend: Node.js 20+. For SEB: Windows/macOS with SEB installed. For proctoring: camera + microphone permissions.

### How do I deploy to production?
Use Docker Compose with docker-compose.yml + docker-compose.prod.yml. Set environment variables (JWT_SECRET_KEY, DATABASE_URL, etc.). Run migrations with alembic. Build frontend with 'npm run build'. Use Nginx/Caddy reverse proxy with Let's Encrypt TLS.

---

## Quick Keyword Index

| Keyword | FAQ IDs |
|---------|---------|
| exam | 1, 2, 3, 7, 8, 9, 16, 17, 18 |
| student | 2, 8, 9, 23, 24 |
| teacher | 1, 7, 9, 16, 17, 18, 23 |
| AI | 7, 16, 17, 18 |
| grading | 7, 8, 9, 16, 17, 18 |
| offline | 8 |
| SEB | 3, 23, 24 |
| proctoring | 23, 24 |
| Passkeys | 6, 15 |
| 2FA | 5 |
| password | 4 |
| package | 19, 20, 21, 22 |
| pepkg | 21, 22 |
| sharing | 22 |
| export | 19 |
| import | 20 |
| question bank | 13 |
| module | 14 |
| Passkeys | 6, 15 |
| 2FA | 5 |
| password reset | 4 |
| browser | 10 |
| privacy | 11 |
| help | 12 |
| system requirements | 25 |
| deployment | 26 |
| proctoring | 23, 24 |
| GDPR | 23 |
| camera | 23, 24 |
| microphone | 23, 24 |
| eye tracking | 24 |
| face detection | 24 |
| audio | 24 |
| tab switching | 24 |
| violation | 24 |
| Google SSO | - |
| TOTP | 5 |
| recovery codes | 5 |
| biometric | 6, 15 |
| iCloud | 6, 15 |
| Google Password Manager | 6, 15 |
| Gemini | 16 |
| OpenRouter | 16 |
| Ollama | 16 |
| OpenAI | 16 |
| ChatGPT | 16 |
| hallucination | 18 |
| prompt injection | 18 |
| rate limiting | 18 |
| cost tracking | 18 |
| provider health | 18 |
| fallback | 18 |
| confidence | 17, 18 |
| review workflow | 17 |
| bulk actions | 17 |
| pepkg CLI | 21 |
| registry | 22 |
| search | 22 |
| validate | 21 |
| publish | 22 |
| unpublish | 22 |
| export | 19 |
| import | 20 |
| question bank | 13 |
| module | 14 |
| reusable | 14 |
| context | 14 |
| dynamic math | - |
| variable | - |
| randomization | - |
| multiple choice | - |
| essay | - |
| file upload | - |
| audio response | - |
| STT | - |
| OCR | - |
| handwritten | - |
| math | - |
| LaTeX | - |
| speech-to-text | - |
| faster-whisper | - |
| Tesseract | - |
| Presidio | - |
| PII | - |
| anonymizer | - |
| Fernet | - |
| Argon2id | - |
| JWT | - |
| HS256 | - |
| TLS | - |
| CSP | - |
| HSTS | - |
| OWASP | - |
| NIST | - |
| AI RMF | - |
| SSDF | - |
| CSF | - |
| SLSA | - |
| cosign | - |
| SBOM | - |
| Trivy | - |
| bandit | - |
| pip-audit | - |
| npm audit | - |
| gitleaks | - |
| Dependabot | - |
| OpenTelemetry | - |
| Prometheus | - |
| Grafana | - |
| Alertmanager | - |
| SLO | - |
| burn rate | - |
| burn-rate | - |
| latency | - |
| availability | - |
| error rate | - |
| cost | - |
| budget | - |
| provider health | 18 |
| fallback | 18 |
| manual grading | 18 |
| teacher approval | 17 |
| anonymizer | - |
| Presidio | - |
| PII scrubber | - |
| encryption | - |
| Fernet | - |
| AES-128 | - |
| AI key | - |
| master secret | - |
| Google SSO | - |
| OAuth2 | - |
| OIDC | - |
| TOTP | 5 |
| RFC 6238 | 5 |
| pyotp | 5 |
| recovery codes | 5 |
| Passkeys | 6, 15 |
| WebAuthn | 6, 15 |
| FIDO2 | 6, 15 |
| platform authenticator | 6, 15 |
| cross-device sync | 6, 15 |
| iCloud Keychain | 6, 15 |
| Google Password Manager | 6, 15 |
| Windows Hello | 6, 15 |
| Touch ID | 6, 15 |
| Android biometrics | 6, 15 |
| phishing-resistant | 6, 15 |
| OWASP A07 | 6, 15 |
| NIST AI RMF | - |
| Generative AI Profile | - |
| NIST SSDF | - |
| NIST CSF | - |
| OWASP Top 10 | - |
| OpenTelemetry | - |
| Prometheus | - |
| Grafana | - |
| Alertmanager | - |
| SLO | - |
| burn rate | - |
| latency | - |
| availability | - |
| error rate | - |
| cost | - |
| budget | - |
| provider health | 18 |
| fallback | 18 |
| manual grading | 18 |
| teacher approval | 17 |
| anonymizer | - |
| Presidio | - |
| PII scrubber | - |
| encryption | - |
| Fernet | - |
| AES-128 | - |
| AI key | - |
| master secret | - |
| Google SSO | - |
| OAuth2 | - |
| OIDC | - |
| TOTP | 5 |
| RFC 6238 | 5 |
| pyotp | 5 |
| recovery codes | 5 |
| Passkeys | 6, 15 |
| WebAuthn | 6, 15 |
| FIDO2 | 6, 15 |
| platform authenticator | 6, 15 |
| cross-device sync | 6, 15 |
| iCloud Keychain | 6, 15 |
| Google Password Manager | 6, 15 |
| Windows Hello | 6, 15 |
| Touch ID | 6, 15 |
| Android biometrics | 6, 15 |
| phishing-resistant | 6, 15 |
| OWASP A07 | 6, 15 |
| NIST AI RMF | - |
| Generative AI Profile | - |
| NIST SSDF | - |
| NIST CSF | - |
| OWASP Top 10 | - |
| OpenTelemetry | - |
| Prometheus | - |
| Grafana | - |
| Alertmanager | - |
| SLO | - |
| burn rate | - |
| latency | - |
| availability | - |
| error rate | - |
| cost | - |
| budget | - |

---

*Last updated: 2026-10-13*
*Version: 1.1*
*Total FAQs: 26*