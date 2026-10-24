"""
Admin Routes for PlannedEducation
Endpoints for administrative operations (user management, exam oversight, system stats).
"""

import hashlib
import re
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import auth, backup_service, database, models, schemas
from .deployment_config import (
    DeploymentConfigResponse,
    DeploymentConfigSchema,
    load_deployment_config,
    save_deployment_config,
)
from .routes_auth import (
    _decode_recovery_codes,
    _encode_recovery_codes,
    _validate_password,
    get_current_user,
    get_password_hash,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency to ensure the current user is a superadmin (is_admin=True)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_teacher_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency to ensure the current user is an approved teacher or admin."""
    if not (current_user.is_admin or (current_user.role in ("admin", "teacher") and current_user.teacher_approved)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin access required"
        )
    return current_user


def generate_temporary_password() -> str:
    """Generate a secure temporary password meeting complexity requirements (uppercase, lowercase, digit, special)."""
    chars = string.ascii_letters + string.digits
    rand_chars = "".join(secrets.choice(chars) for _ in range(8))
    return f"TempPass#{rand_chars}!"


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get system-wide statistics for admin dashboard."""
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_exams = db.query(func.count(models.Exam.id)).scalar() or 0
    total_submissions = db.query(func.count(models.ExamSubmission.id)).scalar() or 0

    # Active exams = exams that have at least one submission in progress or recently started
    active_exams = (
        db.query(func.count(models.Exam.id))
        .join(models.ExamSubmission, models.Exam.id == models.ExamSubmission.exam_id)
        .filter(models.ExamSubmission.started_at.isnot(None))
        .filter(models.ExamSubmission.completed_at.is_(None))
        .scalar() or 0
    )

    return {
        "totalUsers": total_users,
        "totalExams": total_exams,
        "totalSubmissions": total_submissions,
        "activeExams": active_exams,
    }


@router.get("/users")
def get_admin_users(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get all users for admin management."""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
        for user in users
    ]


@router.patch("/users/{user_id}")
def update_admin_user(
    user_id: str,
    is_active: bool,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Activate or deactivate a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    # Cybersecurity safeguard: non-superadmin cannot deactivate an administrator
    if (user.is_admin or user.role == "admin") and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Superadmin privilege required to modify administrator accounts")

    user.is_active = is_active
    db.commit()
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}


@router.delete("/users/{user_id}")
def delete_admin_user(
    user_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Delete a user (and all their data via cascade)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Cybersecurity safeguard: non-superadmin cannot delete an administrator
    if (user.is_admin or user.role == "admin") and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Superadmin privilege required to delete administrator accounts")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/reset-password", response_model=schemas.AdminResetPasswordResponse)
def admin_reset_user_password(
    user_id: str,
    payload: schemas.AdminResetPasswordRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """
    Directly reset a user's password from the Admin Panel without needing an email.
    If no new_password is provided in payload, a secure temporary password is auto-generated.
    Optionally clears 2FA / Passkeys if the user lost their authenticator device.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cybersecurity safeguard: non-superadmin cannot reset an administrator's password
    if (user.is_admin or user.role == "admin") and user.id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Superadmin privilege required to reset administrator accounts")

    # Set custom or generated password
    if payload.new_password and payload.new_password.strip():
        new_pwd = payload.new_password.strip()
        _validate_password(new_pwd)
    else:
        new_pwd = generate_temporary_password()

    # Hash and update password
    user.hashed_password = get_password_hash(new_pwd)

    # Invalidate pending reset OTPs
    user.password_reset_otp = None
    user.password_reset_otp_expires = None

    # Invalidate existing refresh tokens for security
    user.refresh_token_hash = None
    user.refresh_token_expires = None

    # Clear brute-force lockout and quick-reset flags
    user.failed_login_attempts = 0
    user.locked_until = None
    user.force_password_reset = False
    user.reset_by_teacher_id = None

    # Optionally reset 2FA / TOTP / WebAuthn
    if payload.reset_2fa:
        user.totp_enabled = False
        user.totp_secret = None
        user.recovery_codes = None
        user.webauthn_credentials = None
        user.webauthn_challenge = None
        user.webauthn_challenge_expires = None

    db.commit()

    return schemas.AdminResetPasswordResponse(
        status="success",
        user_id=user.id,
        username=user.username,
        email=user.email,
        temporary_password=new_pwd,
        reset_2fa=payload.reset_2fa,
        message=f"Password for {user.username} was reset successfully.",
    )


@router.get("/exams")
def get_admin_exams(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get all exams for admin oversight."""
    exams = (
        db.query(
            models.Exam.id,
            models.Exam.title,
            models.Exam.teacher_id,
            models.User.full_name.label("teacher_name"),
            func.count(models.Question.id).label("question_count"),
            func.count(models.ExamSubmission.id).label("submission_count"),
            models.Exam.created_at,
        )
        .join(models.User, models.Exam.teacher_id == models.User.id)
        .outerjoin(models.Question, models.Exam.id == models.Question.exam_id)
        .outerjoin(models.ExamSubmission, models.Exam.id == models.ExamSubmission.exam_id)
        .group_by(models.Exam.id, models.User.full_name)
        .order_by(models.Exam.created_at.desc())
        .all()
    )

    return [
        {
            "id": exam.id,
            "title": exam.title,
            "teacher_id": exam.teacher_id,
            "teacher_name": exam.teacher_name or "Unknown",
            "question_count": exam.question_count,
            "submission_count": exam.submission_count,
            "is_published": exam.submission_count > 0,  # Consider published if has submissions
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
        }
        for exam in exams
    ]


@router.delete("/exams/{exam_id}")
def delete_admin_exam(
    exam_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Delete an exam (and all related data via cascade)."""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    db.delete(exam)
    db.commit()
    return {"message": "Exam deleted successfully"}


@router.post("/users", response_model=schemas.AdminCreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: schemas.AdminCreateUserRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Create a new user (admin, teacher, student, or parent) directly from the admin dashboard."""
    # Auto-derive username if omitted
    chosen_username = payload.username
    if not chosen_username:
        base_username = re.sub(r"[^a-zA-Z0-9_.-]", "_", payload.email.split("@")[0].lower())
        if len(base_username) < 3:
            base_username = f"user_{base_username}"
        cand = base_username[:50]
        suffix = 1
        while db.query(models.User).filter(models.User.username == cand.lower()).first():
            cand = f"{base_username[:45]}_{suffix}"
            suffix += 1
        chosen_username = cand
    chosen_username = chosen_username.lower()

    # Check if username or email exists
    existing_user = db.query(models.User).filter(
        (models.User.username == chosen_username) | (models.User.email == payload.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username or email already exists."
        )

    # Validate or generate password
    temp_pwd = None
    if payload.password and payload.password.strip():
        pwd = payload.password.strip()
        _validate_password(pwd)
    else:
        pwd = generate_temporary_password()
        temp_pwd = pwd

    hashed_pwd = get_password_hash(pwd)
    is_admin = (payload.role == "admin")

    new_user = models.User(
        username=chosen_username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hashed_pwd,
        is_admin=is_admin,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return schemas.AdminCreateUserResponse(
        status="success",
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        temporary_password=temp_pwd,
        message=f"User {new_user.username} created successfully.",
    )


@router.post("/users/superadmin", response_model=schemas.AdminCreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_superadmin_user(
    payload: schemas.AdminCreateUserRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """
    Create a new superadmin user.
    Only existing superadmins can create other superadmins.
    """
    # Only superadmins can create superadmins
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privilege required to create superadmin accounts"
        )

    # Check if username or email exists
    existing_user = db.query(models.User).filter(
        (models.User.username == payload.username) | (models.User.email == payload.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username or email already exists."
        )

    # Validate or generate password
    temp_pwd = None
    if payload.password and payload.password.strip():
        pwd = payload.password.strip()
        _validate_password(pwd)
    else:
        pwd = generate_temporary_password()
        temp_pwd = pwd

    hashed_pwd = get_password_hash(pwd)

    new_user = models.User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hashed_pwd,
        is_admin=True,  # Superadmin flag
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return schemas.AdminCreateUserResponse(
        status="success",
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        temporary_password=temp_pwd,
        message=f"Superadmin {new_user.username} created successfully.",
    )


@router.get("/config", response_model=DeploymentConfigResponse)
def get_admin_deployment_config(
    current_user: models.User = Depends(require_admin),
):
    """Get current deployment and network configuration."""
    cfg = load_deployment_config()
    cfg["config_file_path"] = "config/deployment.json"
    cfg["restart_required"] = False
    return cfg


@router.put("/config")
def update_admin_deployment_config(
    payload: DeploymentConfigSchema,
    current_user: models.User = Depends(require_admin),
):
    """Update deployment configuration and synchronize config/deployment.json and .env."""
    result = save_deployment_config(payload)
    return {
        "status": "success",
        "message": "Deployment configuration saved successfully. A platform restart is required to apply network changes.",
        "restart_required": True,
        "config": result,
    }


# ── Teacher Approval Management ───────────────────────────────────────────────

@router.get("/pending-teachers")
def get_pending_teachers(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Retrieve all teachers awaiting administrative approval."""
    pending = (
        db.query(models.User)
        .filter(models.User.role == "teacher", models.User.teacher_approved.is_(False))
        .order_by(models.User.created_at.desc())
        .all()
    )
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "is_active": u.is_active,
        }
        for u in pending
    ]


@router.post("/teachers/{user_id}/approve")
def approve_teacher(
    user_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Approve a self-registered teacher, granting them full exam creation rights."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "teacher":
        raise HTTPException(status_code=400, detail="User is not a teacher")

    user.teacher_approved = True
    user.is_active = True

    # Send in-app notification to the teacher
    notif = models.InAppNotification(
        user_id=user.id,
        title="Teacher Account Approved",
        message="Your teacher status has been verified and approved by an administrator! You can now publish exams, manage classes, and access curriculum modules.",
        type="system",
        link="/teacher-exams",
    )
    db.add(notif)
    db.commit()

    return {"status": "success", "message": f"Teacher {user.username} approved successfully."}


@router.post("/teachers/{user_id}/deny")
def deny_teacher(
    user_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Deny a self-registered teacher's request and convert their account to a student role."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = "student"
    user.teacher_approved = True

    notif = models.InAppNotification(
        user_id=user.id,
        title="Teacher Registration Update",
        message="Your request for teacher privileges was declined by the administrator. Your account has been designated as a student account.",
        type="system",
        link="/exam",
    )
    db.add(notif)
    db.commit()

    return {"status": "success", "message": f"Teacher request for {user.username} denied; role set to student."}


# ── Admin Emergency Backup Codes ──────────────────────────────────────────────

@router.get("/backup-codes")
def get_admin_backup_codes_status(
    current_user: models.User = Depends(require_admin),
):
    """Check how many emergency backup codes the administrator has active."""
    codes = _decode_recovery_codes(current_user.recovery_codes)
    return {
        "has_backup_codes": len(codes) > 0,
        "active_codes_count": len(codes),
        "username": current_user.username,
    }


@router.post("/backup-codes/generate")
def generate_admin_backup_codes(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """
    Generate 5 fresh one-time emergency backup codes for the administrator.
    Admins MUST print or save these codes to ensure system access cannot be lost.
    """
    fresh_codes = auth.generate_recovery_codes(count=5)
    hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in fresh_codes]

    current_user.recovery_codes = _encode_recovery_codes(hashed_codes)
    db.commit()

    return {
        "status": "success",
        "recovery_codes": fresh_codes,
        "message": (
            "5 emergency backup codes generated! PRINT OR SAVE THESE CODES IMMEDIATELY in a secure location. "
            "If you lose access to your password or 2FA, these one-time codes are the only way to recover administrator access."
        ),
    }


# ── Database Backup Operations ────────────────────────────────────────────────

@router.post("/database/backup")
def trigger_database_backup(
    current_user: models.User = Depends(require_admin),
):
    """Trigger an immediate manual database backup."""
    result = backup_service.create_database_backup(is_auto=False)
    return result


@router.get("/database/backups")
def get_database_backups(
    current_user: models.User = Depends(require_admin),
):
    """List all available database backups."""
    return backup_service.list_database_backups()


@router.get("/database/backups/{filename}/download")
def download_database_backup(
    filename: str,
    current_user: models.User = Depends(require_admin),
):
    """Download a database backup snapshot with path-traversal protection."""
    target_path = backup_service.get_backup_file_path(filename)
    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    return FileResponse(
        path=str(target_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/database/backups/{filename}")
def delete_database_backup(
    filename: str,
    current_user: models.User = Depends(require_admin),
):
    """Delete an old database backup."""
    success = backup_service.delete_backup_file(filename)
    if not success:
        raise HTTPException(status_code=404, detail="Backup file not found or could not be deleted")
    return {"status": "success", "message": f"Backup {filename} deleted successfully."}


# ── School Header Customization ──────────────────────────────────────────────

@router.get("/school/header", response_model=schemas.SchoolHeaderResponse)
def get_school_header(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Get the school's header customization settings."""
    school = db.query(models.School).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return schemas.SchoolHeaderResponse(
        header_display_mode=school.header_display_mode,
        header_text=school.header_text,
        header_image_url=school.header_image_url,
    )


@router.put("/school/header", response_model=schemas.SchoolHeaderResponse)
def update_school_header(
    payload: schemas.SchoolHeaderUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Update the school's header customization settings (admin/superadmin only)."""
    school = db.query(models.School).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    school.header_display_mode = payload.header_display_mode
    school.header_text = payload.header_text
    school.header_image_url = payload.header_image_url
    db.commit()
    db.refresh(school)

    return schemas.SchoolHeaderResponse(
        header_display_mode=school.header_display_mode,
        header_text=school.header_text,
        header_image_url=school.header_image_url,
    )


