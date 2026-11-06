"""OCR Review Routes for PlannedEducation.

Endpoints for teacher review of OCR/handwriting recognition results.
Teacher can approve, correct, or reject OCR text before it proceeds
to anonymizer → AI grading pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models, schemas
from .routes_auth import get_current_user

router = APIRouter(prefix="/ocr/review", tags=["ocr-review"])


class OCRReviewListResponse(BaseModel):
    """Response model for listing OCR reviews."""
    id: str
    submission_id: str
    exam_id: str
    student_id: str
    student_name: str | None = None
    exam_title: str | None = None
    original_text: str
    original_confidence: float
    is_handwritten: bool
    status: str
    corrected_text: str | None = None
    reviewed_at: datetime | None = None
    anonymized: bool
    ai_graded: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[OCRReviewListResponse])
async def list_ocr_reviews(
    status_filter: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    List OCR reviews for the current teacher's exams.
    Only teachers can access reviews for their own exams.
    """
    query = db.query(models.OCRReview).join(models.Exam)

    # Teachers can only see reviews for their own exams
    if current_user.role == "teacher":
        query = query.filter(models.Exam.teacher_id == current_user.id)
    elif current_user.role in ("admin", "superadmin"):
        pass  # Admins can see all
    else:
        # Students/parents can only see their own submissions
        query = query.filter(models.OCRReview.student_id == current_user.id)

    if status_filter:
        query = query.filter(models.OCRReview.status == status_filter)

    reviews = query.order_by(models.OCRReview.created_at.desc()).all()

    results = []
    for review in reviews:
        student = db.query(models.User).filter(models.User.id == review.student_id).first()
        exam = db.query(models.Exam).filter(models.Exam.id == review.exam_id).first()
        results.append(OCRReviewListResponse(
            id=review.id,
            submission_id=review.submission_id,
            exam_id=review.exam_id,
            student_id=review.student_id,
            student_name=student.full_name if student else None,
            exam_title=exam.title if exam else None,
            original_text=review.original_text,
            original_confidence=review.original_confidence,
            is_handwritten=review.is_handwritten,
            status=review.status.value if hasattr(review.status, 'value') else review.status,
            corrected_text=review.corrected_text,
            reviewed_at=review.reviewed_at,
            anonymized=review.anonymized,
            ai_graded=review.ai_graded,
            created_at=review.created_at,
        ))

    return results


@router.get("/{review_id}", response_model=schemas.OCRReviewResponse)
async def get_ocr_review(
    review_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get a specific OCR review by ID."""
    review = db.query(models.OCRReview).filter(models.OCRReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="OCR review not found")

    # Permission check
    if current_user.role == "teacher" and review.exam.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this review")
    if current_user.role == "student" and review.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this review")

    return review


@router.post("/", response_model=schemas.OCRReviewResponse)
async def create_ocr_review(
    review_data: schemas.OCRReviewSubmit,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Submit OCR results for teacher review.
    Creates a new OCR review record with pending status.
    """
    # Verify the exam exists
    exam = db.query(models.Exam).filter(models.Exam.id == review_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Permission check - teachers can create reviews for their exams
    if current_user.role == "teacher" and exam.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create review for this exam")

    # Check if review already exists for this submission
    existing = db.query(models.OCRReview).filter(
        models.OCRReview.submission_id == review_data.submission_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="OCR review already exists for this submission")

    review = models.OCRReview(
        submission_id=review_data.submission_id,
        exam_id=review_data.exam_id,
        student_id=review_data.student_id,
        original_text=review_data.original_text,
        original_confidence=review_data.original_confidence,
        is_handwritten=review_data.is_handwritten,
        image_url=review_data.image_url,
        words_json=review_data.words_json,
        status=models.OCRReviewStatus.pending,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return review


@router.put("/{review_id}", response_model=schemas.OCRReviewResponse)
async def update_ocr_review(
    review_id: str,
    update_data: schemas.OCRReviewUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Update OCR review status (approve, correct, reject).
    Only teachers can update reviews for their own exams.
    """
    review = db.query(models.OCRReview).filter(models.OCRReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="OCR review not found")

    # Permission check
    if current_user.role == "teacher" and review.exam.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this review")

    # Update fields
    if update_data.status is not None:
        review.status = models.OCRReviewStatus(update_data.status)
    if update_data.corrected_text is not None:
        review.corrected_text = update_data.corrected_text
    if update_data.review_notes is not None:
        review.review_notes = update_data.review_notes

    if update_data.status in ("approved", "corrected", "rejected"):
        review.reviewed_at = datetime.now(UTC)
        review.teacher_id = current_user.id

    db.commit()
    db.refresh(review)

    return review


@router.post("/{review_id}/approve", response_model=schemas.OCRReviewResponse)
async def approve_ocr_review(
    review_id: str,
    approve_data: schemas.OCRReviewApprove,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Approve or correct OCR text.
    Once approved/corrected, the text can proceed to anonymizer → AI grading.
    """
    review = db.query(models.OCRReview).filter(models.OCRReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="OCR review not found")

    # Permission check
    if current_user.role == "teacher" and review.exam.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this review")

    review.status = models.OCRReviewStatus(approve_data.status)
    if approve_data.corrected_text is not None:
        review.corrected_text = approve_data.corrected_text
    if approve_data.review_notes is not None:
        review.review_notes = approve_data.review_notes

    if approve_data.status in ("approved", "corrected", "rejected"):
        review.reviewed_at = datetime.now(UTC)
        review.teacher_id = current_user.id

    db.commit()
    db.refresh(review)

    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ocr_review(
    review_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete an OCR review record."""
    review = db.query(models.OCRReview).filter(models.OCRReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="OCR review not found")

    # Permission check
    if current_user.role == "teacher" and review.exam.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")

    db.delete(review)
    db.commit()

    return None
