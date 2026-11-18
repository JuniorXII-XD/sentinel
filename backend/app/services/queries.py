from datetime import timedelta
from sqlalchemy import select, func
from ..models import SecurityEvent, Alert, utcnow


def iso(value):
    return value.isoformat(timespec="microseconds") + "Z" if value else None


def event_json(x):
    return {
        "id": x.id,
        "event_type": x.event_type,
        "source_ip": x.source_ip,
        "user_id": x.user_id,
        "occurred_at": iso(x.occurred_at),
        "metadata": x.metadata_json,
        "severity": x.severity,
        "is_demo": x.is_demo,
    }


def alert_json(x):
    return {
        "id": x.id,
        "rule_id": x.rule_id,
        "severity": x.severity,
        "status": x.status,
        "description": x.description,
        "created_at": iso(x.created_at),
        "updated_at": iso(x.updated_at),
        "resolved_at": iso(x.resolved_at),
        "subject": x.subject,
        "is_demo": x.is_demo,
    }


def filters(model, scope, days):
    field = model.occurred_at if model is SecurityEvent else model.created_at
    return [
        model.is_demo.is_(scope == "demo"),
        field >= utcnow() - timedelta(days=days),
    ]


def summary_data(db, scope, days):
    efilter, afilter = filters(SecurityEvent, scope, days), filters(Alert, scope, days)

    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    event_counts = dict(
        db.execute(
            select(SecurityEvent.event_type, func.count())
            .where(*efilter)
            .group_by(SecurityEvent.event_type)
        ).all()
    )
    severities = dict(
        db.execute(
            select(Alert.severity, func.count())
            .where(*afilter)
            .group_by(Alert.severity)
        ).all()
    )
    statuses = dict(
        db.execute(
            select(Alert.status, func.count()).where(*afilter).group_by(Alert.status)
        ).all()
    )
    # SQL DATE() is supported by SQLite and PostgreSQL. Fill missing days explicitly.
    grouped = db.execute(
        select(
            func.date(SecurityEvent.occurred_at), SecurityEvent.event_type, func.count()
        )
        .where(*efilter)
        .group_by(func.date(SecurityEvent.occurred_at), SecurityEvent.event_type)
    ).all()
    start = (utcnow() - timedelta(days=days)).date()
    buckets = {
        str(start + timedelta(days=i)): {
            "date": str(start + timedelta(days=i)),
            "success": 0,
            "failed": 0,
            "other": 0,
        }
        for i in range(days + 1)
    }
    for date, kind, n in grouped:
        if str(date) in buckets:
            buckets[str(date)][
                {"login_success": "success", "login_failed": "failed"}.get(
                    kind, "other"
                )
            ] += n
    total_alerts = sum(severities.values())
    recommendations = [
        "Review related events before classifying any alert as an attack.",
        "Enable MFA at the monitored identity provider; SENTINEL does not implement MFA.",
    ]
    if event_counts.get("login_failed", 0):
        recommendations.append(
            "Review repeated failures, validate account ownership and inspect trusted identity-provider logs."
        )
    if statuses.get("open", 0):
        recommendations.append(
            "Assign an investigator to open alerts and document the outcome."
        )
    return {
        "scope": scope,
        "days": days,
        "generated_at": iso(utcnow()),
        "total_events": sum(event_counts.values()),
        "active_alerts": statuses.get("open", 0) + statuses.get("investigating", 0),
        "high_risk_events": count(
            SecurityEvent, *efilter, SecurityEvent.severity.in_(["high", "critical"])
        ),
        "login_success": event_counts.get("login_success", 0),
        "login_failed": event_counts.get("login_failed", 0),
        "total_alerts": total_alerts,
        "resolved_alerts": statuses.get("resolved", 0),
        "resolution_rate": round(statuses.get("resolved", 0) / total_alerts * 100, 1)
        if total_alerts
        else 0,
        "event_types": event_counts,
        "severity": severities,
        "status": statuses,
        "timeline": list(buckets.values()),
        "recommendations": recommendations,
    }
