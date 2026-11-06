"""Regression tests for F-006 (WebAuthn login) and F-049 (RefreshSession)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from src.plannededucation.api import auth, database, models
from src.plannededucation.api.main import app
from src.plannededucation.api.schema_ensure import ensure_schema

client = TestClient(app)


def _register_and_login(email: str, username: str, password: str = "SecurePass1!") -> dict:
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "role": "student",
        },
    )
    assert registration.status_code == 201, registration.text
    token_response = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert token_response.status_code == 200, token_response.text
    return token_response.json()


def test_schema_includes_refresh_sessions_migration():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    ensure_schema(engine, models.Base.metadata)

    with engine.connect() as connection:
        versions = [
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
    assert versions == [1, 2, 3, 4, 5, 6]
    assert "refresh_sessions" in inspect(engine).get_table_names()
    exam_columns = {column["name"] for column in inspect(engine).get_columns("exams")}
    assert "home_exam_enabled" in exam_columns
    columns = {column["name"] for column in inspect(engine).get_columns("refresh_sessions")}
    assert {
        "id",
        "user_id",
        "token_hash",
        "family_id",
        "device_label",
        "created_at",
        "expires_at",
        "revoked_at",
        "replaced_by",
    }.issubset(columns)


def test_webauthn_login_start_without_auth_returns_400_without_passkeys():
    email = "webauthn_login_f006@example.com"
    username = "webauthn_login_f006"
    _register_and_login(email, username)

    # No bearer — unauthenticated start must not require prior login.
    response = client.post(
        "/auth/webauthn/login/start",
        json={"email": email},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Passkey authentication unavailable"

    # Unknown account uses the same generic shape (anti-enumeration).
    unknown = client.post(
        "/auth/webauthn/login/start",
        json={"email": "nobody_f006@example.com"},
    )
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "Passkey authentication unavailable"


def test_webauthn_login_start_returns_options_when_passkeys_present():
    email = "webauthn_opts_f006@example.com"
    username = "webauthn_opts_f006"
    _register_and_login(email, username)

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        # Minimal stored credential shape used by start (finish not exercised here).
        user.webauthn_credentials = (
            '[{"credential_id": "YWJjZGVmZ2hpams", "public_key": "AQID", '
            '"sign_count": 0, "created_at": "2026-01-01T00:00:00+00:00"}]'
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/auth/webauthn/login/start",
        json={"email": email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "challenge" in body
    assert body["rpId"]
    assert body["allowCredentials"]

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        assert user.webauthn_challenge
        assert user.webauthn_challenge_expires is not None
    finally:
        db.close()


def test_refresh_rotation_logout_and_password_change_revoke_sessions():
    email = "refresh_f049@example.com"
    username = "refresh_f049"
    password = "SecurePass1!"
    tokens = _register_and_login(email, username, password)
    refresh1 = tokens["refresh_token"]
    access = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access}"}

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        sessions = (
            db.query(models.RefreshSession)
            .filter(models.RefreshSession.user_id == user.id)
            .all()
        )
        assert len(sessions) == 1
        assert sessions[0].revoked_at is None
        family_id = sessions[0].family_id
    finally:
        db.close()

    rotated = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert rotated.status_code == 200, rotated.text
    refresh2 = rotated.json()["refresh_token"]
    assert refresh2 != refresh1

    # Old token reuse must fail and revoke the family.
    reuse = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert reuse.status_code == 401

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        family_rows = (
            db.query(models.RefreshSession)
            .filter(models.RefreshSession.family_id == family_id)
            .all()
        )
        assert family_rows
        assert all(row.revoked_at is not None for row in family_rows)
    finally:
        db.close()

    # Fresh login for logout + password-change coverage.
    again = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert again.status_code == 200
    access2 = again.json()["access_token"]
    refresh_a = again.json()["refresh_token"]
    headers2 = {"Authorization": f"Bearer {access2}"}

    logout = client.post(
        "/auth/logout",
        headers=headers2,
        json={"refresh_token": refresh_a},
    )
    assert logout.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": refresh_a}).status_code == 401

    # Login again, then password change must revoke all sessions.
    third = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert third.status_code == 200
    access3 = third.json()["access_token"]
    refresh_b = third.json()["refresh_token"]
    # Second concurrent device session.
    fourth = client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    assert fourth.status_code == 200
    refresh_c = fourth.json()["refresh_token"]

    change = client.put(
        "/auth/settings",
        headers={"Authorization": f"Bearer {access3}"},
        json={
            "current_password": password,
            "password": "SecurePass2!",
        },
    )
    assert change.status_code == 200, change.text

    assert client.post("/auth/refresh", json={"refresh_token": refresh_b}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": refresh_c}).status_code == 401

    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        active = (
            db.query(models.RefreshSession)
            .filter(
                models.RefreshSession.user_id == user.id,
                models.RefreshSession.revoked_at.is_(None),
            )
            .count()
        )
        assert active == 0
        assert user.refresh_token_hash is None
    finally:
        db.close()


def test_issue_refresh_session_clears_legacy_hash():
    db = database.SessionLocal()
    try:
        user = models.User(
            email="legacy_refresh_f049@example.com",
            username="legacy_refresh_f049",
            hashed_password="unused",
            refresh_token_hash="legacy",
            refresh_token_expires=datetime.now(UTC) + timedelta(days=1),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        tokens, session = auth.issue_refresh_session(db, user)
        db.commit()
        assert tokens["refresh_token"]
        assert session.token_hash
        assert user.refresh_token_hash is None
        assert user.refresh_token_expires is None
    finally:
        db.close()
