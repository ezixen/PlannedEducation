"""
OCR Routes for PlannedEducation
Endpoints for OCR processing of handwritten exam submissions.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from . import models
from .limiter import limiter
from .ocr_service import (
    HandwritingRecognitionService,
    OCRService,
    get_handwriting_service,
    get_ocr_service,
)
from .routes_auth import get_current_user

router = APIRouter(prefix="/ocr", tags=["ocr"])

# F-038: hard caps on request size / concurrency (free/local; no Redis worker required)
MAX_OCR_BASE64_CHARS = 6_000_000  # ~4.5 MB binary
MAX_OCR_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_OCR_BATCH_ITEMS = 10
MAX_OCR_BULK_FILES = 20
_ocr_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")


def _enforce_base64_cap(data: str) -> None:
    if len(data) > MAX_OCR_BASE64_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image payload exceeds maximum allowed size",
        )


async def _run_ocr(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_ocr_executor, lambda: fn(*args, **kwargs))


class OCRRequest(BaseModel):
    """Request model for OCR processing."""
    image_base64: str = Field(..., max_length=MAX_OCR_BASE64_CHARS, description="Base64 encoded image data")
    language: str = Field(default="eng", description="Tesseract language code")
    is_math: bool = Field(default=False, description="Whether to use math-specific OCR")


class OCRResponse(BaseModel):
    """Response model for OCR processing."""
    text: str
    confidence: float
    language: str
    bounding_boxes: list[dict] | None = None
    error: str | None = None


class OCRBatchRequest(BaseModel):
    """Request model for batch OCR processing."""
    images: list[str] = Field(..., max_length=MAX_OCR_BATCH_ITEMS, description="List of base64 encoded images")
    language: str = Field(default="eng", description="Tesseract language code")
    is_math: bool = Field(default=False, description="Whether to use math-specific OCR")


class OCRBatchResponse(BaseModel):
    """Response model for batch OCR processing."""
    results: list[OCRResponse]


@router.post("/process", response_model=OCRResponse)
@limiter.limit("30/minute")
async def process_ocr(
    request: Request,
    payload: OCRRequest,
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process a single image through OCR.
    Returns extracted text with confidence scores.
    """
    _ = request
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    _enforce_base64_cap(payload.image_base64)
    result = await _run_ocr(
        ocr_service.extract_text_from_base64,
        payload.image_base64,
        language=payload.language,
        config="--psm 6 --oem 3" if payload.is_math else "--psm 6",
    )

    return OCRResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        bounding_boxes=result.bounding_boxes,
        error=result.error
    )


@router.post("/process-upload", response_model=OCRResponse)
@limiter.limit("30/minute")
async def process_ocr_upload(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="eng"),
    is_math: bool = Form(default=False),
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process an uploaded image file through OCR.
    Accepts multipart/form-data with image file.
    """
    _ = request
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    image_data = await file.read(MAX_OCR_UPLOAD_BYTES + 1)
    if len(image_data) > MAX_OCR_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds maximum allowed size",
        )

    config = "--psm 6 --oem 3" if is_math else "--psm 6"
    result = await _run_ocr(ocr_service.extract_text, image_data, language, config)

    return OCRResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        bounding_boxes=result.bounding_boxes,
        error=result.error
    )


@router.post("/batch", response_model=OCRBatchResponse)
@limiter.limit("10/minute")
async def process_ocr_batch(
    request: Request,
    payload: OCRBatchRequest,
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process multiple images through OCR in batch.
    Useful for multi-page exam submissions.
    """
    _ = request
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    if len(payload.images) > MAX_OCR_BATCH_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch limited to {MAX_OCR_BATCH_ITEMS} images",
        )

    results = []
    config = "--psm 6 --oem 3" if payload.is_math else "--psm 6"

    for image_base64 in payload.images:
        _enforce_base64_cap(image_base64)
        result = await _run_ocr(
            ocr_service.extract_text_from_base64,
            image_base64,
            language=payload.language,
            config=config,
        )
        results.append(OCRResponse(
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            bounding_boxes=result.bounding_boxes,
            error=result.error
        ))

    return OCRBatchResponse(results=results)


