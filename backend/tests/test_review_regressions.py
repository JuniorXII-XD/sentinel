"""Regression coverage for the five v1.0 review findings."""

import asyncio
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, event
from sqlalchemy.exc import IntegrityError
from app.config import Settings
from app.database import SessionLocal, engine
from app.main import app
from app.middleware import BodyLimitMiddleware
from app.models import SecurityEvent, Session, RateBucket, DetectionRule, utcnow
from conftest import sign_in, PASSWORD
from test_engine import emit, get_alerts


@pytest.mark.parametrize("cookie", [None, "invalid-cookie"])
def test_anonymous_session_probe_does_not_create_events_or_counters(client, cookie):
    if cookie:
        client.cookies.set("sentinel_session", cookie)
    for _ in range(3):
        assert client.get("/api/auth/me").status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SecurityEvent)) == 0
        assert db.scalar(select(func.count()).select_from(RateBucket)) == 0
    sign_in(client)
    assert client.get("/api/overview").json()["high_risk_events"] == 0


@pytest.mark.parametrize("kind", ["absolute", "idle", "disabled"])
def test_invalid_session_probe_remains_quiet(logged, kind):
    with SessionLocal() as db:
        row = db.scalar(select(Session))
        if kind == "absolute":
            row.expires_at = utcnow() - timedelta(seconds=1)
        elif kind == "idle":
            row.last_seen_at = utcnow() - timedelta(minutes=31)
        else:
            row.user.is_active = False
        db.commit()
        count = db.scalar(select(func.count()).select_from(SecurityEvent))
    assert logged.get("/api/auth/me").status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SecurityEvent)) == count


def test_real_protected_route_denial_still_audited(client):
    assert client.get("/api/events").status_code == 401
    with SessionLocal() as db:
        row = db.scalar(select(SecurityEvent))
        assert row.event_type == "unauthorized_access"
        assert row.metadata_json["path"] == "/api/events"


def test_pair_throttle_does_not_lock_account_from_another_ip():
    with TestClient(
        app, client=("192.0.2.10", 1234), headers={"Origin": "http://testserver"}
    ) as attacker:
        for _ in range(8):
            assert (
                attacker.post(
                    "/api/auth/login", json={"username": "ADMIN", "password": "wrong"}
                ).status_code
                == 401
            )
        assert (
            attacker.post(
                "/api/auth/login", json={"username": "admin", "password": PASSWORD}
            ).status_code
            == 429
        )
        # A different account on that source has an independent pair bucket.
        sign_in(attacker, "analyst")
    with TestClient(
        app, client=("192.0.2.11", 1234), headers={"Origin": "http://testserver"}
    ) as owner:
        sign_in(owner)
        assert owner.get("/api/events").status_code == 200


def test_ip_limit_survives_username_rotation_and_forwarded_ip_spoof(client):
    for i in range(20):
        assert (
            client.post(
                "/api/auth/login",
                json={"username": f"absent{i}", "password": "wrong"},
                headers={"X-Forwarded-For": f"192.0.2.{i + 1}"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "another", "password": "wrong"}
        ).status_code
        == 429
    )


def test_pair_limit_recovers_after_fixed_window(client):
    for _ in range(8):
        client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": PASSWORD}
        ).status_code
        == 429
    )
    with SessionLocal() as db:
        for bucket in db.scalars(select(RateBucket)):
            bucket.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    sign_in(client)


def test_session_touch_is_coalesced_but_api_counter_still_enforced(logged):
    with SessionLocal() as db:
        original = db.scalar(select(Session)).last_seen_at
    updates = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.upper().startswith("UPDATE SESSIONS"):
            updates.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        for _ in range(3):
            assert logged.get("/api/auth/me").status_code == 200
        with SessionLocal() as db:
            assert db.scalar(select(Session)).last_seen_at == original
            bucket = db.scalar(select(RateBucket).where(RateBucket.key.like("api:%")))
            assert bucket.hits == 3
        assert updates == []
        with SessionLocal() as db:
            db.scalar(select(Session)).last_seen_at = utcnow() - timedelta(seconds=31)
            db.commit()
        updates.clear()
        assert logged.get("/api/auth/me").status_code == 200
        assert len(updates) == 1
        with SessionLocal() as db:
            assert db.scalar(select(Session)).last_seen_at > original
            db.scalar(select(RateBucket).where(RateBucket.key.like("api:%"))).hits = 240
            db.commit()
        assert logged.get("/api/auth/me").status_code == 429
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_production_requires_explicit_non_test_hosts(monkeypatch):
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    assert "testserver" not in Settings(_env_file=None).allowed_hosts
    options = dict(
        _env_file=None,
        environment="production",
        demo_enabled=False,
        cookie_secure=True,
        trusted_origins=["https://sentinel.example"],
    )
    with pytest.raises(ValueError, match="explicit ALLOWED_HOSTS"):
        Settings(**options)
    with pytest.raises(ValueError, match="testserver"):
        Settings(**options, allowed_hosts=["testserver"])
    monkeypatch.setenv("ALLOWED_HOSTS", '["sentinel.example"]')
    assert Settings(**options).allowed_hosts == ["sentinel.example"]


