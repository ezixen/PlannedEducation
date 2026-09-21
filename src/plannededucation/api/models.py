from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, Text
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
    
    student = relationship("User", foreign_keys=[student_id], back_populates="student_records")
    parent = relationship("User", foreign_keys=[parent_id])

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    teacher_id = Column(Integer, ForeignKey("users.id"))

    teacher = relationship("User", back_populates="taught_courses")

