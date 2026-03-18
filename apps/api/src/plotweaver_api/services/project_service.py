from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import Chapter, ChapterVersion, Project
from plotweaver_api.db.settings import settings
from plotweaver_api.repositories.project_repo import ProjectRepository
from plotweaver_api.schemas.project import ProjectCreateRequest, ProjectImportResponse, ProjectResponse
from plotweaver_api.storage.interface import StorageClient
from plotweaver_api.storage.local_storage import LocalStorageClient


CHAPTER_RE = re.compile(r"^\s*(?:##\s*)?第\s*([0-9一二三四五六七八九十百千两零〇]+)\s*章\s*[：:]?\s*(.*)$")


class ProjectService:
    def __init__(self, repo: ProjectRepository, storage: StorageClient | None = None):
        self.repo = repo
        self.storage = storage or LocalStorageClient(root_dir=settings.storage_local_root)

    def create(self, tenant_id: str, payload: ProjectCreateRequest, user_id: str | None = None) -> ProjectResponse:
        project = Project(
            tenant_id=tenant_id,
            owner_user_id=user_id,
            title=payload.title,
            description=payload.description,
            language=payload.language,
            status="ACTIVE",
            created_by=user_id,
            updated_by=user_id,
        )
        saved = self.repo.add(project)
        return self._to_response(saved)

    def import_from_text(
        self,
        tenant_id: str,
        title: str,
        novel_text: str,
        description: str | None = None,
        language: str = "zh-CN",
        user_id: str | None = None,
    ) -> ProjectImportResponse:
        text = (novel_text or "").strip()
        if not text:
            raise ValidationError("Novel text is empty", details={"field": "file"})

        chapters = self._split_chapters(text)
        if not chapters:
            raise ValidationError("No chapter headings found", details={"hint": "Expected heading like 第1章"})

        project = Project(
            tenant_id=tenant_id,
            owner_user_id=user_id,
            title=title.strip(),
            description=description,
            language=language,
            status="ACTIVE",
            created_by=user_id,
            updated_by=user_id,
        )
        self.repo.add(project)

        for idx, chapter_payload in enumerate(chapters, start=1):
            order_index = chapter_payload.get("order_index") or idx
            chapter = Chapter(
                tenant_id=tenant_id,
                project_id=project.id,
                chapter_key=f"chapter_{idx:03d}",
                kind="NORMAL",
                title=chapter_payload["title"],
                subtitle=None,
                volume_id=None,
                arc_id=None,
                order_index=order_index,
                status="GENERATED",
                summary=(chapter_payload["content"][:120] if chapter_payload["content"] else ""),
                created_by=user_id,
                updated_by=user_id,
            )
            self.repo.session.add(chapter)
            self.repo.session.flush()

            content = chapter_payload["content"]
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            byte_size = len(content.encode("utf-8"))
            storage_key = f"projects/{project.id}/chapters/{chapter.id}/imports/v1.txt"
            self.storage.put_text(storage_key, content)

            version = ChapterVersion(
                tenant_id=tenant_id,
                chapter_id=chapter.id,
                version_no=1,
                source_type="IMPORTED",
                storage_bucket=settings.storage_bucket,
                storage_key=storage_key,
                content_sha256=content_hash,
                byte_size=byte_size,
                created_by=user_id,
            )
            self.repo.session.add(version)

        self.repo.session.flush()
        self.repo.session.refresh(project)
        return ProjectImportResponse(project=self._to_response(project), chapter_count=len(chapters))

    def delete(self, project_id: str, user_id: str | None = None) -> None:
        project = self.repo.get(project_id)
        if project is None or project.deleted_at is not None:
            raise NotFoundError("Project not found", details={"project_id": project_id})
        now = datetime.now(timezone.utc)
        project.deleted_at = now
        project.updated_at = now
        project.updated_by = user_id
        project.status = "ARCHIVED"
        self.repo.session.flush()

    def get(self, project_id: str) -> ProjectResponse | None:
        project = self.repo.get(project_id)
        if project is None or project.deleted_at is not None:
            return None
        return self._to_response(project)

    def list(self, tenant_id: str, limit: int = 20, offset: int = 0) -> list[ProjectResponse]:
        return [self._to_response(item) for item in self.repo.list_by_tenant(tenant_id, limit=limit, offset=offset)]

    @staticmethod
    def _parse_chinese_numeral(text: str) -> int | None:
        digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        units = {"十": 10, "百": 100, "千": 1000}
        total = 0
        current = 0
        for char in text:
            if char in digits:
                current = digits[char]
                continue
            if char in units:
                unit = units[char]
                if current == 0:
                    current = 1
                total += current * unit
                current = 0
                continue
            return None
        value = total + current
        return value if value > 0 else None

    @staticmethod
    def _parse_chapter_no(raw_no: str) -> int | None:
        raw_no = (raw_no or "").strip()
        if not raw_no:
            return None
        try:
            value = int(raw_no)
            return value if value > 0 else None
        except ValueError:
            return ProjectService._parse_chinese_numeral(raw_no)

    @staticmethod
    def _split_chapters(novel_text: str) -> list[dict[str, str | int]]:
        lines = novel_text.splitlines()
        chunks: list[dict[str, str | int]] = []
        current_title: str | None = None
        current_lines: list[str] = []
        current_no: int | None = None

        for line in lines:
            m = CHAPTER_RE.match(line.strip())
            if m:
                if current_title is not None:
                    chunks.append(
                        {
                            "title": current_title,
                            "content": "\n".join(current_lines).strip(),
                            "order_index": current_no,
                        }
                    )
                raw_chapter_no = m.group(1).strip()
                current_no = ProjectService._parse_chapter_no(raw_chapter_no)
                title_suffix = m.group(2).strip()
                title = f"第{raw_chapter_no}章"
                if title_suffix:
                    title = f"{title}：{title_suffix}"
                current_title = title
                # Follow Day6 split behavior: keep heading line in chapter body.
                current_lines = [line]
                continue
            if current_title is not None:
                current_lines.append(line)

        if current_title is not None:
            chunks.append(
                {
                    "title": current_title,
                    "content": "\n".join(current_lines).strip(),
                    "order_index": current_no,
                }
            )

        return [c for c in chunks if c["title"]]

    @staticmethod
    def _to_response(project: Project) -> ProjectResponse:
        return ProjectResponse(
            id=str(project.id),
            tenant_id=str(project.tenant_id),
            title=project.title,
            description=project.description,
            language=project.language,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
