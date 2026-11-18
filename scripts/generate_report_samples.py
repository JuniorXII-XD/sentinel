"""Generate real API report artifacts against a disposable local SQLite database.
Run from the project root with its Python virtual environment active.
"""

import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="sentinel-report-") as temporary:
    os.environ.update(
        DATABASE_URL="sqlite:///" + str(Path(temporary) / "reports.db"),
        ENVIRONMENT="development",
        DEMO_ENABLED="true",
        TRUSTED_ORIGINS='["http://testserver"]',
        ALLOWED_HOSTS='["testserver"]',
        COOKIE_SECURE="false",
    )
    os.chdir(root / "backend")
    sys.path.insert(0, str(root / "backend"))
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from app.database import SessionLocal, engine
    from app.models import User
    from app.security import hash_password
    from app.main import app

    command.upgrade(Config("alembic.ini"), "head")
    password = secrets.token_urlsafe(24)
    with SessionLocal() as db:
        db.add(
            User(
                username="report.operator",
                password_hash=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    target = root / "docs" / "sample-reports"
    target.mkdir(exist_ok=True)
    with TestClient(app, headers={"Origin": "http://testserver"}) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "report.operator", "password": password},
        )
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        client.post("/api/demo/seed").raise_for_status()
        summary = client.get("/api/reports/summary?scope=demo&days=7")
        summary.raise_for_status()
        (target / "summary.json").write_text(json.dumps(summary.json(), indent=2))
        for format in ["csv", "pdf"]:
            response = client.post(
                f"/api/reports/export?scope=demo&days=7&format={format}"
            )
            response.raise_for_status()
            (target / f"sentinel-demo-7d.{format}").write_bytes(response.content)
        client.post("/api/auth/logout").raise_for_status()
    engine.dispose()
    print("API-generated demo CSV, PDF and summary saved; temporary database removed.")