def test_spray_uses_db_per_account_cap():
    with SessionLocal() as db:
        db.get(DetectionRule, "AUTH-002").max_attempts_per_account = 3
        db.flush()
        for i in range(3):
            emit(db, account="alice", offset=i)
        for i in range(4):
            emit(db, account=f"user{i}", offset=10 + i)
        assert len(get_alerts(db, "AUTH-002")) == 1


@pytest.mark.parametrize("field,value", [("min_accounts", 4), ("min_source_ips", 3)])
def test_cluster_reads_db_minimums_and_workspace_scope(field, value):
    with SessionLocal() as db:
        setattr(db.get(DetectionRule, "AUTH-003"), field, value)
        db.flush()
        for i in range(10):
            emit(db, ip=f"192.0.2.{i % 2 + 1}", account=f"user{i % 3}", offset=i)
        assert not get_alerts(db, "AUTH-003")
        emit(db, ip="192.0.2.3", account="user3", offset=11)
        alert = get_alerts(db, "AUTH-003")[0]
        assert alert.subject == "workspace" and ":workspace:" in alert.dedup_key


@pytest.mark.parametrize(
    "rule,field,value",
    [
        ("AUTH-002", "max_attempts_per_account", 0),
        ("AUTH-002", "max_attempts_per_account", None),
        ("AUTH-003", "min_accounts", -1),
        ("AUTH-003", "min_source_ips", None),
    ],
)
def test_invalid_rule_parameters_rejected_by_db(rule, field, value):
    with SessionLocal() as db:
        setattr(db.get(DetectionRule, rule), field, value)
        with pytest.raises(IntegrityError):
            db.flush()


def test_settings_exposes_all_numeric_parameters_but_does_not_accept_edits(logged):
    rules = {r["id"]: r for r in logged.get("/api/settings").json()["rules"]}
    assert rules["AUTH-002"]["max_attempts_per_account"] == 2
    assert rules["AUTH-003"]["min_accounts"] == 3
    assert rules["AUTH-003"]["min_source_ips"] == 2
    assert (
        logged.patch(
            "/api/settings/rules/AUTH-002",
            json={"enabled": True, "max_attempts_per_account": 3},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("size", [16384, 16385])
def test_body_limit_with_chunked_receive_and_disconnect(size):
    async def exercise():
        messages = iter(
            [
                {"type": "http.request", "body": b"x" * 8000, "more_body": True},
                {
                    "type": "http.request",
                    "body": b"x" * (size - 8000),
                    "more_body": False,
                },
                {"type": "http.disconnect"},
            ]
        )
        sent, called = [], []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        async def downstream(scope, receive, send):
            called.append(True)
            message = await receive()
            assert len(message["body"]) == size and not message["more_body"]
            assert (await receive())["type"] == "http.disconnect"

        await BodyLimitMiddleware(downstream)(
            {"type": "http", "method": "POST"}, receive, send
        )
        if size == 16384:
            assert called == [True]
        else:
            assert called == [] and sent[0]["status"] == 413

    asyncio.run(exercise())


def test_body_limit_replays_valid_json_to_login(client):
    body = '{"username":"admin","password":"' + PASSWORD + '"}'
    body += " " * (16384 - len(body))
    assert (
        client.post(
            "/api/auth/login",
            content=body,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 200
    )


def test_body_limit_early_disconnect_does_not_call_app():
    async def exercise():
        async def receive():
            return {"type": "http.disconnect"}

        async def unexpected(*args):
            pytest.fail("Disconnected request must not reach the application")

        await BodyLimitMiddleware(unexpected)(
            {"type": "http", "method": "POST"}, receive, unexpected
        )

    asyncio.run(exercise())
