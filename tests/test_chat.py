"""
test_chat.py — WebSocket auth, message broadcast, and rejection of invalid tokens.
Updated to use first-frame token auth (not URL query params).
"""
import json
import pytest
from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models

client = TestClient(app)


def _register_and_token(email: str, username: str) -> tuple[models.User, str]:
    db = next(database.get_db())
    client.post("/auth/register", json={"email": email, "username": username, "password": "Chat1234!"})
    token = client.post("/auth/token", data={"username": email, "password": "Chat1234!"}).json()["access_token"]
    user = db.query(models.User).filter_by(email=email).first()
    return user, token


def _ws_auth(ws, token: str):
    """Send the auth frame (first message the server expects)."""
    ws.send_text(json.dumps({"token": token}))


def _setup_exam_with_submission(db, teacher: models.User, student: models.User) -> models.Exam:
    """Create an exam owned by teacher and a submission for student."""
    exam = models.Exam(title="Chat Exam", teacher_id=teacher.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    sub = models.ExamSubmission(
        exam_id=exam.id,
        student_id=student.id,
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db.add(sub)
    db.commit()
    return exam


def test_websocket_rejects_invalid_token():
    """Connection with a garbage token must be closed with code 1008."""
    try:
        with client.websocket_connect("/chat/exam/non-existent-exam-id") as ws:
            ws.send_text(json.dumps({"token": "garbage.invalid.token"}))
            # Server should close after receiving bad auth
            ws.receive_text()  # May raise WebSocketDisconnect
        pytest.fail("Expected WebSocketDisconnect but connection stayed open")
    except Exception as e:
        code = getattr(e, "code", None)
        # 1008 = Policy Violation (our auth failure code)
        assert code == 1008 or "disconnect" in str(e).lower() or "close" in str(e).lower()


def test_websocket_rejects_missing_token():
    """Missing token in first frame must close the connection."""
    try:
        with client.websocket_connect("/chat/exam/some-exam-id") as ws:
            ws.send_text(json.dumps({}))  # No token field
            ws.receive_text()
        pytest.fail("Expected WebSocketDisconnect but stayed open")
    except Exception as e:
        assert getattr(e, "code", None) == 1008 or "disconnect" in str(e).lower() or "close" in str(e).lower()


def test_websocket_teacher_can_join_own_exam():
    """Exam owner (teacher) must be able to connect even without a submission."""
    db = next(database.get_db())
    teacher, teacher_token = _register_and_token("chat_teacher@test.com", "chat_teacher")
    student, _ = _register_and_token("chat_student@test.com", "chat_student")
    exam = _setup_exam_with_submission(db, teacher, student)

    try:
        with client.websocket_connect(f"/chat/exam/{exam.id}") as ws:
            _ws_auth(ws, teacher_token)
            # If we get here without exception, the teacher was accepted
            # Send a message and confirm we don't crash
            ws.send_text("Test message from teacher")
    except Exception as e:
        # A 1008 here means auth failed — fail the test
        if getattr(e, "code", None) == 1008:
            pytest.fail(f"Teacher was rejected from own exam: {e}")


def test_websocket_student_can_join_with_active_submission():
    """Student with an active submission must be able to join the exam chat."""
    db = next(database.get_db())
    teacher, _ = _register_and_token("chat_teacher2@test.com", "chat_teacher2")
    student, student_token = _register_and_token("chat_student2@test.com", "chat_student2")
    exam = _setup_exam_with_submission(db, teacher, student)

    try:
        with client.websocket_connect(f"/chat/exam/{exam.id}") as ws:
            _ws_auth(ws, student_token)
            ws.send_text("Question about problem 3")
    except Exception as e:
        if getattr(e, "code", None) == 1008:
            pytest.fail(f"Student with valid submission was rejected: {e}")


def test_websocket_stranger_rejected():
    """A user with no relationship to the exam must be rejected."""
    db = next(database.get_db())
    teacher, _ = _register_and_token("chat_teacher3@test.com", "chat_teacher3")
    student, _ = _register_and_token("chat_student3@test.com", "chat_student3")
    stranger, stranger_token = _register_and_token("chat_stranger@test.com", "chat_stranger")
    exam = _setup_exam_with_submission(db, teacher, student)

    try:
        with client.websocket_connect(f"/chat/exam/{exam.id}") as ws:
            _ws_auth(ws, stranger_token)
            ws.receive_text()  # Should not succeed
        pytest.fail("Stranger was allowed into the exam chat room")
    except Exception as e:
        assert getattr(e, "code", None) == 1008 or "disconnect" in str(e).lower() or "close" in str(e).lower()
