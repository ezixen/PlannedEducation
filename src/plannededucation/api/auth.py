import base64
import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt  # PyJWT for JWT encoding/decoding
from cryptography.fernet import Fernet

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


def generate_recovery_codes(
    count: int = RECOVERY_CODE_COUNT, length: int = RECOVERY_CODE_LENGTH
) -> list[str]:
    """Generate a list of one-time recovery codes for 2FA / password reset fallback."""
    codes: list[str] = []
    for _ in range(count):
        code = secrets.token_hex(length // 2)[:length]
        codes.append(code)
    return codes


# ── Token Configuration ──────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS = 365  # 1 year for "remember me"

# ── Token Creation ───────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode.setdefault("jti", uuid.uuid4().hex)
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    to_encode["type"] = "access"
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None, remember_me: bool = False) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()
    to_encode.setdefault("jti", uuid.uuid4().hex)
    if remember_me:
        expire = datetime.now(UTC) + (
            expires_delta if expires_delta else timedelta(days=REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS)
        )
    else:
        expire = datetime.now(UTC) + (
            expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
    to_encode["exp"] = expire
    to_encode["type"] = "refresh"
    to_encode["remember_me"] = remember_me
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(data: dict, remember_me: bool = False) -> dict:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data, remember_me=remember_me),
        "token_type": "bearer",
    }


def verify_refresh_token(token: str) -> dict | None:
    """Verify a refresh token and return its payload if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.exceptions.InvalidTokenError:
        return None


# ── Session Token Management (Device Tracking & Remember Me) ─────────────────
# Based on easylegalaid patterns for device tracking and encrypted sessions

_HASH_VERSION_HMAC_SHA256 = "hmac-sha256"
_USER_SESSION_TTL_HOURS = 30 * 24  # 30 days for regular users
_ADMIN_SESSION_TTL_HOURS = 7 * 24  # 7 days for admins
_REMEMBER_ME_TTL_HOURS = 365 * 24  # 1 year for "remember me"

def _token_hash_secret() -> bytes | None:
    """Get the secret for HMAC token hashing from environment."""
    secret = os.getenv("TOKEN_HASH_SECRET")
    if not secret:
        return None
    return secret.encode("utf-8")


def _legacy_sha256(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def _preferred_secret_hash(raw_value: str) -> str:
    secret = _token_hash_secret()
    if secret is None:
        return _legacy_sha256(raw_value)
    digest = hmac.new(secret, raw_value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{_HASH_VERSION_HMAC_SHA256}${digest}"


def secret_hash_candidates(raw_value: str) -> tuple[str, ...]:
    preferred = _preferred_secret_hash(raw_value)
    legacy = _legacy_sha256(raw_value)
    if preferred == legacy:
        return (legacy,)
    return (preferred, legacy)


def _hash_token(raw_token: str) -> str:
    return _preferred_secret_hash(raw_token)


def _fernet_for_tokens() -> Fernet | None:
    secret = _token_hash_secret()
    if not secret:
        return None
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_session_token(raw_token: str) -> str:
    fernet = _fernet_for_tokens()
    if fernet is None:
        return raw_token
    return fernet.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def _decrypt_session_token(payload: str | None) -> str | None:
    if not payload:
        return None
    fernet = _fernet_for_tokens()
    if fernet is None:
        return payload
    try:
        return fernet.decrypt(payload.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def _hash_device_id(device_id: str | None) -> str | None:
    if not device_id:
        return None
    normalized = device_id.strip()
    if not normalized:
        return None
    return _preferred_secret_hash(f"device:{normalized}")


def session_ttl_hours_for_user(user_role: str, is_admin: bool) -> int:
    """Absolute server session lifetime: 7 days for admins, 30 days for users."""
    if is_admin:
        return 7 * 24
    return 30 * 24


def create_session_token(
    user_id: str,
    user_role: str,
    is_admin: bool,
    device_id: str | None = None,
    remember_me: bool = False,
) -> tuple[str, int]:
    """
    Create a session token with device tracking.
    Returns (raw_token, expires_in_seconds).
    """
    raw_token = secrets.token_urlsafe(36)
    now = datetime.now(UTC)
    
    if remember_me:
        token_ttl_hours = 365 * 24  # 1 year for "remember me"
    else:
        token_ttl_hours = 7 * 24 if is_admin else 30 * 24
    
    expires_at = datetime.now(UTC) + timedelta(hours=token_ttl_hours)
    preferred_hash = _preferred_secret_hash(raw_token)
    device_id_hash = _hash_device_id(device_id)
    
    # The actual session storage is handled by the caller (routes_auth.py)
    # This function just generates the token and returns it with expiry
    expires_in = int(token_ttl_hours * 3600)
    return raw_token, expires_in


def _hash_device_id(device_id: str | None) -> str | None:
    if not device_id:
        return None
    normalized = device_id.strip()
    if not normalized:
        return None
    return _preferred_secret_hash(f"device:{normalized}")
