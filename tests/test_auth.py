"""
test_auth.py — registration, login, /auth/me, settings, password policy.
"""
import pytest
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app

client = TestClient(app)

# ── Registration ─────────────────────────────────────────────────────────────

def test_register_success():
    r = client.post("/auth/register", json={
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "Secure1234!",
        "full_name": "New User",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "newuser@test.com"
    assert data["username"] == "newuser"
    # Sensitive fields must NEVER appear in the response
    assert "hashed_password" not in data
    assert "ai_api_key_encrypted" not in data
    assert "totp_secret" not in data


def test_register_duplicate_email():
    payload = {"email": "dupe@test.com", "username": "dupe1", "password": "Secure1234!"}
    client.post("/auth/register", json=payload)
    r = client.post("/auth/register", json={**payload, "username": "dupe2"})
    assert r.status_code == 400
    assert "Email already registered" in r.json()["detail"]


def test_register_duplicate_username():
    client.post("/auth/register", json={"email": "u1@test.com", "username": "dupeuser", "password": "Secure1234!"})
    r = client.post("/auth/register", json={"email": "u2@test.com", "username": "dupeuser", "password": "Secure1234!"})
    assert r.status_code == 400
    assert "Username already taken" in r.json()["detail"]


# ── Password policy ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("pwd,reason", [
    ("short1A",  "too short"),
    ("alllowercase1", "no uppercase"),
    ("ALLUPPERCASE1", "no lowercase"),
    ("NoDigitsHere!", "no digit"),
    ("abc",           "too short + no complexity"),
])
def test_register_weak_password_rejected(pwd, reason):
    r = client.post("/auth/register", json={
        "email": f"weak_{pwd[:4]}@test.com",
        "username": f"weak_{pwd[:4]}",
        "password": pwd,
    })
    assert r.status_code == 422, f"Expected 422 for '{reason}' but got {r.status_code}"


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_with_email():
    client.post("/auth/register", json={
        "email": "login_email@test.com", "username": "login_email",
        "password": "Login1234!", "full_name": "Login Email",
    })
    r = client.post("/auth/token", data={"username": "login_email@test.com", "password": "Login1234!"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"


def test_login_with_username():
    client.post("/auth/register", json={
        "email": "login_uname@test.com", "username": "login_uname",
        "password": "Login1234!",
    })
    r = client.post("/auth/token", data={"username": "login_uname", "password": "Login1234!"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password():
    client.post("/auth/register", json={
        "email": "wrongpwd@test.com", "username": "wrongpwd", "password": "Correct1!",
    })
    r = client.post("/auth/token", data={"username": "wrongpwd@test.com", "password": "WrongPass1!"})
    assert r.status_code == 401


def test_login_nonexistent_user():
    r = client.post("/auth/token", data={"username": "ghost@ghost.com", "password": "Ghost1234!"})
    assert r.status_code == 401


# ── /auth/me ─────────────────────────────────────────────────────────────────

def test_auth_me_returns_user():
    client.post("/auth/register", json={
        "email": "me@test.com", "username": "meuser", "password": "MeUser1!",
    })
    token = client.post("/auth/token", data={"username": "me@test.com", "password": "MeUser1!"}).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me@test.com"
    assert "hashed_password" not in data


def test_auth_me_unauthenticated():
    r = client.get("/auth/me")
    assert r.status_code == 401


# ── Settings ──────────────────────────────────────────────────────────────────

def test_update_settings():
    client.post("/auth/register", json={
        "email": "settings@test.com", "username": "settingsuser", "password": "Settings1!",
    })
    token = client.post("/auth/token", data={"username": "settings@test.com", "password": "Settings1!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.put("/auth/settings", json={"full_name": "Updated Name"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["full_name"] == "Updated Name"


def test_change_password_and_login_again():
    client.post("/auth/register", json={
        "email": "chpwd@test.com", "username": "chpwduser", "password": "OldPass1!",
    })
    token = client.post("/auth/token", data={"username": "chpwd@test.com", "password": "OldPass1!"}).json()["access_token"]
    client.put("/auth/settings", json={"password": "NewPass1!"}, headers={"Authorization": f"Bearer {token}"})

    # Old password no longer works
    r = client.post("/auth/token", data={"username": "chpwd@test.com", "password": "OldPass1!"})
    assert r.status_code == 401

    # New password works
    r = client.post("/auth/token", data={"username": "chpwd@test.com", "password": "NewPass1!"})
    assert r.status_code == 200
