from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import Character

from .base import RepositoryBase


class CharacterRepository(RepositoryBase[Character]):
    def __init__(self, session: Session):
        super().__init__(session, Character)

    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[Character]:
        stmt = (
            select(Character)
            .where(Character.project_id == project_id)
            .where(Character.deleted_at.is_(None))
            .order_by(Character.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
