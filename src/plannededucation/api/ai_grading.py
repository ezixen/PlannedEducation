import os
from google import genai

# Setup Gemini API (Free Tier)
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY", "dummy_key_for_testing")
client = genai.Client(api_key=GENAI_API_KEY)

def anonymize_and_grade_submission(answers_text: str, rubric: str) -> str:
    """
    CRITICAL PRIVACY RULE: We ONLY pass the raw answers text.
    The student's name, email, and ID are completely stripped before calling this function.
    
    This function asks the free external AI to pre-grade the exam based on a rubric.
    """
    prompt = f"""
    You are an expert, objective teacher grading an exam.
    Please grade the following anonymized student answers strictly according to the rubric provided.
    
    RUBRIC:
    {rubric}
    
    ANONYMIZED STUDENT ANSWERS:
    {answers_text}
    
    Provide your grading in a structured, concise format, highlighting where points were lost.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI Grading failed: {str(e)}"

def group_common_mistakes(answers_batch: list[str]) -> str:
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
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI Grouping failed: {str(e)}"

