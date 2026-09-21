# PlannedEducation - Technical Implementation Plan

## 1. Project Goal & Overview
PlannedEducation aims to revolutionize test-taking and grading by providing a secure, open-source framework for schools. The system combines a secure kiosk test-taking environment (preventing cheating) with powerful, **privacy-first AI grading tools** to save teachers hours of work.

## 2. Architecture & Tech Stack
- **Frontend / Client UI**: React + TypeScript + Vite.
  - Follows WIWM conventions: Hamburger menu style, explicit theming support (`theme_mode`, `skin_id`), and nested submenus within Settings.
  - **Offline Capability**: Utilizes PWA Service Workers and IndexedDB to cache tests locally. If the network drops, progress is saved locally and synced once reconnected.
- **Desktop Executable (Anti-Cheating Kiosk)**: **Safe Exam Browser (SEB)**. 
  - We integrate with the open-source SEB ecosystem. PlannedEducation generates `.seb` configuration files to launch the SEB client securely on PC/Mac.
- **Backend / API**: Python FastAPI (`src/plannededucation/api`).
- **Database**: Cloud SQL / PostgreSQL (via SQLAlchemy) to handle relational data (Users, Tests, Grades).

## 3. Secure Kiosk & Anti-Cheating (SEB + Custom Security)
We leverage **Safe Exam Browser (SEB)** to handle the OS-level lockdown (Full screen, blocking Alt+Tab/Task Manager, VM detection). 

### Custom Security Layers Added:
1. **Cryptographic Validation**: The FastAPI backend verifies the SEB Config Key Hash to ensure the student is actually using the locked browser, not Chrome/Edge.
2. **Dynamic Screen Watermarking**: The student's ID/name is subtly watermarked across the screen to trace illicit smartphone photos.
3. **Optional AI Webcam & Audio Proctoring**: An optional toggle for remote exams. Tracks eye movement, multiple faces, and background audio. *Note: Heavily warned regarding GDPR and privacy, as it is not strictly necessary for in-person exams.*
4. **Secure "Digital Hand Raise" Chat**: Borrowing architecture from the WIWM project's DM system. A secure, locked-down WebSocket chat allowing students to ping the teacher for clarification without exiting the exam.

## 4. Test Creation & Delivery (LMS Core)
1. **Question Banks & Randomization**: Pulls 10 questions randomly from a pool of 50 and scrambles multiple-choice answers, ensuring unique tests for adjacent students.
2. **Dynamic Math/Variable Questions**: Changes numbers in equations per student (e.g., `2x + 4 = 10` vs `3x + 6 = 15`) to prevent copying final answers.
3. **Student Accommodations**: Built-in toggles for specific students (e.g., IEPs) to automatically receive 1.5x or 2.0x time on timed exams.

## 5. Teacher AI Grading & Audio Tools (Privacy-First)
All AI features utilize a free external AI API. **CRITICAL: AI processing is 100% anonymous.** No Personal Identifiable Information (PII) is ever sent to the external AI. The AI can only read, analyze, and generate files to simplify grading.

1. **AI Answer Grouping**: Groups similar handwritten math/text mistakes so the teacher writes feedback once for the entire group.
2. **AI Pre-Grading via Rubrics**: The anonymized text is checked against a rubric. The AI suggests a score; the teacher approves.
3. **Math OCR**: Translates messy handwritten math into digital text/LaTeX for the AI to analyze.
4. **Blind Grading**: Hides student names during the manual grading phase to eliminate bias.
5. **Plagiarism & AI Detection**: Scans submissions for external AI/copy-pasting.
6. **Audio Feedback & Speech-to-Text**: Teachers can record audio memos for feedback. Integrated speech recognition translates teacher speech to text for faster grading note generation.

## 6. Portals & Roles
1. **Student**: Test-taking interface inside SEB, and dashboard for upcoming tests.
2. **Teacher**: Test creation, class groupings, secure chat monitoring, and AI grading dashboard.
3. **Parent/Guardian Portal**: A secure, **read-only** login for parents to track their child's test scores and teacher feedback.
*Note: There is NO Admin portal. The system is entirely self-managed by teachers to remain open-source. Administration relies on automated workflows (Lost password flows, TOTP 2FA).*

## 7. Open Source Modular Extensions
Teachers can share and download custom test modules or rubrics.
**CRITICAL SECURITY CONSTRAINT**: To prevent malicious supply-chain attacks, modules are strictly data-definitions (e.g., JSON/YAML test templates). **NO executable code** (Python/JS/WASM) can be uploaded or shared through the modular system to prevent backdoors infecting student computers.

## 8. Execution Order (The Roadmap)
1. **Phase 1: Foundation**: Database models, Authentication (Google SSO + Standard + TOTP 2FA), and the React Vite Portal Shell (Routing, Hamburger Menu, Themes).
2. **Phase 2: Core Exam Engine**: Test creation, Class Groupings, Question Banks, Variables, Accommodations, and offline PWA support.
3. **Phase 3: Security Integration**: SEB header validation, Screen Watermarking, and the Secure Chat (WIWM port).
4. **Phase 4: AI & Grading**: Anonymization pipeline, external AI integration, OCR, Audio/Speech-to-text, and the Teacher Dashboard.
5. **Phase 5: Optional Proctoring**: The WebRTC/Webcam AI proctoring toggle with GDPR compliance flags.
