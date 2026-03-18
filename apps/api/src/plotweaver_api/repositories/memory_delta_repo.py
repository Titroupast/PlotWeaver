from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import MemoryDelta

from .base import RepositoryBase


class MemoryDeltaRepository(RepositoryBase[MemoryDelta]):
    def __init__(self, session: Session):
        super().__init__(session, MemoryDelta)

    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MemoryDelta]:
        stmt = (
            select(MemoryDelta)
            .where(MemoryDelta.project_id == project_id)
            .where(MemoryDelta.deleted_at.is_(None))
            .order_by(MemoryDelta.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_project_status(self, project_id: str, gate_status: str, limit: int = 100, offset: int = 0) -> list[MemoryDelta]:
        stmt = (
            select(MemoryDelta)
            .where(MemoryDelta.project_id == project_id)
            .where(MemoryDelta.gate_status == gate_status)
            .where(MemoryDelta.deleted_at.is_(None))
            .order_by(MemoryDelta.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
