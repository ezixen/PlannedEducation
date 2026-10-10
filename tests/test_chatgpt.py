"""Tests for the teacher ChatGPT device-code OAuth gate and Responses API integration."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api.main import app
from src.plannededucation.chatgpt import models as chatgpt_models
from src.plannededucation.chatgpt import token_store
from src.plannededucation.chatgpt.history_store import (
    clear_all_for_tests as clear_history_for_tests,
)


def _make_fake_jwt(account_id: str = "acct_teacher_123") -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}).encode()
        )
        .decode()
        .rstrip("=")
    )
    return f"{header}.{payload}.sig"


@pytest.fixture(autouse=True)
def _clean_chatgpt_stores():
    token_store.clear_all_for_tests()
    clear_history_for_tests()
    chatgpt_models.clear_options_cache_for_tests()
    yield
    token_store.clear_all_for_tests()
    clear_history_for_tests()
    chatgpt_models.clear_options_cache_for_tests()


def _register_and_login(client: TestClient, email: str, role: str) -> dict[str, str]:
    username = email.split("@")[0]
    reg_res = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "StrongPassword123!",
            "full_name": f"Test {role.title()}",
            "role": role,
        },
    )
    assert reg_res.status_code in (200, 201, 400), reg_res.text
    res = client.post(
        "/auth/token",
        data={"username": email, "password": "StrongPassword123!"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_student_forbidden_from_chatgpt_gate():
    client = TestClient(app)
    headers = _register_and_login(client, "student_gpt_test@school.edu", "student")
    res = client.get("/chatgpt/session", headers=headers)
    assert res.status_code == 403


def test_teacher_chatgpt_device_login_and_chat_flow():
    client = TestClient(app)
    headers = _register_and_login(client, "teacher_gpt_test@school.edu", "teacher")

    # 1. Session starts disconnected
    sess = client.get("/chatgpt/session", headers=headers)
    assert sess.status_code == 200
    assert sess.json()["connected"] is False

    # 2. Fallback options returned when disconnected
    opts = client.get("/chatgpt/options", headers=headers)
    assert opts.status_code == 200
    assert opts.json()["default_model"] == "gpt-5.4-mini"

    # 3. Start device login
    with patch(
        "src.plannededucation.chatgpt.oauth.start_device_login",
        new=AsyncMock(
            return_value={
                "device_auth_id": "dev_auth_123",
                "user_code": "ABCD-1234",
                "interval_seconds": 5.0,
                "verification_uri": "https://auth.openai.com/codex/device",
                "verification_uri_complete": None,
            }
        ),
    ):
        start_res = client.post("/chatgpt/login/start", headers=headers)
        assert start_res.status_code == 200
        start_data = start_res.json()
        assert start_data["user_code"] == "ABCD-1234"
        login_id = start_data["login_id"]

    # 4. Poll pending then complete
    with patch(
        "src.plannededucation.chatgpt.oauth.poll_device_authorization",
        new=AsyncMock(return_value=None),
    ):
        poll_pending = client.post(
            "/chatgpt/login/poll",
            json={"login_id": login_id},
            headers=headers,
        )
        assert poll_pending.status_code == 200
        assert poll_pending.json()["status"] == "pending"

    fake_tokens = token_store.ChatGptTokens(
        access_token=_make_fake_jwt("acct_teacher_999"),
        refresh_token="ref_token_xyz",
        account_id="acct_teacher_999",
        expires_at=time.time() + 3600,
    )
    with (
        patch(
            "src.plannededucation.chatgpt.oauth.poll_device_authorization",
            new=AsyncMock(
                return_value={
                    "authorization_code": "auth_code_1",
                    "code_verifier": "verifier_1",
                }
            ),
        ),
        patch(
            "src.plannededucation.chatgpt.oauth.exchange_device_code",
            new=AsyncMock(return_value=fake_tokens),
        ),
    ):
        poll_done = client.post(
            "/chatgpt/login/poll",
            json={"login_id": login_id},
            headers=headers,
        )
        assert poll_done.status_code == 200
        assert poll_done.json()["status"] == "complete"

    # 5. Session is now connected
    sess_after = client.get("/chatgpt/session", headers=headers)
    assert sess_after.status_code == 200
    assert sess_after.json()["connected"] is True
    assert sess_after.json()["account_id"] == "acct_teacher_999"

    # 6. Send chat message and verify history
    with (
        patch(
            "src.plannededucation.chatgpt.models.fetch_codex_models",
            new=AsyncMock(return_value=chatgpt_models.fallback_snapshot()),
        ),
        patch(
            "src.plannededucation.chatgpt.client.create_response",
            new=AsyncMock(
                return_value="Grade suggestion: 9/10 — clear explanation of photosynthesis."
            ),
        ),
    ):
        chat_res = client.post(
            "/chatgpt/chat",
            json={
                "message": "Grade this anonymized answer on photosynthesis.",
                "model": "gpt-5.4-mini",
                "reasoning_effort": "medium",
                "verbosity": "medium",
            },
            headers=headers,
        )
        assert chat_res.status_code == 200
        assert "9/10" in chat_res.json()["reply"]

    hist_res = client.get("/chatgpt/history", headers=headers)
    assert hist_res.status_code == 200
    messages = hist_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # 7. Clear history and logout
    del_res = client.delete("/chatgpt/history", headers=headers)
    assert del_res.status_code == 204
    assert client.get("/chatgpt/history", headers=headers).json()["messages"] == []

    logout_res = client.post("/chatgpt/logout", headers=headers)
    assert logout_res.status_code == 204
    assert client.get("/chatgpt/session", headers=headers).json()["connected"] is False


def test_teacher_correction_and_student_side_by_side_comparison():
    client = TestClient(app)
    teacher_headers = _register_and_login(client, "teacher_math_corr@school.edu", "teacher")
    student_headers = _register_and_login(client, "student_math_corr@school.edu", "student")

    # 1. Teacher creates a Math exam with 2 questions
    create_res = client.post(
        "/exams/",
        json={
            "title": "Algebra & Arithmetic Assessment",
            "description": "Solve linear equations and show your steps.",
            "duration_minutes": 30,
        },
        headers=teacher_headers,
    )
    assert create_res.status_code == 201, create_res.text
    exam_data = create_res.json()
    exam_id = exam_data["id"]

    q1_res = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "question_type": "multiple_choice",
            "text": "What is the solution to 3x - 5 = 16?",
            "points": 5,
            "options": ["x = 5", "x = 7", "x = 9", "x = 11"],
            "correct_answer": "x = 7",
            "rubric": "Add 5 to both sides (3x = 21), then divide by 3 (x = 7).",
        },
        headers=teacher_headers,
    )
    assert q1_res.status_code == 201, q1_res.text

    q2_res = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "question_type": "essay",
            "text": "Solve 2(x + 4) = 18 and show your step-by-step work.",
            "points": 10,
            "correct_answer": "Step 1: 2x + 8 = 18\nStep 2: 2x = 10\nStep 3: x = 5",
            "rubric": "5 pts for expanding/dividing, 5 pts for final x = 5.",
        },
        headers=teacher_headers,
    )
    assert q2_res.status_code == 201, q2_res.text

    # 2. Student starts and submits the exam (Q1 right, Q2 has a subtraction error)
    start_res = client.post(f"/exams/{exam_id}/start", headers=student_headers)
    assert start_res.status_code == 200, start_res.text
    start_payload = start_res.json()
    sub_id = start_payload["submission_id"]
    questions = start_payload["questions"]
    q1_id = questions[0]["question_id"]
    q2_id = questions[1]["question_id"]

    submit_res = client.post(
        f"/exams/{exam_id}/submit",
        json={
            "submission_id": sub_id,
            "answers": [
                {"question_id": q1_id, "response": "x = 7"},
                {
                    "question_id": q2_id,
                    "response": (
                        "Step 1: 2x + 4 = 18 (forgot to multiply 4 by 2)\n"
                        "Step 2: 2x = 14\nStep 3: x = 7"
                    ),
                },
            ],
        },
        headers=student_headers,
    )
    assert submit_res.status_code == 200, submit_res.text

    # 3. Student checks their submission before teacher grades it
    pre_review = client.get(f"/exams/{exam_id}/my-submission", headers=student_headers)
    assert pre_review.status_code == 200, pre_review.text
    assert pre_review.json()["is_graded"] is False

    # 4. Teacher saves per-question corrections and scores
    grade_res = client.post(
        f"/anonymizer/submissions/{sub_id}/grades",
        json={
            "score": 10,
            "feedback": "Good effort! Review distribution in Question 2.",
            "question_grades": [
                {
                    "question_id": q1_id,
                    "score": 5,
                    "feedback": "Spot on! 3(7) - 5 = 16.",
                    "corrected_answer": "x = 7 (3x = 21 -> x = 7)",
                },
                {
                    "question_id": q2_id,
                    "score": 5,
                    "feedback": (
                        "Correct method after step 1, "
                        "but remember to distribute 2 to BOTH terms inside (x + 4)."
                    ),
                    "corrected_answer": (
                        "Correction of your Step 1: 2(x + 4) = 2x + 8 = 18 (not 2x + 4)\n"
                        "Step 2: Subtract 8 -> 2x = 10\n"
                        "Step 3: Divide by 2 -> x = 5"
                    ),
                },
            ],
        },
        headers=teacher_headers,
    )
    assert grade_res.status_code == 200, grade_res.text

    # 5. Student re-opens the exam and compares original vs teacher-corrected version side-by-side
    post_review = client.get(f"/exams/{exam_id}/my-submission", headers=student_headers)
    assert post_review.status_code == 200, post_review.text
    review_data = post_review.json()
    assert review_data["is_graded"] is True
    assert review_data["score"] == 10
    assert review_data["total_possible"] == 15
    q2_review = next(q for q in review_data["questions"] if q["question_id"] == q2_id)
    assert "2x + 4 = 18" in q2_review["student_response"]
    assert "2(x + 4) = 2x + 8 = 18" in q2_review["corrected_answer"]
    assert "distribute 2 to BOTH terms" in q2_review["teacher_feedback"]
