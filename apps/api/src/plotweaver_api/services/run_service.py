from __future__ import annotations

from plotweaver_api.core.errors import ConflictError, NotFoundError
from plotweaver_api.db.models import Run
from plotweaver_api.repositories.run_repo import RunRepository
from plotweaver_api.schemas.run import RunCreateRequest, RunResponse, RunStateUpdateRequest
from plotweaver_api.tasks.interface import TaskRunner


class RunService:
    def __init__(self, repo: RunRepository, task_runner: TaskRunner):
        self.repo = repo
        self.task_runner = task_runner

    def create(self, tenant_id: str, payload: RunCreateRequest, user_id: str | None = None) -> RunResponse:
        existing = self.repo.get_by_idempotency(tenant_id, payload.idempotency_key)
        if existing is not None:
            raise ConflictError("Run with same idempotency key already exists", details={"run_id": str(existing.id)})

        run = Run(
            tenant_id=tenant_id,
            project_id=payload.project_id,
            base_chapter_id=payload.base_chapter_id,
            target_chapter_id=payload.target_chapter_id,
            requirement_id=payload.requirement_id,
            state="QUEUED",
            idempotency_key=payload.idempotency_key,
            attempt_count=0,
            retry_count=0,
            current_step="PLANNER",
            checkpoint_json={"completed_steps": [], "artifact_ids": {}},
            created_by=user_id,
            updated_by=user_id,
        )
        run = self.repo.add(run)

        task_id = self.task_runner.enqueue(
            task_name="run_orchestration",
            payload={
                "run_id": str(run.id),
                "tenant_id": tenant_id,
                "project_id": str(run.project_id),
            },
        )
        run.checkpoint_json["task_id"] = task_id

        self.repo.session.flush()
        self.repo.session.refresh(run)
        return self._to_response(run)

    def get(self, run_id: str) -> RunResponse:
        run = self.repo.get(run_id)
        if run is None or run.deleted_at is not None:
            raise NotFoundError("Run not found", details={"run_id": run_id})
        return self._to_response(run)

    def list(self, project_id: str, limit: int = 50, offset: int = 0) -> list[RunResponse]:
        return [self._to_response(item) for item in self.repo.list_by_project(project_id, limit=limit, offset=offset)]

    def update_state(self, run_id: str, payload: RunStateUpdateRequest) -> RunResponse:
        run = self.repo.get(run_id)
        if run is None or run.deleted_at is not None:
            raise NotFoundError("Run not found", details={"run_id": run_id})
        run.state = payload.state
        run.error_code = payload.error_code
        run.error_message = payload.error_message
        self.repo.session.flush()
        self.repo.session.refresh(run)
        return self._to_response(run)

    @staticmethod
    def _to_response(run: Run) -> RunResponse:
        return RunResponse(
            id=str(run.id),
            project_id=str(run.project_id),
            state=run.state,
            idempotency_key=run.idempotency_key,
            attempt_count=run.attempt_count,
            retry_count=run.retry_count,
            current_step=run.current_step,
            checkpoint_json=run.checkpoint_json,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
