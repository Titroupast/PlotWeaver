from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from plotweaver_api.core.config import settings
from plotweaver_api.schemas.common import HealthResponse


class HealthService:
    def __init__(self, session: Session):
        self.session = session

    def liveness(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            timestamp=datetime.now(timezone.utc),
        )

    def readiness(self) -> HealthResponse:
        self.session.execute(text("SELECT 1"))
        return HealthResponse(
            status="ready",
            service=settings.app_name,
            timestamp=datetime.now(timezone.utc),
        )
