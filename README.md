# PlannedEducation 🎓

PlannedEducation is a modern, open-source teacher's aid, grading software, and secure test-taking environment. It is designed to provide teachers with powerful tools to manage classes and automate grading without compromising student privacy or test integrity.

## 🌟 Main Goals

1. **Uncompromising Exam Security**: Lock down student devices during exams using cryptographically verified Safe Exam Browser (SEB) integrations, preventing cheating, unauthorized task switching, or AI-assistance.
2. **Absolute Data Privacy**: Decouple Student Personally Identifiable Information (PII) from AI. We utilize an innovative **Anonymizer API Gateway** that strips names and emails before external AI models ever see the data.
3. **Equitable Accessibility**: Built-in support for Individualized Education Programs (IEPs), allowing teachers to globally assign time multipliers (e.g., 1.5x time) to specific students.
4. **Parental Transparency**: A secure, read-only portal for parents and guardians to track their child's academic progress, exam scores, and teacher feedback.

---

## 🛠️ Core Services & Functions

### 1. The Teacher Portal (React + Vite)
- **Exam Editor**: Create dynamic exams utilizing `[rand:1-10]` tags to mathematically generate unique variations of questions for every student.
- **Class Groupings**: Group students into classes, manage rosters, and assign IEP accessibility settings.
- **AI Integration Hub**: Generate strict grading rubrics and provide anonymized access tokens to external AI grading scripts (compatible with Gemini, OpenAI, Ollama, etc.).

### 2. The Secure Student Exam Environment
- **Dynamic Randomization**: Answers are automatically scrambled and math variables are randomized to prevent screen-peeking.
- **Cryptographic Locks**: The `/exams/{id}/start` API endpoint will reject any requests that do not originate from an approved, locked-down Safe Exam Browser profile.
- **Digital Hand Raise**: A WebRTC/WebSocket secure chat overlay allows students to ask the teacher questions without breaking the browser lock.

### 3. The Backend Engine (Python FastAPI & PostgreSQL)
- **Robust Architecture**: Built on FastAPI and SQLAlchemy, defaulting to PostgreSQL for production deployments.
- **The Anonymizer API**: A specialized proxy layer that acts as a secure air-gap between student tests and external AI models.
- **Stateless Authentication**: Purely Google SSO driven with Auth App 2FA. (We intentionally omit email services to cut costs and reduce attack surfaces).

---

## 🚀 How to Run Locally

We provide clean, localized PowerShell scripts to spin up the entire ecosystem on your machine without needing a cloud database. The local environment safely falls back to a temporary SQLite database.

1. **Start the Environment:**
   Run the background startup script from the root directory:
   ```powershell
   .\scripts\local\start.ps1
   ```
   *The backend will be available at `http://localhost:8000/docs` and the frontend at `http://localhost:5173`.*

2. **Verify Health:**
   Run the canary debug script to ensure the local ports are responding correctly:
   ```powershell
   python scripts\testing\canary.py
   ```

3. **Stop the Environment:**
   When you're finished, forcefully spin down the node and python background processes:
   ```powershell
   .\scripts\local\stop.ps1
   ```

---

## 🔮 Future Plans

- **Cross-Platform Native Wrappers**: Wrapping the web portals into native Desktop Executables via Tauri/Electron for Windows, Linux, and macOS to natively monitor and prevent screen-sharing apps during exams.
- **Job Inspiration & Analytics**: Analyzing student performance over time to provide inspirational career path suggestions based on their strongest aptitudes.
- **Decentralized Question Banks**: Allowing teachers to securely share modular test packages and JSON/YAML data definitions globally.

---

### Contributing & Questions
If you have questions about extending the AI integrations, setting up a Safe Exam Browser profile, or contributing to the codebase, please review the architecture guidelines in `AGENTS.md` and `docs/`.

*Built for the future of equitable education.*

