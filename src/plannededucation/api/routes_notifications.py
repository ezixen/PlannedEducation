"""
In-App Notification and Internal Password Reset Request Routes for PlannedEducation.
Handles in-platform alerts, unread counts, teacher approval notifications,
and student-to-teacher/parent password reset requests.
"""

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth, database, models, schemas
from .email_service import send_email
from .limiter import limiter
from .routes_auth import _validate_password, get_current_user, get_password_hash

logger = logging.getLogger("plannededucation")

router = APIRouter(prefix="/notifications", tags=["notifications"])


class RequestPasswordResetInternalPayload(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)
    target_role: str = Field(..., pattern=r"^(teacher|parent|admin)$")
    note: str | None = Field(None, max_length=256)


@router.get("", response_model=list[schemas.InAppNotificationResponse])
def get_user_notifications(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve the latest notifications for the current authenticated user."""
    notifications = (
        db.query(models.InAppNotification)
        .filter(models.InAppNotification.user_id == current_user.id)
        .order_by(models.InAppNotification.created_at.desc())
        .limit(50)
        .all()
    )
    return notifications


@router.get("/unread-count", response_model=schemas.UnreadCountResponse)
def get_unread_notification_count(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Fast endpoint for 1-minute poller to display unread badge count."""
    count = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.user_id == current_user.id,
            models.InAppNotification.is_read.is_(False),
        )
        .count()
    )
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.id == notification_id,
            models.InAppNotification.user_id == current_user.id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "success", "message": "Notification marked as read"}


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark all unread notifications for the current user as read."""
    db.query(models.InAppNotification).filter(
        models.InAppNotification.user_id == current_user.id,
        models.InAppNotification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a notification."""
    notif = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.id == notification_id,
            models.InAppNotification.user_id == current_user.id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()
    return {"status": "success", "message": "Notification deleted"}


@router.post("/request-password-reset")
@limiter.limit("5/minute")
def request_password_reset_internal(
    request: Request,
    payload: RequestPasswordResetInternalPayload,
    db: Session = Depends(database.get_db),
):
    """
    Allow students or teachers who cannot log in to request an in-platform password reset
    from their teacher, parent, or an administrator.
    """
    _ = request  # required for slowapi
    lookup = payload.identifier.strip().lower()
    user = (
        db.query(models.User)
        .filter((models.User.email == lookup) | (models.User.username == lookup))
        .first()
    )
    # Always generic — no enumeration (F-007)
    generic = {
        "status": "success",
        "message": "If this account exists, your password reset request has been dispatched to your designated supervisor.",
    }
    if not user:
        return generic

    recipients: list[models.User] = []

    if payload.target_role == "teacher":
        # Teachers who already have exam submissions from this student — never broadcast all teachers
        linked = (
            db.query(models.User)
            .join(models.Exam, models.Exam.teacher_id == models.User.id)
            .join(models.ExamSubmission, models.ExamSubmission.exam_id == models.Exam.id)
            .filter(
                models.ExamSubmission.student_id == user.id,
                models.User.role == "teacher",
                models.User.is_active == True,
                models.User.teacher_approved == True,
            )
            .distinct()
            .all()
        )
        recipients.extend(linked)
        if not recipients:
            admins = db.query(models.User).filter(models.User.is_admin == True, models.User.is_active == True).all()
            recipients.extend(admins)

    elif payload.target_role == "parent":
        # Active parent relationships only (F-007)
        rel_parents = (
            db.query(models.User)
            .join(models.AccountRelationship, models.AccountRelationship.parent_id == models.User.id)
            .filter(
                models.AccountRelationship.student_id == user.id,
                models.AccountRelationship.status == models.RelationshipStatus.active,
                models.User.role == "parent",
                models.User.is_active == True,
            )
            .all()
        )
        recipients.extend(rel_parents)
        if not recipients:
            admins = db.query(models.User).filter(models.User.is_admin == True, models.User.is_active == True).all()
            recipients.extend(admins)

    elif payload.target_role == "admin":
        admins = (
            db.query(models.User)
            .filter(
                models.User.is_active == True,
                (models.User.is_admin == True) | (models.User.role == "admin"),
            )
            .all()
        )
        recipients.extend(admins)

    # De-duplicate recipients
    recipient_ids = set()
    for rec in recipients:
        if rec.id not in recipient_ids and rec.id != user.id:
            recipient_ids.add(rec.id)
            action_data = {
                "requester_id": user.id,
                "requester_role": user.role,
                "note": payload.note or "Password reset requested via platform.",
            }
            notif = models.InAppNotification(
                user_id=rec.id,
                title="Password Reset Request",
                message=f"{user.full_name or user.username} requested a password reset. Review the request in your notifications.",
                type="password_reset_request",
                link="/settings",
                action_payload=json.dumps(action_data),
            )
            db.add(notif)

    db.commit()

    # Same generic message whether or not recipients were found (no enumeration)
    return generic


