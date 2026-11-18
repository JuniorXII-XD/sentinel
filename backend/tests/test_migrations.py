import os
import subprocess
import sys
import sqlite3


def test_nonempty_starter_upgrade_preserves_evidence(tmp_path):
    target = tmp_path / "legacy.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(target)}

    def alembic(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    alembic("upgrade", "0001")
    with sqlite3.connect(target) as conn:
        conn.execute(
            "INSERT INTO users VALUES (1,'legacy','hash','admin',1,'2026-01-01 00:00:00')"
        )
        conn.execute(
            "INSERT INTO security_events VALUES (1,NULL,'login_failed','192.0.2.1','2026-01-01 00:00:00','{}')"
        )
        conn.execute(
            "INSERT INTO alerts VALUES (1,1,'AUTH-001','high','open','Legacy alert','2026-01-01 00:00:00')"
        )
    alembic("upgrade", "head")
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT is_demo,dedup_key FROM alerts").fetchone() == (
            1,
            "legacy:1",
        )
        assert conn.execute("SELECT is_demo FROM security_events").fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM alert_history").fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM alert_evidence").fetchone() == (1,)
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    alembic("check")


def test_standard_upgrade_preserves_alert_history_and_dedup_scope(tmp_path):
    target = tmp_path / "standard.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(target)}

    def alembic(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    alembic("upgrade", "0002")
    with sqlite3.connect(target) as conn:
        conn.execute(
            "INSERT INTO security_events (id,event_type,source_ip,occurred_at,metadata_json,severity,is_demo) "
            "VALUES (1,'login_failed','192.0.2.1','2026-11-18 00:00:00','{}','medium',0)"
        )
        conn.execute(
            "INSERT INTO alerts (id,event_id,rule_id,severity,status,description,created_at,updated_at,is_demo,subject,dedup_key) "
            "VALUES (1,1,'AUTH-003','medium','investigating','Existing cluster','2026-11-18 00:00:00','2026-11-18 00:00:00',0,'tenant','AUTH-003:0:tenant:123')"
        )
        conn.execute("INSERT INTO alert_evidence VALUES (1,1)")
        conn.execute(
            "INSERT INTO alert_history (id,alert_id,new_status,note,created_at) "
            "VALUES (1,1,'investigating','Keep this note','2026-11-18 00:00:00')"
        )
        # Operator numeric tuning and disabled state must survive the upgrade.
        conn.execute(
            "UPDATE detection_rules SET threshold=12,window_seconds=600,enabled=0 WHERE id='AUTH-003'"
        )
    alembic("upgrade", "head")
    with sqlite3.connect(target) as conn:
        assert conn.execute(
            "SELECT subject,dedup_key,status FROM alerts"
        ).fetchone() == ("workspace", "AUTH-003:0:workspace:123", "investigating")
        assert conn.execute("SELECT note FROM alert_history").fetchone() == (
            "Keep this note",
        )
        assert conn.execute("SELECT * FROM alert_evidence").fetchone() == (1, 1)
        assert conn.execute(
            "SELECT threshold,window_seconds,enabled,min_accounts,min_source_ips FROM detection_rules WHERE id='AUTH-003'"
        ).fetchone() == (12, 600, 0, 3, 2)
        assert conn.execute(
            "SELECT max_attempts_per_account FROM detection_rules WHERE id='AUTH-002'"
        ).fetchone() == (2,)
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    alembic("check")
