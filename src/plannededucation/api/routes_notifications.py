"""
In-App Notification and Internal Password Reset Request Routes for PlannedEducation.
Handles in-platform alerts, unread counts, teacher approval notifications,
and student-to-teacher/parent password reset requests.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models, schemas
from .email_service import send_email
from .routes_admin import generate_temporary_password
from .routes_auth import get_current_user, get_password_hash

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
def request_password_reset_internal(
    payload: RequestPasswordResetInternalPayload,
    db: Session = Depends(database.get_db),
):
    """
    Allow students or teachers who cannot log in to request an in-platform password reset
    from their teacher, parent, or an administrator.
    """
    lookup = payload.identifier.strip().lower()
    user = (
        db.query(models.User)
        .filter((models.User.email == lookup) | (models.User.username == lookup))
        .first()
    )
    if not user:
        # Generic response to prevent user enumeration
        return {
            "status": "success",
            "message": "If this account exists, your password reset request has been dispatched to your designated supervisor.",
        }

    recipients: list[models.User] = []

    if payload.target_role == "teacher":
        # Find teachers linked through classes or relationships
        # Or fall back to active teachers in the system
        teachers = (
            db.query(models.User)
            .filter(models.User.role == "teacher", models.User.is_active == True)
            .all()
        )
        recipients.extend(teachers)

    elif payload.target_role == "parent":
        # Find parents linked to this student
        rel_parents = (
            db.query(models.User)
            .join(models.AccountRelationship, models.AccountRelationship.parent_id == models.User.id)
            .filter(models.AccountRelationship.student_id == user.id)
            .all()
        )
        recipients.extend(rel_parents)
        if not recipients:
            # If no parent linked, fallback to admins
            admins = db.query(models.User).filter((models.User.is_admin == True) | (models.User.role == "admin")).all()
            recipients.extend(admins)

    elif payload.target_role == "admin":
        admins = db.query(models.User).filter((models.User.is_admin == True) | (models.User.role == "admin")).all()
        recipients.extend(admins)

    # De-duplicate recipients
    recipient_ids = set()
    for rec in recipients:
        if rec.id not in recipient_ids and rec.id != user.id:
            recipient_ids.add(rec.id)
            action_data = {
                "requester_id": user.id,
                "requester_email": user.email,
                "requester_username": user.username,
                "requester_name": user.full_name or user.username,
                "requester_role": user.role,
                "note": payload.note or "Password reset requested via platform.",
            }
            notif = models.InAppNotification(
                user_id=rec.id,
                title="Password Reset Request",
                message=f"{user.full_name or user.username} ({user.email}) requested a password reset. Note: {payload.note or 'No note provided'}.",
                type="password_reset_request",
                link="/settings",
                action_payload=json.dumps(action_data),
            )
            db.add(notif)

    db.commit()

    return {
        "status": "success",
        "message": f"Password reset request dispatched to your {payload.target_role}(s). They will review and reset your password inside the platform.",
    }


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
        if current_user.role == "teacher" and target_user.role != "student":
            raise HTTPException(status_code=403, detail="Teachers can only approve password resets for students.")
        if current_user.role == "parent":
            # Check linkage
            link_exists = db.query(models.AccountRelationship).filter(
                models.AccountRelationship.parent_id == current_user.id,
                models.AccountRelationship.student_id == target_user.id,
            ).first()
            if not link_exists:
                raise HTTPException(status_code=403, detail="Parents can only reset passwords for their linked children.")

    # Determine temporary password
    if payload.new_password and payload.new_password.strip():
        temp_pwd = payload.new_password.strip()
    else:
        temp_pwd = generate_temporary_password()

    target_user.hashed_password = get_password_hash(temp_pwd)
    target_user.refresh_token_hash = None
    target_user.refresh_token_expires = None

    # Mark original notification as read
    notif.is_read = True

    # Send in-app notification to the user
    user_notif = models.InAppNotification(
        user_id=target_user.id,
        title="Password Reset Approved",
        message=f"Your password reset request was approved by {current_user.full_name or current_user.username}. Your temporary password is: {temp_pwd}. Please change it upon login.",
        type="system",
        link="/settings",
    )
    db.add(user_notif)
    db.commit()

    # If email is configured, also dispatch email notice
    try:
        await send_email(
            to_email=target_user.email,
            subject="PlannedEducation — Password Reset Approved",
            text_content=(
                f"Hello {target_user.full_name or target_user.username},\n\n"
                f"Your password reset request was approved by {current_user.full_name or current_user.username}.\n\n"
                f"Your temporary password is:\n\n"
                f"    {temp_pwd}\n\n"
                f"Please log in to PlannedEducation and update your password in Settings.\n\n"
                f"— PlannedEducation Platform"
            ),
        )
    except Exception as exc:
        logger.warning(f"Could not dispatch password reset email: {exc}")

    return {
        "status": "success",
        "message": f"Password for {target_user.username} was reset successfully.",
        "temporary_password": temp_pwd,
    }


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

