from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Session, SecurityEvent, Alert, User, utcnow
from app.config import get_settings, Settings
from app.security import verify_password
from conftest import sign_in, PASSWORD


def test_login_cookie_and_hashed_session(client):
    response = sign_in(client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Secure" not in cookie  # HTTP local development only
    raw = client.cookies.get("sentinel_session")
    with SessionLocal() as db:
        row = db.scalar(select(Session))
        assert row.token_hash != raw and len(row.token_hash) == 64
        user = db.scalar(select(User).where(User.username == "admin"))
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(PASSWORD, user.password_hash)
    assert client.get("/api/auth/me").json()["user"]["role"] == "admin"


def test_bad_login_generic_no_secrets(client):
    a = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    b = client.post("/api/auth/login", json={"username": "absent", "password": "wrong"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    with SessionLocal() as db:
        logs = str([e.metadata_json for e in db.scalars(select(SecurityEvent))])
        assert "password" not in logs and "wrong" not in logs


def test_validation_does_not_echo_password(client):
    response = client.post(
        "/api/auth/login", json={"username": "bad name", "password": "DO-NOT-ECHO-THIS"}
    )
    assert response.status_code == 422
    assert "DO-NOT-ECHO" not in response.text


def test_origin_required_for_login(client):
    for origin in ["https://evil.example", "null", ""]:
        assert (
            client.post(
                "/api/auth/login",
                headers={"Origin": origin},
                json={"username": "admin", "password": PASSWORD},
            ).status_code
            == 403
        )


def test_csrf_and_logout_revocation(logged):
    raw = logged.cookies.get("sentinel_session")
    assert (
        logged.post("/api/auth/logout", headers={"X-CSRF-Token": "bad"}).status_code
        == 403
    )
    assert logged.post("/api/auth/logout").status_code == 204
    logged.cookies.set("sentinel_session", raw)
    assert logged.get("/api/auth/me").status_code == 401


def test_login_rotates_session(logged):
    previous = logged.cookies.get("sentinel_session")
    sign_in(logged)
    assert logged.cookies.get("sentinel_session") != previous
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Session)) == 1


@pytest.mark.parametrize("kind", ["absolute", "idle"])
def test_session_expiry(logged, kind):
    with SessionLocal() as db:
        row = db.scalar(select(Session))
        if kind == "absolute":
            row.expires_at = utcnow() - timedelta(seconds=1)
        else:
            row.last_seen_at = utcnow() - timedelta(minutes=31)
        db.commit()
    assert logged.get("/api/overview").status_code == 401


def test_account_rate_limit_and_detection(client):
    for _ in range(8):
        assert (
            client.post(
                "/api/auth/login", json={"username": "admin", "password": "bad"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": PASSWORD}
        ).status_code
        == 429
    )
    with SessionLocal() as db:
        assert db.scalar(select(Alert).where(Alert.rule_id == "AUTH-001"))
        assert db.scalar(
            select(SecurityEvent).where(
                SecurityEvent.event_type == "suspicious_activity"
            )
        )


def test_analyst_cannot_admin_and_audited(client):
    sign_in(client, "analyst")
    assert client.get("/api/settings/users").status_code == 403
    assert client.post("/api/demo/seed").status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(Alert).where(Alert.rule_id == "ACCESS-001"))
    assert client.get("/api/events").status_code == 200


def test_unauthenticated_routes(client):
    for path in [
        "/api/overview",
        "/api/events",
        "/api/alerts",
        "/api/settings",
        "/api/reports/summary",
    ]:
        assert client.get(path).status_code == 401
    assert (
        client.post(
            "/api/demo/events",
            json={
                "event_type": "login_failed",
                "source_ip": "192.0.2.1",
                "account": "test",
            },
        ).status_code
        == 401
    )


def test_body_limit_and_security_headers(client):
    assert client.post("/api/auth/login", content="x" * 17000).status_code == 413
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in res.headers["content-security-policy"]
    assert (
        client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    )


def test_production_config_fails_closed():
    with pytest.raises(ValueError):
        Settings(environment="production", demo_enabled=True)
    cfg = Settings(
        environment="production",
        demo_enabled=False,
        cookie_secure=True,
        trusted_origins=["https://sentinel.example"],
        allowed_hosts=["sentinel.example"],
    )
    assert cfg.cookie_name.startswith("__Host-")


def test_demo_disabled_outside_development(logged):
    cfg = get_settings()
    old = cfg.environment
    try:
        cfg.environment = "production"
        assert logged.post("/api/demo/seed").status_code == 404
    finally:
        cfg.environment = old


def test_user_create_change_revoke(logged):
    created = logged.post(
        "/api/settings/users",
        json={"username": "New.User", "password": PASSWORD, "role": "analyst"},
    )
    assert created.status_code == 201 and created.json()["username"] == "new.user"
    assert (
        logged.post(
            "/api/settings/users", json={"username": "new.user", "password": PASSWORD}
        ).status_code
        == 409
    )
    assert (
        logged.patch(
            "/api/settings/users/1", json={"role": "analyst", "is_active": True}
        ).status_code
        == 400
    )
    with SessionLocal() as db:
        db.add(
            Session(
                user_id=2,
                token_hash="a" * 64,
                csrf_token="x" * 43,
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        db.commit()
    assert (
        logged.patch(
            "/api/settings/users/2", json={"role": "analyst", "is_active": False}
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert not db.scalar(select(Session).where(Session.user_id == 2))


def test_secure_cookie_flags(client):
    cfg = get_settings()
    try:
        cfg.cookie_secure = True
        response = client.post(
            "/api/auth/login", json={"username": "admin", "password": PASSWORD}
        )
        assert response.status_code == 200
        assert "__Host-sentinel=" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
        assert "Domain=" not in response.headers["set-cookie"]
        assert "max-age=" in response.headers["strict-transport-security"]
    finally:
        cfg.cookie_secure = False


def test_cors_rejects_untrusted_origin(client):
    res = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code == 400
    assert "access-control-allow-origin" not in res.headers


def test_forwarded_ip_is_not_trusted(client):
    client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "192.0.2.200"},
        json={"username": "admin", "password": "wrong"},
    )
    with SessionLocal() as db:
        event = db.scalar(
            select(SecurityEvent).where(SecurityEvent.event_type == "login_failed")
        )
        assert event.source_ip != "192.0.2.200"


def test_rate_counter_is_atomic_across_connections():
    from concurrent.futures import ThreadPoolExecutor
    from app.security import rate_hit

    def attempt(_):
        with SessionLocal() as db:
            allowed = rate_hit(db, "parallel", "account", 8, 300)
            db.commit()
            return allowed

    with ThreadPoolExecutor(max_workers=6) as workers:
        assert sum(workers.map(attempt, range(12))) == 8


def test_unexpected_error_is_generic_and_no_trace(logged, monkeypatch):
    import app.routers.monitor as monitor

    def fail(*args):
        raise RuntimeError("PRIVATE-internal-password-token")

    monkeypatch.setattr(monitor, "summary_data", fail)
    result = logged.get("/api/overview")
    assert result.status_code == 500
    assert result.json() == {"detail": "Internal server error"}
    assert "PRIVATE" not in result.text


def test_wildcard_hosts_and_origins_rejected():
    with pytest.raises(ValueError):
        Settings(allowed_hosts=["*.example.com"])
    with pytest.raises(ValueError):
        Settings(trusted_origins=["https://*.example.com"])
