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

### Teacher's Aides & Shared Grading
1. From **Classes**, nominate a registered student as a Teacher's Aide by email or username.
2. Share selected exams with aides for collaborative correction; revoke access anytime.
3. Aides see only exams you explicitly share — not your full roster or private messages.

### Teachers' Lounge & Direct Messages
1. While signed in, open **Messages** next to the notification bell in the top header (or choose **Messages** from the menu) to browse the Teachers' Lounge directory of approved teachers (plus admins who opted in).
2. Conversation contents are stored securely on the school server and are visible only to the people in that conversation and authorized administrators — this is school-hosted private messaging, not a consumer chat app.
3. Students cannot message each other. Student→teacher messages stay off until you enable them under Classes.
4. School superadmins can publish a platform support email in **Admin → Deployment Config** that stays visible to teachers.

### Help & FAQ
1. Open the hamburger menu and choose **Help** to open the in-app FAQ assistant.
2. The special-characters picker stays as the floating control in the bottom-right corner for typing math and science symbols.

### Special Characters Picker
1. Click the floating special-characters control to open Math, Chemistry, Physics, Greek, and accent pages.
2. Search a category name and press Enter, or flip pages with arrows / Left-Right keys.
3. In Exam Editor, attach custom module character sets so students see the same symbols during that exam.

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

## 4. Secure Exam Browser (SEB) & Time Limits

PlannedEducation natively supports **Safe Exam Browser (SEB)** to guarantee a secure, locked-down testing environment:
1. When publishing an exam, toggle **Require Safe Exam Browser**.
2. Download the pre-configured `.seb` file or distribute the direct SEB launch link to students.
3. During the exam:
   - OS shortcuts (Alt+Tab, Windows Key, Ctrl+Alt+Del) are disabled.
   - Screen capture, virtual machines, and external monitors are restricted.
   - The exam session must start from SEB when you require it — ordinary browsers are rejected for those exams.
4. **Server-side time limit**: The exam duration you set (and any accommodation multiplier) is enforced by the server when the student submits. Extending time only on the student device does not keep a late submission open.
5. **Emergency Exit**: If a workstation encounters a hardware fault or restarts, the student re-authenticates with SEB or requests teacher intervention without losing already saved answers.

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

### 2. Privacy-Preserving AI Grading
- Select one or more tests and click **AI Correct Selected**.
- Before any answer text is sent to an external AI provider you configured, PlannedEducation removes personal details (names, emails, phones, locations, and similar identifiers).
- If privacy filtering is unavailable, external AI grading is blocked rather than sending raw student text.
- The AI evaluates each answer against your rubric or correct answer, provides constructive feedback, explains mistakes, suggests step-by-step solutions, and proposes scores.
- If no external AI key is configured, PlannedEducation can still use its local deterministic rubric matcher so grading workflows continue offline.

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

### 5. Sealing & Archiving
- When approved, final scores and feedback are written to the school database.
- The archived package is compressed and encrypted so sealed downloads stay protected at rest.
- The temporary staging file is cleaned up, and the test is marked **Graded & Sealed**.
- You can download sealed archives from the Archive Browser when your school keeps offline copies.

### 6. Reviewable & Re-correctable Any Time
- Archived tests are never locked permanently away from educators.
- Teachers can click **"🔄 Re-open & Re-correct"** at any time to return a graded test to staging, adjust points or comments if a mistake was made, and re-seal it into the archive.

### 7. Offline Test Package Uploads
- Teachers can upload offline test submissions or student responses (`.json`, `.txt`, `.zip`) directly via the **"📤 Upload Test Paper"** button in the Archive Browser.
- Uploaded tests are registered immediately, ready for AI or manual grading.
