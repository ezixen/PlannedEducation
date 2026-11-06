"""F-048 residual: authenticated sealed offline sync + teacher sync URL policy."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app
from src.plannededucation.api.routes_auth import get_password_hash
from src.plannededucation.api.routes_sync import MAX_SEALED_SYNC_BYTES
from src.plannededucation.api.url_safety import UnsafeURLError, validate_teacher_sync_url

client = TestClient(app)


def _token_for(
    email: str, password: str = "SecurePassw0rd!", role: str = "student"
) -> tuple[str, str]:
    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            user = models.User(
                email=email,
                username=email.split("@")[0] + "_" + uuid.uuid4().hex[:6],
                full_name="Sync User",
                hashed_password=get_password_hash(password),
                role=role,
                teacher_approved=(role == "teacher"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    login = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"], user_id


def _make_exam(teacher_id: str) -> str:
    db = database.SessionLocal()
    try:
        exam = models.Exam(
            id=str(uuid.uuid4()),
            title="Sync Exam",
            teacher_id=teacher_id,
            duration_minutes=30,
        )
        db.add(exam)
        db.commit()
        return exam.id
    finally:
        db.close()


def _sealed_body(
    *,
    submission_id: str,
    exam_id: str,
    student_id: str,
    content_hash: str = "c" * 40,
    sync_hash: str = "d" * 40,
    extra: dict | None = None,
) -> dict:
    body = {
        "submissionId": submission_id,
        "examId": exam_id,
        "studentId": student_id,
        "contentHash": content_hash,
        "sync": {"syncHash": sync_hash},
        "answers": [],
    }
    if extra:
        body.update(extra)
    return body


# ── Teacher sync URL policy (private/LAN only; opposite of AI SSRF) ───────────


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.1.50:8787",
        "https://10.0.0.12/sync",
        "http://172.16.0.1",
        "http://127.0.0.1:9000",
        "http://localhost:9000",
    ],
)
def test_f048_teacher_sync_allows_private_lan(url: str):
    assert validate_teacher_sync_url(url, resolve_dns=False).startswith("http")


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.com/exfil",
        "https://8.8.8.8/",
        "https://1.1.1.1/collect",
        "file:///etc/passwd",
        "https://user:pass@192.168.1.1/",
    ],
)
def test_f048_teacher_sync_blocks_public_and_exfil(url: str):
    with pytest.raises(UnsafeURLError):
        validate_teacher_sync_url(url, resolve_dns=False)


def test_f048_teacher_sync_allowlist_hostname(monkeypatch):
    monkeypatch.setenv("TEACHER_SYNC_URL_ALLOWLIST", "sync.school.local,other.lan")
    assert validate_teacher_sync_url(
        "https://sync.school.local:8443", resolve_dns=False
    ).startswith("https://")
    with pytest.raises(UnsafeURLError):
        validate_teacher_sync_url("https://not-listed.example", resolve_dns=False)


# ── Authenticated sealed sync endpoints ──────────────────────────────────────


def test_f048_unauthenticated_post_returns_401():
    res = client.post(
        "/sync/submission",
        json=_sealed_body(
            submission_id=str(uuid.uuid4()),
            exam_id=str(uuid.uuid4()),
            student_id=str(uuid.uuid4()),
        ),
    )
    assert res.status_code == 401


def test_f048_unauthenticated_get_returns_401():
    res = client.get(f"/sync/submission/{uuid.uuid4()}")
    assert res.status_code == 401


def test_f048_student_ownership_foreign_denied_teacher_can_get():
    student_token, student_id = _token_for("f048_student@example.com", role="student")
    other_token, _other_id = _token_for("f048_other@example.com", role="student")
    teacher_token, teacher_id = _token_for("f048_teacher@example.com", role="teacher")
    other_teacher_token, _other_teacher_id = _token_for(
        "f048_teacher_other@example.com", role="teacher"
    )
    exam_id = _make_exam(teacher_id)

    submission_id = str(uuid.uuid4())
    body = _sealed_body(
        submission_id=submission_id,
        exam_id=exam_id,
        student_id=student_id,
    )

    own = client.post(
        "/sync/submission",
        headers={"Authorization": f"Bearer {student_token}"},
        json=body,
    )
    assert own.status_code == 200, own.text
    assert own.json().get("submissionId") == submission_id or own.json().get(
        "submission_id"
    ) == submission_id

    # Foreign student cannot upload claiming another student's id
    foreign = client.post(
        "/sync/submission",
        headers={"Authorization": f"Bearer {other_token}"},
        json={**body, "submissionId": str(uuid.uuid4())},
    )
    assert foreign.status_code == 403

    # Owner student can GET
    student_get = client.get(
        f"/sync/submission/{submission_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_get.status_code == 200, student_get.text
    assert student_get.json().get("contentHash") == "c" * 40

    # Exam teacher owner can GET
    teacher_get = client.get(
        f"/sync/submission/{submission_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert teacher_get.status_code == 200, teacher_get.text

    # Unrelated student denied
    denied = client.get(
        f"/sync/submission/{submission_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 403

    # Unrelated teacher denied
    other_teacher_denied = client.get(
        f"/sync/submission/{submission_id}",
        headers={"Authorization": f"Bearer {other_teacher_token}"},
    )
    assert other_teacher_denied.status_code == 403


def test_f048_oversized_payload_rejected():
    student_token, student_id = _token_for("f048_big@example.com", role="student")
    _teacher_token, teacher_id = _token_for(
        "f048_big_teacher@example.com", role="teacher"
    )
    exam_id = _make_exam(teacher_id)
    huge = "x" * (MAX_SEALED_SYNC_BYTES + 100)
    body = _sealed_body(
        submission_id=str(uuid.uuid4()),
        exam_id=exam_id,
        student_id=student_id,
        extra={"blob": huge},
    )
    assert len(json.dumps(body).encode()) > MAX_SEALED_SYNC_BYTES
    res = client.post(
        "/sync/submission",
        headers={"Authorization": f"Bearer {student_token}"},
        json=body,
    )
    assert res.status_code == 413, res.text


def test_f048_missing_content_hash_rejected():
    student_token, student_id = _token_for("f048_nohash@example.com", role="student")
    _teacher_token, teacher_id = _token_for(
        "f048_nohash_teacher@example.com", role="teacher"
    )
    exam_id = _make_exam(teacher_id)
    body = _sealed_body(
        submission_id=str(uuid.uuid4()),
        exam_id=exam_id,
        student_id=student_id,
    )
    del body["contentHash"]
    res = client.post(
        "/sync/submission",
        headers={"Authorization": f"Bearer {student_token}"},
        json=body,
    )
    assert res.status_code == 422
