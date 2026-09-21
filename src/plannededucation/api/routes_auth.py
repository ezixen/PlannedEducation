from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt

from . import models, schemas, auth, database

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/signup", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

from google.oauth2 import id_token
from google.auth.transport import requests

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID" # Will be replaced via ENV

@router.post("/google", response_model=schemas.Token)
def google_login(data: schemas.GoogleLogin, db: Session = Depends(database.get_db)):
    try:
        # Validate the token with Google
        idinfo = id_token.verify_oauth2_token(data.token, requests.Request(), GOOGLE_CLIENT_ID)
        
        email = idinfo['email']
        google_id = idinfo['sub']
        name = idinfo.get('name', '')
        
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            # Create new user via Google
            if not data.role:
                raise HTTPException(status_code=400, detail="Role is required for first-time signup")
            
            user = models.User(
                email=email,
                google_id=google_id,
                full_name=name,
                role=data.role
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update google ID if not set
            if not user.google_id:
                user.google_id = google_id
                db.commit()

        # Generate our JWT
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
        
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google Token")

