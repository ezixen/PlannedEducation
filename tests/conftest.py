"""
conftest.py - shared fixtures for the test suite.
Uses an in-memory SQLite database so tests are fully isolated from the live Postgres DB.
"""
import os
import pytest

# Must be set BEFORE any application modules are imported
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_plannededucation.db")
os.environ.setdefault("PLANNED_EDUCATION_ENV", "test")
os.environ.setdefault("ALLOW_DEV_SEB_BYPASS", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_1234567890")

from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from src.plannededucation.api.routes_auth import get_password_hash


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables once per session, then drop them on teardown."""
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    yield
    models.Base.metadata.drop_all(bind=database.engine)
    if os.path.exists("./test_plannededucation.db"):
        try:
            os.remove("./test_plannededucation.db")
        except OSError:
            pass


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def db():
    session = next(database.get_db())
    yield session
    session.close()


def make_user(db, email: str, username: str, full_name: str = "Test User") -> models.User:
    """Helper: create a user with a hashed password or return existing."""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=get_password_hash("Test1234!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def make_token(user: models.User) -> str:
    """Helper: mint a valid JWT for the given user."""
    return auth.create_access_token(data={"sub": user.email})


def auth_headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {make_token(user)}"}
