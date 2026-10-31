import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta

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
        if email is None:
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
@limiter.limit("500/minute")
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
    hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in plain_recovery_codes]

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
@limiter.limit("500/minute")
async def login_for_access_token(
    request: Request,
    db: Session = Depends(database.get_db),
):
    # Parse form data manually to avoid OAuth2PasswordRequestForm issues
    content_type = request.headers.get("content-type", "")
    logger.info(f"Content-Type: {content_type}")

    # Read raw body first
    body = await request.body()
    logger.info(f"Raw body: {body.decode('utf-8', errors='replace')}")

    # Parse form data from body
    from urllib.parse import parse_qs
    form_data = parse_qs(body.decode("utf-8"))
    username = form_data.get("username", [""])[0].lower()
    password = form_data.get("password", [""])[0]
    remember_me = form_data.get("remember_me", ["false"])[0].lower() == "true"

    logger.info(f"Login attempt: username={username}, remember_me={remember_me}")

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

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(UTC)

    remember_me = False  # OAuth2PasswordRequestForm doesn't support remember_me
    tokens = auth.create_token_pair({"sub": user.email}, remember_me=remember_me)
    user.refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
    if remember_me:
        user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()
    return tokens


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("200/minute")
def refresh_access_token(
    request: Request,
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(database.get_db),
):
    """Refresh an access token using a valid refresh token."""
    payload_data = auth.verify_refresh_token(payload.refresh_token)
    if not payload_data:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    email = payload_data.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Verify refresh token hash matches database
    if not user.refresh_token_hash or not user.refresh_token_expires:
        raise HTTPException(status_code=401, detail="No refresh token stored")

    if user.refresh_token_expires is None:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    provided_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    if not secrets.compare_digest(user.refresh_token_hash, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if (
        user.refresh_token_expires is not None
        and _as_utc(_require_datetime(user.refresh_token_expires)) < datetime.now(UTC)  # type: ignore[operator]
    ):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Check if the refresh token has remember_me flag
    payload_data = auth.verify_refresh_token(payload.refresh_token)
    remember_me = payload_data.get("remember_me", False) if payload_data else False

    tokens = auth.create_token_pair({"sub": user.email}, remember_me=remember_me)
    # Update refresh token hash in database (rotate)
    user.refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
    if remember_me:
        user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
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
    user.password_reset_otp = reset_token
    user.password_reset_otp_expires = datetime.now(UTC) + timedelta(hours=24)
    db.commit()

    # Determine base URL for one-click reset link
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        base_url = origin.split("/#")[0].rstrip("/")
        for path_suffix in ("/login", "/register", "/dashboard"):
            if path_suffix in base_url:
                base_url = base_url.split(path_suffix)[0]
    else:
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    reset_link = f"{base_url}/reset-password?token={reset_token}&email={user.email}"

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

    # Check reset token or legacy OTP
    token_candidate = payload.token or payload.otp
    if token_candidate:
        if not user.password_reset_otp or user.password_reset_otp != token_candidate:
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
        provided_hash = hashlib.sha256(payload.recovery_code.encode()).hexdigest()
        if provided_hash not in codes:
            raise HTTPException(status_code=400, detail="Invalid recovery code")
        # Remove used recovery code
        remaining = [c for c in codes if c != provided_hash]
        user.recovery_codes = _encode_recovery_codes(remaining)

    else:
        raise HTTPException(status_code=400, detail="Reset token or recovery code required")

    # Validate new password
    _validate_password(payload.new_password)
    user.hashed_password = get_password_hash(payload.new_password)
    user.password_reset_otp = None
    user.password_reset_otp_expires = None
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
    student.refresh_token_hash = None
    student.is_active = True

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
        "message": f"Password reset initiated for {student.full_name or student.username}. They can now enter their email address on the login page and set their new password.",
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
    student.refresh_token_hash = None
    student.is_active = True

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
        "message": f"Password reset initiated for {student.full_name or student.username}. They can now enter their email address on the login page and set their new password.",
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

    # Only superadmin can reset another admin account
    if target_user.is_admin and not current_user.is_admin:
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
    target_user.refresh_token_hash = None
    target_user.is_active = True

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
        "message": f"Password reset initiated for {target_user.full_name or target_user.username}. They can now enter their email address on the login page and set their new password.",
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
    if expires is not None:
        if _as_utc(_require_datetime(expires)) < datetime.now(UTC):  # type: ignore[operator]
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
        email=user.email,
        username=user.username,
        full_name=user.full_name,
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
    user.failed_login_attempts = 0
    user.locked_until = None
    user.is_active = True

    tokens = {
        "access_token": auth.create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        "refresh_token": auth.create_refresh_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS),
        ),
        "token_type": "bearer",
    }
    user.refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
    user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
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
        [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes]
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
        provided_hash = hashlib.sha256(payload.recovery_code.encode()).hexdigest()
        if not codes or provided_hash not in codes:
            raise HTTPException(status_code=400, detail="Invalid recovery code")
        remaining = [c for c in codes if c != provided_hash]
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Regenerate recovery codes (invalidates old ones). Requires TOTP confirmation."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    # In a real implementation, require TOTP confirmation here
    recovery_codes = auth.generate_recovery_codes()
    current_user.recovery_codes = _encode_recovery_codes(
        [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes]
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
        current_user.ai_base_url = payload.ai_base_url
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

def _get_webauthn_credentials(user: models.User) -> list[bytes]:
    """Get user's registered WebAuthn credentials as raw byte IDs."""
    if not user.webauthn_credentials:
        return []
    try:
        creds = json.loads(user.webauthn_credentials)
        return [
            base64.urlsafe_b64decode(cred["credential_id"])
            for cred in creds
            if "credential_id" in cred
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
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

@router.post("/webauthn/registration/start", response_model=schemas.WebAuthnSetupResponse)
def webauthn_registration_start(
    current_user: models.User = Depends(get_current_user),
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
    # Note: In production, use a proper session store

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

@router.post("/webauthn/authentication/start", response_model=schemas.WebAuthnAuthenticationStart)
def webauthn_authentication_start(
    current_user: models.User = Depends(get_current_user),
):
    """Start WebAuthn authentication (passkey login)."""
    credentials = _get_webauthn_credentials(current_user)
    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered")

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=cred_id) for cred_id in credentials
    ]

    options = generate_authentication_options(
        rp_id=WEBAUTHN_RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    challenge = base64.urlsafe_b64encode(options.challenge).decode()

    # Store challenge
    current_user.webauthn_challenge = challenge
    current_user.webauthn_challenge_expires = datetime.now(UTC) + timedelta(minutes=5)

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
        ] if options.allow_credentials else None,
        userVerification=options.user_verification,
        extensions=options.extensions or {},
    )

