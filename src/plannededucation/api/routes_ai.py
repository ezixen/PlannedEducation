from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from . import database, models, schemas
from .routes_auth import get_current_user
import os
import tempfile
from google import genai
from google.genai import types

router = APIRouter(prefix="/ai", tags=["ai"])

# Setup Gemini API (Free Tier)
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY", "dummy_key_for_testing")
client = genai.Client(api_key=GENAI_API_KEY)

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

    # Read the file into a temporary location so we can upload it to Gemini
    # Gemini requires the file to be uploaded to their File API for processing
    try:
        content = await file.read()
        
        # Use inline data (Base64) for small images instead of File API to keep it simple and stateless
        import base64
        encoded_image = base64.b64encode(content).decode('utf-8')
        
        prompt = "Transcribe this handwritten math into digital text and LaTeX. Only output the transcription, no chat."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=content, mime_type=file.content_type)
            ]
        )
        return {"transcription": response.text}
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
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=content, mime_type=file.content_type)
            ]
        )
        return {"transcription": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