@router.get("/languages")
async def get_supported_languages(
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """Get list of supported Tesseract languages."""
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    languages = ocr_service.get_supported_languages()
    return {"languages": languages}


@router.get("/health")
async def ocr_health_check(
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """Authenticated readiness for OCR (F-051)."""
    _ = current_user
    return {"status": "ok" if ocr_service.is_available() else "unavailable"}


@router.post("/bulk-upload")
@limiter.limit("5/minute")
async def process_ocr_bulk_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    language: str = Form(default="eng"),
    subject: str = Form(default="math"),
    is_math: bool = Form(default=False),
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process multiple uploaded image files through OCR in bulk.
    Digitizes handwritten tests (math, chemistry, physics, essays, etc.).
    """
    _ = request
    if len(files) > MAX_OCR_BULK_FILES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Bulk upload limited to {MAX_OCR_BULK_FILES} files",
        )
    results = []
    config = "--psm 6 --oem 3" if (is_math or subject in ("math", "physics", "chemistry")) else "--psm 6"

    for idx, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        image_data = await file.read(MAX_OCR_UPLOAD_BYTES + 1)
        if len(image_data) > MAX_OCR_UPLOAD_BYTES:
            results.append({
                "filename": file.filename,
                "page_index": idx + 1,
                "text": "",
                "confidence": 0.0,
                "language": language,
                "subject": subject,
                "error": "File exceeds maximum allowed size",
                "bounding_boxes": [],
            })
            continue
        if ocr_service.is_available():
            result = await _run_ocr(ocr_service.extract_text, image_data, language, config)
            extracted_text = result.text
            conf = result.confidence
            err = result.error
            boxes = result.bounding_boxes
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OCR service not available",
            )

        results.append({
            "filename": file.filename,
            "page_index": idx + 1,
            "text": extracted_text,
            "confidence": conf,
            "language": language,
            "subject": subject,
            "error": err,
            "bounding_boxes": boxes,
        })

    return {"results": results, "total": len(results)}


# ── Handwriting Recognition Routes ───────────────────────────────────────────

class HandwritingRecognizeRequest(BaseModel):
    """Request model for handwriting recognition."""
    image_base64: str = Field(..., max_length=MAX_OCR_BASE64_CHARS, description="Base64 encoded image data")
    language: str = Field(default="en", description="Language code for recognition")
    confidence_threshold: float = Field(default=0.3, description="Minimum confidence (0.0-1.0)")


class HandwritingRecognizeResponse(BaseModel):
    """Response model for handwriting recognition."""
    text: str
    confidence: float
    language: str
    words: list[dict] | None = None
    error: str | None = None
    is_handwritten: bool = True


@router.post("/handwriting/recognize", response_model=HandwritingRecognizeResponse)
@limiter.limit("20/minute")
async def recognize_handwriting(
    request: Request,
    payload: HandwritingRecognizeRequest,
    current_user: models.User = Depends(get_current_user),
    hw_service: HandwritingRecognitionService = Depends(get_handwriting_service),
):
    """
    Recognize handwritten text from an image using EasyOCR.
    Returns per-word confidence scores for teacher review workflow.
    """
    _ = request
    _enforce_base64_cap(payload.image_base64)
    result = await _run_ocr(
        hw_service.recognize_handwriting_from_base64,
        payload.image_base64,
        language=payload.language,
        confidence_threshold=payload.confidence_threshold,
    )

    return HandwritingRecognizeResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        words=result.words,
        error=result.error,
        is_handwritten=result.is_handwritten,
    )


@router.post("/handwriting/recognize-upload", response_model=HandwritingRecognizeResponse)
@limiter.limit("20/minute")
async def recognize_handwriting_upload(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    confidence_threshold: float = Form(default=0.3),
    current_user: models.User = Depends(get_current_user),
    hw_service: HandwritingRecognitionService = Depends(get_handwriting_service),
):
    """
    Recognize handwritten text from an uploaded image file using EasyOCR.
    Accepts multipart/form-data with image file.
    """
    _ = request
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    image_data = await file.read(MAX_OCR_UPLOAD_BYTES + 1)
    if len(image_data) > MAX_OCR_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds maximum allowed size",
        )
    result = await _run_ocr(
        hw_service.recognize_handwriting,
        image_data,
        language=language,
        confidence_threshold=confidence_threshold,
    )

    return HandwritingRecognizeResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        words=result.words,
        error=result.error,
        is_handwritten=result.is_handwritten,
    )


@router.get("/handwriting/health")
async def handwriting_health_check(
    current_user: models.User = Depends(get_current_user),
    hw_service: HandwritingRecognitionService = Depends(get_handwriting_service),
):
    """Authenticated readiness for handwriting OCR (F-051)."""
    _ = current_user
    return {"status": "ok" if hw_service.is_available() else "unavailable"}
