from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    character_id: str
    canonical_name: str
    display_name: str
    aliases_json: list[Any]
    merge_status: str
    card_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MemoryDeltaResponse(BaseModel):
    id: str
    run_id: str
    project_id: str
    delta_type: str
    payload_json: dict[str, Any]
    gate_status: str
    risk_level: str
    applied_at: datetime | None
    applied_by: str | None
    created_at: datetime


class MergeDecisionResponse(BaseModel):
    id: str
    project_id: str
    run_id: str | None
    delta_id: str | None
    decision_type: str
    payload_json: dict[str, Any]
    reason: str | None
    created_at: datetime


class MemorySnapshotItem(BaseModel):
    memory_type: str
    version_no: int
    summary_json: dict[str, Any] | list[Any] | None
    updated_at: datetime


class MemorySnapshotResponse(BaseModel):
    project_id: str
    snapshots: list[MemorySnapshotItem]


class MemoryHistoryItem(BaseModel):
    id: str
    memory_type: str
    version_no: int
    summary_json: dict[str, Any] | list[Any] | None
    created_at: datetime
    updated_at: datetime


class MemoryDeltaDecisionRequest(BaseModel):
    decision: Literal["MERGE", "REJECT"]
    reason: str | None = None


class MemoryDeltaDecisionResponse(BaseModel):
    delta: MemoryDeltaResponse
    merge_decision: MergeDecisionResponse | None
