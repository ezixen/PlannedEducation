from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from enum import Enum

class RoleEnum(str, Enum):
    student = "student"
    teacher = "teacher"
    parent = "parent"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: RoleEnum

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class GoogleLogin(BaseModel):
    token: str  # The ID token from Google frontend
    role: Optional[RoleEnum] = None # Needed if signing up for the first time
