from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_ocr_math_endpoint():
    db: Session = next(database.get_db())
    
    teacher_email = "ai_teacher@school.edu"
    teacher = db.query(models.User).filter(models.User.email == teacher_email).first()
    if not teacher:
        teacher = models.User(email=teacher_email, google_id="mock_g_ai_1", full_name="AI Teacher", role="teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})

    with patch('src.plannededucation.api.routes_ai.ai_client.get_ai_response') as mock_get_ai:
        mock_get_ai.return_value = "x = 5"

        file_data = b"dummy_image_data"
        files = {'file': ('math.jpg', file_data, 'image/jpeg')}
        
        response = client.post(
            "/ai/ocr-math", 
            headers={"Authorization": f"Bearer {teacher_token}"},
            files=files
        )
        
        assert response.status_code == 200
        assert response.json()["transcription"] == "x = 5"
        mock_get_ai.assert_called_once()
        assert "Transcribe this handwritten math" in mock_get_ai.call_args[0][1]

def test_speech_to_text_endpoint():
    db: Session = next(database.get_db())
    
    teacher_email = "ai_teacher@school.edu"
    teacher = db.query(models.User).filter(models.User.email == teacher_email).first()
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})

    with patch('src.plannededucation.api.routes_ai.ai_client.get_ai_response') as mock_get_ai:
        mock_get_ai.return_value = "Great job on the essay."

        file_data = b"dummy_audio_data"
        files = {'file': ('audio.mp3', file_data, 'audio/mpeg')}
        
        response = client.post(
            "/ai/speech-to-text", 
            headers={"Authorization": f"Bearer {teacher_token}"},
            files=files
        )
        
        assert response.status_code == 200
        assert response.json()["transcription"] == "Great job on the essay."


