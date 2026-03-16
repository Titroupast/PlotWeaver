from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Project

from .base import RepositoryBase


class ProjectRepository(RepositoryBase[Project]):
    def __init__(self, session: Session):
        super().__init__(session, Project)

    def list_by_tenant(self, tenant_id: str, limit: int = 20, offset: int = 0) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
