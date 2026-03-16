from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Run

from .base import RepositoryBase


class RunRepository(RepositoryBase[Run]):
    def __init__(self, session: Session):
        super().__init__(session, Run)

    def get_by_idempotency(self, tenant_id: str, idempotency_key: str) -> Run | None:
        stmt = (
            select(Run)
            .where(Run.tenant_id == tenant_id)
            .where(Run.idempotency_key == idempotency_key)
            .where(Run.deleted_at.is_(None))
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_by_project(self, project_id: str, limit: int = 50, offset: int = 0) -> list[Run]:
        stmt = (
            select(Run)
            .where(Run.project_id == project_id)
            .where(Run.deleted_at.is_(None))
            .order_by(Run.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def list_retryable(self, limit: int = 100, offset: int = 0) -> list[Run]:
        stmt = (
            select(Run)
            .where(Run.state.in_(["RETRYING", "FAILED"]))
            .where(Run.deleted_at.is_(None))
            .order_by(Run.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
