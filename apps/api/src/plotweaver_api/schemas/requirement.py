from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RequirementCreateRequest(BaseModel):
    chapter_goal: str = ""
    payload_json: dict[str, Any]
    payload_hash: str = ""
    source: str = "API"


class RequirementResponse(BaseModel):
    id: str
    project_id: str
    chapter_goal: str
    payload_json: dict[str, Any]
    payload_hash: str = ""
    source: str
    created_at: datetime
