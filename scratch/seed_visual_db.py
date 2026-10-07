import json
import logging
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.abspath("."))
os.environ["DATABASE_URL"] = "sqlite:///./test_visual.db"
os.environ["PLANNED_EDUCATION_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "test_visual_jwt_secret_key_1234567890"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="

from src.plannededucation.api import database, models
from src.plannededucation.api.routes_auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.drop_all(bind=database.engine)
models.Base.metadata.create_all(bind=database.engine)

db = next(database.get_db())

# 1. Teacher
teacher = models.User(
    id="teacher-uuid-001",
    email="teacher@example.com",
    username="teacher",
    full_name="Prof. Sarah Jenkins",
    role="teacher",
    hashed_password=get_password_hash("password123"),
    is_active=True,
)
db.add(teacher)

# 2. Student
student = models.User(
    id="student-uuid-001",
    email="student@example.com",
    username="student",
    full_name="Alex Rivera",
    role="student",
    hashed_password=get_password_hash("password123"),
    is_active=True,
)
db.add(student)

# 3. Parent
parent = models.User(
    id="parent-uuid-001",
    email="parent@example.com",
    username="parent",
    full_name="Elena Rivera",
    role="parent",
    hashed_password=get_password_hash("password123"),
    is_active=True,
)
db.add(parent)

# 4. Disposable test user for destructive test
disposable = models.User(
    id="disposable-uuid-001",
    email="disposable@example.com",
    username="disposable_user",
    full_name="Temporary User",
    role="student",
    hashed_password=get_password_hash("password123"),
    is_active=True,
)
db.add(disposable)

# Commit users so foreign keys work
db.commit()

# 5. AccountRelationship (Parent -> Student, approved)
rel = models.AccountRelationship(
    student_id=student.id,
    parent_id=parent.id,
    teacher_id=teacher.id,
    student_approved=True,
    parent_approved=True,
    teacher_approved=True,
    status=models.RelationshipStatus.active,
)
db.add(rel)

# 6. ClassGroup
cls = models.ClassGroup(
    id="class-uuid-001",
    name="Grade 10 Biology - Period 3",
    teacher_id=teacher.id,
)
db.add(cls)

# 7. Exam
SAMPLE_EXAM_ID = "e8efa978-a1cd-481c-bd6b-83a1e05d8e00"
exam = models.Exam(
    id=SAMPLE_EXAM_ID,
    title="Biology Midterm Examination 2026",
    description="Cellular Biology, Genetics, and Plant Physiology midterm assessment.",
    duration_minutes=60,
    teacher_id=teacher.id,
)
db.add(exam)

# 8. Questions
q1 = models.Question(
    id="q-uuid-001",
    exam_id=SAMPLE_EXAM_ID,
    question_type=models.QuestionType.multiple_choice,
    text=(
        "Which cellular organelle is responsible for generating most of the "
        "chemical energy needed by the cell?"
    ),
    options_json=json.dumps([
        "Mitochondria",
        "Nucleus",
        "Ribosome",
        "Endoplasmic Reticulum",
    ]),
    correct_answer="Mitochondria",
    points=2,
)
q2 = models.Question(
    id="q-uuid-002",
    exam_id=SAMPLE_EXAM_ID,
    question_type=models.QuestionType.multiple_choice,
    text="What is the primary genetic molecule in eukaryotes?",
    options_json=json.dumps([
        "Deoxyribonucleic acid (DNA)",
        "Ribonucleic acid (RNA)",
        "Lipid bilayer",
        "Adenosine triphosphate",
    ]),
    correct_answer="Deoxyribonucleic acid (DNA)",
    points=2,
)
q3 = models.Question(
    id="q-uuid-003",
    exam_id=SAMPLE_EXAM_ID,
    question_type=models.QuestionType.essay,
    text=(
        "Summarize the core light-dependent reactions in photosynthesis and "
        "why water molecules are split."
    ),
    rubric=(
        "Student explains photosystem II, photolysis releasing oxygen, and "
        "electron transport generating ATP/NADPH."
    ),
    points=5,
)
db.add_all([q1, q2, q3])

# 9. ExamSubmission
sub = models.ExamSubmission(
    id="sub-uuid-001",
    exam_id=SAMPLE_EXAM_ID,
    student_id=student.id,
    started_at=datetime.now(UTC),
    score=88.5,
    feedback="Excellent understanding of cellular bio and genetics!",
)
db.add(sub)

# 10. Answers
a1 = models.Answer(
    submission_id=sub.id,
    question_id=q1.id,
    student_response="Mitochondria",
)
a2 = models.Answer(
    submission_id=sub.id,
    question_id=q2.id,
    student_response="Deoxyribonucleic acid (DNA)",
)
db.add_all([a1, a2])

# 11. ProctoringSession & Events
psess = models.ProctoringSession(
    id="psess-uuid-001",
    submission_id=sub.id,
    student_id=student.id,
    exam_id=SAMPLE_EXAM_ID,
    consent_given=True,
    camera_enabled=True,
    microphone_enabled=True,
    total_events=3,
    violation_count=0,
)
db.add(psess)

pe1 = models.ProctoringEvent(
    session_id=psess.id,
    event_type=models.ProctoringEventType.session_start,
    severity="info",
    event_data=json.dumps({"detail": "Exam started securely in safe browser environment"}),
)
pe2 = models.ProctoringEvent(
    session_id=psess.id,
    event_type=models.ProctoringEventType.face_detected,
    severity="info",
    event_data=json.dumps({"face_count": 1, "confidence": 0.98}),
)
db.add_all([pe1, pe2])

db.commit()
logger.info("Successfully seeded test_visual.db with complete multi-role records!")
