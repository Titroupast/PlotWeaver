from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChapterCreateRequest(BaseModel):
    chapter_key: str
    kind: str = "NORMAL"
    title: str
    subtitle: str | None = None
    volume_id: str | None = None
    arc_id: str | None = None
    order_index: int
    status: str = "GENERATED"
    summary: str = ""


class ChapterResponse(BaseModel):
    id: str
    project_id: str
    chapter_key: str
    kind: str
    title: str
    order_index: int
    status: str
    summary: str
    created_at: datetime
    updated_at: datetime
