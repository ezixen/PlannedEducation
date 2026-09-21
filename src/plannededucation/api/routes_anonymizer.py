from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from . import database, models, schemas
from .routes_auth import get_current_user

router = APIRouter(prefix="/anonymizer", tags=["anonymizer"])

@router.get("/exams/{exam_id}/submissions", response_model=List[Dict])
def get_anonymized_submissions(
    exam_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Read-only API access for external AI services.
    Returns exam submissions but completely strips out student IDs, names, and emails.
    """
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can export data")

    exam = db.query(models.Exam).filter(models.Exam.id == exam_id, models.Exam.teacher_id == current_user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    submissions = db.query(models.ExamSubmission).filter(models.ExamSubmission.exam_id == exam_id).all()
    
    anonymized_data = []
    
    # Generate a temporary anonymous mapping (e.g. Student A, Student B) so the AI can group answers 
    # without knowing who they belong to.
    for index, sub in enumerate(submissions):
        anon_answers = []
        for ans in sub.answers:
            anon_answers.append({
                "question_id": ans.question_id,
                "question_text": ans.question.text,
                "student_response": ans.student_response,
                "points_possible": ans.question.points
            })
            
        anonymized_data.append({
            "anonymous_student_ref": f"Student_{index + 1}",
            "submission_id": sub.id, # We keep submission ID so the AI can POST grades back to this ID
            "answers": anon_answers
        })

    return anonymized_data

@router.post("/submissions/{submission_id}/grades")
def post_ai_grades(
    submission_id: int,
    feedback: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint for external AIs to push graded feedback files back to the system.
    """
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Unauthorized")

    submission = db.query(models.ExamSubmission).filter(models.ExamSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    # In a real app, save this feedback to a Grade model.
    # For now, we return success.
    return {"status": "success", "message": "Feedback attached successfully"}
