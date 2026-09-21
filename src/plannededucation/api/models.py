from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
import enum
from .database import Base

class RoleEnum(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    parent = "parent"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    role = Column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # 2FA / Security
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    
    # AI Provider Settings (For Teachers)
    ai_provider = Column(String, default="gemini") # gemini, openrouter, ollama, openai
    ai_api_key = Column(String, nullable=True) 
    ai_model_name = Column(String, default="gemini-2.5-flash")
    ai_base_url = Column(String, nullable=True)

    # Relationships
    student_records = relationship("StudentRecord", foreign_keys="[StudentRecord.student_id]", back_populates="student", cascade="all, delete")
    taught_courses = relationship("Course", back_populates="teacher")
    class_groups = relationship("ClassGroup", back_populates="teacher")

class ClassGroup(Base):
    __tablename__ = "class_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    
    teacher = relationship("User", back_populates="class_groups")

class StudentRecord(Base):
    __tablename__ = "student_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True) # The parent tied to this student
    time_multiplier = Column(Float, default=1.0) # IEP accommodations, e.g. 1.5x time
    
    student = relationship("User", foreign_keys=[student_id], back_populates="student_records")
    parent = relationship("User", foreign_keys=[parent_id])

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String)
    duration_minutes = Column(Integer, default=60)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    seb_config_key = Column(String, nullable=True) # SEB Config Hash
    
    questions = relationship("Question", back_populates="exam", cascade="all, delete")
    submissions = relationship("ExamSubmission", back_populates="exam", cascade="all, delete")

class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    dynamic_math = "dynamic_math"

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    question_type = Column(Enum(QuestionType), nullable=False)
    text = Column(String, nullable=False)
    options_json = Column(String, nullable=True) # JSON array for multiple choice
    correct_answer = Column(String, nullable=True)
    points = Column(Integer, default=1)
    
    exam = relationship("Exam", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete")

class ExamSubmission(Base):
    __tablename__ = "exam_submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(String) # ISO timestamp
    completed_at = Column(String, nullable=True)
    
    exam = relationship("Exam", back_populates="submissions")
    student = relationship("User")
    answers = relationship("Answer", back_populates="submission", cascade="all, delete")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("exam_submissions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    student_response = Column(Text, nullable=True) # Text for short/long/math, Option index for multiple choice
    
    # Store the actual text seen by the student in case of Dynamic Math or Scrambled Options
    generated_question_text = Column(Text, nullable=True)
    generated_options_json = Column(Text, nullable=True)

    submission = relationship("ExamSubmission", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    teacher_id = Column(Integer, ForeignKey("users.id"))

    teacher = relationship("User", back_populates="taught_courses")

