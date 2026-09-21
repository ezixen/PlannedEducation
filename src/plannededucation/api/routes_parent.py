from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from . import database, models, schemas
from .routes_auth import get_current_user

router = APIRouter(prefix="/parents", tags=["parents"])

@router.get("/children-progress")
def get_children_progress(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns the exam scores and feedback for all students tied to this parent.
    """
    if current_user.role != schemas.RoleEnum.parent:
        raise HTTPException(status_code=403, detail="Only parents can access this endpoint")

    # Find all student records linked to this parent
    records = db.query(models.StudentRecord).filter(models.StudentRecord.parent_id == current_user.id).all()
    
    result = []
    for record in records:
        student = record.student
        
        # Get all completed submissions for this student
        submissions = db.query(models.ExamSubmission).filter(
            models.ExamSubmission.student_id == student.id,
            models.ExamSubmission.completed_at != None
        ).all()
        
        exam_history = []
        for sub in submissions:
            exam_history.append({
                "exam_title": sub.exam.title,
                "completed_at": sub.completed_at,
                "score": "Pending", # AI/Teacher grades will populate this eventually
                "feedback": "No feedback yet."
            })
            
        result.append({
            "student_id": student.id,
            "student_name": student.full_name,
            "recent_exams": exam_history
        })

    return result
