"""
test_routes_parent.py — parent/student relationship handshake and children progress.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models

client = TestClient(app)


def _register_and_token(email: str, username: str) -> tuple[models.User, str]:
    db = next(database.get_db())
    client.post("/auth/register", json={"email": email, "username": username, "password": "Parent1234!"})
    token = client.post("/auth/token", data={"username": email, "password": "Parent1234!"}).json()["access_token"]
    user = db.query(models.User).filter_by(email=email).first()
    return user, token


# ── Relationship request & approval handshake ─────────────────────────────────

def test_relationship_request_and_approve():
    parent, parent_token = _register_and_token("rel_parent@test.com", "rel_parent")
    student, student_token = _register_and_token("rel_student@test.com", "rel_student")

    # Parent initiates relationship request
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    assert r.status_code == 201
    rel_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    # Student approves
    r = client.post(f"/parents/relationships/{rel_id}/approve",
                    headers={"Authorization": f"Bearer {student_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_relationship_request_self_link_rejected():
    _, token = _register_and_token("self_link@test.com", "self_link")
    user = next(database.get_db()).query(models.User).filter_by(email="self_link@test.com").first()
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"student_id": user.id})
    assert r.status_code == 400


def test_duplicate_relationship_rejected():
    parent, parent_token = _register_and_token("dup_parent@test.com", "dup_parent")
    student, _ = _register_and_token("dup_student@test.com", "dup_student")
    h = {"Authorization": f"Bearer {parent_token}"}

    client.post("/parents/relationships/request", headers=h, json={"student_id": student.id})
    r = client.post("/parents/relationships/request", headers=h, json={"student_id": student.id})
    assert r.status_code == 409


def test_relationship_reject():
    parent, parent_token = _register_and_token("reject_parent@test.com", "reject_parent")
    student, student_token = _register_and_token("reject_student@test.com", "reject_student")

    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    rel_id = r.json()["id"]

    # Student rejects
    r = client.post(f"/parents/relationships/{rel_id}/reject",
                    headers={"Authorization": f"Bearer {student_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_third_party_cannot_approve():
    parent, parent_token = _register_and_token("thirdp_parent@test.com", "thirdp_parent")
    student, _ = _register_and_token("thirdp_student@test.com", "thirdp_student")
    _, stranger_token = _register_and_token("thirdp_stranger@test.com", "thirdp_stranger")

    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    rel_id = r.json()["id"]

    r = client.post(f"/parents/relationships/{rel_id}/approve",
                    headers={"Authorization": f"Bearer {stranger_token}"})
    assert r.status_code == 403


# ── Children progress ─────────────────────────────────────────────────────────

def test_children_progress_empty_without_active_relationship():
    _, parent_token = _register_and_token("progress_parent@test.com", "progress_parent")
    r = client.get("/parents/children-progress",
                   headers={"Authorization": f"Bearer {parent_token}"})
    assert r.status_code == 200
    assert r.json() == []  # No active relationships → empty list


def test_children_progress_shows_data_after_approval():
    db = next(database.get_db())
    parent, parent_token = _register_and_token("data_parent@test.com", "data_parent")
    student, student_token = _register_and_token("data_student@test.com", "data_student")
    teacher, _ = _register_and_token("data_teacher@test.com", "data_teacher")

    # Request + approve relationship
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    rel_id = r.json()["id"]
    client.post(f"/parents/relationships/{rel_id}/approve",
                headers={"Authorization": f"Bearer {student_token}"})

    # Create a completed exam submission for the student
    exam = models.Exam(title="History Final", description="Hard", teacher_id=teacher.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    sub = models.ExamSubmission(
        exam_id=exam.id,
        student_id=student.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        score=88.5,
        feedback="Good job!",
    )
    db.add(sub)
    db.commit()

    r = client.get("/parents/children-progress",
                   headers={"Authorization": f"Bearer {parent_token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    child = data[0]
    assert child["student_name"] == student.full_name or student.username
    # Email must never appear
    assert "data_student@test.com" not in str(child)
    assert len(child["recent_exams"]) == 1
    assert child["recent_exams"][0]["exam_title"] == "History Final"
    assert child["recent_exams"][0]["score"] == 88.5
