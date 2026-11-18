"""standard security schema"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "detection_rules",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "threshold > 0 AND window_seconds > 0", name="ck_rule_positive"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    from datetime import datetime, timezone

    rules = [
        (
            "AUTH-001",
            "Repeated login failures",
            "5 failures from one IP in 60 seconds",
            "high",
            5,
            60,
        ),
        (
            "AUTH-002",
            "Password spraying pattern",
            "5 accounts, at most 2 attempts each, in 5 minutes",
            "high",
            5,
            300,
        ),
        (
            "AUTH-003",
            "Multiple-account failure cluster",
            "10 failures, 3 accounts, 2 sources in 5 minutes",
            "medium",
            10,
            300,
        ),
        (
            "ACCESS-001",
            "Restricted privilege access",
            "Signed-in account requests admin access",
            "critical",
            1,
            300,
        ),
        (
            "AUTH-004",
            "Unusual login time",
            "Successful login outside local work hours",
            "low",
            1,
            3600,
        ),
    ]
    connection = op.get_bind()
    for key, name, description, severity, threshold, window in rules:
        connection.execute(
            sa.text(
                "INSERT INTO detection_rules (id,name,description,severity,threshold,window_seconds,enabled,created_at) VALUES (:id,:name,:description,:severity,:threshold,:window,:enabled,:now)"
            ),
            dict(
                id=key,
                name=name,
                description=description,
                severity=severity,
                threshold=threshold,
                window=window,
                enabled=True,
                now=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" "),
            ),
        )
    for key in connection.execute(
        sa.text("SELECT DISTINCT rule_id FROM alerts")
    ).scalars():
        if key not in {r[0] for r in rules}:
            connection.execute(
                sa.text(
                    "INSERT INTO detection_rules (id,name,description,severity,threshold,window_seconds,enabled,created_at) VALUES (:id,:name,:description,:severity,1,300,:enabled,:now)"
                ),
                dict(
                    id=key,
                    name="Legacy rule",
                    description="Imported inactive legacy rule",
                    severity="low",
                    enabled=False,
                    now=datetime.now(timezone.utc)
                    .replace(tzinfo=None)
                    .isoformat(sep=" "),
                ),
            )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_check_constraint("ck_user_role", "role IN ('admin','analyst')")
    op.create_table(
        "rate_buckets",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    with op.batch_alter_table("rate_buckets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_rate_buckets_expires_at"), ["expires_at"], unique=False
        )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sessions_expires_at"), ["expires_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_sessions_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "alert_evidence",
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["security_events.id"],
        ),
        sa.PrimaryKeyConstraint("alert_id", "event_id"),
    )
    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("alert_history", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_alert_history_alert_id"), ["alert_id"], unique=False
        )

    with op.batch_alter_table("alerts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "subject",
                sa.String(length=120),
                server_default="legacy",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("dedup_key", sa.String(length=200), nullable=True)
        )
        batch_op.create_index(
            "ix_alert_filter", ["is_demo", "status", "created_at"], unique=False
        )
        batch_op.create_unique_constraint("uq_alert_dedup", ["dedup_key"])
        batch_op.create_check_constraint(
            "ck_alert_status", "status IN ('open','investigating','resolved')"
        )
        batch_op.create_check_constraint(
            "ck_alert_severity", "severity IN ('low','medium','high','critical')"
        )
        batch_op.create_foreign_key(
            "fk_alert_rule", "detection_rules", ["rule_id"], ["id"]
        )

    with op.batch_alter_table("security_events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "severity", sa.String(length=20), server_default="low", nullable=False
            )
        )
        batch_op.create_check_constraint(
            "ck_event_severity", "severity IN ('low','medium','high','critical')"
        )
        batch_op.add_column(
            sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.create_index(
            "ix_event_detection", ["is_demo", "event_type", "occurred_at"], unique=False
        )
        batch_op.create_index(
            "ix_event_ip_time", ["source_ip", "occurred_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_security_events_is_demo"), ["is_demo"], unique=False
        )

    connection.execute(
        sa.text(
            "UPDATE alerts SET updated_at=created_at, dedup_key='legacy:' || CAST(id AS VARCHAR)"
        )
    )
    connection.execute(
        sa.text(
            "INSERT INTO alert_evidence (alert_id,event_id) SELECT id,event_id FROM alerts"
        )
    )
    connection.execute(
        sa.text(
            "INSERT INTO alert_history (alert_id,old_status,new_status,note,created_at) SELECT id,NULL,status,'Imported from Starter v0.1',created_at FROM alerts"
        )
    )
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column("dedup_key", existing_type=sa.String(200), nullable=False)
        batch_op.alter_column(
            "is_demo", existing_type=sa.Boolean(), server_default=None
        )
        batch_op.alter_column(
            "subject", existing_type=sa.String(120), server_default=None
        )
    with op.batch_alter_table("security_events") as batch_op:
        batch_op.alter_column(
            "is_demo", existing_type=sa.Boolean(), server_default=None
        )
        batch_op.alter_column(
            "severity", existing_type=sa.String(20), server_default=None
        )


def downgrade():
    raise RuntimeError(
        "Standard upgrade is forward-only. Restore your pre-migration backup to return to v0.1."
    )
