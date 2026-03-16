from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Requirement

from .base import RepositoryBase


class RequirementRepository(RepositoryBase[Requirement]):
    def __init__(self, session: Session):
        super().__init__(session, Requirement)

    def list_by_project(self, project_id: str, limit: int = 50, offset: int = 0) -> list[Requirement]:
        stmt = (
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .where(Requirement.deleted_at.is_(None))
            .order_by(Requirement.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
