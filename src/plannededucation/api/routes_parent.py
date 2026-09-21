from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import database, models
from .routes_auth import get_current_user

router = APIRouter(prefix="/parents", tags=["parents"])


@router.get("/children-progress")
def get_children_progress(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns exam scores and feedback for all students linked to the requesting
    user via an ACTIVE AccountRelationship (all three parties have approved).
    """
    # Only return data for fully-approved relationships
    relationships = (
        db.query(models.AccountRelationship)
        .filter(
            models.AccountRelationship.parent_id == current_user.id,
            models.AccountRelationship.status == models.RelationshipStatus.active,
        )
        .all()
    )

    if not relationships:
        return []

    result = []
    for rel in relationships:
        student = rel.student
        if not student:
            continue

        # Only return completed submissions
        submissions = (
            db.query(models.ExamSubmission)
            .filter(
                models.ExamSubmission.student_id == student.id,
                models.ExamSubmission.completed_at.isnot(None),
            )
            .all()
        )

        exam_history = [
            {
                "exam_title": sub.exam.title,
                "completed_at": sub.completed_at.isoformat() if sub.completed_at else None,
                "score": sub.score,
                "feedback": sub.feedback,
            }
            for sub in submissions
        ]

        result.append(
            {
                # Only expose the student's name and UUID — no email/phone
                "student_id": student.id,
                "student_name": student.full_name or student.username,
                "recent_exams": exam_history,
            }
        )

    return result


@router.post("/relationships/request", status_code=201)
def request_relationship(
    body: dict,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    A parent initiates a link request to a student (by student UUID).
    The student must then approve via /relationships/{id}/approve.
    """
    from . import schemas

    student_id: str = body.get("student_id", "")
    teacher_id: str | None = body.get("teacher_id")

    if not student_id:
        raise HTTPException(status_code=422, detail="student_id is required")

    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create a relationship with yourself")

    # Check for duplicate
    existing = (
        db.query(models.AccountRelationship)
        .filter(
            models.AccountRelationship.student_id == student_id,
            models.AccountRelationship.parent_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Relationship request already exists")

    rel = models.AccountRelationship(
        student_id=student_id,
        parent_id=current_user.id,
        teacher_id=teacher_id,
        parent_approved=True,   # Initiator implicitly approves
        student_approved=False,
        teacher_approved=(teacher_id is None),  # No teacher required → skip
        status=models.RelationshipStatus.pending,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return {"id": rel.id, "status": rel.status}


@router.post("/relationships/{rel_id}/approve")
def approve_relationship(
    rel_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Student or teacher approves a pending relationship.
    When all required approvals are collected, status becomes 'active'.
    """
    rel = db.query(models.AccountRelationship).filter(models.AccountRelationship.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")

    if rel.status == models.RelationshipStatus.rejected:
        raise HTTPException(status_code=409, detail="This relationship has been rejected")

    # Determine who is approving
    if current_user.id == rel.student_id:
        rel.student_approved = True
    elif current_user.id == rel.teacher_id:
        rel.teacher_approved = True
    else:
        raise HTTPException(status_code=403, detail="You are not a party to this relationship")

    # Activate if all required approvals are met
    teacher_ok = rel.teacher_approved or rel.teacher_id is None
    if rel.parent_approved and rel.student_approved and teacher_ok:
        rel.status = models.RelationshipStatus.active

    db.commit()
    return {"id": rel.id, "status": rel.status}


@router.post("/relationships/{rel_id}/reject")
def reject_relationship(
    rel_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Any party to the relationship can reject it."""
    rel = db.query(models.AccountRelationship).filter(models.AccountRelationship.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")

    is_party = current_user.id in {rel.student_id, rel.parent_id, rel.teacher_id}
    if not is_party:
        raise HTTPException(status_code=403, detail="You are not a party to this relationship")

    rel.status = models.RelationshipStatus.rejected
    db.commit()
    return {"id": rel.id, "status": rel.status}
