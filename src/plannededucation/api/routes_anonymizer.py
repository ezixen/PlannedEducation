from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

from . import database, models, schemas
from .routes_auth import get_current_user

router = APIRouter(prefix="/anonymizer", tags=["anonymizer"])


def _get_submission_and_verify_ownership(
    submission_id: str,
    current_user: models.User,
    db: Session,
) -> models.ExamSubmission:
    """Fetch a submission and verify the requesting user owns the parent exam."""
    submission = (
        db.query(models.ExamSubmission)
        .filter(models.ExamSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Only the teacher who owns the exam may access any submission for it
    if submission.exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this submission",
        )
    return submission


@router.get("/exams/{exam_id}/submissions", response_model=List[Dict])
def get_anonymized_submissions(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns anonymised exam submissions — student identity stripped.
    Only accessible to the exam owner (teacher).
    """
    exam = (
        db.query(models.Exam)
        .filter(models.Exam.id == exam_id, models.Exam.teacher_id == current_user.id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found or access denied")

    submissions = (
        db.query(models.ExamSubmission)
        .filter(models.ExamSubmission.exam_id == exam_id)
        .all()
    )

    anonymized_data = []
    for index, sub in enumerate(submissions):
        anon_answers = []
        for ans in sub.answers:
            anon_answers.append(
                {
                    "question_id": ans.question_id,
                    "question_text": ans.generated_question_text or ans.question.text,
                    "student_response": ans.student_response,
                    "points_possible": ans.question.points,
                    "correct_answer": ans.question.correct_answer,
                    "rubric": ans.question.rubric,
                }
            )

        anonymized_data.append(
            {
                "anonymous_student_ref": f"Student_{index + 1}",
                "submission_id": sub.id,  # Kept so AI can POST grades back
                "answers": anon_answers,
            }
        )

    return anonymized_data


@router.post("/submissions/{submission_id}/grades")
def post_ai_grades(
    submission_id: str,
    body: schemas.AiGradeRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Endpoint for posting AI-generated grades back to the system.
    Only the teacher who owns the exam may post grades for its submissions.
    """
    submission = _get_submission_and_verify_ownership(submission_id, current_user, db)

    submission.feedback = body.feedback
    if body.score is not None:
        submission.score = body.score

    db.commit()
    return {"status": "success", "message": "Grades and feedback saved"}
