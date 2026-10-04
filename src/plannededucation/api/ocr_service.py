"""
OCR Service for PlannedEducation
Free, open-source OCR using Tesseract via pytesseract.
Handles handwritten math and text recognition for AI grading pipeline.
"""

import base64
import io
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

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


@dataclass
class MathOCRResult:
    """Result of math OCR processing with LaTeX conversion."""
    text: str
    latex: str
    confidence: float
    language: str
    bounding_boxes: list[dict[str, Any]] | None = None
    error: str | None = None
    symbols: list[dict[str, Any]] = field(default_factory=list)
    structure: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)


@dataclass
class MathSymbol:
    """Detected math symbol with position and classification."""
    symbol: str
    latex: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    symbol_type: str  # 'operator', 'number', 'variable', 'function', 'bracket', 'other'


class OCRService:
    """
    Service for Optical Character Recognition using Tesseract.
    Supports multiple languages and math-specific recognition.
    """

    def __init__(self):
        self.available = TESSERACT_AVAILABLE
        if not self.available:
            logger.warning(
                "Tesseract OCR not available. Install pytesseract and tesseract-ocr binary."
            )

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
        """Extract text from image data.

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
        math_config = (
            "--psm 6 --oem 3 "
            "-c tessedit_char_whitelist="
            "0123456789+-=()[]{}<>^_/\\.,"
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )

        return self.extract_text(image_data, language, math_config)

    def get_supported_languages(self) -> list[str]:
        """Get list of supported Tesseract languages."""
        if not self.available:
            return []
        try:
            return pytesseract.get_languages(config='')
        except Exception:
            return ['eng']

    # ==================== MATH OCR PIPELINE ====================

    def _deskew_image(self, image: Image.Image) -> Image.Image:
        """Deskew image using OpenCV for better OCR accuracy."""
        if not OPENCV_AVAILABLE:
            return image
        
        try:
            # Convert PIL to OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            
            # Threshold
            _, thresh = cv2.threshold(cv_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            # Find largest contour (assumed to be text)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[-1]
            
            # Correct angle
            if angle < -45:
                angle = 90 + angle
            
            # Rotate if needed
            if abs(angle) > 0.5:
                (h, w) = image.size
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(np.array(image), M, (w, h), 
                                         flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return Image.fromarray(rotated)
            
            return image
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
            return image

    def _detect_math_lines(self, image: Image.Image) -> list[dict]:
        """Detect lines of mathematical text in the image."""
        if not OPENCV_AVAILABLE:
            return []
        
        try:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(cv_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Horizontal projection to find lines
            horizontal_proj = np.sum(thresh, axis=1)
            
            # Find line boundaries
            lines = []
            in_line = False
            start = 0
            
            for i, val in enumerate(horizontal_proj):
                if val > 0 and not in_line:
                    in_line = True
                    start = i
                elif val == 0 and in_line:
                    in_line = False
                    if i - start > 10:  # Minimum line height
                        lines.append({'y_start': start, 'y_end': i, 'height': i - start})
            
            if in_line and len(horizontal_proj) - start > 10:
                lines.append({'y_start': start, 'y_end': len(horizontal_proj), 'height': len(horizontal_proj) - start})
            
            return lines
        except Exception as e:
            logger.warning(f"Line detection failed: {e}")
            return []

    def _detect_math_symbols(self, image: Image.Image, line: dict) -> list[MathSymbol]:
        """Detect individual math symbols in a line using contour analysis."""
        if not OPENCV_AVAILABLE:
            return []
        
        try:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(cv_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Crop to line region
            y_start = line['y_start']
            y_end = line['y_end']
            line_img = thresh[line['y_start']:line['y_end'], :]
            
            # Find contours
            contours, _ = cv2.findContours(line_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            symbols = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w < 5 or h < 5:  # Filter noise
                    continue
                
                # Extract symbol region
                symbol_img = line_img[y:y+h, x:x+w]
                
                # Classify symbol type based on shape
                symbol_type = self._classify_symbol(contour, w, h)
                
                # Get LaTeX representation
                latex = self._symbol_to_latex(symbol_type, symbol_img)
                
                symbols.append(MathSymbol(
                    symbol=symbol_type,
                    latex=latex,
                    confidence=0.8,  # Placeholder
                    x=x,
                    y=y + line['y_start'],
                    width=w,
                    height=h,
                    symbol_type=symbol_type
                ))
            
            return symbols
        except Exception as e:
            logger.warning(f"Symbol detection failed: {e}")
            return []

    def _symbol_to_latex(self, symbol_type: str, symbol_img: np.ndarray) -> str:
        """Convert detected symbol to LaTeX."""
        # This is a simplified mapping - in production, use a trained classifier
        latex_map = {
            'operator': '\\times',
            'bracket': '\\left( \\right)',
            'dot': '\\cdot',
            'number': '0',  # Placeholder
            'variable': 'x',
            'operator': '+',
        }
        return latex_map.get(symbol_type, 'x')

    def _convert_to_latex(self, text: str, symbols: list[MathSymbol]) -> str:
        """Convert OCR text and symbols to LaTeX."""
        # Replace common patterns with LaTeX
        latex = text
        
        # Replace common math patterns
        replacements = {
            r'(\d+)\s*/\s*(\d+)': r'\\frac{\1}{\2}',
            r'(\d+)\s*\^\s*(\d+)': r'\1^{\2}',
            r'sqrt\s*\(([^)]+)\)': r'\\sqrt{\1}',
            r'sin\s*\(([^)]+)\)': r'\\sin(\1)',
            r'cos\s*\(([^)]+)\)': r'\\cos(\1)',
            r'tan\s*\(([^)]+)\)': r'\\tan(\1)',
            r'log\s*\(([^)]+)\)': r'\\log(\1)',
            r'lim\s*\(([^)]+)\)': r'\\lim_{\1}',
            r'sum\s*\(([^)]+)\)': r'\\sum_{\1}',
            r'int\s*\(([^)]+)\)': r'\\int_{\1}',
            r'pi': r'\\pi',
            r'alpha': r'\\alpha',
            r'beta': r'\\beta',
            r'gamma': r'\\gamma',
            r'theta': r'\\theta',
            r'lambda': r'\\lambda',
            r'sigma': r'\\sigma',
            r'integral': r'\\int',
            r'infinity': r'\\infty',
            r'partial': r'\\partial',
            r'nabla': r'\\nabla',
            r'pm': r'\\pm',
            r'leq': r'\\le',
            r'geq': r'\\ge',
            r'neq': r'\\neq',
            r'approx': r'\\approx',
            r'times': r'\\times',
            r'div': r'\\div',
        }
        
        for pattern, replacement in replacements.items():
            latex = re.sub(pattern, replacement, latex, flags=re.IGNORECASE)
        
        return latex

    def _validate_math(self, latex: str) -> dict:
        """Validate LaTeX math expression for syntax errors."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check balanced brackets
        brackets = {'(': ')', '[': ']', '{': '}', '\\{': '\\}', '\\(': '\\)', '\\[': '\\]'}
        stack = []
        for i, char in enumerate(latex):
            if char in '([{':
                stack.append((char, i))
            elif char in ')]}':
                if not stack:
                    validation['valid'] = False
                    validation['errors'].append(f'Unmatched closing bracket at position {i}')
                else:
                    open_bracket, pos = stack.pop()
                    expected = brackets.get(open_bracket)
                    if expected and char != expected:
                        validation['warnings'].append(f'Mismatched brackets at position {i}: {open_bracket}...{char}')
        
        if stack:
            validation['valid'] = False
            validation['errors'].append(f'Unclosed brackets: {stack}')
        
        # Check for common LaTeX errors
        if '\\frac' in latex and '{' not in latex:
            validation['warnings'].append('\\frac found without braces')
        
        return validation

    def extract_math_pipeline(
        self,
        image_data: bytes,
        language: str = "eng",
        return_latex: bool = True,
        validate: bool = True
    ) -> MathOCRResult:
        """
        Complete math OCR pipeline:
        1. Deskew image
        2. Detect lines
        3. Detect symbols in each line
        4. Convert to LaTeX
        5. Validate LaTeX
        """
        if not self.available:
            return MathOCRResult(
                text="",
                latex="",
                confidence=0.0,
                language=language,
                error="Tesseract not available"
            )
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Step 1: Deskew
            image = self._deskew_image(image)
            
            # Step 2: Preprocess
            image = self._preprocess_image(image)
            
            # Step 3: Detect lines
            lines = self._detect_math_lines(image)
            
            # Step 4: Extract text with Tesseract (math config)
            math_config = (
                "--psm 6 --oem 3 "
                "-c tessedit_char_whitelist="
                "0123456789+-=()[]{}<>^_/\\.,"
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            )
            
            result = self.extract_text(
                io.BytesIO(),
                language=language,
                config=math_config
            )
            
            # Actually extract from image
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes = image_bytes.getvalue()
            
            text_result = self.extract_text(image_bytes, language, math_config)
            
            # Step 5: Detect symbols in each line
            all_symbols = []
            for line in self._detect_math_lines(image):
                symbols = self._detect_math_symbols(image, line)
                all_symbols.extend(symbols)
            
            # Step 5: Convert to LaTeX
            latex = ""
            if return_latex:
                latex = self._convert_to_latex(text_result.text, all_symbols)
            
            # Step 6: Validate
            validation = {}
            if validate:
                validation = self._validate_math(latex)
            
            # Calculate overall confidence
            confidence = text_result.confidence
            
            return MathOCRResult(
                text=text_result.text,
                latex=latex,
                confidence=confidence,
                language=language,
                bounding_boxes=text_result.bounding_boxes,
                symbols=[s.__dict__ for s in all_symbols],
                structure={'lines': len(self._detect_math_lines(image))},
                validation=validation
            )
            
        except Exception as e:
            logger.error(f"Math OCR pipeline failed: {e}")
            return MathOCRResult(
                text="",
                latex="",
                confidence=0.0,
                language=language,
                error=str(e)
            )

    def extract_math_advanced(
        self,
        image_data: bytes,
        language: str = "eng",
        return_latex: bool = True,
        validate: bool = True
    ) -> MathOCRResult:
        """
        Advanced math OCR with full pipeline.
        """
        return self.extract_math_pipeline(image_data, language, return_latex, validate)


# Global OCR service instance
ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    """Dependency injection for OCR service."""
    return ocr_service
