"""create core task-c tables

Revision ID: 20260316_0001
Revises:
Create Date: 2026-03-16 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260316_0001"
down_revision = None
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _uuid_col(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, UUID, nullable=nullable)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "projects",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        sa.Column("owner_user_id", UUID, nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False, server_default=sa.text("'zh-CN'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
    )

    op.create_index(
        "uq_projects_tenant_title_active",
        "projects",
        ["tenant_id", "title"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "chapters",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("chapter_key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False, server_default=sa.text("'NORMAL'")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("volume_id", sa.Text(), nullable=True),
        sa.Column("arc_id", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'GENERATED'")),
        sa.Column("summary", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("order_index >= 0", name="ck_chapters_order_index_non_negative"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "project_id", "chapter_key", name="uq_chapters_tenant_project_key"),
        sa.UniqueConstraint("tenant_id", "project_id", "order_index", name="uq_chapters_tenant_project_order"),
    )
    op.create_index("ix_chapters_tenant_project_order", "chapters", ["tenant_id", "project_id", "order_index"])

    op.create_table(
        "chapter_versions",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("chapter_id"),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version_no > 0", name="ck_chapter_versions_version_no_positive"),
        sa.CheckConstraint("byte_size >= 0", name="ck_chapter_versions_byte_size_non_negative"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "chapter_id", "version_no", name="uq_chapter_versions_tenant_chapter_version"),
    )
    op.create_index("ix_chapter_versions_tenant_chapter_version", "chapter_versions", ["tenant_id", "chapter_id", "version_no"])

    op.create_table(
        "requirements",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("chapter_goal", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=sa.text("'API'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_requirements_tenant_project_created", "requirements", ["tenant_id", "project_id", "created_at"])

    op.create_table(
        "runs",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("base_chapter_id", UUID, nullable=True),
        sa.Column("target_chapter_id", UUID, nullable=True),
        sa.Column("requirement_id", UUID, nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "uq_runs_tenant_idempotency_active",
        "runs",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_runs_tenant_project_state_created", "runs", ["tenant_id", "project_id", "state", "created_at"])

    op.create_table(
        "run_artifacts",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("run_id"),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "run_id", "artifact_type", "version_no", name="uq_run_artifacts_tenant_run_type_version"),
    )
    op.create_index("ix_run_artifacts_tenant_run_type_version", "run_artifacts", ["tenant_id", "run_id", "artifact_type", "version_no"])

    op.create_table(
        "memories",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("summary_json", JSONB, nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "project_id", "memory_type", "version_no", name="uq_memories_tenant_project_type_version"),
    )
    op.create_index("ix_memories_tenant_project_type", "memories", ["tenant_id", "project_id", "memory_type"])

    op.create_table(
        "characters",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("character_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("aliases_json", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("merge_status", sa.String(length=32), nullable=False, server_default=sa.text("'CONFIRMED'")),
        sa.Column("card_json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "project_id", "character_id", name="uq_characters_tenant_project_character_id"),
    )
    op.create_index("ix_characters_tenant_project_merge_status", "characters", ["tenant_id", "project_id", "merge_status"])

    op.create_table(
        "memory_deltas",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("run_id"),
        _uuid_col("project_id"),
        sa.Column("delta_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("gate_status", sa.String(length=32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memory_deltas_tenant_run_type", "memory_deltas", ["tenant_id", "run_id", "delta_type"])

    op.create_table(
        "merge_decisions",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        _uuid_col("tenant_id"),
        _uuid_col("project_id"),
        sa.Column("run_id", UUID, nullable=True),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_merge_decisions_tenant_project_created", "merge_decisions", ["tenant_id", "project_id", "created_at"])


def downgrade() -> None:
    for table in [
        "merge_decisions",
        "memory_deltas",
        "characters",
        "memories",
        "run_artifacts",
        "runs",
        "requirements",
        "chapter_versions",
        "chapters",
        "projects",
        "tenants",
    ]:
        op.drop_table(table)
