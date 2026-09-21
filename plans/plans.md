# PlannedEducation - Technical Implementation Plan

## 1. Project Goal & Overview
PlannedEducation aims to revolutionize test-taking and grading by providing a secure, open-source framework for schools. The system will provide a secure test-taking executable that prevents cheating and a grading system utilizing AI text recognition and text-to-speech features.

This document serves as the master plan for implementing the application using modern best practices, focusing on PC environments (Windows/Linux, MacOS coming later).

## 2. Architecture & Tech Stack
- **Frontend / Client UI**: React + TypeScript + Vite.
  - Follows WIWM conventions: Hamburger menu style, explicit theming support (`theme_mode`, `skin_id`), and nested submenus within Settings.
  - **Offline Capability**: Utilizes PWA Service Workers and IndexedDB to cache tests locally. If network drops, progress is saved locally and synced once reconnected.
- **Desktop Executable (Anti-Cheating Kiosk)**: **Safe Exam Browser (SEB)**. 
  - Instead of building a custom locking wrapper from scratch, we will integrate with the open-source SEB ecosystem. PlannedEducation will act as the master server that generates custom `.seb` configuration files to launch the SEB client securely on Windows/MacOS/iOS.
- **Backend / API**: Python FastAPI (`src/plannededucation/api`).
- **Database**: Cloud SQL / PostgreSQL or Firestore (depending on infrastructure choices, following ELA conventions).

## 3. Secure Kiosk / Exam Mode (SEB Integration)
We will leverage **Safe Exam Browser (SEB)** to handle the OS-level lockdown, preventing us from needing to maintain complex C# or C++ locking hooks across multiple operating systems.

### Capabilities Provided by SEB out-of-the-box:
1. **Full-Screen Lock**: The app occupies the full screen and prevents minimizing or task switching.
2. **Shortcut Blocking**: Disables `Alt+Tab`, `Ctrl+Alt+Del`, `Win` key, and other OS-level escapes.
3. **App Monitoring**: Monitors and blocks blacklisted processes (e.g., screen recording, remote desktop).
4. **VM Detection**: Prevents running inside a Virtual Machine or Sandbox.
5. **Config & Keys**: Uses robust cryptographic keys (Browser Exam Key & Config Key) so the backend can verify the student is actually using the locked-down SEB client and not a standard Chrome browser.

### Edge Cases & Contingencies (Handled by our Portal inside SEB):
- **Power Outage / App Crash / Accidental Restart**: The test state is constantly auto-saved to IndexedDB via the frontend. Resuming the exam requires a Teacher/Admin password intervention via our backend logic.
- **Network Drops**: If the internet disconnects, the React Service Worker intercepts network requests and saves them locally. The exam is not interrupted. Once online, it syncs.
- **Hardware Failures**: Keyboards disconnecting or mouse freezing must be handled gracefully without kicking the student out of the test environment.

## 4. Grading & Teacher Aid Features
- **AI Text Recognition (OCR & GenAI)**: Teachers can take pictures of handwritten exams or essays, and the backend will process them to recognize key phrases, dates, equations, and solutions.
- **Text-to-Speech (TTS)**: The software will read essays out loud to the teacher.
- **Voice Commands**: Teachers can use voice commands to add notes, remarks, or correct the AI's grading.
- **TA Handoff**: Tests can be securely emailed or transferred to Teaching Assistants (TAs) for collaborative grading. No post-grading modifications allowed by unauthorized users.

## 5. Longer Term Vision: Job Statistics
- Collect and display averages/statistics of professionals in various fields based on their past academic performance.
- Serve as an inspirational tool to show students real-world paths to their desired careers (e.g., doctors, athletes, engineers) and the required academic milestones.

## 6. Folder Structure & Documentation Strategy
Follows the ELA (EasyLegalAid) structure:
- **`web/apps/portal/`**: The student/teacher web portal and desktop UI.
- **`web/apps/admin/`**: High-level admin management.
- **`src/`**: Backend API codebase.
- **`docs/public-user/`**: Product English only. End-user guides (students, teachers) and FAQ.
- **`docs/admin-user/`**: Operator and school administrator docs.
- **`docs/ai-internal-functional/`**: Technical specs, how-it-works, architecture details.
- **`plans/`**: Master plans, ExecutionStatus, tracking.

## 7. Execution Steps
- **Step 1**: Scaffold the repository, initialize the Git project, create `web/apps/portal` (Vite) and backend API.
- **Step 2**: Implement the basic UI layout (Hamburger menu, themes, settings submenus).
- **Step 3**: Setup the Desktop wrapper (Tauri/Electron) and implement the OS-level lock (Kiosk mode).
- **Step 4**: Develop the test delivery and offline-capable auto-save mechanisms.
- **Step 5**: Build the teacher grading interface and integrate AI OCR and TTS APIs.
- **Step 6**: Beta testing in a controlled school environment.

