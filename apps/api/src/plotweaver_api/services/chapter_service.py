from __future__ import annotations

from sqlalchemy import select

from plotweaver_api.core.errors import NotFoundError
from plotweaver_api.db.models import Chapter, ChapterVersion
from plotweaver_api.repositories.chapter_repo import ChapterRepository
from plotweaver_api.schemas.chapter import ChapterCreateRequest, ChapterLatestContentResponse, ChapterResponse
from plotweaver_api.storage.interface import StorageClient
from plotweaver_api.storage.local_storage import LocalStorageClient


class ChapterService:
    def __init__(self, repo: ChapterRepository, storage: StorageClient | None = None):
        self.repo = repo
        self.storage = storage or LocalStorageClient()

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

    def get_latest_content(self, project_id: str, chapter_id: str) -> ChapterLatestContentResponse:
        chapter = self.repo.get(chapter_id)
        if chapter is None or chapter.deleted_at is not None or str(chapter.project_id) != project_id:
            raise NotFoundError("Chapter not found", details={"project_id": project_id, "chapter_id": chapter_id})

        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter.id)
            .where(ChapterVersion.deleted_at.is_(None))
            .order_by(ChapterVersion.version_no.desc())
            .limit(1)
        )
        latest = self.repo.session.scalar(stmt)
        if latest is None:
            raise NotFoundError("Chapter content not found", details={"chapter_id": chapter_id})

        content = self.storage.get_text(latest.storage_key)
        return ChapterLatestContentResponse(
            chapter_id=str(chapter.id),
            version_no=latest.version_no,
            storage_bucket=latest.storage_bucket,
            storage_key=latest.storage_key,
            content_sha256=latest.content_sha256,
            byte_size=latest.byte_size,
            content=content,
            created_at=latest.created_at,
        )

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
