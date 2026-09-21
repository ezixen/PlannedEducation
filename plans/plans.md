# PlannedEducation - Technical Implementation Plan

## 1. Project Goal & Overview
PlannedEducation aims to revolutionize test-taking and grading by providing a secure, open-source framework for schools. The system will provide a secure test-taking executable that prevents cheating and a grading system utilizing AI text recognition and text-to-speech features.

This document serves as the master plan for implementing the application using modern best practices, focusing on PC environments (Windows/Linux, MacOS coming later).

## 2. Architecture & Tech Stack
- **Frontend / Client UI**: React + TypeScript + Vite.
  - Follows WIWM conventions: Hamburger menu style, explicit theming support (`theme_mode`, `skin_id`), and nested submenus within Settings.
- **Desktop Executable**: **Tauri** or **Electron**. Tauri is recommended for a smaller footprint and better integration with OS-level locking features via Rust, which is ideal for a secure exam environment.
- **Backend / API**: Python FastAPI (`src/plannededucation/api`).
- **Database**: Cloud SQL / PostgreSQL or Firestore (depending on infrastructure choices, following ELA conventions).

## 3. Secure Kiosk / Exam Mode (Anti-Cheating)
The core feature of the desktop app is its ability to lock down the PC during a test.
### Capabilities Required:
1. **Full-Screen Lock**: The app must occupy the full screen and prevent minimizing or switching.
2. **Task Manager & Shortcut Blocking**: Disable `Alt+Tab`, `Ctrl+Alt+Del`, `Win` key, `Cmd` key, and other OS-level escape sequences.
3. **App Monitoring**: Monitor running processes. If blacklisted processes (e.g., screen recording, remote desktop, chat applications) are detected, block the test and alert the teacher.
4. **Multi-Monitor Handling**: Blank out or disable secondary monitors to prevent hidden reference materials.
5. **VM & Sandbox Detection**: Prevent running inside a Virtual Machine or Sandbox to avoid host-level cheating (e.g., running the VM in a window while googling on the host).
6. **Clipboard Clearing**: Clear clipboard on test start and disable copy-paste functions.
7. **Network Whitelisting**: Disable external network access except for the PlannedEducation backend API.

### Edge Cases & Contingencies:
- **Power Outage / App Crash / Accidental Restart**: The test state must be constantly auto-saved locally (encrypted) or to the backend. If a restart occurs, resuming requires a Teacher/Admin password since the student has already started a test that day.
- **Network Drops**: If the internet disconnects, the test must continue locally in encrypted storage and sync once reconnected, without penalizing the student.
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
