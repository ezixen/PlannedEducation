"""
OCR Service for PlannedEducation
Free, open-source OCR using Tesseract via pytesseract.
Handles handwritten math and text recognition for AI grading pipeline.
"""

import base64
import io
import logging
from dataclasses import dataclass
from typing import Any

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing."""
    text: str
    confidence: float
    language: str
    bounding_boxes: list[dict[str, Any]] | None = None
    error: str | None = None


class OCRService:
    """
    Service for Optical Character Recognition using Tesseract.
    Supports multiple languages and math-specific recognition.
    """
    
    def __init__(self):
        self.available = TESSERACT_AVAILABLE
        if not self.available:
            logger.warning("Tesseract OCR not available. Install pytesseract and tesseract-ocr binary.")
    
    def is_available(self) -> bool:
        """Check if OCR service is available."""
        return self.available
    
    def extract_text(
        self,
        image_data: bytes,
        language: str = "eng",
        config: str = "--psm 6",
        preprocess: bool = True
    ) -> OCRResult:
        """
        Extract text from image data.
        
        Args:
            image_data: Raw image bytes
            language: Tesseract language code (eng, math, etc.)
            config: Tesseract config string
            preprocess: Whether to apply image preprocessing
            
        Returns:
            OCRResult with extracted text and metadata
        """
        if not self.available:
            return OCRResult(
                text="",
                confidence=0.0,
                language=language,
                error="Tesseract not available"
            )
        
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess if requested
            if preprocess:
                image = self._preprocess_image(image)
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(
                image,
                lang=language,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract text
            text = pytesseract.image_to_string(
                image,
                lang=language,
                config=config
            ).strip()
            
            # Get bounding boxes for each word
            bounding_boxes = []
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    bounding_boxes.append({
                        'text': data['text'][i],
                        'confidence': data['conf'][i],
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'block_num': data['block_num'][i],
                        'line_num': data['line_num'][i],
                    })
            
            return OCRResult(
                text=text,
                confidence=avg_confidence / 100.0,  # Normalize to 0-1
                language=language,
                bounding_boxes=bounding_boxes
            )
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                language=language,
                error=str(e)
            )
    
    def extract_text_from_base64(
        self,
        base64_data: str,
        language: str = "eng",
        config: str = "--psm 6"
    ) -> OCRResult:
        """Extract text from base64 encoded image."""
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',', 1)[1]
            
            image_data = base64.b64decode(base64_data)
            return self.extract_text(image_data, language, config)
        except Exception as e:
            logger.error(f"Base64 decode failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                language=language,
                error=f"Invalid base64 data: {e}"
            )
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.
        - Convert to grayscale
        - Increase contrast
        - Resize if too small
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Resize if too small (Tesseract works better with larger images)
        min_dimension = 1000
        if image.width < min_dimension or image.height < min_dimension:
            scale = max(min_dimension / image.width, min_dimension / image.height)
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        return image
    
    def extract_math(
        self,
        image_data: bytes,
        language: str = "eng"
    ) -> OCRResult:
        """
        Extract mathematical expressions from image.
        Uses Tesseract with math-specific configuration.
        """
        # Math-specific config: single block, sparse text
        math_config = "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789+-=()[]{}<>^_/\\.,abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        return self.extract_text(image_data, language, math_config)
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported Tesseract languages."""
        if not self.available:
            return []
        try:
            return pytesseract.get_languages(config='')
        except Exception:
            return ['eng']


# Global OCR service instance
ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    """Dependency injection for OCR service."""
    return ocr_service