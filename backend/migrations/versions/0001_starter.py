"""Original v0.1 schema. Stamp only a verified, backed-up existing v0.1 database."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("source_ip", sa.String(45), nullable=False),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=False),
    )
    for field in ["event_type", "source_ip", "occurred_at"]:
        op.create_index("ix_security_events_" + field, "security_events", [field])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "event_id", sa.Integer, sa.ForeignKey("security_events.id"), nullable=False
        ),
        sa.Column("rule_id", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table("alerts")
    op.drop_table("security_events")
    op.drop_table("users")
