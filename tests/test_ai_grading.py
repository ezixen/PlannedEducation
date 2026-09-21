import pytest
from unittest.mock import patch, MagicMock
from src.plannededucation.api.ai_grading import anonymize_and_grade_submission, group_common_mistakes
from src.plannededucation.api.models import User

@patch('src.plannededucation.api.ai_grading.ai_client.get_ai_response')
def test_anonymize_and_grade_submission(mock_get_ai):
    mock_get_ai.return_value = "Grade: 8/10. Student lost points on question 2."
    
    dummy_user = User(ai_provider="gemini")
    rubric = "10 points total. -2 for math errors."
    answers = "Q1: x=5, Q2: 4" # NO PII
    
    result = anonymize_and_grade_submission(dummy_user, answers, rubric)
    
    mock_get_ai.assert_called_once()
    args = mock_get_ai.call_args[0]
    
    # Verify the prompt contains the answers but absolutely NO student info
    assert "Q1: x=5" in args[1]
    assert "John Doe" not in args[1]
    
    assert "8/10" in result

@patch('src.plannededucation.api.ai_grading.ai_client.get_ai_response')
def test_group_common_mistakes(mock_get_ai):
    mock_get_ai.return_value = "Group 1: Forgot to carry the 1."
    
    dummy_user = User(ai_provider="gemini")
    answers = ["42", "41", "41", "42"]
    
    result = group_common_mistakes(dummy_user, answers)
    
    mock_get_ai.assert_called_once()
    assert "Group 1:" in result

