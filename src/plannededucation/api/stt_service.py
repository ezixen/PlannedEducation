"""
Speech-to-Text Service for PlannedEducation
Free, open-source speech recognition using faster-whisper (CTranslate2 optimized Whisper).
Supports local inference without external API dependencies.
"""

import base64
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""
    text: str
    language: str
    language_probability: float
    duration: float
    segments: list[dict[str, Any]] | None = None
    error: str | None = None


class SpeechToTextService:
    """
    Service for Speech-to-Text using faster-whisper.
    Supports multiple languages and various audio formats.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        download_root: str | None = None
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None
        self.available = FASTER_WHISPER_AVAILABLE

        if not self.available:
            logger.warning("faster-whisper not available. Install with: pip install faster-whisper")

    def _get_model(self) -> WhisperModel:
        """Lazy load the Whisper model."""
        if self._model is None:
            if not self.available:
                raise RuntimeError("faster-whisper not installed")

            # Auto-detect device
            if self.device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self.device

            # Auto-detect compute type
            if self.compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
            else:
                compute_type = self.compute_type

            logger.info(f"Loading Whisper model: {self.model_size} on {device} with {compute_type}")
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
                download_root=self.download_root
            )

        return self._model

    def is_available(self) -> bool:
        """Check if STT service is available."""
        return self.available

    def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        task: str = "transcribe",
        beam_size: int = 5,
        vad_filter: bool = True,
        vad_parameters: dict | None = None
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            language: Language code (None for auto-detect)
            task: "transcribe" or "translate" (to English)
            beam_size: Beam size for decoding
            vad_filter: Whether to use Voice Activity Detection
            vad_parameters: VAD parameters dict
            
        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        if not self.available:
            return TranscriptionResult(
                text="",
                language="",
                language_probability=0.0,
                duration=0.0,
                error="faster-whisper not available"
            )

        try:
            model = self._get_model()

            # Write audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            try:
                # Transcribe
                segments, info = model.transcribe(
                    tmp_path,
                    language=language,
                    task=task,
                    beam_size=beam_size,
                    vad_filter=vad_filter,
                    vad_parameters=vad_parameters or {"min_silence_duration_ms": 500}
                )

                # Collect segments
                segment_list = []
                full_text = []

                for segment in segments:
                    segment_dict = {
                        "id": segment.id,
                        "seek": segment.seek,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "tokens": segment.tokens,
                        "temperature": segment.temperature,
                        "avg_logprob": segment.avg_logprob,
                        "compression_ratio": segment.compression_ratio,
                        "no_speech_prob": segment.no_speech_prob,
                    }
                    segment_list.append(segment_dict)
                    full_text.append(segment.text)

                return TranscriptionResult(
                    text=" ".join(full_text).strip(),
                    language=info.language,
                    language_probability=info.language_probability,
                    duration=info.duration,
                    segments=segment_list
                )

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # Ignore cleanup errors

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return TranscriptionResult(
                text="",
                language="",
                language_probability=0.0,
                duration=0.0,
                error=str(e)
            )

    def transcribe_from_base64(
        self,
        base64_data: str,
        language: str | None = None,
        task: str = "transcribe"
    ) -> TranscriptionResult:
        """Transcribe from base64 encoded audio."""
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:audio'):
                base64_data = base64_data.split(',', 1)[1]

            audio_data = base64.b64decode(base64_data)
            return self.transcribe(audio_data, language, task)
        except Exception as e:
            logger.error(f"Base64 decode failed: {e}")
            return TranscriptionResult(
                text="",
                language="",
                language_probability=0.0,
                duration=0.0,
                error=f"Invalid base64 data: {e}"
            )

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages (Whisper supports 99+ languages)."""
        # Whisper supports 99 languages - returning common ones
        return [
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
            "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
            "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
            "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
            "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
            "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
            "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
            "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
        ]


# Global STT service instance (lazy initialization)
_stt_service = None


def get_stt_service(
    model_size: str = "base",
    device: str = "auto",
    compute_type: str = "auto"
) -> SpeechToTextService:
    """Dependency injection for STT service."""
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechToTextService(
            model_size=model_size,
            device=device,
            compute_type=compute_type
        )
    return _stt_service
