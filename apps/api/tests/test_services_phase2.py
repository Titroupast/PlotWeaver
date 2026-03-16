from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from plotweaver_api.core.contracts import validate_requirement_payload
from plotweaver_api.core.errors import ValidationError
from plotweaver_api.schemas.run import RunCreateRequest
from plotweaver_api.services.run_service import RunService


class _FakeTaskRunner:
    def enqueue(self, task_name: str, payload: dict) -> str:
        assert task_name == "run_generation"
        assert "run_id" in payload
        return "task-1"


class _FakeRepo:
    def __init__(self):
        self.session = self

    def get_by_idempotency(self, tenant_id: str, key: str):
        return None

    def add(self, run):
        run.id = "run-1"
        run.created_at = datetime.now(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        return run

    def flush(self):
        return None

    def refresh(self, _obj):
        return None


def test_requirement_contract_validation_missing_keys() -> None:
    with pytest.raises(ValidationError):
        validate_requirement_payload({"chapter_goal": "x"})


def test_run_service_create_drives_state_to_succeeded() -> None:
    service = RunService(repo=_FakeRepo(), task_runner=_FakeTaskRunner())
    payload = RunCreateRequest(project_id="proj-1", idempotency_key="idem-1")
    out = service.create(tenant_id="tenant-1", payload=payload)
    assert out.state == "SUCCEEDED"
    assert out.attempt_count == 1
