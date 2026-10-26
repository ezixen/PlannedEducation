import json
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    username: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str | None = Field(None, max_length=128)
    phone_number: str | None = Field(None, max_length=32)


class UserCreate(UserBase):
    # Password complexity is validated server-side in routes_auth.py
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="student", pattern=r"^(student|teacher|parent)$")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=128)
    email: EmailStr | None = None
    phone_number: str | None = Field(None, max_length=32)
    # password is optional; server enforces complexity if provided
    password: str | None = Field(None, min_length=8, max_length=128)
    # current_password is required when changing password
    current_password: str | None = Field(None, min_length=1, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool
    role: str
    totp_enabled: bool
    teacher_approved: bool = True
    # hashed_password, totp_secret, ai_api_key_encrypted NEVER included here


class UserRegistrationResponse(UserResponse):
    recovery_codes: list[str] | None = None
    message: str | None = None


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



class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


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


class AIQuestionCreate(BaseModel):
    """Question schema for AI-assisted exam generation."""
    question_type: QuestionTypeEnum = Field(..., description="Type of question: multiple_choice, essay, dynamic_math")
    text: str = Field(..., min_length=1, max_length=4096, description="Question text prompt")
    options: list[str] | None = Field(None, description="List of choices for multiple choice questions (auto-serialized)")
    options_json: str | None = Field(None, description="Pre-serialized JSON string of choices")
    correct_answer: str | None = Field(None, max_length=2048, description="The correct answer text or formula")
    rubric: str | None = Field(None, max_length=4096, description="Grading criteria or explanation for the answer")
    points: int = Field(1, ge=1, le=100, description="Point value for this question (1-100)")


class AIExamCreate(BaseModel):
    """Request schema for an AI assistant to generate an entire exam atomically."""
    title: str = Field(..., min_length=1, max_length=256, description="Exam title")
    description: str | None = Field(None, max_length=2048, description="Exam description or instructions")
    duration_minutes: int = Field(60, ge=1, le=600, description="Duration in minutes (1 to 600)")
    seb_config_key: str | None = Field(None, max_length=512, description="Safe Exam Browser configuration key (optional)")
    ai_model_name: str | None = Field(None, max_length=128, description="AI model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o')")
    ai_prompt_summary: str | None = Field(None, max_length=512, description="Brief summary of teacher prompt used for generation")
    questions: list[AIQuestionCreate] = Field(..., min_length=1, description="List of questions to generate inside the exam")


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

class QuestionGradeItem(BaseModel):
    question_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    feedback: str = Field("", max_length=4096)
    corrected_answer: str | None = Field(None, max_length=8192)


class AiGradeRequest(BaseModel):
    feedback: str = Field(..., max_length=16384)
    score: float | None = Field(None, ge=0.0, le=100.0)
    question_grades: list[QuestionGradeItem] | None = None


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
    reset_link_sent: bool = True
    otp_sent: bool = True


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=128)
    token: str | None = Field(None, max_length=128)
    otp: str | None = Field(None)
    recovery_code: str | None = Field(None, min_length=8, max_length=16)


class AdminResetPasswordRequest(BaseModel):
    new_password: str | None = Field(None, min_length=8, max_length=128)
    reset_2fa: bool = Field(False, description="Reset and disable 2FA/Passkeys for the user")


class AdminResetPasswordResponse(BaseModel):
    status: str
    user_id: str
    username: str
    email: str
    temporary_password: str
    reset_2fa: bool
    message: str


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    username: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str | None = Field(None, max_length=128)
    role: str = Field(default="admin", pattern=r"^(admin|teacher|student|parent)$")
    password: str | None = Field(None, min_length=8, max_length=128)


class AdminCreateUserResponse(BaseModel):
    status: str
    user_id: str
    username: str
    email: str
    full_name: str | None
    role: str
    temporary_password: str | None = None
    message: str


# ── In-App Notifications ─────────────────────────────────────────────────────

class InAppNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    link: str | None = None
    action_payload: str | None = None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread_count: int


class TeacherResetCheckRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)


class TeacherResetCheckResponse(BaseModel):
    teacher_reset_active: bool
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    message: str | None = None


class TeacherResetCompleteRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=128)


