from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from plotweaver_api.schemas.run import HumanReviewDecisionRequest, RunExecuteRequest
from plotweaver_api.services.orchestrator_service import OrchestratorService


class _FakeSession:
    def __init__(self, chapter=None):
        self.chapter = chapter
        self.added_versions = []

    def flush(self):
        return None

    def refresh(self, _obj):
        return None

    def get(self, _model, _id):
        return self.chapter

    def scalar(self, _stmt):
        stmt_text = str(_stmt)
        if "storage_key" in stmt_text:
            return self.added_versions[-1] if self.added_versions else None
        if "max(" in stmt_text:
            return self.added_versions[-1].version_no if self.added_versions else None
        return None

    def add(self, obj):
        self.added_versions.append(obj)
        return obj


class _FakeRunRepo:
    def __init__(self, run, chapter=None):
        self._run = run
        self.session = _FakeSession(chapter=chapter)

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


class _FakeStorage:
    def __init__(self):
        self.writes = {}

    def put_text(self, key: str, content: str) -> str:
        self.writes[key] = content
        return key

    def get_text(self, key: str) -> str:
        return self.writes[key]


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
    run.target_chapter_id = "chapter-1"
    run.requirement_id = None
    return run


def _make_chapter():
    class C:
        pass

    chapter = C()
    chapter.id = "chapter-1"
    chapter.chapter_key = "chapter_1"
    chapter.kind = "NORMAL"
    chapter.title = "Chapter One"
    chapter.subtitle = None
    chapter.volume_id = None
    chapter.arc_id = None
    chapter.order_index = 1
    chapter.status = "GENERATED"
    chapter.summary = ""
    return chapter


def test_orchestrator_execute_to_succeeded_and_events_present() -> None:
    run = _make_run()
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )

    out = service.execute("run-1", RunExecuteRequest(auto_continue=True))
    assert out.state == "SUCCEEDED"
    assert set(out.checkpoint_json["completed_steps"]) == {"PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"}

    events = service.list_events("run-1")
    assert len(events) >= 5


def test_reviewer_suggestions_include_contract_check_lines() -> None:
    run = _make_run()
    artifact_repo = _FakeArtifactRepo()
    service = OrchestratorService(
        run_repo=_FakeRunRepo(run),
        artifact_repo=artifact_repo,
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
    )

    service.execute("run-1", RunExecuteRequest(auto_continue=True))
    review = next(item for item in artifact_repo.items if item.artifact_type == "REVIEW")
    suggestions = review.payload_json["revision_suggestions"]
    joined = " ".join(suggestions)
    assert "must_include" in joined
    assert "must_not_include" in joined
    assert "continuity_constraints" in joined


def test_writer_step_persists_chapter_version_and_storage_content() -> None:
    run = _make_run()
    chapter = _make_chapter()
    artifact_repo = _FakeArtifactRepo()
    storage = _FakeStorage()
    run_repo = _FakeRunRepo(run, chapter=chapter)

    service = OrchestratorService(
        run_repo=run_repo,
        artifact_repo=artifact_repo,
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
        storage=storage,
    )

    service.execute("run-1", RunExecuteRequest(auto_continue=True))

    assert storage.writes
    assert len(run_repo.session.added_versions) == 1
    version = run_repo.session.added_versions[0]
    assert version.chapter_id == chapter.id
    assert version.version_no == 1


def test_writer_persist_is_idempotent_for_same_run() -> None:
    run = _make_run()
    chapter = _make_chapter()
    run_repo = _FakeRunRepo(run, chapter=chapter)
    storage = _FakeStorage()
    service = OrchestratorService(
        run_repo=run_repo,
        artifact_repo=_FakeArtifactRepo(),
        event_repo=_FakeEventRepo(),
        task_runner=_FakeTaskRunner(),
        storage=storage,
    )

    chapter_meta = {
        "title": "T",
        "status": "GENERATED",
        "summary": "S",
    }
    service._persist_writer_output(run, chapter_meta, "v1")
    service._persist_writer_output(run, chapter_meta, "v2")

    assert len(run_repo.session.added_versions) == 1


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
    assert rewritten.state == "WAITING_USER_APPROVAL"
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
    service.execute("run-1", RunExecuteRequest(auto_continue=True))
    events = service.list_events("run-1")
    assert events
    after_cursor = events[0].cursor
    replay = service.list_events("run-1", after_cursor=after_cursor)
    assert replay
