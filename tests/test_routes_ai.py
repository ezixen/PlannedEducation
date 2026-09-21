from fastapi.testclient import TestClient
from src.plannededucation.api.main import app
from src.plannededucation.api import database, models, auth
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_ocr_math_endpoint():
    db: Session = next(database.get_db())
    
    # Setup mock teacher
    teacher_email = "ai_teacher@school.edu"
    teacher = db.query(models.User).filter(models.User.email == teacher_email).first()
    if not teacher:
        teacher = models.User(email=teacher_email, google_id="mock_g_ai_1", full_name="AI Teacher", role="teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})

    # Mock the Gemini client
    with patch('src.plannededucation.api.routes_ai.client.models.generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = "x = 5"
        mock_generate.return_value = mock_response

        # Create a dummy image file
        file_data = b"dummy_image_data"
        files = {'file': ('math.jpg', file_data, 'image/jpeg')}
        
        response = client.post(
            "/ai/ocr-math", 
            headers={"Authorization": f"Bearer {teacher_token}"},
            files=files
        )
        
        assert response.status_code == 200
        assert response.json()["transcription"] == "x = 5"
        
        # Verify Gemini was called
        mock_generate.assert_called_once()
        kwargs = mock_generate.call_args[1]
        assert kwargs['model'] == 'gemini-2.5-flash'
        # Ensure the prompt and the file bytes are in the contents
        contents = kwargs['contents']
        assert "Transcribe this handwritten math" in contents[0]

def test_speech_to_text_endpoint():
    db: Session = next(database.get_db())
    
    teacher_email = "ai_teacher@school.edu"
    teacher = db.query(models.User).filter(models.User.email == teacher_email).first()
    teacher_token = auth.create_access_token(data={"sub": teacher.email, "role": teacher.role})

    with patch('src.plannededucation.api.routes_ai.client.models.generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = "Great job on the essay."
        mock_generate.return_value = mock_response

        file_data = b"dummy_audio_data"
        files = {'file': ('audio.mp3', file_data, 'audio/mpeg')}
        
        response = client.post(
            "/ai/speech-to-text", 
            headers={"Authorization": f"Bearer {teacher_token}"},
            files=files
        )
        
        assert response.status_code == 200
        assert response.json()["transcription"] == "Great job on the essay."
