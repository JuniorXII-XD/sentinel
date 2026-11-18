"""Explicit detection parameters and workspace scope.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("max_attempts_per_account", "min_accounts", "min_source_ips"):
        op.add_column("detection_rules", sa.Column(name, sa.Integer(), nullable=True))
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE detection_rules SET max_attempts_per_account=2 WHERE id='AUTH-002'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE detection_rules SET min_accounts=3, min_source_ips=2 WHERE id='AUTH-003'"
        )
    )
    descriptions = {
        "AUTH-001": "Repeated failures from one source within the configured window.",
        "AUTH-002": "One source targets distinct accounts with a configured per-account failure cap.",
        "AUTH-003": "A workspace-wide failure cluster across the configured minimum accounts and sources.",
    }
    for key, description in descriptions.items():
        conn.execute(
            sa.text("UPDATE detection_rules SET description=:description WHERE id=:id"),
            {"id": key, "description": description},
        )
    with op.batch_alter_table("detection_rules") as batch:
        batch.create_check_constraint(
            "ck_rule_parameters_positive",
            "(max_attempts_per_account IS NULL OR max_attempts_per_account > 0) AND "
            "(min_accounts IS NULL OR min_accounts > 0) AND "
            "(min_source_ips IS NULL OR min_source_ips > 0)",
        )
        batch.create_check_constraint(
            "ck_spray_parameters",
            "id != 'AUTH-002' OR max_attempts_per_account IS NOT NULL",
        )
        batch.create_check_constraint(
            "ck_cluster_parameters",
            "id != 'AUTH-003' OR (min_accounts IS NOT NULL AND min_source_ips IS NOT NULL)",
        )
    # Rename existing alerts too, so the rolling dedup lookup continues to match.
    conn.execute(
        sa.text(
            "UPDATE alerts SET subject='workspace', "
            "dedup_key=replace(dedup_key, ':tenant:', ':workspace:') "
            "WHERE rule_id='AUTH-003' AND subject='tenant'"
        )
    )


def downgrade():
    raise RuntimeError(
        "Forward-only evidence migration; restore a verified backup to roll back."
    )
