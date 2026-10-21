
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import database, models, schemas
from .routes_auth import get_current_user

# ── Presidio PII Scrubber (Free, Open-Source) ────────────────────────────────
# Microsoft Presidio (MIT License) - scrubs PII from text before sending to external AI
try:
    from presidio_analyzer import AnalyzerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None

# Initialize Presidio engine (lazy initialization)
_analyzer = None

def _get_presidio_analyzer():
    """Lazy initialization of Presidio Analyzer engine."""
    global _analyzer
    if not PRESIDIO_AVAILABLE:
        return None
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer

ENTITY_MAPPING = {
    "PERSON": "[PERSON]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[PHONE]",
    "LOCATION": "[LOCATION]",
    "DATE_TIME": "[DATE]",
    "NRP": "[ID]",
    "CREDIT_CARD": "[CREDIT_CARD]",
    "IP_ADDRESS": "[IP]",
    "URL": "[URL]",
}

def _anonymize_spans(text: str, results) -> str:
    """
    Replace PII spans identified by AnalyzerEngine with clean privacy placeholders.
    Handles overlapping spans by prioritizing higher confidence scores.
    """
    if not text or not results:
        return text

    sorted_by_score = sorted(results, key=lambda r: (r.score, r.end - r.start), reverse=True)
    kept_spans = []
    for r in sorted_by_score:
        if not any(max(r.start, k.start) < min(r.end, k.end) for k in kept_spans):
            kept_spans.append(r)

    kept_spans.sort(key=lambda r: r.start, reverse=True)
    chars = list(text)
    for r in kept_spans:
        replacement = ENTITY_MAPPING.get(r.entity_type, f"[{r.entity_type}]")
        chars[r.start:r.end] = list(replacement)
    return "".join(chars)

def scrub_pii(text: str, language: str = "en") -> str:
    """
    Scrub PII from text using Microsoft Presidio Analyzer and native span redaction.
    Returns text with PII replaced by entity type placeholders.
    """
    if not text or not PRESIDIO_AVAILABLE:
        return text

    analyzer = _get_presidio_analyzer()
    if not analyzer:
        return text

    try:
        # Analyze text for PII entities
        results = analyzer.analyze(text=text, language=language)
        return _anonymize_spans(text, results)
    except Exception:
        # Fail open - return original text if scrubbing fails
        return text

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


@router.get("/exams/{exam_id}/submissions", response_model=list[dict])
def get_anonymized_submissions(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns anonymised exam submissions — student identity stripped AND PII scrubbed.
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
        parsed_question_grades = {}
        summary_feedback = sub.feedback
        if sub.feedback and sub.feedback.startswith("{"):
            try:
                import json
                fb_obj = json.loads(sub.feedback)
                if isinstance(fb_obj, dict) and "question_grades" in fb_obj:
                    summary_feedback = fb_obj.get("summary_feedback", "")
                    for qg in fb_obj.get("question_grades", []):
                        if isinstance(qg, dict) and "question_id" in qg:
                            parsed_question_grades[qg["question_id"]] = qg
            except Exception:
                pass

        anon_answers = []
        for ans in sub.answers:
            # Scrub PII from student response before sending to external AI
            scrubbed_response = scrub_pii(ans.student_response or "")
            saved_qg = parsed_question_grades.get(ans.question_id, {})
            anon_answers.append(
                {
                    "question_id": ans.question_id,
                    "question_type": ans.question.question_type,
                    "question_text": ans.generated_question_text or ans.question.text,
                    "student_response": scrubbed_response,
                    "points_possible": ans.question.points,
                    "correct_answer": ans.question.correct_answer,
                    "rubric": ans.question.rubric,
                    "saved_score": saved_qg.get("score"),
                    "saved_feedback": saved_qg.get("feedback"),
                    "saved_corrected_answer": saved_qg.get("corrected_answer"),
                }
            )

        anonymized_data.append(
            {
                "anonymous_student_ref": f"Student_{index + 1}",
                "submission_id": sub.id,  # Kept so AI can POST grades back
                "score": sub.score,
                "feedback": summary_feedback,
                "teacher_approved": sub.score is not None,
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
    Endpoint for posting AI-generated and teacher-corrected grades back to the system.
    Only the teacher who owns the exam may post grades for its submissions.
    """
    import json

    submission = _get_submission_and_verify_ownership(submission_id, current_user, db)

    if body.question_grades:
        submission.feedback = json.dumps(
            {
                "summary_feedback": body.feedback,
                "question_grades": [qg.model_dump() for qg in body.question_grades],
            }
        )
    else:
        submission.feedback = body.feedback

    if body.score is not None:
        submission.score = body.score

    db.commit()
    return {"status": "success", "message": "Grades and feedback saved"}

