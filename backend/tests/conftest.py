import os
import tempfile
from pathlib import Path

os.environ["ENVIRONMENT"] = "development"
os.environ["DEMO_ENABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///" + str(
    Path(tempfile.mkdtemp(prefix="sentinel-tests-")) / "test.db"
)
os.environ["TRUSTED_ORIGINS"] = '["http://testserver"]'
os.environ["ALLOWED_HOSTS"] = '["testserver"]'
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password
from app.services.detection import seed_rules
from app.main import app

PASSWORD = "Test-only-password-42!"


@pytest.fixture(scope="session", autouse=True)
def migrate():
    from alembic.config import Config
    from alembic import command

    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def reset_database(migrate):
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    with SessionLocal() as db:
        seed_rules(db)
        for name, role in [("admin", "admin"), ("analyst", "analyst")]:
            db.add(
                User(username=name, password_hash=hash_password(PASSWORD), role=role)
            )
        db.commit()


@pytest.fixture
def client():
    with TestClient(
        app, headers={"Origin": "http://testserver"}, raise_server_exceptions=False
    ) as client:
        yield client


def sign_in(client, username="admin"):
    response = client.post(
        "/api/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response


@pytest.fixture
def logged(client):
    sign_in(client)
    return client
