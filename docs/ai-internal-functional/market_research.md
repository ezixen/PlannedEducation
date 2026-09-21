# Market Research & Competitor Analysis

## 1. Instructure & Canvas (Learning Management System)
**What it is:** Instructure is the company behind **Canvas**, one of the world's most widely used Learning Management Systems (LMS) for K-12, Higher Education, and Corporate environments.
**What it offers:**
- **Canvas LMS:** Course creation, assignment distribution, student communication, and grading rubrics.
- **Mastery Connect:** K-12 assessment management for tracking student mastery of state standards.
- **Elevate & Impact:** Analytics, data syncing, and tracking student/teacher engagement.
- **AI Features (IgniteAI):** Canvas is beginning to introduce AI tools to assist educators with course creation and grading, but these are often premium add-ons.
**Format:** It is a cloud-based SaaS platform (Web-based application), with companion mobile apps.
**Pricing:** Instructure **does not provide public, standardized pricing**. Their pricing model is highly customized based on institutional contracts (student headcount, required tiers like Canvas Core, Plus, or Next, and support levels). Anecdotally, it can range from a few dollars per student per year to tens of thousands of dollars for mid-sized institutions.

---

## 2. Secure Test-Taking & PC Locking (Anti-Cheating)

### Open Source Solutions
1. **Safe Exam Browser (SEB)**
   - **Status:** Free & Open Source (GitHub).
   - **What it does:** It acts as a "kiosk" application that turns any computer into a secure workstation. It locks the computer, prevents task switching, disables shortcuts (like Ctrl+Alt+Del, Alt+Tab), detects virtual machines, and restricts navigation.
   - **Overlap with Planned Education:** This is *exactly* the PC-locking technology we are planning to build. SEB is widely integrated into Canvas and Moodle.
2. **OpenLock**
   - **Status:** Open Source (Linux focus).
   - **What it does:** Similar to SEB, focuses on providing a secure lockdown browser environment, specifically tailored for Linux systems.

### Paid / Commercial Solutions
1. **Respondus LockDown Browser**
   - **Status:** Commercial / Paid.
   - **What it does:** The industry standard for locking down testing environments. It prevents printing, copying, going to other URLs, or accessing other applications. Often paired with "Respondus Monitor" which uses webcams and AI to detect eye movement and background noise to flag cheating.
2. **Honorlock / Proctorio**
   - **Status:** Commercial / Highly Expensive.
   - **What it does:** Uses aggressive AI and browser extensions to lock down the test, record the student via webcam/mic, and analyze their ID and room environment.

---

## 3. AI Grading & Text Recognition (Teacher Aids)

### Open Source & DIY Solutions
Finding a complete, end-to-end open-source AI grading software is rare because heavy AI processing usually costs money. However, there are pieces:
1. **OCR Engines (Tesseract, EasyOCR, PaddleOCR):** Free, open-source engines that can turn photos of handwritten exams into digital text.
2. **GitHub Projects (e.g., AI-Handwrite-Grader, essay-grader-tech):** Community projects built by individuals to piece together OCR and local Large Language Models (like Ollama) to grade handwritten assignments locally without cloud costs.

### Commercial / Paid Solutions
1. **Gradescope (by Turnitin)**
   - **What it does:** Allows teachers to scan handwritten exams. AI groups similar answers together so the teacher only has to grade a specific mistake once, and the software applies it to all students who made that mistake.
   - **Cost:** Paid institutional license.
2. **Turnitin**
   - **What it does:** Primarily plagiarism detection, but recently heavily focused on AI-writing detection (detecting if a student used ChatGPT).

---

## 4. Conclusion & Our Unique Value Proposition
### Is Planned Education a new idea?
The individual components exist:
- **Lockdown Browsers:** Safe Exam Browser (Open Source), Respondus (Paid).
- **LMS:** Canvas, Moodle (Open Source).
- **AI Grading:** Gradescope (Paid).

### How Planned Education Stands Out:
1. **All-in-One Kiosk + AI Grader:** There is currently no *free, open-source* platform that seamlessly combines a native desktop locking app (like Safe Exam Browser) with an integrated AI-driven teacher grading and text-to-speech module out of the box. 
2. **The "Job Statistics" Vision:** No LMS currently maps student grades directly to real-world job statistics, average incomes, or career trajectories to inspire students natively within the testing platform. This feature is highly unique.
3. **Cost Factor:** By making it open source, we bypass the heavy institutional licensing fees of Canvas, Respondus, and Gradescope, creating a massive impact for underfunded schools globally.

**Recommendation:** We do not need to reinvent the wheel for the locking mechanism. We should study the source code of **Safe Exam Browser (SEB)** (or even fork/integrate it) to handle the deep OS-level locks, and focus our primary development on the AI grading, UI (Vite/React), and the inspirational Job Statistics features.

