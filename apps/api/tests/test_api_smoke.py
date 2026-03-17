from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from plotweaver_api.dependencies.services import get_chapter_service, get_health_service, get_project_service
from plotweaver_api.main import create_app
from plotweaver_api.schemas.chapter import ChapterLatestContentResponse
from plotweaver_api.schemas.common import HealthResponse


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


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_health_service] = lambda: _FakeHealthService()
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_chapter_service] = lambda: _FakeChapterService()
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
