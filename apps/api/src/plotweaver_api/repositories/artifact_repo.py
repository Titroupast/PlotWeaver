from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotweaver_api.db.models import RunArtifact

from .base import RepositoryBase


class ArtifactRepository(RepositoryBase[RunArtifact]):
    def __init__(self, session: Session):
        super().__init__(session, RunArtifact)

    def list_by_run(self, run_id: str, limit: int = 100, offset: int = 0) -> list[RunArtifact]:
        stmt = (
            select(RunArtifact)
            .where(RunArtifact.run_id == run_id)
            .where(RunArtifact.deleted_at.is_(None))
            .order_by(RunArtifact.version_no.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())
