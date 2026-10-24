import base64
import enum
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow() is deprecated in Python 3.12+)."""
    return datetime.now(UTC)


# ── Enumerations ─────────────────────────────────────────────────────────────

class QuestionType(enum.StrEnum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"


class RelationshipStatus(enum.StrEnum):
    pending = "pending"
    active = "active"
    rejected = "rejected"


class UserRole(enum.StrEnum):
    student = "student"
    teacher = "teacher"
    parent = "parent"
    admin = "admin"


class ArchiveStatus(enum.StrEnum):
    active = "active"           # Currently stored on server
    archived = "archived"       # Moved to external storage
    deleted = "deleted"         # Removed from server (only external copy exists)


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    google_id = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(256), nullable=True)
    full_name = Column(String(128), nullable=True)
    phone_number = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(16), default='student', nullable=False)  # teacher, student, parent
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # 2FA
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)

    # Password Reset (self-service, email OTP or recovery codes)
    password_reset_otp = Column(String(128), nullable=True)
    password_reset_otp_expires = Column(DateTime(timezone=True), nullable=True)
    recovery_codes = Column(Text, nullable=True)  # JSON array of one-time recovery codes

    # AI Provider Settings — api_key stored ENCRYPTED via crypto.py
    ai_provider = Column(String(32), default="gemini")
    ai_api_key_encrypted = Column(Text, nullable=True)  # Renamed; plaintext never stored
    ai_model_name = Column(String(128), default="gemini-2.5-flash")
    ai_base_url = Column(String(512), nullable=True)

    # Refresh Tokens (for session management)
    refresh_token_hash = Column(String(256), nullable=True)  # Hashed refresh token
    refresh_token_expires = Column(DateTime(timezone=True), nullable=True)  # Expiry timestamp

    # WebAuthn / Passkeys (OWASP A07:2025)
    webauthn_credentials = Column(Text, nullable=True)  # JSON array of registered credentials
    webauthn_challenge = Column(String(256), nullable=True)  # Challenge for registration/auth
    webauthn_challenge_expires = Column(DateTime(timezone=True), nullable=True)  # Challenge expiry

    # Admin role
    is_admin = Column(Boolean, default=False, server_default="0", nullable=False)
    # Teacher approval (teachers who self-register require admin approval before accessing exams/modules)
    teacher_approved = Column(Boolean, default=True, server_default="1", nullable=False)

    # Classroom Emergency Password Reset (teachers can unlock student account right before tests)
    force_password_reset = Column(Boolean, default=False, server_default="0", nullable=False)
    reset_by_teacher_id = Column(String(36), nullable=True)
    reset_by_parent_id = Column(String(36), nullable=True)
    reset_by_admin_id = Column(String(36), nullable=True)
    reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Cybersecurity & Brute-Force Safeguards
    failed_login_attempts = Column(Integer, default=0, server_default="0", nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    exams = relationship("Exam", back_populates="teacher", cascade="all, delete-orphan")
    student_records = relationship(
        "StudentRecord",
        foreign_keys="[StudentRecord.student_id]",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    taught_courses = relationship(
        "Course", back_populates="teacher", cascade="all, delete-orphan"
    )
    class_groups = relationship(
        "ClassGroup", back_populates="teacher", cascade="all, delete-orphan"
    )
    packages = relationship("Package", back_populates="author", cascade="all, delete-orphan")
# User Sessions (for device tracking and "Remember Me")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """User session with device tracking for 'Remember Me' functionality."""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(256), nullable=False, index=True)
    token_encrypted = Column(Text, nullable=True)  # Encrypted session token
    device_id_hash = Column(String(256), nullable=True, index=True)  # Hashed device fingerprint
    device_info = Column(Text, nullable=True)  # JSON: browser, OS, IP, etc.
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    remember_me = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="sessions")


class AccountRelationship(Base):
    """
    Three-way handshake: parent requests to link to a student.
    The student must approve, and optionally a teacher must also approve.
    Only when all required parties have approved does is_active become True.
    """
    __tablename__ = "account_relationships"
    __table_args__ = (
        UniqueConstraint("student_id", "parent_id", name="uq_student_parent"),
    )

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    student_approved = Column(Boolean, default=False, nullable=False)
    parent_approved = Column(
        Boolean, default=True, nullable=False
    )  # Initiator is implicitly approved
    teacher_approved = Column(Boolean, default=False, nullable=False)

    status = Column(Enum(RelationshipStatus), default=RelationshipStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    student = relationship("User", foreign_keys=[student_id])
    parent = relationship("User", foreign_keys=[parent_id])
    teacher = relationship("User", foreign_keys=[teacher_id])


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(128), index=True, nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    teacher = relationship("User", back_populates="class_groups")


class StudentRecord(Base):
    """IEP / accommodation record for a student.

    Parent linkage is handled via AccountRelationship.
    """
    __tablename__ = "student_records"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # parent_id removed — use AccountRelationship for all parent/student links
    time_multiplier = Column(Float, default=1.0, nullable=False)

    student = relationship("User", foreign_keys=[student_id], back_populates="student_records")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    title = Column(String(256), index=True, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seb_config_key = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    teacher = relationship("User", back_populates="exams")
    questions = relationship(
        "Question", back_populates="exam", cascade="all, delete-orphan"
    )
    submissions = relationship(
        "ExamSubmission", back_populates="exam", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    exam_id = Column(String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)  # JSON array for multiple choice
    correct_answer = Column(Text, nullable=True)  # Never returned to students
    rubric = Column(Text, nullable=True)  # Grading rubric for AI (never returned to students)
    points = Column(Integer, default=1, nullable=False)

    exam = relationship("Exam", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_student_submission"),
    )

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    exam_id = Column(String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)

    exam = relationship("Exam", back_populates="submissions")
    student = relationship("User")
    answers = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    submission_id = Column(
        String(36),
        ForeignKey("exam_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_response = Column(Text, nullable=True)
    generated_question_text = Column(Text, nullable=True)
    generated_options_json = Column(Text, nullable=True)

    submission = relationship("ExamSubmission", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(128), index=True, nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    teacher = relationship("User", back_populates="taught_courses")


# ── Proctoring Models ────────────────────────────────────────────────────────

class ProctoringEventType(enum.StrEnum):
    """Types of proctoring events that can be recorded."""
    face_detected = "face_detected"
    face_lost = "face_lost"
    multiple_faces = "multiple_faces"
    eye_movement = "eye_movement"
    gaze_off_screen = "gaze_off_screen"
    audio_anomaly = "audio_anomaly"
    tab_switch = "tab_switch"
    window_blur = "window_blur"
    fullscreen_exit = "fullscreen_exit"
    seb_violation = "seb_violation"
    session_start = "session_start"
    session_end = "session_end"


class ProctoringSession(Base):
    """Proctoring session for an exam submission."""
    __tablename__ = "proctoring_sessions"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    submission_id = Column(
        String(36),
        ForeignKey("exam_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    student_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id = Column(
        String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )

    # GDPR Consent
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    consent_version = Column(String(32), nullable=True)

    # Session tracking
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Configuration
    camera_enabled = Column(Boolean, default=False, nullable=False)
    microphone_enabled = Column(Boolean, default=False, nullable=False)
    screen_recording_enabled = Column(Boolean, default=False, nullable=False)

    # Summary statistics
    total_events = Column(Integer, default=0, nullable=False)
    violation_count = Column(Integer, default=0, nullable=False)
    max_simultaneous_faces = Column(Integer, default=1, nullable=False)

    # Relationships
    submission = relationship("ExamSubmission")
    student = relationship("User")
    exam = relationship("Exam")
    events = relationship("ProctoringEvent", back_populates="session", cascade="all, delete-orphan")


class ProctoringEvent(Base):
    """Individual proctoring event recorded during a session."""
    __tablename__ = "proctoring_events"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    session_id = Column(
        String(36),
        ForeignKey("proctoring_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Event details
    event_type = Column(Enum(ProctoringEventType), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    severity = Column(String(16), default="info", nullable=False)  # info, warning, violation

    # Event data (JSON)
    event_data = Column(Text, nullable=True)  # JSON with event-specific data

    # Media references (optional)
    screenshot_ref = Column(String(256), nullable=True)  # Reference to stored screenshot
    audio_ref = Column(String(256), nullable=True)  # Reference to stored audio clip

    # Relationships
    session = relationship("ProctoringSession", back_populates="events")


class ProctoringConsent(Base):
    """GDPR consent record for proctoring."""
    __tablename__ = "proctoring_consents"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)

    # Consent details
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    consent_version = Column(String(32), nullable=False)

    # What was consented to
    camera_consent = Column(Boolean, default=False, nullable=False)
    microphone_consent = Column(Boolean, default=False, nullable=False)
    screen_recording_consent = Column(Boolean, default=False, nullable=False)
    data_processing_consent = Column(Boolean, default=False, nullable=False)

    # Withdrawal
    withdrawn = Column(Boolean, default=False, nullable=False)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("User")
    exam = relationship("Exam")

    __table_args__ = (
        UniqueConstraint("student_id", "exam_id", name="uq_student_exam_consent"),
    )


# ── Alert Models ─────────────────────────────────────────────────────────────

class AlertSeverity(enum.StrEnum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertStatus(enum.StrEnum):
    firing = "firing"
    resolved = "resolved"


# ── Package/Module Models ────────────────────────────────────────────────────

class PackageCategory(enum.StrEnum):
    """Standard module categories for the central repository."""
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


class PackageStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Package(Base):
    """Module package - a shareable, versioned exam package with metadata."""
    __tablename__ = "packages"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(256), index=True, nullable=False)
    version = Column(String(32), default="1.0.0", nullable=False)
    description = Column(Text, nullable=True)

    # Categorization
    category = Column(Enum(PackageCategory), default=PackageCategory.other, index=True, nullable=False)
    subject = Column(String(128), index=True, nullable=True)  # e.g., "Algebra I", "Organic Chemistry"
    grade_level = Column(String(32), index=True, nullable=True)  # e.g., "9", "10-12", "university"
    tags = Column(Text, nullable=True)  # JSON array of tags

    # Licensing
    license = Column(String(64), default="CC-BY-4.0", nullable=False)

    # Package content (JSON)
    package_data = Column(Text, nullable=False)  # Full package JSON
    checksum = Column(String(64), nullable=False)  # SHA-256 of package_data

    # Versioning
    version = Column(String(32), default="1.0.0", nullable=False)
    parent_package_id = Column(String(36), ForeignKey("packages.id"), nullable=True)  # For forks/updates

    # Ownership & Status
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(PackageStatus), default=PackageStatus.draft, index=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # Published to central repo

    # Source tracking
    source_url = Column(String(512), nullable=True)  # Original source (central repo, custom site, etc.)
    source_type = Column(String(32), nullable=True)  # "central", "custom", "local", "fork"

    # Statistics
    download_count = Column(Integer, default=0, nullable=False)
    rating_avg = Column(Float, nullable=True)
    rating_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    author = relationship("User", back_populates="packages")
    ratings = relationship("PackageRating", back_populates="package", cascade="all, delete-orphan")
    downloads = relationship("PackageDownload", back_populates="package", cascade="all, delete-orphan")
    parent = relationship("Package", remote_side=[id], backref="forks")


class PackageRating(Base):
    """User ratings for packages."""
    __tablename__ = "package_ratings"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    package_id = Column(String(36), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    review = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    package = relationship("Package", back_populates="ratings")
    user = relationship("User")


class PackageDownload(Base):
    """Track package downloads for statistics."""
    __tablename__ = "package_downloads"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    package_id = Column(String(36), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(32), nullable=True)  # "central", "custom", "direct"
    downloaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    ip_hash = Column(String(64), nullable=True)  # Hashed IP for privacy

    # Relationships
    package = relationship("Package", back_populates="downloads")
    user = relationship("User")


class School(Base):
    """School/organization for multi-tenant support."""
    __tablename__ = "schools"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(256), nullable=False)
    domain = Column(String(256), unique=True, index=True, nullable=True)  # School domain
    address = Column(Text, nullable=True)
    contact_email = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Header customization for school branding
    header_image_url = Column(String(512), nullable=True)  # URL to custom header image
    header_text = Column(String(256), nullable=True)  # Custom text shown instead of image
    header_display_mode = Column(String(32), default="text", nullable=False)  # "text", "image", "none"

    # Relationships
    package_sources = relationship("PackageSource", back_populates="school")


class PackageSource(Base):
    """Custom module sources configured by schools."""
    __tablename__ = "package_sources"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    url = Column(String(512), nullable=False)  # Base URL of the source
    api_key = Column(String(256), nullable=True)  # Optional API key for private sources
    source_type = Column(String(32), default="custom", nullable=False)  # "central", "custom", "github"
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # Show in default browse
    priority = Column(Integer, default=0, nullable=False)  # Display order

    # Sync settings
    auto_sync = Column(Boolean, default=False, nullable=False)
    sync_interval_hours = Column(Integer, default=24, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(32), nullable=True)  # "success", "error", "partial"
    last_sync_error = Column(Text, nullable=True)

    # Filtering
    allowed_categories = Column(Text, nullable=True)  # JSON array of categories to sync
    allowed_tags = Column(Text, nullable=True)  # JSON array of tags to sync

    # School ownership (for multi-tenant)
    school_id = Column(String(36), ForeignKey("schools.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    school = relationship("School", back_populates="package_sources")


class Alert(Base):
    """Alerts from Alertmanager."""
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    fingerprint = Column(String(64), index=True, nullable=False)  # Alertmanager fingerprint
    alertname = Column(String(128), index=True, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.firing, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.info, nullable=False)

    # Labels (JSON)
    labels_json = Column(Text, nullable=False)  # All labels as JSON

    # Annotations (JSON)
    annotations_json = Column(Text, nullable=True)  # All annotations as JSON

    # Timing
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    generator_url = Column(String(512), nullable=True)
    receiver = Column(String(64), nullable=True)
    group_key = Column(String(128), nullable=True)

    # Notification tracking
    notifications_sent = Column(Integer, default=0, nullable=False)
    last_notification_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        # Unique constraint on fingerprint + status to prevent duplicates
        UniqueConstraint("fingerprint", "status", name="uq_alert_fingerprint_status"),
    )


# ── Archive Models ───────────────────────────────────────────────────────────

class ArchivedSubmission(Base):
    """
    Compressed, encrypted archive of a sealed exam submission.
    Stored in year/month/teacher/student folder structure.
    """
    __tablename__ = "archived_submissions"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    submission_id = Column(String(36), unique=True, index=True, nullable=False)
    exam_id = Column(
        String(36), ForeignKey("exams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    teacher_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Archive metadata
    archive_year = Column(Integer, index=True, nullable=False)
    archive_month = Column(Integer, index=True, nullable=False)  # 1-12
    archive_path = Column(String(512), nullable=False)  # Relative path in archive storage

    # Compressed, encrypted data
    compressed_data = Column(Text, nullable=False)  # Base64 encoded compressed+encrypted blob
    original_size = Column(Integer, nullable=False)
    compressed_size = Column(Integer, nullable=False)
    compression_ratio = Column(Float, nullable=False)
    compression_algorithm = Column(String(32), default="zstd", nullable=False)

    # Encryption metadata
    encryption_algorithm = Column(String(32), default="AES-GCM", nullable=False)
    encryption_iv = Column(String(64), nullable=False)
    encryption_salt = Column(String(64), nullable=False)
    key_id = Column(String(128), nullable=False)

    # Integrity
    content_hash = Column(String(64), nullable=False)  # SHA-256 of original sealed submission
    archive_hash = Column(String(64), nullable=False)  # SHA-256 of compressed_data

    # Status
    status = Column(Enum(ArchiveStatus), default=ArchiveStatus.active, nullable=False)

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    deleted_from_server_at = Column(DateTime(timezone=True), nullable=True)

    # External storage reference (for off-site backup)
    external_storage_ref = Column(String(512), nullable=True)  # e.g., S3 key, USB drive ID

    # Relationships
    exam = relationship("Exam")
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])

    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_archived_submission"),
    )


class ArchiveJob(Base):
    """Background job for archiving graduated students' tests."""
    __tablename__ = "archive_jobs"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    job_type = Column(String(32), nullable=False)  # 'archive', 'restore', 'verify', 'cleanup'
    status = Column(String(32), default="pending", nullable=False)  # pending, running, etc.

    # Filters
    graduation_year: int = Column(Integer, nullable=True)
    teacher_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Progress
    total_items = Column(Integer, default=0, nullable=False)
    processed_items = Column(Integer, default=0, nullable=False)
    failed_items = Column(Integer, default=0, nullable=False)

    # Configuration
    archive_to_external = Column(Boolean, default=False, nullable=False)
    external_storage_path = Column(String(512), nullable=True)
    delete_after_archive = Column(Boolean, default=True, nullable=False)
    compression_level = Column(Integer, default=3, nullable=False)  # zstd level 1-22

    # Results
    result_summary = Column(Text, nullable=True)  # JSON summary
    error_log = Column(Text, nullable=True)  # JSON array of errors

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[teacher_id])


# ── In-App Notifications ─────────────────────────────────────────────────────

class InAppNotification(Base):
    """
    In-platform notification for user alerts, teacher status approvals,
    and password reset requests.
    """
    __tablename__ = "in_app_notifications"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(32), default="info", nullable=False)  # teacher_approval, password_reset_request, system, info
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    link = Column(String(256), nullable=True)  # Frontend navigation route/tab
    action_payload = Column(Text, nullable=True)  # JSON metadata (e.g. requester_id, request_id)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    recipient = relationship("User", foreign_keys=[user_id])
