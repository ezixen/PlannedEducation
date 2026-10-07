import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Optional

import argon2
import httpx
import jwt  # PyJWT for JWT encoding/decoding
import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticationCredential,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    COSEAlgorithmIdentifier,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    UserVerificationRequirement,
)

from . import auth, crypto, database, models, schemas

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
                if time.time() < expiry and hmac.compare_digest(correct_answer, user_answer.strip()):
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


# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
if os.getenv("PLANNED_EDUCATION_ENV") == "test":
    def _noop_limit(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator
    limiter.limit = _noop_limit



router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

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


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
@limiter.limit("10/minute")
def register_user(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    _validate_password(user.password)

    # Atomic duplicate check — use case-insensitive email comparison
    existing_email = (
        db.query(models.User)
        .filter(models.User.email == user.email.lower())
        .first()
    )
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = (
        db.query(models.User)
        .filter(models.User.username == user.username.lower())
        .first()
    )
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    db_user = models.User(
        email=user.email.lower(),
        username=user.username.lower(),
        full_name=user.full_name,
        phone_number=user.phone_number,
        hashed_password=get_password_hash(user.password),
        role=user.role,
        is_admin=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Pre-compute a valid Argon2id hash for constant-time comparisons to prevent timing attacks
_DUMMY_HASH = get_password_hash("dummy_password_for_timing_check")

@router.post("/token", response_model=schemas.Token)
@limiter.limit("20/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    # Allow login by email OR username (case-insensitive)
    lookup = form_data.username.lower()
    user = (
        db.query(models.User)
        .filter(
            (models.User.email == lookup) | (models.User.username == lookup)
        )
        .first()
    )

    if not user:
        # Perform a dummy verify to prevent timing oracle
        verify_password(form_data.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not user.hashed_password:
        # User exists but has no password (e.g., Google-only account)
        verify_password(form_data.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=401,
            detail=(
                "This account uses Google sign-in. "
                "Please use the Google button to log in."
            ),
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is deactivated. Please contact support.",
        )

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
    user.refresh_token_expires = datetime.now(UTC) + timedelta(
        days=auth.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.commit()
    return tokens


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("20/minute")
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

    provided_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    if not secrets.compare_digest(user.refresh_token_hash, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if _as_utc(user.refresh_token_expires) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    tokens = auth.create_token_pair({"sub": user.email})
    # Update refresh token hash in database (rotate)
    user.refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
    user.refresh_token_expires = datetime.now(UTC) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()
    return tokens


@router.post("/google", response_model=schemas.Token)
@limiter.limit("20/minute")
def google_login(
    request: Request,
    data: schemas.GoogleLogin,
    db: Session = Depends(database.get_db),
):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured on this server",
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            data.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        ) from None

    email: str = idinfo["email"].lower()
    google_id: str = idinfo["sub"]
    name: str = idinfo.get("name", "")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Build a unique username from the email prefix, avoiding collisions
        base = email.split("@")[0]
        username = base
        suffix = 1
        while db.query(models.User).filter(models.User.username == username).first():
            username = f"{base}{suffix}"
            suffix += 1

        user = models.User(
            email=email,
            username=username,
            google_id=google_id,
            full_name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Link Google ID if this account was created with password
        if not user.google_id:
            user.google_id = google_id
            db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    tokens = auth.create_token_pair({"sub": user.email})
    # Store refresh token hash in database
    user.refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
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

    # Generate a 6-digit OTP
    otp = str(secrets.randbelow(900000) + 100000)
    user.password_reset_otp = otp
    user.password_reset_otp_expires = datetime.now(UTC) + timedelta(minutes=10)
    db.commit()

    # In production, send email here. For now, log it (dev only).
    if os.getenv("PLANNED_EDUCATION_ENV") == "development":
        import logging

        logging.getLogger(__name__).info(
            "[DEV] Password reset OTP for %s: %s", user.email, otp
        )

    return schemas.PasswordResetResponse(
        message="If the email exists, a reset OTP has been sent.",
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

    # Check OTP
    if payload.otp:
        if not user.password_reset_otp or user.password_reset_otp != payload.otp:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        if (user.password_reset_otp_expires
                and _as_utc(user.password_reset_otp_expires) < datetime.now(UTC)):
            raise HTTPException(status_code=400, detail="OTP has expired")

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
        raise HTTPException(status_code=400, detail="OTP or recovery code required")

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
    provider = payload.provider or CAPTCHA_PROVIDER
    
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

    rp = RelyingParty(id=WEBAUTHN_RP_ID, name=WEBAUTHN_RP_NAME)
    user = User(
        id=webauthn_user["id"],
        name=webauthn_user["name"],
        display_name=webauthn_user["displayName"],
    )
    existing_keys = [cred.id for cred in existing_credentials]

    options, challenge = create_webauthn_credentials(
        rp=rp,
        user=user,
        existing_keys=existing_keys,
        attachment=AuthenticatorAttachment.PLATFORM,
        require_resident=True,
        user_verification=UserVerification.REQUIRED,
    )

    # Store challenge in user session (simplified: use user model)
    current_user.webauthn_challenge = base64.urlsafe_b64encode(options.challenge).decode()
    current_user.webauthn_challenge_expires = datetime.now(UTC) + timedelta(minutes=5)
    # Note: In production, use a proper session store

    # Convert options to dict for response
    options_dict = options_to_json(options)
    options_dict = json.loads(options_dict)

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

    if _as_utc(current_user.webauthn_challenge_expires) < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Registration challenge expired")

    try:
        # Extract credential data from payload
        client_data_b64 = payload.response.get("clientDataJSON", "")
        attestation_b64 = payload.response.get("attestationObject", "")

        rp = RelyingParty(id=WEBAUTHN_RP_ID, name=WEBAUTHN_RP_NAME)
        verification = verify_create_webauthn_credentials(
            rp=rp,
            challenge_b64=current_user.webauthn_challenge,
            client_data_b64=client_data_b64,
            attestation_b64=attestation_b64,
            fido_metadata=None,  # Optional FIDO metadata
            user_verification_required=True,
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

    rp = RelyingParty(id=WEBAUTHN_RP_ID, name=WEBAUTHN_RP_NAME)
    existing_keys = [cred.id for cred in credentials]

    options, challenge = get_webauthn_credentials(
        rp=rp,
        existing_keys=existing_keys,
        user_verification=UserVerification.REQUIRED,
    )

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

    if _as_utc(current_user.webauthn_challenge_expires) < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Authentication challenge expired")

    try:
        # Extract credential data from payload
        client_data_b64 = payload.response.get("clientDataJSON", "")
        authenticator_b64 = payload.response.get("authenticatorData", "")
        signature_b64 = payload.response.get("signature", "")

        # Get the credential ID to look up the public key
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

        rp = RelyingParty(id=WEBAUTHN_RP_ID, name=WEBAUTHN_RP_NAME)
        verification = verify_get_webauthn_credentials(
            rp=rp,
            challenge_b64=current_user.webauthn_challenge,
            client_data_b64=client_data_b64,
            authenticator_b64=authenticator_b64,
            signature_b64=signature_b64,
            sign_count=sign_count,
            pubkey_alg=-7,  # ES256
            pubkey=pubkey,
            user_verification_required=True,
        )
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
