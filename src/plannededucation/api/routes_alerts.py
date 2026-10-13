"""Alert webhook endpoints for Alertmanager integration."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertLabel(BaseModel):
    alertname: str
    job: Optional[str] = None
    severity: Optional[str] = None
    slo: Optional[str] = None
    burn_rate: Optional[str] = None
    component: Optional[str] = None
    csf_function: Optional[str] = None
    csf_category: Optional[str] = None
    # Allow additional labels
    class Config:
        extra = "allow"


class AlertAnnotation(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    class Config:
        extra = "allow"


class Alert(BaseModel):
    labels: AlertLabel
    annotations: AlertAnnotation
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None


class AlertmanagerPayload(BaseModel):
    receiver: str
    status: str
    alerts: List[Alert]
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: Optional[str] = None
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