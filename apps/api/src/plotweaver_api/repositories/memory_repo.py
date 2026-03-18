from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Memory

from .base import RepositoryBase


class MemoryRepository(RepositoryBase[Memory]):
    def __init__(self, session: Session):
        super().__init__(session, Memory)

    def get_latest_by_type(self, project_id: str, memory_type: str) -> Memory | None:
        stmt = (
            select(Memory)
            .where(Memory.project_id == project_id)
            .where(Memory.memory_type == memory_type)
            .where(Memory.deleted_at.is_(None))
            .order_by(Memory.version_no.desc(), Memory.updated_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_latest_by_project(self, project_id: str) -> list[Memory]:
        items: list[Memory] = []
        for memory_type in ("CHARACTERS", "WORLD_RULES", "STORY_SO_FAR"):
            row = self.get_latest_by_type(project_id, memory_type)
            if row is not None:
                items.append(row)
        return items

    def list_history(self, project_id: str, limit: int = 100, offset: int = 0) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.project_id == project_id)
            .where(Memory.deleted_at.is_(None))
            .order_by(Memory.memory_type.asc(), Memory.version_no.desc(), Memory.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
