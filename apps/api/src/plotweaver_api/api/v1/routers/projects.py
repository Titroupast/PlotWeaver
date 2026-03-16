from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_project_service
from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.schemas.project import ProjectCreateRequest, ProjectResponse
from plotweaver_api.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return service.list(tenant_id=tenant_id, limit=limit, offset=offset)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return service.create(tenant_id=tenant_id, payload=payload, user_id=user_id)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    project = service.get(project_id)
    if project is None:
        from plotweaver_api.core.errors import NotFoundError

        raise NotFoundError("Project not found", details={"project_id": project_id})
    return project
