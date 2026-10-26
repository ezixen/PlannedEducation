"""
tests/test_ai_exam_creation_api.py
Comprehensive test suite verifying AI Exam Creation logic (POST /exams/ai-create):
1. Teacher authentication and atomic exam + question creation
2. Automatic array-to-JSON serialization for multiple-choice options
3. Automatic [AI-Assisted Draft] attribution tag with AI model metadata
4. Administrator authorization to create AI exams
5. Rejection of unauthorized roles (students / unapproved users -> 403 Forbidden)
6. Integrity of database relationships between created Exam and Questions
"""

import json
import os
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Fast in-memory SQLite for test isolation
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PLANNED_EDUCATION_ENV"] = "test"
os.environ["ALLOW_DEV_SEB_BYPASS"] = "true"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_1234567890"

from src.plannededucation.api import models, schemas
from src.plannededucation.api.routes_exam import ai_create_exam

test_engine = create_engine("sqlite:///:memory:")
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all database tables in memory for isolated fast testing."""
    models.Base.metadata.create_all(bind=test_engine)
    yield
    models.Base.metadata.drop_all(bind=test_engine)


def test_teacher_ai_create_exam_atomic():
    """An approved teacher can create an entire exam with questions atomically."""
    with TestSessionLocal() as db:
        teacher = models.User(
            email="ai_teacher@test.edu",
            username="aiteacher",
            full_name="AI Teacher",
            role="teacher",
            teacher_approved=True,
            is_active=True,
            hashed_password="mock_hashed_pw",
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

        payload = schemas.AIExamCreate(
            title="Introduction to Algorithms - Divide & Conquer",
            description="Generated exam on binary search, merge sort, and recurrences.",
            duration_minutes=50,
            ai_model_name="gemini-2.5-pro",
            questions=[
                schemas.AIQuestionCreate(
                    question_type="multiple_choice",
                    text="What is the worst-case asymptotic time complexity of standard Merge Sort?",
                    options=["O(N)", "O(N log N)", "O(N^2)", "O(2^N)"],
                    correct_answer="O(N log N)",
                    rubric="Option B is correct. Merge sort divides in log N levels and merges in O(N).",
                    points=5,
                ),
                schemas.AIQuestionCreate(
                    question_type="essay",
                    text="State the Master Theorem conditions and explain when it cannot be applied.",
                    options=None,
                    correct_answer=None,
                    rubric="Full credit for correctly defining T(n) = aT(n/b) + f(n).",
                    points=10,
                ),
            ],
        )

        exam = ai_create_exam(payload, db=db, current_user=teacher)

        assert exam.title == "Introduction to Algorithms - Divide & Conquer"
        assert "[AI-Assisted Draft | Model: gemini-2.5-pro]" in exam.description
        assert exam.teacher_id == teacher.id

        # Verify questions created in database
        questions = db.query(models.Question).filter(models.Question.exam_id == exam.id).all()
        assert len(questions) == 2

        # Check multiple choice serialization
        mc_q = next(q for q in questions if q.question_type.value == "multiple_choice")
        assert mc_q.options_json is not None
        opts = json.loads(mc_q.options_json)
        assert "O(N log N)" in opts
        assert mc_q.correct_answer == "O(N log N)"
        assert mc_q.points == 5

        # Check essay question
        essay_q = next(q for q in questions if q.question_type.value == "essay")
        assert essay_q.points == 10
        assert "Master Theorem" in essay_q.text


def test_student_rejected_from_ai_create():
    """Students cannot use the AI exam creation endpoint (must return 403 Forbidden)."""
    with TestSessionLocal() as db:
        student = models.User(
            email="ai_student@test.edu",
            username="aistudent",
            full_name="AI Student",
            role="student",
            teacher_approved=False,
            is_active=True,
            hashed_password="mock_hashed_pw",
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        payload = schemas.AIExamCreate(
            title="Unauthorized Student Exam Draft",
            description="Student trying to draft exam",
            duration_minutes=30,
            questions=[
                schemas.AIQuestionCreate(
                    question_type="essay",
                    text="Unauthorized question text.",
                    points=5,
                )
            ],
        )

        with pytest.raises(HTTPException) as exc_info:
            ai_create_exam(payload, db=db, current_user=student)

        assert exc_info.value.status_code == 403
        assert "Only teachers and administrators" in exc_info.value.detail


def test_admin_can_ai_create_exam():
    """An administrator can also create an AI exam draft."""
    with TestSessionLocal() as db:
        admin = models.User(
            email="ai_admin@test.edu",
            username="aiadmin",
            full_name="AI Administrator",
            role="admin",
            is_admin=True,
            teacher_approved=True,
            is_active=True,
            hashed_password="mock_hashed_pw",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        payload = schemas.AIExamCreate(
            title="Admin Diagnostic Exam",
            description="Schoolwide curriculum baseline",
            duration_minutes=45,
            ai_model_name="claude-3-5-sonnet",
            questions=[
                schemas.AIQuestionCreate(
                    question_type="multiple_choice",
                    text="What is the capital of Hungary?",
                    options=["Vienna", "Budapest", "Prague", "Warsaw"],
                    correct_answer="Budapest",
                    points=2,
                )
            ],
        )

        exam = ai_create_exam(payload, db=db, current_user=admin)
        assert exam.teacher_id == admin.id
        assert "[AI-Assisted Draft | Model: claude-3-5-sonnet]" in exam.description
