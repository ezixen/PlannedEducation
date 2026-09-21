from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
import os
import secrets

# ── JWT Configuration ────────────────────────────────────────────────────────
# A strong secret MUST be injected via the environment in every environment.
# The development fallback uses os.urandom so the secret is never a known string,
# but tokens will be invalidated on every process restart (intentional: dev only).
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")

if not SECRET_KEY:
    env = os.getenv("PLANNED_EDUCATION_ENV", "production")
    if env == "development":
        # Per-process ephemeral key: tokens don't survive restarts, which is fine in dev.
        SECRET_KEY = secrets.token_hex(64)
        import warnings
        warnings.warn(
            "JWT_SECRET_KEY not set — using a random ephemeral key. "
            "All tokens will be invalidated on restart. Set JWT_SECRET_KEY in .env.",
            RuntimeWarning,
            stacklevel=1,
        )
    else:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set as an environment variable in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\""
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Reduced from 120 to 60 min for tighter security


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
