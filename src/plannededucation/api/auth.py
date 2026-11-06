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
RECOVERY_CODE_LENGTH = 32  # 128 bits rendered as 32 hexadecimal characters

_RECOVERY_CODE_HASH_SECRET = os.getenv("RECOVERY_CODE_HASH_SECRET", "")
_AUTH_ENVIRONMENT = os.getenv("PLANNED_EDUCATION_ENV", "production").lower()
if _AUTH_ENVIRONMENT in {"production", "staging"}:
    if not _RECOVERY_CODE_HASH_SECRET:
        raise RuntimeError(
            "RECOVERY_CODE_HASH_SECRET must be set in production/staging."
        )
    if _RECOVERY_CODE_HASH_SECRET == SECRET_KEY:
        raise RuntimeError(
            "RECOVERY_CODE_HASH_SECRET must differ from JWT_SECRET_KEY."
        )
    if not os.getenv("TOKEN_HASH_SECRET"):
        raise RuntimeError("TOKEN_HASH_SECRET must be set in production/staging.")
    if os.getenv("TOKEN_HASH_SECRET") in {SECRET_KEY, _RECOVERY_CODE_HASH_SECRET}:
        raise RuntimeError(
            "TOKEN_HASH_SECRET must differ from JWT and recovery-code secrets."
        )


