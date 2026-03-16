"""add jsonb indexes and active partial indexes

Revision ID: 20260316_0002
Revises: 20260316_0001
Create Date: 2026-03-16 00:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0002"
down_revision = "20260316_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_requirements_payload_gin",
        "requirements",
        ["payload_json"],
        postgresql_using="gin",
        postgresql_ops={"payload_json": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_run_artifacts_payload_gin",
        "run_artifacts",
        ["payload_json"],
        postgresql_using="gin",
        postgresql_ops={"payload_json": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_characters_aliases_gin",
        "characters",
        ["aliases_json"],
        postgresql_using="gin",
    )

    op.create_index(
        "uq_chapters_key_active",
        "chapters",
        ["tenant_id", "project_id", "chapter_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_chapters_order_active",
        "chapters",
        ["tenant_id", "project_id", "order_index"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_chapters_order_active", table_name="chapters")
    op.drop_index("uq_chapters_key_active", table_name="chapters")
    op.drop_index("ix_characters_aliases_gin", table_name="characters")
    op.drop_index("ix_run_artifacts_payload_gin", table_name="run_artifacts")
    op.drop_index("ix_requirements_payload_gin", table_name="requirements")
