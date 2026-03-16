from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
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

    def list_by_run_after(
        self,
        run_id: str,
        after_created_at: datetime | None,
        after_event_id: UUID | None,
        limit: int = 200,
    ) -> list[RunEvent]:
        stmt = select(RunEvent).where(RunEvent.run_id == run_id)
        if after_created_at is not None:
            if after_event_id:
                stmt = stmt.where(
                    or_(
                        RunEvent.created_at > after_created_at,
                        and_(RunEvent.created_at == after_created_at, RunEvent.id > after_event_id),
                    )
                )
            else:
                stmt = stmt.where(RunEvent.created_at > after_created_at)
        stmt = stmt.order_by(RunEvent.created_at.asc(), RunEvent.id.asc()).limit(limit)
        return list(self.session.scalars(stmt).all())
