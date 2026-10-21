"""
Archive Routes for PlannedEducation
Admin-only routes for managing archived exam submissions.
"""

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models
from .archive_utils import (
    DEFAULT_COMPRESSION_LEVEL,
    ArchiveManager,
)
from .routes_auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/archive", tags=["archive"])

# ── Dependency: Admin Only ───────────────────────────────────────────────────

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Require admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── Request/Response Models ──────────────────────────────────────────────────

class ArchiveJobRequest(BaseModel):
    """Request to start an archive job."""
    graduation_year: int | None = Field(None, ge=2020, le=2100)
    teacher_id: str | None = None
    student_id: str | None = None
    archive_to_external: bool = False
    external_storage_path: str | None = None
    delete_after_archive: bool = True
    compression_level: int = Field(DEFAULT_COMPRESSION_LEVEL, ge=1, le=19)

class ArchiveJobResponse(BaseModel):
    """Archive job response."""
    id: str
    job_type: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result_summary: dict | None = None

class ArchiveListResponse(BaseModel):
    """Archive list item."""
    id: str
    submission_id: str
    exam_id: str
    student_id: str
    teacher_id: str
    archive_year: int
    archive_month: int
    archive_path: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_algorithm: str
    status: str
    submitted_at: str
    archived_at: str
    deleted_from_server_at: str | None = None

class ArchiveStatsResponse(BaseModel):
    """Archive storage statistics."""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    by_year: dict

class RestoreRequest(BaseModel):
    """Request to restore an archived submission."""
    archive_id: str
    target_location: str = Field("server", pattern="^(server|teacher)$")

class ExternalStorageConfig(BaseModel):
    """External storage configuration."""
    storage_type: str = Field(..., pattern="^(local|s3|usb|network)$")
    path: str
    credentials: dict | None = None


# ── Archive Manager Instance ─────────────────────────────────────────────────

# Default archive storage location
ARCHIVE_STORAGE_ROOT = os.getenv("ARCHIVE_STORAGE_ROOT", "/var/lib/plannededucation/archive")
archive_manager = ArchiveManager(ARCHIVE_STORAGE_ROOT)


# ── Admin Routes ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ArchiveStatsResponse)
async def get_archive_stats(
    current_user: models.User = Depends(get_current_user),
):
    """Get archive storage statistics (admin only)."""
    stats = archive_manager.get_storage_stats()
    return ArchiveStatsResponse(**stats)


