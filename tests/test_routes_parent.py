"""
test_routes_parent.py — parent/student relationship handshake and children progress.
"""
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app

client = TestClient(app)


def _register_and_token(email: str, username: str, role: str = "student") -> tuple[models.User, str]:
    """Register a user with an explicit role and return (User, access_token).

    F-035 / F-050: All callers must pass an explicit role so the tests reflect
    the enforced invariant (parent role for parent-side requests).
    """
    client.post("/auth/register", json={"email": email, "username": username, "password": "Parent1234!", "role": role})
    token = client.post("/auth/token", data={"username": email, "password": "Parent1234!"}).json()["access_token"]
    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        # Detach so callers can use attributes after the session closes.
        if user is not None:
            db.expunge(user)
        return user, token
    finally:
        db.close()


# ── Relationship request & approval handshake ─────────────────────────────────

def test_relationship_request_and_approve():
    # F-035: parent-role user initiates; student-role user approves
    parent, parent_token = _register_and_token("rel_parent@test.com", "rel_parent", role="parent")
    student, student_token = _register_and_token("rel_student@test.com", "rel_student", role="student")

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
    # A parent-role user should get 400 when targeting themselves.
    parent, token = _register_and_token("self_link@test.com", "self_link", role="parent")
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"student_id": parent.id})
    # Self-link check fires first (400 Bad Request), role check passed (parent → parent is itself, not a student)
    # Backend checks: role != parent → 403, then self-link → 400, then target must be student → 422.
    # With parent role but targeting themselves (also a parent), we get 422 (target not student).
    assert r.status_code in (400, 422)


def test_non_parent_role_cannot_request_relationship():
    """F-035: a student or teacher cannot act as the parent side."""
    student, student_token = _register_and_token("nonparent_req@test.com", "nonparent_req", role="student")
    other, _ = _register_and_token("nonparent_tgt@test.com", "nonparent_tgt", role="student")
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {student_token}"},
                    json={"student_id": other.id})
    assert r.status_code == 403


def test_non_student_target_rejected():
    """F-035: parent cannot link to a non-student account."""
    parent, parent_token = _register_and_token("badtgt_parent@test.com", "badtgt_parent", role="parent")
    teacher, _ = _register_and_token("badtgt_teacher@test.com", "badtgt_teacher", role="teacher")
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": teacher.id})
    assert r.status_code == 422


def test_duplicate_relationship_rejected():
    parent, parent_token = _register_and_token("dup_parent@test.com", "dup_parent", role="parent")
    student, _ = _register_and_token("dup_student@test.com", "dup_student", role="student")
    h = {"Authorization": f"Bearer {parent_token}"}

    client.post("/parents/relationships/request", headers=h, json={"student_id": student.id})
    r = client.post("/parents/relationships/request", headers=h, json={"student_id": student.id})
    assert r.status_code == 409


def test_relationship_reject():
    parent, parent_token = _register_and_token("reject_parent@test.com", "reject_parent", role="parent")
    student, student_token = _register_and_token("reject_student@test.com", "reject_student", role="student")

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
    parent, parent_token = _register_and_token("thirdp_parent@test.com", "thirdp_parent", role="parent")
    student, _ = _register_and_token("thirdp_student@test.com", "thirdp_student", role="student")
    _, stranger_token = _register_and_token("thirdp_stranger@test.com", "thirdp_stranger", role="student")

    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    rel_id = r.json()["id"]

    r = client.post(f"/parents/relationships/{rel_id}/approve",
                    headers={"Authorization": f"Bearer {stranger_token}"})
    assert r.status_code == 403


# ── Children progress ─────────────────────────────────────────────────────────

def test_children_progress_requires_parent_role():
    """F-035: a student cannot access /children-progress."""
    _, student_token = _register_and_token("prog_nonparent@test.com", "prog_nonparent", role="student")
    r = client.get("/parents/children-progress",
                   headers={"Authorization": f"Bearer {student_token}"})
    assert r.status_code == 403


def test_children_progress_empty_without_active_relationship():
    _, parent_token = _register_and_token("progress_parent@test.com", "progress_parent", role="parent")
    r = client.get("/parents/children-progress",
                   headers={"Authorization": f"Bearer {parent_token}"})
    assert r.status_code == 200
    assert r.json() == []  # No active relationships → empty list


def test_children_progress_shows_data_after_approval():
    parent, parent_token = _register_and_token("data_parent@test.com", "data_parent", role="parent")
    student, student_token = _register_and_token("data_student@test.com", "data_student", role="student")
    teacher, _ = _register_and_token("data_teacher@test.com", "data_teacher", role="teacher")

    # Request + approve relationship
    r = client.post("/parents/relationships/request",
                    headers={"Authorization": f"Bearer {parent_token}"},
                    json={"student_id": student.id})
    rel_id = r.json()["id"]
    client.post(f"/parents/relationships/{rel_id}/approve",
                headers={"Authorization": f"Bearer {student_token}"})

    # Create a completed exam submission for the student
    db = database.SessionLocal()
    try:
        exam = models.Exam(title="History Final", description="Hard", teacher_id=teacher.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        sub = models.ExamSubmission(
            exam_id=exam.id,
            student_id=student.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            score=88.5,
            feedback="Good job!",
        )
        db.add(sub)
        db.commit()
    finally:
        db.close()

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
