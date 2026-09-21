from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth, schemas
from sqlalchemy.orm import Session
import json

client = TestClient(app)

def setup_test_users(db: Session):
    teacher = db.query(models.User).filter_by(email="teacher_exam@school.edu").first()
    if not teacher:
        teacher = models.User(email="teacher_exam@school.edu", google_id="mock_g_1", full_name="Exam Teacher", role="teacher")
        db.add(teacher)
        
    student = db.query(models.User).filter_by(email="student_exam@school.edu").first()
    if not student:
        student = models.User(email="student_exam@school.edu", google_id="mock_g_2", full_name="Exam Student", role="student")
        db.add(student)
        
    db.commit()
    db.refresh(teacher)
    db.refresh(student)
    return teacher, student

def test_create_and_get_exams():
    db: Session = next(database.get_db())
    teacher, student = setup_test_users(db)
    
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})
    
    # 1. Create Exam
    response = client.post(
        "/exams/", 
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"title": "Math Final", "description": "Hard test", "seb_config_key": "dummy_key"}
    )
    assert response.status_code == 200
    exam_id = response.json()["id"]
    
    # 2. Add Questions
    q_data = {
        "question_type": "dynamic_math",
        "text": "Solve: 2x = [rand:2-10]",
        "points": 10
    }
    response = client.post(
        f"/exams/{exam_id}/questions", 
        headers={"Authorization": f"Bearer {teacher_token}"},
        json=q_data
    )
    assert response.status_code == 200

    # 3. Get SEB Config
    response = client.get(f"/exams/{exam_id}/seb-config")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/seb"
    assert b"dummy_key" in response.content

def test_start_and_submit_exam():
    db: Session = next(database.get_db())
    teacher, student = setup_test_users(db)
    
    # Ensure there is an exam
    exam = db.query(models.Exam).filter_by(teacher_id=teacher.id).first()
    if not exam:
        exam = models.Exam(title="Math Final", description="Hard test", teacher_id=teacher.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        
        q = models.Question(exam_id=exam.id, question_type=models.QuestionType.dynamic_math, text="Solve: x = [rand:1-5]", points=5)
        db.add(q)
        db.commit()

    student_token = auth.create_access_token(data={"sub": student.email, "role": student.role})
    
    # Start Exam (Mocking SEB verification via FastAPI dependency override)
    from src.plannededucation.api.seb_security import verify_seb_request
    app.dependency_overrides[verify_seb_request] = lambda: True

    try:
        # If the student already started it in a previous test run, we need to handle it or clean DB.
        db.query(models.ExamSubmission).filter_by(student_id=student.id).delete()
        db.query(models.Answer).filter_by(submission_id=None).delete() # clean orphans if any
        db.commit()
        
        response = client.post(
            f"/exams/{exam.id}/start", 
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "submission_id" in data
        assert len(data["questions"]) > 0
        
        q_rendered = data["questions"][0]["text"]
        assert "[rand" not in q_rendered # Ensure math variables were resolved
        
        # Submit Exam
        submit_payload = [
            {"question_id": data["questions"][0]["question_id"], "response": "12"}
        ]
        
        response = client.post(
            f"/exams/{exam.id}/submit", 
            headers={"Authorization": f"Bearer {student_token}"},
            json=submit_payload
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        app.dependency_overrides.clear()
