from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChapterKind(str, enum.Enum):
    NORMAL = "NORMAL"
    PROLOGUE = "PROLOGUE"
    SIDE_STORY = "SIDE_STORY"
    EXTRA = "EXTRA"


class ChapterStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class RunState(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RUNNING_PLANNER = "RUNNING_PLANNER"
    RUNNING_WRITER = "RUNNING_WRITER"
    RUNNING_REVIEWER = "RUNNING_REVIEWER"
    RUNNING_MEMORY_CURATOR = "RUNNING_MEMORY_CURATOR"
    WAITING_HUMAN_REVIEW = "WAITING_HUMAN_REVIEW"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CANCELLED = "CANCELLED"


class ArtifactType(str, enum.Enum):
    OUTLINE = "OUTLINE"
    REVIEW = "REVIEW"
    MEMORY_GATE = "MEMORY_GATE"
    CHAPTER_META = "CHAPTER_META"


class MergeStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    PENDING_REVIEW = "PENDING_REVIEW"
    SPLIT_REQUIRED = "SPLIT_REQUIRED"


class MemoryType(str, enum.Enum):
    WORLD_RULES = "WORLD_RULES"
    STORY_SO_FAR = "STORY_SO_FAR"
    OTHER = "OTHER"


class DeltaType(str, enum.Enum):
    CHARACTERS = "CHARACTERS"
    WORLD_RULES = "WORLD_RULES"
    STORY_SO_FAR = "STORY_SO_FAR"


class DecisionType(str, enum.Enum):
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    ALIAS_LINK = "ALIAS_LINK"
    REJECT = "REJECT"
    PENDING_REVIEW = "PENDING_REVIEW"


class TenantScopedMixin:
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )


class AuditSoftDeleteMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Project(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "uq_projects_tenant_title_active",
            "tenant_id",
            "title",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    owner_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'zh-CN'"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'ACTIVE'"))

    chapters = relationship("Chapter", back_populates="project")


class Chapter(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "chapter_key", name="uq_chapters_tenant_project_key"),
        UniqueConstraint("tenant_id", "project_id", "order_index", name="uq_chapters_tenant_project_order"),
        CheckConstraint("order_index >= 0", name="ck_chapters_order_index_non_negative"),
        Index("ix_chapters_tenant_project_order", "tenant_id", "project_id", "order_index"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    chapter_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'NORMAL'"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    volume_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    arc_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'GENERATED'"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))

    project = relationship("Project", back_populates="chapters")
    versions = relationship("ChapterVersion", back_populates="chapter")


class ChapterVersion(Base, TenantScopedMixin):
    __tablename__ = "chapter_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "chapter_id", "version_no", name="uq_chapter_versions_tenant_chapter_version"),
        CheckConstraint("version_no > 0", name="ck_chapter_versions_version_no_positive"),
        CheckConstraint("byte_size >= 0", name="ck_chapter_versions_byte_size_non_negative"),
        Index("ix_chapter_versions_tenant_chapter_version", "tenant_id", "chapter_id", "version_no"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    chapter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chapter = relationship("Chapter", back_populates="versions")


class Requirement(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "requirements"
    __table_args__ = (
        Index("ix_requirements_tenant_project_created", "tenant_id", "project_id", "created_at"),
        Index(
            "ix_requirements_payload_gin",
            "payload_json",
            postgresql_using="gin",
            postgresql_ops={"payload_json": "jsonb_path_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_goal: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'API'"))


class Run(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "runs"
    __table_args__ = (
        Index("uq_runs_tenant_idempotency_active", "tenant_id", "idempotency_key", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_runs_tenant_project_state_created", "tenant_id", "project_id", "state", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    base_chapter_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    target_chapter_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoint_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunEvent(Base, TenantScopedMixin):
    __tablename__ = "run_events"
    __table_args__ = (
        Index("ix_run_events_tenant_run_created", "tenant_id", "run_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RunArtifact(Base, TenantScopedMixin):
    __tablename__ = "run_artifacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "artifact_type", "version_no", name="uq_run_artifacts_tenant_run_type_version"),
        Index("ix_run_artifacts_tenant_run_type_version", "tenant_id", "run_id", "artifact_type", "version_no"),
        Index(
            "ix_run_artifacts_payload_gin",
            "payload_json",
            postgresql_using="gin",
            postgresql_ops={"payload_json": "jsonb_path_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Memory(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "memory_type", "version_no", name="uq_memories_tenant_project_type_version"),
        Index("ix_memories_tenant_project_type", "tenant_id", "project_id", "memory_type"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_bucket: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class Character(Base, TenantScopedMixin, AuditSoftDeleteMixin):
    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "character_id", name="uq_characters_tenant_project_character_id"),
        Index("ix_characters_tenant_project_merge_status", "tenant_id", "project_id", "merge_status"),
        Index(
            "ix_characters_aliases_gin",
            "aliases_json",
            postgresql_using="gin",
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    merge_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'CONFIRMED'"))
    card_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class MemoryDelta(Base, TenantScopedMixin):
    __tablename__ = "memory_deltas"
    __table_args__ = (
        Index("ix_memory_deltas_tenant_run_type", "tenant_id", "run_id", "delta_type"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    delta_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    gate_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'PENDING'"))
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'LOW'"))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MergeDecision(Base, TenantScopedMixin):
    __tablename__ = "merge_decisions"
    __table_args__ = (
        Index("ix_merge_decisions_tenant_project_created", "tenant_id", "project_id", "created_at"),
        Index("ix_merge_decisions_tenant_delta_created", "tenant_id", "delta_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    delta_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("memory_deltas.id", ondelete="SET NULL"), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
