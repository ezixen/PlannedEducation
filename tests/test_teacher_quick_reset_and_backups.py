"""
Tests for Teacher Classroom Quick Password Reset, Brute-Force Lockout,
and Admin Database Backup Services.
"""

from datetime import UTC, datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from plannededucation.api import backup_service, database, models
from plannededucation.api.main import app
from plannededucation.api.routes_auth import get_password_hash


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_user(db, email, username, role="student", is_admin=False, teacher_approved=True):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    user = models.User(
        email=email,
        username=username,
        full_name=username.capitalize(),
        hashed_password=get_password_hash("TestPassword123!"),
        role=role,
        is_admin=is_admin,
        is_active=True,
        teacher_approved=teacher_approved,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_auth_token(client, email_or_uname, password="TestPassword123!"):
    res = client.post("/auth/token", data={"username": email_or_uname, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_teacher_quick_reset_and_student_completion(client, db_session):
    # Setup teacher and student
    teacher = create_test_user(db_session, "teacher_quick@school.edu", "teacherquick", role="teacher", teacher_approved=True)
    student = create_test_user(db_session, "student_quick@school.edu", "studentquick", role="student")
    admin = create_test_user(db_session, "admin_quick@school.edu", "adminquick", role="admin", is_admin=True)

    t_token = get_auth_token(client, "teacher_quick@school.edu")

    # 1. Teacher initiates quick reset for student
    res = client.post(
        f"/auth/teacher/quick-reset/{student.id}",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify student is flagged for reset
    db_session.refresh(student)
    assert student.force_password_reset is True

    # 2. Student attempts login with old password -> should intercept with TEACHER_RESET_ACTIVE
    login_res = client.post("/auth/token", data={"username": "student_quick@school.edu", "password": "TestPassword123!"})
    assert login_res.status_code == 403
    assert "TEACHER_RESET_ACTIVE" in login_res.json()["detail"]

    # 3. Check status via endpoint
    check_res = client.post("/auth/teacher-reset/check", json={"identifier": "student_quick@school.edu"})
    assert check_res.status_code == 200
    assert check_res.json()["teacher_reset_active"] is True

    # 4. Student sets new password
    new_pwd = "BrandNewPassword2026!"
    complete_res = client.post("/auth/teacher-reset/complete", json={
        "identifier": "student_quick@school.edu",
        "new_password": new_pwd,
    })
    assert complete_res.status_code == 200
    assert "access_token" in complete_res.json()

    # 5. Verify student can now log in normally with new password
    token2 = get_auth_token(client, "student_quick@school.edu", password=new_pwd)
    assert token2 is not None

    # 6. Verify teacher cannot reset an administrator's account
    bad_res = client.post(
        f"/auth/teacher/quick-reset/{admin.id}",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert bad_res.status_code == 400
    assert "Teachers can only quick-reset student accounts" in bad_res.json()["detail"]


def test_brute_force_lockout(client, db_session):
    victim = create_test_user(db_session, "victim@school.edu", "victimstudent", role="student")
    # Reset any lockout
    victim.failed_login_attempts = 0
    victim.locked_until = None
    db_session.commit()

    # 4 bad attempts
    for _ in range(4):
        res = client.post("/auth/token", data={"username": "victim@school.edu", "password": "WrongPassword!"})
        assert res.status_code == 401

    # 5th bad attempt -> triggers 15 min lock
    res5 = client.post("/auth/token", data={"username": "victim@school.edu", "password": "WrongPassword!"})
    assert res5.status_code == 403
    assert "temporarily locked" in res5.json()["detail"]

    # Even right password is now blocked while locked
    res_blocked = client.post("/auth/token", data={"username": "victim@school.edu", "password": "TestPassword123!"})
    assert res_blocked.status_code == 403
    assert "temporarily locked" in res_blocked.json()["detail"]


def test_admin_database_backup_operations(client, db_session):
    superadmin = create_test_user(db_session, "superadmin_backup@school.edu", "superbackup", role="admin", is_admin=True)
    admin_token = get_auth_token(client, "superadmin_backup@school.edu")

    # 1. Trigger manual backup
    res = client.post("/admin/database/backup", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "filename" in data
    filename = data["filename"]

    # 2. List backups
    list_res = client.get("/admin/database/backups", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    backups = list_res.json()
    assert any(b["filename"] == filename for b in backups)

    # 3. Download backup
    dl_res = client.get(f"/admin/database/backups/{filename}/download", headers={"Authorization": f"Bearer {admin_token}"})
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0

    # 4. Delete backup
    del_res = client.delete(f"/admin/database/backups/{filename}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"


def test_admin_password_protection(client, db_session):
    superadmin = create_test_user(db_session, "super_boss@school.edu", "superboss", role="admin", is_admin=True)
    normal_teacher = create_test_user(db_session, "normal_teacher@school.edu", "normalteacher", role="teacher", is_admin=False)

    teacher_token = get_auth_token(client, "normal_teacher@school.edu")

    # Non-superadmin cannot reset superadmin's password
    res = client.post(
        f"/admin/users/{superadmin.id}/reset-password",
        json={"reset_2fa": False},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert res.status_code == 403
    assert "Superadmin privilege required" in res.json()["detail"]