@router.post("/approve-password-reset/{notification_id}")
async def approve_password_reset_request(
    notification_id: str,
    payload: schemas.InternalPasswordResetApprove,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Approve an in-platform password reset request.
    Allowed for:
    - Admins: can approve any user
    - Teachers: can approve student requests
    - Parents: can approve their linked child's requests
    """
    notif = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.id == notification_id,
            models.InAppNotification.user_id == current_user.id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notif.type != "password_reset_request" or not notif.action_payload:
        raise HTTPException(status_code=400, detail="Notification is not a pending password reset request")
    if notif.action_consumed_at is not None:
        raise HTTPException(status_code=409, detail="This reset request was already approved")

    try:
        action_data = json.loads(notif.action_payload)
        requester_id = action_data.get("requester_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid action payload") from None

    target_user = db.query(models.User).filter(models.User.id == requester_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Requester account not found")

    # Authorization verification
    if not current_user.is_admin and current_user.role != "admin":
        if current_user.role == "teacher":
            if not current_user.teacher_approved or target_user.role != "student":
                raise HTTPException(status_code=403, detail="Teachers can only approve password resets for students.")
            linked_exam = (
                db.query(models.ExamSubmission)
                .join(models.Exam, models.Exam.id == models.ExamSubmission.exam_id)
                .filter(
                    models.ExamSubmission.student_id == target_user.id,
                    models.Exam.teacher_id == current_user.id,
                )
                .first()
            )
            if not linked_exam:
                raise HTTPException(status_code=403, detail="Teachers can only approve requests from their students.")
        elif current_user.role == "parent":
            if target_user.role != "student":
                raise HTTPException(status_code=403, detail="Parents can only reset student accounts.")
            link_exists = db.query(models.AccountRelationship).filter(
                models.AccountRelationship.parent_id == current_user.id,
                models.AccountRelationship.student_id == target_user.id,
                models.AccountRelationship.status == models.RelationshipStatus.active,
            ).first()
            if not link_exists:
                raise HTTPException(status_code=403, detail="Parents can only reset passwords for their linked children.")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to approve password resets.")

    # Single-use: refuse if already consumed (F-007)
    if action_data.get("consumed"):
        raise HTTPException(status_code=400, detail="This reset request was already approved")

    # Classroom / supervisor handoff: issue a one-time reset capability token
    # (same model as teacher quick-reset). Do NOT set a temporary password while
    # force_password_reset is on — login intercepts before password verify, so a
    # temp password is unusable and clearing reset_token locked the account.
    auth.revoke_all_refresh_sessions(db, target_user.id)
    auth.clear_legacy_refresh_fields(target_user)
    target_user.password_reset_otp = None
    target_user.password_reset_otp_expires = None
    target_user.failed_login_attempts = 0
    target_user.locked_until = None
    target_user.is_active = True
    target_user.force_password_reset = True
    target_user.reset_expires = datetime.now(UTC) + timedelta(hours=24)
    if current_user.is_admin or current_user.role == "admin":
        target_user.reset_by_admin_id = current_user.id
        target_user.reset_by_teacher_id = None
        target_user.reset_by_parent_id = None
    elif current_user.role == "teacher":
        target_user.reset_by_teacher_id = current_user.id
        target_user.reset_by_admin_id = None
        target_user.reset_by_parent_id = None
    elif current_user.role == "parent":
        target_user.reset_by_parent_id = current_user.id
        target_user.reset_by_teacher_id = None
        target_user.reset_by_admin_id = None

    # Optional: supervisor chose the final password now (no login handoff needed).
    if payload.new_password and payload.new_password.strip():
        chosen = payload.new_password.strip()
        _validate_password(chosen)
        target_user.hashed_password = get_password_hash(chosen)
        target_user.force_password_reset = False
        target_user.reset_token = None
        target_user.reset_expires = None
        plain_reset_token = None
    else:
        plain_reset_token = hashlib.sha256(
            f"{target_user.id}:{current_user.id}:{secrets.token_hex(32)}".encode()
        ).hexdigest()
        target_user.reset_token = plain_reset_token

    # Consume notification action atomically so concurrent approvals cannot
    # reuse the same capability.
    consumed_at = datetime.now(UTC)
    consumed = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.id == notification_id,
            models.InAppNotification.user_id == current_user.id,
            models.InAppNotification.action_consumed_at.is_(None),
        )
        .update(
            {"action_consumed_at": consumed_at, "is_read": True},
            synchronize_session=False,
        )
    )
    if consumed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This reset request was already approved")

    # Keep the legacy marker for old clients; the timestamp is authoritative.
    action_data["consumed"] = True
    notif.action_payload = json.dumps(action_data)

    if plain_reset_token:
        user_msg = (
            f"Your password reset request was approved by "
            f"{current_user.full_name or current_user.username}. "
            "Ask them for the one-time reset code, then use "
            "'My account was reset' on the login page to choose a new password."
        )
        link = "/login"
    else:
        user_msg = (
            f"Your password was set by "
            f"{current_user.full_name or current_user.username}. "
            "You can sign in with the password they provided."
        )
        link = "/login"
    user_notif = models.InAppNotification(
        user_id=target_user.id,
        title="Password Reset Approved",
        message=user_msg,
        type="system",
        link=link,
    )
    db.add(user_notif)
    db.commit()

    try:
        await send_email(
            to_email=target_user.email,
            subject="PlannedEducation — Password Reset Approved",
            text_content=(
                f"Hello {target_user.full_name or target_user.username},\n\n"
                f"Your password reset request was approved by {current_user.full_name or current_user.username}.\n\n"
                "Use the one-time reset code from your supervisor on the login page "
                "to choose a new password (or sign in if they set one for you).\n\n"
                f"— PlannedEducation Platform"
            ),
        )
    except Exception as exc:
        logger.warning(f"Could not dispatch password reset email: {exc}")

    result = {
        "status": "success",
        "message": (
            f"Password reset approved for {target_user.username}. "
            + (
                "Share the reset_token securely; they complete it on the login page."
                if plain_reset_token
                else "They can sign in with the password you provided."
            )
        ),
        "requester_id": target_user.id,
        "requester_email": target_user.email,
    }
    # One-time supervisor handoff of the capability token (not a password).
    if plain_reset_token:
        result["reset_token"] = plain_reset_token
    return result


@router.post("/approve-teacher/{notification_id}")
def approve_teacher_from_notification(
    notification_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Admin one-click approval of a pending teacher registration from notification."""
    if not (current_user.is_admin or current_user.role == "admin"):
        raise HTTPException(status_code=403, detail="Administrator privileges required.")

    notif = (
        db.query(models.InAppNotification)
        .filter(
            models.InAppNotification.id == notification_id,
            models.InAppNotification.user_id == current_user.id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    teacher_id = None
    if notif.action_payload:
        try:
            payload_data = json.loads(notif.action_payload)
            teacher_id = payload_data.get("teacher_id")
        except Exception:
            pass

    if not teacher_id:
        raise HTTPException(status_code=400, detail="Notification does not contain a valid teacher payload")

    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher account not found")

    teacher.teacher_approved = True
    notif.is_read = True

    # Send congratulatory notification to teacher
    congrats = models.InAppNotification(
        user_id=teacher.id,
        title="Teacher Privileges Approved",
        message="Your teacher status has been verified and approved by the administrator! You can now publish exams, manage classes, and access exam modules.",
        type="system",
        link="/teacher-exams",
    )
    db.add(congrats)
    db.commit()

    return {
        "status": "success",
        "message": f"Teacher {teacher.username} has been approved.",
    }

