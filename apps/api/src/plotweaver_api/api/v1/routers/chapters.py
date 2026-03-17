from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_chapter_service
from plotweaver_api.schemas.chapter import ChapterCreateRequest, ChapterLatestContentResponse, ChapterResponse
from plotweaver_api.services.chapter_service import ChapterService

router = APIRouter(prefix="/projects/{project_id}/chapters", tags=["chapters"])


@router.get("", response_model=list[ChapterResponse])
def list_chapters(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ChapterService = Depends(get_chapter_service),
) -> list[ChapterResponse]:
    return service.list(project_id=project_id, limit=limit, offset=offset)


@router.post("", response_model=ChapterResponse, status_code=201)
def create_chapter(
    project_id: str,
    payload: ChapterCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: ChapterService = Depends(get_chapter_service),
) -> ChapterResponse:
    return service.create(tenant_id=tenant_id, project_id=project_id, payload=payload, user_id=user_id)


@router.get("/{chapter_id}/latest-content", response_model=ChapterLatestContentResponse)
def get_latest_chapter_content(
    project_id: str,
    chapter_id: str,
    service: ChapterService = Depends(get_chapter_service),
) -> ChapterLatestContentResponse:
    return service.get_latest_content(project_id=project_id, chapter_id=chapter_id)
