from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_, update
from ..database import get_db
from ..models import SecurityEvent, Alert, AlertEvidence, AlertHistory, utcnow
from ..schemas import Scope, Severity, Status, AlertChange
from ..dependencies import principal, admin, source_ip
from ..services.events import record_event
from ..services.queries import filters, event_json, alert_json, iso, summary_data

router = APIRouter(prefix="/api", tags=["Monitoring"])


@router.get("/overview")
def overview(
    scope: Scope = "live",
    days: int = Query(7, ge=1, le=90),
    user=Depends(principal),
    db=Depends(get_db),
):
    return summary_data(db, scope, days)


@router.get("/events")
def events(
    scope: Scope = "live",
    days: int = Query(7, ge=1, le=90),
    q: str = Query("", max_length=100),
    event_type: str = Query("", max_length=60),
    severity: Severity | None = None,
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(principal),
    db=Depends(get_db),
):
    conditions = filters(SecurityEvent, scope, days)
    if q:
        # SQLAlchemy autoescape treats user wildcards as literal text.
        conditions.append(
            or_(
                SecurityEvent.source_ip.contains(q, autoescape=True),
                SecurityEvent.event_type.contains(q, autoescape=True),
                SecurityEvent.metadata_json["account"]
                .as_string()
                .contains(q, autoescape=True),
            )
        )
    if event_type:
        conditions.append(SecurityEvent.event_type == event_type)
    if severity:
        conditions.append(SecurityEvent.severity == severity)
    total = db.scalar(
        select(func.count()).select_from(SecurityEvent).where(*conditions)
    )
    rows = db.scalars(
        select(SecurityEvent)
        .where(*conditions)
        .order_by(SecurityEvent.occurred_at.desc(), SecurityEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [event_json(x) for x in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/alerts")
def alerts(
    scope: Scope = "live",
    days: int = Query(7, ge=1, le=90),
    status: Status | None = None,
    severity: Severity | None = None,
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(principal),
    db=Depends(get_db),
):
    conditions = filters(Alert, scope, days)
    if status:
        conditions.append(Alert.status == status)
    if severity:
        conditions.append(Alert.severity == severity)
    total = db.scalar(select(func.count()).select_from(Alert).where(*conditions))
    rows = db.scalars(
        select(Alert)
        .where(*conditions)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [alert_json(x) for x in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: int, user=Depends(principal), db=Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    events = db.scalars(
        select(SecurityEvent)
        .join(AlertEvidence, AlertEvidence.event_id == SecurityEvent.id)
        .where(AlertEvidence.alert_id == alert.id)
        .order_by(SecurityEvent.occurred_at)
    ).all()
    history = db.scalars(
        select(AlertHistory)
        .where(AlertHistory.alert_id == alert.id)
        .order_by(AlertHistory.id)
    ).all()
    return {
        **alert_json(alert),
        "events": [event_json(x) for x in events],
        "history": [
            {
                "id": x.id,
                "actor_id": x.actor_id,
                "old_status": x.old_status,
                "new_status": x.new_status,
                "note": x.note,
                "created_at": iso(x.created_at),
            }
            for x in history
        ],
    }


@router.patch("/alerts/{alert_id}")
def update_alert(
    alert_id: int,
    payload: AlertChange,
    request: Request,
    user=Depends(admin),
    db=Depends(get_db),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    try:
        expected = (
            datetime.fromisoformat(payload.expected_updated_at.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
    except ValueError:
        raise HTTPException(422, "Invalid update timestamp")
    old_status = alert.status
    now = utcnow()
    result = db.execute(
        update(Alert)
        .where(Alert.id == alert_id, Alert.updated_at == expected)
        .values(
            status=payload.status,
            updated_at=now,
            resolved_at=now if payload.status == "resolved" else None,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Alert changed. Refresh before saving.")
    db.add(
        AlertHistory(
            alert_id=alert_id,
            actor_id=user.id,
            old_status=old_status,
            new_status=payload.status,
            note=payload.note,
        )
    )
    record_event(
        db,
        "alert_updated",
        source_ip(request),
        user.id,
        {"alert_id": alert_id, "old_status": old_status, "new_status": payload.status},
        is_demo=alert.is_demo,
    )
    db.commit()
    db.refresh(alert)
    return alert_json(alert)
