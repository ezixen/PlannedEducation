"""
Tests for Teacher's Aide nomination/approval, collaborative exam sharing,
Teacher Lounge messaging, and student DM policies.
"""
import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app
from src.plannededucation.api.routes_auth import get_password_hash


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


def _create_user(db, email, username, role="student", is_admin=False, teacher_approved=True):
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


def _get_token(client, email):
    res = client.post("/auth/token", data={"username": email, "password": "TestPassword123!"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_teacher_aide_nomination_and_approval(client, db_session):
    teacher = _create_user(db_session, "prof_smith@school.edu", "profsmith", role="teacher")
    student1 = _create_user(db_session, "aide_candidate1@school.edu", "aidecand1", role="student")
    student2 = _create_user(db_session, "aide_candidate2@school.edu", "aidecand2", role="student")

    t_token = _get_token(client, "prof_smith@school.edu")

    # 1. Direct nomination by identifier (email)
    nom_res = client.post(
        "/auth/teacher-aide/nominate",
        headers={"Authorization": f"Bearer {t_token}"},
        json={"identifier": "aide_candidate1@school.edu"},
    )
    assert nom_res.status_code == 200, nom_res.text
    assert nom_res.json()["is_teacher_aide"] is True

    # Verify student1 is aide
    db_session.refresh(student1)
    assert student1.is_teacher_aide is True
    assert student1.aide_approved_by == teacher.id

    # 2. Approval by user_id
    app_res = client.post(
        "/auth/teacher-aide/approve",
        headers={"Authorization": f"Bearer {t_token}"},
        json={"user_id": student2.id},
    )
    assert app_res.status_code == 200, app_res.text
    assert app_res.json()["is_teacher_aide"] is True

    # 3. List my aides
    list_res = client.get(
        "/auth/teacher-aide/my-aides",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert list_res.status_code == 200
    aides_ids = [a["id"] for a in list_res.json()]
    assert student1.id in aides_ids
    assert student2.id in aides_ids


def test_student_dm_policy_disabled_by_default(client, db_session):
    teacher = _create_user(db_session, "prof_jones@school.edu", "profjones", role="teacher")
    student = _create_user(db_session, "timmy@school.edu", "timmy", role="student")
    other_student = _create_user(db_session, "sally@school.edu", "sally", role="student")

    t_token = _get_token(client, "prof_jones@school.edu")
    s_token = _get_token(client, "timmy@school.edu")

    # 1. Student attempts to message another student -> 403 Forbidden
    res_s2s = client.post(
        "/chat/messages/direct",
        headers={"Authorization": f"Bearer {s_token}"},
        json={"recipient_id": other_student.id, "content": "Hey Sally"},
    )
    assert res_s2s.status_code == 403
    assert "not enabled" in res_s2s.json()["detail"].lower()

    # 2. Student attempts to message teacher when disabled -> 403 Forbidden
    res_s2t = client.post(
        "/chat/messages/direct",
        headers={"Authorization": f"Bearer {s_token}"},
        json={"recipient_id": teacher.id, "content": "Question about exam"},
    )
    assert res_s2t.status_code == 403
    assert "disabled by default" in res_s2t.json()["detail"].lower()

    # 3. Teacher enables student DMs
    toggle_res = client.patch(
        "/auth/teacher/settings/student-dms",
        headers={"Authorization": f"Bearer {t_token}"},
        json={"allow_student_dms": True},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["allow_student_dms"] is True

    # 4. Student can now message teacher successfully
    res_s2t_allowed = client.post(
        "/chat/messages/direct",
        headers={"Authorization": f"Bearer {s_token}"},
        json={"recipient_id": teacher.id, "content": "Question about exam"},
    )
    assert res_s2t_allowed.status_code == 200
    assert res_s2t_allowed.json()["content"] == "Question about exam"

    # 5. Teacher can reply to student
    res_t2s = client.post(
        "/chat/messages/direct",
        headers={"Authorization": f"Bearer {t_token}"},
        json={"recipient_id": student.id, "content": "Here is the answer."},
    )
    assert res_t2s.status_code == 200
    assert res_t2s.json()["content"] == "Here is the answer."


def test_teachers_lounge_directory(client, db_session):
    _create_user(db_session, "lounge_teacher@school.edu", "loungeteacher", role="teacher")
    _create_user(db_session, "lounge_admin@school.edu", "loungeadmin", role="admin", is_admin=True)

    t_token = _get_token(client, "lounge_teacher@school.edu")

    res = client.get(
        "/chat/teachers-lounge/directory",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "teachers" in data
    assert "admins" in data
    assert "admin_support_email" in data
