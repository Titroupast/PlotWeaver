from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArtifactCreateRequest(BaseModel):
    run_id: str
    artifact_type: str
    version_no: int = 1
    payload_json: dict[str, Any]
    payload_hash: str = ""


class ArtifactResponse(BaseModel):
    id: str
    run_id: str
    artifact_type: str
    version_no: int
    payload_json: dict[str, Any]
    payload_hash: str = ""
    created_at: datetime
