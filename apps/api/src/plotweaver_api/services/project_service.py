from __future__ import annotations

from plotweaver_api.db.models import Project
from plotweaver_api.repositories.project_repo import ProjectRepository
from plotweaver_api.schemas.project import ProjectCreateRequest, ProjectResponse


class ProjectService:
    def __init__(self, repo: ProjectRepository):
        self.repo = repo

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

    def get(self, project_id: str) -> ProjectResponse | None:
        project = self.repo.get(project_id)
        if project is None or project.deleted_at is not None:
            return None
        return self._to_response(project)

    def list(self, tenant_id: str, limit: int = 20, offset: int = 0) -> list[ProjectResponse]:
        return [self._to_response(item) for item in self.repo.list_by_tenant(tenant_id, limit=limit, offset=offset)]

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
