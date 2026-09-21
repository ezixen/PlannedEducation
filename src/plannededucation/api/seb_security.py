import hashlib
import hmac
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from . import database, models

def verify_seb_request(request: Request, exam_id: int, db: Session = Depends(database.get_db)):
    """
    Validates the X-SafeExamBrowser-RequestHash header.
    The hash is computed by SEB as SHA256(URL + SEB_CONFIG_KEY).
    """
    import os
    if os.getenv("PLANNED_EDUCATION_ENV") == "development" and os.getenv("ALLOW_DEV_AUTH") == "true":
        return True

    # 1. Fetch Exam SEB Config Key
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if not exam.seb_config_key:
        raise HTTPException(
            status_code=409,
            detail="This exam has no Safe Exam Browser configuration and cannot be started."
        )

    # 2. Extract SEB Header
    seb_header = request.headers.get("X-SafeExamBrowser-RequestHash")
    if not seb_header:
        raise HTTPException(
            status_code=403, 
            detail="Safe Exam Browser is required. Please launch the exam via the .seb config file."
        )

    # 3. Compute expected hash
    # The URL must exactly match what SEB sends (including query params)
    url = str(request.url)
    payload = url + exam.seb_config_key
    expected_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    if not hmac.compare_digest(expected_hash, seb_header):
        raise HTTPException(
            status_code=403,
            detail="SEB Security Violation: Config Key Hash mismatch. You are using an unauthorized browser or modified SEB."
        )
    
    return True

