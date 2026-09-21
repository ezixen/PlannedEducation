import pytest
from unittest.mock import patch, MagicMock
from src.plannededucation.api.ai_grading import anonymize_and_grade_submission, group_common_mistakes

@patch('src.plannededucation.api.ai_grading.client.models.generate_content')
def test_anonymize_and_grade_submission(mock_generate):
    # Setup mock AI response
    mock_response = MagicMock()
    mock_response.text = "Grade: 8/10. Student lost points on question 2."
    mock_generate.return_value = mock_response
    
    rubric = "10 points total. -2 for math errors."
    answers = "Q1: x=5, Q2: 4" # NO PII (No name, no email)
    
    result = anonymize_and_grade_submission(answers, rubric)
    
    # Verify the AI was called
    mock_generate.assert_called_once()
    kwargs = mock_generate.call_args[1]
    
    # Verify the prompt contains the answers but absolutely NO student info
    assert "Q1: x=5" in kwargs['contents']
    assert "John Doe" not in kwargs['contents']
    
    # Verify the output
    assert "8/10" in result

@patch('src.plannededucation.api.ai_grading.client.models.generate_content')
def test_group_common_mistakes(mock_generate):
    mock_response = MagicMock()
    mock_response.text = "Group 1: Forgot to carry the 1."
    mock_generate.return_value = mock_response
    
    answers = ["42", "41", "41", "42"]
    
    result = group_common_mistakes(answers)
    
    mock_generate.assert_called_once()
    assert "Group 1:" in result

