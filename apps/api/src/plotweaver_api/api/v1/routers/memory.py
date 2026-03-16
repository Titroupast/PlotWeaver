from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.services import get_memory_service
from plotweaver_api.schemas.memory import CharacterResponse, MemoryDeltaResponse, MergeDecisionResponse
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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryDeltaResponse]:
    return service.list_memory_deltas(project_id=project_id, limit=limit, offset=offset)


@router.get("/projects/{project_id}/merge-decisions", response_model=list[MergeDecisionResponse])
def list_merge_decisions(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemoryService = Depends(get_memory_service),
) -> list[MergeDecisionResponse]:
    return service.list_merge_decisions(project_id=project_id, limit=limit, offset=offset)
