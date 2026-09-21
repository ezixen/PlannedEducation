from . import ai_client, models

def anonymize_and_grade_submission(user: models.User, answers_text: str, rubric: str) -> str:
    """
    CRITICAL PRIVACY RULE: We ONLY pass the raw answers text.
    The student's name, email, and ID are completely stripped before calling this function.
    """
    prompt = f"""
    Please grade the following anonymized student answers strictly according to the rubric provided.
    
    RUBRIC:
    {rubric}
    
    ANONYMIZED STUDENT ANSWERS:
    {answers_text}
    
    Provide your grading in a structured, concise format, highlighting where points were lost.
    """
    try:
        return ai_client.get_ai_response(user, prompt)
    except Exception as e:
        return f"AI Grading failed: {str(e)}"

def group_common_mistakes(user: models.User, answers_batch: list[str]) -> str:
    """
    Takes an anonymized list of student answers across the whole class and asks the AI 
    to group them by common mathematical or logical mistakes.
    """
    prompt = f"""
    Analyze the following batch of anonymized student answers for a single question.
    Group them into 3-4 common mistake categories so the teacher can write one feedback 
    message for each group. Do not identify students, just the mistakes.
    
    BATCH ANSWERS:
    {answers_batch}
    """
    try:
        return ai_client.get_ai_response(user, prompt)
    except Exception as e:
        return f"AI Grouping failed: {str(e)}"

