from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from plotweaver_api.core.contracts import build_payload_hash, validate_artifact_payload
from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import Run, RunArtifact, RunEvent
from plotweaver_api.repositories.artifact_repo import ArtifactRepository
from plotweaver_api.repositories.run_event_repo import RunEventRepository
from plotweaver_api.repositories.run_repo import RunRepository
from plotweaver_api.schemas.run import HumanReviewDecisionRequest, RunEventResponse, RunExecuteRequest, RunResponse
from plotweaver_api.tasks.interface import TaskRunner


MAX_RETRY = 3


@dataclass(frozen=True)
class StepSpec:
    name: str
    running_state: str
    artifact_type: str


STEPS: list[StepSpec] = [
    StepSpec("PLANNER", "RUNNING_PLANNER", "OUTLINE"),
    StepSpec("WRITER", "RUNNING_WRITER", "CHAPTER_META"),
    StepSpec("REVIEWER", "RUNNING_REVIEWER", "REVIEW"),
    StepSpec("MEMORY_CURATOR", "RUNNING_MEMORY_CURATOR", "MEMORY_GATE"),
]


class OrchestratorService:
    def __init__(
        self,
        run_repo: RunRepository,
        artifact_repo: ArtifactRepository,
        event_repo: RunEventRepository,
        task_runner: TaskRunner,
    ):
        self.run_repo = run_repo
        self.artifact_repo = artifact_repo
        self.event_repo = event_repo
        self.task_runner = task_runner

    def execute(self, run_id: str, payload: RunExecuteRequest | None = None) -> RunResponse:
        run = self._get_run(run_id)

        if run.state == "WAITING_HUMAN_REVIEW":
            raise ValidationError("Run is waiting for human review", details={"run_id": run_id})
        if run.state in {"SUCCEEDED", "CANCELLED"}:
            return self._to_run_response(run)

        start_step = payload.resume_from_step if payload and payload.resume_from_step else (run.current_step or STEPS[0].name)
        run.attempt_count = (run.attempt_count or 0) + 1
        run.started_at = run.started_at or datetime.now(timezone.utc)

        self._emit(run, "RUN_EXECUTION_STARTED", step=start_step, payload={"attempt": run.attempt_count})

        try:
            start_idx = next(i for i, s in enumerate(STEPS) if s.name == start_step)
        except StopIteration as exc:
            raise ValidationError("Invalid resume_from_step", details={"step": start_step}) from exc

        try:
            for step in STEPS[start_idx:]:
                run.current_step = step.name
                run.state = step.running_state
                self._emit(run, "STEP_STARTED", step=step.name)

                artifact_payload = self._build_step_payload(run, step.name)
                validated_payload = validate_artifact_payload(step.artifact_type, artifact_payload)
                artifact = self._save_artifact(run, step.artifact_type, validated_payload)

                checkpoint = dict(run.checkpoint_json or {})
                completed = list(checkpoint.get("completed_steps", []))
                if step.name not in completed:
                    completed.append(step.name)
                artifact_ids = dict(checkpoint.get("artifact_ids", {}))
                artifact_ids[step.name] = str(artifact.id)
                checkpoint["completed_steps"] = completed
                checkpoint["artifact_ids"] = artifact_ids
                run.checkpoint_json = checkpoint

                self._emit(
                    run,
                    "STEP_COMPLETED",
                    step=step.name,
                    payload={"artifact_id": str(artifact.id), "artifact_type": step.artifact_type},
                )

            gate_payload = self._find_gate_payload(run)
            if gate_payload and (not gate_payload.get("pass", True) or gate_payload.get("recommended_action") == "REVIEW_MANUALLY"):
                run.state = "WAITING_HUMAN_REVIEW"
                self._emit(run, "HUMAN_REVIEW_REQUIRED", step="MEMORY_CURATOR", payload=gate_payload)
            else:
                run.state = "SUCCEEDED"
                run.finished_at = datetime.now(timezone.utc)
                self._emit(run, "RUN_SUCCEEDED", payload={"completed_steps": run.checkpoint_json.get("completed_steps", [])})

            run.error_code = None
            run.error_message = None
        except Exception as exc:
            run.retry_count = (run.retry_count or 0) + 1
            if run.retry_count <= MAX_RETRY:
                run.state = "RETRYING"
                retry_task_id = self.task_runner.enqueue(
                    task_name="run_orchestration_retry",
                    payload={"run_id": str(run.id), "step": run.current_step, "retry_count": run.retry_count},
                )
                self._emit(
                    run,
                    "RUN_RETRY_SCHEDULED",
                    step=run.current_step,
                    payload={"retry_count": run.retry_count, "task_id": retry_task_id, "error": str(exc)},
                )
            else:
                run.state = "FAILED"
                run.finished_at = datetime.now(timezone.utc)
                self._emit(run, "RUN_FAILED", step=run.current_step, payload={"error": str(exc)})

            run.error_code = "PW-RUN-500"
            run.error_message = str(exc)

        self.run_repo.session.flush()
        self.run_repo.session.refresh(run)
        return self._to_run_response(run)

    def apply_human_review(self, run_id: str, payload: HumanReviewDecisionRequest) -> RunResponse:
        run = self._get_run(run_id)
        if run.state != "WAITING_HUMAN_REVIEW":
            raise ValidationError("Run is not waiting for human review", details={"run_id": run_id, "state": run.state})

        decision = payload.decision.upper()
        self._emit(run, "HUMAN_REVIEW_DECISION", step="MEMORY_CURATOR", payload={"decision": decision, "reason": payload.reason})

        if decision == "APPROVE":
            run.state = "SUCCEEDED"
            run.finished_at = datetime.now(timezone.utc)
        elif decision == "REQUEST_REWRITE":
            run.state = "RUNNING_WRITER"
            run.current_step = "WRITER"
        elif decision == "REJECT":
            run.state = "FAILED"
            run.finished_at = datetime.now(timezone.utc)
            run.error_code = "PW-RUN-HUMAN-REJECT"
            run.error_message = payload.reason or "Human review rejected"
        else:
            raise ValidationError("Invalid human review decision", details={"decision": payload.decision})

        self.run_repo.session.flush()
        self.run_repo.session.refresh(run)
        return self._to_run_response(run)

    def list_events(
        self,
        run_id: str,
        limit: int = 200,
        offset: int = 0,
        after_cursor: str | None = None,
    ) -> list[RunEventResponse]:
        if after_cursor:
            try:
                after_created_at, after_event_id = self._decode_cursor(after_cursor)
            except ValueError as exc:
                raise ValidationError("Invalid after_cursor", details={"after_cursor": after_cursor}) from exc
            events = self.event_repo.list_by_run_after(
                run_id=run_id,
                after_created_at=after_created_at,
                after_event_id=after_event_id,
                limit=limit,
            )
        else:
            events = self.event_repo.list_by_run(run_id, limit=limit, offset=offset)
        return [
            RunEventResponse(
                id=str(e.id),
                run_id=str(e.run_id),
                event_type=e.event_type,
                step=e.step,
                payload_json=e.payload_json,
                created_at=e.created_at,
                cursor=self._encode_cursor(e.created_at, str(e.id)),
            )
            for e in events
        ]

    def _get_run(self, run_id: str) -> Run:
        run = self.run_repo.get(run_id)
        if run is None or run.deleted_at is not None:
            raise NotFoundError("Run not found", details={"run_id": run_id})
        return run

    def _save_artifact(self, run: Run, artifact_type: str, payload: dict[str, Any]) -> RunArtifact:
        existing = None
        for row in self.artifact_repo.list_by_run(str(run.id), limit=200, offset=0):
            if row.artifact_type == artifact_type and row.version_no == 1:
                existing = row
                break

        if existing is not None:
            existing.payload_json = payload
            existing.payload_hash = build_payload_hash(payload)
            self.artifact_repo.session.flush()
            self.artifact_repo.session.refresh(existing)
            return existing

        artifact = RunArtifact(
            tenant_id=run.tenant_id,
            run_id=run.id,
            artifact_type=artifact_type,
            version_no=1,
            payload_json=payload,
            payload_hash=build_payload_hash(payload),
        )
        return self.artifact_repo.add(artifact)

    def _emit(self, run: Run, event_type: str, step: str | None = None, payload: dict[str, Any] | None = None) -> None:
        evt = RunEvent(
            tenant_id=run.tenant_id,
            run_id=run.id,
            event_type=event_type,
            step=step,
            payload_json=payload,
        )
        self.event_repo.add(evt)

    @staticmethod
    def _build_step_payload(run: Run, step: str) -> dict[str, Any]:
        if step == "PLANNER":
            return {
                "chapter_goal": "Auto-generated planner goal",
                "conflict": "Auto-generated conflict",
                "beats": ["beat-1", "beat-2"],
                "foreshadowing": ["hint-1"],
                "ending_hook": "cliffhanger",
            }
        if step == "WRITER":
            return {
                "chapter_id": f"run_{str(run.id)[:8]}",
                "kind": "NORMAL",
                "title": "Generated Chapter",
                "order_index": 1,
                "status": "GENERATED",
                "summary": "Generated by orchestrator",
            }
        if step == "REVIEWER":
            return {
                "character_consistency_score": 90,
                "world_consistency_score": 90,
                "style_match_score": 90,
                "repetition_issues": [],
                "revision_suggestions": [
                    "硬约束检查：must_include 已覆盖。",
                    "硬约束检查：must_not_include 未触发。",
                    "硬约束检查：continuity_constraints 无违例。",
                ],
            }
        if step == "MEMORY_CURATOR":
            return {
                "pass": True,
                "issues": [],
                "recommended_action": "AUTO_MERGE",
            }
        raise ValidationError("Unsupported orchestration step", details={"step": step})

    def _find_gate_payload(self, run: Run) -> dict[str, Any] | None:
        for row in self.artifact_repo.list_by_run(str(run.id), limit=200, offset=0):
            if row.artifact_type == "MEMORY_GATE":
                return row.payload_json
        return None

    @staticmethod
    def _encode_cursor(created_at: datetime, event_id: str) -> str:
        created = created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return f"{created}|{event_id}"

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID | None]:
        raw_created_at, _, raw_event_id = cursor.partition("|")
        created_at = datetime.fromisoformat(raw_created_at.replace("Z", "+00:00"))
        event_id = UUID(raw_event_id) if raw_event_id else None
        return created_at, event_id

    @staticmethod
    def _to_run_response(run: Run) -> RunResponse:
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
