from datetime import timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from ..models import SecurityEvent, utcnow
from ..config import get_settings
from .events import record_event


def seed_demo(db, actor_id):
    if db.scalar(
        select(func.count())
        .select_from(SecurityEvent)
        .where(SecurityEvent.is_demo.is_(True))
    ):
        return False
    now = utcnow()
    for day in range(6, -1, -1):
        count = 15 + (6 - day) * 4
        for i in range(count):
            record_event(
                db,
                "login_success",
                f"192.0.2.{20 + i % 7}",
                metadata={"account": f"lab.user{i % 7}", "scenario": "baseline"},
                is_demo=True,
                occurred_at=now - timedelta(days=day, minutes=count - i + 20),
            )
    for i in range(7):
        record_event(
            db,
            "login_failed",
            "192.0.2.42",
            metadata={"account": "lab.finance", "scenario": "repeated_failures"},
            is_demo=True,
            occurred_at=now - timedelta(minutes=8) + timedelta(seconds=i * 5),
        )
    for i in range(6):
        record_event(
            db,
            "login_failed",
            "198.51.100.24",
            metadata={"account": f"lab.sales{i}", "scenario": "spray_pattern"},
            is_demo=True,
            occurred_at=now - timedelta(minutes=5) + timedelta(seconds=i * 5),
        )
    for i in range(10):
        record_event(
            db,
            "login_failed",
            f"203.0.113.{10 + i % 3}",
            metadata={"account": f"lab.ops{i % 4}", "scenario": "account_cluster"},
            is_demo=True,
            occurred_at=now - timedelta(minutes=3) + timedelta(seconds=i),
        )
    record_event(
        db,
        "unauthorized_access",
        "192.0.2.75",
        actor_id,
        {"reason": "simulated_admin_access", "scenario": "restricted_access"},
        is_demo=True,
        occurred_at=now - timedelta(minutes=1),
    )
    cfg = get_settings()
    local = (
        now.replace(tzinfo=ZoneInfo("UTC"))
        .astimezone(ZoneInfo(cfg.timezone))
        .replace(hour=2, minute=10, second=0, microsecond=0)
    )
    if local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None) > now:
        local -= timedelta(days=1)
    record_event(
        db,
        "login_success",
        "192.0.2.99",
        metadata={"account": "lab.night", "scenario": "unusual_hour"},
        is_demo=True,
        occurred_at=local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
    )
    return True
