"""Authenticated sealed offline sync endpoints (F-048).

POST /sync/submission — student uploads own sealed submission.
GET  /sync/submission/{submission_id} — student (own), exam teacher, or admin.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from . import database, models
from .routes_auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])

# Cap sealed JSON size to limit abuse / educational-record exfil balloons.
MAX_SEALED_SYNC_BYTES = 2 * 1024 * 1024  # 2 MiB


class SealedSyncMeta(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sync_hash: str = Field(..., alias="syncHash", min_length=8, max_length=128)


class SealedSyncSubmissionIn(BaseModel):
    """Minimal required fields from client SealedExamSubmission (camelCase)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    submission_id: str = Field(..., alias="submissionId", min_length=1, max_length=64)
    exam_id: str = Field(..., alias="examId", min_length=1, max_length=36)
    student_id: str = Field(..., alias="studentId", min_length=1, max_length=36)
    content_hash: str = Field(..., alias="contentHash", min_length=8, max_length=128)
    sync: SealedSyncMeta

    @field_validator("submission_id", "exam_id", "student_id", "content_hash")
    @classmethod
    def _strip_nonempty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("field must not be empty")
        return cleaned


class SealedSyncAck(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    submission_id: str = Field(..., alias="submissionId")
    exam_id: str = Field(..., alias="examId")
    student_id: str = Field(..., alias="studentId")
    content_hash: str = Field(..., alias="contentHash")
    sync_hash: str = Field(..., alias="syncHash")
    stored: bool = True


def _is_admin(user: models.User) -> bool:
    return bool(getattr(user, "is_admin", False) or user.role == "admin")


def _can_read_sealed(
    user: models.User,
    record: models.SealedSyncSubmission,
    exam: models.Exam | None,
) -> bool:
    if record.student_id == user.id:
        return True
    if _is_admin(user):
        return True
    if exam is not None and exam.teacher_id == user.id and user.role in {
        "teacher",
        "admin",
    }:
        return True
    return False


def _enforce_payload_size(raw_bytes: int) -> None:
    if raw_bytes > MAX_SEALED_SYNC_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Sealed submission exceeds maximum allowed size",
        )


@router.post("/submission", response_model=SealedSyncAck, status_code=status.HTTP_200_OK)
def upload_sealed_submission(
    request: Request,
    body: SealedSyncSubmissionIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> SealedSyncAck:
    """Store a sealed offline submission. Caller may only upload their own."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            _enforce_payload_size(int(content_length))
        except ValueError:
            pass

    # Fail closed: student_id in the sealed envelope must match the bearer.
    if body.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students may only sync their own sealed submissions",
        )
    if current_user.role == "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the exam student may upload a sealed submission",
        )

    exam = db.query(models.Exam).filter(models.Exam.id == body.exam_id).first()
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    # Preserve client camelCase extras (answers, encryption, timing, …).
    payload_dict: dict[str, Any] = body.model_dump(by_alias=True, mode="json")
    try:
        payload_text = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid sealed submission payload",
        ) from exc

    payload_bytes = len(payload_text.encode("utf-8"))
    _enforce_payload_size(payload_bytes)

    sync_hash = body.sync.sync_hash
    existing = (
        db.query(models.SealedSyncSubmission)
        .filter(models.SealedSyncSubmission.id == body.submission_id)
        .first()
    )
    if existing is not None:
        if existing.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submission id already owned by another student",
            )
        existing.exam_id = body.exam_id
        existing.content_hash = body.content_hash
        existing.sync_hash = sync_hash
        existing.payload_json = payload_text
        existing.payload_bytes = payload_bytes
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = models.SealedSyncSubmission(
            id=body.submission_id,
            exam_id=body.exam_id,
            student_id=current_user.id,
            content_hash=body.content_hash,
            sync_hash=sync_hash,
            payload_json=payload_text,
            payload_bytes=payload_bytes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return SealedSyncAck(
        submissionId=record.id,
        examId=record.exam_id,
        studentId=record.student_id,
        contentHash=record.content_hash,
        syncHash=record.sync_hash,
        stored=True,
    )


@router.get("/submission/{submission_id}")
def get_sealed_submission(
    submission_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return sealed payload to the owning student, exam teacher, or admin."""
    record = (
        db.query(models.SealedSyncSubmission)
        .filter(models.SealedSyncSubmission.id == submission_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sealed submission not found",
        )

    exam = db.query(models.Exam).filter(models.Exam.id == record.exam_id).first()
    if not _can_read_sealed(current_user, record, exam):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this sealed submission",
        )

    try:
        payload = json.loads(record.payload_json)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.exception("Corrupt sealed sync payload for %s", submission_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sealed submission could not be read",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sealed submission could not be read",
        )
    return payload
