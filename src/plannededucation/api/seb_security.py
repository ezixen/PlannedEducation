import hashlib
import hmac
import os
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from . import database, models


def verify_seb_request(
    request: Request,
    exam_id: str,
    db: Session = Depends(database.get_db),
) -> bool:
    """
    Validates the X-SafeExamBrowser-RequestHash header.

    SEB computes the hash as: SHA256(url + seb_config_key)
    where `url` is the full request URL including query string.

    In development mode (ALLOW_DEV_SEB_BYPASS=true), this check is skipped
    so you can test without actually running Safe Exam Browser.
    """
    env = os.getenv("PLANNED_EDUCATION_ENV")
    if (
        env in ("development", "test")
        and os.getenv("ALLOW_DEV_SEB_BYPASS", "").lower() == "true"
    ):
        return True

    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if not exam.seb_config_key:
        raise HTTPException(
            status_code=409,
            detail="This exam has no Safe Exam Browser configuration. "
                   "Generate a .seb config file first.",
        )

    seb_header = request.headers.get("X-SafeExamBrowser-RequestHash")
    if not seb_header:
        raise HTTPException(
            status_code=403,
            detail="Safe Exam Browser is required. "
                   "Please launch the exam via the .seb config file.",
        )

    # Recompute expected hash
    url = str(request.url)
    expected_hash = hashlib.sha256(
        (url + exam.seb_config_key).encode("utf-8")
    ).hexdigest()

    # Constant-time comparison prevents timing side-channel attacks
    if not hmac.compare_digest(expected_hash, seb_header.lower()):
        raise HTTPException(
            status_code=403,
            detail="SEB security violation: request hash mismatch.",
        )

    return True
