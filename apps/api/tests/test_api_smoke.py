from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from plotweaver_api.dependencies.services import (
    get_chapter_service,
    get_health_service,
    get_memory_service,
    get_project_service,
)
from plotweaver_api.main import create_app
from plotweaver_api.schemas.chapter import ChapterLatestContentResponse
from plotweaver_api.schemas.common import HealthResponse
from plotweaver_api.schemas.memory import (
    MemoryDeltaDecisionRequest,
    MemoryDeltaDecisionResponse,
    MemoryDeltaResponse,
    MemoryHistoryItem,
    MemorySnapshotItem,
    MemorySnapshotResponse,
    MergeDecisionResponse,
)


class _FakeHealthService:
    def liveness(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="PlotWeaver API",
            timestamp=datetime.now(timezone.utc),
        )

    def readiness(self) -> HealthResponse:
        return HealthResponse(
            status="ready",
            service="PlotWeaver API",
            timestamp=datetime.now(timezone.utc),
        )


class _FakeProjectService:
    def get(self, _project_id: str):
        return None


class _FakeChapterService:
    def get_latest_content(self, project_id: str, chapter_id: str):
        _ = project_id
        return ChapterLatestContentResponse(
            chapter_id=chapter_id,
            version_no=1,
            storage_bucket="local-filesystem",
            storage_key=f"projects/demo/chapters/{chapter_id}/v1.txt",
            content_sha256="abc123",
            byte_size=12,
            content="hello world",
            created_at=datetime.now(timezone.utc),
        )


class _FakeMemoryService:
    def list_characters(self, project_id: str, limit: int = 100, offset: int = 0):
        _ = (project_id, limit, offset)
        return []

    def list_memory_deltas(self, project_id: str, limit: int = 100, offset: int = 0, status: str | None = None):
        _ = (project_id, limit, offset)
        now = datetime.now(timezone.utc)
        return [
            MemoryDeltaResponse(
                id="delta-1",
                run_id="run-1",
                project_id=project_id,
                delta_type="STORY_SO_FAR",
                payload_json={"items": ["新的事件"]},
                gate_status=status or "PENDING_REVIEW",
                risk_level="HIGH",
                applied_at=None,
                applied_by=None,
                created_at=now,
            )
        ]

    def list_merge_decisions(self, project_id: str, limit: int = 100, offset: int = 0):
        _ = (project_id, limit, offset)
        return []

    def get_snapshots(self, project_id: str):
        return MemorySnapshotResponse(
            project_id=project_id,
            snapshots=[
                MemorySnapshotItem(
                    memory_type="CHARACTERS",
                    version_no=2,
                    summary_json=["主角：林渊"],
                    updated_at=datetime.now(timezone.utc),
                )
            ],
        )

    def list_history(self, project_id: str, limit: int = 100, offset: int = 0):
        _ = (limit, offset)
        now = datetime.now(timezone.utc)
        return [
            MemoryHistoryItem(
                id="mem-1",
                memory_type="CHARACTERS",
                version_no=2,
                summary_json=["主角：林渊"],
                created_at=now,
                updated_at=now,
            )
        ]

    def decide_delta(self, project_id: str, delta_id: str, payload: MemoryDeltaDecisionRequest, user_id: str | None):
        now = datetime.now(timezone.utc)
        status = "MERGED" if payload.decision == "MERGE" else "REJECTED"
        return MemoryDeltaDecisionResponse(
            delta=MemoryDeltaResponse(
                id=delta_id,
                run_id="run-1",
                project_id=project_id,
                delta_type="STORY_SO_FAR",
                payload_json={"items": ["新的事件"]},
                gate_status=status,
                risk_level="HIGH",
                applied_at=now,
                applied_by=user_id,
                created_at=now,
            ),
            merge_decision=MergeDecisionResponse(
                id="decision-1",
                project_id=project_id,
                run_id="run-1",
                delta_id=delta_id,
                decision_type=payload.decision,
                payload_json={"items": ["新的事件"]},
                reason=payload.reason,
                created_at=now,
            ),
        )


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_health_service] = lambda: _FakeHealthService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_chapter_service] = lambda: _FakeChapterService()
    app.dependency_overrides[get_memory_service] = lambda: _FakeMemoryService()
    return TestClient(app)


def test_request_id_header_is_set(client: TestClient) -> None:
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers


def test_not_found_error_shape_contains_trace_id(client: TestClient) -> None:
    resp = client.get("/api/v1/projects/pj-not-exists", headers={"x-request-id": "trace-1"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "PW-COMMON-404"
    assert body["trace_id"] == "trace-1"


def test_chapter_latest_content_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/projects/p1/chapters/c1/latest-content")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chapter_id"] == "c1"
    assert body["version_no"] == 1
    assert body["content"] == "hello world"


def test_memory_snapshots_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/memory/projects/p1/snapshots")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == "p1"
    assert len(body["snapshots"]) == 1
    assert body["snapshots"][0]["memory_type"] == "CHARACTERS"


def test_memory_deltas_pending_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/memory/projects/p1/deltas?status=PENDING_REVIEW")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["gate_status"] == "PENDING_REVIEW"


def test_memory_decision_endpoint(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/memory/projects/p1/deltas/delta-1/decision",
        json={"decision": "MERGE", "reason": "manual approve"},
        headers={"x-user-id": "user-1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["delta"]["gate_status"] == "MERGED"
    assert body["merge_decision"]["decision_type"] == "MERGE"
