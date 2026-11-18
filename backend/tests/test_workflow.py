import pytest
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Alert, SecurityEvent
from app.routers.reports import safe_cell
from conftest import sign_in


def test_seed_dashboard_search_alert_lifecycle_reports(logged):
    res = logged.post("/api/demo/seed")
    assert res.status_code == 200 and res.json()["created"]
    assert logged.post("/api/demo/seed").json()["created"] is False
    demo = logged.get("/api/overview?scope=demo").json()
    live = logged.get("/api/overview?scope=live").json()
    assert demo["total_events"] > 200
    assert live["total_events"] < 10
    assert demo["login_failed"] == 23
    alerts = logged.get("/api/alerts?scope=demo&page_size=100").json()["items"]
    assert {"AUTH-001", "AUTH-002", "AUTH-003", "ACCESS-001", "AUTH-004"} <= {
        a["rule_id"] for a in alerts
    }
    assert all(a["is_demo"] for a in alerts)
    a = alerts[0]
    detail = logged.get(f"/api/alerts/{a['id']}").json()
    assert detail["events"] and detail["history"]
    update = {
        "status": "investigating",
        "note": "Reviewed synthetic IP evidence.",
        "expected_updated_at": a["updated_at"],
    }
    changed = logged.patch(f"/api/alerts/{a['id']}", json=update)
    assert changed.status_code == 200, changed.text
    assert logged.patch(f"/api/alerts/{a['id']}", json=update).status_code == 409
    resolved = logged.patch(
        f"/api/alerts/{a['id']}",
        json={
            **update,
            "status": "resolved",
            "note": "Confirmed authorized lab scenario.",
            "expected_updated_at": changed.json()["updated_at"],
        },
    )
    assert resolved.status_code == 200 and resolved.json()["resolved_at"]
    assert len(logged.get(f"/api/alerts/{a['id']}").json()["history"]) == 3
    search = logged.get("/api/events?scope=demo&q=192.0.2.42").json()
    assert search["total"] == 7
    assert (
        logged.get("/api/events?scope=demo&q=%27%20OR%201%3D1--").json()["total"] == 0
    )
    assert (
        logged.get("/api/events?scope=demo&page_size=2").json()["items"].__len__() == 2
    )
    csv = logged.post("/api/reports/export?scope=demo&format=csv")
    assert (
        csv.status_code == 200
        and "text/csv" in csv.headers["content-type"]
        and "login_failed" in csv.text
    )
    pdf = logged.post("/api/reports/export?scope=demo&format=pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert logged.get("/api/reports/summary?scope=demo").json()["resolved_alerts"] == 1


@pytest.mark.parametrize(
    "ip", ["192.0.2.999", "8.8.8.8", "127.0.0.1", "::1", "192.0.2.1evil"]
)
def test_demo_ip_restriction(logged, ip):
    assert (
        logged.post(
            "/api/demo/events",
            json={"source_ip": ip, "event_type": "login_failed", "account": "test"},
        ).status_code
        == 422
    )


def test_demo_ingestion_and_rule_toggle(logged):
    assert (
        logged.patch(
            "/api/settings/rules/AUTH-001", json={"enabled": False}
        ).status_code
        == 200
    )
    for _ in range(5):
        assert (
            logged.post(
                "/api/demo/events",
                json={
                    "source_ip": "192.0.2.1",
                    "event_type": "login_failed",
                    "account": "test",
                },
            ).status_code
            == 201
        )
    with SessionLocal() as db:
        assert not db.scalar(select(Alert).where(Alert.rule_id == "AUTH-001"))
        assert db.scalar(
            select(SecurityEvent).where(SecurityEvent.event_type == "rule_changed")
        )


def test_analyst_cannot_modify_alert(client):
    sign_in(client)
    client.post("/api/demo/seed")
    a = client.get("/api/alerts?scope=demo").json()["items"][0]
    client.post("/api/auth/logout")
    sign_in(client, "analyst")
    assert (
        client.patch(
            f"/api/alerts/{a['id']}",
            json={
                "status": "resolved",
                "note": "unauthorized",
                "expected_updated_at": a["updated_at"],
            },
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "value", ["=1+1", "+cmd", "-1", "@sum(A1)", ' \t=HYPERLINK("bad")']
)
def test_csv_formula_injection(value):
    assert safe_cell(value).startswith("'")


def test_filters_validation_and_unknown_routes(logged):
    for path in [
        "/api/overview?days=0",
        "/api/events?page_size=999",
        "/api/alerts?status=bad",
        "/api/overview?scope=invalid",
    ]:
        assert logged.get(path).status_code == 422
    assert logged.get("/api/alerts/99999").status_code == 404
    assert logged.get("/api/does-not-exist").status_code == 404
