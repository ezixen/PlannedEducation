from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from typing import Optional
from enum import Enum


# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: Optional[str] = Field(None, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=32)


class UserCreate(UserBase):
    # Password complexity is validated server-side in routes_auth.py
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=32)
    # password is optional; server enforces complexity if provided
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool
    # hashed_password, totp_secret, ai_api_key_encrypted NEVER included here


# ── Auth ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class GoogleLogin(BaseModel):
    token: str  # The ID token from Google frontend


# ── Questions ─────────────────────────────────────────────────────────────────

class QuestionTypeEnum(str, Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"


class QuestionBase(BaseModel):
    question_type: QuestionTypeEnum
    text: str = Field(..., min_length=1, max_length=4096)
    options_json: Optional[str] = None  # JSON string
    correct_answer: Optional[str] = Field(None, max_length=2048)
    rubric: Optional[str] = Field(None, max_length=4096)
    points: int = Field(1, ge=1, le=100)


class QuestionCreate(QuestionBase):
    pass


class QuestionResponse(QuestionBase):
    """Full question including correct answer — ONLY for exam owners (teachers)."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    exam_id: str


class StudentQuestionResponse(BaseModel):
    """Stripped question safe for students taking an exam. No answers, no rubric."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    exam_id: str
    question_type: QuestionTypeEnum
    text: str
    options_json: Optional[str] = None
    points: int


# ── Exams ─────────────────────────────────────────────────────────────────────

class ExamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2048)
    duration_minutes: int = Field(60, ge=1, le=600)
    seb_config_key: Optional[str] = Field(None, max_length=512)


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    """Full response for the exam owner (teacher). Includes questions with answers."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    teacher_id: str
    questions: list[QuestionResponse] = []


class ExamListResponse(BaseModel):
    """Safe metadata response for listing exams — no questions, no answers."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str] = None
    duration_minutes: int
    teacher_id: str


# ── Submission ────────────────────────────────────────────────────────────────

class AnswerSubmission(BaseModel):
    question_id: str
    response: str = Field("", max_length=16384)


class ExamSubmitRequest(BaseModel):
    answers: list[AnswerSubmission]


# ── AI ────────────────────────────────────────────────────────────────────────

class AiGradeRequest(BaseModel):
    feedback: str = Field(..., max_length=8192)
    score: Optional[float] = Field(None, ge=0.0, le=100.0)


# ── Account Relationships ─────────────────────────────────────────────────────

class RelationshipRequest(BaseModel):
    student_id: str
    teacher_id: Optional[str] = None


class RelationshipApproval(BaseModel):
    approved: bool