class InternalPasswordResetRequest(BaseModel):
    target_role: str = Field(..., pattern=r"^(teacher|parent|admin)$")
    target_user_id: str | None = None
    note: str | None = Field(None, max_length=256)


class InternalPasswordResetApprove(BaseModel):
    new_password: str | None = Field(None, min_length=8, max_length=128)


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


# ── School Header Customization ──────────────────────────────────────────────

class SchoolHeaderUpdate(BaseModel):
    header_display_mode: str = Field(..., pattern=r"^(text|image|none)$")
    header_text: str | None = Field(None, max_length=256)
    header_image_url: str | None = Field(None, max_length=512)


class SchoolHeaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    header_display_mode: str
    header_text: str | None
    header_image_url: str | None


# ── AI Key Management ────────────────────────────────────────────────────────

class AIKeyUpdate(BaseModel):
    ai_provider: str | None = Field(None, pattern=r"^(chatgpt|gemini|openrouter|ollama|openai|anthropic|deepseek|groq|cohere|mistral|custom)$")
    ai_api_key: str | None = Field(None, max_length=512)
    ai_model_name: str | None = Field(None, max_length=128)
    ai_base_url: str | None = Field(None, max_length=512)


class AIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ai_provider: str | None = None
    ai_model_name: str | None = None
    ai_base_url: str | None = None
    has_api_key: bool = False


# ── WebAuthn / Passkeys ──────────────────────────────────────────────────────
# Phishing-resistant authentication (OWASP A07:2025)

class WebAuthnRegistrationStart(BaseModel):
    """Response for starting WebAuthn registration."""
    challenge: str
    rp: dict
    user: dict
    pubKeyCredParams: list[dict]
    timeout: int
    attestation: str
    authenticatorSelection: dict
    extensions: dict | None = None


class WebAuthnRegistrationFinish(BaseModel):
    """Request to finish WebAuthn registration."""
    id: str
    rawId: str
    response: dict
    type: str
    clientExtensionResults: dict | None = None


class WebAuthnAuthenticationStart(BaseModel):
    """Response for starting WebAuthn authentication."""
    challenge: str
    timeout: int
    rpId: str
    allowCredentials: list[dict] | None = None
    userVerification: str
    extensions: dict | None = None


class WebAuthnAuthenticationFinish(BaseModel):
    """Request to finish WebAuthn authentication."""
    id: str
    rawId: str
    response: dict
    type: str
    clientExtensionResults: dict | None = None


class WebAuthnCredentialResponse(BaseModel):
    """Stored credential info for user."""
    credential_id: str
    public_key: str
    sign_count: int
    transports: list[str] | None = None
    created_at: str
    last_used_at: str | None = None


class WebAuthnSetupResponse(BaseModel):
    """Response for WebAuthn setup initiation."""
    registration_options: WebAuthnRegistrationStart
    message: str


class WebAuthnVerifyResponse(BaseModel):
    """Response for WebAuthn verification."""
    verified: bool
    message: str


# ── CAPTCHA / Bot Protection ─────────────────────────────────────────────────

class CaptchaChallengeResponse(BaseModel):
    """Response for CAPTCHA challenge generation."""
    challenge_id: str
    question: str
    site_key: str | None = None
    provider: str

class CaptchaVerifyRequest(BaseModel):
    """Request to verify CAPTCHA."""
    token: str
    provider: str | None = None


# ── Packages / Modules ────────────────────────────────────────────────────────

class PackageCategoryEnum(StrEnum):
    mathematics = "mathematics"
    chemistry = "chemistry"
    biology = "biology"
    physics = "physics"
    computer_science = "computer_science"
    languages = "languages"
    history = "history"
    geography = "geography"
    literature = "literature"
    arts = "arts"
    health_pe = "health_pe"
    economics = "economics"
    philosophy = "philosophy"
    other = "other"


