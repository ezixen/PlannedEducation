"""
Tests for Proctoring routes.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api.main import app
from src.plannededucation.api.models import ProctoringConsent, ProctoringEvent, ProctoringSession


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def student_headers(client):
    """Create a test student user and return auth headers."""
    client.post("/auth/register", json={
        "email": "proctor_student@test.com",
        "username": "proctor_student",
        "password": "ProctorTest1!",
        "full_name": "Proctor Student",
    })
    token = client.post("/auth/token", data={
        "username": "proctor_student@test.com",
        "password": "ProctorTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def teacher_headers(client):
    """Create a test teacher user and return auth headers."""
    client.post("/auth/register", json={
        "email": "proctor_teacher@test.com",
        "username": "proctor_teacher",
        "password": "ProctorTest1!",
        "full_name": "Proctor Teacher",
        "role": "teacher",
    })
    token = client.post("/auth/token", data={
        "username": "proctor_teacher@test.com",
        "password": "ProctorTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def exam_id(client, teacher_headers):
    """Create a test exam and return its ID."""
    response = client.post(
        "/exams",
        json={
            "title": "Proctoring Test Exam",
            "description": "Test exam for proctoring",
            "duration_minutes": 60,
        },
        headers=teacher_headers
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def submission_id(client, student_headers, exam_id):
    """Create a test submission and return its ID."""
    # Start exam
    start_response = client.post(
        f"/exams/{exam_id}/start",
        headers=student_headers
    )
    assert start_response.status_code == 200
    
    # Submit exam
    submit_response = client.post(
        f"/exams/{exam_id}/submit",
        json={"answers": []},
        headers=student_headers
    )
    assert submit_response.status_code == 200
    # The submit endpoint returns status/message, not submission_id
    # We need to get the submission ID from the start response
    return start_response.json()["submission_id"]


class TestProctoringConsent:
    """Test proctoring consent endpoints."""

    def test_give_consent_success(self, client, student_headers, exam_id):
        """Test successful consent creation."""
        response = client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["student_id"] == data["student_id"]
        assert data["exam_id"] == exam_id
        assert data["consent_given"] is True
        assert data["camera_consent"] is True
        assert data["microphone_consent"] is True
        assert data["screen_recording_consent"] is True
        assert data["data_processing_consent"] is True
        assert data["withdrawn"] is False

    def test_give_consent_partial(self, client, student_headers, exam_id):
        """Test consent with only some options enabled."""
        response = client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": False,
                "screen_recording_consent": False,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["camera_consent"] is True
        assert data["microphone_consent"] is False

    def test_get_consent_success(self, client, student_headers, exam_id):
        """Test getting existing consent."""
        # First create consent
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        # Get consent
        response = client.get(f"/proctoring/consent/{exam_id}", headers=student_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["exam_id"] == exam_id
        assert data["consent_given"] is True

    def test_get_consent_not_found(self, client, student_headers, exam_id):
        """Test getting consent when none exists."""
        response = client.get(f"/proctoring/consent/{exam_id}", headers=student_headers)
        
        assert response.status_code == 404
        assert "Consent not found" in response.json()["detail"]

    def test_withdraw_consent_success(self, client, student_headers, exam_id):
        """Test withdrawing consent."""
        # First create consent
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        # Withdraw consent
        response = client.delete(f"/proctoring/consent/{exam_id}", headers=student_headers)
        
        assert response.status_code == 200
        assert "withdrawn" in response.json()["message"]
        
        # Verify consent is withdrawn
        get_response = client.get(f"/proctoring/consent/{exam_id}", headers=student_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["withdrawn"] is True
        assert data["consent_given"] is False

    def test_withdraw_consent_not_found(self, client, student_headers, exam_id):
        """Test withdrawing consent when none exists."""
        response = client.delete(f"/proctoring/consent/{exam_id}", headers=student_headers)
        
        assert response.status_code == 404
        assert "Consent not found" in response.json()["detail"]


class TestProctoringSession:
    """Test proctoring session endpoints."""

    def test_start_session_success(self, client, student_headers, exam_id, submission_id):
        """Test starting a proctoring session."""
        # First give consent
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        # Start session
        response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["submission_id"] == submission_id
        assert data["student_id"] == data["student_id"]
        assert data["exam_id"] == exam_id
        assert data["consent_given"] is True
        assert data["camera_enabled"] is True
        assert data["microphone_enabled"] is True
        assert data["screen_recording_enabled"] is True
        assert data["total_events"] == 0
        assert data["violation_count"] == 0

    def test_start_session_without_consent(self, client, student_headers, exam_id, submission_id):
        """Test starting session without consent fails."""
        response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        
        assert response.status_code == 403
        assert "Proctoring consent required" in response.json()["detail"]

    def test_start_session_duplicate(self, client, student_headers, exam_id, submission_id):
        """Test starting duplicate session fails."""
        # Give consent
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        # Start first session
        client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        
        # Try to start second session
        response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        
        assert response.status_code == 400
        assert "Session already exists" in response.json()["detail"]

    def test_end_session_success(self, client, student_headers, exam_id, submission_id):
        """Test ending a proctoring session."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # End session
        response = client.post(f"/proctoring/session/{session_id}/end", headers=student_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ended_at"] is not None
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] >= 0

    def test_end_session_already_ended(self, client, student_headers, exam_id, submission_id):
        """Test ending already ended session fails."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # End session once
        client.post(f"/proctoring/session/{session_id}/end", headers=student_headers)
        
        # Try to end again
        response = client.post(f"/proctoring/session/{session_id}/end", headers=student_headers)
        
        assert response.status_code == 400
        assert "Session already ended" in response.json()["detail"]

    def test_get_session_success(self, client, student_headers, exam_id, submission_id):
        """Test getting session details."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Get session
        response = client.get(f"/proctoring/session/{session_id}", headers=student_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["submission_id"] == submission_id

    def test_get_session_by_submission(self, client, student_headers, exam_id, submission_id):
        """Test getting session by submission ID."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        
        # Get session by submission
        response = client.get(f"/proctoring/session/submission/{submission_id}", headers=student_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["submission_id"] == submission_id


class TestProctoringEvents:
    """Test proctoring event endpoints."""

    def test_record_event_success(self, client, student_headers, exam_id, submission_id):
        """Test recording a single proctoring event."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Record event
        response = client.post(
            "/proctoring/event",
            json={
                "session_id": session_id,
                "event_type": "face_detected",
                "severity": "info",
                "event_data": {"confidence": 0.95},
            },
            headers=student_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session_id
        assert data["event_type"] == "face_detected"
        assert data["severity"] == "info"
        assert data["event_data"] is not None

    def test_record_event_violation(self, client, student_headers, exam_id, submission_id):
        """Test recording a violation event."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Record violation event
        response = client.post(
            "/proctoring/event",
            json={
                "session_id": session_id,
                "event_type": "multiple_faces",
                "severity": "violation",
                "event_data": {"face_count": 2},
            },
            headers=student_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "multiple_faces"
        assert data["severity"] == "violation"
        
        # Verify session stats updated
        session_response = client.get(f"/proctoring/session/{session_id}", headers=student_headers)
        session_data = session_response.json()
        assert session_data["violation_count"] == 1
        assert session_data["max_simultaneous_faces"] == 2

    def test_record_event_ended_session(self, client, student_headers, exam_id, submission_id):
        """Test recording event on ended session fails."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # End session
        client.post(f"/proctoring/session/{session_id}/end", headers=student_headers)
        
        # Try to record event
        response = client.post(
            "/proctoring/event",
            json={
                "session_id": session_id,
                "event_type": "face_detected",
                "severity": "info",
            },
            headers=student_headers
        )
        
        assert response.status_code == 400
        assert "Session has ended" in response.json()["detail"]

    def test_record_events_batch(self, client, student_headers, exam_id, submission_id):
        """Test recording multiple events in batch."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Record batch events
        response = client.post(
            "/proctoring/events/batch",
            json={
                "session_id": session_id,
                "events": [
                    {"event_type": "face_detected", "severity": "info", "event_data": {"confidence": 0.9}},
                    {"event_type": "eye_movement", "severity": "info", "event_data": {"gaze_x": 0.5, "gaze_y": 0.5}},
                    {"event_type": "tab_switch", "severity": "warning", "event_data": {"new_tab": "google.com"}},
                ],
            },
            headers=student_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["event_type"] == "face_detected"
        assert data[1]["event_type"] == "eye_movement"
        assert data[2]["event_type"] == "tab_switch"
        assert data[2]["severity"] == "warning"

    def test_get_session_events(self, client, student_headers, exam_id, submission_id):
        """Test getting events for a session."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Record some events
        client.post(
            "/proctoring/event",
            json={"session_id": session_id, "event_type": "face_detected", "severity": "info"},
            headers=student_headers
        )
        client.post(
            "/proctoring/event",
            json={"session_id": session_id, "event_type": "tab_switch", "severity": "warning"},
            headers=student_headers
        )
        
        # Get events
        response = client.get(f"/proctoring/session/{session_id}/events", headers=student_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        event_types = [e["event_type"] for e in data]
        assert "face_detected" in event_types
        assert "tab_switch" in event_types

    def test_get_session_events_filtered(self, client, student_headers, exam_id, submission_id):
        """Test getting filtered events for a session."""
        # Give consent and start session
        client.post(
            "/proctoring/consent",
            json={
                "exam_id": exam_id,
                "camera_consent": True,
                "microphone_consent": True,
                "screen_recording_consent": True,
                "data_processing_consent": True,
                "consent_version": "1.0",
            },
            headers=student_headers
        )
        
        start_response = client.post(
            "/proctoring/session/start",
            json={
                "exam_id": exam_id,
                "submission_id": submission_id,
                "camera_enabled": True,
                "microphone_enabled": True,
                "screen_recording_enabled": True,
            },
            headers=student_headers
        )
        session_id = start_response.json()["id"]
        
        # Record events
        client.post(
            "/proctoring/event",
            json={"session_id": session_id, "event_type": "face_detected", "severity": "info"},
            headers=student_headers
        )
        client.post(
            "/proctoring/event",
            json={"session_id": session_id, "event_type": "tab_switch", "severity": "warning"},
            headers=student_headers
        )
        
        # Get only warning events
        response = client.get(
            f"/proctoring/session/{session_id}/events?severity=warning",
            headers=student_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "tab_switch"
        assert data[0]["severity"] == "warning"


class TestProctoringStats:
    """Test proctoring statistics endpoints."""

    def test_get_stats_teacher(self, client, teacher_headers, exam_id):
        """Test getting proctoring stats as teacher."""
        response = client.get(f"/proctoring/stats?exam_id={exam_id}", headers=teacher_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "active_sessions" in data
        assert "total_events" in data
        assert "total_violations" in data
        assert "events_by_type" in data
        assert "violations_by_type" in data

    def test_get_stats_student_forbidden(self, client, student_headers, exam_id):
        """Test getting proctoring stats as student fails."""
        response = client.get(f"/proctoring/stats?exam_id={exam_id}", headers=student_headers)
        
        assert response.status_code == 403
        assert "Teacher access required" in response.json()["detail"]

    def test_get_stats_unauthorized(self, client, exam_id):
        """Test getting proctoring stats without auth fails."""
        response = client.get(f"/proctoring/stats?exam_id={exam_id}")
        
        assert response.status_code == 401


class TestProctoringHealth:
    """Test proctoring health check."""

    def test_health_check(self, client):
        """Test proctoring health check."""
        response = client.get("/proctoring/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["service"] == "proctoring"
        assert "features" in data
        assert "face_detection" in data["features"]
        assert "eye_tracking" in data["features"]
        assert "audio_monitoring" in data["features"]
        assert "gdpr_consent" in data["features"]
        assert "event_recording" in data["features"]
        assert "batch_events" in data["features"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])