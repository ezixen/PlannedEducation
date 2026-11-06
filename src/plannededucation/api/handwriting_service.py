"""Handwriting Recognition Service using EasyOCR.

Provides handwritten text recognition for exam submissions with
per-word confidence scores for teacher review workflow.

Falls back to Tesseract OCR if EasyOCR is not available.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None


@dataclass
class HandwritingWord:
    """A single recognized word with position and confidence."""
    text: str
    confidence: float  # 0.0 - 1.0
    x: int
    y: int
    width: int
    height: int


@dataclass
class HandwritingRecognitionResult:
    """Result of handwriting recognition with per-word data for teacher review."""
    text: str
    confidence: float  # Overall average confidence 0.0 - 1.0
    language: str
    words: list[HandwritingWord] = field(default_factory=list)
    error: str | None = None
    is_handwritten: bool = True
    engine: str = "easyocr"  # "easyocr" or "tesseract"


class HandwritingRecognitionService:
    """
    Handwriting recognition service using EasyOCR.
    Designed for handwritten exam submissions where Tesseract struggles.
    Falls back to Tesseract if EasyOCR is not available.
    """

    def __init__(self, languages: list[str] | None = None, gpu: bool = False):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader = None
        self.available = EASYOCR_AVAILABLE
        if not self.available:
            logger.warning(
                "EasyOCR not available. Handwriting recognition will fall back to Tesseract."
            )

    def _get_reader(self):
        """Lazy load EasyOCR reader."""
        if self._reader is None and self.available:
            try:
                self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR reader: {e}")
                self.available = False
                self._reader = None
        return self._reader

    def is_available(self) -> bool:
        """Check if handwriting recognition service is available."""
        return self.available

    def recognize_handwriting(
        self,
        image_data: bytes,
        language: str = "en",
        confidence_threshold: float = 0.3,
    ) -> HandwritingRecognitionResult:
        """
        Recognize handwritten text from image using EasyOCR.
        Returns per-word confidence scores for teacher review workflow.

        Args:
            image_data: Raw image bytes
            language: Language code for recognition
            confidence_threshold: Minimum confidence to include a word (0.0-1.0)

        Returns:
            HandwritingRecognitionResult with recognized text and per-word data
        """
        reader = self._get_reader()
        if reader is None:
            # Fall back to Tesseract
            return self._fallback_to_tesseract(image_data, language)

        try:
            import numpy as np

            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)

            # Run recognition
            results = reader.readtext(img_array)

            words = []
            full_text_parts = []
            total_conf = 0.0
            count = 0

            for bbox, text, conf in results:
                if conf < confidence_threshold:
                    continue

                # Calculate bounding box
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                word_entry = HandwritingWord(
                    text=text,
                    confidence=round(conf, 3),
                    x=int(min(x_coords)),
                    y=int(min(y_coords)),
                    width=int(max(x_coords) - min(x_coords)),
                    height=int(max(y_coords) - min(y_coords)),
                )
                words.append(word_entry)
                full_text_parts.append(text)
                total_conf += conf
                count += 1

            full_text = " ".join(full_text_parts)
            avg_confidence = total_conf / count if count > 0 else 0.0

            return HandwritingRecognitionResult(
                text=full_text,
                confidence=avg_confidence,
                language=language,
                words=[w.__dict__ for w in words],
                is_handwritten=True,
                engine="easyocr",
            )

        except Exception as e:
            logger.error(f"Handwriting recognition failed: {e}")
            return self._fallback_to_tesseract(image_data, language)

    def _fallback_to_tesseract(
        self, image_data: bytes, language: str = "en"
    ) -> HandwritingRecognitionResult:
        """Fall back to Tesseract OCR when EasyOCR is unavailable."""
        try:
            result = self._extract_tesseract(image_data, language=language, config="--psm 6")
            words = []
            if result.get("bounding_boxes"):
                for box in result["bounding_boxes"]:
                    words.append({
                        "text": box.get("text", ""),
                        "confidence": box.get("confidence", 0) / 100.0,
                        "x": box.get("x", 0),
                        "y": box.get("y", 0),
                        "width": box.get("width", 0),
                        "height": box.get("height", 0),
                    })

            return HandwritingRecognitionResult(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                language=language,
                words=words,
                error=result.get("error"),
                is_handwritten=False,
                engine="tesseract",
            )
        except Exception as e:
            return HandwritingRecognitionResult(
                text="",
                confidence=0.0,
                language=language,
                error=str(e),
                is_handwritten=False,
                engine="tesseract",
            )

    def _extract_tesseract(
        self, image_data: bytes, language: str = "en", config: str = "--psm 6"
    ) -> dict:
        """Extract text using Tesseract as fallback."""
        if not TESSERACT_AVAILABLE:
            return {"text": "", "confidence": 0.0, "language": language,
                    "bounding_boxes": [], "error": "Tesseract not available"}

        try:
            image = Image.open(io.BytesIO(image_data))
            data = pytesseract.image_to_data(
                image, lang=language, config=config,
                output_type=pytesseract.Output.DICT
            )

            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            text = pytesseract.image_to_string(
                image, lang=language, config=config
            ).strip()

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

            return {
                "text": text,
                "confidence": avg_confidence / 100.0,
                "language": language,
                "bounding_boxes": bounding_boxes,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return {"text": "", "confidence": 0.0, "language": language,
                    "bounding_boxes": [], "error": str(e)}

    def recognize_handwriting_from_base64(
        self,
        base64_data: str,
        language: str = "en",
        confidence_threshold: float = 0.3,
    ) -> HandwritingRecognitionResult:
        """Recognize handwriting from base64 encoded image."""
        try:
            if base64_data.startswith("data:image"):
                base64_data = base64_data.split(",", 1)[1]
            image_data = base64.b64decode(base64_data)
            return self.recognize_handwriting(image_data, language, confidence_threshold)
        except Exception as e:
            return HandwritingRecognitionResult(
                text="",
                confidence=0.0,
                language=language,
                error=f"Invalid base64 data: {e}",
                is_handwritten=False,
                engine="tesseract",
            )


# Global handwriting recognition service instance
handwriting_service = HandwritingRecognitionService()


def get_handwriting_service() -> HandwritingRecognitionService:
    """Dependency injection for handwriting recognition service."""
    return handwriting_service
