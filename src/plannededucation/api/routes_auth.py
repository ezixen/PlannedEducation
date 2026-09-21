from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

import os
from google.oauth2 import id_token
from google.auth.transport import requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

@router.post("/google", response_model=schemas.Token)
def google_login(data: schemas.GoogleLogin, db: Session = Depends(database.get_db)):
    try:
        allow_dev_auth = os.getenv("ALLOW_DEV_AUTH") == "true"
        if allow_dev_auth and data.token == "dev-token-teacher":
            email = "teacher@plannededucation.local"
            google_id = "dev-123"
            name = "Test Teacher"
            if not data.role: data.role = "teacher"
        elif allow_dev_auth and data.token == "dev-token-student":
            email = "student@plannededucation.local"
            google_id = "dev-456"
            name = "Test Student"
            if not data.role: data.role = "student"
        else:
            if not GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=503, detail="Google sign-in is not configured")
            # Validate the token with Google
            idinfo = id_token.verify_oauth2_token(data.token, requests.Request(), GOOGLE_CLIENT_ID)
            
            email = idinfo['email']
            google_id = idinfo['sub']
            name = idinfo.get('name', '')
        
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            # Create new user via Google
            # Self-sign-up must never grant privileged teacher or parent roles.
            # Those accounts need an invitation/provisioning flow, which has not
            # been built yet.
            if data.role not in (None, schemas.RoleEnum.student):
                raise HTTPException(status_code=403, detail="Teacher and parent accounts must be provisioned by the school")
            
            user = models.User(
                email=email,
                google_id=google_id,
                full_name=name,
                role=schemas.RoleEnum.student
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

