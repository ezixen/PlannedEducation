# Temporary Project Audit Notes

Date: 2026-09-21  
Scope: quick audit of the whole workspace for purpose, logic issues, security leaks, and obvious maintenance problems.

## What this project does

- A school/testing app with three user roles: `student`, `teacher`, and `parent`.
- Backend: FastAPI + SQLAlchemy in `src/plannededucation/api/`.
- Frontend: React + Vite in `web/apps/portal/`.
- Main features:
  - Google SSO login
  - teacher exam creation/editing
  - student exam taking with SEB-style lockdown messaging
  - anonymous AI grading export
  - parent progress view
  - optional webcam/mic proctoring toggle

## Highest-risk problems

1. **Student answer-key leak in exam listing**
   - `src/plannededucation/api/routes_exam.py`
   - `GET /exams/` returns all exams to students, not just assigned/owned exams.
   - The response model includes nested questions, and `schemas.QuestionResponse` exposes `correct_answer` and `rubric`.
   - This is a direct data leak of answer keys to students.

2. **Role escalation on first Google login**
   - `src/plannededucation/api/routes_auth.py`
   - The first-time role comes from client input (`GoogleLogin.role`).
   - Any new account can choose `teacher` or `parent` unless another server-side rule is added.

3. **WebSocket auth token is passed in the URL**
   - `web/apps/portal/src/components/SecureChat.tsx`
   - `src/plannededucation/api/routes_chat.py`
   - The JWT is sent as a query string parameter, which can leak through logs, history, proxies, and browser tooling.

4. **Chat room authorization is incomplete**
   - `src/plannededucation/api/routes_chat.py`
   - Any authenticated user with a valid token can join any exam room if they know the `exam_id`.
   - There is no exam membership/ownership check.

5. **Hardcoded secrets and placeholders**
   - `src/plannededucation/api/auth.py` hardcodes `SECRET_KEY`.
   - `src/plannededucation/api/routes_auth.py` hardcodes `GOOGLE_CLIENT_ID` as a placeholder.
   - This is not production-safe and will break real SSO unless replaced.

6. **Parent dashboard token bug**
   - `web/apps/portal/src/pages/ParentDashboard.tsx`
   - It reads `localStorage.getItem('token')`, but the app stores `access_token`.
   - Parent progress fetches will fail unless this is fixed.

7. **Exam-taking page is still mocked**
   - `web/apps/portal/src/pages/TakeExam.tsx`
   - It does not call `/exams/{id}/start` or `/exams/{id}/submit`.
   - It hardcodes fake exam content and uses `examId={1}` for chat.
   - The student workflow is not wired to the backend.

8. **Startup scripts / docs do not match the workspace**
   - `README.md` references `.
scripts\local\start.ps1` and `.
scripts\local\stop.ps1`, but the actual launcher scripts are at the repo root: `start.ps1` and `stop.ps1`.
   - `start.ps1` also references `C:/.venv/Scripts/python.exe`, which is likely wrong on most machines.

9. **Screen watermark exposes PII on every authenticated page**
   - `web/apps/portal/src/components/WatermarkOverlay.tsx`
   - It renders `user.email | user.id` across the whole viewport.
   - This is intentional anti-sharing leakage, but it is still visible PII and should be called out clearly.

10. **Admin app is only the default Vite starter**
    - `web/apps/admin/src/App.tsx`
    - The admin portal is not implemented yet; it is still scaffold content.

## Additional logic / design issues

- `src/plannededucation/api/routes_anonymizer.py`
  - The AI-grades endpoint is labeled for external AI, but it still requires a teacher-authenticated user.
  - It also does not persist feedback anywhere, so grading is effectively a stub.

- `src/plannededucation/api/routes_exam.py`
  - `verify_seb_request` only checks a request-header hash based on a shared config key.
  - That is not strong browser attestation; it is easy to misunderstand as stronger than it really is.

- `src/plannededucation/api/main.py`
  - `Base.metadata.create_all(bind=engine)` runs at import/startup time.
  - That can be surprising and risky for real deployments.

- `src/plannededucation/api/routes_chat.py`
  - WebSocket DB sessions are opened manually and never explicitly closed.
  - This can leak resources under load.

- `src/plannededucation/api/models.py`
  - `ExamSubmission.started_at` and `completed_at` are stored as strings, not datetime fields.
  - This will make filtering and time calculations harder later.

- `web/apps/portal/src/components/ProctoringToggle.tsx`
  - It requests camera/mic access but does not send any meaningful proctoring events anywhere.
  - It is UI-only right now.

## Testing / coverage notes

- `tests/test_auth.py` is only a dummy placeholder.
- Most tests are integration-ish happy-path checks and do not cover the serious authorization leaks above.
- I did not find syntax errors in the workspace through the editor diagnostics, but that does not mean the app is safe or fully functional.

## Short verdict

The project is a teacher/student/parent exam platform with SEB, AI grading, and chat/proctoring features, but it currently has several major security and workflow gaps:

- student access control is too permissive
- role assignment is user-controlled
- auth tokens leak in WebSocket URLs
- parent and exam-taking flows are partially broken or mocked
- startup/docs are inconsistent
- secrets and SSO config are not production-ready

This file is temporary and should be replaced with a proper security/architecture review later.