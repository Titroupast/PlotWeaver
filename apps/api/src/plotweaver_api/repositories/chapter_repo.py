from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Chapter

from .base import RepositoryBase


class ChapterRepository(RepositoryBase[Chapter]):
    def __init__(self, session: Session):
        super().__init__(session, Chapter)

    def list_by_project(self, project_id: str, limit: int = 50, offset: int = 0) -> list[Chapter]:
        stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .where(Chapter.deleted_at.is_(None))
            .order_by(Chapter.order_index.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