class PackageStatusEnum(StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class PackageSourceTypeEnum(StrEnum):
    central = "central"
    custom = "custom"
    github = "github"
    local = "local"
    fork = "fork"


class PackageMetadataBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    description: str | None = Field(None, max_length=2048)
    category: PackageCategoryEnum = PackageCategoryEnum.other
    subject: str | None = Field(None, max_length=128)
    grade_level: str | None = Field(None, max_length=32)
    tags: list[str] = Field(default_factory=list)
    license: str = Field("CC-BY-4.0", max_length=64)


class PackageMetadataResponse(PackageMetadataBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version: str
    description: str | None = None
    author: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    checksum: str
    status: str
    is_public: bool
    source_type: str | None = None
    source_url: str | None = None
    download_count: int = 0
    rating_avg: float | None = None
    rating_count: int = 0
    parent_package_id: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v] if v else []
        return v or []

    @field_validator("author", mode="before")
    @classmethod
    def _parse_author(cls, v):
        if hasattr(v, "full_name") or hasattr(v, "username"):
            return v.full_name or v.username or ""
        return str(v) if v is not None else ""

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, v):
        if hasattr(v, "value"):
            return v.value
        return str(v) if v is not None else "draft"


class PackageCreate(PackageMetadataBase):
    package_data: dict  # Full TestPackage JSON
    is_public: bool = False
    source_type: PackageSourceTypeEnum = PackageSourceTypeEnum.local
    source_url: str | None = None


class PackageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    version: str | None = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    description: str | None = Field(None, max_length=2048)
    category: PackageCategoryEnum | None = None
    subject: str | None = Field(None, max_length=128)
    grade_level: str | None = Field(None, max_length=32)
    tags: list[str] | None = None
    license: str | None = Field(None, max_length=64)
    is_public: bool | None = None
    status: str | None = None


class PackageResponse(PackageMetadataResponse):
    package_data: dict  # Full TestPackage JSON
    parent_package_id: str | None = None
    rating_avg: float | None = None
    rating_count: int = 0
    download_count: int = 0

    @field_validator("package_data", mode="before")
    @classmethod
    def _parse_package_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}


class PackageListResponse(BaseModel):
    packages: list[PackageMetadataResponse]
    total: int
    page: int
    page_size: int


class PackageExportRequest(BaseModel):
    exam_id: str
    include_answers: bool = True
    include_rubrics: bool = True
    include_variables: bool = True
    format: str = Field("json", pattern=r"^(json|yaml)$")
    compress: bool = False
    language: str | None = None
    language_name: str | None = None
    country: str | None = None
    subject: str | None = None
    grade_level: str | None = None
    save_to_server: bool = False


class PackageImportResult(BaseModel):
    success: bool
    package_id: str | None = None
    exam_id: str | None = None
    questions_imported: int = 0
    rubrics_imported: int = 0
    errors: list[str] = []
    warnings: list[str] = []


class PackageValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class PackageListFilters(BaseModel):
    subject: str | None = None
    grade_level: str | None = None
    tags: str | None = None
    author_id: str | None = None
    category: PackageCategoryEnum | None = None
    status: str | None = None
    is_public: bool | None = None
    search: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PackageDownloadResponse(BaseModel):
    content: str
    media_type: str
    filename: str


class PackageRatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review: str | None = Field(None, max_length=2048)


class PackageRatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    package_id: str
    user_id: str
    rating: int
    review: str | None = None
    created_at: datetime
    updated_at: datetime


class PackageSourceTypeEnum(StrEnum):
    central = "central"
    custom = "custom"
    github = "github"


class PackageSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., max_length=512)
    api_key: str | None = Field(None, max_length=256)
    source_type: PackageSourceTypeEnum = PackageSourceTypeEnum.custom
    is_enabled: bool = True
    is_default: bool = False
    priority: int = Field(0, ge=0)
    auto_sync: bool = False
    sync_interval_hours: int = Field(24, ge=1, le=168)
    allowed_categories: list[str] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)


class PackageSourceCreate(PackageSourceBase):
    pass


class PackageSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    url: str | None = Field(None, max_length=512)
    api_key: str | None = Field(None, max_length=256)
    is_enabled: bool | None = None
    is_default: bool | None = None
    priority: int | None = Field(None, ge=0)
    auto_sync: bool | None = None
    sync_interval_hours: int | None = Field(None, ge=1, le=168)
    allowed_categories: list[str] | None = None
    allowed_tags: list[str] | None = None


class PackageSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    url: str
    source_type: str
    is_enabled: bool
    is_default: bool
    priority: int
    auto_sync: bool
    sync_interval_hours: int
    allowed_categories: list[str] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)
    last_synced_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("allowed_categories", "allowed_tags", mode="before")
    @classmethod
    def _parse_lists(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v] if v else []
        return v or []
