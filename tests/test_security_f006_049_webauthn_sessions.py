"""F-006 WebAuthn login start + F-049 refresh session revoke regressions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.plannededucation.api.main import app

client = TestClient(app)


def _register(email: str, password: str = "SecurePassw0rd!") -> None:
    res = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": email.split("@")[0],
            "password": password,
            "full_name": "Test User",
            "role": "student",
        },
    )
    assert res.status_code in (200, 201), res.text


def test_f006_webauthn_login_start_without_auth_is_generic():
    email = "f006_webauthn_missing@example.com"
    _register(email)
    res = client.post("/auth/webauthn/login/start", json={"email": email})
    # No passkeys registered → generic unavailable (no bearer required).
    assert res.status_code == 400
    assert "unavailable" in res.text.lower()


def test_f006_webauthn_login_start_unknown_email_same_shape():
    res = client.post(
        "/auth/webauthn/login/start",
        json={"email": "does-not-exist-f006@example.com"},
    )
    assert res.status_code == 400
    assert "unavailable" in res.text.lower()


def test_f049_password_change_revokes_refresh_session():
    email = "f049_sessions@example.com"
    password = "SecurePassw0rd!"
    _register(email, password)
    login = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    change = client.put(
        "/auth/settings",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"password": "NewSecurePass1!", "current_password": password},
    )
    assert change.status_code == 200, change.text
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
