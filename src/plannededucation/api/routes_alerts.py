"""Alert webhook endpoints for Alertmanager integration."""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertLabel(BaseModel):
    model_config = ConfigDict(extra="allow")

    alertname: str
    job: str | None = None
    severity: str | None = None
    slo: str | None = None
    burn_rate: str | None = None
    component: str | None = None
    csf_function: str | None = None
    csf_category: str | None = None


class AlertAnnotation(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    description: str | None = None


class Alert(BaseModel):
    labels: AlertLabel
    annotations: AlertAnnotation
    startsAt: str
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerPayload(BaseModel):
    receiver: str
    status: str
    alerts: list[Alert]
    groupLabels: dict[str, str]
    commonLabels: dict[str, str]
    commonAnnotations: dict[str, str]
    externalURL: str | None = None
    version: str
    groupKey: str
    truncatedAlerts: int = 0


@router.post("/webhook")
async def alertmanager_webhook(payload: AlertmanagerPayload, request: Request):
    """
    Receive alerts from Alertmanager.

    This endpoint processes Alertmanager webhook payloads and logs them.
    In production, you would integrate with your notification system
    (email, Slack, PagerDuty, etc.) here.
    """
    logger.info(
        "Alertmanager webhook received",
        extra={
            "receiver": payload.receiver,
            "status": payload.status,
            "alert_count": len(payload.alerts),
            "group_key": payload.groupKey,
            "external_url": payload.externalURL,
        }
    )

    for alert in payload.alerts:
        logger.warning(
            "Alert fired",
            extra={
                "alertname": alert.labels.alertname,
                "severity": alert.labels.severity,
                "job": alert.labels.job,
                "slo": alert.labels.slo,
                "burn_rate": alert.labels.burn_rate,
                "component": alert.labels.component,
                "csf_function": alert.labels.csf_function,
                "csf_category": alert.labels.csf_category,
                "summary": alert.annotations.summary,
                "description": alert.annotations.description,
                "starts_at": alert.startsAt,
                "ends_at": alert.endsAt,
                "fingerprint": alert.fingerprint,
            }
        )

    # In production, you would:
    # 1. Store alerts in database for audit trail
    # 2. Forward to notification systems (email, Slack, PagerDuty, etc.)
    # 3. Trigger incident response workflows
    # 4. Update alert status in dashboard

    return {"status": "received", "alert_count": len(payload.alerts)}


@router.get("/health")
async def alerts_health():
    """Health check for alerts endpoint."""
    return {"status": "healthy", "service": "alerts"}
