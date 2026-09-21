from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from . import database, models, schemas, ai_client
from .routes_auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/ocr-math")
async def ocr_handwritten_math(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    """
    Takes an image of a student's handwritten math problem and translates it 
    into digital text/LaTeX for further AI grading.
    """
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can run OCR grading tools")

    try:
        content = await file.read()
        prompt = "Transcribe this handwritten math into digital text and LaTeX. Only output the transcription, no chat."
        
        result = ai_client.get_ai_response(current_user, prompt, image_bytes=content)
        return {"transcription": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speech-to-text")
async def teacher_audio_feedback(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    """
    Transcribes a teacher's spoken audio memo into text for grading feedback.
    """
    if current_user.role != schemas.RoleEnum.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can run Speech-to-Text")

    try:
        content = await file.read()
        prompt = "Transcribe this teacher's grading feedback audio into text. Only output the transcription, no chat."
        
        result = ai_client.get_ai_response(current_user, prompt, audio_bytes=content)
        return {"transcription": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

