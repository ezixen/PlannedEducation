"""
Unit tests for In-App Notifications, Teacher Self-Registration Approval,
Admin Emergency Backup Codes, and Internal Password Reset Requests.
"""

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api import models
from src.plannededucation.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_student_registration_and_recovery_codes(client):
    """Ensure user registration returns 5 one-time recovery codes."""
    res = client.post("/auth/register", json={
        "email": "student_recov@example.com",
        "username": "student_recov",
        "password": "Password123!",
        "full_name": "Recovery Student",
        "role": "student",
    })
    assert res.status_code == 201
    data = res.json()
    assert "recovery_codes" in data
    assert len(data["recovery_codes"]) == 5
    assert data["role"] == "student"
    assert data["teacher_approved"] is True


def test_admin_cannot_self_register(client):
    """Admins cannot self-register through public registration endpoint."""
    res = client.post("/auth/register", json={
        "email": "fake_admin@example.com",
        "username": "fake_admin",
        "password": "Password123!",
        "full_name": "Fake Admin",
        "role": "admin",
    })
    # Either 422 (Pydantic regex) or 403 (explicit check)
    assert res.status_code in (403, 422)


def test_teacher_self_registration_pending_approval(client, db):
    """Self-registered teacher defaults to pending approval and notifies admins."""
    # Ensure an admin exists in db
    admin = db.query(models.User).filter(models.User.email == "admin_for_notif@example.com").first()
    if not admin:
        client.post("/auth/register", json={
            "email": "admin_for_notif@example.com",
            "username": "admin_for_notif",
            "password": "Password123!",
            "full_name": "Admin Supervisor",
            "role": "teacher",
        })
        admin = db.query(models.User).filter(models.User.email == "admin_for_notif@example.com").first()
        admin.is_admin = True
        admin.teacher_approved = True
        db.commit()

    # Self-register a teacher
    res = client.post("/auth/register", json={
        "email": "teacher_pending@example.com",
        "username": "teacher_pending",
        "password": "Password123!",
        "full_name": "Pending Teacher",
        "role": "teacher",
    })
    assert res.status_code == 201
    teacher_data = res.json()
    assert teacher_data["teacher_approved"] is False

    # Check that admin received an InAppNotification
    notif = db.query(models.InAppNotification).filter(
        models.InAppNotification.user_id == admin.id,
        models.InAppNotification.type == "teacher_approval"
    ).order_by(models.InAppNotification.created_at.desc()).first()
    assert notif is not None
    assert "Pending Teacher" in notif.message or "teacher_pending" in notif.message

    # Teacher tries to create an exam while pending -> 403 Forbidden
    login_res = client.post("/auth/token", data={
        "username": "teacher_pending@example.com",
        "password": "Password123!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    exam_res = client.post("/exams/", json={
        "title": "Unauthorized Exam",
        "description": "Should fail",
        "duration_minutes": 30,
    }, headers=headers)
    assert exam_res.status_code == 403
    assert "pending administrator approval" in exam_res.json()["detail"].lower()

    # Admin approves teacher
    admin_login = client.post("/auth/token", data={
        "username": "admin_for_notif@example.com",
        "password": "Password123!",
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    approve_res = client.post(f"/admin/teachers/{teacher_data['id']}/approve", headers=admin_headers)
    assert approve_res.status_code == 200

    # Teacher now successfully creates exam
    exam_res2 = client.post("/exams/", json={
        "title": "Authorized Exam",
        "description": "Should succeed",
        "duration_minutes": 30,
    }, headers=headers)
    assert exam_res2.status_code == 201


def test_admin_emergency_backup_codes(client, db):
    """Admin can view backup codes status and generate fresh emergency backup codes."""
    admin = db.query(models.User).filter(models.User.email == "admin_backup@example.com").first()
    if not admin:
        client.post("/auth/register", json={
            "email": "admin_backup@example.com",
            "username": "admin_backup",
            "password": "Password123!",
            "full_name": "Admin Backup Tester",
            "role": "teacher",
        })
        admin = db.query(models.User).filter(models.User.email == "admin_backup@example.com").first()
        admin.is_admin = True
        admin.teacher_approved = True
        db.commit()

    login = client.post("/auth/token", data={
        "username": "admin_backup@example.com",
        "password": "Password123!",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Generate fresh emergency codes
    gen_res = client.post("/admin/backup-codes/generate", headers=headers)
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert "recovery_codes" in data
    assert len(data["recovery_codes"]) == 5

    # Check status endpoint
    status_res = client.get("/admin/backup-codes", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_backup_codes"] is True
    assert status_res.json()["active_codes_count"] == 5


def test_notifications_unread_count_and_lifecycle(client, db):
    """Test notification list, unread count polling, marking as read, and deleting."""
    user = db.query(models.User).filter(models.User.email == "notif_user@example.com").first()
    if not user:
        client.post("/auth/register", json={
            "email": "notif_user@example.com",
            "username": "notif_user",
            "password": "Password123!",
            "full_name": "Notification User",
            "role": "student",
        })
        user = db.query(models.User).filter(models.User.email == "notif_user@example.com").first()

    login = client.post("/auth/token", data={
        "username": "notif_user@example.com",
        "password": "Password123!",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Add a mock notification directly to user
    notif = models.InAppNotification(
        user_id=user.id,
        title="Test Notification",
        message="This is a test notification",
        type="system",
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Poller endpoint: unread count
    count_res = client.get("/notifications/unread-count", headers=headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] >= 1

    # List notifications
    list_res = client.get("/notifications", headers=headers)
    assert list_res.status_code == 200
    notifs = list_res.json()
    assert any(n["id"] == notif.id for n in notifs)

    # Mark as read
    read_res = client.patch(f"/notifications/{notif.id}/read", headers=headers)
    assert read_res.status_code == 200

    # Delete notification
    del_res = client.delete(f"/notifications/{notif.id}", headers=headers)
    assert del_res.status_code == 200

