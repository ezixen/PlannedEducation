"""
test_exams.py — exam CRUD, question creation, access control, and SEB config.
"""
import pytest
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models
from src.plannededucation.api.seb_security import verify_seb_request

client = TestClient(app)


def _register_and_token(email: str, username: str, password: str = "Exam1234!") -> str:
    client.post("/auth/register", json={"email": email, "username": username, "password": password})
    return client.post("/auth/token", data={"username": email, "password": password}).json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Create exam ───────────────────────────────────────────────────────────────

def test_create_exam():
    token = _register_and_token("exam_create@test.com", "exam_create")
    r = client.post("/exams/", json={"title": "Algebra 101", "duration_minutes": 60}, headers=_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Algebra 101"
    assert data["duration_minutes"] == 60
    assert "id" in data
    assert "teacher_id" in data


# ── Public listing must not leak answers ─────────────────────────────────────

def test_exam_list_has_no_question_data():
    token = _register_and_token("exam_list@test.com", "exam_list")
    h = _headers(token)
    # Create an exam with a question that has a correct_answer
    r = client.post("/exams/", json={"title": "List Test", "duration_minutes": 30}, headers=h)
    exam_id = r.json()["id"]
    client.post(f"/exams/{exam_id}/questions", headers=h, json={
        "question_type": "multiple_choice",
        "text": "2+2=?",
        "correct_answer": "4",
        "options_json": '["1","2","3","4"]',
        "points": 1,
    })

    # GET /exams/ — must return metadata only
    listing = client.get("/exams/", headers=h).json()
    for exam in listing:
        assert "questions" not in exam, "SECURITY: /exams/ leaked question data to all users!"
        assert "correct_answer" not in str(exam)


# ── Owner gets full data via /exams/mine ─────────────────────────────────────

def test_my_exams_returns_full_data_for_owner():
    token = _register_and_token("exam_mine@test.com", "exam_mine")
    h = _headers(token)
    client.post("/exams/", json={"title": "My Exam", "duration_minutes": 45}, headers=h)
    r = client.get("/exams/mine", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    # Full response includes questions list
    assert "questions" in data[0]


# ── IDOR: non-owner cannot access full exam detail ───────────────────────────

def test_idor_non_owner_cannot_get_exam_detail():
    owner_token = _register_and_token("owner_idor@test.com", "owner_idor")
    other_token = _register_and_token("other_idor@test.com", "other_idor")

    r = client.post("/exams/", json={"title": "Private Exam", "duration_minutes": 60}, headers=_headers(owner_token))
    exam_id = r.json()["id"]

    r = client.get(f"/exams/{exam_id}", headers=_headers(other_token))
    assert r.status_code == 403


# ── Question creation requires ownership ─────────────────────────────────────

def test_non_owner_cannot_add_question():
    owner_token = _register_and_token("qowner@test.com", "qowner")
    other_token = _register_and_token("qother@test.com", "qother")

    r = client.post("/exams/", json={"title": "Owned Exam", "duration_minutes": 60}, headers=_headers(owner_token))
    exam_id = r.json()["id"]

    r = client.post(f"/exams/{exam_id}/questions", headers=_headers(other_token), json={
        "question_type": "essay", "text": "Hacked question", "points": 1,
    })
    assert r.status_code == 403


# ── SEB config only for owner ─────────────────────────────────────────────────

def test_seb_config_requires_ownership():
    owner_token = _register_and_token("sebowner@test.com", "sebowner")
    other_token = _register_and_token("sebother@test.com", "sebother")

    r = client.post("/exams/", json={"title": "SEB Exam", "duration_minutes": 60, "seb_config_key": "mysecret"}, headers=_headers(owner_token))
    exam_id = r.json()["id"]

    # Non-owner gets 403
    r = client.get(f"/exams/{exam_id}/seb-config", headers=_headers(other_token))
    assert r.status_code == 403

    # Owner gets the file
    r = client.get(f"/exams/{exam_id}/seb-config", headers=_headers(owner_token))
    assert r.status_code == 200
    assert b"mysecret" in r.content


# ── SEB security rejects unauthorized browsers ────────────────────────────────

def test_start_exam_seb_rejection_without_key():
    """An exam WITH a seb_config_key must reject requests that lack the SEB header."""
    owner_token = _register_and_token("sebreject_owner@test.com", "sebreject_owner")
    student_token = _register_and_token("sebreject_student@test.com", "sebreject_student")
    h_owner = _headers(owner_token)

    # Create a locked exam (with SEB key)
    r = client.post("/exams/", json={"title": "Locked Exam", "duration_minutes": 60, "seb_config_key": "secret_hash"}, headers=h_owner)
    exam_id = r.json()["id"]

    # We do this by temporarily disabling ALLOW_DEV_SEB_BYPASS
    import os
    original_bypass = os.environ.get("ALLOW_DEV_SEB_BYPASS")
    os.environ["ALLOW_DEV_SEB_BYPASS"] = "false"

    try:
        r = client.post(f"/exams/{exam_id}/start", headers=_headers(student_token))
        # Must be rejected because no SEB header is present
        assert r.status_code == 403
        assert "Safe Exam Browser" in r.json()["detail"]
    finally:
        if original_bypass is not None:
            os.environ["ALLOW_DEV_SEB_BYPASS"] = original_bypass
        else:
            del os.environ["ALLOW_DEV_SEB_BYPASS"]


# ── Start and submit exam (dev bypass mode) ───────────────────────────────────

def test_start_and_submit_exam_dev_bypass():
    owner_token = _register_and_token("bypassowner@test.com", "bypassowner")
    student_token = _register_and_token("bypassstudent@test.com", "bypassstudent")
    h_owner = _headers(owner_token)
    h_student = _headers(student_token)

    # Create exam + question
    r = client.post("/exams/", json={"title": "Bypass Exam", "duration_minutes": 45, "seb_config_key": "some_key"}, headers=h_owner)
    exam_id = r.json()["id"]
    client.post(f"/exams/{exam_id}/questions", headers=h_owner, json={
        "question_type": "dynamic_math",
        "text": "Solve: x + [rand:1-5] = 10",
        "correct_answer": "varies",
        "points": 5,
    })

    # Dev bypass is active via ALLOW_DEV_SEB_BYPASS=true in conftest
    r = client.post(f"/exams/{exam_id}/start", headers=h_student)
    if r.status_code != 200:
        print("\n\nSTART RESPONSE:", r.json(), "\n\n")
    assert r.status_code == 200
    data = r.json()
    assert "submission_id" in data
    assert len(data["questions"]) == 1
    # [rand:X-Y] tokens must be resolved
    assert "[rand" not in data["questions"][0]["text"]
    # Correct answer must NOT be returned to student
    assert "correct_answer" not in data["questions"][0]

    submission_id = data["submission_id"]
    question_id = data["questions"][0]["question_id"]

    # Submit
    r = client.post(f"/exams/{exam_id}/submit", headers=h_student, json={
        "answers": [{"question_id": question_id, "response": "7"}]
    })
    if r.status_code != 200:
        print("\n\nSUBMIT RESPONSE:", r.json(), "\n\n")
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    # Double submit must fail
    r = client.post(f"/exams/{exam_id}/submit", headers=h_student, json={
        "answers": [{"question_id": question_id, "response": "7"}]
    })
    assert r.status_code == 409


# ── Delete exam ───────────────────────────────────────────────────────────────

def test_delete_exam():
    token = _register_and_token("exam_del@test.com", "exam_del")
    h = _headers(token)
    r = client.post("/exams/", json={"title": "To Delete", "duration_minutes": 30}, headers=h)
    exam_id = r.json()["id"]

    r = client.delete(f"/exams/{exam_id}", headers=h)
    assert r.status_code == 204

    # Confirm it's gone
    r = client.get(f"/exams/{exam_id}", headers=h)
    assert r.status_code == 404
