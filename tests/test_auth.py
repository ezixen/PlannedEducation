from fastapi.testclient import TestClient
from src.plannededucation.api.main import app

client = TestClient(app)

def test_signup_and_login():
    # 1. Signup
    signup_data = {
        "email": "teacher@plannededucation.org",
        "password": "securepassword",
        "full_name": "Test Teacher",
        "role": "teacher"
    }
    response = client.post("/auth/signup", json=signup_data)
    
    # It might already exist if tests run multiple times on sqlite, so handle 200 or 400
    assert response.status_code in [200, 400]

    # 2. Login
    login_data = {
        "username": "teacher@plannededucation.org",
        "password": "securepassword"
    }
    response = client.post("/auth/token", data=login_data)
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert token is not None

    # 3. Get /me
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "teacher@plannededucation.org"