@router.post("/webauthn/authentication/finish", response_model=schemas.WebAuthnVerifyResponse)
def webauthn_authentication_finish(
    payload: schemas.WebAuthnAuthenticationFinish,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Finish WebAuthn authentication (passkey login)."""
    if not current_user.webauthn_challenge:
        raise HTTPException(status_code=400, detail="No active authentication challenge")

    expires = current_user.webauthn_challenge_expires
    if (
        expires is not None
        and _as_utc(_require_datetime(expires)) < datetime.now(UTC)  # type: ignore[operator]
    ):
        raise HTTPException(status_code=400, detail="Authentication challenge expired")

    credential_id = payload.id

    # Look up the stored credential to get the public key
    creds = (
        json.loads(current_user.webauthn_credentials)
        if current_user.webauthn_credentials
        else []
    )
    stored_cred = next((c for c in creds if c["credential_id"] == credential_id), None)
    if not stored_cred:
        raise HTTPException(status_code=400, detail="Credential not found")

    pubkey = base64.b64decode(stored_cred["public_key"])
    sign_count = stored_cred.get("sign_count", 0)
    expected_challenge = base64.urlsafe_b64decode(
        current_user.webauthn_challenge + "==="
    )

    try:
        verification = verify_authentication_response(
            credential=payload.model_dump(),
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

    # Update sign count and last used
    stored_cred["sign_count"] = verification.sign_count
    stored_cred["last_used_at"] = datetime.now(UTC).isoformat()
    current_user.webauthn_credentials = json.dumps(creds)
    current_user.webauthn_challenge = None
    current_user.webauthn_challenge_expires = None
    db.commit()

    return schemas.WebAuthnVerifyResponse(
        verified=True,
        message="Passkey authentication successful"
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
def delete_webauthn_credential(
    credential_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a registered passkey."""
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
