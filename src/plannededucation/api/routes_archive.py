"""
Archive Routes for PlannedEducation
Admin-only routes for managing archived exam submissions.
"""

import json
import os
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models, schemas
from .routes_auth import get_current_user
from .archive_utils import (
    ArchiveManager,
    build_archive_path,
    compress_data,
    decompress_data,
    DEFAULT_COMPRESSION_LEVEL,
)

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
    graduation_year: Optional[int] = Field(None, ge=2020, le=2100)
    teacher_id: Optional[str] = None
    student_id: Optional[str] = None
    archive_to_external: bool = False
    external_storage_path: Optional[str] = None
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
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[dict] = None

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
    deleted_from_server_at: Optional[str] = None

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
    credentials: Optional[dict] = None


# ── Archive Manager Instance ─────────────────────────────────────────────────

# Default archive storage location
ARCHIVE_STORAGE_ROOT = os.getenv("ARCHIVE_STORAGE_ROOT", "/var/lib/plannededucation/archive")
archive_manager = ArchiveManager(ARCHIVE_STORAGE_ROOT)


# ── Admin Routes ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ArchiveStatsResponse)
async def get_archive_stats(
    current_user: models.User = Depends(require_admin),
):
    """Get archive storage statistics (admin only)."""
    stats = archive_manager.get_storage_stats()
    return ArchiveStatsResponse(**stats)


@router.get("/list", response_model=list[ArchiveListResponse])
async def list_archives(
    year: Optional[int] = Query(None, ge=2020, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    teacher_username: Optional[str] = None,
    student_username: Optional[str] = None,
    status: Optional[str] = Query(None, pattern="^(active|archived|deleted)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(database.get_db),
):
    """List archived submissions with filters (admin only)."""
    query = db.query(models.ArchivedSubmission)
    
    if year:
        query = query.filter(models.ArchivedSubmission.archive_year == year)
    if month:
        query = query.filter(models.ArchivedSubmission.archive_month == month)
    if teacher_username:
        query = query.join(models.User, models.ArchivedSubmission.teacher_id == models.User.id).filter(models.User.username == teacher_username)
    if student_username:
        query = query.join(models.User, models.ArchivedSubmission.student_id == models.User.id).filter(models.User.username == student_username)
    if status:
        query = query.filter(models.ArchivedSubmission.status == status)
    
    total = query.count()
    archives = query.order_by(models.ArchivedSubmission.archived_at.desc()).offset(offset).limit(limit).all()
    
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
            deleted_from_server_at=a.deleted_from_server_at.isoformat() if a.deleted_from_server_at else None,
        )
        for a in archives
    ]


@router.post("/jobs", response_model=ArchiveJobResponse, status_code=201)
async def create_archive_job(
    request: ArchiveJobRequest,
    current_user: models.User = Depends(require_admin),
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
    status: Optional[str] = Query(None, pattern="^(pending|running|completed|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(require_admin),
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
    current_user: models.User = Depends(require_admin),
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


@router.post("/jobs/{job_id}/start")
async def start_archive_job(
    job_id: str,
    current_user: models.User = Depends(require_admin),
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
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(database.get_db),
):
    """Restore an archived submission (admin only)."""
    archive = db.query(models.ArchivedSubmission).filter(models.ArchivedSubmission.id == request.archive_id).first()
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
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(database.get_db),
):
    """Delete archive from server storage (admin only)."""
    archive = db.query(models.ArchivedSubmission).filter(models.ArchivedSubmission.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    
    # Delete local file
    try:
        archive_manager.get_archive_file_path(archive.archive_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not delete archive file: {e}")
    
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
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(database.get_db),
):
    """Download an archive file (admin only)."""
    archive = db.query(models.ArchivedSubmission).filter(models.ArchivedSubmission.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    
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
    year: Optional[int] = Query(None, ge=2020, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    student_username: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get archives for exams administered by current teacher."""
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Teacher or admin access required")
    
    query = db.query(models.ArchivedSubmission).filter(models.ArchivedSubmission.teacher_id == current_user.id)
    
    if year:
        query = query.filter(models.ArchivedSubmission.archive_year == year)
    if month:
        query = query.filter(models.ArchivedSubmission.archive_month == month)
    if student_username:
        query = query.join(models.User, models.ArchivedSubmission.student_id == models.User.id).filter(models.User.username == student_username)
    
    archives = query.order_by(models.ArchivedSubmission.archived_at.desc()).offset(offset).limit(limit).all()
    
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
            deleted_from_server_at=a.deleted_from_server_at.isoformat() if a.deleted_from_server_at else None,
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
    
    return {
        "total_archives": stats.total or 0,
        "total_size_bytes": stats.total_size or 0,
        "total_size_mb": round((stats.total_size or 0) / (1024 * 1024), 2),
        "original_size_bytes": stats.original_size or 0,
        "compression_savings_mb": round(((stats.original_size or 0) - (stats.total_size or 0)) / (1024 * 1024), 2),
        "by_year": [
            {"year": y.archive_year, "count": y.count, "size_mb": round((y.size or 0) / (1024 * 1024), 2)}
            for y in by_year
        ],
    }


# ── Admin Management Routes ──────────────────────────────────────────────────

@router.post("/admin/create")
async def create_admin(
    user_id: str,
    current_user: models.User = Depends(require_admin),
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
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(database.get_db),
):
    """List all admins."""
    admins = db.query(models.User).filter(models.User.is_admin == True).all()
    return [
        {"id": a.id, "username": a.username, "email": a.email, "full_name": a.full_name, "created_at": a.created_at.isoformat()}
        for a in admins
    ]


@router.delete("/admin/{user_id}")
async def revoke_admin(
    user_id: str,
    current_user: models.User = Depends(require_admin),
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