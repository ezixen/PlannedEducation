"""
OCR Routes for PlannedEducation
Endpoints for OCR processing of handwritten exam submissions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from . import database, models, schemas
from .routes_auth import get_current_user
from .ocr_service import get_ocr_service, OCRService, OCRResult

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
    bounding_boxes: Optional[List[dict]] = None
    error: Optional[str] = None


class OCRBatchRequest(BaseModel):
    """Request model for batch OCR processing."""
    images: List[str] = Field(..., description="List of base64 encoded images")
    language: str = Field(default="eng", description="Tesseract language code")
    is_math: bool = Field(default=False, description="Whether to use math-specific OCR")


class OCRBatchResponse(BaseModel):
    """Response model for batch OCR processing."""
    results: List[OCRResponse]


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