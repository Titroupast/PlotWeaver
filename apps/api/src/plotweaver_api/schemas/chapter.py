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


class ChapterLatestContentResponse(BaseModel):
    chapter_id: str
    version_no: int
    storage_bucket: str
    storage_key: str
    content_sha256: str
    byte_size: int
    content: str
    created_at: datetime


class ChapterVersionItem(BaseModel):
    chapter_id: str
    version_no: int
    run_id: str | None = None
    version_title: str | None = None
    storage_bucket: str
    storage_key: str
    content_sha256: str
    byte_size: int
    created_at: datetime
