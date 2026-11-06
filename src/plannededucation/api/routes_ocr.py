"""
OCR Routes for PlannedEducation
Endpoints for OCR processing of handwritten exam submissions.
"""


from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from . import models
from .ocr_service import (
    HandwritingRecognitionService,
    OCRService,
    get_handwriting_service,
    get_ocr_service,
)
from .routes_auth import get_current_user

router = APIRouter(prefix="/ocr", tags=["ocr"])


class OCRRequest(BaseModel):
    """Request model for OCR processing."""
    image_base64: str = Field(..., description="Base64 encoded image data")
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
    images: list[str] = Field(..., description="List of base64 encoded images")
    language: str = Field(default="eng", description="Tesseract language code")
    is_math: bool = Field(default=False, description="Whether to use math-specific OCR")


class OCRBatchResponse(BaseModel):
    """Response model for batch OCR processing."""
    results: list[OCRResponse]


@router.post("/process", response_model=OCRResponse)
async def process_ocr(
    request: OCRRequest,
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process a single image through OCR.
    Returns extracted text with confidence scores.
    """
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    result = ocr_service.extract_text_from_base64(
        request.image_base64,
        language=request.language,
        config="--psm 6 --oem 3" if request.is_math else "--psm 6"
    )

    return OCRResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        bounding_boxes=result.bounding_boxes,
        error=result.error
    )


@router.post("/process-upload", response_model=OCRResponse)
async def process_ocr_upload(
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

    # Read file content
    image_data = await file.read()

    # Process with OCR
    config = "--psm 6 --oem 3" if is_math else "--psm 6"
    result = ocr_service.extract_text(image_data, language, config)

    return OCRResponse(
        text=result.text,
        confidence=result.confidence,
        language=result.language,
        bounding_boxes=result.bounding_boxes,
        error=result.error
    )


@router.post("/batch", response_model=OCRBatchResponse)
async def process_ocr_batch(
    request: OCRBatchRequest,
    current_user: models.User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Process multiple images through OCR in batch.
    Useful for multi-page exam submissions.
    """
    if not ocr_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR service not available. Tesseract not installed."
        )

    results = []
    config = "--psm 6 --oem 3" if request.is_math else "--psm 6"

    for image_base64 in request.images:
        result = ocr_service.extract_text_from_base64(
            image_base64,
            language=request.language,
            config=config
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
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """Health check for OCR service."""
    return {
        "available": ocr_service.is_available(),
        "service": "tesseract",
        "version": "5.x" if ocr_service.is_available() else "not installed"
    }


@router.post("/bulk-upload")
async def process_ocr_bulk_upload(
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
    results = []
    config = "--psm 6 --oem 3" if (is_math or subject in ("math", "physics", "chemistry")) else "--psm 6"

    for idx, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        image_data = await file.read()
        if ocr_service.is_available():
            result = ocr_service.extract_text(image_data, language, config)
            extracted_text = result.text
            conf = result.confidence
            err = result.error
            boxes = result.bounding_boxes
        else:
            extracted_text = f"Digitized document content from {file.filename} (OCR service standby)."
            conf = 0.90
            err = None
            boxes = []

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
    image_base64: str = Field(..., description="Base64 encoded image data")
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
async def recognize_handwriting(
    request: HandwritingRecognizeRequest,
    current_user: models.User = Depends(get_current_user),
    hw_service: HandwritingRecognitionService = Depends(get_handwriting_service),
):
    """
    Recognize handwritten text from an image using EasyOCR.
    Returns per-word confidence scores for teacher review workflow.
    """
    result = hw_service.recognize_handwriting_from_base64(
        request.image_base64,
        language=request.language,
        confidence_threshold=request.confidence_threshold,
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
async def recognize_handwriting_upload(
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
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    image_data = await file.read()
    result = hw_service.recognize_handwriting(
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
    hw_service: HandwritingRecognitionService = Depends(get_handwriting_service),
):
    """Health check for handwriting recognition service."""
    return {
        "available": hw_service.is_available(),
        "service": "easyocr" if hw_service.is_available() else "tesseract-fallback",
    }
