from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
import os

# Local development needs an explicit temporary key. Deployments must inject a
# strong value through the environment instead of shipping a known JWT secret.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    if os.getenv("PLANNED_EDUCATION_ENV") == "development":
        SECRET_KEY = "local-development-only-secret-do-not-deploy"
    else:
        raise RuntimeError("JWT_SECRET_KEY must be configured outside local development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# We exclusively use Google SSO; no password hashing required.

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

