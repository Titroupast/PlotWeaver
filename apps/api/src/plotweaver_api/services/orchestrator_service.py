from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from plotweaver_api.core.contracts import validate_artifact_payload
from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import Chapter, ChapterVersion, Run, RunArtifact, RunEvent
from plotweaver_api.db.settings import settings
from plotweaver_api.repositories.artifact_repo import ArtifactRepository
from plotweaver_api.repositories.run_event_repo import RunEventRepository
from plotweaver_api.repositories.run_repo import RunRepository
from plotweaver_api.schemas.run import HumanReviewDecisionRequest, RunEventResponse, RunExecuteRequest, RunResponse
from plotweaver_api.storage.interface import StorageClient
from plotweaver_api.storage.local_storage import LocalStorageClient
from plotweaver_api.tasks.interface import TaskRunner

MAX_RETRY = 3


@dataclass(frozen=True)
class StepSpec:
    name: str
    running_state: str
    artifact_type: str


@dataclass(frozen=True)
class StepExecutionResult:
    artifact_payload: dict[str, Any]
    chapter_text: str | None = None


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
        storage: StorageClient | None = None,
    ):
        self.run_repo = run_repo
        self.artifact_repo = artifact_repo
        self.event_repo = event_repo
        self.task_runner = task_runner
        self.storage = storage or LocalStorageClient(root_dir=settings.storage_local_root)

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

        requirement_ctx = self._load_requirement_context(run)
        step_context: dict[str, Any] = {"requirement": requirement_ctx}

        try:
            for step in STEPS[start_idx:]:
                run.current_step = step.name
                run.state = step.running_state
                self._emit(run, "STEP_STARTED", step=step.name)

                execution = self._execute_step(run, step.name, step_context)
                validated_payload = validate_artifact_payload(step.artifact_type, execution.artifact_payload)
                artifact = self._save_artifact(run, step.artifact_type, validated_payload)

                if step.name == "WRITER" and execution.chapter_text:
                    self._persist_writer_output(run, validated_payload, execution.chapter_text)
                    step_context["chapter_text"] = execution.chapter_text

                step_context[step.name] = validated_payload

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
            gate_failed = bool(gate_payload and not gate_payload.get("pass", gate_payload.get("passed", True)))
            gate_manual = bool(gate_payload and gate_payload.get("recommended_action") == "REVIEW_MANUALLY")
            if gate_payload and (gate_failed or gate_manual):
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

    def _execute_step(self, run: Run, step: str, ctx: dict[str, Any]) -> StepExecutionResult:
        requirement = dict(ctx.get("requirement") or {})

        if step == "PLANNER":
            chapter_goal = str(requirement.get("chapter_goal") or "推进当前章节主线并埋下下一章悬念")
            must_include = [str(x).strip() for x in (requirement.get("must_include") or []) if str(x).strip()]
            must_not_include = [str(x).strip() for x in (requirement.get("must_not_include") or []) if str(x).strip()]
            continuity = [str(x).strip() for x in (requirement.get("continuity_constraints") or []) if str(x).strip()]

            beats = must_include[:3] if must_include else ["承接上一章冲突", "推进关键抉择", "收束并抛出钩子"]
            conflict = must_not_include[0] if must_not_include else "目标推进与外部阻力升级"
            foreshadowing = continuity[:2] if continuity else ["保留关键伏笔并延后揭示"]

            return StepExecutionResult(
                artifact_payload={
                    "chapter_goal": chapter_goal,
                    "conflict": conflict,
                    "beats": beats,
                    "foreshadowing": foreshadowing,
                    "ending_hook": "在结尾抛出新的不确定性，驱动下一章",
                }
            )

        if step == "WRITER":
            outline = ctx.get("PLANNER") or self._find_artifact_payload(run, "OUTLINE") or {}
            target_chapter = self._get_target_chapter(run)
            now = datetime.now(timezone.utc).replace(microsecond=0)
            created_iso = now.isoformat().replace("+00:00", "Z")

            title = (target_chapter.title if target_chapter else "Generated Chapter") or "Generated Chapter"
            chapter_goal = str(outline.get("chapter_goal") or requirement.get("chapter_goal") or "继续推进剧情")
            beats = [str(x) for x in (outline.get("beats") or [])]
            chapter_text = self._compose_chapter_text(title=title, chapter_goal=chapter_goal, beats=beats)

            return StepExecutionResult(
                artifact_payload={
                    "chapter_id": target_chapter.chapter_key if target_chapter else f"run_{str(run.id)[:8]}",
                    "kind": (target_chapter.kind if target_chapter else "NORMAL") or "NORMAL",
                    "title": title,
                    "subtitle": target_chapter.subtitle if target_chapter else None,
                    "volume_id": target_chapter.volume_id if target_chapter else None,
                    "arc_id": target_chapter.arc_id if target_chapter else None,
                    "order_index": target_chapter.order_index if target_chapter else 1,
                    "status": "GENERATED",
                    "summary": chapter_text[:120],
                    "created_at": created_iso,
                    "updated_at": created_iso,
                },
                chapter_text=chapter_text,
            )

        if step == "REVIEWER":
            chapter_text = str(ctx.get("chapter_text") or "")
            if not chapter_text:
                chapter_text = self._read_latest_target_chapter_text(run)

            must_include = [str(x).strip() for x in (requirement.get("must_include") or []) if str(x).strip()]
            must_not_include = [str(x).strip() for x in (requirement.get("must_not_include") or []) if str(x).strip()]
            continuity = [str(x).strip() for x in (requirement.get("continuity_constraints") or []) if str(x).strip()]

            include_hit = sum(1 for item in must_include if item and item in chapter_text)
            include_score = 90 if not must_include else int(70 + min(30, (include_hit / max(1, len(must_include))) * 30))
            banned_hit = [item for item in must_not_include if item and item in chapter_text]
            consistency_penalty = min(20, len(banned_hit) * 10)

            character_score = max(0, min(100, include_score - consistency_penalty))
            world_score = max(0, min(100, include_score - (5 if not continuity else 0)))
            style_score = max(0, min(100, 88 - (5 if len(chapter_text) < 100 else 0)))

            suggestions = [
                f"must_include 检查：命中 {include_hit}/{len(must_include)}。",
                f"must_not_include 检查：违例 {len(banned_hit)} 项。",
                f"continuity_constraints 检查：约束条目 {len(continuity)}，建议人工复核关键连续性。",
            ]

            return StepExecutionResult(
                artifact_payload={
                    "character_consistency_score": character_score,
                    "world_consistency_score": world_score,
                    "style_match_score": style_score,
                    "repetition_issues": banned_hit,
                    "revision_suggestions": suggestions,
                }
            )

        if step == "MEMORY_CURATOR":
            review = ctx.get("REVIEWER") or self._find_artifact_payload(run, "REVIEW") or {}
            min_score = min(
                int(review.get("character_consistency_score", 0)),
                int(review.get("world_consistency_score", 0)),
                int(review.get("style_match_score", 0)),
            )
            issues = [str(x) for x in (review.get("repetition_issues") or []) if str(x).strip()]
            passed = min_score >= 80 and len(issues) <= 2
            return StepExecutionResult(
                artifact_payload={
                    "pass": passed,
                    "issues": issues,
                    "recommended_action": "AUTO_MERGE" if passed else "REVIEW_MANUALLY",
                }
            )

        raise ValidationError("Unsupported orchestration step", details={"step": step})

    def _persist_writer_output(self, run: Run, chapter_meta: dict[str, Any], chapter_text: str) -> None:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return

        target_chapter = self._get_target_chapter(run)
        if target_chapter is None:
            return

        same_run_stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == target_chapter.id)
            .where(ChapterVersion.storage_key.like(f"%/runs/{run.id}/%"))
            .where(ChapterVersion.deleted_at.is_(None))
            .order_by(ChapterVersion.version_no.desc())
            .limit(1)
        )
        same_run_version = session.scalar(same_run_stmt)

        content_hash = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
        byte_size = len(chapter_text.encode("utf-8"))

        if same_run_version is not None:
            self.storage.put_text(same_run_version.storage_key, chapter_text)
            same_run_version.content_sha256 = content_hash
            same_run_version.byte_size = byte_size
        else:
            max_ver_stmt = select(func.max(ChapterVersion.version_no)).where(ChapterVersion.chapter_id == target_chapter.id)
            max_ver = session.scalar(max_ver_stmt)
            version_no = int(max_ver or 0) + 1
            storage_key = f"projects/{run.project_id}/chapters/{target_chapter.id}/runs/{run.id}/v{version_no}.txt"
            self.storage.put_text(storage_key, chapter_text)

            version = ChapterVersion(
                tenant_id=run.tenant_id,
                chapter_id=target_chapter.id,
                version_no=version_no,
                source_type="GENERATED",
                storage_bucket=settings.storage_bucket,
                storage_key=storage_key,
                content_sha256=content_hash,
                byte_size=byte_size,
            )
            session.add(version)

        target_chapter.status = str(chapter_meta.get("status") or "GENERATED")
        target_chapter.summary = str(chapter_meta.get("summary") or chapter_text[:120])
        target_chapter.title = str(chapter_meta.get("title") or target_chapter.title)

    def _find_artifact_payload(self, run: Run, artifact_type: str) -> dict[str, Any] | None:
        for row in self.artifact_repo.list_by_run(str(run.id), limit=200, offset=0):
            if row.artifact_type == artifact_type:
                return row.payload_json
        return None

    def _get_target_chapter(self, run: Run) -> Chapter | None:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "get"):
            return None
        if not run.target_chapter_id:
            return None
        return session.get(Chapter, run.target_chapter_id)

    def _read_latest_target_chapter_text(self, run: Run) -> str:
        target = self._get_target_chapter(run)
        if target is None:
            return ""
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return ""

        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == target.id)
            .where(ChapterVersion.deleted_at.is_(None))
            .order_by(ChapterVersion.version_no.desc())
            .limit(1)
        )
        latest = session.scalar(stmt)
        if latest is None:
            return ""
        try:
            return self.storage.get_text(latest.storage_key)
        except Exception:
            return ""

    def _load_requirement_context(self, run: Run) -> dict[str, Any]:
        default_ctx = {
            "chapter_goal": "",
            "must_include": [],
            "must_not_include": [],
            "tone": "",
            "continuity_constraints": [],
            "target_length": 0,
            "optional_notes": "",
        }
        if not run.requirement_id:
            return default_ctx

        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "get"):
            return default_ctx

        try:
            from plotweaver_api.db.models import Requirement

            requirement = session.get(Requirement, run.requirement_id)
            if requirement is None or requirement.deleted_at is not None:
                return default_ctx
            payload = dict(requirement.payload_json or {})
            merged = dict(default_ctx)
            merged.update(payload)
            if not merged.get("chapter_goal"):
                merged["chapter_goal"] = requirement.chapter_goal or ""
            return merged
        except Exception:
            return default_ctx

    @staticmethod
    def _compose_chapter_text(title: str, chapter_goal: str, beats: list[str]) -> str:
        beat_lines = beats or ["承接冲突", "推进情节", "留下悬念"]
        body_parts = [
            f"{title}",
            "",
            f"本章目标：{chapter_goal}",
            "",
        ]
        for idx, beat in enumerate(beat_lines, start=1):
            body_parts.append(f"第{idx}段：{beat}。角色在压力下作出选择，推动情节向前。")
        body_parts.append("")
        body_parts.append("结尾：一个新的变量出现，迫使主角在下一章重新评估局势。")
        return "\n".join(body_parts).strip()

    def _save_artifact(self, run: Run, artifact_type: str, payload: dict[str, Any]) -> RunArtifact:
        existing = None
        for row in self.artifact_repo.list_by_run(str(run.id), limit=200, offset=0):
            if row.artifact_type == artifact_type and row.version_no == 1:
                existing = row
                break

        if existing is not None:
            existing.payload_json = payload
            existing.payload_hash = self._hash_payload(payload)
            self.artifact_repo.session.flush()
            self.artifact_repo.session.refresh(existing)
            return existing

        artifact = RunArtifact(
            tenant_id=run.tenant_id,
            run_id=run.id,
            artifact_type=artifact_type,
            version_no=1,
            payload_json=payload,
            payload_hash=self._hash_payload(payload),
        )
        return self.artifact_repo.add(artifact)

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        import json

        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    def _emit(self, run: Run, event_type: str, step: str | None = None, payload: dict[str, Any] | None = None) -> None:
        event_payload = {
            "step": step,
            "artifact_type": None,
            "artifact_id": None,
            "error": None,
        }
        if payload:
            event_payload.update(payload)
        evt = RunEvent(
            tenant_id=run.tenant_id,
            run_id=run.id,
            event_type=event_type,
            step=step,
            payload_json=event_payload,
        )
        self.event_repo.add(evt)

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
