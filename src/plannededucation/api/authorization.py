"""Shared authorization policies for security-sensitive domain operations.

Classroom-facing explanations of teacher approval live in docs/user/.
Engineering contracts and audit status live in docs/dev/SECURITY_ARCHITECTURE.md.
"""

from fastapi import HTTPException, status

from . import models


def require_exam_author(user: models.User) -> models.User:
    """Require an approved teacher or administrator for exam authoring (F-014)."""
    if user.is_admin or user.role == "admin":
        return user
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approved teachers and administrators can author exams.",
        )
    if not getattr(user, "teacher_approved", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your teacher account is pending administrator approval before you can create or manage exams.",
        )
    return user
