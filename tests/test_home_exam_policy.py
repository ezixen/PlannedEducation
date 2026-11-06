"""Home-exam / classroom delivery gates (platform + per-exam)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.plannededucation.api import models
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.deployment_config import (
    DeploymentConfigSchema,
    load_deployment_config,
    save_deployment_config,
)
from src.plannededucation.api.main import app

client = TestClient(app)


def _register(role: str = "teacher") -> tuple[str, dict]:
    email = f"home_{role}_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": email.split("@")[0],
            "password": password,
            "full_name": f"Home {role}",
            "role": role,
        },
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    if role == "teacher":
        db = SessionLocal()
        try:
            u = db.query(models.User).filter(models.User.id == user_id).first()
            assert u is not None
            u.teacher_approved = True
            db.commit()
        finally:
            db.close()
    tok = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert tok.status_code == 200, tok.text
    return user_id, {"Authorization": f"Bearer {tok.json()['access_token']}"}


def _set_platform_home_exam(enabled: bool) -> None:
    cfg = load_deployment_config()
    cfg["home_exam_proctoring_enabled"] = enabled
    save_deployment_config(DeploymentConfigSchema(**cfg))


def test_feature_status_defaults_off():
    _set_platform_home_exam(False)
    _, headers = _register("student")
    res = client.get("/proctoring/feature-status", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["home_exam_proctoring_enabled"] is False
    assert body["beta"] is True


def test_teacher_cannot_enable_home_exam_when_platform_off():
    _set_platform_home_exam(False)
    _, headers = _register("teacher")
    create = client.post(
        "/exams/",
        headers=headers,
        json={
            "title": "Classroom math",
            "duration_minutes": 30,
            "home_exam_enabled": True,
        },
    )
    assert create.status_code == 403


def test_delivery_mode_and_consent_gated():
    _set_platform_home_exam(True)
    _, teacher_h = _register("teacher")
    create = client.post(
        "/exams/",
        headers=teacher_h,
        json={"title": "Remote quiz", "duration_minutes": 20, "home_exam_enabled": False},
    )
    assert create.status_code == 201, create.text
    exam_id = create.json()["id"]
    assert create.json().get("home_exam_enabled") is False

    # Platform on but exam still classroom → consent denied
    _, student_h = _register("student")
    denied = client.post(
        "/proctoring/consent",
        headers=student_h,
        json={
            "exam_id": exam_id,
            "consent_version": "1.0",
            "camera_consent": True,
            "microphone_consent": True,
            "screen_recording_consent": False,
            "data_processing_consent": True,
        },
    )
    assert denied.status_code == 403

    enabled = client.put(
        f"/exams/{exam_id}/delivery-mode",
        headers=teacher_h,
        json={"home_exam_enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["home_exam_enabled"] is True

    ok = client.post(
        "/proctoring/consent",
        headers=student_h,
        json={
            "exam_id": exam_id,
            "consent_version": "1.0",
            "camera_consent": True,
            "microphone_consent": True,
            "screen_recording_consent": False,
            "data_processing_consent": True,
        },
    )
    assert ok.status_code == 201, ok.text
    _set_platform_home_exam(False)
