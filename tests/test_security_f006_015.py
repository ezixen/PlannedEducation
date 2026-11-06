"""Focused regression tests for the F-006–F-015 security controls."""

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from src.plannededucation.api import database, db_encryption, models, routes_anonymizer
from src.plannededucation.api.authorization import require_exam_author
from src.plannededucation.api.main import app
from src.plannededucation.api.schema_ensure import ensure_schema

client = TestClient(app)


def test_answer_sensitive_fields_are_registered_for_encryption():
    assert {
        "student_response",
        "generated_question_text",
        "generated_options_json",
    }.issubset(models.Answer.__encrypted_fields__)


def test_database_encryption_uses_versioned_envelope_and_rejects_bad_ciphertext(
    monkeypatch,
):
    key = Fernet.generate_key()
    monkeypatch.setattr(db_encryption, "_db_fernet", Fernet(key))

    encrypted = db_encryption.encrypt_field("gAAAA is valid student text")
    assert encrypted is not None
    assert encrypted.startswith("pe-db-v1$")
    assert db_encryption.decrypt_field(encrypted) == "gAAAA is valid student text"

    with pytest.raises(RuntimeError, match="failed authentication"):
        db_encryption.decrypt_field("pe-db-v1$gAAAA-invalid")


def test_privacy_scrubber_fails_closed_when_unavailable(monkeypatch):
    monkeypatch.setattr(routes_anonymizer, "_presidio_checked", True)
    monkeypatch.setattr(routes_anonymizer, "_analyzer", None)
    monkeypatch.setattr(routes_anonymizer, "PRESIDIO_AVAILABLE", False)

    with pytest.raises(routes_anonymizer.PrivacyScrubbingError):
        routes_anonymizer.scrub_pii("Student answer with an email@example.edu")


def test_students_cannot_author_exams():
    student = models.User(role="student", is_admin=False, teacher_approved=True)
    with pytest.raises(HTTPException) as exc_info:
        require_exam_author(student)
    assert exc_info.value.status_code == 403


def test_pending_teachers_cannot_author_exams():
    teacher = models.User(role="teacher", is_admin=False, teacher_approved=False)
    with pytest.raises(HTTPException) as exc_info:
        require_exam_author(teacher)
    assert exc_info.value.status_code == 403


def test_schema_assurance_records_versioned_migrations():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    ensure_schema(engine, models.Base.metadata)

    with engine.connect() as connection:
        migration_rows = connection.exec_driver_sql(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert [row[0] for row in migration_rows] == [1, 2, 3, 4, 5]
    assert "refresh_sessions" in inspect(engine).get_table_names()
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert "is_superadmin" in columns


def test_exam_authorization_and_server_deadline():
    teacher_email = "security_teacher_f015@example.com"
    student_email = "security_student_f015@example.com"
    teacher_password = "Teacher1234!"
    student_password = "Student1234!"

    teacher_registration = client.post(
        "/auth/register",
        json={
            "email": teacher_email,
            "username": "security_teacher_f015",
            "password": teacher_password,
            "role": "teacher",
        },
    )
    student_registration = client.post(
        "/auth/register",
        json={
            "email": student_email,
            "username": "security_student_f015",
            "password": student_password,
            "role": "student",
        },
    )
    assert teacher_registration.status_code == 201
    assert student_registration.status_code == 201

    teacher_token = client.post(
        "/auth/token", data={"username": teacher_email, "password": teacher_password}
    ).json()["access_token"]
    student_token = client.post(
        "/auth/token", data={"username": student_email, "password": student_password}
    ).json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    forbidden_create = client.post(
        "/exams/",
        headers=student_headers,
        json={"title": "Unauthorized", "duration_minutes": 1},
    )
    assert forbidden_create.status_code == 403

    exam_response = client.post(
        "/exams/",
        headers=teacher_headers,
        json={
            "title": "Deadline Security",
            "duration_minutes": 1,
            "seb_config_key": "security-test-key",
        },
    )
    assert exam_response.status_code == 201, exam_response.text
    exam_id = exam_response.json()["id"]
    question_response = client.post(
        f"/exams/{exam_id}/questions",
        headers=teacher_headers,
        json={"question_type": "essay", "text": "Answer", "points": 1},
    )
    assert question_response.status_code == 201

    start_response = client.post(f"/exams/{exam_id}/start", headers=student_headers)
    assert start_response.status_code == 200, start_response.text
    question_id = start_response.json()["questions"][0]["question_id"]

    db = database.SessionLocal()
    try:
        submission = (
            db.query(models.ExamSubmission)
            .filter(models.ExamSubmission.id == start_response.json()["submission_id"])
            .first()
        )
        assert submission is not None
        submission.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    late_response = client.post(
        f"/exams/{exam_id}/submit",
        headers=student_headers,
        json={"answers": [{"question_id": question_id, "response": "late"}]},
    )
    assert late_response.status_code == 409
