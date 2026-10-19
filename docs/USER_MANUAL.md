# PlannedEducation — User Manual

Complete handbook for teachers, students, parents, and administrators using PlannedEducation.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Roles & Account Types](#2-roles--account-types)
3. [Teacher Guide](#3-teacher-guide)
4. [Student Guide](#4-student-guide)
5. [Parent Guide](#5-parent-guide)
6. [Admin & Superadmin Guide](#6-admin--superadmin-guide)
7. [Password Recovery & Reset](#7-password-recovery--reset)
8. [Exams & Grading](#8-exams--grading)
9. [Security & Privacy](#9-security--privacy)
10. [FAQ](#10-faq)

---

## 1. Getting Started

### Accessing the Platform

PlannedEducation is a **browser-based application**. After your school's administrator deploys it:

1. Open any modern web browser
2. Navigate to your school's platform URL (e.g., `http://exam.yourschool.edu:5173`)
3. Register or log in with your school credentials

No client software installation is required — everything runs in the browser.

### Registration

1. Click **Register** on the login page
2. Select your role: **Student**, **Teacher**, **Parent**, or **Admin**
3. Enter your email, username, full name, and a secure password
4. **Save your 5 one-time recovery codes** — print them or write them down immediately!

---

## 2. Roles & Account Types

| Role | Primary Purpose | Key Capabilities |
|------|----------------|------------------|
| **Student** | Take exams | View exams, submit answers, view grades |
| **Teacher** | Create & manage exams | Create exams, question banks, modules, grade submissions, reset student passwords |
| **Parent** | Monitor child's progress | View child's grades, link student accounts, reset child's password |
| **Admin** | School administration | Create users, manage exams, reset teacher passwords, configure deployment |
| **Superadmin** | System administration | Everything admins can, plus create other superadmins |

### Teacher Approval

Self-registered teachers require **one-click administrator approval** before gaining exam creation rights. This prevents students from registering as teachers to inspect exam questions or answer keys.

---

## 3. Teacher Guide

### Getting Started

1. Register as a **Teacher** at `/register`
2. Wait for administrator approval (you'll receive a notification)
3. Once approved, you can create exams, classes, and question banks

### Creating Classes

1. Navigate to **Classes** in the sidebar
2. Click **Create Class**
3. Enter class name, grade level, and subject
4. Share the class join code with students, or add student accounts directly

### Creating Exams

1. Navigate to **Teacher Exams**
2. Click **Create New Exam**
3. Fill in exam details (title, description, duration, instructions)
4. Add questions:
   - **Multiple Choice**: Auto-graded instantly
   - **Essay**: Detailed rubrics with AI-assisted drafting
   - **Dynamic Math**: Uses `[rand:1-10]` variable placeholders for unique values per student
5. Publish the exam when ready

### Dynamic Math Variables

To prevent students from copying answers, embed variables inside brackets:

```
Solve for x: {a}x + {b} = {c}
```

Configure variable ranges (e.g., `a: 2..10`, `b: 1..20`). Each student receives a deterministically seeded set of numbers.

### Curriculum Modules

Group related questions into reusable **Modules** (e.g., *Unit 3: Quadratic Equations*):
- Tag questions by difficulty, IEP accommodation, and curriculum standard
- Import/export test packages using the standardized `.pepkg` format
- Share curriculum with colleagues across your school or district

### Pre-Exam Emergency Password Reset

Right before an exam, students frequently forget their passwords:

1. In **Teacher Dashboard → Real-Time Student Monitoring** or **Classes → Manage Students**, locate the student
2. Click the yellow **"⚡ Reset Pwd for Test"** button
3. Confirm the quick reset dialog
4. Instruct the student to open `/login` and enter their school email
5. The system detects the active unlock and prompts the student to set a new password immediately

The reset link expires in **24 hours**.

### AI-Assisted Grading

1. Navigate to **Teacher Dashboard**
2. Review student submissions
3. Use AI to draft grades and feedback — you review and approve before applying
4. Use **Smart Mistake Grouping** to see patterns across the class

---

## 4. Student Guide

### Registration & Recovery Codes

1. Open the platform URL and click **Register**
2. Select **Student**, enter your school email, username, full name, and password
3. **CRITICAL**: Save your **5 one-time recovery codes** immediately!
   - Print them or write them down in your notebook
   - Each code can be used once to reset your password without anyone's help

### Taking Exams

1. Log in and click on your assigned exam under **My Exams**
2. If your school uses **Safe Exam Browser (SEB)**, click **Launch Exam in SEB**
3. SEB locks your workstation into full-screen exam mode (blocks Alt+Tab, Windows Key, etc.)
4. Answers auto-save as you type — if network disconnects, the exam continues offline
5. Click **Submit Exam** when finished

### Password Recovery (3 Ways)

**Method 1: Self-Reset with Recovery Codes (Fastest)**
1. On the login screen, click **Forgot Password?**
2. Enter your email and one of your 5 recovery codes
3. Choose a new password and sign in immediately

**Method 2: Emergency Classroom Unlock by Teacher**
1. Tell your teacher you can't log in
2. Your teacher clicks **"⚡ Reset Pwd for Test"** next to your name
3. Go to `/login`, type your email
4. Type your new password and click **Set Password and Sign In**

**Method 3: Supervisor Reset Request**
1. Click **Forgot Password?** → **Request Supervisor Reset**
2. Select your linked Teacher or Parent
3. Your supervisor receives a notification and can generate a temporary reset code

---

## 5. Parent Guide

### Registration & Account Linking

1. Register as a **Parent** at `/register`
2. Save your **5 one-time recovery codes**
3. Navigate to **My Children**
4. Click **Link Student Account**
5. Enter your child's student identifier or linkage code

### Viewing Progress

- View upcoming exams, completed assignments, and recent grading scores
- Review detailed teacher feedback and rubric breakdowns
- Track mastery across curriculum subjects over the school term

### Privacy & FERPA Compliance

PlannedEducation strictly complies with FERPA and GDPR student privacy rules. No student records or personal data are ever sold or shared with third parties.

### Helping Your Child Recover Their Password

If your child forgets their password and has exhausted recovery codes:
1. Your child selects you as their supervisor from **Forgot Password?**
2. A notification appears on your dashboard
3. Open the notification and click **Approve Reset**
4. Give the temporary password to your child

The reset link expires in **24 hours**.

---

## 6. Admin & Superadmin Guide

### Admin Capabilities

Admins can:
- Create users (teachers, students, parents, other admins)
- Manage exams and exam oversight
- Reset teacher passwords
- Configure deployment settings
- Approve/deny teacher registrations
- Create database backups
- Customize school header branding

### Superadmin Capabilities

Superadmins have all admin capabilities **plus**:
- Create other superadmins (`POST /admin/users/superadmin`)
- Create admin accounts

Superadmin creation is restricted to existing superadmins only.

### School Header Customization

Admins and superadmins can customize the platform header:

| Mode | Description |
|------|-------------|
| **text** | Shows school name as text |
| **image** | Shows custom header image |
| **none** | No header displayed |

Configure via **Admin Dashboard → School Settings → Header** or API:
```json
{
  "header_display_mode": "text",
  "header_text": "Lincoln High School",
  "header_image_url": null
}
```

### Deployment Configuration

Edit `config/deployment.json` directly, or use **Admin Dashboard → ⚙️ Deployment & Network** to update domain names, ports, and SMTP settings.

---

## 7. Password Recovery & Reset

### Reset Hierarchy (No Email Required)

| Initiator | Can Reset | Required | Expires |
|-----------|-----------|----------|---------|
| Teacher | Students only | Approved teacher | 24 hours |
| Parent | Their children only | Active relationship | 24 hours |
| Admin | Teachers only | Admin privilege | 24 hours |
| Superadmin | Teachers + Admins | Superadmin privilege | 24 hours |
| Self (Email) | Own account | Email + OTP | 24 hours |

### Self-Reset with Recovery Codes

Every user receives 5 one-time recovery codes at registration. Use them on the login screen under **Forgot Password?** to instantly reset your password without assistance.

### Email-Based Reset (Optional)

If your school configures SMTP email:
1. Click **Forgot password?** on `/login`
2. Enter your registered email
3. Receive a 6-digit OTP via email
4. Enter the OTP and set a new password

Email is optional — the platform works fully without it.

---

## 8. Exams & Grading

### Question Types

| Type | Description | Grading |
|------|-------------|---------|
| Multiple Choice | Single or multi-select options | Auto-graded |
| Essay | Long-form written response | Teacher-graded with rubric |
| Dynamic Math | Variable placeholders `[rand:1-10]` | Auto-graded |

### Dynamic Math Variables

```
Solve for x: {a}x + {b} = {c}
```

Each student gets unique values while testing the same concept.

### AI-Assisted Grading

Teachers can use AI to draft grades and feedback for essay questions. The teacher reviews and approves before applying grades to student records.

### Smart Mistake Grouping

Instantly see patterns across the class — "These 5 students all struggled with the same concept" — for efficient reteaching.

---

## 9. Security & Privacy

### Security Features

- **Argon2id** password hashing (OWASP recommended)
- **Rate limiting** on auth endpoints
- **Brute-force lockout** (5 failed attempts = 15 min lockout)
- **JWT** with 30-minute expiry
- **Fernet encryption** for sensitive data at rest
- **Microsoft Presidio** PII scrubbing for anonymized content
- **Security headers** (CSP, HSTS, X-Frame-Options)
- **CORS** with explicit allow-list

### Privacy & Compliance

- **FERPA** and **GDPR** compliant
- Student records are private to the student, parents, and authorized teachers
- No student data is sold or shared with third parties
- Exam logs and proctoring events are sensitive educational records

### Safe Exam Browser (SEB)

SEB creates a locked-down browser environment that prevents:
- Tab switching
- Screen sharing
- Unauthorized applications
- Background processes

---

## 10. FAQ

### How do I create an exam?
Go to the Teacher Dashboard, click 'Create New Exam', fill in the details, add questions, and save.

### How do students join an exam?
Students receive an exam code or link from their teacher, or click the direct link provided.

### What is the Secure Exam Browser (SEB)?
A locked-down browser that prevents students from accessing other applications or websites during an exam.

### How do I reset my password?
1. Use one of your 5 recovery codes (fastest)
2. Ask your teacher/parent for a quick reset (classroom emergency)
3. Ask an administrator to reset it from the Admin Panel
4. Use email OTP if your school has email configured

### Can administrators reset passwords without email?
Yes! Administrators can reset any user's password directly from the Admin Panel > Users tab.

### How do database backups work?
Automated midnight backups at 00:00 UTC, with 30-day retention. Admins can also create instant backups anytime.

### How do I enable two-factor authentication?
Go to Settings > Security, click 'Enable 2FA', scan the QR code with your authenticator app.

### What are Passkeys?
Passwordless authentication using biometrics or device PIN. Set up in Settings > Passkeys.

### How do I share exams with other teachers?
Export exams as `.pepkg` packages and import them into other teachers' accounts.

### Is email required?
No. Email is 100% optional. The platform works fully in offline mode without email.
