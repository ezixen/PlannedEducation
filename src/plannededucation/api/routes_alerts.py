"""Alert webhook endpoints for Alertmanager integration."""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from . import database, models

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
async def alertmanager_webhook(
    payload: AlertmanagerPayload,
    request: Request,
    db: Session = Depends(database.get_db),
):
    """
    Receive alerts from Alertmanager.

    This endpoint processes Alertmanager webhook payloads, stores them in the database,
    and can forward to notification systems (email, Slack, PagerDuty, etc.).
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
        # Store alert in database
        alert_record = models.Alert(
            fingerprint=alert.fingerprint,
            alertname=alert.labels.alertname,
            status=models.AlertStatus.firing if payload.status == "firing" else models.AlertStatus.resolved,
            severity=models.AlertSeverity(alert.labels.severity) if alert.labels.severity in ["critical", "warning", "info"] else models.AlertSeverity.info,
            labels_json=json.dumps({k: v for k, v in alert.labels.model_dump().items() if v is not None}),
            annotations_json=json.dumps({k: v for k, v in alert.annotations.model_dump().items() if v is not None}) if alert.annotations else None,
            starts_at=datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00")),
            ends_at=datetime.fromisoformat(alert.endsAt.replace("Z", "+00:00")) if alert.endsAt else None,
            resolved_at=datetime.now(UTC) if payload.status == "resolved" else None,
            generator_url=alert.generatorURL,
            receiver=payload.receiver,
            group_key=payload.groupKey,
        )
        db.merge(alert_record)
        db.commit()

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

        # Forward to notification systems (email, Slack, PagerDuty, etc.)
        # This is where you'd integrate with your notification system
        # await send_notification(alert_record)

    return {"status": "received", "alert_count": len(payload.alerts)}


@router.get("/health")
async def alerts_health():
    """Health check for alerts endpoint."""
    return {"status": "healthy", "service": "alerts"}


@router.get("", response_model=list[dict])
async def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(database.get_db),
):
    """List stored alerts with optional filtering."""
    query = db.query(models.Alert)
    if status:
        query = query.filter(models.Alert.status == models.AlertStatus(status))
    if severity:
        query = query.filter(models.Alert.severity == models.AlertSeverity(severity))
    alerts = query.order_by(models.Alert.created_at.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "fingerprint": a.fingerprint,
            "alertname": a.alertname,
            "status": a.status.value,
            "severity": a.severity.value,
            "labels": json.loads(a.labels_json),
            "annotations": json.loads(a.annotations_json) if a.annotations_json else None,
            "starts_at": a.starts_at.isoformat(),
            "ends_at": a.ends_at.isoformat() if a.ends_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "receiver": a.receiver,
            "group_key": a.group_key,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.get("/{alert_id}", response_model=dict)
async def get_alert(alert_id: str, db: Session = Depends(database.get_db)):
    """Get a specific alert by ID."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        "id": alert.id,
        "fingerprint": alert.fingerprint,
        "alertname": alert.alertname,
        "status": alert.status.value,
        "severity": alert.severity.value,
        "labels": json.loads(alert.labels_json),
        "annotations": json.loads(alert.annotations_json) if alert.annotations_json else None,
        "starts_at": alert.starts_at.isoformat(),
        "ends_at": alert.ends_at.isoformat() if alert.ends_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "receiver": alert.receiver,
        "group_key": alert.group_key,
        "created_at": alert.created_at.isoformat(),
        "updated_at": alert.updated_at.isoformat(),
    }
