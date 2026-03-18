from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import MergeDecision

from .base import RepositoryBase


class MergeDecisionRepository(RepositoryBase[MergeDecision]):
    def __init__(self, session: Session):
        super().__init__(session, MergeDecision)

    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MergeDecision]:
        stmt = (
            select(MergeDecision)
            .where(MergeDecision.project_id == project_id)
            .where(MergeDecision.deleted_at.is_(None))
            .order_by(MergeDecision.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_delta(self, delta_id: str, limit: int = 20, offset: int = 0) -> list[MergeDecision]:
        stmt = (
            select(MergeDecision)
            .where(MergeDecision.delta_id == delta_id)
            .where(MergeDecision.deleted_at.is_(None))
            .order_by(MergeDecision.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
