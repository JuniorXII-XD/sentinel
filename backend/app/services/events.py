from .detection import evaluate
from ..models import SecurityEvent

ALLOWED_METADATA = {
    "account",
    "reason",
    "path",
    "target_user_id",
    "old_role",
    "new_role",
    "old_active",
    "new_active",
    "alert_id",
    "old_status",
    "new_status",
    "scenario",
    "source",
    "rule_id",
    "enabled",
    "format",
    "scope",
}


def record_event(
    db,
    event_type,
    source_ip,
    user_id=None,
    metadata=None,
    is_demo=False,
    occurred_at=None,
    severity=None,
):
    # Strict allowlist: callers cannot accidentally persist passwords/tokens/arbitrary payloads.
    clean = {
        k: v
        for k, v in (metadata or {}).items()
        if k in ALLOWED_METADATA and isinstance(v, (str, int, bool, type(None)))
    }
    clean = {k: v[:200] if isinstance(v, str) else v for k, v in clean.items()}
    level = severity or {
        "login_failed": "medium",
        "unauthorized_access": "high",
        "suspicious_activity": "high",
        "privilege_changed": "medium",
    }.get(event_type, "low")
    item = SecurityEvent(
        event_type=event_type,
        source_ip=source_ip,
        user_id=user_id,
        metadata_json=clean,
        is_demo=is_demo,
        severity=level,
    )
    if occurred_at is not None:
        item.occurred_at = occurred_at
    db.add(item)
    db.flush()
    evaluate(db, item)
    return item
