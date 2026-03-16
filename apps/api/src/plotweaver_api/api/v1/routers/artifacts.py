from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_artifact_service
from plotweaver_api.schemas.artifact import ArtifactCreateRequest, ArtifactResponse
from plotweaver_api.services.artifact_service import ArtifactService

router = APIRouter(prefix="/runs/{run_id}/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactResponse])
def list_artifacts(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: ArtifactService = Depends(get_artifact_service),
) -> list[ArtifactResponse]:
    return service.list(run_id=run_id, limit=limit, offset=offset)


@router.post("", response_model=ArtifactResponse, status_code=201)
def create_artifact(
    run_id: str,
    payload: ArtifactCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactResponse:
    payload = payload.model_copy(update={"run_id": run_id})
    return service.create(tenant_id=tenant_id, payload=payload)
