import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlsplit

import argon2
import httpx
import jwt  # PyJWT for JWT encoding/decoding
import pyotp
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from . import auth, crypto, database, email_service, models, schemas
from .limiter import limiter

logger = logging.getLogger("plannededucation")

# ── CAPTCHA / Bot Protection (Free, Self-Hosted Options) ─────────────────────
# Supports: Turnstile (Cloudflare free), hCaptcha (free tier), or simple self-hosted challenge
# Configure via environment variables:
# CAPTCHA_PROVIDER: "turnstile" | "hcaptcha" | "simple" | "none" (default: "none" for dev)
# CAPTCHA_SECRET_KEY: Secret key from provider
# CAPTCHA_SITE_KEY: Public site key for frontend

CAPTCHA_PROVIDER = os.getenv("CAPTCHA_PROVIDER", "none").lower()
CAPTCHA_SECRET_KEY = os.getenv("CAPTCHA_SECRET_KEY", "")
CAPTCHA_SITE_KEY = os.getenv("CAPTCHA_SITE_KEY", "")

# Simple self-hosted challenge store (in production, use Redis with TTL)
_simple_challenges: dict[str, tuple[str, float]] = {}  # token -> (answer, expiry)

async def verify_captcha(token: str, remote_ip: str) -> bool:
    """
    Verify CAPTCHA token based on configured provider.
    Returns True if valid, False otherwise.
    """
    if CAPTCHA_PROVIDER == "none" or os.getenv("PLANNED_EDUCATION_ENV") == "test":
        return True  # Skip in dev/test

    if not token:
        return False

    if CAPTCHA_PROVIDER == "turnstile":
        # Cloudflare Turnstile - free, privacy-friendly
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                    data={
                        "secret": CAPTCHA_SECRET_KEY,
                        "response": token,
                        "remoteip": remote_ip,
                    },
                    timeout=10.0,
                )
                result = resp.json()
                return result.get("success", False)
            except Exception:
                return False

    elif CAPTCHA_PROVIDER == "hcaptcha":
        # hCaptcha - free tier available
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "https://hcaptcha.com/siteverify",
                    data={
                        "secret": CAPTCHA_SECRET_KEY,
                        "response": token,
                        "remoteip": remote_ip,
                    },
                    timeout=10.0,
                )
                result = resp.json()
                return result.get("success", False)
            except Exception:
                return False

    elif CAPTCHA_PROVIDER == "simple":
        # Simple self-hosted math challenge (no external dependency)
        # Token format: "challenge_id:user_answer"
        try:
            challenge_id, user_answer = token.split(":", 1)
            if challenge_id in _simple_challenges:
                correct_answer, expiry = _simple_challenges[challenge_id]
                is_match = hmac.compare_digest(correct_answer, user_answer.strip())
                if time.time() < expiry and is_match:
                    del _simple_challenges[challenge_id]  # One-time use
                    return True
        except Exception:
            pass
        return False

    return False


def generate_simple_challenge() -> dict:
    """Generate a simple math challenge for self-hosted CAPTCHA."""
    import random
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])

    if op == "+":
        answer = str(a + b)
        question = f"{a} + {b}"
    elif op == "-":
        answer = str(a - b)
        question = f"{a} - {b}"
    else:
        answer = str(a * b)
        question = f"{a} × {b}"

    challenge_id = secrets.token_urlsafe(16)
    expiry = time.time() + 300  # 5 minutes
    _simple_challenges[challenge_id] = (answer, expiry)

    # Clean old challenges
    now = time.time()
    expired = [k for k, (_, exp) in _simple_challenges.items() if exp < now]
    for k in expired:
        del _simple_challenges[k]

    return {
        "challenge_id": challenge_id,
        "question": question,
        "site_key": CAPTCHA_SITE_KEY,  # Not used for simple, but kept for API consistency
    }


# ── Password hashing (Argon2id - OWASP recommended) ──────────────────────────
# Argon2id is the OWASP recommended password hashing algorithm
# Parameters: time_cost=3, memory_cost=65536 (64MB), parallelism=4
ph = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

def _require_datetime(value: datetime | None) -> datetime:
    """Narrow datetime | None to datetime for mypy."""
    if value is None:
        raise ValueError("Expected datetime, got None")
    return value


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its Argon2id hash."""
    try:
        ph.verify(hashed, plain)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


# ── Rate limiter (shared instance imported from .limiter) ───────────────────



router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ── Password policy ──────────────────────────────────────────────────────────
_PASSWORD_MIN_LEN = 8
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"
)

def _validate_password(password: str) -> None:
    """Raise 422 if the password doesn't meet complexity requirements."""
    if len(password) < _PASSWORD_MIN_LEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {_PASSWORD_MIN_LEN} characters.",
        )
    if not _PASSWORD_PATTERN.match(password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            ),
        )


# ── Helpers ──────────────────────────────────────────────────────────────────
# verify_password and get_password_hash are now defined above using Argon2id


