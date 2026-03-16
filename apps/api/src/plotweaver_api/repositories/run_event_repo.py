from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import RunEvent

from .base import RepositoryBase


class RunEventRepository(RepositoryBase[RunEvent]):
    def __init__(self, session: Session):
        super().__init__(session, RunEvent)

    def list_by_run(self, run_id: str, limit: int = 200, offset: int = 0) -> list[RunEvent]:
        stmt = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
