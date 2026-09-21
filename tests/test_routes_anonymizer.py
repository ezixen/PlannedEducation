from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session

client = TestClient(app)

def setup_anonymizer_data(db: Session):
    teacher = db.query(models.User).filter_by(email="anon_teacher@school.edu").first()
    if not teacher:
        teacher = models.User(email="anon_teacher@school.edu", google_id="mock_g_anon_1", full_name="Anon Teacher", role="teacher")
        db.add(teacher)
        
    student = db.query(models.User).filter_by(email="anon_student@school.edu").first()
    if not student:
        student = models.User(email="anon_student@school.edu", google_id="mock_g_anon_2", full_name="John Doe", role="student")
        db.add(student)
        
    db.commit()
    db.refresh(teacher)
    db.refresh(student)
    
    exam = db.query(models.Exam).filter_by(teacher_id=teacher.id).first()
    if not exam:
        exam = models.Exam(title="Anon Exam", description="Test", teacher_id=teacher.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        
        q = models.Question(exam_id=exam.id, question_type="essay", text="What is water?", points=5, rubric="Must mention H2O")
        db.add(q)
        db.commit()
        db.refresh(q)
        
        sub = models.ExamSubmission(exam_id=exam.id, student_id=student.id, started_at="2026-01-01T12:00:00")
        db.add(sub)
        db.commit()
        db.refresh(sub)
        
        ans = models.Answer(submission_id=sub.id, question_id=q.id, student_response="H2O")
        db.add(ans)
        db.commit()

    return teacher, exam

def test_get_anonymized_submissions():
    db: Session = next(database.get_db())
    teacher, exam = setup_anonymizer_data(db)
    
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})
    
    response = client.get(
        f"/anonymizer/exams/{exam.id}/submissions", 
        headers={"Authorization": f"Bearer {teacher_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    
    # CRITICAL PRIVACY CHECK
    submission_data = data[0]
    assert "anonymous_student_ref" in submission_data
    assert "John Doe" not in str(submission_data)
    assert "anon_student" not in str(submission_data)
    
    assert submission_data["answers"][0]["student_response"] == "H2O"

def test_post_ai_grades():
    db: Session = next(database.get_db())
    teacher, exam = setup_anonymizer_data(db)
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})
    
    submission = db.query(models.ExamSubmission).filter_by(exam_id=exam.id).first()
    
    response = client.post(
        f"/anonymizer/submissions/{submission.id}/grades", 
        headers={"Authorization": f"Bearer {teacher_token}"},
        params={"feedback": "Good job."}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