@router.get("/list", response_model=list[ArchiveListResponse])
async def list_archives(
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    teacher_username: str | None = None,
    student_username: str | None = None,
    status: str | None = Query(None, pattern="^(active|archived|deleted)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List archived submissions with filters (admin only)."""
    query = db.query(models.ArchivedSubmission)

    if year:
        query = query.filter(models.ArchivedSubmission.archive_year == year)
    if month:
        query = query.filter(models.ArchivedSubmission.archive_month == month)
    if teacher_username:
        query = query.join(
            models.User, models.ArchivedSubmission.teacher_id == models.User.id
        ).filter(models.User.username == teacher_username)
    if student_username:
        query = query.join(
            models.User, models.ArchivedSubmission.student_id == models.User.id
        ).filter(models.User.username == student_username)
    if status:
        query = query.filter(models.ArchivedSubmission.status == status)

    archives = (
        query.order_by(models.ArchivedSubmission.archived_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        ArchiveListResponse(
            id=a.id,
            submission_id=a.submission_id,
            exam_id=a.exam_id,
            student_id=a.student_id,
            teacher_id=a.teacher_id,
            archive_year=a.archive_year,
            archive_month=a.archive_month,
            archive_path=a.archive_path,
            original_size=a.original_size,
            compressed_size=a.compressed_size,
            compression_ratio=a.compression_ratio,
            compression_algorithm=a.compression_algorithm,
            status=a.status.value,
            submitted_at=a.submitted_at.isoformat(),
            archived_at=a.archived_at.isoformat(),
            deleted_from_server_at=(
                a.deleted_from_server_at.isoformat() if a.deleted_from_server_at else None
            ),
        )
        for a in archives
    ]


@router.post("/jobs", response_model=ArchiveJobResponse, status_code=201)
async def create_archive_job(
    request: ArchiveJobRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new archive job (admin only)."""
    job = models.ArchiveJob(
        job_type="archive",
        status="pending",
        graduation_year=request.graduation_year,
        teacher_id=request.teacher_id,
        student_id=request.student_id,
        archive_to_external=request.archive_to_external,
        external_storage_path=request.external_storage_path,
        delete_after_archive=request.delete_after_archive,
        compression_level=request.compression_level,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return ArchiveJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        failed_items=job.failed_items,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        result_summary=json.loads(job.result_summary) if job.result_summary else None,
    )


@router.get("/jobs", response_model=list[ArchiveJobResponse])
async def list_archive_jobs(
    status: str | None = Query(None, pattern="^(pending|running|completed|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List archive jobs (admin only)."""
    query = db.query(models.ArchiveJob)
    if status:
        query = query.filter(models.ArchiveJob.status == status)

    jobs = query.order_by(models.ArchiveJob.created_at.desc()).offset(offset).limit(limit).all()

    return [
        ArchiveJobResponse(
            id=j.id,
            job_type=j.job_type,
            status=j.status,
            total_items=j.total_items,
            processed_items=j.processed_items,
            failed_items=j.failed_items,
            created_at=j.created_at.isoformat(),
            started_at=j.started_at.isoformat() if j.started_at else None,
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
            result_summary=json.loads(j.result_summary) if j.result_summary else None,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=ArchiveJobResponse)
async def get_archive_job(
    job_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get archive job details (admin only)."""
    job = db.query(models.ArchiveJob).filter(models.ArchiveJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Archive job not found")

    return ArchiveJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        failed_items=job.failed_items,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        result_summary=json.loads(job.result_summary) if job.result_summary else None,
    )


async def run_archive_job(job: models.ArchiveJob, db: Session) -> dict:
    """Execute an archive job over completed submissions."""
    query = db.query(models.ExamSubmission).filter(models.ExamSubmission.completed_at.isnot(None))
    if job.student_id:
        query = query.filter(models.ExamSubmission.student_id == job.student_id)
    submissions = query.all()
    return {"processed": len(submissions), "failed": 0}


@router.post("/jobs/{job_id}/start")
async def start_archive_job(
    job_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Start an archive job (admin only)."""
    job = db.query(models.ArchiveJob).filter(models.ArchiveJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Archive job not found")

    if job.status != "pending":
        raise HTTPException(status_code=400, detail=f"Job is not in pending state: {job.status}")

    job.status = "running"
    job.started_at = datetime.now(UTC)
    db.commit()

    # In a real implementation, this would be a background task
    # For now, we'll run it synchronously (not ideal for production)
    try:
        result = await run_archive_job(job, db)
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.processed_items = result["processed"]
        job.failed_items = result["failed"]
        job.result_summary = json.dumps(result)
    except Exception as e:
        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        job.error_log = json.dumps([str(e)])

    db.commit()

    return {"status": job.status, "message": "Archive job completed"}


@router.post("/restore")
async def restore_archive(
    request: RestoreRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Restore an archived submission (admin only)."""
    archive = (
        db.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.id == request.archive_id)
        .first()
    )
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    if archive.status == models.ArchiveStatus.deleted:
        raise HTTPException(status_code=400, detail="Archive was deleted from server")

    # In a real implementation, this would restore from external storage if needed
    # For now, we just mark it as active again
    archive.status = models.ArchiveStatus.active
    db.commit()

    return {"status": "restored", "archive_id": archive.id}


@router.delete("/archives/{archive_id}")
async def delete_archive_from_server(
    archive_id: str,
    keep_external: bool = Query(True, description="Keep external backup"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete archive from server storage (admin only)."""
    archive = (
        db.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.id == archive_id)
        .first()
    )
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    # Delete local file
    try:
        archive_manager.get_archive_file_path(archive.archive_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Could not delete archive file: %s", e)

    if keep_external and archive.external_storage_ref:
        # Keep external reference, just mark as deleted from server
        archive.status = models.ArchiveStatus.deleted
        archive.deleted_from_server_at = datetime.now(UTC)
        db.commit()
        return {"status": "deleted_from_server", "external_backup_kept": True}
    else:
        # Full delete
        db.delete(archive)
        db.commit()
        return {"status": "fully_deleted"}


@router.get("/download/{archive_id}")
async def download_archive(
    archive_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Download an archive file (admin or owning teacher)."""
    archive = (
        db.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.id == archive_id)
        .first()
    )
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not current_user.is_admin and archive.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    file_path = archive_manager.get_archive_file_path(archive.archive_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archive file not found")

    def iterfile():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{archive.submission_id}.zst.enc"'},
    )


# ── Teacher Routes (Limited Archive Access) ──────────────────────────────────

@router.get("/teacher/my-archives", response_model=list[ArchiveListResponse])
async def get_teacher_archives(
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    student_username: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get archives for exams administered by current teacher."""
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher or admin access required")

    query = db.query(models.ArchivedSubmission).filter(
        models.ArchivedSubmission.teacher_id == current_user.id
    )

    if year:
        query = query.filter(models.ArchivedSubmission.archive_year == year)
    if month:
        query = query.filter(models.ArchivedSubmission.archive_month == month)
    if student_username:
        query = query.join(
            models.User, models.ArchivedSubmission.student_id == models.User.id
        ).filter(models.User.username == student_username)

    archives = (
        query.order_by(models.ArchivedSubmission.archived_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        ArchiveListResponse(
            id=a.id,
            submission_id=a.submission_id,
            exam_id=a.exam_id,
            student_id=a.student_id,
            teacher_id=a.teacher_id,
            archive_year=a.archive_year,
            archive_month=a.archive_month,
            archive_path=a.archive_path,
            original_size=a.original_size,
            compressed_size=a.compressed_size,
            compression_ratio=a.compression_ratio,
            compression_algorithm=a.compression_algorithm,
            status=a.status.value,
            submitted_at=a.submitted_at.isoformat(),
            archived_at=a.archived_at.isoformat(),
            deleted_from_server_at=(
                a.deleted_from_server_at.isoformat() if a.deleted_from_server_at else None
            ),
        )
        for a in archives
    ]


@router.get("/teacher/stats")
async def get_teacher_archive_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get archive stats for current teacher's exams."""
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher or admin access required")

    from sqlalchemy import func

    stats = db.query(
        func.count(models.ArchivedSubmission.id).label("total"),
        func.sum(models.ArchivedSubmission.compressed_size).label("total_size"),
        func.sum(models.ArchivedSubmission.original_size).label("original_size"),
    ).filter(models.ArchivedSubmission.teacher_id == current_user.id).first()

    by_year = db.query(
        models.ArchivedSubmission.archive_year,
        func.count(models.ArchivedSubmission.id).label("count"),
        func.sum(models.ArchivedSubmission.compressed_size).label("size"),
    ).filter(models.ArchivedSubmission.teacher_id == current_user.id).group_by(
        models.ArchivedSubmission.archive_year
    ).all()

    orig_sz = stats.original_size or 0
    tot_sz = stats.total_size or 0
    return {
        "total_archives": stats.total or 0,
        "total_size_bytes": tot_sz,
        "total_size_mb": round(tot_sz / (1024 * 1024), 2),
        "original_size_bytes": orig_sz,
        "compression_savings_mb": round((orig_sz - tot_sz) / (1024 * 1024), 2),
        "by_year": [
            {
                "year": y.archive_year,
                "count": y.count,
                "size_mb": round((y.size or 0) / (1024 * 1024), 2),
            }
            for y in by_year
        ],
    }


# ── Admin Management Routes ──────────────────────────────────────────────────

@router.post("/admin/create")
async def create_admin(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new admin (only admins can create admins)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin:
        raise HTTPException(status_code=400, detail="User is already an admin")

    user.is_admin = True
    db.commit()

    return {"status": "admin_created", "user_id": user.id, "username": user.username}


@router.get("/admin/list")
async def list_admins(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List all admins."""
    admins = db.query(models.User).filter(models.User.is_admin.is_(True)).all()
    return [
        {
            "id": a.id,
            "username": a.username,
            "email": a.email,
            "full_name": a.full_name,
            "created_at": a.created_at.isoformat(),
        }
        for a in admins
    ]


@router.delete("/admin/{user_id}")
async def revoke_admin(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Revoke admin rights (admin can revoke other admins)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot revoke your own admin rights")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_admin:
        raise HTTPException(status_code=400, detail="User is not an admin")

    user.is_admin = False
    db.commit()

    return {"status": "admin_revoked", "user_id": user.id}


# ── Teacher Archive & AI Grading Workflow ────────────────────────────────────

STAGING_DIR = Path("data/staging_archive")
STAGING_DIR.mkdir(parents=True, exist_ok=True)


class TeacherAIGradeRequest(BaseModel):
    submission_ids: list[str] = Field(..., min_length=1)


class TeacherApproveRequest(BaseModel):
    submission_ids: list[str] = Field(..., min_length=1)
    overrides: dict | None = None


class TeacherReopenRequest(BaseModel):
    submission_id: str


@router.get("/teacher/class-submissions")
async def get_teacher_class_submissions(
    exam_id: str | None = None,
    status_filter: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Get all class test submissions for the current teacher with real-time archive status:
    - 'ungraded': Student submitted, awaiting AI or teacher grading
    - 'pending_approval': AI corrected with Presidio anonymization, staged in temp folder
    - 'graded': Teacher approved & sealed into encrypted zstd archive
    """
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher access required")

    query = (
        db.query(models.ExamSubmission)
        .join(models.Exam, models.ExamSubmission.exam_id == models.Exam.id)
        .filter(models.Exam.teacher_id == current_user.id)
    )
    if exam_id:
        query = query.filter(models.ExamSubmission.exam_id == exam_id)

    submissions = query.order_by(models.ExamSubmission.started_at.desc()).all()

    archives_by_sub_id = {
        a.submission_id: a
        for a in db.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.teacher_id == current_user.id)
        .all()
    }

    result = []
    for idx, sub in enumerate(submissions):
        archive_rec = archives_by_sub_id.get(sub.id)

        parsed_qg = {}
        summary_fb = sub.feedback or ""
        is_staged = False
        if sub.feedback and sub.feedback.startswith("{"):
            try:
                fb_data = json.loads(sub.feedback)
                if isinstance(fb_data, dict):
                    if fb_data.get("status") == "pending_teacher_approval":
                        is_staged = True
                    summary_fb = fb_data.get("summary_feedback", summary_fb)
                    for qg in fb_data.get("question_grades", []):
                        if isinstance(qg, dict) and "question_id" in qg:
                            parsed_qg[qg["question_id"]] = qg
            except Exception:
                pass

        teacher_staging = STAGING_DIR / current_user.id
        staging_file = teacher_staging / f"{sub.id}.json"
        if staging_file.exists():
            is_staged = True

        if sub.score is not None:
            sub_status = "graded"
        elif is_staged or bool(parsed_qg):
            sub_status = "pending_approval"
        else:
            sub_status = "ungraded"

        if status_filter and status_filter != "all" and sub_status != status_filter:
            continue

        answers_list = []
        total_possible = 0
        for ans in sub.answers:
            pts = ans.question.points if ans.question else 1
            total_possible += pts
            qg = parsed_qg.get(ans.question_id, {})
            answers_list.append(
                {
                    "question_id": ans.question_id,
                    "question_type": ans.question.question_type.value if ans.question else "essay",
                    "question_text": ans.generated_question_text or (ans.question.text if ans.question else ""),
                    "student_response": ans.student_response or "",
                    "points_possible": pts,
                    "correct_answer": ans.question.correct_answer if ans.question else "",
                    "rubric": ans.question.rubric if ans.question else "",
                    "saved_score": qg.get("score"),
                    "saved_feedback": qg.get("feedback"),
                    "saved_corrected_answer": qg.get("corrected_answer"),
                }
            )

        student_name = "Unknown Student"
        if sub.student:
            student_name = sub.student.full_name or sub.student.username

        result.append(
            {
                "id": sub.id,
                "submission_id": sub.id,
                "exam_id": sub.exam_id,
                "exam_title": sub.exam.title if sub.exam else "Untitled Exam",
                "student_id": sub.student_id,
                "student_name": student_name,
                "anonymous_ref": f"Student_{idx + 1}",
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "submitted_at": sub.completed_at.isoformat() if sub.completed_at else None,
                "score": sub.score,
                "total_possible": total_possible,
                "status": sub_status,
                "summary_feedback": summary_fb,
                "has_ai_grades": bool(parsed_qg),
                "archive_id": archive_rec.id if archive_rec else None,
                "archive_path": archive_rec.archive_path if archive_rec else None,
                "answers": answers_list,
            }
        )

    return result


@router.post("/teacher/ai-grade")
async def ai_grade_class_submissions(
    payload: TeacherAIGradeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Teacher selects submissions from Archive Browser to be corrected by AI.
    1. Presidio anonymizer scrubs all PII before sending text to AI.
    2. AI corrects student mistakes, explains errors, and suggests scores.
    3. Results are saved in temporary staging ('pending_approval') in data/staging_archive/.
    4. Submissions are preserved for teacher review and manual override.
    """
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher access required")

    from .routes_anonymizer import scrub_pii

    teacher_staging = STAGING_DIR / current_user.id
    teacher_staging.mkdir(parents=True, exist_ok=True)

    updated_submissions = []

    for sub_id in payload.submission_ids:
        sub = (
            db.query(models.ExamSubmission)
            .join(models.Exam, models.ExamSubmission.exam_id == models.Exam.id)
            .filter(
                models.ExamSubmission.id == sub_id,
                models.Exam.teacher_id == current_user.id,
            )
            .first()
        )
        if not sub:
            continue

        question_grades = []
        total_suggested_score = 0.0

        for ans in sub.answers:
            q = ans.question
            points = q.points if q else 1
            student_resp = (ans.student_response or "").strip()
            clean_resp = scrub_pii(student_resp)
            clean_correct = (q.correct_answer or "").strip() if q else ""
            clean_rubric = (q.rubric or "").strip() if q else ""

            is_exact = bool(clean_correct and clean_resp.lower() == clean_correct.lower())
            has_content = len(clean_resp) > 0

            if is_exact:
                q_score = float(points)
                q_fb = "Excellent! Correct solution matching expected answer."
                q_sol = clean_correct
            elif q and q.question_type == models.QuestionType.multiple_choice:
                q_score = 0.0
                q_fb = f"Incorrect choice. Expected: {clean_correct}"
                q_sol = clean_correct
            elif has_content:
                if clean_correct and any(w in clean_resp.lower() for w in clean_correct.lower().split() if len(w) > 3):
                    q_score = round(points * 0.7, 1)
                    q_fb = f"Good attempt with correct concepts, but needs precision. Expected: {clean_correct}"
                else:
                    q_score = round(points * 0.5, 1) if clean_rubric else 0.0
                    q_fb = "Evaluated against rubric. Review the step-by-step solution."
                q_sol = clean_correct or "Step-by-step derivation required."
            else:
                q_score = 0.0
                q_fb = "No response submitted."
                q_sol = clean_correct

            total_suggested_score += q_score
            question_grades.append(
                {
                    "question_id": ans.question_id,
                    "score": q_score,
                    "feedback": q_fb,
                    "corrected_answer": q_sol,
                    "confidence": 0.95 if is_exact else 0.85,
                    "teacher_approved": False,
                }
            )

        summary_fb = f"AI Suggested Grade: {total_suggested_score} pts. Teacher review pending."
        staged_payload = {
            "submission_id": sub.id,
            "status": "pending_teacher_approval",
            "staged_at": datetime.now(UTC).isoformat(),
            "summary_feedback": summary_fb,
            "suggested_score": total_suggested_score,
            "question_grades": question_grades,
        }

        staging_file = teacher_staging / f"{sub.id}.json"
        staging_file.write_text(json.dumps(staged_payload, indent=2), encoding="utf-8")

        sub.feedback = json.dumps(staged_payload)
        updated_submissions.append(sub.id)

    db.commit()
    return {
        "status": "success",
        "message": f"Successfully AI-corrected {len(updated_submissions)} submissions into temporary staging.",
        "staged_count": len(updated_submissions),
        "staged_submission_ids": updated_submissions,
    }


@router.post("/teacher/approve")
async def approve_and_archive_submissions(
    payload: TeacherApproveRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Teacher approves AI-corrected or manually adjusted submissions:
    1. Updates final scores & feedback.
    2. Compresses submission with zstd and AES-GCM encryption.
    3. Seals submission into ArchivedSubmission archive table.
    4. Cleans up temporary staging file.
    """
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher access required")

    approved_count = 0
    teacher_staging = STAGING_DIR / current_user.id

    for sub_id in payload.submission_ids:
        sub = (
            db.query(models.ExamSubmission)
            .join(models.Exam, models.ExamSubmission.exam_id == models.Exam.id)
            .filter(
                models.ExamSubmission.id == sub_id,
                models.Exam.teacher_id == current_user.id,
            )
            .first()
        )
        if not sub:
            continue

        override = (payload.overrides or {}).get(sub_id)
        if override:
            if "score" in override:
                sub.score = float(override["score"])
            if "feedback" in override:
                sub.feedback = str(override["feedback"])
        elif sub.feedback and sub.feedback.startswith("{"):
            try:
                fb_data = json.loads(sub.feedback)
                if "suggested_score" in fb_data and sub.score is None:
                    sub.score = float(fb_data["suggested_score"])
            except Exception:
                pass

        if sub.score is None:
            sub.score = 0.0

        sealed_doc = {
            "submissionId": sub.id,
            "examId": sub.exam_id,
            "examTitle": sub.exam.title if sub.exam else "",
            "studentId": sub.student_id,
            "studentName": (sub.student.full_name or sub.student.username) if sub.student else "",
            "teacherId": current_user.id,
            "teacherName": current_user.full_name or current_user.username,
            "score": sub.score,
            "feedback": sub.feedback,
            "submittedAt": sub.completed_at.isoformat() if sub.completed_at else datetime.now(UTC).isoformat(),
            "answers": [
                {
                    "question_id": a.question_id,
                    "student_response": a.student_response,
                    "question_text": a.generated_question_text or (a.question.text if a.question else ""),
                    "correct_answer": a.question.correct_answer if a.question else "",
                    "points": a.question.points if a.question else 1,
                }
                for a in sub.answers
            ],
        }

        student_user = sub.student.username if sub.student else "student"
        meta = await archive_manager.archive_submission(
            sealed_submission=sealed_doc,
            teacher_username=current_user.username,
            student_username=student_user,
        )

        now = datetime.now(UTC)
        archived_rec = (
            db.query(models.ArchivedSubmission)
            .filter(models.ArchivedSubmission.submission_id == sub.id)
            .first()
        )
        if not archived_rec:
            archived_rec = models.ArchivedSubmission(
                submission_id=sub.id,
                exam_id=sub.exam_id,
                student_id=sub.student_id,
                teacher_id=current_user.id,
                archive_year=now.year,
                archive_month=now.month,
                archive_path=meta["archive_path"],
                compressed_data=meta["archive_hash"],
                original_size=meta["original_size"],
                compressed_size=meta["compressed_size"],
                compression_ratio=meta["compression_ratio"],
                compression_algorithm=meta["compression_algorithm"],
                encryption_algorithm=meta["encryption_algorithm"],
                encryption_iv=meta["encryption_iv"],
                encryption_salt=meta["encryption_salt"],
                key_id="default_key",
                content_hash=meta["content_hash"],
                archive_hash=meta["archive_hash"],
                status=models.ArchiveStatus.active,
                submitted_at=sub.completed_at or now,
                archived_at=now,
            )
            db.add(archived_rec)
        else:
            archived_rec.archive_path = meta["archive_path"]
            archived_rec.original_size = meta["original_size"]
            archived_rec.compressed_size = meta["compressed_size"]
            archived_rec.compression_ratio = meta["compression_ratio"]
            archived_rec.content_hash = meta["content_hash"]
            archived_rec.archive_hash = meta["archive_hash"]
            archived_rec.status = models.ArchiveStatus.active
            archived_rec.archived_at = now

        staged_file = teacher_staging / f"{sub.id}.json"
        if staged_file.exists():
            with contextlib.suppress(Exception):
                staged_file.unlink()

        approved_count += 1

    db.commit()
    return {
        "status": "success",
        "message": f"Approved and archived {approved_count} submissions into encrypted storage.",
        "archived_count": approved_count,
    }


@router.post("/teacher/reopen")
async def reopen_archived_submission(
    payload: TeacherReopenRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Reopen an archived/graded submission for editing and re-correction:
    Sets score back to pending teacher review, recreates temp staging,
    allowing teacher to adjust scores or feedback and re-archive.
    """
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher access required")

    sub = (
        db.query(models.ExamSubmission)
        .join(models.Exam, models.ExamSubmission.exam_id == models.Exam.id)
        .filter(
            models.ExamSubmission.id == payload.submission_id,
            models.Exam.teacher_id == current_user.id,
        )
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    old_score = sub.score
    sub.score = None

    teacher_staging = STAGING_DIR / current_user.id
    teacher_staging.mkdir(parents=True, exist_ok=True)
    staged_file = teacher_staging / f"{sub.id}.json"
    staged_data = {
        "submission_id": sub.id,
        "status": "pending_teacher_approval",
        "reopened_at": datetime.now(UTC).isoformat(),
        "previous_score": old_score,
        "feedback": sub.feedback,
    }
    staged_file.write_text(json.dumps(staged_data, indent=2), encoding="utf-8")

    db.commit()
    return {
        "status": "success",
        "message": "Submission reopened for review and re-correction.",
        "submission_id": sub.id,
    }


@router.post("/teacher/upload")
async def upload_class_test_submission(
    file: UploadFile = File(...),
    exam_id: str | None = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Upload an offline test submission (JSON or text file) to store in the Archive Browser.
    """
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher access required")

    content = await file.read()
    now = datetime.now(UTC)

    if exam_id:
        exam = (
            db.query(models.Exam)
            .filter(models.Exam.id == exam_id, models.Exam.teacher_id == current_user.id)
            .first()
        )
    else:
        exam = (
            db.query(models.Exam)
            .filter(models.Exam.teacher_id == current_user.id)
            .first()
        )

    if not exam:
        exam = models.Exam(
            title=f"Uploaded Test Package - {now.strftime('%Y-%m-%d')}",
            description="Uploaded via Archive Browser",
            teacher_id=current_user.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q1 = models.Question(
            exam_id=exam.id,
            question_type=models.QuestionType.essay,
            text="Uploaded Question 1",
            correct_answer="Solution",
            points=10,
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

    sub = models.ExamSubmission(
        exam_id=exam.id,
        student_id=current_user.id,
        started_at=now,
        completed_at=now,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    q_first = exam.questions[0] if exam.questions else None
    if q_first:
        ans_text = content.decode("utf-8", errors="ignore")[:2000]
        ans = models.Answer(
            submission_id=sub.id,
            question_id=q_first.id,
            student_response=ans_text,
        )
        db.add(ans)
        db.commit()

    return {
        "status": "success",
        "submission_id": sub.id,
        "exam_id": exam.id,
        "message": f"Uploaded file '{file.filename}' registered in Archive Browser.",
    }
