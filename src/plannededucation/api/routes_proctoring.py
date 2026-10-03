"""
Proctoring Routes for PlannedEducation
Endpoints for proctoring event pipeline, GDPR consent, and session management.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models
from .routes_auth import get_current_user

router = APIRouter(prefix="/proctoring", tags=["proctoring"])


# ── Pydantic Schemas ────────────────────────────────────────────────────────

class ProctoringConsentRequest(BaseModel):
    """Request model for proctoring consent."""
    exam_id: str = Field(..., description="Exam ID")
    camera_consent: bool = Field(default=False)
    microphone_consent: bool = Field(default=False)
    screen_recording_consent: bool = Field(default=False)
    data_processing_consent: bool = Field(default=False)
    consent_version: str = Field(default="1.0")


class ProctoringConsentResponse(BaseModel):
    """Response model for proctoring consent."""
    id: str
    student_id: str
    exam_id: str
    consent_given: bool
    consent_timestamp: datetime
    consent_version: str
    camera_consent: bool
    microphone_consent: bool
    screen_recording_consent: bool
    data_processing_consent: bool
    withdrawn: bool
    withdrawn_at: datetime | None = None


class ProctoringSessionStartRequest(BaseModel):
    """Request model for starting a proctoring session."""
    exam_id: str = Field(..., description="Exam ID")
    submission_id: str = Field(..., description="Exam submission ID")
    camera_enabled: bool = Field(default=False)
    microphone_enabled: bool = Field(default=False)
    screen_recording_enabled: bool = Field(default=False)


class ProctoringSessionResponse(BaseModel):
    """Response model for proctoring session."""
    id: str
    submission_id: str
    student_id: str
    exam_id: str
    consent_given: bool
    consent_timestamp: datetime | None = None
    consent_version: str | None = None
    camera_enabled: bool
    microphone_enabled: bool
    screen_recording_enabled: bool
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    total_events: int
    violation_count: int
    max_simultaneous_faces: int


class ProctoringEventRequest(BaseModel):
    """Request model for recording a proctoring event."""
    session_id: str | None = Field(default=None, description="Proctoring session ID (optional for batch requests)")
    event_type: str = Field(..., description="Event type")
    severity: str = Field(default="info", description="Severity: info, warning, violation")
    event_data: dict[str, Any] | None = Field(default=None)
    screenshot_ref: str | None = Field(default=None)
    audio_ref: str | None = Field(default=None)


class ProctoringEventResponse(BaseModel):
    """Response model for proctoring event."""
    id: str
    session_id: str
    event_type: str
    timestamp: datetime
    severity: str
    event_data: dict[str, Any] | None = None
    screenshot_ref: str | None = None
    audio_ref: str | None = None

    @classmethod
    def from_orm(cls, obj):
        """Parse JSON string event_data back to dict."""
        data = {
            "id": obj.id,
            "session_id": obj.session_id,
            "event_type": obj.event_type,
            "timestamp": obj.timestamp,
            "severity": obj.severity,
            "event_data": json.loads(obj.event_data) if obj.event_data else None,
            "screenshot_ref": obj.screenshot_ref,
            "audio_ref": obj.audio_ref,
        }
        return cls(**data)


class ProctoringEventBatchRequest(BaseModel):
    """Request model for batch event recording."""
    session_id: str = Field(..., description="Proctoring session ID")
    events: list[ProctoringEventRequest] = Field(..., description="List of events")


class ProctoringStatsResponse(BaseModel):
    """Response model for proctoring statistics."""
    total_sessions: int
    active_sessions: int
    total_events: int
    total_violations: int
    events_by_type: dict[str, int]
    violations_by_type: dict[str, int]


# ── Helper Functions ────────────────────────────────────────────────────────

def _get_session_and_verify(
    session_id: str,
    current_user: models.User,
    db: Session,
) -> models.ProctoringSession:
    """Fetch a proctoring session and verify access."""
    session = (
        db.query(models.ProctoringSession)
        .filter(models.ProctoringSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Proctoring session not found")

    # Students can only access their own sessions
    # Teachers can access sessions for their exams
    is_student_owner = current_user.role == "student" and session.student_id != current_user.id
    is_teacher_owner = current_user.role == "teacher" and session.exam.teacher_id != current_user.id
    if is_student_owner or is_teacher_owner:
        raise HTTPException(status_code=403, detail="Access denied")

    return session


# ── Consent Endpoints ──────────────────────────────────────────────────────

@router.post("/consent", response_model=ProctoringConsentResponse, status_code=201)
def give_consent(
    request: ProctoringConsentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Record GDPR consent for proctoring.
    Must be given before starting a proctored exam.
    """
    # Verify exam exists
    exam = db.query(models.Exam).filter(models.Exam.id == request.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Check if consent already exists
    existing = (
        db.query(models.ProctoringConsent)
        .filter(
            models.ProctoringConsent.student_id == current_user.id,
            models.ProctoringConsent.exam_id == request.exam_id
        )
        .first()
    )

    if existing:
        # Update existing consent
        existing.consent_given = True
        existing.consent_timestamp = datetime.now(UTC)
        existing.consent_version = request.consent_version
        existing.camera_consent = request.camera_consent
        existing.microphone_consent = request.microphone_consent
        existing.screen_recording_consent = request.screen_recording_consent
        existing.data_processing_consent = request.data_processing_consent
        existing.withdrawn = False
        existing.withdrawn_at = None
        db.commit()
        db.refresh(existing)
        return existing

    # Create new consent
    consent = models.ProctoringConsent(
        student_id=current_user.id,
        exam_id=request.exam_id,
        consent_given=True,
        consent_timestamp=datetime.now(UTC),
        consent_version=request.consent_version,
        camera_consent=request.camera_consent,
        microphone_consent=request.microphone_consent,
        screen_recording_consent=request.screen_recording_consent,
        data_processing_consent=request.data_processing_consent,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


@router.get("/consent/{exam_id}", response_model=ProctoringConsentResponse)
def get_consent(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get proctoring consent for an exam."""
    consent = (
        db.query(models.ProctoringConsent)
        .filter(
            models.ProctoringConsent.student_id == current_user.id,
            models.ProctoringConsent.exam_id == exam_id
        )
        .first()
    )
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    return consent


@router.delete("/consent/{exam_id}")
def withdraw_consent(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Withdraw proctoring consent (GDPR right to withdraw)."""
    consent = (
        db.query(models.ProctoringConsent)
        .filter(
            models.ProctoringConsent.student_id == current_user.id,
            models.ProctoringConsent.exam_id == exam_id
        )
        .first()
    )
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    consent.withdrawn = True
    consent.withdrawn_at = datetime.now(UTC)
    consent.consent_given = False
    db.commit()
    return {"status": "success", "message": "Consent withdrawn"}


# ── Session Endpoints ──────────────────────────────────────────────────────

@router.post("/session/start", response_model=ProctoringSessionResponse, status_code=201)
def start_session(
    request: ProctoringSessionStartRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Start a proctoring session for an exam submission.
    Requires valid consent.
    """
    # Verify submission exists and belongs to student
    submission = (
        db.query(models.ExamSubmission)
        .filter(
            models.ExamSubmission.id == request.submission_id,
            models.ExamSubmission.student_id == current_user.id
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify exam matches
    if submission.exam_id != request.exam_id:
        raise HTTPException(status_code=400, detail="Submission exam mismatch")

    # Check consent
    consent = (
        db.query(models.ProctoringConsent)
        .filter(
            models.ProctoringConsent.student_id == current_user.id,
            models.ProctoringConsent.exam_id == request.exam_id,
            models.ProctoringConsent.consent_given,
            models.ProctoringConsent.withdrawn.is_(False),
        )
        .first()
    )
    if not consent:
        raise HTTPException(status_code=403, detail="Proctoring consent required")

    # Check if session already exists
    existing = (
        db.query(models.ProctoringSession)
        .filter(models.ProctoringSession.submission_id == request.submission_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Session already exists for this submission")

    # Create session
    session = models.ProctoringSession(
        submission_id=request.submission_id,
        student_id=current_user.id,
        exam_id=request.exam_id,
        consent_given=True,
        consent_timestamp=consent.consent_timestamp,
        consent_version=consent.consent_version,
        camera_enabled=request.camera_enabled,
        microphone_enabled=request.microphone_enabled,
        screen_recording_enabled=request.screen_recording_enabled,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/session/{session_id}/end", response_model=ProctoringSessionResponse)
def end_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """End a proctoring session."""
    session = _get_session_and_verify(session_id, current_user, db)

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.ended_at = datetime.now(UTC)
    # Ensure both datetimes are timezone-aware for subtraction
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    session.duration_seconds = int((session.ended_at - started_at).total_seconds())
    db.commit()
    db.refresh(session)
    return session


@router.get("/session/{session_id}", response_model=ProctoringSessionResponse)
def get_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get proctoring session details."""
    session = _get_session_and_verify(session_id, current_user, db)
    return session


@router.get("/session/submission/{submission_id}", response_model=ProctoringSessionResponse)
def get_session_by_submission(
    submission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get proctoring session by submission ID."""
    session = (
        db.query(models.ProctoringSession)
        .filter(models.ProctoringSession.submission_id == submission_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify access
    is_student_owner = current_user.role == "student" and session.student_id != current_user.id
    is_teacher_owner = current_user.role == "teacher" and session.exam.teacher_id != current_user.id
    if is_student_owner or is_teacher_owner:
        raise HTTPException(status_code=403, detail="Access denied")

    return session


# ── Event Endpoints ────────────────────────────────────────────────────────

@router.post("/event", response_model=ProctoringEventResponse, status_code=201)
def record_event(
    request: ProctoringEventRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Record a single proctoring event."""
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for single event recording")
    session = _get_session_and_verify(request.session_id, current_user, db)

    # Verify session is active
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session has ended")

    # Create event
    event = models.ProctoringEvent(
        session_id=request.session_id,
        event_type=request.event_type,
        severity=request.severity,
        event_data=json.dumps(request.event_data) if request.event_data else None,
        screenshot_ref=request.screenshot_ref,
        audio_ref=request.audio_ref,
    )
    db.add(event)

    # Update session stats
    session.total_events += 1
    if request.severity == "violation":
        session.violation_count += 1

    # Track max simultaneous faces
    if request.event_type == "multiple_faces" and request.event_data:
        face_count = request.event_data.get("face_count", 1)
        session.max_simultaneous_faces = max(session.max_simultaneous_faces, face_count)

    db.commit()
    db.refresh(event)
    return ProctoringEventResponse.from_orm(event)


@router.post("/events/batch", response_model=list[ProctoringEventResponse])
def record_events_batch(
    request: ProctoringEventBatchRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Record multiple proctoring events in batch."""
    session = _get_session_and_verify(request.session_id, current_user, db)

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session has ended")

    events = []
    for event_req in request.events:
        event = models.ProctoringEvent(
            session_id=request.session_id,
            event_type=event_req.event_type,
            severity=event_req.severity,
            event_data=json.dumps(event_req.event_data) if event_req.event_data else None,
            screenshot_ref=event_req.screenshot_ref,
            audio_ref=event_req.audio_ref,
        )
        db.add(event)
        events.append(event)

        # Update session stats
        session.total_events += 1
        if event_req.severity == "violation":
            session.violation_count += 1

        if event_req.event_type == "multiple_faces" and event_req.event_data:
            face_count = event_req.event_data.get("face_count", 1)
            session.max_simultaneous_faces = max(session.max_simultaneous_faces, face_count)

    db.commit()
    for event in events:
        db.refresh(event)
    
    # Convert to response models with parsed event_data
    return [ProctoringEventResponse.from_orm(e) for e in events]


@router.get("/session/{session_id}/events", response_model=list[ProctoringEventResponse])
def get_session_events(
    session_id: str,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get events for a proctoring session."""
    _get_session_and_verify(session_id, current_user, db)

    query = db.query(models.ProctoringEvent).filter(
        models.ProctoringEvent.session_id == session_id
    )

    if event_type:
        query = query.filter(models.ProctoringEvent.event_type == event_type)
    if severity:
        query = query.filter(models.ProctoringEvent.severity == severity)

    events = (
        query.order_by(models.ProctoringEvent.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [ProctoringEventResponse.from_orm(e) for e in events]


# ── Statistics Endpoints ───────────────────────────────────────────────────

@router.get("/stats", response_model=ProctoringStatsResponse)
def get_proctoring_stats(
    exam_id: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get proctoring statistics (teacher only)."""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

    query = db.query(models.ProctoringSession)

    if exam_id:
        # Verify teacher owns exam
        exam = db.query(models.Exam).filter(
            models.Exam.id == exam_id,
            models.Exam.teacher_id == current_user.id
        ).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        query = query.filter(models.ProctoringSession.exam_id == exam_id)
    else:
        # Only sessions for teacher's exams
        teacher_exam_ids = db.query(models.Exam.id).filter(
            models.Exam.teacher_id == current_user.id
        ).subquery()
        query = query.filter(models.ProctoringSession.exam_id.in_(teacher_exam_ids))

    sessions = query.all()

    # Aggregate stats
    total_sessions = len(sessions)
    active_sessions = sum(1 for s in sessions if not s.ended_at)
    total_events = sum(s.total_events for s in sessions)
    total_violations = sum(s.violation_count for s in sessions)

    # Events by type
    events_by_type = {}
    violations_by_type = {}

    for session in sessions:
        for event in session.events:
            events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
            if event.severity == "violation":
                violations_by_type[event.event_type] = (
                    violations_by_type.get(event.event_type, 0) + 1
                )

    return ProctoringStatsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_events=total_events,
        total_violations=total_violations,
        events_by_type=events_by_type,
        violations_by_type=violations_by_type,
    )


@router.get("/health")
async def proctoring_health_check():
    """Health check for proctoring service."""
    return {
        "available": True,
        "service": "proctoring",
        "features": [
            "face_detection",
            "eye_tracking",
            "audio_monitoring",
            "gdpr_consent",
            "event_recording",
            "batch_events"
        ]
    }
