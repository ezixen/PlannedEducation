"""
Speech-to-Text Routes for PlannedEducation
Endpoints for audio transcription using faster-whisper.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from . import models
from .limiter import limiter
from .routes_auth import get_current_user
from .stt_service import SpeechToTextService, get_stt_service

router = APIRouter(prefix="/stt", tags=["speech-to-text"])

# F-038: hard caps on request size / concurrency
MAX_STT_BASE64_CHARS = 12_000_000  # ~9 MB binary
MAX_STT_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_STT_BATCH_ITEMS = 5
_stt_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")


def _enforce_base64_cap(data: str) -> None:
    if len(data) > MAX_STT_BASE64_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio payload exceeds maximum allowed size",
        )


async def _run_stt(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_stt_executor, lambda: fn(*args, **kwargs))


class STTRequest(BaseModel):
    """Request model for STT processing."""
    audio_base64: str = Field(..., max_length=MAX_STT_BASE64_CHARS, description="Base64 encoded audio data")
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
    audios: list[str] = Field(..., max_length=MAX_STT_BATCH_ITEMS, description="List of base64 encoded audio files")
    language: str | None = Field(default=None, description="Language code")
    task: str = Field(default="transcribe", description="Task: transcribe or translate")


class STTBatchResponse(BaseModel):
    """Response model for batch STT processing."""
    results: list[STTResponse]


@router.post("/transcribe", response_model=STTResponse)
@limiter.limit("10/minute")
async def transcribe_audio(
    request: Request,
    payload: STTRequest,
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """
    Transcribe audio from base64 encoded data.
    Returns transcribed text with metadata.
    """
    _ = request
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    _enforce_base64_cap(payload.audio_base64)
    result = await _run_stt(
        stt_service.transcribe_from_base64,
        payload.audio_base64,
        language=payload.language,
        task=payload.task,
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
@limiter.limit("10/minute")
async def transcribe_audio_upload(
    request: Request,
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
    _ = request
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file"
        )

    audio_data = await file.read(MAX_STT_UPLOAD_BYTES + 1)
    if len(audio_data) > MAX_STT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded audio exceeds maximum allowed size",
        )

    result = await _run_stt(
        stt_service.transcribe,
        audio_data,
        language=language,
        task=task,
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
@limiter.limit("5/minute")
async def transcribe_batch(
    request: Request,
    payload: STTBatchRequest,
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """
    Transcribe multiple audio files in batch.
    Useful for processing multiple audio feedback recordings.
    """
    _ = request
    if not stt_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT service not available. faster-whisper not installed."
        )

    if len(payload.audios) > MAX_STT_BATCH_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch limited to {MAX_STT_BATCH_ITEMS} audio files",
        )

    results = []

    for audio_base64 in payload.audios:
        _enforce_base64_cap(audio_base64)
        result = await _run_stt(
            stt_service.transcribe_from_base64,
            audio_base64,
            language=payload.language,
            task=payload.task,
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
    """Authenticated model catalog (F-051)."""
    _ = current_user
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
    current_user: models.User = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    """Authenticated readiness for STT (F-051)."""
    _ = current_user
    return {"status": "ok" if stt_service.is_available() else "unavailable"}
