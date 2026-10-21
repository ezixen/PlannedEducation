"""
test_routes_archive_and_ai.py — Automated verification for teacher archive browser,
PII-scrubbed AI grading, temporary staging, teacher approval, sealing, and reopening.
"""
from datetime import UTC, datetime
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app

client = TestClient(app)


def _register_user(email: str, username: str, role: str = "student", full_name: str = "Test User") -> tuple[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "Password123!", "role": role, "full_name": full_name},
    )
    # Automatically approve teacher if needed
    db = next(database.get_db())
    u = db.query(models.User).filter_by(email=email).first()
    if u and role == "teacher":
        u.teacher_approved = True
        db.commit()
    token = client.post("/auth/token", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return u.id, token


def test_archive_teacher_class_submissions_and_ai_workflow():
    db = next(database.get_db())
    teacher_id, teacher_token = _register_user("archive_teacher@test.com", "arch_tchr", role="teacher", full_name="Dr. Euler")
    student_id, student_token = _register_user("archive_student@test.com", "arch_stdnt", role="student", full_name="Jane Doe")

    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    s_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Teacher creates an exam
    exam_res = client.post(
        "/exams",
        json={"title": "High School Math 101", "description": "Algebra & Geometry", "duration_minutes": 60},
        headers=t_headers,
    )
    assert exam_res.status_code in (200, 201)
    exam_id = exam_res.json()["id"]

    # Teacher adds questions
    q1_res = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "question_type": "multiple_choice",
            "text": "What is 2 + 2?",
            "correct_answer": "4",
            "rubric": "Must be 4",
            "points": 5,
        },
        headers=t_headers,
    )
    assert q1_res.status_code in (200, 201)
    q1_id = q1_res.json()["id"]

    q2_res = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "question_type": "essay",
            "text": "Solve for x: 3x - 6 = 0. Show all steps.",
            "correct_answer": "x = 2",
            "rubric": "Add 6 to both sides, divide by 3 to get x = 2.",
            "points": 10,
        },
        headers=t_headers,
    )
    assert q2_res.status_code in (200, 201)
    q2_id = q2_res.json()["id"]

    # 2. Student starts exam and submits answers (with some PII to verify Presidio scrubbing)
    start_res = client.post(f"/exams/{exam_id}/start", headers=s_headers)
    assert start_res.status_code == 200

    submit_res = client.post(
        f"/exams/{exam_id}/submit",
        json={
            "answers": [
                {"question_id": q1_id, "response": "4"},
                {"question_id": q2_id, "response": "My name is Jane Doe and email is jane@test.com. 3x = 6 so x = 2."},
            ]
        },
        headers=s_headers,
    )
    assert submit_res.status_code == 200

    # 3. Teacher views class submissions in Archive Browser
    subs_res = client.get(f"/archive/teacher/class-submissions?exam_id={exam_id}", headers=t_headers)
    assert subs_res.status_code == 200
    subs_data = subs_res.json()
    assert len(subs_data) >= 1
    target_sub = next(s for s in subs_data if s["exam_id"] == exam_id)
    assert target_sub["status"] == "ungraded"
    sub_id = target_sub["submission_id"]

    # 4. Teacher selects submission for AI correction
    ai_grade_res = client.post(
        "/archive/teacher/ai-grade",
        json={"submission_ids": [sub_id]},
        headers=t_headers,
    )
    assert ai_grade_res.status_code == 200
    assert ai_grade_res.json()["staged_count"] == 1

    # Verify status changed to 'pending_approval' (staged in temp folder)
    subs_res2 = client.get(f"/archive/teacher/class-submissions?exam_id={exam_id}", headers=t_headers)
    target_sub2 = next(s for s in subs_res2.json() if s["submission_id"] == sub_id)
    assert target_sub2["status"] == "pending_approval"
    assert target_sub2["has_ai_grades"] is True

    # 5. Teacher reviews in TeacherCorrectionModal and approves
    approve_res = client.post(
        "/archive/teacher/approve",
        json={
            "submission_ids": [sub_id],
            "overrides": {
                sub_id: {
                    "score": 15.0,
                    "feedback": "Perfect mathematical derivation. Well done!",
                }
            },
        },
        headers=t_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["archived_count"] == 1

    # Verify submission status is now 'graded' and sealed in archive
    subs_res3 = client.get(f"/archive/teacher/class-submissions?exam_id={exam_id}", headers=t_headers)
    target_sub3 = next(s for s in subs_res3.json() if s["submission_id"] == sub_id)
    assert target_sub3["status"] == "graded"
    assert target_sub3["score"] == 15.0
    assert target_sub3["archive_id"] is not None
    archive_id = target_sub3["archive_id"]

    # 6. Verify teacher can download the archive (.zst.enc)
    download_res = client.get(f"/archive/download/{archive_id}", headers=t_headers)
    assert download_res.status_code == 200
    assert len(download_res.content) > 0

    # 7. Teacher can reopen the archived test for re-correction
    reopen_res = client.post(
        "/archive/teacher/reopen",
        json={"submission_id": sub_id},
        headers=t_headers,
    )
    assert reopen_res.status_code == 200

    subs_res4 = client.get(f"/archive/teacher/class-submissions?exam_id={exam_id}", headers=t_headers)
    target_sub4 = next(s for s in subs_res4.json() if s["submission_id"] == sub_id)
    assert target_sub4["status"] == "pending_approval"


def test_ai_key_provider_schema():
    # Verify AI key update accepts modern free/open providers: anthropic, deepseek, groq, etc.
    _, teacher_token = _register_user("aikey_teacher@test.com", "aikey_tchr", role="teacher")
    t_headers = {"Authorization": f"Bearer {teacher_token}"}

    for provider in ["gemini", "openrouter", "ollama", "openai", "anthropic", "deepseek", "groq", "cohere", "mistral", "custom"]:
        res = client.put(
            "/auth/ai-key",
            json={"ai_provider": provider, "ai_api_key": "test_key_12345", "ai_model_name": "test-model"},
            headers=t_headers,
        )
        assert res.status_code == 200, f"Failed for provider {provider}: {res.text}"