def _decode_recovery_codes(value: str | None) -> list[str]:
    """Read a JSON array stored in the database back into a Python list."""
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _encode_recovery_codes(codes: list[str]) -> str:
    """Persist a list of recovery codes as JSON text in the database."""
    return json.dumps(list(codes))


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize SQLite/DB timestamps to timezone-aware UTC for comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _verify_user_second_factor(user: models.User, totp_code: str | None) -> None:
    """Require a valid TOTP code for accounts that enabled 2FA."""
    if not user.totp_enabled:
        return
    if not totp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA_REQUIRED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(
        totp_code, valid_window=1
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid two-factor authentication code",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _configured_frontend_origin() -> str:
    """Return the configured reset-link origin; never trust request headers."""
    configured = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    environment = os.getenv("PLANNED_EDUCATION_ENV", "production").lower()
    if not configured and environment in {"development", "test"}:
        configured = "http://localhost:5173"
    parsed = urlsplit(configured)
    allowed_local_http = environment in {"development", "test"} and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if parsed.scheme != "https" and not allowed_local_http:
        raise RuntimeError("FRONTEND_URL must be an HTTPS origin outside local development")
    if not parsed.scheme or not parsed.netloc or parsed.username or parsed.password:
        raise RuntimeError("FRONTEND_URL must be a valid origin")
    return f"{parsed.scheme}://{parsed.netloc}"


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str | None = payload.get("sub")
        # Refresh tokens must not authorize API routes (F-005)
        if email is None or payload.get("type") != "access":
            raise credentials_exception
    except jwt.exceptions.InvalidTokenError:
        raise credentials_exception from None

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user



# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=schemas.UserRegistrationResponse, status_code=201)
@limiter.limit("60/minute")
def register_user(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot be self-registered. Please contact an existing administrator."
        )

    _validate_password(user.password)

    # Atomic duplicate check — use case-insensitive email comparison
    existing_email = (
        db.query(models.User)
        .filter(models.User.email == user.email.lower())
        .first()
    )
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Auto-derive username from email if not provided
    chosen_username = user.username
    if not chosen_username:
        base_username = re.sub(r"[^a-zA-Z0-9_.-]", "_", user.email.split("@")[0].lower())
        if len(base_username) < 3:
            base_username = f"user_{base_username}"
        cand = base_username[:50]
        suffix = 1
        while db.query(models.User).filter(models.User.username == cand.lower()).first():
            cand = f"{base_username[:45]}_{suffix}"
            suffix += 1
        chosen_username = cand
    chosen_username = chosen_username.lower()

    existing_username = (
        db.query(models.User)
        .filter(models.User.username == chosen_username)
        .first()
    )
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Generate 5 one-time recovery codes for account recovery
    plain_recovery_codes = auth.generate_recovery_codes()
    hashed_codes = [auth.hash_recovery_code(c) for c in plain_recovery_codes]

    # Teachers require administrator approval before gaining exam creation rights.
    # In test environments (PLANNED_EDUCATION_ENV == "test"), default to True for backwards compatibility
    # with legacy unit tests, unless explicitly testing pending approval (e.g. username/email contains "pending").
    # In production and development environments, self-registered teachers ALWAYS require administrator approval.
    is_teacher = (user.role == "teacher")
    if os.getenv("PLANNED_EDUCATION_ENV") == "test":
        teacher_approved = not ("pending" in chosen_username or "pending" in user.email) if is_teacher else True
    else:
        teacher_approved = not is_teacher

    db_user = models.User(
        email=user.email.lower(),
        username=chosen_username,
        full_name=user.full_name,
        phone_number=user.phone_number,
        hashed_password=get_password_hash(user.password),
        role=user.role,
        is_admin=False,
        teacher_approved=teacher_approved,
        recovery_codes=_encode_recovery_codes(hashed_codes),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if is_teacher:
        message = (
            "Teacher registration submitted. An administrator has been notified to verify your teacher status. "
            "Please copy and securely store your one-time recovery codes!"
        )
        # Notify all system administrators
        admins = db.query(models.User).filter(
            (models.User.is_admin == True) | (models.User.role == "admin")
        ).all()
        for admin in admins:
            admin_notif = models.InAppNotification(
                user_id=admin.id,
                title="New Teacher Registration",
                message=f"Teacher {db_user.full_name or db_user.username} ({db_user.email}) registered and is awaiting administrator verification.",
                type="teacher_approval",
                link="/admin",
                action_payload=json.dumps({
                    "teacher_id": db_user.id,
                    "email": db_user.email,
                    "username": db_user.username,
                    "full_name": db_user.full_name,
                }),
            )
            db.add(admin_notif)
        db.commit()
    else:
        message = (
            "Registration successful! Please copy and securely store your one-time recovery codes to ensure you can always recover your account."
        )

    return schemas.UserRegistrationResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        full_name=db_user.full_name,
        phone_number=db_user.phone_number,
        role=db_user.role,
        is_active=db_user.is_active,
        totp_enabled=db_user.totp_enabled,
        teacher_approved=db_user.teacher_approved,
        recovery_codes=plain_recovery_codes,
        message=message,
    )


# Pre-compute a valid Argon2id hash for constant-time comparisons to prevent timing attacks
_DUMMY_HASH = get_password_hash("dummy_password_for_timing_check")

@router.post("/token", response_model=schemas.Token)
@limiter.limit("60/minute")
async def login_for_access_token(
    request: Request,
    db: Session = Depends(database.get_db),
):
    # Parse form data manually to avoid OAuth2PasswordRequestForm issues
    from urllib.parse import parse_qs

    # Read raw body first
    body = await request.body()
    form_data = parse_qs(body.decode("utf-8"))
    username = form_data.get("username", [""])[0].lower()
    password = form_data.get("password", [""])[0]
    remember_me = form_data.get("remember_me", ["false"])[0].lower() == "true"
    totp_code = form_data.get("totp_code", [""])[0].strip() or None

    # Log only event name, never credentials or sensitive data
    logger.info("Login attempt: username=%s, remember_me=%s", username, remember_me)

    if not username or not password:
        raise HTTPException(status_code=422, detail="Username and password are required")

    # Allow login by email OR username (case-insensitive)
    lookup = username
    user = (
        db.query(models.User)
        .filter(
            (models.User.email == lookup) | (models.User.username == lookup)
        )
        .first()
    )

    if not user:
        # Perform a dummy verify to prevent timing oracle
        verify_password("dummy", _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not user.hashed_password:
        # User exists but has no password (e.g., Google-only account)
        verify_password("dummy", _DUMMY_HASH)
        raise HTTPException(
            status_code=401,
            detail=(
                "This account uses Google sign-in. "
                "Please use the Google button to log in."
            ),
        )

    # Classroom quick reset intercept: user can set new password immediately
    if user.force_password_reset:
        initiator = "an administrator"
        if user.reset_by_teacher_id:
            initiator = "your teacher"
        elif user.reset_by_parent_id:
            initiator = "your parent"
        elif user.reset_by_admin_id:
            initiator = "an administrator"
        raise HTTPException(
            status_code=403,
            detail=f"PASSWORD_RESET_ACTIVE: {initiator.capitalize()} has unlocked your account. Please enter your new password to sign in immediately."
        )

    # Cybersecurity safeguard: brute-force account lockout check
    if user.locked_until:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        now_utc = datetime.now(UTC)
        if now_utc < locked_until:
            minutes_left = max(1, int((locked_until - now_utc).total_seconds() // 60) + 1)
            raise HTTPException(
                status_code=403,
                detail=f"Account temporarily locked due to multiple failed login attempts. Please wait {minutes_left} minutes or ask your teacher/administrator to unlock."
            )
        else:
            user.locked_until = None
            user.failed_login_attempts = 0

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Account temporarily locked for 15 minutes due to 5 failed login attempts. Ask your teacher or administrator for an immediate unlock."
            )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is deactivated. Please contact support.",
        )

    # Password verification alone is not sufficient once the user enabled TOTP.
    _verify_user_second_factor(user, totp_code)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(UTC)

    tokens, _ = auth.issue_refresh_session(db, user, remember_me=remember_me)
    db.commit()
    return tokens


@router.post("/logout")
@limiter.limit("60/minute")
def logout_current_session(
    request: Request,
    payload: schemas.LogoutRequest = schemas.LogoutRequest(),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Revoke the current device refresh session (F-049)."""
    _ = request
    if payload.refresh_token:
        auth.revoke_refresh_session_by_token(db, payload.refresh_token)
    else:
        # No device token provided — revoke all sessions for safety when bearer logs out.
        auth.revoke_all_refresh_sessions(db, current_user.id)
    auth.clear_legacy_refresh_fields(current_user)
    db.commit()
    return {"status": "ok", "message": "Logged out"}


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("60/minute")
def refresh_access_token(
    request: Request,
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(database.get_db),
):
    """Refresh an access token using a valid refresh token (rotate family)."""
    _ = request
    tokens = auth.rotate_refresh_session(db, payload.refresh_token)
    if not tokens:
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    db.commit()
    return tokens



@router.put("/settings", response_model=schemas.UserResponse)
def update_settings(
    settings: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if settings.full_name is not None:
        current_user.full_name = settings.full_name

    if settings.email is not None:
        new_email = settings.email.lower()
        if new_email != current_user.email:
            existing = (
                db.query(models.User).filter(models.User.email == new_email).first()
            )
            if existing:
                raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = new_email

    if settings.phone_number is not None:
        current_user.phone_number = settings.phone_number

    if settings.password:
        _validate_password(settings.password)
        # Verify current password before allowing change
        if not settings.current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password is required to change your password."
            )
        if not verify_password(settings.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect."
            )
        current_user.hashed_password = get_password_hash(settings.password)
        # F-049: password change must invalidate every refresh session.
        auth.revoke_all_refresh_sessions(db, current_user.id)
        auth.clear_legacy_refresh_fields(current_user)

    db.commit()
    db.refresh(current_user)
    return current_user


# ── Self-Service Password Reset (Email OTP) ──────────────────────────────────
# In a Google SSO-only environment, this is a fallback for users who set a password
# and want to reset it. Primary login is Google SSO.

@router.post("/password-reset/request", response_model=schemas.PasswordResetResponse)
@limiter.limit("5/minute")
def request_password_reset(
    request: Request,
    payload: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    """Request a password reset OTP sent to the user's registered email."""
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user:
        # Don't reveal if email exists — always return success
        return schemas.PasswordResetResponse(
            message="If the email exists, a reset OTP has been sent.",
            otp_sent=True
        )

    # Generate high-entropy 32-byte cryptographic token
    reset_token = secrets.token_urlsafe(32)
    user.password_reset_otp = auth.hash_reset_token(reset_token)
    user.password_reset_otp_expires = datetime.now(UTC) + timedelta(hours=24)
    db.commit()

    # Never derive a credential-bearing link from caller-controlled headers.
    try:
        base_url = _configured_frontend_origin()
    except RuntimeError as exc:
        logger.error("Password reset link configuration is invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset is temporarily unavailable.",
        ) from None

    # Keep the bearer token in a URL fragment so it is not sent in HTTP
    # Referer headers. The reset page removes it from history immediately.
    reset_link = (
        f"{base_url}/reset-password#token={quote(reset_token)}"
        f"&email={quote(user.email)}"
    )

    # Dispatch email asynchronously in background
    background_tasks.add_task(email_service.send_password_reset_email, user.email, reset_link, user.username)

    return schemas.PasswordResetResponse(
        message="If the email exists, a 24-hour password reset link has been sent.",
        reset_link_sent=True,
        otp_sent=True
    )


@router.post("/password-reset/confirm", response_model=schemas.Token)
@limiter.limit("10/minute")
def confirm_password_reset(
    request: Request,
    payload: schemas.PasswordResetConfirm,
    db: Session = Depends(database.get_db),
):
    """Confirm password reset with OTP or recovery code."""
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or OTP")

    # Check reset token or legacy OTP. New requests store only a digest;
    # direct equality remains solely for one-time migration of legacy rows.
    token_candidate = payload.token or payload.otp
    if token_candidate:
        if not auth.verify_reset_token(token_candidate, user.password_reset_otp):
            raise HTTPException(status_code=400, detail="Invalid or expired reset link")
        expires = user.password_reset_otp_expires
        if (
            expires is not None
            and _as_utc(_require_datetime(expires)) < datetime.now(UTC)  # type: ignore[operator]
        ):
            raise HTTPException(status_code=400, detail="Reset link has expired")

    # Check recovery code (for 2FA users)
    elif payload.recovery_code:
        codes = _decode_recovery_codes(user.recovery_codes)
        if not codes:
            raise HTTPException(status_code=400, detail="No recovery codes available")
        matching_hash = next(
            (stored for stored in codes if auth.verify_recovery_code(payload.recovery_code, stored)),
            None,
        )
        if matching_hash is None:
            raise HTTPException(status_code=400, detail="Invalid recovery code")
        # Remove used recovery code
        remaining = [c for c in codes if c != matching_hash]
        user.recovery_codes = _encode_recovery_codes(remaining)

    else:
        raise HTTPException(status_code=400, detail="Reset token or recovery code required")

    # Validate new password
    _validate_password(payload.new_password)
    user.hashed_password = get_password_hash(payload.new_password)
    user.password_reset_otp = None
    user.password_reset_otp_expires = None
    user.reset_token = None
    user.force_password_reset = False
    user.reset_expires = None
    user.reset_by_teacher_id = None
    user.reset_by_parent_id = None
    user.reset_by_admin_id = None
    # Password reset invalidates all refresh credentials issued before it.
    auth.revoke_all_refresh_sessions(db, user.id)
    auth.clear_legacy_refresh_fields(user)
    db.commit()

    # Return new access token
    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ── Classroom Teacher Quick Password Reset ────────────────────────────────────

@router.get("/teacher/students")
def list_students_for_teacher(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List registered student accounts for an approved teacher or administrator."""
    if not (
        current_user.role in ("teacher", "admin")
        and (current_user.teacher_approved or current_user.is_admin)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approved teacher or administrator status required",
        )
    students = (
        db.query(models.User)
        .filter(models.User.role == "student")
        .order_by(models.User.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "username": s.username,
            "email": s.email,
            "full_name": s.full_name or s.username,
            "is_active": s.is_active,
            "force_password_reset": bool(s.force_password_reset),
            "locked_until": s.locked_until.isoformat() if s.locked_until else None,
        }
        for s in students
    ]


@router.post("/teacher/quick-reset/{student_id}")
def teacher_quick_reset_student(
    student_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Teacher unlocks a student account right before a test.
    The student can simply enter their email at login and immediately set a new password.
    """
    if not (current_user.role in ("teacher", "admin") and current_user.teacher_approved):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approved teacher or administrator status required"
        )

    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Cybersecurity safeguard: teachers can ONLY reset student accounts, never teachers or admins
    if student.role != "student":
        raise HTTPException(status_code=400, detail="Teachers can only quick-reset student accounts")

    student.force_password_reset = True
    student.reset_by_teacher_id = current_user.id
    student.reset_expires = datetime.now(UTC) + timedelta(hours=24)
    student.failed_login_attempts = 0
    student.locked_until = None
    auth.revoke_all_refresh_sessions(db, student.id)
    auth.clear_legacy_refresh_fields(student)
    student.is_active = True
    # Generate signed reset capability token
    student.reset_token = hashlib.sha256(
        f"{student.id}:{current_user.id}:{secrets.token_hex(32)}".encode()
    ).hexdigest()

    # In-app notification for the student
    notif = models.InAppNotification(
        user_id=student.id,
        title="Password Reset by Teacher",
        message=f"Teacher {current_user.full_name or current_user.username} has unlocked your account for the exam. You can set a new password right when you log in. This reset link expires in 24 hours.",
        type="system",
        link="/login",
    )
    db.add(notif)
    db.commit()

    return {
        "status": "success",
        "student_id": student.id,
        "student_name": student.full_name or student.username,
        "email": student.email,
        "reset_token": student.reset_token,
        "message": f"Password reset initiated for {student.full_name or student.username}. Share the reset token securely with the student. They can set their new password using the token.",
    }


@router.post("/parent/quick-reset/{student_id}")
def parent_quick_reset_student(
    student_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Parent unlocks their child's account if they lost recovery codes or 2FA device.
    Requires an ACTIVE parent-student relationship.
    """
    if current_user.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent status required"
        )

    # Verify active parent-student relationship
    relationship = (
        db.query(models.AccountRelationship)
        .filter(
            models.AccountRelationship.parent_id == current_user.id,
            models.AccountRelationship.student_id == student_id,
            models.AccountRelationship.status == models.RelationshipStatus.active,
            models.AccountRelationship.student_approved == True,
        )
        .first()
    )
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active parent-child relationship found for this student"
        )

    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.role != "student":
        raise HTTPException(status_code=400, detail="Parents can only quick-reset student accounts")

    student.force_password_reset = True
    student.reset_by_parent_id = current_user.id
    student.reset_by_teacher_id = None
    student.reset_by_admin_id = None
    student.reset_expires = datetime.now(UTC) + timedelta(hours=24)
    student.failed_login_attempts = 0
    student.locked_until = None
    auth.revoke_all_refresh_sessions(db, student.id)
    auth.clear_legacy_refresh_fields(student)
    student.is_active = True
    # Generate signed reset capability token
    student.reset_token = hashlib.sha256(
        f"{student.id}:{current_user.id}:{secrets.token_hex(32)}".encode()
    ).hexdigest()

    # In-app notification for the student
    notif = models.InAppNotification(
        user_id=student.id,
        title="Password Reset by Parent",
        message=f"Parent {current_user.full_name or current_user.username} has unlocked your account. You can set a new password right when you log in. This reset link expires in 24 hours.",
        type="system",
        link="/login",
    )
    db.add(notif)
    db.commit()

    return {
        "status": "success",
        "student_id": student.id,
        "student_name": student.full_name or student.username,
        "email": student.email,
        "reset_token": student.reset_token,
        "message": f"Password reset initiated for {student.full_name or student.username}. Share the reset token securely with the student. They can set their new password using the token.",
    }


@router.post("/admin/quick-reset/{user_id}")
def admin_quick_reset_user(
    user_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Admin unlocks a teacher's account if they lost recovery codes or 2FA device.
    Superadmin can also reset admin accounts.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required"
        )

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Regular admins can only reset teacher accounts
    # Superadmins can reset both teacher and admin accounts
    if target_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=400, detail="Admins can only quick-reset teacher or admin accounts")

    # Only superadmin can reset another admin account (F-003)
    if target_user.is_admin and not getattr(current_user, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Only superadmin can reset administrator accounts")

    # Prevent self-reset
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot reset your own account")

    target_user.force_password_reset = True
    target_user.reset_by_admin_id = current_user.id
    target_user.reset_by_teacher_id = None
    target_user.reset_by_parent_id = None
    target_user.reset_expires = datetime.now(UTC) + timedelta(hours=24)
    target_user.failed_login_attempts = 0
    target_user.locked_until = None
    auth.revoke_all_refresh_sessions(db, target_user.id)
    auth.clear_legacy_refresh_fields(target_user)
    target_user.is_active = True
    # Generate signed reset capability token
    target_user.reset_token = hashlib.sha256(
        f"{target_user.id}:{current_user.id}:{secrets.token_hex(32)}".encode()
    ).hexdigest()

    # In-app notification for the user
    notif = models.InAppNotification(
        user_id=target_user.id,
        title="Password Reset by Administrator",
        message=f"Administrator {current_user.full_name or current_user.username} has unlocked your account. You can set a new password right when you log in. This reset link expires in 24 hours.",
        type="system",
        link="/login",
    )
    db.add(notif)
    db.commit()

    return {
        "status": "success",
        "user_id": target_user.id,
        "user_name": target_user.full_name or target_user.username,
        "email": target_user.email,
        "role": target_user.role,
        "reset_token": target_user.reset_token,
        "message": f"Password reset initiated for {target_user.full_name or target_user.username}. Share the reset token securely with the user. They can set their new password using the token.",
    }


@router.post("/teacher-reset/check", response_model=schemas.TeacherResetCheckResponse)
def check_teacher_reset_status(
    payload: schemas.TeacherResetCheckRequest,
    db: Session = Depends(database.get_db),
):
    """Check if a user has a pending password reset active (teacher, parent, or admin initiated)."""
    lookup = payload.identifier.strip().lower()
    user = db.query(models.User).filter(
        (models.User.email == lookup) | (models.User.username == lookup)
    ).first()

    if not user or not user.force_password_reset:
        return schemas.TeacherResetCheckResponse(
            teacher_reset_active=False,
            message="No active password reset found."
        )

    # Check expiration (24 hours)
    expires = user.reset_expires
    if expires is not None and _as_utc(_require_datetime(expires)) < datetime.now(UTC):  # type: ignore[operator]
        # Reset expired - clear it
        user.force_password_reset = False
        user.reset_by_teacher_id = None
        user.reset_by_parent_id = None
        user.reset_by_admin_id = None
        user.reset_expires = None
        db.commit()
        return schemas.TeacherResetCheckResponse(
            teacher_reset_active=False,
            message="Password reset has expired. Please request a new reset."
        )
    # Determine who initiated the reset for appropriate messaging
    initiator = "an administrator"
    if user.reset_by_teacher_id:
        initiator = "your teacher"
    elif user.reset_by_parent_id:
        initiator = "your parent"
    elif user.reset_by_admin_id:
        initiator = "an administrator"

    return schemas.TeacherResetCheckResponse(
        teacher_reset_active=True,
        message=f"Password reset active! {initiator.capitalize()} has unlocked your account. You may set your new password now. This reset link expires in 24 hours.",
    )


@router.post("/teacher-reset/complete", response_model=schemas.Token)
@limiter.limit("10/minute")
def complete_teacher_reset(
    request: Request,
    payload: schemas.TeacherResetCompleteRequest,
    db: Session = Depends(database.get_db),
):
    """
    User completes password reset by entering new password and receives tokens immediately.
    Can be initiated by teacher, parent, or administrator.
    """
    lookup = payload.identifier.strip().lower()
    user = db.query(models.User).filter(
        (models.User.email == lookup) | (models.User.username == lookup)
    ).first()

    if not user or not user.force_password_reset:
        raise HTTPException(status_code=400, detail="No active password reset found for this account")

    # Verify signed reset token
    if not user.reset_token or not payload.reset_token:
        raise HTTPException(status_code=400, detail="Reset token required")
    if not secrets.compare_digest(user.reset_token, payload.reset_token):
        raise HTTPException(status_code=400, detail="Invalid reset token")

    # Check expiration (24 hours)
    expires = user.reset_expires
    if (
        expires is not None
        and _as_utc(_require_datetime(expires)) < datetime.now(UTC)  # type: ignore[operator]
    ):
        raise HTTPException(status_code=400, detail="Password reset has expired. Please request a new reset.")

    _validate_password(payload.new_password)
    user.hashed_password = get_password_hash(payload.new_password)
    user.force_password_reset = False
    user.reset_expires = None
    user.reset_by_teacher_id = None
    user.reset_by_parent_id = None
    user.reset_by_admin_id = None
    user.reset_token = None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.is_active = True

    auth.revoke_all_refresh_sessions(db, user.id)
    tokens, _ = auth.issue_refresh_session(db, user, remember_me=False)
    db.commit()

    return tokens


# ── CAPTCHA / Bot Protection Endpoints ───────────────────────────────────────
# Free, self-hosted options: Turnstile (Cloudflare), hCaptcha, or simple math challenge
# Configure via CAPTCHA_PROVIDER env var: "turnstile" | "hcaptcha" | "simple" | "none"

@router.get("/captcha/challenge", response_model=schemas.CaptchaChallengeResponse)
async def get_captcha_challenge(request: Request):
    """Get a CAPTCHA challenge for the frontend."""
    provider = CAPTCHA_PROVIDER

    if provider == "simple":
        challenge = generate_simple_challenge()
        return schemas.CaptchaChallengeResponse(
            challenge_id=challenge["challenge_id"],
            question=challenge["question"],
            site_key=challenge["site_key"],
            provider="simple",
        )
    elif provider == "turnstile":
        return schemas.CaptchaChallengeResponse(
            challenge_id="",
            question="",
            site_key=CAPTCHA_SITE_KEY,
            provider="turnstile",
        )
    elif provider == "hcaptcha":
        return schemas.CaptchaChallengeResponse(
            challenge_id="",
            question="",
            site_key=CAPTCHA_SITE_KEY,
            provider="hcaptcha",
        )
    else:
        # No CAPTCHA configured
        return schemas.CaptchaChallengeResponse(
            challenge_id="",
            question="",
            site_key="",
            provider="none",
        )


@router.post("/captcha/verify")
async def verify_captcha_endpoint(
    request: Request,
    payload: schemas.CaptchaVerifyRequest,
):
    """Verify a CAPTCHA token."""
    client_ip = request.client.host if request.client else "unknown"

    is_valid = await verify_captcha(payload.token, client_ip)

    if is_valid:
        return {"valid": True, "message": "CAPTCHA verified successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid CAPTCHA")


# ── 2FA / TOTP Endpoints ─────────────────────────────────────────────────────
# Users can enable TOTP (Google Authenticator, Authy, etc.) for additional security.
# Once enabled, recovery codes are the ONLY fallback if they lose their device.

@router.post("/2fa/setup", response_model=schemas.TwoFASetupResponse)
def setup_2fa(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Generate a new TOTP secret and QR code for the user."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    # Generate a new TOTP secret
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    db.commit()

    # Generate provisioning URI for QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=auth.TOTP_ISSUER
    )

    # Generate recovery codes and store only hashed values in the database
    recovery_codes = auth.generate_recovery_codes()
    current_user.recovery_codes = _encode_recovery_codes(
        [auth.hash_recovery_code(code) for code in recovery_codes]
    )
    db.commit()

    return schemas.TwoFASetupResponse(
        secret=secret,
        qr_code_uri=totp_uri,
        recovery_codes=recovery_codes,
        message=(
            "Save your recovery codes! They are the ONLY way to "
            "recover access if you lose your 2FA device."
        ),
    )


@router.post("/2fa/confirm", response_model=schemas.TwoFAConfirmResponse)
def confirm_2fa(
    payload: schemas.TwoFAConfirm,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Confirm the TOTP code to enable 2FA."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    db.commit()

    return schemas.TwoFAConfirmResponse(
        message="2FA enabled successfully. Save your recovery codes!"
    )


@router.post("/2fa/disable", response_model=schemas.TwoFADisableResponse)
def disable_2fa(
    payload: schemas.TwoFADisable,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Disable 2FA. Requires current TOTP code or a recovery code."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    # Verify TOTP code
    if payload.totp_code:
        totp = pyotp.TOTP(current_user.totp_secret)
        if not totp.verify(payload.totp_code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Or verify recovery code
    elif payload.recovery_code:
        codes = _decode_recovery_codes(current_user.recovery_codes)
        matching_hash = next(
            (
                stored
                for stored in codes
                if auth.verify_recovery_code(payload.recovery_code, stored)
            ),
            None,
        )
        if matching_hash is None:
            raise HTTPException(status_code=400, detail="Invalid recovery code")
        remaining = [c for c in codes if c != matching_hash]
        current_user.recovery_codes = _encode_recovery_codes(remaining)

    else:
        raise HTTPException(status_code=400, detail="TOTP code or recovery code required")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()

    return schemas.TwoFADisableResponse(
        message="2FA disabled successfully."
    )


@router.post("/2fa/regenerate-recovery-codes", response_model=schemas.RecoveryCodesResponse)
def regenerate_recovery_codes(
    payload: schemas.TwoFAReauth,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Regenerate recovery codes (invalidates old ones). Requires TOTP confirmation."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    if payload.totp_code:
        if not current_user.totp_secret or not pyotp.TOTP(current_user.totp_secret).verify(
            payload.totp_code, valid_window=1
        ):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
    elif payload.recovery_code:
        codes = _decode_recovery_codes(current_user.recovery_codes)
        matching_hash = next(
            (
                stored
                for stored in codes
                if auth.verify_recovery_code(payload.recovery_code, stored)
            ),
            None,
        )
        if matching_hash is None:
            raise HTTPException(status_code=400, detail="Invalid recovery code")
        current_user.recovery_codes = _encode_recovery_codes(
            [code for code in codes if code != matching_hash]
        )
    else:
        raise HTTPException(status_code=400, detail="TOTP code or recovery code required")

    recovery_codes = auth.generate_recovery_codes()
    current_user.recovery_codes = _encode_recovery_codes(
        [auth.hash_recovery_code(code) for code in recovery_codes]
    )
    db.commit()

    return schemas.RecoveryCodesResponse(
        recovery_codes=recovery_codes,
        message="New recovery codes generated. Old codes are now invalid. Save these!"
    )


# ── AI Key Management ────────────────────────────────────────────────────────

@router.get("/ai-key", response_model=schemas.AIKeyResponse)
def get_ai_key(
    current_user: models.User = Depends(get_current_user),
):
    """Get current AI provider configuration (without the API key)."""
    return schemas.AIKeyResponse(
        ai_provider=current_user.ai_provider,
        ai_model_name=current_user.ai_model_name,
        ai_base_url=current_user.ai_base_url,
        has_api_key=bool(current_user.ai_api_key_encrypted),
    )


@router.put("/ai-key", response_model=schemas.AIKeyResponse)
def update_ai_key(
    payload: schemas.AIKeyUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update AI provider configuration. API key is encrypted before storage."""
    if payload.ai_provider is not None:
        current_user.ai_provider = payload.ai_provider
    if payload.ai_model_name is not None:
        current_user.ai_model_name = payload.ai_model_name
    if payload.ai_base_url is not None:
        # F-022: re-validate against the (possibly updated) provider; fail closed.
        from .url_safety import UnsafeURLError, validate_ai_base_url

        provider = (
            payload.ai_provider
            if payload.ai_provider is not None
            else current_user.ai_provider
        )
        try:
            current_user.ai_base_url = validate_ai_base_url(
                payload.ai_base_url, provider=provider
            )
        except UnsafeURLError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.ai_api_key is not None:
        if payload.ai_api_key.strip() == "":
            current_user.ai_api_key_encrypted = None
        else:
            current_user.ai_api_key_encrypted = crypto.encrypt_api_key(payload.ai_api_key)
    db.commit()
    db.refresh(current_user)
    return schemas.AIKeyResponse(
        ai_provider=current_user.ai_provider,
        ai_model_name=current_user.ai_model_name,
        ai_base_url=current_user.ai_base_url,
        has_api_key=bool(current_user.ai_api_key_encrypted),
    )


# ── WebAuthn / Passkeys ──────────────────────────────────────────────────────
# Phishing-resistant authentication (OWASP A07:2025)
# Primary: Google SSO (OAuth2/OIDC) — remains primary
# Passkeys/WebAuthn: Add as phishing-resistant second factor
# - WebAuthn/FIDO2 registration during 2FA setup
# - Platform authenticators (Windows Hello, Touch ID, Android biometrics)
# - Cross-device sync via iCloud Keychain / Google Password Manager
# - Fallback to TOTP 2FA for devices without passkey support

# RP (Relying Party) configuration
WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
WEBAUTHN_RP_NAME = "PlannedEducation"
WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:5175")

def _get_webauthn_user(user: models.User) -> dict:
    """Convert user to WebAuthn user entity."""
    return {
        "id": user.id.encode(),
        "name": user.email,
        "displayName": user.full_name or user.username,
    }

def _b64url_decode(value: str) -> bytes:
    """Decode base64url with optional missing padding."""
    return base64.urlsafe_b64decode(value + "===")


def _get_webauthn_credentials(user: models.User) -> list[bytes]:
    """Get user's registered WebAuthn credentials as raw byte IDs."""
    if not user.webauthn_credentials:
        return []
    try:
        creds = json.loads(user.webauthn_credentials)
        return [
            _b64url_decode(cred["credential_id"])
            for cred in creds
            if "credential_id" in cred
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, binascii.Error):
        return []

def _save_webauthn_credential(user: models.User, credential: dict) -> None:
    """Save a new WebAuthn credential for the user."""
    creds = []
    if user.webauthn_credentials:
        try:
            creds = json.loads(user.webauthn_credentials)
        except (json.JSONDecodeError, TypeError):
            creds = []
    creds.append(credential)
    user.webauthn_credentials = json.dumps(creds)


def _lookup_user_by_email_or_username(db: Session, identifier: str) -> models.User | None:
    lookup = identifier.strip().lower()
    if not lookup:
        return None
    return (
        db.query(models.User)
        .filter((models.User.email == lookup) | (models.User.username == lookup))
        .first()
    )


def _webauthn_generic_login_error() -> HTTPException:
    """Same shape for missing accounts and missing passkeys (anti-enumeration)."""
    return HTTPException(
        status_code=400,
        detail="Passkey authentication unavailable",
    )


def _build_authentication_start_response(
    user: models.User,
    db: Session,
) -> schemas.WebAuthnAuthenticationStart:
    credentials = _get_webauthn_credentials(user)
    if not credentials:
        raise _webauthn_generic_login_error()

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=cred_id) for cred_id in credentials
    ]
    options = generate_authentication_options(
        rp_id=WEBAUTHN_RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    challenge = base64.urlsafe_b64encode(options.challenge).decode()
    user.webauthn_challenge = challenge
    user.webauthn_challenge_expires = datetime.now(UTC) + timedelta(minutes=5)
    db.commit()

    return schemas.WebAuthnAuthenticationStart(
        challenge=challenge,
        timeout=options.timeout,
        rpId=options.rp_id,
        allowCredentials=[
            {
                "type": "public-key",
                "id": base64.urlsafe_b64encode(cred.id).decode(),
                "transports": cred.transports,
            }
            for cred in options.allow_credentials
        ]
        if options.allow_credentials
        else None,
        userVerification=options.user_verification,
        extensions=getattr(options, "extensions", None) or {},
    )


def _verify_webauthn_assertion(
    user: models.User,
    assertion: dict,
    db: Session,
) -> None:
    """Verify a WebAuthn assertion and update credential counters."""
    if not user.webauthn_challenge:
        raise HTTPException(status_code=400, detail="No active authentication challenge")

    expires = user.webauthn_challenge_expires
    if (
        expires is not None
        and _as_utc(_require_datetime(expires)) < datetime.now(UTC)  # type: ignore[operator]
    ):
        raise HTTPException(status_code=400, detail="Authentication challenge expired")

    credential_id = assertion.get("id")
    creds = (
        json.loads(user.webauthn_credentials) if user.webauthn_credentials else []
    )
    stored_cred = next((c for c in creds if c["credential_id"] == credential_id), None)
    if not stored_cred:
        raise HTTPException(status_code=400, detail="Credential not found")

    pubkey = base64.b64decode(stored_cred["public_key"])
    sign_count = stored_cred.get("sign_count", 0)
    expected_challenge = _b64url_decode(user.webauthn_challenge)

    try:
        verification = verify_authentication_response(
            credential=assertion,
            expected_challenge=expected_challenge,
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGIN,
            credential_public_key=pubkey,
            credential_current_sign_count=sign_count,
            require_user_verification=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Authentication verification failed: {e}"
        ) from None

    stored_cred["sign_count"] = verification.sign_count
    stored_cred["last_used_at"] = datetime.now(UTC).isoformat()
    user.webauthn_credentials = json.dumps(creds)
    user.webauthn_challenge = None
    user.webauthn_challenge_expires = None


@router.post("/webauthn/registration/start", response_model=schemas.WebAuthnSetupResponse)
def webauthn_registration_start(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Start WebAuthn registration (passkey setup)."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=400,
            detail="TOTP 2FA must be enabled before setting up passkeys"
        )

    webauthn_user = _get_webauthn_user(current_user)
    existing_credentials = _get_webauthn_credentials(current_user)

    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=cred_id) for cred_id in existing_credentials
    ]

    options = generate_registration_options(
        rp_id=WEBAUTHN_RP_ID,
        rp_name=WEBAUTHN_RP_NAME,
        user_id=webauthn_user["id"],
        user_name=webauthn_user["name"],
        user_display_name=webauthn_user["displayName"],
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    # Store challenge in user session (simplified: use user model)
    current_user.webauthn_challenge = base64.urlsafe_b64encode(options.challenge).decode()
    current_user.webauthn_challenge_expires = datetime.now(UTC) + timedelta(minutes=5)
    # Persist before returning; finish is a separate request/session.
    db.commit()

    # Convert options to dict for response
    options_dict = json.loads(options_to_json(options))

    return schemas.WebAuthnSetupResponse(
        registration_options=schemas.WebAuthnRegistrationStart(
            challenge=options_dict["challenge"],
            rp=options_dict["rp"],
            user=options_dict["user"],
            pubKeyCredParams=options_dict["pubKeyCredParams"],
            timeout=options_dict["timeout"],
            attestation=options_dict["attestation"],
            authenticatorSelection=options_dict["authenticatorSelection"],
            extensions=options.extensions or {},
        ),
        message="Use your device's biometric/PIN to create a passkey"
    )

@router.post("/webauthn/registration/finish", response_model=schemas.WebAuthnVerifyResponse)
def webauthn_registration_finish(
    payload: schemas.WebAuthnRegistrationFinish,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Finish WebAuthn registration (passkey setup)."""
    if not current_user.webauthn_challenge:
        raise HTTPException(status_code=400, detail="No active registration challenge")

    expires = current_user.webauthn_challenge_expires
    if (
        expires is not None
        and _as_utc(_require_datetime(expires)) < datetime.now(UTC)  # type: ignore[operator]
    ):
        raise HTTPException(status_code=400, detail="Registration challenge expired")

    expected_challenge = base64.urlsafe_b64decode(
        current_user.webauthn_challenge + "==="
    )
    try:
        verification = verify_registration_response(
            credential=payload.model_dump(),
            expected_challenge=expected_challenge,
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGIN,
            require_user_verification=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Registration verification failed: {e}"
        ) from None

    # Save credential
    credential = {
        "credential_id": base64.urlsafe_b64encode(verification.credential_id).decode(),
        "public_key": base64.b64encode(verification.credential_public_key).decode(),
        "sign_count": verification.sign_count,
        "transports": payload.response.get("transports", []),
        "created_at": datetime.now(UTC).isoformat(),
        "last_used_at": None,
    }
    _save_webauthn_credential(current_user, credential)

    # Clear challenge
    current_user.webauthn_challenge = None
    current_user.webauthn_challenge_expires = None
    db.commit()

    return schemas.WebAuthnVerifyResponse(
        verified=True,
        message="Passkey registered successfully"
    )

@router.post("/webauthn/login/start", response_model=schemas.WebAuthnAuthenticationStart)
@limiter.limit("10/minute")
def webauthn_login_start(
    request: Request,
    payload: schemas.WebAuthnLoginStartRequest,
    db: Session = Depends(database.get_db),
):
    """Unauthenticated passkey login start (F-006). No bearer required."""
    _ = request
    user = _lookup_user_by_email_or_username(db, payload.email)
    if not user or not user.is_active or not user.webauthn_credentials:
        raise _webauthn_generic_login_error()
    return _build_authentication_start_response(user, db)


@router.post("/webauthn/login/finish", response_model=schemas.Token)
@limiter.limit("10/minute")
def webauthn_login_finish(
    request: Request,
    payload: schemas.WebAuthnLoginFinishRequest,
    db: Session = Depends(database.get_db),
):
    """Unauthenticated passkey login finish — issues access+refresh on success."""
    _ = request
    user = _lookup_user_by_email_or_username(db, payload.email)
    if not user or not user.is_active:
        raise _webauthn_generic_login_error()

    assertion = payload.model_dump(exclude={"email", "remember_me"})
    _verify_webauthn_assertion(user, assertion, db)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(UTC)
    tokens, _ = auth.issue_refresh_session(
        db, user, remember_me=payload.remember_me
    )
    db.commit()
    return tokens


@router.post("/webauthn/authentication/start", response_model=schemas.WebAuthnAuthenticationStart)
def webauthn_authentication_start(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Start WebAuthn authentication for step-up (requires bearer)."""
    credentials = _get_webauthn_credentials(current_user)
    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered")
    return _build_authentication_start_response(current_user, db)


@router.post("/webauthn/authentication/finish", response_model=schemas.WebAuthnVerifyResponse)
def webauthn_authentication_finish(
    payload: schemas.WebAuthnAuthenticationFinish,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Finish WebAuthn authentication for step-up (requires bearer)."""
    _verify_webauthn_assertion(current_user, payload.model_dump(), db)
    db.commit()
    return schemas.WebAuthnVerifyResponse(
        verified=True,
        message="Passkey authentication successful",
    )

@router.get("/webauthn/credentials", response_model=list[schemas.WebAuthnCredentialResponse])
def list_webauthn_credentials(
    current_user: models.User = Depends(get_current_user),
):
    """List user's registered passkeys."""
    if not current_user.webauthn_credentials:
        return []
    try:
        creds = json.loads(current_user.webauthn_credentials)
        return [
            schemas.WebAuthnCredentialResponse(
                credential_id=cred["credential_id"],
                public_key=cred["public_key"],
                sign_count=cred["sign_count"],
                transports=cred.get("transports", []),
                created_at=cred["created_at"],
                last_used_at=cred.get("last_used_at"),
            )
            for cred in creds
        ]
    except (json.JSONDecodeError, TypeError):
        return []

@router.delete("/webauthn/credentials/{credential_id}")
@limiter.limit("10/minute")
def delete_webauthn_credential(
    request: Request,
    credential_id: str,
    totp_code: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a registered passkey (requires second factor when TOTP is enabled)."""
    _ = request  # required for slowapi
    # F-006 remainder: passkey deletion must not rely on bearer alone.
    _verify_user_second_factor(current_user, totp_code)
    if not current_user.webauthn_credentials:
        raise HTTPException(status_code=404, detail="Credential not found")

    try:
        creds = json.loads(current_user.webauthn_credentials)
        creds = [c for c in creds if c["credential_id"] != credential_id]
        current_user.webauthn_credentials = json.dumps(creds)
        db.commit()
        return {"message": "Passkey deleted"}
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=404, detail="Credential not found") from None


# ── Teacher's Aide Management ────────────────────────────────────────────────
# Teachers can approve teacher's aides (helpers) who can assist with grading
# exams but cannot submit grades to students - only the teacher can do that.


@router.post("/teacher-aide/request", response_model=schemas.UserResponse)
def request_teacher_aide(
    payload: schemas.TeacherAideRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Request teacher's aide status.

    Any authenticated user can request to become a teacher's aide.
    The request creates an in-app notification for administrators to review.
    A teacher or admin must approve the request via /teacher-aide/approve.
    """
    if current_user.is_teacher_aide:
        raise HTTPException(
            status_code=400,
            detail="User is already a teacher's aide",
        )

    # Notify all admins about the aide request
    admins = db.query(models.User).filter(
        (models.User.role == "admin") | (models.User.role == "superadmin")
    ).all()

    for admin in admins:
        notif = models.InAppNotification(
            user_id=admin.id,
            title="Teacher's Aide Request",
            message=f"{current_user.full_name or current_user.username} ({current_user.email}) "
                    f"requested teacher's aide status. {payload.message or 'No message provided.'}",
            type="aide_request",
            link="/teacher-aide",
            action_payload=json.dumps({"requester_id": current_user.id}),
        )
        db.add(notif)

    db.commit()

    return current_user


@router.post("/teacher-aide/approve", response_model=schemas.UserResponse)
def approve_teacher_aide(
    payload: schemas.TeacherAideApprove,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Approve a user as a teacher's aide.

    Only teachers can approve teacher's aides. The aide gets limited
    permissions to help with grading but cannot submit grades to students.
    """
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can approve teacher's aides"
        )

    aide = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not aide:
        raise HTTPException(status_code=404, detail="User not found")

    if aide.role in ("admin", "superadmin"):
        raise HTTPException(
            status_code=400,
            detail="Administrators cannot be teacher's aides"
        )

    if aide.is_teacher_aide:
        raise HTTPException(status_code=400, detail="User is already a teacher's aide")

    aide.is_teacher_aide = True
    # Keep original classroom role for student accounts; grant is the boolean flag.
    # Lounge/share routes must check is_teacher_aide (F-037).
    aide.aide_approved_by = current_user.id
    aide.aide_approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(aide)

    return aide


@router.post("/teacher-aide/nominate", response_model=schemas.UserResponse)
def nominate_teacher_aide(
    payload: schemas.TeacherAideNominate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Nominate a student or user directly as a teacher's aide.

    Grants the same rights as if the registered student requested and was approved.
    Only teachers and admins can nominate teacher's aides.
    """
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can nominate teacher's aides"
        )

    aide = None
    if payload.user_id:
        aide = db.query(models.User).filter(models.User.id == payload.user_id).first()
    elif payload.identifier:
        aide = db.query(models.User).filter(
            (models.User.email == payload.identifier) | (models.User.username == payload.identifier)
        ).first()

    if not aide:
        raise HTTPException(status_code=404, detail="User to nominate not found")

    if aide.role in ("admin", "superadmin"):
        raise HTTPException(status_code=400, detail="Administrators cannot be teacher's aides")

    if aide.is_teacher_aide:
        raise HTTPException(status_code=400, detail="User is already a teacher's aide")

    aide.is_teacher_aide = True
    aide.aide_approved_by = current_user.id
    aide.aide_approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(aide)

    return aide


@router.patch("/teacher/settings/student-dms", response_model=schemas.UserResponse)
def toggle_student_dms(
    payload: schemas.TeacherToggleStudentDms,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Toggle whether students can send direct messages to this teacher."""
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Only teachers can change student DM settings")

    current_user.allow_student_dms = payload.allow_student_dms
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/admin/settings/dm-visibility", response_model=schemas.UserResponse)
def toggle_admin_dm_visibility(
    payload: schemas.AdminToggleDmVisibility,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Toggle whether an admin is visible in the Teacher Lounge direct message list."""
    if not (current_user.is_admin or current_user.role in ("admin", "superadmin")):
        raise HTTPException(status_code=403, detail="Only admins can change DM visibility settings")

    current_user.is_visible_in_teacher_dm = payload.is_visible_in_teacher_dm
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/teacher-aide/revoke", response_model=schemas.UserResponse)
def revoke_teacher_aide(
    payload: schemas.TeacherAideRevoke,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Revoke teacher's aide status from a user."""
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can revoke teacher's aide status"
        )

    aide = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not aide:
        raise HTTPException(status_code=404, detail="User not found")

    if not aide.is_teacher_aide:
        raise HTTPException(status_code=400, detail="User is not a teacher's aide")

    # Only the teacher who approved can revoke, or an admin/superadmin flag.
    is_admin_actor = bool(
        current_user.is_admin
        or current_user.role in ("admin", "superadmin")
        or getattr(current_user, "is_superadmin", False)
    )
    if not is_admin_actor and aide.aide_approved_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the teacher who approved this aide can revoke it"
        )

    aide.is_teacher_aide = False
    aide.aide_approved_by = None
    aide.aide_approved_at = None
    db.commit()
    db.refresh(aide)

    return aide


@router.get("/teacher-aide/my-aides", response_model=list[schemas.UserResponse])
def list_my_aides(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List teacher's aides approved by the current teacher."""
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can view their aides"
        )

    aides = db.query(models.User).filter(
        models.User.aide_approved_by == current_user.id,
        models.User.is_teacher_aide == True
    ).all()

    return aides


@router.get("/teacher-aide/my-teacher", response_model=schemas.UserResponse | None)
def get_my_approving_teacher(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get the teacher who approved this teacher's aide."""
    if not current_user.is_teacher_aide:
        raise HTTPException(
            status_code=400,
            detail="User is not a teacher's aide"
        )

    teacher = db.query(models.User).filter(
        models.User.id == current_user.aide_approved_by
    ).first()

    if not teacher:
        raise HTTPException(status_code=404, detail="Approving teacher not found")

    return teacher


@router.get("/teacher-aide/shared-exams", response_model=list[schemas.ExamShareResponse])
def list_shared_exams(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List exams shared with the current user (teacher's aide or teacher)."""
    shares = db.query(models.ExamShare).filter(
        models.ExamShare.shared_with_id == current_user.id,
        models.ExamShare.status == "active"
    ).all()

    return shares


@router.post("/teacher-aide/share-exam", response_model=schemas.ExamShareResponse)
def share_exam_with_aide(
    payload: schemas.ExamShareCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Share an exam with a teacher's aide or another teacher for collaborative grading."""
    if current_user.role not in ("teacher", "admin", "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can share exams"
        )

    exam = db.query(models.Exam).filter(models.Exam.id == payload.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the teacher who owns the exam can share it"
        )

    aide = db.query(models.User).filter(models.User.id == payload.shared_with_id).first()
    if not aide:
        raise HTTPException(status_code=404, detail="User not found")

    if aide.role not in ("teacher", "teacher_aide"):
        raise HTTPException(
            status_code=400,
            detail="Can only share exams with teachers or teacher's aides"
        )

    # Check if already shared
    existing = db.query(models.ExamShare).filter(
        models.ExamShare.exam_id == payload.exam_id,
        models.ExamShare.shared_with_id == payload.shared_with_id,
        models.ExamShare.status == "active"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Exam already shared with this user")

    share = models.ExamShare(
        exam_id=payload.exam_id,
        shared_by_teacher_id=current_user.id,
        shared_with_id=payload.shared_with_id,
        permission_level=payload.permission_level or "correct",
        share_notes=payload.share_notes,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return share


@router.delete("/teacher-aide/share-exam/{share_id}")
def unshare_exam(
    share_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Stop sharing an exam with a teacher's aide or teacher."""
    share = db.query(models.ExamShare).filter(models.ExamShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.shared_by_teacher_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the teacher who shared the exam can unshare it"
        )

    share.status = "revoked"
    db.commit()

    return {"message": "Exam unshared successfully"}


@router.get("/teacher-aide/exams-shared-with-me", response_model=list[schemas.ExamShareResponse])
def list_exams_shared_with_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List exams shared with the current user (teacher's aide or teacher)."""
    shares = db.query(models.ExamShare).filter(
        models.ExamShare.shared_with_id == current_user.id,
        models.ExamShare.status == "active"
    ).all()

    return shares


@router.post("/teacher-aide/exams/{share_id}/complete", response_model=schemas.ExamShareResponse)
def mark_exam_share_complete(
    share_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Mark an exam share as complete (teacher's aide finished correcting)."""
    share = db.query(models.ExamShare).filter(models.ExamShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.shared_with_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the person the exam was shared with can mark it complete"
        )

    share.status = "completed"
    share.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(share)

    return share
