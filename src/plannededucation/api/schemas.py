from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from enum import Enum

class RoleEnum(str, Enum):
    student = "student"
    teacher = "teacher"
    parent = "parent"

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

class QuestionTypeEnum(str, Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"

class QuestionBase(BaseModel):
    question_type: QuestionTypeEnum
    text: str
    options_json: Optional[str] = None
    correct_answer: Optional[str] = None
    rubric: Optional[str] = None
    points: int = 1

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int

class ExamBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 60
    seb_config_key: Optional[str] = None

class ExamCreate(ExamBase):
    pass

class ExamResponse(ExamBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    questions: list[QuestionResponse] = []
