from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_requirement_service
from plotweaver_api.schemas.requirement import RequirementCreateRequest, RequirementResponse
from plotweaver_api.services.requirement_service import RequirementService

router = APIRouter(prefix="/projects/{project_id}/requirements", tags=["requirements"])


@router.get("", response_model=list[RequirementResponse])
def list_requirements(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RequirementService = Depends(get_requirement_service),
) -> list[RequirementResponse]:
    return service.list(project_id=project_id, limit=limit, offset=offset)


@router.post("", response_model=RequirementResponse, status_code=201)
def create_requirement(
    project_id: str,
    payload: RequirementCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: RequirementService = Depends(get_requirement_service),
) -> RequirementResponse:
    return service.create(tenant_id=tenant_id, project_id=project_id, payload=payload, user_id=user_id)
