from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database
from .routes_auth import get_current_user

router = APIRouter(prefix="/exams", tags=["exams"])

@router.post("/", response_model=schemas.ExamResponse)
def create_exam(
    exam: schemas.ExamCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can create exams")
        
    db_exam = models.Exam(**exam.model_dump(), teacher_id=current_user.id)
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam

@router.get("/", response_model=List[schemas.ExamResponse])
def get_exams(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role == schemas.RoleEnum.teacher:
        # Teachers see their own exams
        return db.query(models.Exam).filter(models.Exam.teacher_id == current_user.id).all()
    # Students would see exams assigned to them (for now return all for simplicity in MVP)
    return db.query(models.Exam).all()

@router.post("/{exam_id}/questions", response_model=schemas.QuestionResponse)
def create_question(
    exam_id: int,
    question: schemas.QuestionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can add questions")
        
    db_exam = db.query(models.Exam).filter(models.Exam.id == exam_id, models.Exam.teacher_id == current_user.id).first()
    if not db_exam:
        raise HTTPException(status_code=404, detail="Exam not found or you are not the owner")
        
    db_question = models.Question(**question.model_dump(), exam_id=exam_id)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

from .seb_security import verify_seb_request

@router.post("/{exam_id}/start")
def start_exam(
    exam_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    is_secure: bool = Depends(verify_seb_request)
):
    """
    This endpoint can ONLY be hit if the student is using a cryptographically verified Safe Exam Browser window.
    """
    if current_user.role != schemas.RoleEnum.student:
        raise HTTPException(status_code=403, detail="Only students can take exams")
        
    submission = models.ExamSubmission(
        exam_id=exam_id,
        student_id=current_user.id,
        started_at="NOW" # Simplified for MVP, use real UTC datetime
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"message": "Exam started securely in SEB", "submission_id": submission.id}
