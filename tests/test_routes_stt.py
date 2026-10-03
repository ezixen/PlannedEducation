"""
Tests for STT routes.
"""

import base64
import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api.main import app
from src.plannededucation.api.stt_service import TranscriptionResult, get_stt_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create a test user and return auth headers."""
    # Register a test user
    client.post("/auth/register", json={
        "email": "stt_test@test.com",
        "username": "stt_test",
        "password": "SttTest1!",
        "full_name": "STT Test User",
    })
    # Login to get token
    token = client.post("/auth/token", data={
        "username": "stt_test@test.com",
        "password": "SttTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_audio_base64():
    """Create a simple test audio as base64 (minimal WAV header)."""
    # Minimal WAV file (44 byte header + 1 second of silence at 8kHz)
    wav_header = (
        b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
        b'\x40\x1f\x00\x00\x40\x1f\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00'
    )
    return base64.b64encode(wav_header).decode()


@pytest.fixture
def mock_stt_service():
    """Create a mock STT service."""
    mock_stt = MagicMock()
    mock_stt.is_available.return_value = True
    return mock_stt


class TestSTTRoutes:
    """Test STT API endpoints."""

    def test_transcribe_audio_success(self, client, auth_headers, sample_audio_base64, mock_stt_service):
        """Test successful audio transcription."""
        mock_stt_service.transcribe_from_base64.return_value = TranscriptionResult(
            text="Hello world",
            language="en",
            language_probability=0.99,
            duration=1.5,
            segments=[{"id": 0, "start": 0.0, "end": 1.5, "text": "Hello world"}]
        )
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            response = client.post(
                "/stt/transcribe",
                json={"audio_base64": sample_audio_base64, "language": "en", "task": "transcribe"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Hello world"
            assert data["language"] == "en"
            assert data["language_probability"] == 0.99
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_audio_translate(self, client, auth_headers, sample_audio_base64, mock_stt_service):
        """Test audio translation to English."""
        mock_stt_service.transcribe_from_base64.return_value = TranscriptionResult(
            text="Hello world",
            language="en",
            language_probability=0.95,
            duration=2.0,
            segments=[{"id": 0, "start": 0.0, "end": 2.0, "text": "Hello world"}]
        )
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            response = client.post(
                "/stt/transcribe",
                json={"audio_base64": sample_audio_base64, "language": "es", "task": "translate"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Hello world"
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_audio_unavailable(self, client, auth_headers, sample_audio_base64):
        """Test STT when service is unavailable."""
        mock_stt = MagicMock()
        mock_stt.is_available.return_value = False
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt
        try:
            response = client.post(
                "/stt/transcribe",
                json={"audio_base64": sample_audio_base64, "language": "en", "task": "transcribe"},
                headers=auth_headers
            )
            
            assert response.status_code == 503
            assert "STT service not available" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_audio_upload(self, client, auth_headers, mock_stt_service):
        """Test STT with file upload."""
        mock_stt_service.transcribe.return_value = TranscriptionResult(
            text="Uploaded audio text",
            language="en",
            language_probability=0.90,
            duration=3.0,
            segments=[{"id": 0, "start": 0.0, "end": 3.0, "text": "Uploaded audio text"}]
        )
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            # Create a minimal WAV file
            wav_data = (
                b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
                b'\x40\x1f\x00\x00\x40\x1f\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00'
            )
            
            response = client.post(
                "/stt/transcribe-upload",
                files={"file": ("test.wav", wav_data, "audio/wav")},
                data={"language": "en", "task": "transcribe"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Uploaded audio text"
        finally:
            app.dependency_overrides.clear()

    def test_transcribe_batch(self, client, auth_headers, sample_audio_base64, mock_stt_service):
        """Test batch transcription."""
        mock_stt_service.transcribe_from_base64.return_value = TranscriptionResult(
            text="Batch audio",
            language="en",
            language_probability=0.88,
            duration=1.0,
            segments=[]
        )
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            response = client.post(
                "/stt/batch",
                json={"audios": [sample_audio_base64, sample_audio_base64], "language": "en", "task": "transcribe"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert all(r["text"] == "Batch audio" for r in data["results"])
        finally:
            app.dependency_overrides.clear()

    def test_get_languages(self, client, auth_headers, mock_stt_service):
        """Test getting supported languages."""
        mock_stt_service.get_supported_languages.return_value = ["en", "es", "fr", "de", "zh"]
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            response = client.get("/stt/languages", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "languages" in data
            assert "en" in data["languages"]
        finally:
            app.dependency_overrides.clear()

    def test_get_models(self, client):
        """Test getting available models (no auth required)."""
        response = client.get("/stt/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 5
        assert data["recommended"] == "base"

    def test_health_check(self, client, mock_stt_service):
        """Test STT health check (no auth required)."""
        mock_stt_service.model_size = "base"
        
        app.dependency_overrides[get_stt_service] = lambda: mock_stt_service
        try:
            response = client.get("/stt/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
            assert data["service"] == "faster-whisper"
            assert data["model"] == "base"
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])