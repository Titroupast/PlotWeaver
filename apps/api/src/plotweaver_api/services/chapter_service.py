from __future__ import annotations

import hashlib
import re

from sqlalchemy import select

from plotweaver_api.core.errors import NotFoundError
from plotweaver_api.db.models import Chapter, ChapterVersion, RunArtifact
from plotweaver_api.repositories.chapter_repo import ChapterRepository
from plotweaver_api.schemas.chapter import ChapterCreateRequest, ChapterLatestContentResponse, ChapterResponse, ChapterVersionItem
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
        return self.get_content(project_id=project_id, chapter_id=chapter_id, version_no=None)

    def get_content(self, project_id: str, chapter_id: str, version_no: int | None = None) -> ChapterLatestContentResponse:
        chapter = self.repo.get(chapter_id)
        if chapter is None or chapter.deleted_at is not None or str(chapter.project_id) != project_id:
            raise NotFoundError("Chapter not found", details={"project_id": project_id, "chapter_id": chapter_id})

        stmt = select(ChapterVersion).where(ChapterVersion.chapter_id == chapter.id).where(ChapterVersion.deleted_at.is_(None))
        if version_no is not None:
            stmt = stmt.where(ChapterVersion.version_no == version_no)
        stmt = stmt.order_by(ChapterVersion.version_no.desc()).limit(1)
        latest = self.repo.session.scalar(stmt)
        if latest is None:
            raise NotFoundError(
                "Chapter content not found",
                details={"chapter_id": chapter_id, "version_no": version_no},
            )

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

    def update_content(
        self,
        project_id: str,
        chapter_id: str,
        content: str,
        version_no: int | None = None,
    ) -> ChapterLatestContentResponse:
        chapter = self.repo.get(chapter_id)
        if chapter is None or chapter.deleted_at is not None or str(chapter.project_id) != project_id:
            raise NotFoundError("Chapter not found", details={"project_id": project_id, "chapter_id": chapter_id})

        stmt = select(ChapterVersion).where(ChapterVersion.chapter_id == chapter.id).where(ChapterVersion.deleted_at.is_(None))
        if version_no is not None:
            stmt = stmt.where(ChapterVersion.version_no == version_no)
        stmt = stmt.order_by(ChapterVersion.version_no.desc()).limit(1)
        target = self.repo.session.scalar(stmt)
        if target is None:
            raise NotFoundError(
                "Chapter content not found",
                details={"chapter_id": chapter_id, "version_no": version_no},
            )

        payload = content or ""
        self.storage.put_text(target.storage_key, payload)
        encoded = payload.encode("utf-8")
        target.byte_size = len(encoded)
        target.content_sha256 = hashlib.sha256(encoded).hexdigest()
        self.repo.session.flush()

        return ChapterLatestContentResponse(
            chapter_id=str(chapter.id),
            version_no=target.version_no,
            storage_bucket=target.storage_bucket,
            storage_key=target.storage_key,
            content_sha256=target.content_sha256,
            byte_size=target.byte_size,
            content=payload,
            created_at=target.created_at,
        )

    def list_versions(self, project_id: str, chapter_id: str, limit: int = 50, offset: int = 0) -> list[ChapterVersionItem]:
        chapter = self.repo.get(chapter_id)
        if chapter is None or chapter.deleted_at is not None or str(chapter.project_id) != project_id:
            raise NotFoundError("Chapter not found", details={"project_id": project_id, "chapter_id": chapter_id})

        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter.id)
            .where(ChapterVersion.deleted_at.is_(None))
            .order_by(ChapterVersion.version_no.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self.repo.session.scalars(stmt).all())

        run_id_cache: dict[str, str | None] = {}
        title_by_run_id: dict[str, str] = {}
        for row in rows:
            run_id = self._extract_run_id_from_storage_key(row.storage_key)
            run_id_cache[row.storage_key] = run_id
            if not run_id or run_id in title_by_run_id:
                continue
            artifact_stmt = (
                select(RunArtifact)
                .where(RunArtifact.run_id == run_id)
                .where(RunArtifact.artifact_type == "CHAPTER_META")
                .where(RunArtifact.deleted_at.is_(None))
                .order_by(RunArtifact.created_at.desc())
                .limit(1)
            )
            artifact = self.repo.session.scalar(artifact_stmt)
            if artifact and isinstance(artifact.payload_json, dict):
                title = str(artifact.payload_json.get("title") or "").strip()
                if title:
                    title_by_run_id[run_id] = title

        return [
            ChapterVersionItem(
                chapter_id=str(chapter.id),
                version_no=row.version_no,
                run_id=run_id_cache.get(row.storage_key),
                version_title=title_by_run_id.get(run_id_cache.get(row.storage_key) or ""),
                storage_bucket=row.storage_bucket,
                storage_key=row.storage_key,
                content_sha256=row.content_sha256,
                byte_size=row.byte_size,
                created_at=row.created_at,
            )
            for row in rows
        ]

    @staticmethod
    def _extract_run_id_from_storage_key(storage_key: str) -> str | None:
        match = re.search(r"/runs/([0-9a-fA-F-]{36})/", storage_key or "")
        return match.group(1) if match else None

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
