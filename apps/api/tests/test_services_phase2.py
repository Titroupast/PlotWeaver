from __future__ import annotations

from datetime import datetime, timezone

import pytest

from plotweaver_api.core.contracts import validate_requirement_payload
from plotweaver_api.core.errors import ConflictError, NotFoundError, ValidationError
from plotweaver_api.schemas.run import RunCreateRequest, RunStateUpdateRequest
from plotweaver_api.services.run_service import RunService


class _FakeTaskRunner:
    def enqueue(self, task_name: str, payload: dict) -> str:
        assert task_name == "run_orchestration"
        assert "run_id" in payload
        return "task-1"


class _FakeRepo:
    def __init__(self):
        self.session = self
        self._runs = []
        self._by_id = {}

    def get_by_idempotency(self, tenant_id: str, key: str):
        for run in self._runs:
            if run.tenant_id == tenant_id and run.idempotency_key == key and run.deleted_at is None:
                return run
        return None

    def add(self, run):
        run.id = f"run-{len(self._runs) + 1}"
        run.created_at = datetime.now(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        run.deleted_at = None
        self._runs.append(run)
        self._by_id[run.id] = run
        return run

    def flush(self):
        return None

    def refresh(self, _obj):
        return None

    def get(self, run_id: str):
        return self._by_id.get(run_id)

    def list_by_project(self, project_id: str, limit: int = 50, offset: int = 0):
        matches = [run for run in self._runs if str(run.project_id) == project_id]
        return matches[offset : offset + limit]


def test_requirement_contract_validation_missing_keys() -> None:
    with pytest.raises(ValidationError):
        validate_requirement_payload({"chapter_goal": "x"})


def test_run_service_create_sets_queued_and_checkpoint() -> None:
    service = RunService(repo=_FakeRepo(), task_runner=_FakeTaskRunner())
    payload = RunCreateRequest(project_id="proj-1", idempotency_key="idem-1")
    out = service.create(tenant_id="tenant-1", payload=payload)
    assert out.state == "QUEUED"
    assert out.current_step == "PLANNER"
    assert out.checkpoint_json["task_id"] == "task-1"


def test_run_service_create_conflict_on_duplicate_idempotency_key() -> None:
    repo = _FakeRepo()
    service = RunService(repo=repo, task_runner=_FakeTaskRunner())
    payload = RunCreateRequest(project_id="proj-1", idempotency_key="idem-dup")
    service.create(tenant_id="tenant-1", payload=payload)
    with pytest.raises(ConflictError):
        service.create(tenant_id="tenant-1", payload=payload)


def test_run_service_get_update_and_list_paths() -> None:
    repo = _FakeRepo()
    service = RunService(repo=repo, task_runner=_FakeTaskRunner())
    created = service.create(
        tenant_id="tenant-1",
        payload=RunCreateRequest(project_id="proj-1", idempotency_key="idem-2"),
    )

    fetched = service.get(created.id)
    assert fetched.id == created.id

    updated = service.update_state(
        created.id,
        RunStateUpdateRequest(state="FAILED", error_code="X", error_message="bad"),
    )
    assert updated.state == "FAILED"
    assert updated.retry_count == 0

    listed = service.list("proj-1")
    assert len(listed) == 1


def test_run_service_not_found_raises() -> None:
    service = RunService(repo=_FakeRepo(), task_runner=_FakeTaskRunner())
    with pytest.raises(NotFoundError):
        service.get("missing-run")
