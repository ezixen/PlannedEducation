"""
test_auth_flows.py - refresh-token rotation, 2FA recovery codes, password reset.
Regression tests for flows that previously failed at runtime.
"""
import pyotp
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app

client = TestClient(app)
PASSWORD = "Secure1234!"


def _register_and_login(email: str, username: str) -> dict:
    r = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": PASSWORD},
    )
    assert r.status_code == 201
    r = client.post("/auth/token", data={"username": email, "password": PASSWORD})
    assert r.status_code == 200
    return r.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_refresh_works_after_password_login():
    tokens = _register_and_login("refresh@test.com", "refreshuser")
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]
    # Old refresh token is rotated out and must no longer be accepted
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


def test_2fa_setup_confirm_and_disable_with_recovery_code():
    tokens = _register_and_login("twofa@test.com", "twofauser")
    headers = _auth(tokens)

    r = client.post("/auth/2fa/setup", headers=headers)
    assert r.status_code == 200
    setup = r.json()
    assert setup["recovery_codes"]

    code = pyotp.TOTP(setup["secret"]).now()
    r = client.post("/auth/2fa/confirm", headers=headers, json={"code": code})
    assert r.status_code == 200

    # Recovery codes are stored hashed, never in plaintext
    db = next(database.get_db())
    try:
        user = db.query(models.User).filter(models.User.email == "twofa@test.com").first()
        assert setup["recovery_codes"][0] not in user.recovery_codes
    finally:
        db.close()

    recovery = setup["recovery_codes"][0]
    r = client.post("/auth/2fa/disable", headers=headers, json={"recovery_code": recovery})
    assert r.status_code == 200, r.text


def test_recovery_code_is_single_use_for_password_reset():
    tokens = _register_and_login("reset@test.com", "resetuser")
    headers = _auth(tokens)
    setup = client.post("/auth/2fa/setup", headers=headers).json()
    recovery = setup["recovery_codes"][0]

    body = {"email": "reset@test.com", "recovery_code": recovery, "new_password": "Changed1234!"}
    r = client.post("/auth/password-reset/confirm", json=body)
    assert r.status_code == 200, r.text
    r = client.post("/auth/password-reset/confirm", json=body)
    assert r.status_code == 400
