import enum
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str | None = Field(None, max_length=128)
    phone_number: str | None = Field(None, max_length=32)


class UserCreate(UserBase):
    # Password complexity is validated server-side in routes_auth.py
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=128)
    email: EmailStr | None = None
    phone_number: str | None = Field(None, max_length=32)
    # password is optional; server enforces complexity if provided
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool
    role: str
    totp_enabled: bool
    # hashed_password, totp_secret, ai_api_key_encrypted NEVER included here


# ── Auth ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class GoogleLogin(BaseModel):
    token: str  # The ID token from Google frontend


# ── Questions ─────────────────────────────────────────────────────────────────

class QuestionTypeEnum(StrEnum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"


class QuestionBase(BaseModel):
    question_type: QuestionTypeEnum
    text: str = Field(..., min_length=1, max_length=4096)
    options_json: str | None = None  # JSON string
    correct_answer: str | None = Field(None, max_length=2048)
    rubric: str | None = Field(None, max_length=4096)
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
    options_json: str | None = None
    points: int


# ── Exams ─────────────────────────────────────────────────────────────────────

class ExamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=2048)
    duration_minutes: int = Field(60, ge=1, le=600)
    seb_config_key: str | None = Field(None, max_length=512)


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
    description: str | None = None
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
    score: float | None = Field(None, ge=0.0, le=100.0)


# ── Account Relationships ─────────────────────────────────────────────────────

class RelationshipRequest(BaseModel):
    student_id: str
    teacher_id: str | None = None


class RelationshipApproval(BaseModel):
    approved: bool


# ── Password Reset ────────────────────────────────────────────────────────────

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    message: str
    otp_sent: bool


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=128)
    otp: str | None = Field(None, pattern=r"^\d{6}$")
    recovery_code: str | None = Field(None, min_length=8, max_length=16)


# ── 2FA / TOTP ────────────────────────────────────────────────────────────────

class TwoFASetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    recovery_codes: list[str]
    message: str


class TwoFAConfirm(BaseModel):
    code: str = Field(..., pattern=r"^\d{6}$")


class TwoFAConfirmResponse(BaseModel):
    message: str


class TwoFADisable(BaseModel):
    totp_code: str | None = Field(None, pattern=r"^\d{6}$")
    recovery_code: str | None = Field(None, min_length=8, max_length=16)


class TwoFADisableResponse(BaseModel):
    message: str


class RecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]
    message: str


# ── AI Key Management ────────────────────────────────────────────────────────

class AIKeyUpdate(BaseModel):
    ai_provider: str | None = Field(None, pattern=r"^(gemini|openrouter|ollama|openai)$")
    ai_api_key: str | None = Field(None, max_length=512)
    ai_model_name: str | None = Field(None, max_length=128)
    ai_base_url: str | None = Field(None, max_length=512)


class AIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ai_provider: str | None = None
    ai_model_name: str | None = None
    ai_base_url: str | None = None
    has_api_key: bool = False
