from datetime import timedelta


def detect_repeated_failures(events, threshold=5, window_seconds=60):
    """Pure rule: list of dicts with source_ip, event_type, occurred_at."""
    failures = sorted(
        (e for e in events if e["event_type"] == "login_failed"),
        key=lambda e: e["occurred_at"],
    )
    by_ip = {}
    for event in failures:
        ip = event["source_ip"]
        times = by_ip.setdefault(ip, [])
        now = event["occurred_at"]
        times.append(now)
        cutoff = now - timedelta(seconds=window_seconds)
        while times and times[0] < cutoff:
            times.pop(0)
        if len(times) >= threshold:
            return {
                "rule_id": "AUTH-001",
                "severity": "high",
                "source_ip": ip,
                "count": len(times),
            }
    return None


# The starter's pure AUTH-001 function above is retained for compatibility.
from collections import Counter
from datetime import timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..models import DetectionRule, SecurityEvent, Alert, AlertEvidence, AlertHistory
from ..config import get_settings

RULES = [
    (
        "AUTH-001",
        "Repeated login failures",
        "Repeated failures from one source within the configured window.",
        "high",
        5,
        60,
    ),
    (
        "AUTH-002",
        "Password spraying pattern",
        "One source targets distinct accounts with a configured per-account failure cap.",
        "high",
        5,
        300,
    ),
    (
        "AUTH-003",
        "Multiple-account failure cluster",
        "A workspace-wide failure cluster across the configured minimum accounts and sources.",
        "medium",
        10,
        300,
    ),
    (
        "ACCESS-001",
        "Restricted privilege access",
        "A signed-in account attempted an administrator-only operation.",
        "critical",
        1,
        300,
    ),
    (
        "AUTH-004",
        "Unusual login time",
        "Successful login outside configured local working hours.",
        "low",
        1,
        3600,
    ),
]

RULE_PARAMETERS = {
    "AUTH-002": {"max_attempts_per_account": 2},
    "AUTH-003": {"min_accounts": 3, "min_source_ips": 2},
}


def seed_rules(db):
    for key, name, description, severity, threshold, window in RULES:
        if db.get(DetectionRule, key) is None:
            db.add(
                DetectionRule(
                    id=key,
                    name=name,
                    description=description,
                    severity=severity,
                    threshold=threshold,
                    window_seconds=window,
                    **RULE_PARAMETERS.get(key, {}),
                )
            )
    db.flush()


def make_alert(db, rule, event, subject, evidence):
    # Recent-window lookup suppresses boundary duplicates. A unique key also handles races
    # inside a bucket. Evidence is bounded to 200 rows per alert.
    cutoff = event.occurred_at - timedelta(seconds=rule.window_seconds)
    existing = db.scalar(
        select(Alert)
        .where(
            Alert.rule_id == rule.id,
            Alert.subject == subject,
            Alert.is_demo == event.is_demo,
            Alert.created_at >= cutoff,
            Alert.created_at <= event.occurred_at,
        )
        .order_by(Alert.id.desc())
        .limit(1)
    )
    if existing:
        known = set(
            db.scalars(
                select(AlertEvidence.event_id).where(
                    AlertEvidence.alert_id == existing.id
                )
            )
        )
        for e in evidence:
            if e.id not in known and len(known) < 200:
                db.add(AlertEvidence(alert_id=existing.id, event_id=e.id))
                known.add(e.id)
        return
    bucket = (
        int(event.occurred_at.replace(tzinfo=timezone.utc).timestamp())
        // rule.window_seconds
    )
    alert = Alert(
        event_id=event.id,
        rule_id=rule.id,
        severity=rule.severity,
        description=f"{rule.name}: suspicious signal requiring investigation; not a confirmed attack.",
        created_at=event.occurred_at,
        updated_at=event.occurred_at,
        is_demo=event.is_demo,
        subject=subject,
        dedup_key=f"{rule.id}:{int(event.is_demo)}:{subject}:{bucket}",
    )
    try:
        with db.begin_nested():
            db.add(alert)
            db.flush()
            db.add_all(
                [
                    AlertEvidence(alert_id=alert.id, event_id=e.id)
                    for e in evidence[:200]
                ]
            )
            db.add(
                AlertHistory(
                    alert_id=alert.id,
                    new_status="open",
                    note="Rule triggered; analyst review required.",
                    created_at=event.occurred_at,
                )
            )
    except IntegrityError:
        # A competing transaction created this same fingerprint.
        pass


def evaluate(db, event):
    if event.event_type not in ("login_failed", "login_success", "unauthorized_access"):
        return
    rules = db.scalars(
        select(DetectionRule).where(DetectionRule.enabled.is_(True))
    ).all()
    for rule in rules:
        evidence, subject = [], event.source_ip
        if (
            rule.id in ("AUTH-001", "AUTH-002", "AUTH-003")
            and event.event_type == "login_failed"
        ):
            query = select(SecurityEvent).where(
                SecurityEvent.is_demo == event.is_demo,
                SecurityEvent.event_type == "login_failed",
                SecurityEvent.occurred_at
                >= event.occurred_at - timedelta(seconds=rule.window_seconds),
                SecurityEvent.occurred_at <= event.occurred_at,
            )
            if rule.id != "AUTH-003":
                query = query.where(SecurityEvent.source_ip == event.source_ip)
            recent = db.scalars(
                query.order_by(SecurityEvent.id.desc()).limit(1000)
            ).all()
            if rule.id == "AUTH-001":
                result = detect_repeated_failures(
                    [
                        {
                            "source_ip": x.source_ip,
                            "event_type": x.event_type,
                            "occurred_at": x.occurred_at,
                        }
                        for x in recent
                    ],
                    rule.threshold,
                    rule.window_seconds,
                )
                if result:
                    evidence = recent
            else:
                counts = Counter(
                    x.metadata_json.get("account")
                    for x in recent
                    if x.metadata_json.get("account")
                )
                if (
                    rule.id == "AUTH-002"
                    and len(counts) >= rule.threshold
                    and max(counts.values(), default=0) <= rule.max_attempts_per_account
                ):
                    evidence = recent
                if (
                    rule.id == "AUTH-003"
                    and len(recent) >= rule.threshold
                    and len(counts) >= rule.min_accounts
                    and len({x.source_ip for x in recent}) >= rule.min_source_ips
                ):
                    subject, evidence = "workspace", recent
        elif (
            rule.id == "ACCESS-001"
            and event.event_type == "unauthorized_access"
            and event.user_id is not None
        ):
            subject, evidence = f"user:{event.user_id}", [event]
        elif rule.id == "AUTH-004" and event.event_type == "login_success":
            cfg = get_settings()
            hour = (
                event.occurred_at.replace(tzinfo=timezone.utc)
                .astimezone(ZoneInfo(cfg.timezone))
                .hour
            )
            if not cfg.work_start <= hour < cfg.work_end:
                subject, evidence = (
                    event.metadata_json.get("account", f"user:{event.user_id}"),
                    [event],
                )
        if evidence:
            make_alert(db, rule, event, subject, evidence)
