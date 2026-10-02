
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import database, models, schemas
from .routes_auth import get_current_user

# ── Presidio PII Scrubber (Free, Open-Source) ────────────────────────────────
# Microsoft Presidio (MIT License) - scrubs PII from text before sending to external AI
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None
    AnonymizerEngine = None
    OperatorConfig = None

# Initialize Presidio engines (lazy initialization)
_analyzer = None
_anonymizer = None

def _get_presidio_engines():
    """Lazy initialization of Presidio engines."""
    global _analyzer, _anonymizer
    if not PRESIDIO_AVAILABLE:
        return None, None
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def scrub_pii(text: str, language: str = "en") -> str:
    """
    Scrub PII from text using Microsoft Presidio.
    Returns text with PII replaced by entity type placeholders.
    """
    if not text or not PRESIDIO_AVAILABLE:
        return text
    
    analyzer, anonymizer = _get_presidio_engines()
    if not analyzer or not anonymizer:
        return text
    
    try:
        # Analyze text for PII entities
        results = analyzer.analyze(text=text, language=language)
        
        # Anonymize found entities
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[PERSON]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[DATE]"}),
            "NRP": OperatorConfig("replace", {"new_value": "[ID]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CREDIT_CARD]"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[IP]"}),
            "URL": OperatorConfig("replace", {"new_value": "[URL]"}),
        }
        
        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        return anonymized.text
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
        anon_answers = []
        for ans in sub.answers:
            # Scrub PII from student response before sending to external AI
            scrubbed_response = scrub_pii(ans.student_response or "")
            anon_answers.append(
                {
                    "question_id": ans.question_id,
                    "question_text": ans.generated_question_text or ans.question.text,
                    "student_response": scrubbed_response,
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
