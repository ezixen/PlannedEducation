"""
test_routes_anonymizer.py — anonymized submission access and AI grade posting.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models

client = TestClient(app)


def _register_and_token(email: str, username: str) -> str:
    client.post("/auth/register", json={"email": email, "username": username, "password": "Anon1234!", "full_name": "John Doe"})
    return client.post("/auth/token", data={"username": email, "password": "Anon1234!"}).json()["access_token"]


def _setup_exam_with_submission(db, teacher: models.User, student: models.User) -> tuple:
    exam = db.query(models.Exam).filter_by(teacher_id=teacher.id).first()
    if not exam:
        exam = models.Exam(title="Anon Exam", description="Test", teacher_id=teacher.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q = models.Question(
            exam_id=exam.id,
            question_type=models.QuestionType.essay,
            text="What is water?",
            correct_answer="H2O",
            rubric="Must mention H2O",
            points=5,
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        sub = models.ExamSubmission(
            exam_id=exam.id,
            student_id=student.id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        ans = models.Answer(
            submission_id=sub.id,
            question_id=q.id,
            student_response="Water is H2O",
        )
        db.add(ans)
        db.commit()

    return exam


def test_get_anonymized_submissions():
    db = next(database.get_db())
    teacher_token = _register_and_token("anon_teacher@test.com", "anon_teacher")
    student_token = _register_and_token("anon_student@test.com", "anon_student")
    teacher = db.query(models.User).filter_by(email="anon_teacher@test.com").first()
    student = db.query(models.User).filter_by(email="anon_student@test.com").first()

    exam = _setup_exam_with_submission(db, teacher, student)
    h = {"Authorization": f"Bearer {teacher_token}"}

    r = client.get(f"/anonymizer/exams/{exam.id}/submissions", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0

    submission_data = data[0]
    # Student identity must be stripped
    assert "anonymous_student_ref" in submission_data
    assert submission_data["anonymous_student_ref"].startswith("Student_")
    assert "anon_student@test.com" not in str(submission_data)
    assert student.full_name not in str(submission_data)

    # Actual answer content is retained for AI grading
    assert submission_data["answers"][0]["student_response"] == "Water is H2O"


def test_get_anonymized_submissions_non_owner_forbidden():
    db = next(database.get_db())
    teacher_token = _register_and_token("anon_teacher2@test.com", "anon_teacher2")
    student_token = _register_and_token("anon_student2@test.com", "anon_student2")
    other_token = _register_and_token("anon_other@test.com", "anon_other")
    teacher = db.query(models.User).filter_by(email="anon_teacher2@test.com").first()
    student = db.query(models.User).filter_by(email="anon_student2@test.com").first()

    exam = _setup_exam_with_submission(db, teacher, student)

    # Non-owner must be denied
    r = client.get(f"/anonymizer/exams/{exam.id}/submissions",
                   headers={"Authorization": f"Bearer {other_token}"})
    assert r.status_code in (403, 404)


def test_post_ai_grades_persists():
    db = next(database.get_db())
    teacher_token = _register_and_token("grade_teacher@test.com", "grade_teacher")
    student_token = _register_and_token("grade_student@test.com", "grade_student")
    teacher = db.query(models.User).filter_by(email="grade_teacher@test.com").first()
    student = db.query(models.User).filter_by(email="grade_student@test.com").first()

    exam = _setup_exam_with_submission(db, teacher, student)
    h = {"Authorization": f"Bearer {teacher_token}"}

    submission = db.query(models.ExamSubmission).filter_by(exam_id=exam.id, student_id=student.id).first()

    r = client.post(
        f"/anonymizer/submissions/{submission.id}/grades",
        headers=h,
        json={"feedback": "Excellent work!", "score": 95.0},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    # Verify it was actually persisted in the DB
    db.refresh(submission)
    assert submission.feedback == "Excellent work!"
    assert submission.score == 95.0


def test_post_ai_grades_idor_blocked():
    """A user who doesn't own the exam must not be able to write grades."""
    db = next(database.get_db())
    teacher_token = _register_and_token("grade_teacher3@test.com", "grade_teacher3")
    student_token = _register_and_token("grade_student3@test.com", "grade_student3")
    other_token = _register_and_token("grade_other3@test.com", "grade_other3")
    teacher = db.query(models.User).filter_by(email="grade_teacher3@test.com").first()
    student = db.query(models.User).filter_by(email="grade_student3@test.com").first()

    exam = _setup_exam_with_submission(db, teacher, student)
    submission = db.query(models.ExamSubmission).filter_by(exam_id=exam.id, student_id=student.id).first()

    r = client.post(
        f"/anonymizer/submissions/{submission.id}/grades",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"feedback": "Hacked grade!", "score": 100.0},
    )
    assert r.status_code == 403
