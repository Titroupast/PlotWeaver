from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Any | None = None
    trace_id: str | None = None


class PageParams(BaseModel):
    limit: int = 20
    offset: int = 0


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
