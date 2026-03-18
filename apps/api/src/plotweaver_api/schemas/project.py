from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    title: str
    description: str | None = None
    language: str = "zh-CN"


class ProjectImportResponse(BaseModel):
    project: "ProjectResponse"
    chapter_count: int


class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None
    language: str
    status: str
    created_at: datetime
    updated_at: datetime


ProjectImportResponse.model_rebuild()
