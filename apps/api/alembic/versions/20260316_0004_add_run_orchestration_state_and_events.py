"""add run orchestration state and events

Revision ID: 20260316_0004
Revises: 20260316_0003
Create Date: 2026-03-16 14:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260316_0004"
down_revision = "20260316_0003"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("runs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("runs", sa.Column("current_step", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("checkpoint_json", JSONB, nullable=True))

    op.create_table(
        "run_events",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("step", sa.String(length=64), nullable=True),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_run_events_tenant_run_created", "run_events", ["tenant_id", "run_id", "created_at"])

    op.execute(
        """
        ALTER TABLE run_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE run_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation_run_events
          ON run_events
          FOR ALL
          USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
          WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_run_events ON run_events")
    op.execute("ALTER TABLE run_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE run_events DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_run_events_tenant_run_created", table_name="run_events")
    op.drop_table("run_events")

    op.drop_column("runs", "checkpoint_json")
    op.drop_column("runs", "current_step")
    op.drop_column("runs", "retry_count")