def _normalize_recovery_code(code: str) -> str:
    """Normalize the human-entered representation before verification."""
    return re.sub(r"[-\s]", "", code).upper()


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code with a dedicated server-side HMAC secret.

    Recovery codes are high-entropy, one-time values. A keyed digest prevents
    offline verification by a database reader while remaining inexpensive
    enough for bounded recovery attempts. Legacy SHA-256 values remain
    verifiable through ``verify_recovery_code`` during migration.
    """
    secret = _RECOVERY_CODE_HASH_SECRET
    if not secret:
        # Tests/development must not require another local credential. The
        # derived value is process-local when development uses an ephemeral JWT
        # key and is never accepted as a production configuration.
        secret = f"{SECRET_KEY}|recovery-code"
    digest = hmac.new(
        secret.encode("utf-8"),
        _normalize_recovery_code(code).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac-sha256${digest}"


def verify_recovery_code(code: str, stored_hash: str) -> bool:
    """Verify a recovery code against current or legacy storage formats."""
    normalized = _normalize_recovery_code(code)
    if stored_hash.startswith("hmac-sha256$"):
        expected = hash_recovery_code(normalized)
        return hmac.compare_digest(stored_hash, expected)

    # Legacy deployments stored unsalted SHA-256 digests. Accept them only
    # during the controlled migration; callers consume a matching code.
    legacy_candidates = (
        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        hashlib.sha256(code.encode("utf-8")).hexdigest(),
    )
    return any(
        hmac.compare_digest(stored_hash, candidate)
        for candidate in legacy_candidates
    )


def generate_recovery_codes(
    count: int = RECOVERY_CODE_COUNT, length: int = RECOVERY_CODE_LENGTH
) -> list[str]:
    """Generate a list of one-time recovery codes for 2FA / password reset fallback."""
    if length < 32:
        raise ValueError("Recovery codes must contain at least 128 bits of entropy")
    return [secrets.token_hex(length // 2)[:length].upper() for _ in range(count)]


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


def hash_refresh_token(raw_token: str) -> str:
    """Persist only a digest of a refresh bearer token."""
    return _preferred_secret_hash(raw_token)


def _as_utc_ts(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def clear_legacy_refresh_fields(user) -> None:
    """Clear the single-slot legacy refresh columns once RefreshSession is authoritative."""
    user.refresh_token_hash = None
    user.refresh_token_expires = None


def issue_refresh_session(
    db,
    user,
    *,
    remember_me: bool = False,
    device_label: str | None = None,
    family_id: str | None = None,
) -> tuple[dict, object]:
    """Issue access+refresh tokens and insert a RefreshSession row.

    Prefer the per-device table; legacy user.refresh_token_* columns are cleared.
    Returns ``(token_pair, refresh_session_row)``.
    """
    from . import models  # local import avoids cycles with routes_auth

    tokens = create_token_pair({"sub": user.email}, remember_me=remember_me)
    expire_days = (
        REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS if remember_me else REFRESH_TOKEN_EXPIRE_DAYS
    )
    session = models.RefreshSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_refresh_token(tokens["refresh_token"]),
        family_id=family_id or str(uuid.uuid4()),
        device_label=device_label,
        expires_at=datetime.now(UTC) + timedelta(days=expire_days),
    )
    db.add(session)
    clear_legacy_refresh_fields(user)
    return tokens, session


def revoke_all_refresh_sessions(db, user_id: str) -> int:
    """Revoke every active refresh session for a user. Returns count revoked."""
    from . import models

    now = datetime.now(UTC)
    rows = (
        db.query(models.RefreshSession)
        .filter(
            models.RefreshSession.user_id == user_id,
            models.RefreshSession.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
    return len(rows)


def revoke_refresh_family(db, family_id: str) -> int:
    """Revoke an entire refresh-token family (reuse / theft response)."""
    from . import models

    now = datetime.now(UTC)
    rows = (
        db.query(models.RefreshSession)
        .filter(
            models.RefreshSession.family_id == family_id,
            models.RefreshSession.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
    return len(rows)


def revoke_refresh_session_by_token(db, raw_token: str) -> bool:
    """Revoke the session matching a raw refresh token, if any."""
    from . import models

    candidates = secret_hash_candidates(raw_token)
    row = (
        db.query(models.RefreshSession)
        .filter(models.RefreshSession.token_hash.in_(candidates))
        .first()
    )
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.now(UTC)
    return True


def _find_refresh_session(db, raw_token: str):
    from . import models

    candidates = secret_hash_candidates(raw_token)
    return (
        db.query(models.RefreshSession)
        .filter(models.RefreshSession.token_hash.in_(candidates))
        .first()
    )


def rotate_refresh_session(db, raw_token: str) -> dict | None:
    """Rotate a refresh token within its family.

    Reuse of an already-revoked token revokes the whole family and returns None.
    Legacy single-hash rows are migrated into RefreshSession on first successful rotate.
    """
    from . import models

    payload = verify_refresh_token(raw_token)
    if not payload:
        return None

    email = payload.get("sub")
    remember_me = bool(payload.get("remember_me", False))
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        return None

    now = datetime.now(UTC)
    session = _find_refresh_session(db, raw_token)

    if session is not None:
        if session.revoked_at is not None:
            revoke_refresh_family(db, session.family_id)
            clear_legacy_refresh_fields(user)
            return None
        expires = _as_utc_ts(session.expires_at)
        if expires is not None and expires < now:
            session.revoked_at = now
            return None
        if session.user_id != user.id:
            return None

        session.revoked_at = now
        tokens, replacement = issue_refresh_session(
            db,
            user,
            remember_me=remember_me,
            device_label=session.device_label,
            family_id=session.family_id,
        )
        session.replaced_by = replacement.id
        return tokens

    # Legacy single-slot fallback (one-time migrate into RefreshSession).
    provided = hashlib.sha256(raw_token.encode()).hexdigest()
    legacy_hash = user.refresh_token_hash
    legacy_expires = _as_utc_ts(user.refresh_token_expires)
    if not legacy_hash or not legacy_expires:
        return None
    if not hmac.compare_digest(legacy_hash, provided) and not any(
        hmac.compare_digest(legacy_hash, candidate)
        for candidate in secret_hash_candidates(raw_token)
    ):
        return None
    if legacy_expires < now:
        clear_legacy_refresh_fields(user)
        return None

    clear_legacy_refresh_fields(user)
    tokens, _ = issue_refresh_session(db, user, remember_me=remember_me)
    return tokens


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


def hash_reset_token(raw_token: str) -> str:
    """Store only a keyed digest of a password-reset bearer token."""
    return _preferred_secret_hash(raw_token)


def verify_reset_token(raw_token: str, stored_value: str | None) -> bool:
    """Verify a current or legacy password-reset token in constant time."""
    if not stored_value:
        return False
    digest_match = any(
        hmac.compare_digest(stored_value, candidate)
        for candidate in secret_hash_candidates(raw_token)
    )
    if digest_match:
        return True
    # Only pre-envelope rows may use direct comparison. A digest-shaped value
    # must never be accepted as its own bearer token.
    if stored_value.startswith("hmac-sha256$") or re.fullmatch(r"[0-9a-f]{64}", stored_value):
        return False
    return hmac.compare_digest(stored_value, raw_token)


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
    token_ttl_hours = 365 * 24 if remember_me else (7 * 24 if is_admin else 30 * 24)
    expires_in = int(token_ttl_hours * 3600)
    return raw_token, expires_in
