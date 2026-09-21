"""
test_routes_exam.py — legacy exam route tests, now updated to match new API.
Kept as a separate file to preserve historical test intent while using correct schema.
"""
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth

client = TestClient(app)


def _register_and_token(email: str, username: str) -> str:
    client.post("/auth/register", json={"email": email, "username": username, "password": "Route1234!"})
    return client.post("/auth/token", data={"username": email, "password": "Route1234!"}).json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_exams():
    teacher_token = _register_and_token("routes_teacher@test.com", "routes_teacher")
    h = _headers(teacher_token)

    # Create
    r = client.post("/exams/", json={"title": "Routes Exam", "duration_minutes": 90}, headers=h)
    assert r.status_code == 201
    exam_id = r.json()["id"]

    # Add question
    r = client.post(f"/exams/{exam_id}/questions", headers=h, json={
        "question_type": "dynamic_math",
        "text": "Solve for x: 2x + 4 = 10",
        "points": 5,
    })
    assert r.status_code == 201

    # /exams/ listing must NOT include questions (student-safe view)
    r = client.get("/exams/", headers=h)
    assert r.status_code == 200
    for exam in r.json():
        assert "questions" not in exam

    # /exams/mine includes questions for owner
    r = client.get("/exams/mine", headers=h)
    assert r.status_code == 200
    my_exams = r.json()
    found = next((e for e in my_exams if e["id"] == exam_id), None)
    assert found is not None
    assert len(found["questions"]) >= 1
    assert found["questions"][0]["question_type"] == "dynamic_math"
    assert found["questions"][0]["points"] == 5


def test_seb_config_generation():
    token = _register_and_token("seb_gen@test.com", "seb_gen")
    h = _headers(token)

    r = client.post("/exams/", json={
        "title": "SEB Test", "duration_minutes": 60, "seb_config_key": "dummy_key_abc"
    }, headers=h)
    assert r.status_code == 201
    exam_id = r.json()["id"]

    r = client.get(f"/exams/{exam_id}/seb-config", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/seb"
    assert b"dummy_key_abc" in r.content
    assert b"Cache-Control" in bytes(str(r.headers), "utf-8") or "no-store" in r.headers.get("cache-control", "")


def test_start_and_submit_with_multiple_choice():
    owner_token = _register_and_token("mc_owner@test.com", "mc_owner")
    student_token = _register_and_token("mc_student@test.com", "mc_student")
    h_owner = _headers(owner_token)
    h_student = _headers(student_token)

    r = client.post("/exams/", json={"title": "MC Exam", "duration_minutes": 30, "seb_config_key": "some_key"}, headers=h_owner)
    exam_id = r.json()["id"]

    r = client.post(f"/exams/{exam_id}/questions", headers=h_owner, json={
        "question_type": "multiple_choice",
        "text": "What is 2+2?",
        "options_json": '["1", "2", "3", "4"]',
        "correct_answer": "4",
        "points": 2,
    })
    assert r.status_code == 201
    question_id = r.json()["id"]

    # Start (dev bypass active)
    r = client.post(f"/exams/{exam_id}/start", headers=h_student)
    assert r.status_code == 200
    exam_data = r.json()
    assert len(exam_data["questions"]) == 1
    # Options must be present, correct_answer must NOT be
    q = exam_data["questions"][0]
    assert q["options"] is not None
    assert "correct_answer" not in q

    # Submit
    r = client.post(f"/exams/{exam_id}/submit", headers=h_student, json={
        "answers": [{"question_id": q["question_id"], "response": "4"}]
    })
    assert r.status_code == 200
    assert r.json()["status"] == "success"
