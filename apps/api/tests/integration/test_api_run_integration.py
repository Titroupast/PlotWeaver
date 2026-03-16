from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from plotweaver_api.core.errors import ConflictError, NotFoundError, ValidationError
from plotweaver_api.dependencies.services import get_orchestrator_service, get_run_service
from plotweaver_api.main import create_app
from plotweaver_api.schemas.run import (
    HumanReviewDecisionRequest,
    RunEventResponse,
    RunExecuteRequest,
    RunResponse,
    RunStateUpdateRequest,
)


class _FakeRunService:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.run = RunResponse(
            id="run-1",
            project_id="proj-1",
            state="QUEUED",
            idempotency_key="idem-1",
            attempt_count=0,
            retry_count=0,
            current_step="PLANNER",
            checkpoint_json={"completed_steps": [], "artifact_ids": {}},
            created_at=now,
            updated_at=now,
        )

    def list(self, project_id: str, limit: int, offset: int) -> list[RunResponse]:
        _ = (project_id, limit, offset)
        return [self.run]

    def get(self, run_id: str) -> RunResponse:
        if run_id != self.run.id:
            raise NotFoundError("Run not found", details={"run_id": run_id})
        return self.run

    def create(self, tenant_id: str, payload: Any, user_id: str | None = None) -> RunResponse:
        _ = (tenant_id, payload, user_id)
        return self.run

    def update_state(self, run_id: str, payload: RunStateUpdateRequest) -> RunResponse:
        if run_id != self.run.id:
            raise NotFoundError("Run not found", details={"run_id": run_id})
        self.run = self.run.model_copy(update={"state": payload.state})
        return self.run


class _FakeOrchestratorService:
    def __init__(self, run_service: _FakeRunService):
        self._run_service = run_service
        now = datetime.now(timezone.utc)
        self._events = [
            RunEventResponse(
                id="evt-1",
                run_id="run-1",
                event_type="RUN_STARTED",
                step="PLANNER",
                payload_json={"attempt": 1},
                created_at=now,
                cursor=f"{now.isoformat().replace('+00:00', 'Z')}|evt-1",
            )
        ]
        self.last_after_cursor: str | None = None

    def execute(self, run_id: str, payload: RunExecuteRequest | None = None) -> RunResponse:
        _ = payload
        run = self._run_service.get(run_id)
        self._run_service.run = run.model_copy(update={"state": "SUCCEEDED", "current_step": "MEMORY_CURATOR"})
        return self._run_service.run

    def list_events(
        self,
        run_id: str,
        limit: int = 200,
        offset: int = 0,
        after_cursor: str | None = None,
    ) -> list[RunEventResponse]:
        _ = (run_id, limit, offset)
        self.last_after_cursor = after_cursor
        if after_cursor:
            return []
        return self._events

    def apply_human_review(self, run_id: str, payload: HumanReviewDecisionRequest) -> RunResponse:
        _ = payload
        run = self._run_service.get(run_id)
        if run.state != "WAITING_HUMAN_REVIEW":
            raise ConflictError("Run is not waiting for human review")
        self._run_service.run = run.model_copy(update={"state": "SUCCEEDED"})
        return self._run_service.run


def _build_client() -> tuple[TestClient, _FakeOrchestratorService]:
    app = create_app()
    run_service = _FakeRunService()
    orchestrator = _FakeOrchestratorService(run_service)
    app.dependency_overrides[get_run_service] = lambda: run_service
    app.dependency_overrides[get_orchestrator_service] = lambda: orchestrator
    return TestClient(app), orchestrator


def test_runs_events_support_after_cursor_filter() -> None:
    client, orchestrator = _build_client()

    resp = client.get("/api/v1/runs/run-1/events", params={"after_cursor": "2026-03-16T00:00:00Z|evt-0"})
    assert resp.status_code == 200
    assert resp.json() == []
    assert orchestrator.last_after_cursor == "2026-03-16T00:00:00Z|evt-0"


def test_run_stream_emits_state_and_done_events() -> None:
    client, _ = _build_client()

    client.post("/api/v1/runs/run-1/execute", json={})
    with client.stream("GET", "/api/v1/runs/run-1/stream") as stream_resp:
        body = "".join(stream_resp.iter_text())

    assert stream_resp.status_code == 200
    assert "event: run-event" in body
    assert "event: run-state" in body
    assert "event: done" in body


def test_error_shape_for_not_found_and_conflict() -> None:
    client, _ = _build_client()

    not_found = client.get("/api/v1/runs/run-404", headers={"x-request-id": "trace-nf"})
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "PW-COMMON-404"
    assert not_found.json()["trace_id"] == "trace-nf"

    conflict = client.post(
        "/api/v1/runs/run-1/review-decision",
        json={"decision": "APPROVE"},
        headers={"x-request-id": "trace-cf"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "PW-COMMON-409"
    assert conflict.json()["trace_id"] == "trace-cf"


def test_error_shape_for_validation_error() -> None:
    app = create_app()

    class _InvalidCursorOrchestrator(_FakeOrchestratorService):
        def list_events(self, run_id: str, limit: int = 200, offset: int = 0, after_cursor: str | None = None):
            _ = (run_id, limit, offset, after_cursor)
            raise ValidationError("Invalid after_cursor")

    run_service = _FakeRunService()
    app.dependency_overrides[get_run_service] = lambda: run_service
    app.dependency_overrides[get_orchestrator_service] = lambda: _InvalidCursorOrchestrator(run_service)
    client = TestClient(app)

    resp = client.get("/api/v1/runs/run-1/events", params={"after_cursor": "bad"}, headers={"x-request-id": "trace-v"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "PW-COMMON-422"
    assert resp.json()["trace_id"] == "trace-v"
