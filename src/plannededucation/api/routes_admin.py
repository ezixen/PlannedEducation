"""
Admin Routes for PlannedEducation
Endpoints for administrative operations (user management, exam oversight, system stats).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import database, models
from .routes_auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency to ensure the current user is an admin/teacher with admin privileges."""
    # For now, allow any teacher to access admin endpoints
    # In production, you might want a separate admin role
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get system-wide statistics for admin dashboard."""
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_exams = db.query(func.count(models.Exam.id)).scalar() or 0
    total_submissions = db.query(func.count(models.ExamSubmission.id)).scalar() or 0
    
    # Active exams = exams that have at least one submission in progress or recently started
    active_exams = (
        db.query(func.count(models.Exam.id))
        .join(models.ExamSubmission, models.Exam.id == models.ExamSubmission.exam_id)
        .filter(models.ExamSubmission.started_at.isnot(None))
        .filter(models.ExamSubmission.completed_at.is_(None))
        .scalar() or 0
    )
    
    return {
        "totalUsers": total_users,
        "totalExams": total_exams,
        "totalSubmissions": total_submissions,
        "activeExams": active_exams,
    }


@router.get("/users")
def get_admin_users(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get all users for admin management."""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
        for user in users
    ]


@router.patch("/users/{user_id}")
def update_admin_user(
    user_id: str,
    is_active: bool,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Activate or deactivate a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account")
    
    user.is_active = is_active
    db.commit()
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}


@router.delete("/users/{user_id}")
def delete_admin_user(
    user_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Delete a user (and all their data via cascade)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/exams")
def get_admin_exams(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get all exams for admin oversight."""
    exams = (
        db.query(
            models.Exam.id,
            models.Exam.title,
            models.Exam.teacher_id,
            models.User.full_name.label("teacher_name"),
            func.count(models.Question.id).label("question_count"),
            func.count(models.ExamSubmission.id).label("submission_count"),
            models.Exam.created_at,
        )
        .join(models.User, models.Exam.teacher_id == models.User.id)
        .outerjoin(models.Question, models.Exam.id == models.Question.exam_id)
        .outerjoin(models.ExamSubmission, models.Exam.id == models.ExamSubmission.exam_id)
        .group_by(models.Exam.id, models.User.full_name)
        .order_by(models.Exam.created_at.desc())
        .all()
    )
    
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "teacher_id": exam.teacher_id,
            "teacher_name": exam.teacher_name or "Unknown",
            "question_count": exam.question_count,
            "submission_count": exam.submission_count,
            "is_published": exam.submission_count > 0,  # Consider published if has submissions
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
        }
        for exam in exams
    ]


@router.delete("/exams/{exam_id}")
def delete_admin_exam(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Delete an exam (and all related data via cascade)."""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    db.delete(exam)
    db.commit()
    return {"message": "Exam deleted successfully"}