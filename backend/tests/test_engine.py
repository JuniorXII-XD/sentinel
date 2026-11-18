from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Alert, AlertEvidence, DetectionRule
from app.services.events import record_event

BASE = datetime(2026, 11, 17, 5, 0, 0)  # noon Bangkok


def emit(
    db,
    ip="192.0.2.1",
    account="alice",
    offset=0,
    kind="login_failed",
    demo=True,
    user=None,
):
    return record_event(
        db,
        kind,
        ip,
        user_id=user,
        metadata={"account": account},
        is_demo=demo,
        occurred_at=BASE + timedelta(seconds=offset),
    )


def get_alerts(db, rule):
    return db.scalars(select(Alert).where(Alert.rule_id == rule)).all()


def test_threshold_dedup_and_evidence():
    with SessionLocal() as db:
        for i in range(4):
            emit(db, offset=i)
        assert not get_alerts(db, "AUTH-001")
        for i in range(4, 8):
            emit(db, offset=i)
        db.commit()
        alerts = get_alerts(db, "AUTH-001")
        assert len(alerts) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(AlertEvidence)
                .where(AlertEvidence.alert_id == alerts[0].id)
            )
            == 8
        )


def test_detection_window_does_not_include_old_events():
    with SessionLocal() as db:
        for i in range(5):
            emit(db, offset=i * 90)
        assert not get_alerts(db, "AUTH-001")


def test_spray_distinct_accounts_not_repeated_single_user():
    with SessionLocal() as db:
        for i in range(5):
            emit(db, account=f"user{i}", offset=i)
        assert len(get_alerts(db, "AUTH-002")) == 1


def test_spray_rejects_high_per_account_counts():
    with SessionLocal() as db:
        for i in range(3):
            emit(db, account="alice", offset=i)
        for i in range(4):
            emit(db, account=f"user{i}", offset=10 + i)
        assert not get_alerts(db, "AUTH-002")


def test_distributed_multiple_account_cluster():
    with SessionLocal() as db:
        for i in range(10):
            emit(db, ip=f"192.0.2.{i % 2 + 1}", account=f"user{i % 3}", offset=i)
        assert len(get_alerts(db, "AUTH-003")) == 1


def test_multiple_account_rule_requires_multiple_sources():
    with SessionLocal() as db:
        for i in range(10):
            emit(db, account=f"user{i % 3}", offset=i)
        assert not get_alerts(db, "AUTH-003")


def test_privilege_rule_only_authenticated_users():
    with SessionLocal() as db:
        emit(db, kind="unauthorized_access")
        assert not get_alerts(db, "ACCESS-001")
        emit(db, kind="unauthorized_access", user=2)
        assert len(get_alerts(db, "ACCESS-001")) == 1


def test_unusual_hours_with_local_timezone():
    with SessionLocal() as db:
        emit(db, kind="login_success")
        assert not get_alerts(db, "AUTH-004")
        emit(db, kind="login_success", offset=14 * 3600)  # 02:00 next day Bangkok
        assert len(get_alerts(db, "AUTH-004")) == 1


def test_demo_and_live_never_correlate():
    with SessionLocal() as db:
        for i in range(4):
            emit(db, offset=i, demo=True)
        emit(db, offset=5, demo=False)
        assert not get_alerts(db, "AUTH-001")


def test_disabled_rule_and_metadata_allowlist():
    with SessionLocal() as db:
        db.get(DetectionRule, "AUTH-001").enabled = False
        db.flush()
        for i in range(6):
            emit(db, offset=i)
        assert not get_alerts(db, "AUTH-001")
        e = record_event(
            db,
            "login_success",
            "192.0.2.1",
            metadata={"password": "secret", "session_token": "abc", "account": "safe"},
        )
        assert e.metadata_json == {"account": "safe"}


def test_dedup_across_time_bucket_boundary():
    with SessionLocal() as db:
        for i in range(8):
            emit(db, offset=56 + i)
        assert len(get_alerts(db, "AUTH-001")) == 1
