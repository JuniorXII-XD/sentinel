from datetime import datetime, timedelta
from app.services.detection import detect_repeated_failures


def test_five_failures_trigger_alert():
    now = datetime(2026, 1, 1)
    events = [
        {
            "source_ip": "192.0.2.10",
            "event_type": "login_failed",
            "occurred_at": now + timedelta(seconds=i * 10),
        }
        for i in range(5)
    ]
    assert detect_repeated_failures(events)["rule_id"] == "AUTH-001"


def test_four_failures_do_not_trigger():
    now = datetime(2026, 1, 1)
    events = [
        {
            "source_ip": "192.0.2.10",
            "event_type": "login_failed",
            "occurred_at": now + timedelta(seconds=i),
        }
        for i in range(4)
    ]
    assert detect_repeated_failures(events) is None


def test_old_failures_do_not_trigger():
    now = datetime(2026, 1, 1)
    events = [
        {
            "source_ip": "192.0.2.10",
            "event_type": "login_failed",
            "occurred_at": now + timedelta(seconds=i * 90),
        }
        for i in range(5)
    ]
    assert detect_repeated_failures(events) is None
