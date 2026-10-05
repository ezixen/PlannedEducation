# Planned Education 🎓

**A free, open-source teacher's aid, grading companion, and secure test-taking environment — built with care for teachers and students alike.**

Planned Education exists for a simple reason: **teachers shouldn't have to spend their evenings and weekends buried in grading.** When educators are well-rested and supported, they can show up with more patience, creativity, and heart for the children who need them most. And children? They're our future. 💛

---

## 🌟 What Makes Planned Education Special

### For Teachers — Your Time Matters
- **AI Grading Assistant**: Let AI draft grades and feedback for you to review and approve — one click to apply. You stay in control; the AI just does the heavy lifting.
- **Smart Mistake Grouping**: Instantly see patterns across the class. "These 5 students all struggled with the same concept" — now you can reteach efficiently.
- **Modular Test Packages**: Export your exams as JSON/YAML packages and share them with colleagues. Import packages from others. Build a library once, use it forever.
- **IEP & Accessibility Built-In**: Assign time multipliers (1.5x, 2x) per student globally. No more manual adjustments per exam.
- **OCR & Speech-to-Text**: Handwritten math? Audio responses? Upload and let the system transcribe — you grade the content, not the handwriting.

### For Students — Fair, Secure, Stress-Free
- **Safe Exam Browser Lockdown**: Cryptographically verified. No tab-switching, no screen-sharing, no unauthorized help. Just the exam.
- **Dynamic Randomization**: Every student gets a unique variation. `[rand:1-10]` tags shuffle numbers, options, and question order automatically.
- **Digital Hand Raise**: Stuck? Raise your hand in the secure chat overlay — your teacher sees it instantly without breaking the exam lock.
- **Optional Proctoring (Your Choice, Your Consent)**: Webcam/mic for remote exams — **only with your explicit GDPR consent**. You decide what you're comfortable with. Eye-tracking, multi-face detection, and audio monitoring run locally; only event metadata leaves your device.

### For Parents — Transparency Without Surveillance
- **Read-Only Portal**: See your child's progress, scores, and teacher feedback. No grades are hidden, no data is sold.

### For Everyone — Privacy First, Always
- **Anonymizer API Gateway**: Student names and emails are stripped **before** any AI sees the work. The AI grades the answer, not the child.
- **Zero Paid Services**: Everything runs on free tiers, self-hosted infrastructure, or local models (Ollama). No surprise bills. No vendor lock-in.
- **Google SSO + TOTP 2FA**: Secure, familiar login. Recovery codes for when life happens.

---

## 🛠️ Core Features at a Glance

| Area | What You Get |
|------|--------------|
| **Exam Creation** | Dynamic variables, randomization, rubrics, IEP time multipliers |
| **AI Grading** | Anonymized submissions → AI drafts grades → Teacher reviews → One-click apply |
| **Mistake Analytics** | Automatic grouping of similar errors across the class |
| **Test Packages** | Export/import exams as JSON or YAML (compressed optional). Share, version, reuse. |
| **Secure Exam Mode** | SEB cryptographic lock, digital hand raise, offline PWA support |
| **Proctoring (Opt-In)** | GDPR consent flow → Face detection → Eye-gaze tracking → Multi-face alerts → Audio anomaly detection → All events timestamped & auditable |
| **OCR & STT** | Tesseract math OCR + faster-whisper speech-to-text |
| **Auth** | Google OAuth primary, TOTP 2FA, recovery codes, email OTP password reset |
| **Database** | PostgreSQL (prod) / SQLite (dev) via SQLAlchemy |

---

## 🚀 Quick Start (Local Development)

> **Prerequisites**: Docker Desktop, Node.js 20+, Python 3.12+

```powershell
# 1. Start the database & cache
docker compose up -d postgres redis

# 2. Launch the backend API + frontend portal
.\start.ps1
```

- **Backend API docs**: http://localhost:8001/docs
- **Frontend portal**: http://localhost:5175

**Verify everything's healthy:**
```powershell
python scripts\testing\canary.py
```

**When you're done:**
```powershell
Stop-Process -Name python,node -ErrorAction SilentlyContinue
```

---

## 📦 Test Packages — Share & Reuse

Create an exam once. Export it as a package. Share with your department. Import a colleague's package and adapt it.

```bash
# Export (from Teacher Dashboard → Package Manager)
# → JSON or YAML, with/without answers, gzip optional

# Import (drag & drop in Package Manager)
# → Validates structure, checksums, creates new exam with all questions & rubrics
```

Packages include:
- Exam metadata (title, duration, settings, IEP config)
- All questions (multiple choice, essay, dynamic math with variables)
- Rubrics with criteria & keywords
- SHA-256 checksum for integrity

---

## 🔒 Proctoring — Transparent & Consent-Driven

We believe proctoring should be **opt-in, transparent, and privacy-respecting**.

1. **Student sees a clear GDPR consent modal** explaining exactly what data is collected (face presence, gaze coordinates, face count, audio volume levels — no video/audio recordings stored).
2. **Student chooses** which sensors to enable (camera, microphone, screen monitoring).
3. **During the exam**, events are recorded locally and batched to the server every 5 seconds.
4. **Teachers see only aggregated stats**: violation counts, max faces detected, event timeline — never raw video.

**Event types recorded**: `face_detected`, `face_lost`, `multiple_faces`, `eye_movement`, `gaze_off_screen`, `audio_anomaly`, `tab_switch`, `window_blur`, `fullscreen_exit`, `seb_violation`.

---

## 🏗️ Architecture (For the Curious)

```
┌─────────────────────────────────────────────────────────────┐
│                    Planned Education                         │
├─────────────────────┬─────────────────────┬─────────────────┤
│   Frontend (PWA)    │   Backend (FastAPI) │  Infrastructure │
│   React 18 + Vite   │   Python 3.12       │  Docker Compose │
│   TypeScript        │   SQLAlchemy        │  PostgreSQL     │
│   React Router      │   Pydantic          │  Redis          │
│   Workbox SW        │   Presidio (PII)    │  nginx (prod)   │
└─────────────────────┴─────────────────────┴─────────────────┘
```

**Key backend modules:**
- `routes_auth.py` — Google SSO, TOTP 2FA, password reset
- `routes_exam.py` — Exam lifecycle, SEB config, submissions
- `routes_anonymizer.py` — PII stripping proxy for AI
- `routes_proctoring.py` — Consent, sessions, events, stats (22 tests!)
- `routes_packages.py` — Export/import/validate test packages
- `routes_ocr.py` / `routes_stt.py` — Math OCR & speech-to-text
- `routes_chat.py` — Secure WebSocket hand-raise
- `ocr_service.py` / `stt_service.py` — Local ML pipelines

---

## 🤝 Contributing

We welcome contributions! Whether it's:
- 🐛 Bug fixes
- ✨ New features (especially accessibility improvements)
- 📝 Documentation & translations
- 🧪 Tests
- 💡 Ideas for reducing teacher workload

Please read `agents.md` for our coding standards and `docs/` for architecture guides.

**Our promise**: No paid dependencies. Ever. If it can't run free, it doesn't go in.

---

## 📜 License

MIT License — use it, modify it, share it. Just keep it free for educators.

---

## 💬 A Personal Note

This project started because a teacher friend said: *"I love teaching. I hate grading. I miss my evenings."*

If Planned Education gives even one teacher an extra hour with their family, or one student a fairer exam experience, it's worth every line of code.

**Children are our future. Let's give them teachers who are rested, supported, and ready to inspire.** 🌱

---

*Built with ☕ and 💛 for the future of equitable education.*

