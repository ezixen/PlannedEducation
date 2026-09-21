import os
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address

from . import models, schemas, auth, database

# ── Password hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
            detail="Password must contain at least one uppercase letter, one lowercase letter, and one digit.",
        )


# ── Helpers ──────────────────────────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


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
    except JWTError:
        raise credentials_exception

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
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Pre-compute a valid bcrypt hash for constant-time comparisons to prevent timing attacks
_DUMMY_HASH = pwd_context.hash("dummy_password_for_timing_check")

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

    if not user or not user.hashed_password:
        # Perform a dummy verify to prevent timing oracle
        pwd_context.verify(form_data.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")


    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google", response_model=schemas.Token)
@limiter.limit("20/minute")
def google_login(
    request: Request,
    data: schemas.GoogleLogin,
    db: Session = Depends(database.get_db),
):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server")

    try:
        idinfo = id_token.verify_oauth2_token(
            data.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

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

    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


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
