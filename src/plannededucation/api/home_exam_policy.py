"""Home-exam / remote proctoring policy (platform + per-exam gates).

Classroom exams are the default. Webcam, microphone, gaze, and related GDPR
surfaces stay off unless:
1. A superadmin enables ``home_exam_proctoring_enabled`` in deployment config, and
2. The teacher opts the specific exam into ``home_exam_enabled``.
"""

from __future__ import annotations

from fastapi import HTTPException

from . import models
from .deployment_config import load_deployment_config


def is_platform_home_exam_enabled() -> bool:
    cfg = load_deployment_config()
    return bool(cfg.get("home_exam_proctoring_enabled", False))


def assert_platform_home_exam_enabled() -> None:
    if not is_platform_home_exam_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Home-exam proctoring is disabled on this deployment. "
                "A superadmin must enable the beta Home-exam features first."
            ),
        )


def assert_exam_allows_home_proctoring(exam: models.Exam | None) -> None:
    assert_platform_home_exam_enabled()
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    if not bool(getattr(exam, "home_exam_enabled", False)):
        raise HTTPException(
            status_code=403,
            detail=(
                "This exam is configured for classroom delivery only. "
                "Home-exam webcam/microphone/gaze features are not enabled for it."
            ),
        )


def feature_status_payload() -> dict:
    enabled = is_platform_home_exam_enabled()
    return {
        "home_exam_proctoring_enabled": enabled,
        "beta": True,
        "label": "home_exam_proctoring_beta",
        "legal_notice": (
            "Home-exam webcam, microphone, and gaze features are optional beta "
            "capabilities. Laws differ by country; review local guidance before use. "
            "Additional coding may be required to comply with your jurisdiction."
        ),
    }
