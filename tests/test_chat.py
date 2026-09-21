from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session
import json

client = TestClient(app)

def test_websocket_chat():
    db: Session = next(database.get_db())
    
    # 1. Setup mock student
    student_email = "chat_student@school.edu"
    student = db.query(models.User).filter(models.User.email == student_email).first()
    if not student:
        student = models.User(email=student_email, google_id="mock_g_chat_1", full_name="Chat Student", role="student")
        db.add(student)
        db.commit()
        db.refresh(student)

    # 2. Setup mock teacher
    teacher_email = "chat_teacher@school.edu"
    teacher = db.query(models.User).filter(models.User.email == teacher_email).first()
    if not teacher:
        teacher = models.User(email=teacher_email, google_id="mock_g_chat_2", full_name="Chat Teacher", role="teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

    # 3. Generate tokens
    student_token = auth.create_access_token(data={"sub": student.email, "role": student.role})
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})

    # 4. Connect both to the WebSocket room for Exam ID 99
    exam_id = 99
    
    with client.websocket_connect(f"/chat/exam/{exam_id}?token={student_token}") as student_ws:
        with client.websocket_connect(f"/chat/exam/{exam_id}?token={teacher_token}") as teacher_ws:
            
            # Student sends a message
            student_message = "Teacher, I don't understand question 2."
            student_ws.send_text(student_message)
            
            # Both should receive the broadcast
            student_recv = json.loads(student_ws.receive_text())
            teacher_recv = json.loads(teacher_ws.receive_text())
            
            assert student_recv["message"] == student_message
            assert student_recv["sender"] == "Chat Student"
            assert student_recv["role"] == "student"
            
            assert teacher_recv["message"] == student_message
            assert teacher_recv["sender"] == "Chat Student"
            
            # Teacher replies
            teacher_message = "I will come to your desk."
            teacher_ws.send_text(teacher_message)
            
            student_recv2 = json.loads(student_ws.receive_text())
            assert student_recv2["message"] == teacher_message
            assert student_recv2["sender"] == "Chat Teacher"
            assert student_recv2["role"] == "teacher"

def test_websocket_rejects_invalid_token():
    # Should close the connection if the token is garbage
    try:
        with client.websocket_connect("/chat/exam/99?token=invalid_garbage") as ws:
            pass # Should raise an exception or close immediately
    except Exception as e:
        # FastAPI TestClient raises WebSocketDisconnect on code 1008
        assert getattr(e, "code", None) == 1008 or "close" in str(e).lower()
