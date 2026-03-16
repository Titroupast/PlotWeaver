from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_run_service
from plotweaver_api.schemas.run import RunCreateRequest, RunResponse, RunStateUpdateRequest
from plotweaver_api.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunResponse])
def list_runs(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RunService = Depends(get_run_service),
) -> list[RunResponse]:
    return service.list(project_id=project_id, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> RunResponse:
    return service.get(run_id)


@router.post("", response_model=RunResponse, status_code=201)
def create_run(
    payload: RunCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    return service.create(tenant_id=tenant_id, payload=payload, user_id=user_id)


@router.patch("/{run_id}/state", response_model=RunResponse)
def update_run_state(
    run_id: str,
    payload: RunStateUpdateRequest,
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    return service.update_state(run_id=run_id, payload=payload)
