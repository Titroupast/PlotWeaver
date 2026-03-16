from __future__ import annotations

from plotweaver_api.db.models import Chapter
from plotweaver_api.repositories.chapter_repo import ChapterRepository
from plotweaver_api.schemas.chapter import ChapterCreateRequest, ChapterResponse


class ChapterService:
    def __init__(self, repo: ChapterRepository):
        self.repo = repo

    def create(self, tenant_id: str, project_id: str, payload: ChapterCreateRequest, user_id: str | None = None) -> ChapterResponse:
        chapter = Chapter(
            tenant_id=tenant_id,
            project_id=project_id,
            chapter_key=payload.chapter_key,
            kind=payload.kind,
            title=payload.title,
            subtitle=payload.subtitle,
            volume_id=payload.volume_id,
            arc_id=payload.arc_id,
            order_index=payload.order_index,
            status=payload.status,
            summary=payload.summary,
            created_by=user_id,
            updated_by=user_id,
        )
        saved = self.repo.add(chapter)
        return self._to_response(saved)

    def list(self, project_id: str, limit: int = 50, offset: int = 0) -> list[ChapterResponse]:
        return [self._to_response(item) for item in self.repo.list_by_project(project_id, limit=limit, offset=offset)]

    @staticmethod
    def _to_response(chapter: Chapter) -> ChapterResponse:
        return ChapterResponse(
            id=str(chapter.id),
            project_id=str(chapter.project_id),
            chapter_key=chapter.chapter_key,
            kind=chapter.kind,
            title=chapter.title,
            order_index=chapter.order_index,
            status=chapter.status,
            summary=chapter.summary,
            created_at=chapter.created_at,
            updated_at=chapter.updated_at,
        )
