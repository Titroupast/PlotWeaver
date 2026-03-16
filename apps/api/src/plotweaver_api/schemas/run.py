from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RunCreateRequest(BaseModel):
    project_id: str
    base_chapter_id: str | None = None
    target_chapter_id: str | None = None
    requirement_id: str | None = None
    idempotency_key: str


class RunResponse(BaseModel):
    id: str
    project_id: str
    state: str
    idempotency_key: str
    attempt_count: int
    created_at: datetime
    updated_at: datetime


class RunStateUpdateRequest(BaseModel):
    state: str
    error_code: str | None = None
    error_message: str | None = None
