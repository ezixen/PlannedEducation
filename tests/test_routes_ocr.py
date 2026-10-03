"""
Tests for OCR routes.
"""

import base64
import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.plannededucation.api.main import app
from src.plannededucation.api.ocr_service import OCRResult, get_ocr_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create a test user and return auth headers."""
    # Register a test user
    client.post("/auth/register", json={
        "email": "ocr_test@test.com",
        "username": "ocr_test",
        "password": "OcrTest1!",
        "full_name": "OCR Test User",
    })
    # Login to get token
    token = client.post("/auth/token", data={
        "username": "ocr_test@test.com",
        "password": "OcrTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_image_base64():
    """Create a simple test image as base64."""
    img = Image.new('RGB', (200, 100), color='white')
    # Add some text-like pattern
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Test 123", fill='black')
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def mock_ocr_service():
    """Create a mock OCR service."""
    mock_ocr = MagicMock()
    mock_ocr.is_available.return_value = True
    return mock_ocr


class TestOCRRoutes:
    """Test OCR API endpoints."""

    def test_process_ocr_success(self, client, auth_headers, sample_image_base64, mock_ocr_service):
        """Test successful OCR processing."""
        mock_ocr_service.extract_text_from_base64.return_value = OCRResult(
            text="Test 123",
            confidence=0.95,
            language="eng",
            bounding_boxes=[{'text': 'Test', 'confidence': 95, 'x': 10, 'y': 10, 'width': 30, 'height': 20}]
        )
        
        # Override the dependency
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            response = client.post(
                "/ocr/process",
                json={"image_base64": sample_image_base64, "language": "eng", "is_math": False},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Test 123"
            assert data["confidence"] == 0.95
            assert data["language"] == "eng"
        finally:
            app.dependency_overrides.clear()

    def test_process_ocr_math(self, client, auth_headers, sample_image_base64, mock_ocr_service):
        """Test math-specific OCR processing."""
        mock_ocr_service.extract_text_from_base64.return_value = OCRResult(
            text="2x + 4 = 10",
            confidence=0.90,
            language="eng",
            bounding_boxes=[]
        )
        
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            response = client.post(
                "/ocr/process",
                json={"image_base64": sample_image_base64, "language": "eng", "is_math": True},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "2x + 4 = 10"
        finally:
            app.dependency_overrides.clear()

    def test_process_ocr_unavailable(self, client, auth_headers, sample_image_base64):
        """Test OCR when service is unavailable."""
        mock_ocr = MagicMock()
        mock_ocr.is_available.return_value = False
        
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr
        try:
            response = client.post(
                "/ocr/process",
                json={"image_base64": sample_image_base64, "language": "eng", "is_math": False},
                headers=auth_headers
            )
            
            assert response.status_code == 503
            assert "OCR service not available" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_process_ocr_upload(self, client, auth_headers, mock_ocr_service):
        """Test OCR with file upload."""
        mock_ocr_service.extract_text.return_value = OCRResult(
            text="Uploaded text",
            confidence=0.85,
            language="eng",
            bounding_boxes=[]
        )
        
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            # Create a simple image file
            img = Image.new('RGB', (100, 50), color='white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            response = client.post(
                "/ocr/process-upload",
                files={"file": ("test.png", buffer, "image/png")},
                data={"language": "eng", "is_math": "false"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Uploaded text"
        finally:
            app.dependency_overrides.clear()

    def test_process_ocr_batch(self, client, auth_headers, sample_image_base64, mock_ocr_service):
        """Test batch OCR processing."""
        mock_ocr_service.extract_text_from_base64.return_value = OCRResult(
            text="Batch text",
            confidence=0.88,
            language="eng",
            bounding_boxes=[]
        )
        
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            response = client.post(
                "/ocr/batch",
                json={"images": [sample_image_base64, sample_image_base64], "language": "eng", "is_math": False},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert all(r["text"] == "Batch text" for r in data["results"])
        finally:
            app.dependency_overrides.clear()

    def test_get_languages(self, client, auth_headers, mock_ocr_service):
        """Test getting supported languages."""
        mock_ocr_service.get_supported_languages.return_value = ["eng", "fra", "deu", "spa"]
        
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            response = client.get("/ocr/languages", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "languages" in data
            assert "eng" in data["languages"]
        finally:
            app.dependency_overrides.clear()

    def test_health_check(self, client, mock_ocr_service):
        """Test OCR health check (no auth required)."""
        app.dependency_overrides[get_ocr_service] = lambda: mock_ocr_service
        try:
            response = client.get("/ocr/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
            assert data["service"] == "tesseract"
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])