from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session

client = TestClient(app)

def setup_parent_data(db: Session):
    parent = db.query(models.User).filter_by(email="parent_test@school.edu").first()
    if not parent:
        parent = models.User(email="parent_test@school.edu", google_id="mock_g_parent_1", full_name="Dad Doe", role="parent")
        db.add(parent)
        
    student = db.query(models.User).filter_by(email="student_child@school.edu").first()
    if not student:
        student = models.User(email="student_child@school.edu", google_id="mock_g_child_1", full_name="Kid Doe", role="student")
        db.add(student)
        
    teacher = db.query(models.User).filter_by(email="teacher_p@school.edu").first()
    if not teacher:
        teacher = models.User(email="teacher_p@school.edu", google_id="mock_g_p_t", full_name="Teacher P", role="teacher")
        db.add(teacher)

    db.commit()
    db.refresh(parent)
    db.refresh(student)
    db.refresh(teacher)

    # Link parent to child
    record = db.query(models.StudentRecord).filter_by(student_id=student.id).first()
    if not record:
        record = models.StudentRecord(student_id=student.id, parent_id=parent.id)
        db.add(record)
        db.commit()

    # Create an exam and a completed submission for the child
    exam = db.query(models.Exam).filter_by(teacher_id=teacher.id).first()
    if not exam:
        exam = models.Exam(title="History Final", description="Hard test", teacher_id=teacher.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        
        sub = models.ExamSubmission(exam_id=exam.id, student_id=student.id, started_at="2026-01-01T12:00:00", completed_at="2026-01-01T13:00:00")
        db.add(sub)
        db.commit()

    return parent

def test_get_children_progress():
    db: Session = next(database.get_db())
    parent = setup_parent_data(db)
    
    parent_token = auth.create_access_token(data={"sub": parent.email, "role": parent.role})
    
    response = client.get(
        "/parents/children-progress", 
        headers={"Authorization": f"Bearer {parent_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    
    child_data = data[0]
    assert child_data["student_name"] == "Kid Doe"
    assert len(child_data["recent_exams"]) > 0
    assert child_data["recent_exams"][0]["exam_title"] == "History Final"
    assert child_data["recent_exams"][0]["score"] == "Pending"

