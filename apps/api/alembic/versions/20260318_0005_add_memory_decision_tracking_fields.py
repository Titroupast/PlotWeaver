"""add memory decision tracking fields

Revision ID: 20260318_0005
Revises: 20260316_0004
Create Date: 2026-03-18 11:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_0005"
down_revision = "20260316_0004"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "memory_deltas",
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default=sa.text("'LOW'")),
    )
    op.add_column("memory_deltas", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("memory_deltas", sa.Column("applied_by", UUID, nullable=True))

    op.add_column("merge_decisions", sa.Column("delta_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_merge_decisions_delta_id",
        "merge_decisions",
        "memory_deltas",
        ["delta_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_merge_decisions_tenant_delta_created",
        "merge_decisions",
        ["tenant_id", "delta_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_merge_decisions_tenant_delta_created", table_name="merge_decisions")
    op.drop_constraint("fk_merge_decisions_delta_id", "merge_decisions", type_="foreignkey")
    op.drop_column("merge_decisions", "delta_id")

    op.drop_column("memory_deltas", "applied_by")
    op.drop_column("memory_deltas", "applied_at")
    op.drop_column("memory_deltas", "risk_level")
