"""F-050 — deny-by-default negative auth/role matrix for hardened routes.

Covers student / unapproved teacher / parent / non-owner / unauthenticated
denials against exam create, admin user management, teacher approval, and
OCR review mutate endpoints. Does not exercise webcam/eyetracking/homeschool
product features.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app

PASSWORD = "SecurePassw0rd!"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _register(
    client: TestClient,
    *,
    role: str,
    prefix: str,
    approve_teacher: bool | None = None,
) -> dict:
    """Register a user with an explicit role and return login helpers.

    Teachers are auto-approved in PLANNED_EDUCATION_ENV=test unless the
    email/username contains ``pending``. Callers that need a pending teacher
    should pass approve_teacher=False (DB override) or use a pending prefix.
    """
    tag = _uid()
    email = f"{prefix}_{tag}@example.com"
    username = f"{prefix}_{tag}"
    res = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": PASSWORD,
            "full_name": f"F050 {prefix}",
            "role": role,
        },
    )
    assert res.status_code in (200, 201), res.text

    if role == "teacher" and approve_teacher is not None:
        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            assert user is not None
            user.teacher_approved = approve_teacher
            db.commit()
        finally:
            db.close()

    login = client.post(
        "/auth/token",
        data={"username": email, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        user_id = user.id
    finally:
        db.close()

    return {
        "email": email,
        "user_id": user_id,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def _seed_ocr_review(*, teacher_id: str, student_id: str) -> str:
    """Insert exam + submission + pending OCR review; return review id."""
    db = database.SessionLocal()
    try:
        exam = models.Exam(
            id=str(uuid.uuid4()),
            title="F050 OCR Exam",
            teacher_id=teacher_id,
            duration_minutes=30,
        )
        db.add(exam)
        db.flush()
        submission = models.ExamSubmission(
            id=str(uuid.uuid4()),
            exam_id=exam.id,
            student_id=student_id,
        )
        db.add(submission)
        db.flush()
        review = models.OCRReview(
            id=str(uuid.uuid4()),
            submission_id=submission.id,
            exam_id=exam.id,
            student_id=student_id,
            original_text="placeholder answer",
            original_confidence=0.9,
            is_handwritten=False,
            status=models.OCRReviewStatus.pending,
        )
        db.add(review)
        db.commit()
        return review.id
    finally:
        db.close()


# ── Student denials ───────────────────────────────────────────────────────────


def test_f050_student_cannot_create_exam(client: TestClient):
    student = _register(client, role="student", prefix="f050_stu_exam")
    res = client.post(
        "/exams/",
        headers=student["headers"],
        json={"title": "Rogue Exam", "duration_minutes": 30},
    )
    assert res.status_code == 403


def test_f050_student_cannot_create_admin_user(client: TestClient):
    student = _register(client, role="student", prefix="f050_stu_admin")
    res = client.post(
        "/admin/users",
        headers=student["headers"],
        json={
            "username": f"rogue_{_uid()}",
            "email": f"rogue_{_uid()}@example.com",
            "full_name": "Rogue Admin",
            "role": "admin",
        },
    )
    assert res.status_code == 403


def test_f050_student_cannot_approve_teachers(client: TestClient):
    student = _register(client, role="student", prefix="f050_stu_appr")
    pending = _register(
        client, role="teacher", prefix="f050_pending_tgt", approve_teacher=False
    )
    res = client.post(
        f"/admin/teachers/{pending['user_id']}/approve",
        headers=student["headers"],
    )
    assert res.status_code == 403


# ── Unapproved teacher ────────────────────────────────────────────────────────


def test_f050_unapproved_teacher_cannot_create_exam(client: TestClient):
    teacher = _register(
        client, role="teacher", prefix="f050_unapp", approve_teacher=False
    )
    res = client.post(
        "/exams/",
        headers=teacher["headers"],
        json={"title": "Pending Teacher Exam", "duration_minutes": 45},
    )
    assert res.status_code == 403


# ── Parent denials ────────────────────────────────────────────────────────────


def test_f050_parent_cannot_access_admin_routes(client: TestClient):
    parent = _register(client, role="parent", prefix="f050_par_adm")
    for path in ("/admin/stats", "/admin/users", "/admin/exams", "/admin/pending-teachers"):
        res = client.get(path, headers=parent["headers"])
        assert res.status_code == 403, f"{path} -> {res.status_code}"


def test_f050_parent_cannot_mutate_ocr_review(client: TestClient):
    parent = _register(client, role="parent", prefix="f050_par_ocr")
    teacher = _register(
        client, role="teacher", prefix="f050_ocr_owner", approve_teacher=True
    )
    student = _register(client, role="student", prefix="f050_ocr_stu")
    review_id = _seed_ocr_review(
        teacher_id=teacher["user_id"], student_id=student["user_id"]
    )

    create = client.post(
        "/ocr/review/",
        headers=parent["headers"],
        json={
            "submission_id": str(uuid.uuid4()),
            "exam_id": str(uuid.uuid4()),
            "student_id": student["user_id"],
            "original_text": "parent inject",
            "original_confidence": 0.5,
        },
    )
    assert create.status_code == 403

    update = client.put(
        f"/ocr/review/{review_id}",
        headers=parent["headers"],
        json={"status": "approved", "corrected_text": "hijack"},
    )
    assert update.status_code == 403

    approve = client.post(
        f"/ocr/review/{review_id}/approve",
        headers=parent["headers"],
        json={"status": "approved"},
    )
    assert approve.status_code == 403

    delete = client.delete(f"/ocr/review/{review_id}", headers=parent["headers"])
    assert delete.status_code == 403


# ── Non-owner teacher exam mutation ───────────────────────────────────────────


def test_f050_non_owner_teacher_cannot_mutate_exam(client: TestClient):
    owner = _register(client, role="teacher", prefix="f050_own", approve_teacher=True)
    other = _register(client, role="teacher", prefix="f050_oth", approve_teacher=True)

    created = client.post(
        "/exams/",
        headers=owner["headers"],
        json={"title": "Owner Only Exam", "duration_minutes": 40},
    )
    assert created.status_code == 201, created.text
    exam_id = created.json()["id"]

    add_q = client.post(
        f"/exams/{exam_id}/questions",
        headers=other["headers"],
        json={
            "question_type": "essay",
            "text": "Unauthorized question",
            "points": 1,
        },
    )
    assert add_q.status_code == 403

    detail = client.get(f"/exams/{exam_id}", headers=other["headers"])
    assert detail.status_code == 403

    delete = client.delete(f"/exams/{exam_id}", headers=other["headers"])
    assert delete.status_code == 403


# ── Unauthenticated ───────────────────────────────────────────────────────────


def test_f050_unauthenticated_401_on_admin_and_exam_create(client: TestClient):
    admin_res = client.get("/admin/stats")
    assert admin_res.status_code == 401

    exam_res = client.post(
        "/exams/",
        json={"title": "Anon Exam", "duration_minutes": 20},
    )
    assert exam_res.status_code == 401

    approve_res = client.post(f"/admin/teachers/{uuid.uuid4()}/approve")
    assert approve_res.status_code == 401
