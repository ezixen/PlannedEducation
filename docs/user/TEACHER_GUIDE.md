# PlannedEducation — Teacher Guide 🍎

> Complete handbook for teachers and educators using PlannedEducation.
> Covers exam authoring, question banks, AI-assisted grading, classroom monitoring, and emergency student unlocks.

---

## 1. Getting Started & Account Approval

### Self-Registration
1. Navigate to `/register` and select **Teacher**.
2. Enter your email, username, full name, and a secure password.
3. **5 Recovery Codes**: Print or securely store your 5 one-time recovery codes displayed upon registration. These allow you to reset your password instantly at any time without waiting for an administrator.
4. **Administrator Verification Gate**:
   - To safeguard school exam integrity and prevent students from prank-registering as teachers to inspect exam questions or answer keys, all self-registered teachers require one-click administrator approval before gaining exam creation rights.
   - Once approved by a school administrator, your teacher status becomes active immediately.

---

## 2. Classroom & Student Management

### Creating Classes
1. In the sidebar, navigate to **Classes**.
2. Click **Create Class**, enter the class name, grade level, and subject.
3. Share the class join code with your students, or add student accounts directly.

### Pre-Exam Emergency Password Reset ("⚡ Reset Pwd for Test")
Right before a scheduled exam, students frequently forget their passwords and panic under time pressure. PlannedEducation eliminates exam delays with a single-click teacher unlock:
1. In **Teacher Dashboard → Real-Time Student Monitoring** or **Classes → Manage Students**, locate the locked-out student in your roster.
2. Click the yellow **"⚡ Reset Pwd for Test"** button next to their name.
3. Confirm the quick reset dialog.
4. **Student Next Step**: Instruct the student to open the login page (`/login`) and enter their school email. The system immediately detects the active teacher unlock (`TEACHER_RESET_ACTIVE`), highlights the form in green, and prompts the student to type a new password right in the login card.
5. Upon typing their password and clicking **"Set Password and Sign In"**, the student is immediately authenticated and admitted directly into the test session.

---

## 3. Exam Authoring & Dynamic Math Variables

### Question Types Supported
- **Multiple Choice (Single & Multi-Select)**: Auto-graded instantly.
- **Short Answer**: Keyword and regex matching.
- **Essay & Long Form**: Detailed rubrics with AI-assisted drafting and teacher review.
- **Math & Chemistry**: LaTeX notation with dynamic numerical variables.

### Dynamic Math Variables & Seeded Formulas
To prevent students sitting next to each other from copying answers:
- Embed variables inside brackets: e.g. `Solve for x: {a}x + {b} = {c}`
- Configure variable ranges and step sizes (e.g. `a: 2..10`, `b: 1..20`).
- Specify formulas for automated evaluation (e.g. `x = (c - b) / a`).
- Each student receives a deterministically seeded set of numbers so that exam questions remain identical in concept while values differ per workstation.

### Curriculum Modules & Question Banks
- Group related questions into reusable **Modules** (e.g. *Unit 3: Quadratic Equations* or *Cell Biology*).
- Tag questions by difficulty, IEP accommodation, and curriculum standard.
- Import/export test packages using the standardized `.pepkg` format to share curriculum with colleagues across your school or district.

---

## 4. Secure Exam Browser (SEB) & Lockdown Mode

PlannedEducation natively supports **Safe Exam Browser (SEB)** to guarantee a secure, locked-down testing environment:
1. When publishing an exam, toggle **Require Safe Exam Browser**.
2. Download the pre-configured `.seb` file or distribute the direct SEB launch link to students.
3. During the exam:
   - OS shortcuts (Alt+Tab, Windows Key, Ctrl+Alt+Del) are disabled.
   - Screen capture, virtual machines, and external monitors are restricted.
   - Network requests are strictly pinned to the PlannedEducation exam server.
4. **Emergency Exit**: If a workstation encounters a hardware fault or restarts, the student re-authenticates with SEB or requests teacher intervention without losing already saved answers.

---

## 5. Archive Browser & AI-Assisted Grading Workflow

PlannedEducation provides a comprehensive **Archive Browser & AI Grading Pipeline** built directly into the Teacher Dashboard:

### 1. The Archive Browser
- View all completed class exam submissions and offline uploaded test packages in one centralized table.
- Filter by Exam, Year, Month, or Status:
  - `ungraded` (Gray: *Submitted / Needs Grading*)
  - `pending_approval` (Amber: *AI Corrected — Staged in Temp Folder, Pending Teacher Review*)
  - `graded` (Green: *Graded & Sealed in Archive*)
- Multi-select checkboxes allow batch operations across multiple student submissions.

### 2. Privacy-Preserving AI Grading (Zero PII Exposure)
- Select one or more tests and click **"🤖 AI Correct Selected"**.
- **Microsoft Presidio PII Scrubber**: Automatically sanitizes all student personal identifying information (names, email addresses, phone numbers, locations, dates, IDs) from responses and prompts before external evaluation.
- The AI evaluates each answer against your rubric or correct answer, provides constructive feedback, explains mistakes, suggests step-by-step solutions, and proposes scores.
- **Local Fallback**: If no external AI key is configured, PlannedEducation uses a deterministic local rubric matcher so the system works 100% offline.

### 3. Temporary Staging in Temp Folder (`pending_approval`)
- Returned AI suggestions and grades are placed in a secure temporary staging folder on disk: `data/staging_archive/{teacher_id}/{submission_id}.json`.
- The submission status moves to **"AI Corrected (Pending Approval)"**.
- Student identities remain safely mapped in the local database for teacher-only view, while remaining completely hidden from external models.

### 4. Teacher Review & Correction Modal
- Click **"✏️ Review & Correct"** to open the interactive **TeacherCorrectionModal**.
- Side-by-side comparison:
  - **Left**: Original student submission and rubric points.
  - **Right**: AI evaluation, confidence indicator, and step-by-step suggestions.
  - **Bottom/Editor**: Quick feedback chips ("Excellent step-by-step work!", "Correct method, minor arithmetic error", etc.), score adjustments, and solution overrides.
- Teachers can approve questions individually or click **"✓ Approve All & Save Corrected Exam"**.

### 5. Sealing & Encrypted Archiving
- When approved, final scores and feedback are written to the database.
- The test is compressed using **zstandard (zstd)** and encrypted using **AES-GCM**.
- SHA-256 integrity hashes are computed and recorded in `ArchivedSubmission`.
- The temporary staging file is safely cleaned up, and the test is marked **"Graded & Sealed"** (`graded`).
- Sealed archives can be downloaded directly as encrypted `.zst.enc` files.

### 6. Reviewable & Re-correctable Any Time
- Archived tests are never locked permanently away from educators.
- Teachers can click **"🔄 Re-open & Re-correct"** at any time to return a graded test to staging, adjust points or comments if a mistake was made, and re-seal it into the archive.

### 7. Offline Test Package Uploads
- Teachers can upload offline test submissions or student responses (`.json`, `.txt`, `.zip`) directly via the **"📤 Upload Test Paper"** button in the Archive Browser.
- Uploaded tests are registered immediately, ready for AI or manual grading.
