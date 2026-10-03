"""
Tests for Admin routes.
"""

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api.main import app
from src.plannededucation.api.routes_admin import require_admin


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers(client):
    """Create a test admin user and return auth headers."""
    # Register a test admin user (teacher role)
    client.post("/auth/register", json={
        "email": "admin_test@test.com",
        "username": "admin_test",
        "password": "AdminTest1!",
        "full_name": "Admin Test User",
        "role": "teacher",
    })
    # Login to get token
    token = client.post("/auth/token", data={
        "username": "admin_test@test.com",
        "password": "AdminTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_headers(client):
    """Create a test student user and return auth headers."""
    # Register a test student user
    client.post("/auth/register", json={
        "email": "student_test@test.com",
        "username": "student_test",
        "password": "StudentTest1!",
        "full_name": "Student Test User",
    })
    # Login to get token
    token = client.post("/auth/token", data={
        "username": "student_test@test.com",
        "password": "StudentTest1!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAdminRoutes:
    """Test Admin API endpoints."""

    def test_get_stats_success(self, client, admin_headers):
        """Test successful admin stats retrieval."""
        response = client.get("/admin/stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "totalUsers" in data
        assert "totalExams" in data
        assert "totalSubmissions" in data
        assert "activeExams" in data
        assert isinstance(data["totalUsers"], int)
        assert isinstance(data["totalExams"], int)

    def test_get_stats_forbidden_for_student(self, client, student_headers):
        """Test that students cannot access admin stats."""
        response = client.get("/admin/stats", headers=student_headers)
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_get_stats_unauthorized(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/admin/stats")
        
        assert response.status_code == 401

    def test_get_users_success(self, client, admin_headers):
        """Test successful admin users retrieval."""
        response = client.get("/admin/users", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include at least the admin user we created
        assert len(data) >= 1
        user = data[0]
        assert "id" in user
        assert "email" in user
        assert "username" in user
        assert "role" in user
        assert "is_active" in user

    def test_get_users_forbidden_for_student(self, client, student_headers):
        """Test that students cannot access admin users."""
        response = client.get("/admin/users", headers=student_headers)
        
        assert response.status_code == 403

    def test_update_user_active_status(self, client, admin_headers):
        """Test updating user active status."""
        # First get the list of users to find a student to modify
        users_response = client.get("/admin/users", headers=admin_headers)
        users = users_response.json()
        
        # Find a student user (not the admin)
        student_user = next((u for u in users if u["role"] == "student"), None)
        if not student_user:
            # Create a student user
            client.post("/auth/register", json={
                "email": "student_for_admin@test.com",
                "username": "student_for_admin",
                "password": "StudentTest1!",
                "full_name": "Student For Admin",
            })
            users_response = client.get("/admin/users", headers=admin_headers)
            users = users_response.json()
            student_user = next((u for u in users if u["role"] == "student"), None)
        
        assert student_user is not None
        
        # Deactivate the student
        response = client.patch(
            f"/admin/users/{student_user['id']}?is_active=false",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"]
        
        # Verify the change
        users_response = client.get("/admin/users", headers=admin_headers)
        users = users_response.json()
        updated_user = next((u for u in users if u["id"] == student_user["id"]), None)
        assert updated_user is not None
        assert updated_user["is_active"] is False
        
        # Reactivate the student
        response = client.patch(
            f"/admin/users/{student_user['id']}?is_active=true",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "activated" in response.json()["message"]

    def test_update_self_forbidden(self, client, admin_headers):
        """Test that admin cannot modify their own account."""
        # Get admin user ID
        me_response = client.get("/auth/me", headers=admin_headers)
        admin_id = me_response.json()["id"]
        
        response = client.patch(
            f"/admin/users/{admin_id}?is_active=false",
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "Cannot modify your own account" in response.json()["detail"]

    def test_delete_user_success(self, client, admin_headers):
        """Test deleting a user."""
        # Create a user to delete
        client.post("/auth/register", json={
            "email": "delete_me@test.com",
            "username": "delete_me",
            "password": "DeleteMe1!",
            "full_name": "Delete Me",
        })
        
        # Get the user ID
        users_response = client.get("/admin/users", headers=admin_headers)
        users = users_response.json()
        user_to_delete = next((u for u in users if u["username"] == "delete_me"), None)
        assert user_to_delete is not None
        
        # Delete the user
        response = client.delete(
            f"/admin/users/{user_to_delete['id']}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
        
        # Verify deletion
        users_response = client.get("/admin/users", headers=admin_headers)
        users = users_response.json()
        deleted_user = next((u for u in users if u["id"] == user_to_delete["id"]), None)
        assert deleted_user is None

    def test_delete_self_forbidden(self, client, admin_headers):
        """Test that admin cannot delete their own account."""
        me_response = client.get("/auth/me", headers=admin_headers)
        admin_id = me_response.json()["id"]
        
        response = client.delete(
            f"/admin/users/{admin_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    def test_get_exams_success(self, client, admin_headers):
        """Test successful admin exams retrieval."""
        response = client.get("/admin/exams", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            exam = data[0]
            assert "id" in exam
            assert "title" in exam
            assert "teacher_id" in exam
            assert "teacher_name" in exam
            assert "question_count" in exam
            assert "submission_count" in exam
            assert "is_published" in exam

    def test_get_exams_forbidden_for_student(self, client, student_headers):
        """Test that students cannot access admin exams."""
        response = client.get("/admin/exams", headers=student_headers)
        
        assert response.status_code == 403

    def test_delete_exam_success(self, client, admin_headers):
        """Test deleting an exam."""
        # Create an exam to delete
        exam_response = client.post(
            "/exams",
            json={
                "title": "Exam to Delete",
                "description": "Test exam for deletion",
                "duration_minutes": 60,
            },
            headers=admin_headers
        )
        assert exam_response.status_code == 201
        exam_id = exam_response.json()["id"]
        
        # Delete the exam
        response = client.delete(
            f"/admin/exams/{exam_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
        
        # Verify deletion
        exams_response = client.get("/admin/exams", headers=admin_headers)
        exams = exams_response.json()
        deleted_exam = next((e for e in exams if e["id"] == exam_id), None)
        assert deleted_exam is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])