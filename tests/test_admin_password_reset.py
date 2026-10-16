"""
tests/test_admin_password_reset.py
Comprehensive test suite verifying:
1. Admin direct password reset (without requiring email)
2. Auto-generated temporary password complexity & verification
3. Direct 2FA / Passkey reset by admin
4. Non-admin authorization rejection (403 Forbidden)
5. Modular email service (Brevo, SMTP, and Console mock fallback)
"""

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.plannededucation.api import database, email_service, models
from src.plannededucation.api.main import app
from src.plannededucation.api.routes_auth import get_password_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean database session for each test."""
    db: Session = next(database.get_db())
    try:
        # Clear existing test users
        db.query(models.User).filter(
            models.User.email.in_([
                "school_admin@test.edu",
                "lost_student@test.edu",
                "regular_student@test.edu",
                "twofa_teacher@test.edu",
            ])
        ).delete(synchronize_session=False)
        db.commit()
        yield db
    finally:
        db.close()


def _create_user(db: Session, email: str, username: str, role: str = "student", is_admin: bool = False, password: str = "InitialPass#1234") -> models.User:
    user = models.User(
        email=email,
        username=username,
        full_name=username.capitalize(),
        role=role,
        is_admin=is_admin,
        is_active=True,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(email: str, password: str) -> dict:
    resp = client.post("/auth/token", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_reset_user_password_with_custom_password(clean_db):
    """Admin can reset a user's password directly with a custom password."""
    admin = _create_user(clean_db, "school_admin@test.edu", "adminuser", role="admin", is_admin=True)
    student = _create_user(clean_db, "lost_student@test.edu", "loststudent", role="student", is_admin=False)

    admin_headers = _get_auth_headers(admin.email, "InitialPass#1234")

    # Admin resets student password
    new_pwd = "NewSchoolYear#2026!"
    reset_resp = client.post(
        f"/admin/users/{student.id}/reset-password",
        headers=admin_headers,
        json={"new_password": new_pwd, "reset_2fa": False},
    )
    assert reset_resp.status_code == 200, reset_resp.text
    data = reset_resp.json()
    assert data["status"] == "success"
    assert data["username"] == "loststudent"
    assert data["temporary_password"] == new_pwd

    # Student can now log in with the new password
    student_token_resp = client.post("/auth/token", data={"username": student.email, "password": new_pwd})
    assert student_token_resp.status_code == 200
    assert "access_token" in student_token_resp.json()

    # Old password no longer works
    old_token_resp = client.post("/auth/token", data={"username": student.email, "password": "InitialPass#1234"})
    assert old_token_resp.status_code == 401


def test_admin_reset_user_password_with_auto_generated_temporary_password(clean_db):
    """Admin can reset a user's password without specifying one (auto-generated)."""
    admin = _create_user(clean_db, "school_admin@test.edu", "adminuser", role="admin", is_admin=True)
    student = _create_user(clean_db, "lost_student@test.edu", "loststudent", role="student", is_admin=False)

    admin_headers = _get_auth_headers(admin.email, "InitialPass#1234")

    # Admin resets with empty/None new_password
    reset_resp = client.post(
        f"/admin/users/{student.id}/reset-password",
        headers=admin_headers,
        json={"new_password": None, "reset_2fa": False},
    )
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    temp_pwd = data["temporary_password"]
    assert temp_pwd.startswith("TempPass#")
    assert len(temp_pwd) >= 12

    # Student logs in with the auto-generated temporary password
    login_resp = client.post("/auth/token", data={"username": student.email, "password": temp_pwd})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_admin_reset_user_password_and_clear_2fa(clean_db):
    """Admin can reset password AND disable 2FA for users who lost their authenticator device."""
    admin = _create_user(clean_db, "school_admin@test.edu", "adminuser", role="admin", is_admin=True)
    teacher = _create_user(clean_db, "twofa_teacher@test.edu", "twofateacher", role="teacher", is_admin=False)

    # Enable 2FA on teacher account
    teacher_headers = _get_auth_headers(teacher.email, "InitialPass#1234")
    setup_resp = client.post("/auth/2fa/setup", headers=teacher_headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]

    code = pyotp.TOTP(secret).now()
    confirm_resp = client.post("/auth/2fa/confirm", headers=teacher_headers, json={"code": code})
    assert confirm_resp.status_code == 200

    # Verify 2FA is active
    clean_db.refresh(teacher)
    assert teacher.totp_enabled is True

    # Admin resets password and forces reset_2fa=True
    admin_headers = _get_auth_headers(admin.email, "InitialPass#1234")
    reset_resp = client.post(
        f"/admin/users/{teacher.id}/reset-password",
        headers=admin_headers,
        json={"new_password": "NewTeacherPass#2026!", "reset_2fa": True},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["reset_2fa"] is True

    # Verify teacher in DB has 2FA disabled
    clean_db.refresh(teacher)
    assert teacher.totp_enabled is False
    assert teacher.totp_secret is None

    # Teacher logs in directly without 2FA challenge
    login_resp = client.post("/auth/token", data={"username": teacher.email, "password": "NewTeacherPass#2026!"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_non_admin_cannot_reset_passwords(clean_db):
    """Students cannot access the admin reset-password endpoint."""
    student1 = _create_user(clean_db, "regular_student@test.edu", "regstudent", role="student", is_admin=False)
    student2 = _create_user(clean_db, "lost_student@test.edu", "loststudent", role="student", is_admin=False)

    student1_headers = _get_auth_headers(student1.email, "InitialPass#1234")

    resp = client.post(
        f"/admin/users/{student2.id}/reset-password",
        headers=student1_headers,
        json={"new_password": "HackedPassword#2026!", "reset_2fa": False},
    )
    assert resp.status_code == 403


def test_email_service_fallback_and_status(monkeypatch):
    """Email service status and mock fallback functionality."""
    import asyncio

    # When no keys configured
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)

    assert email_service.is_email_configured() is False
    status = email_service.get_email_status()
    assert status["configured"] is False
    assert status["provider"] == "console_mock"

    # Send should succeed (logged safely without exceptions)
    success = asyncio.run(email_service.send_password_reset_email("test@school.edu", "123456", "teststudent"))
    assert success is True

    # When Brevo is configured
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-test-mock-key")
    assert email_service.is_email_configured() is True
    status_brevo = email_service.get_email_status()
    assert status_brevo["provider"] == "brevo"


