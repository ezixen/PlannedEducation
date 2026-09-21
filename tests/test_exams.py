from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session

client = TestClient(app)

def test_create_exam_and_question():
    # 1. Setup mock teacher in DB
    db: Session = next(database.get_db())
    teacher_email = "math_teacher@school.edu"
    user = db.query(models.User).filter(models.User.email == teacher_email).first()
    if not user:
        user = models.User(email=teacher_email, google_id="mock_g_123", full_name="Math Teacher", role="teacher")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Generate token
    token = auth.create_access_token(data={"sub": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Exam
    exam_data = {
        "title": "Midterm Algebra",
        "description": "Chapters 1-3",
        "duration_minutes": 90
    }
    response = client.post("/exams/", json=exam_data, headers=headers)
    assert response.status_code == 200
    exam = response.json()
    assert exam["title"] == "Midterm Algebra"
    exam_id = exam["id"]

    # 4. Add Question
    question_data = {
        "question_type": "dynamic_math",
        "text": "Solve for x: 2x + 4 = 10",
        "points": 5
    }
    response = client.post(f"/exams/{exam_id}/questions", json=question_data, headers=headers)
    assert response.status_code == 200
    question = response.json()
    assert question["question_type"] == "dynamic_math"
    assert question["points"] == 5

    # 5. Get Exams
    response = client.get("/exams/", headers=headers)
    assert response.status_code == 200
    exams_list = response.json()
    assert len(exams_list) >= 1
    # Check if questions are nested in response
    assert len(exams_list[0]["questions"]) >= 1

def test_seb_security_rejection():
    # Setup mock student
    db: Session = next(database.get_db())
    student_email = "student@school.edu"
    user = db.query(models.User).filter(models.User.email == student_email).first()
    if not user:
        user = models.User(email=student_email, google_id="mock_g_stu", full_name="Math Student", role="student")
        db.add(user)
        db.commit()
        db.refresh(user)
        
    # Setup Exam with a config key
    exam = models.Exam(title="Locked Exam", teacher_id=1, seb_config_key="secret_hash_key_123")
    db.add(exam)
    db.commit()
    db.refresh(exam)
    
    token = auth.create_access_token(data={"sub": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Attempt to start exam WITHOUT the SEB Header
    response = client.post(f"/exams/{exam.id}/start", headers=headers)
    assert response.status_code == 403
    assert "Safe Exam Browser is required" in response.json()["detail"]
