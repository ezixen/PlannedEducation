import random
import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database
from .routes_auth import get_current_user

router = APIRouter(prefix="/exams", tags=["exams"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_exam_or_404(exam_id: str, db: Session) -> models.Exam:
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def _require_exam_owner(exam: models.Exam, user: models.User) -> None:
    """Raise 403 if the user is not the exam's owner."""
    if exam.teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this exam",
        )


# ── Exam CRUD ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.ExamResponse, status_code=201)
def create_exam(
    exam: schemas.ExamCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_exam = models.Exam(**exam.model_dump(), teacher_id=current_user.id)
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam


@router.get("/", response_model=List[schemas.ExamListResponse])
def list_exams(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns METADATA ONLY — no questions, no answers, no rubrics.
    Safe for all authenticated users to browse available exams.
    """
    exams = db.query(models.Exam).all()
    return [schemas.ExamListResponse.model_validate(e) for e in exams]


@router.get("/mine", response_model=List[schemas.ExamResponse])
def list_my_exams(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns FULL exam data including questions and answers — only for the
    exams owned by the requesting user.
    """
    exams = (
        db.query(models.Exam)
        .filter(models.Exam.teacher_id == current_user.id)
        .all()
    )
    return [schemas.ExamResponse.model_validate(e) for e in exams]


@router.get("/{exam_id}", response_model=schemas.ExamResponse)
def get_exam(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Full exam detail — only accessible to the exam owner."""
    exam = _get_exam_or_404(exam_id, db)
    _require_exam_owner(exam, current_user)
    return exam


@router.delete("/{exam_id}", status_code=204)
def delete_exam(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = _get_exam_or_404(exam_id, db)
    _require_exam_owner(exam, current_user)
    db.delete(exam)
    db.commit()


# ── Questions ─────────────────────────────────────────────────────────────────

@router.post("/{exam_id}/questions", response_model=schemas.QuestionResponse, status_code=201)
def create_question(
    exam_id: str,
    question: schemas.QuestionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = _get_exam_or_404(exam_id, db)
    _require_exam_owner(exam, current_user)

    db_question = models.Question(**question.model_dump(), exam_id=exam_id)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


@router.delete("/{exam_id}/questions/{question_id}", status_code=204)
def delete_question(
    exam_id: str,
    question_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = _get_exam_or_404(exam_id, db)
    _require_exam_owner(exam, current_user)

    question = (
        db.query(models.Question)
        .filter(models.Question.id == question_id, models.Question.exam_id == exam_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()


# ── SEB Config ───────────────────────────────────────────────────────────────

@router.get("/{exam_id}/seb-config")
def generate_seb_config(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate and download a Safe Exam Browser (.seb) config file.
    Only the exam owner can generate this.
    """
    exam = _get_exam_or_404(exam_id, db)
    _require_exam_owner(exam, current_user)

    start_url = f"https://portal.plannededucation.org/exam/{exam_id}/start"

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>originatorVersion</key>
    <string>SEB_Win_3.7.0</string>
    <key>startURL</key>
    <string>{start_url}</string>
    <key>hashedQuitPassword</key>
    <string></string>
    <key>enableZoomPage</key>
    <true/>
    <key>browserWindowAllowReload</key>
    <false/>
    <key>examKey</key>
    <string>{exam.seb_config_key or ''}</string>
</dict>
</plist>"""

    return Response(
        content=xml_content,
        media_type="application/seb",
        headers={
            "Content-Disposition": f'attachment; filename="Exam_{exam_id}_Lock.seb"',
            "Cache-Control": "no-store",
        },
    )


# ── Exam Execution ───────────────────────────────────────────────────────────

from .seb_security import verify_seb_request


@router.post("/{exam_id}/start")
def start_exam(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    is_secure: bool = Depends(verify_seb_request),
):
    """
    Begin an exam session. SEB verification is required (bypassed in dev mode).
    Returns the student's personalised question set — NO correct answers included.
    """
    exam = _get_exam_or_404(exam_id, db)

    # Prevent duplicate submissions via DB unique constraint + application-level check
    existing_sub = (
        db.query(models.ExamSubmission)
        .filter(
            models.ExamSubmission.exam_id == exam_id,
            models.ExamSubmission.student_id == current_user.id,
        )
        .first()
    )
    if existing_sub:
        raise HTTPException(status_code=409, detail="You have already started this exam")

    submission = models.ExamSubmission(
        exam_id=exam.id,
        student_id=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    db.flush()  # Flush to get submission.id without committing yet

    questions = (
        db.query(models.Question).filter(models.Question.exam_id == exam_id).all()
    )

    # Randomise question selection (max 10 from pool)
    if len(questions) > 10:
        questions = random.sample(questions, 10)
    else:
        random.shuffle(questions)

    generated_questions = []
    for q in questions:
        q_text = q.text

        # Dynamic math: replace [rand:1-10] tokens with actual numbers
        if q.question_type == models.QuestionType.dynamic_math:
            def replace_rand(match: re.Match) -> str:
                lo, hi = map(int, match.group(1).split("-"))
                if lo > hi:
                    lo, hi = hi, lo
                return str(random.randint(lo, hi))

            q_text = re.sub(r"\[rand:(\d+-\d+)\]", replace_rand, q_text)

        # Scramble multiple-choice options
        scrambled_options = None
        if q.question_type == models.QuestionType.multiple_choice and q.options_json:
            try:
                opts = json.loads(q.options_json)
                if isinstance(opts, list):
                    random.shuffle(opts)
                    scrambled_options = json.dumps(opts)
            except (json.JSONDecodeError, TypeError):
                pass  # Malformed options_json; serve as-is

        ans = models.Answer(
            submission_id=submission.id,
            question_id=q.id,
            student_response="",
            generated_question_text=q_text,
            generated_options_json=scrambled_options,
        )
        db.add(ans)

        generated_questions.append(
            {
                "question_id": q.id,
                "question_type": q.question_type,
                "text": q_text,
                "options": json.loads(scrambled_options) if scrambled_options else None,
                "points": q.points,
                # correct_answer and rubric are deliberately excluded
            }
        )

    db.commit()

    return {
        "submission_id": submission.id,
        "questions": generated_questions,
    }


@router.post("/{exam_id}/submit")
def submit_exam(
    exam_id: str,
    body: schemas.ExamSubmitRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    is_secure: bool = Depends(verify_seb_request),
):
    """Submit answers for a running exam. Idempotency: raises 409 if already completed."""
    submission = (
        db.query(models.ExamSubmission)
        .filter(
            models.ExamSubmission.exam_id == exam_id,
            models.ExamSubmission.student_id == current_user.id,
        )
        .first()
    )

    if not submission:
        raise HTTPException(status_code=404, detail="No active submission found for this exam")
    if submission.completed_at is not None:
        raise HTTPException(status_code=409, detail="Exam has already been submitted")

    submission.completed_at = datetime.now(timezone.utc)

    for item in body.answers:
        ans = (
            db.query(models.Answer)
            .filter(
                models.Answer.question_id == item.question_id,
                models.Answer.submission_id == submission.id,
            )
            .first()
        )
        if ans:
            ans.student_response = item.response

    db.commit()
    return {"status": "success", "message": "Exam submitted successfully"}
