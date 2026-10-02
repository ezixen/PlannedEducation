"""
Speech-to-Text Routes for PlannedEducation
Endpoints for audio transcription using faster-whisper.
"""


from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from . import models
from .routes_auth import get_current_user
from .stt_service import SpeechToTextService, get_stt_service

router = APIRouter(prefix="/stt", tags=["speech-to-text"])


class STTRequest(BaseModel):
    """Request model for STT processing."""
    audio_base64: str = Field(..., description="Base64 encoded audio data")
    language: str | None = Field(default=None, description="Language code (None for auto-detect)")
    task: str = Field(default="transcribe", description="Task: transcribe or translate")


class STTResponse(BaseModel):
    """Response model for STT processing."""
    text: str
    language: str
    language_probability: float
    duration: float
    segments: list[dict] | None = None
    error: str | None = None


class STTBatchRequest(BaseModel):
    """Request model for batch STT processing."""
    audios: list[str] = Field(..., description="List of base64 encoded audio files")
    language: str | None = Field(default=None, description="Language code")
    task: str = Field(default="transcribe", description="Task: transcribe or translate")


class STTBatchResponse(BaseModel):
    """Response model for batch STT processing."""
    results: list[STTResponse]


@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(
    request: STTRequest,
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """
    Transcribe audio from base64 encoded data.
    Returns transcribed text with metadata.
    """
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    result = stt_service.transcribe_from_base64(
        request.audio_base64,
        language=request.language,
        task=request.task
    )

    return STTResponse(
        text=result.text,
        language=result.language,
        language_probability=result.language_probability,
        duration=result.duration,
        segments=result.segments,
        error=result.error
    )


@router.post("/transcribe-upload", response_model=STTResponse)
async def transcribe_audio_upload(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    task: str = Form(default="transcribe"),
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """
    Transcribe an uploaded audio file.
    Accepts multipart/form-data with audio file (WAV, MP3, etc.).
    """
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    # Validate file type
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file"
        )

    # Read file content
    audio_data = await file.read()

    # Transcribe
    result = stt_service.transcribe(
        audio_data,
        language=language,
        task=task
    )

    return STTResponse(
        text=result.text,
        language=result.language,
        language_probability=result.language_probability,
        duration=result.duration,
        segments=result.segments,
        error=result.error
    )


@router.post("/batch", response_model=STTBatchResponse)
async def transcribe_batch(
    request: STTBatchRequest,
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """
    Transcribe multiple audio files in batch.
    Useful for processing multiple audio feedback recordings.
    """
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    results = []

    for audio_base64 in request.audios:
        result = stt_service.transcribe_from_base64(
            audio_base64,
            language=request.language,
            task=request.task
        )
        results.append(STTResponse(
            text=result.text,
            language=result.language,
            language_probability=result.language_probability,
            duration=result.duration,
            segments=result.segments,
            error=result.error
        ))

    return STTBatchResponse(results=results)


@router.get("/languages")
async def get_supported_languages(
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """Get list of supported languages."""
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    languages = stt_service.get_supported_languages()
    return {"languages": languages}


@router.get("/models")
async def get_available_models(
    current_user: models.User = Depends(get_current_user),
):
    """Get list of available Whisper model sizes."""
    return {
        "models": [
            {"id": "tiny", "size": "~39 MB", "speed": "fastest", "accuracy": "lowest"},
            {"id": "base", "size": "~74 MB", "speed": "fast", "accuracy": "good"},
            {"id": "small", "size": "~244 MB", "speed": "medium", "accuracy": "better"},
            {"id": "medium", "size": "~769 MB", "speed": "slow", "accuracy": "high"},
            {"id": "large-v3", "size": "~1550 MB", "speed": "slowest", "accuracy": "highest"},
        ],
        "recommended": "base"
    }


@router.get("/health")
async def stt_health_check(
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """Health check for STT service."""
    return {
        "available": stt_service.is_available(),
        "service": "faster-whisper",
        "model": stt_service.model_size if stt_service.is_available() else "not loaded"
    }
