from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from plotweaver_api.schemas.run import HumanReviewDecisionRequest, RunExecuteRequest
from plotweaver_api.services.orchestrator_service import OrchestratorService


class _FakeSession:
    def flush(self):
        return None

    def refresh(self, _obj):
        return None


class _FakeRunRepo:
    def __init__(self, run):
        self._run = run
        self.session = _FakeSession()

    def get(self, run_id: str):
        return self._run if str(self._run.id) == run_id else None


class _FakeArtifactRepo:
    def __init__(self):
        self.items = []

    def list_by_run(self, run_id: str, limit: int = 200, offset: int = 0):
        return [x for x in self.items if str(x.run_id) == run_id][offset : offset + limit]

    @property
    def session(self):
        return _FakeSession()

    def add(self, artifact):
        artifact.id = f"art-{len(self.items)+1}"
        artifact.created_at = datetime.now(timezone.utc)
        self.items.append(artifact)
        return artifact


class _FakeEventRepo:
    def __init__(self):
        self.items = []

    def add(self, event):
        event.id = str(uuid4())
        event.created_at = datetime.now(timezone.utc)
        self.items.append(event)
        return event

    def list_by_run(self, run_id: str, limit: int = 200, offset: int = 0):
        return [x for x in self.items if str(x.run_id) == run_id][offset : offset + limit]

    def list_by_run_after(self, run_id: str, after_created_at, after_event_id, limit: int = 200):
        _ = (after_created_at, after_event_id)
        return [x for x in self.items if str(x.run_id) == run_id][:limit]


class _FakeTaskRunner:
    def enqueue(self, task_name: str, payload: dict):
        return f"task-{task_name}"


def _make_run():
    class R:
        pass

    run = R()
    run.id = "run-1"
    run.tenant_id = "tenant-1"
    run.project_id = "proj-1"
    run.state = "QUEUED"
    run.current_step = "PLANNER"
    run.attempt_count = 0
    run.retry_count = 0
    run.idempotency_key = "idem-1"
    run.checkpoint_json = {"completed_steps": [], "artifact_ids": {}}
    run.error_code = None
    run.error_message = None
    run.created_at = datetime.now(timezone.utc)
    run.updated_at = datetime.now(timezone.utc)
    run.deleted_at = None
    run.started_at = None
    run.finished_at = None
    return run


def test_orchestrator_execute_to_succeeded_and_events_present() -> None:
    run = _make_run()
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )

    out = service.execute("run-1", RunExecuteRequest())
    assert out.state == "SUCCEEDED"
    assert set(out.checkpoint_json["completed_steps"]) == {"PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"}

    events = service.list_events("run-1")
    assert len(events) >= 5


def test_human_review_decision_invalid_state_raises() -> None:
    run = _make_run()
    run.state = "SUCCEEDED"
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )

    try:
        service.apply_human_review("run-1", HumanReviewDecisionRequest(decision="APPROVE"))
    except Exception as exc:
        assert "not waiting for human review" in str(exc).lower()
    else:
        raise AssertionError("Expected exception")


def test_human_review_decisions_cover_all_paths() -> None:
    run = _make_run()
    run.state = "WAITING_HUMAN_REVIEW"
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )
    approved = service.apply_human_review("run-1", HumanReviewDecisionRequest(decision="APPROVE"))
    assert approved.state == "SUCCEEDED"

    run.state = "WAITING_HUMAN_REVIEW"
    rewritten = service.apply_human_review("run-1", HumanReviewDecisionRequest(decision="REQUEST_REWRITE"))
    assert rewritten.state == "RUNNING_WRITER"
    assert rewritten.current_step == "WRITER"

    run.state = "WAITING_HUMAN_REVIEW"
    rejected = service.apply_human_review("run-1", HumanReviewDecisionRequest(decision="REJECT", reason="manual reject"))
    assert rejected.state == "FAILED"
    assert run.error_code == "PW-RUN-HUMAN-REJECT"


def test_execute_invalid_resume_from_step_raises_validation() -> None:
    run = _make_run()
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )
    try:
        service.execute("run-1", RunExecuteRequest(resume_from_step="BAD_STEP"))
    except Exception as exc:
        assert "invalid resume_from_step" in str(exc).lower()
    else:
        raise AssertionError("Expected validation exception")


def test_list_events_after_cursor_path_is_supported() -> None:
    run = _make_run()
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )
    service.execute("run-1", RunExecuteRequest())
    events = service.list_events("run-1")
    assert events
    after_cursor = events[0].cursor
    replay = service.list_events("run-1", after_cursor=after_cursor)
    assert replay
