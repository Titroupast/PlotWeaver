from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.services import get_memory_service
from plotweaver_api.schemas.memory import (
    CharacterResponse,
    MemoryDeltaDecisionRequest,
    MemoryDeltaDecisionResponse,
    MemoryDeltaResponse,
    MemoryHistoryItem,
    MemoryRebuildResponse,
    MemorySnapshotResponse,
    MergeDecisionResponse,
)
from plotweaver_api.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/projects/{project_id}/characters", response_model=list[CharacterResponse])
def list_characters(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[CharacterResponse]:
    return service.list_characters(project_id=project_id, limit=limit, offset=offset)


@router.get("/projects/{project_id}/deltas", response_model=list[MemoryDeltaResponse])
def list_memory_deltas(
    project_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryDeltaResponse]:
    return service.list_memory_deltas(project_id=project_id, status=status, limit=limit, offset=offset)


@router.post("/projects/{project_id}/deltas/{delta_id}/decision", response_model=MemoryDeltaDecisionResponse)
def decide_memory_delta(
    project_id: str,
    delta_id: str,
    payload: MemoryDeltaDecisionRequest,
    user_id: str | None = Depends(get_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDeltaDecisionResponse:
    return service.decide_delta(project_id=project_id, delta_id=delta_id, payload=payload, user_id=user_id)


@router.get("/projects/{project_id}/snapshots", response_model=MemorySnapshotResponse)
def get_memory_snapshots(
    project_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> MemorySnapshotResponse:
    return service.get_snapshots(project_id=project_id)


@router.get("/projects/{project_id}/history", response_model=list[MemoryHistoryItem])
def list_memory_history(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryHistoryItem]:
    return service.list_history(project_id=project_id, limit=limit, offset=offset)


@router.post("/projects/{project_id}/rebuild", response_model=MemoryRebuildResponse)
def rebuild_memory_summary(
    project_id: str,
    user_id: str | None = Depends(get_user_id),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryRebuildResponse:
    return service.rebuild_project_summary(project_id=project_id, user_id=user_id)


@router.get("/projects/{project_id}/merge-decisions", response_model=list[MergeDecisionResponse])
def list_merge_decisions(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[MergeDecisionResponse]:
    return service.list_merge_decisions(project_id=project_id, limit=limit, offset=offset)
