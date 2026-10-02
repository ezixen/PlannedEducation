import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT for JWT encoding/decoding

# ── JWT Configuration ────────────────────────────────────────────────────────
# A strong secret MUST be injected via the environment in every environment.
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

# ── Password & 2FA Configuration ─────────────────────────────────────────────
# Password is stored but ONLY used for self-service reset.
# Login is Google SSO only. Password reset is email-OTP or recovery-code based.
PASSWORD_MIN_LEN = 8
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$") if True else None

# 2FA settings
TOTP_ISSUER = "PlannedEducation"
RECOVERY_CODE_COUNT = 5  # Number of one-time recovery codes to generate
RECOVERY_CODE_LENGTH = 8  # Length of each recovery code in characters


def hash_password(password: str) -> str:
    """Hash a password for storage (SHA-256, kept for reset flow only)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash. Used only for self-service reset flow."""
    return hash_password(plain) == hashed


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT, length: int = RECOVERY_CODE_LENGTH) -> list[str]:
    """Generate a list of one-time recovery codes for 2FA / password reset fallback."""
    codes: list[str] = []
    for _ in range(count):
        code = secrets.token_hex(length // 2)[:length]
        codes.append(code)
    return codes


# ── Token Configuration ──────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

# ── Token Creation ───────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    to_encode["type"] = "access"
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode["exp"] = expire
    to_encode["type"] = "refresh"
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(data: dict) -> dict:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type": "bearer",
    }


def verify_refresh_token(token: str) -> dict | None:
    """Verify a refresh token and return its payload if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
