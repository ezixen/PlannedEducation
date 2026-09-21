import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, Text, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from .database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow() is deprecated in Python 3.12+)."""
    return datetime.now(timezone.utc)


# ── Enumerations ─────────────────────────────────────────────────────────────

class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"


class RelationshipStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    rejected = "rejected"


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

    # 2FA
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)

    # AI Provider Settings — api_key stored ENCRYPTED via crypto.py
    ai_provider = Column(String(32), default="gemini")
    ai_api_key_encrypted = Column(Text, nullable=True)  # Renamed; plaintext never stored
    ai_model_name = Column(String(128), default="gemini-2.5-flash")
    ai_base_url = Column(String(512), nullable=True)

    # Relationships
    exams = relationship("Exam", back_populates="teacher", cascade="all, delete-orphan")
    student_records = relationship(
        "StudentRecord",
        foreign_keys="[StudentRecord.student_id]",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    taught_courses = relationship("Course", back_populates="teacher", cascade="all, delete-orphan")
    class_groups = relationship("ClassGroup", back_populates="teacher", cascade="all, delete-orphan")


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
    parent_approved = Column(Boolean, default=True, nullable=False)  # Initiator is implicitly approved
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
    """IEP / accommodation record for a student. Parent linkage is handled via AccountRelationship."""
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

    teacher = relationship("User", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    submissions = relationship("ExamSubmission", back_populates="exam", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    exam_id = Column(String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)   # JSON array for multiple choice
    correct_answer = Column(Text, nullable=True)  # Never returned to students
    rubric = Column(Text, nullable=True)          # Grading rubric for AI (never returned to students)
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
    submission_id = Column(String(36), ForeignKey("exam_submissions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
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
