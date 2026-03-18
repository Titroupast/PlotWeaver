from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from plotweaver_api.core.contracts import validate_artifact_payload
from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import Chapter, ChapterVersion, Character, Memory, MemoryDelta, MergeDecision, Run, RunArtifact, RunEvent
from plotweaver_api.db.settings import settings
from plotweaver_api.repositories.artifact_repo import ArtifactRepository
from plotweaver_api.repositories.run_event_repo import RunEventRepository
from plotweaver_api.repositories.run_repo import RunRepository
from plotweaver_api.schemas.run import HumanReviewDecisionRequest, RunEventResponse, RunExecuteRequest, RunResponse
from plotweaver_api.services.llm_prompts import load_prompt, render_prompt
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
    llm_used: bool = False
    llm_error: str | None = None
    llm_provider: str | None = None


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
        req = payload or RunExecuteRequest()

        if run.state == "WAITING_HUMAN_REVIEW":
            raise ValidationError("Run is waiting for human review", details={"run_id": run_id})
        if run.state in {"SUCCEEDED", "CANCELLED", "FAILED"}:
            return self._to_run_response(run)

        checkpoint = dict(run.checkpoint_json or {})
        start_step = req.resume_from_step or checkpoint.get("pending_step") or run.current_step or STEPS[0].name

        try:
            start_idx = next(i for i, s in enumerate(STEPS) if s.name == start_step)
        except StopIteration as exc:
            raise ValidationError("Invalid resume_from_step", details={"step": start_step}) from exc

        run.attempt_count = (run.attempt_count or 0) + 1
        run.started_at = run.started_at or datetime.now(timezone.utc)
        self._emit(run, "RUN_EXECUTION_STARTED", step=start_step, payload={"attempt": run.attempt_count})

        requirement_ctx = self._load_requirement_context(run)
        step_context: dict[str, Any] = {"requirement": requirement_ctx}

        try:
            idx = start_idx
            while idx < len(STEPS):
                step = STEPS[idx]
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

                if step.name == "MEMORY_CURATOR":
                    memory_result = self._persist_memory_pipeline(
                        run=run,
                        review_payload=step_context.get("REVIEWER") or {},
                        gate_payload=validated_payload,
                        chapter_text=str(step_context.get("chapter_text") or ""),
                    )
                    step_context["memory_pipeline"] = memory_result
                    # Keep MEMORY_GATE artifact consistent with memory pipeline policy.
                    if memory_result.get("enabled") and not memory_result.get("auto_merge", False):
                        if validated_payload.get("recommended_action") != "REVIEW_MANUALLY":
                            validated_payload["recommended_action"] = "REVIEW_MANUALLY"
                        validated_payload["pass"] = False
                        issues = validated_payload.get("issues")
                        if not isinstance(issues, list):
                            issues = []
                        risk = str(memory_result.get("risk_level") or "").upper()
                        marker = f"memory_pipeline risk={risk}, requires manual review"
                        if marker not in issues:
                            issues.append(marker)
                        validated_payload["issues"] = issues
                        artifact.payload_json = validated_payload
                        artifact.payload_hash = self._hash_payload(validated_payload)

                checkpoint = dict(run.checkpoint_json or {})
                completed = list(checkpoint.get("completed_steps", []))
                if step.name not in completed:
                    completed.append(step.name)
                artifact_ids = dict(checkpoint.get("artifact_ids", {}))
                artifact_ids[step.name] = str(artifact.id)
                checkpoint["completed_steps"] = completed
                checkpoint["artifact_ids"] = artifact_ids

                self._emit(
                    run,
                    "STEP_COMPLETED",
                    step=step.name,
                    payload={
                        "artifact_id": str(artifact.id),
                        "artifact_type": step.artifact_type,
                        "artifact_preview": validated_payload,
                        "chapter_text_preview": (execution.chapter_text[:500] if execution.chapter_text else None),
                        "llm_used": execution.llm_used,
                        "llm_error": execution.llm_error,
                        "llm_provider": execution.llm_provider,
                        "memory_pipeline": step_context.get("memory_pipeline") if step.name == "MEMORY_CURATOR" else None,
                    },
                )

                idx += 1
                if not req.auto_continue and idx < len(STEPS):
                    next_step = STEPS[idx].name
                    checkpoint["pending_step"] = next_step
                    run.checkpoint_json = checkpoint
                    run.current_step = next_step
                    run.state = "WAITING_USER_APPROVAL"
                    self._emit(
                        run,
                        "STEP_AWAITING_APPROVAL",
                        step=next_step,
                        payload={"from_step": step.name, "next_step": next_step},
                    )
                    break

                checkpoint.pop("pending_step", None)
                run.checkpoint_json = checkpoint

            if idx >= len(STEPS):
                gate_payload = self._find_gate_payload(run)
                gate_failed = bool(gate_payload and not gate_payload.get("pass", gate_payload.get("passed", True)))
                gate_manual = bool(gate_payload and gate_payload.get("recommended_action") == "REVIEW_MANUALLY")
                if gate_payload and (gate_failed or gate_manual):
                    run.state = "WAITING_HUMAN_REVIEW"
                    run.current_step = "MEMORY_CURATOR"
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
            run.state = "WAITING_USER_APPROVAL"
            run.current_step = "WRITER"
            checkpoint = dict(run.checkpoint_json or {})
            checkpoint["pending_step"] = "WRITER"
            run.checkpoint_json = checkpoint
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
        previous_chapter = self._read_previous_chapter_text(run)
        memory_bundle = self._load_memory_bundle(run, previous_chapter=previous_chapter, requirement=requirement)
        memory_context = memory_bundle["memory_context"]
        style_constraints = memory_bundle["style_constraints"]

        if step == "PLANNER":
            llm_payload, llm_error = self._planner_with_llm(
                requirement=requirement,
                previous_chapter=previous_chapter,
                memory_context=memory_context,
                style_constraints=style_constraints,
            )
            if llm_payload is not None:
                return StepExecutionResult(
                    artifact_payload=llm_payload,
                    llm_used=True,
                    llm_error=None,
                    llm_provider="ARK",
                )

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
                },
                llm_used=False,
                llm_error=llm_error,
                llm_provider="ARK",
            )

        if step == "WRITER":
            outline = ctx.get("PLANNER") or self._find_artifact_payload(run, "OUTLINE") or {}
            target_chapter = self._get_target_chapter(run)
            chapter_hint = self._resolve_target_chapter_hint(run, target_chapter)

            llm_result, llm_error = self._writer_with_llm(
                requirement=requirement,
                outline=outline,
                previous_chapter=previous_chapter,
                memory_context=memory_context,
                chapter_hint=chapter_hint,
            )
            if llm_result is not None:
                return llm_result

            now = datetime.now(timezone.utc).replace(microsecond=0)
            created_iso = now.isoformat().replace("+00:00", "Z")
            title = str(chapter_hint.get("title") or "Generated Chapter")
            chapter_goal = str(outline.get("chapter_goal") or requirement.get("chapter_goal") or "继续推进剧情")
            beats = [str(x) for x in (outline.get("beats") or [])]
            chapter_text = self._compose_chapter_text(title=title, chapter_goal=chapter_goal, beats=beats)

            return StepExecutionResult(
                artifact_payload={
                    "chapter_id": chapter_hint.get("chapter_id") or f"run_{str(run.id)[:8]}",
                    "kind": str(chapter_hint.get("kind") or "NORMAL"),
                    "title": title,
                    "subtitle": chapter_hint.get("subtitle"),
                    "volume_id": chapter_hint.get("volume_id"),
                    "arc_id": chapter_hint.get("arc_id"),
                    "order_index": int(chapter_hint.get("order_index") or 1),
                    "status": "GENERATED",
                    "summary": chapter_text[:120],
                    "created_at": created_iso,
                    "updated_at": created_iso,
                },
                chapter_text=chapter_text,
                llm_used=False,
                llm_error=llm_error,
                llm_provider="ARK",
            )

        if step == "REVIEWER":
            chapter_text = str(ctx.get("chapter_text") or "")
            if not chapter_text:
                chapter_text = self._read_latest_target_chapter_text(run)
            chapter_meta = ctx.get("WRITER") or self._find_artifact_payload(run, "CHAPTER_META") or {}

            llm_payload, llm_error = self._reviewer_with_llm(
                requirement=requirement,
                chapter_text=chapter_text,
                chapter_meta=chapter_meta,
                character_summary=memory_bundle["character_summary"],
                world_summary=memory_bundle["world_summary"],
            )
            if llm_payload is not None:
                return StepExecutionResult(
                    artifact_payload=llm_payload,
                    llm_used=True,
                    llm_error=None,
                    llm_provider="ARK",
                )

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
                },
                llm_used=False,
                llm_error=llm_error,
                llm_provider="ARK",
            )

        if step == "MEMORY_CURATOR":
            review = ctx.get("REVIEWER") or self._find_artifact_payload(run, "REVIEW") or {}
            chapter_text = str(ctx.get("chapter_text") or "")
            if not chapter_text:
                chapter_text = self._read_run_written_chapter_text(run)
            if not chapter_text:
                chapter_text = self._read_latest_target_chapter_text(run)
            llm_payload, llm_error = self._memory_gate_with_llm(
                review=review,
                chapter_text=chapter_text,
                main_memory=memory_bundle["main_memory"],
            )
            if llm_payload is not None:
                return StepExecutionResult(
                    artifact_payload=llm_payload,
                    llm_used=True,
                    llm_error=None,
                    llm_provider="ARK",
                )

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
                },
                llm_used=False,
                llm_error=llm_error,
                llm_provider="ARK",
            )

        raise ValidationError("Unsupported orchestration step", details={"step": step})

    def _persist_writer_output(self, run: Run, chapter_meta: dict[str, Any], chapter_text: str) -> None:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return

        target_chapter = self._ensure_target_chapter(run, chapter_meta)
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
        if session is None or not hasattr(session, "get") or not hasattr(session, "scalar"):
            return None
        base_chapter_id = getattr(run, "base_chapter_id", None)
        base = session.get(Chapter, base_chapter_id) if base_chapter_id else None
        if run.target_chapter_id:
            chapter = session.get(Chapter, run.target_chapter_id)
            if chapter is not None:
                # Guard against accidental self-targeting: continuation must not write back to base chapter.
                if base is not None and str(chapter.id) == str(base.id):
                    pass
                elif base is not None and int(chapter.order_index or 0) <= int(base.order_index or 0):
                    pass
                else:
                    return chapter

        if base is None:
            return None

        next_stmt = (
            select(Chapter)
            .where(Chapter.project_id == run.project_id)
            .where(Chapter.deleted_at.is_(None))
            .where(Chapter.order_index == (base.order_index + 1))
            .order_by(Chapter.created_at.asc())
            .limit(1)
        )
        inferred = session.scalar(next_stmt)
        if inferred is not None:
            run.target_chapter_id = inferred.id
            return inferred
        return None

    def _ensure_target_chapter(self, run: Run, chapter_meta: dict[str, Any] | None = None) -> Chapter | None:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "add"):
            return None

        base_chapter_id = getattr(run, "base_chapter_id", None)
        base = session.get(Chapter, base_chapter_id) if base_chapter_id else None
        existing = self._get_target_chapter(run)

        if existing is not None and base is not None:
            # Same order (or older) means it is not a real continuation target; rebuild to next chapter.
            if int(existing.order_index or 0) <= int(base.order_index or 0):
                existing = None

        if existing is not None:
            return existing

        if base is None:
            return None

        next_index = int(base.order_index or 0) + 1
        title = str((chapter_meta or {}).get("title") or f"第{next_index}章")
        chapter_key = str((chapter_meta or {}).get("chapter_id") or f"chapter_{next_index:03d}")
        new_chapter = Chapter(
            tenant_id=run.tenant_id,
            project_id=run.project_id,
            chapter_key=chapter_key,
            kind=str((chapter_meta or {}).get("kind") or base.kind or "NORMAL"),
            title=title,
            subtitle=(chapter_meta or {}).get("subtitle"),
            volume_id=(chapter_meta or {}).get("volume_id") or base.volume_id,
            arc_id=(chapter_meta or {}).get("arc_id") or base.arc_id,
            order_index=next_index,
            status=str((chapter_meta or {}).get("status") or "DRAFT"),
            summary=str((chapter_meta or {}).get("summary") or ""),
        )
        session.add(new_chapter)
        session.flush()
        run.target_chapter_id = new_chapter.id
        return new_chapter

    def _resolve_target_chapter_hint(self, run: Run, target_chapter: Chapter | None) -> dict[str, Any]:
        session = getattr(self.run_repo, "session", None)
        base_chapter_id = getattr(run, "base_chapter_id", None)
        base = session.get(Chapter, base_chapter_id) if session is not None and base_chapter_id else None

        if target_chapter is not None:
            target_index = int(target_chapter.order_index or 0)
            base_index = int(base.order_index or 0) if base is not None else 0
            # Safety correction: if target is not actually "next", synthesize next hint.
            if base is not None and target_index <= base_index:
                next_index = base_index + 1
                return {
                    "title": f"第{next_index}章",
                    "kind": (base.kind or "NORMAL"),
                    "order_index": next_index,
                    "chapter_id": f"chapter_{next_index:03d}",
                    "subtitle": None,
                    "volume_id": base.volume_id,
                    "arc_id": base.arc_id,
                }
                return chapter
            return {
                "title": target_chapter.title or "Generated Chapter",
                "kind": target_chapter.kind or "NORMAL",
                "order_index": target_chapter.order_index or 1,
                "chapter_id": target_chapter.chapter_key,
                "subtitle": target_chapter.subtitle,
                "volume_id": target_chapter.volume_id,
                "arc_id": target_chapter.arc_id,
            }

        next_index = int(base.order_index or 0) + 1 if base is not None else 1
        return {
            "title": f"第{next_index}章",
            "kind": (base.kind if base is not None else "NORMAL") or "NORMAL",
            "order_index": next_index,
            "chapter_id": f"chapter_{next_index:03d}",
            "subtitle": None,
            "volume_id": (base.volume_id if base is not None else None),
            "arc_id": (base.arc_id if base is not None else None),
        }

    def _read_latest_target_chapter_text(self, run: Run) -> str:
        target = self._get_target_chapter(run)
        if target is None:
            return ""
        return self._read_latest_chapter_text_by_id(str(target.id))

    def _read_run_written_chapter_text(self, run: Run) -> str:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return ""
        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.deleted_at.is_(None))
            .where(ChapterVersion.storage_key.like(f"%/runs/{run.id}/%"))
            .order_by(ChapterVersion.created_at.desc())
            .limit(1)
        )
        latest = session.scalar(stmt)
        if latest is None:
            return ""
        try:
            return self.storage.get_text(latest.storage_key)
        except Exception:
            return ""

    def _read_previous_chapter_text(self, run: Run) -> str:
        base_chapter_id = getattr(run, "base_chapter_id", None)
        if base_chapter_id:
            content = self._read_latest_chapter_text_by_id(str(base_chapter_id))
            if content:
                return content
        return self._read_latest_target_chapter_text(run)

    def _read_latest_chapter_text_by_id(self, chapter_id: str) -> str:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return ""

        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
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

    def _load_memory_bundle(self, run: Run, previous_chapter: str, requirement: dict[str, Any]) -> dict[str, str]:
        notes = str(requirement.get("optional_notes") or "").strip()
        style_constraints = self._format_style_constraints(requirement.get("tone"))
        keywords = self._extract_keywords(previous_chapter + "\n" + json.dumps(requirement, ensure_ascii=False))
        character_lines = self._load_memory_lines(run.project_id, "CHARACTERS", keywords, limit=8)
        if not character_lines:
            character_lines = self._load_character_lines(run.project_id, keywords, limit=8)
        world_lines = self._load_memory_lines(run.project_id, "WORLD_RULES", keywords, limit=8)
        story_lines = self._load_memory_lines(run.project_id, "STORY_SO_FAR", keywords, limit=8)

        context_sections: list[str] = []
        if character_lines:
            context_sections.append("[FACT] Characters\n" + "\n".join(f"- {line}" for line in character_lines))
        if world_lines:
            context_sections.append("[SUMMARY] World Rules\n" + "\n".join(f"- {line}" for line in world_lines))
        if story_lines:
            context_sections.append("[SUMMARY] Story So Far\n" + "\n".join(f"- {line}" for line in story_lines))
        if notes:
            context_sections.append("[NOTES]\n" + notes)

        main_memory_sections: list[str] = []
        if character_lines:
            main_memory_sections.append("人物设定\n" + "\n".join(character_lines))
        if world_lines:
            main_memory_sections.append("世界规则\n" + "\n".join(world_lines))
        if story_lines:
            main_memory_sections.append("前情提要\n" + "\n".join(story_lines))

        return {
            "memory_context": "\n\n".join(context_sections).strip(),
            "character_summary": "\n".join(character_lines).strip(),
            "world_summary": "\n".join(world_lines).strip(),
            "story_summary": "\n".join(story_lines).strip(),
            "style_constraints": style_constraints,
            "main_memory": "\n\n".join(main_memory_sections).strip(),
        }

    def _ensure_project_memory_summaries(self, run: Run, force: bool = False) -> bool:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar") or not hasattr(session, "add"):
            return False

        chapters = self._collect_project_chapters(run.project_id)
        if not chapters:
            return False

        chapter_corpus = self._build_chapter_corpus(chapters)
        if not chapter_corpus.strip():
            return False

        character_summary = self._summarize_characters_from_corpus(chapter_corpus, str(run.project_id))
        world_summary = self._summarize_world_from_corpus(chapter_corpus)
        story_summary = self._summarize_story_from_corpus(chapter_corpus)

        changed = False
        changed = self._upsert_memory_summary(run, "CHARACTERS", character_summary, force=force) or changed
        changed = self._upsert_memory_summary(run, "WORLD_RULES", world_summary, force=force) or changed
        changed = self._upsert_memory_summary(run, "STORY_SO_FAR", story_summary, force=force) or changed
        return changed

    def _collect_project_chapters(self, project_id: str) -> list[tuple[Chapter, ChapterVersion | None, str]]:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalars") or not hasattr(session, "scalar"):
            return []

        chapter_stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .where(Chapter.deleted_at.is_(None))
            .order_by(Chapter.order_index.asc(), Chapter.created_at.asc())
        )
        chapters = list(session.scalars(chapter_stmt).all())
        if not chapters:
            return []

        collected: list[tuple[Chapter, ChapterVersion | None, str]] = []
        for chapter in chapters:
            ver_stmt = (
                select(ChapterVersion)
                .where(ChapterVersion.chapter_id == chapter.id)
                .where(ChapterVersion.deleted_at.is_(None))
                .order_by(ChapterVersion.version_no.desc())
                .limit(1)
            )
            latest = session.scalar(ver_stmt)
            content = ""
            if latest is not None:
                try:
                    content = self.storage.get_text(latest.storage_key)
                except Exception:
                    content = ""
            collected.append((chapter, latest, content.strip()))
        return collected

    @staticmethod
    def _build_chapter_corpus(chapters: list[tuple[Chapter, ChapterVersion | None, str]]) -> str:
        parts: list[str] = []
        for chapter, _, content in chapters:
            title = str(chapter.title or "").strip() or f"Chapter-{chapter.order_index}"
            parts.append(f"## 第{chapter.order_index}章 {title}")
            parts.append(content or "（本章暂无正文）")
        return "\n\n".join(parts).strip()

    def _summarize_characters_from_corpus(self, chapter_corpus: str, project_id: str) -> dict[str, Any]:
        prompt = render_prompt("memory_characters.txt", all_chapters_text=chapter_corpus)
        payload, _ = self._call_llm_json(
            system_prompt="你是角色设定整理助手。请严格输出 JSON 对象。",
            user_prompt=prompt,
            temperature=0.2,
        )
        if payload and isinstance(payload.get("characters"), list):
            return payload
        return {"characters": self._fallback_character_cards(project_id)}

    def _summarize_world_from_corpus(self, chapter_corpus: str) -> dict[str, Any]:
        prompt = render_prompt("memory_world_rules.txt", all_chapters_text=chapter_corpus)
        text, _ = self._call_llm_text(
            system_prompt="你是世界观规则整理助手。仅输出简洁列表，不要解释。",
            user_prompt=prompt,
            temperature=0.2,
        )
        lines = self._parse_numbered_lines(text) if text else []
        if not lines:
            lines = self._fallback_world_rules(chapter_corpus)
        return {"rules": lines}

    def _summarize_story_from_corpus(self, chapter_corpus: str) -> dict[str, Any]:
        prompt = render_prompt("memory_story_so_far.txt", all_chapters_text=chapter_corpus)
        text, _ = self._call_llm_text(
            system_prompt="你是剧情摘要整理助手。仅输出已发生剧情的有序列表。",
            user_prompt=prompt,
            temperature=0.2,
        )
        lines = self._parse_numbered_lines(text) if text else []
        if not lines:
            lines = self._fallback_story_points(chapter_corpus)
        return {"milestones": lines}

    def _upsert_memory_summary(self, run: Run, memory_type: str, summary_json: dict[str, Any], force: bool = False) -> bool:
        session = getattr(self.run_repo, "session", None)
        stmt = (
            select(Memory)
            .where(Memory.project_id == run.project_id)
            .where(Memory.memory_type == memory_type)
            .where(Memory.deleted_at.is_(None))
            .order_by(Memory.version_no.desc(), Memory.updated_at.desc())
            .limit(1)
        )
        latest = session.scalar(stmt)
        latest_version = int(latest.version_no) if latest is not None else 0
        if latest is not None and not force:
            if self._hash_any(latest.summary_json) == self._hash_any(summary_json):
                return False

        memory = Memory(
            tenant_id=run.tenant_id,
            project_id=run.project_id,
            memory_type=memory_type,
            summary_json=summary_json,
            version_no=latest_version + 1,
            storage_bucket=None,
            storage_key=None,
        )
        session.add(memory)
        session.flush()
        return True

    def _load_character_lines(self, project_id: str, keywords: list[str], limit: int = 8) -> list[str]:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalars"):
            return []
        stmt = (
            select(Character)
            .where(Character.project_id == project_id)
            .where(Character.deleted_at.is_(None))
            .order_by(Character.updated_at.desc())
            .limit(50)
        )
        rows = list(session.scalars(stmt).all())
        if not rows:
            return []
        picked: list[str] = []
        for row in rows:
            aliases = [str(x).strip() for x in (row.aliases_json or []) if str(x).strip()][:3]
            alias_part = f"（别名：{', '.join(aliases)}）" if aliases else ""
            card_payload = row.card_json if isinstance(row.card_json, dict) else {}
            role = str(card_payload.get("role") or "").strip()
            role_part = f"，角色：{role}" if role else ""
            line = f"{row.display_name}（ID:{row.character_id}）{alias_part}{role_part}".strip()
            serialized = json.dumps(card_payload, ensure_ascii=False) + "|" + line
            if keywords and not any(token in serialized for token in keywords):
                continue
            picked.append(line)
            if len(picked) >= limit:
                break
        if picked:
            return picked
        fallback = [f"{row.display_name}（ID:{row.character_id}）" for row in rows[:limit]]
        return fallback

    def _load_memory_lines(self, project_id: str, memory_type: str, keywords: list[str], limit: int = 8) -> list[str]:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalar"):
            return []
        stmt = (
            select(Memory)
            .where(Memory.project_id == project_id)
            .where(Memory.memory_type == memory_type)
            .where(Memory.deleted_at.is_(None))
            .order_by(Memory.version_no.desc(), Memory.updated_at.desc())
            .limit(1)
        )
        memory_row = session.scalar(stmt)
        if memory_row is None or not hasattr(memory_row, "summary_json"):
            return []
        source_lines = self._to_lines(memory_row.summary_json)
        if not source_lines:
            return []
        if not keywords:
            return source_lines[:limit]
        picked: list[str] = []
        for line in source_lines:
            if any(token in line for token in keywords):
                picked.append(line)
            if len(picked) >= limit:
                break
        return picked if picked else source_lines[: min(limit, 5)]

    @staticmethod
    def _to_lines(summary_json: Any) -> list[str]:
        if summary_json is None:
            return []
        lines: list[str] = []
        if isinstance(summary_json, str):
            lines = [ln.strip() for ln in summary_json.splitlines() if ln.strip()]
        elif isinstance(summary_json, list):
            for item in summary_json:
                if isinstance(item, dict):
                    for k in ("display_name", "canonical_name", "role"):
                        val = str(item.get(k) or "").strip()
                        if val:
                            lines.append(val)
                            break
                else:
                    text = str(item).strip()
                    if text:
                        lines.append(text)
        elif isinstance(summary_json, dict):
            for key, value in summary_json.items():
                if key == "characters" and isinstance(value, list):
                    for character in value:
                        if not isinstance(character, dict):
                            continue
                        canonical = str(character.get("canonical_name") or "").strip()
                        display = str(character.get("display_name") or "").strip()
                        role = str(character.get("role") or "").strip()
                        aliases = character.get("aliases") if isinstance(character.get("aliases"), list) else []
                        alias_text = "、".join(str(a).strip() for a in aliases if str(a).strip())
                        name = display or canonical
                        if not name:
                            continue
                        role_part = f"（{role}）" if role else ""
                        alias_part = f" 别名:{alias_text}" if alias_text else ""
                        lines.append(f"{name}{role_part}{alias_part}".strip())
                    continue
                if isinstance(value, list):
                    for item in value:
                        text = str(item).strip()
                        if text:
                            lines.append(f"{key}: {text}")
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{key}: {text}")
        return lines

    def _fallback_character_cards(self, project_id: str) -> list[dict[str, Any]]:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "scalars"):
            return []
        stmt = (
            select(Character)
            .where(Character.project_id == project_id)
            .where(Character.deleted_at.is_(None))
            .order_by(Character.updated_at.desc())
            .limit(50)
        )
        rows = list(session.scalars(stmt).all())
        cards: list[dict[str, Any]] = []
        for row in rows:
            card = row.card_json if isinstance(row.card_json, dict) else {}
            aliases = [str(x).strip() for x in (row.aliases_json or []) if str(x).strip()]
            cards.append(
                {
                    "character_id": row.character_id,
                    "canonical_name": row.canonical_name,
                    "display_name": row.display_name,
                    "aliases": aliases,
                    "tags": card.get("tags", []),
                    "role": card.get("role", ""),
                    "age": card.get("age", 0) or 0,
                    "personality": card.get("personality", []),
                    "background": card.get("background", []),
                    "abilities": card.get("abilities", []),
                    "limitations": card.get("limitations", []),
                    "motivation": card.get("motivation", []),
                    "key_memories": card.get("key_memories", []),
                    "story_function": card.get("story_function", []),
                    "beliefs": card.get("beliefs", []),
                    "current_status": card.get("current_status", ""),
                    "relationships": card.get("relationships", []),
                    "identities": card.get("identities", []),
                    "ambiguity": card.get("ambiguity", []),
                    "merge_status": row.merge_status or "CONFIRMED",
                }
            )
            if len(cards) >= 20:
                break
        return cards

    @staticmethod
    def _parse_numbered_lines(text: str | None) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        for raw in text.splitlines():
            item = raw.strip()
            if not item:
                continue
            item = re.sub(r"^\d+\.\s*", "", item)
            item = re.sub(r"^-\s*", "", item)
            item = item.strip()
            if item:
                lines.append(item)
        return lines[:20]

    @staticmethod
    def _fallback_world_rules(chapter_corpus: str) -> list[str]:
        lines = [ln.strip() for ln in chapter_corpus.splitlines() if ln.strip()]
        candidates = [ln for ln in lines if any(key in ln for key in ["规则", "必须", "不能", "学院", "组织", "夜晚", "禁忌"])]
        if not candidates:
            candidates = lines[:8]
        return candidates[:12]

    @staticmethod
    def _fallback_story_points(chapter_corpus: str) -> list[str]:
        lines = [ln.strip() for ln in chapter_corpus.splitlines() if ln.strip() and not ln.startswith("##")]
        if not lines:
            return ["暂无可提取剧情摘要。"]
        return lines[:12]

    @staticmethod
    def _extract_keywords(text: str, limit: int = 10) -> list[str]:
        chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        word_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,20}", text)
        counts: dict[str, int] = {}
        for token in chinese_tokens + word_tokens:
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
        return [item[0] for item in ranked[:limit]]

    @staticmethod
    def _format_style_constraints(tone: Any) -> str:
        if isinstance(tone, dict):
            return json.dumps(tone, ensure_ascii=False, indent=2)
        if isinstance(tone, str):
            return tone.strip()
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

    def _call_llm_text(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> tuple[str | None, str | None]:
        if os.getenv("PYTEST_CURRENT_TEST"):
            return None, "LLM_DISABLED_IN_PYTEST"
        if not settings.ark_api_key or not settings.ark_model:
            return None, "MISSING_ARK_CONFIG"
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)
            resp = client.chat.completions.create(
                model=settings.ark_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            content = resp.choices[0].message.content
            if not content:
                return None, "EMPTY_LLM_RESPONSE"
            return content.strip(), None
        except Exception as exc:
            return None, f"LLM_CALL_FAILED: {exc}"

    def _call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_retry: int = 1,
    ) -> tuple[dict[str, Any] | None, str | None]:
        text, err = self._call_llm_text(system_prompt, user_prompt, temperature=temperature)
        if text is None:
            return None, err
        attempts = 1 + max_retry
        current_text = text
        for _ in range(attempts):
            parsed = self._extract_json_object(current_text)
            if parsed is not None:
                return parsed, None
            retry_text, retry_err = self._call_llm_text(
                system_prompt,
                "请只输出 JSON 对象，不要输出额外解释。",
                temperature=0,
            )
            current_text = retry_text or ""
            err = retry_err or err
        return None, err or "INVALID_JSON_LLM_RESPONSE"

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        raw = text.strip()
        candidates = [raw]
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(raw[start : end + 1])
        for item in candidates:
            try:
                data = json.loads(item)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        return None

    def _planner_with_llm(
        self,
        requirement: dict[str, Any],
        previous_chapter: str,
        memory_context: str,
        style_constraints: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        system_prompt = load_prompt("planner_system.txt")
        user_prompt = render_prompt(
            "planner_user.txt",
            previous_chapter=previous_chapter,
            requirement_json=json.dumps(requirement, ensure_ascii=False, indent=2),
            requirements=json.dumps(requirement, ensure_ascii=False, indent=2),
            memory_context=memory_context,
            style_constraints=style_constraints,
        )
        return self._call_llm_json(system_prompt, user_prompt)

    def _writer_with_llm(
        self,
        requirement: dict[str, Any],
        outline: dict[str, Any],
        previous_chapter: str,
        memory_context: str,
        chapter_hint: dict[str, Any],
    ) -> tuple[StepExecutionResult | None, str | None]:
        system_prompt = load_prompt("writer_system.txt")
        user_prompt = render_prompt(
            "writer_user.txt",
            requirement_json=json.dumps(requirement, ensure_ascii=False, indent=2),
            outline_json=json.dumps(outline, ensure_ascii=False, indent=2),
            chapter_hint_json=json.dumps(chapter_hint, ensure_ascii=False, indent=2),
            previous_chapter=previous_chapter,
            memory_context=memory_context,
        )
        payload, err = self._call_llm_json(system_prompt, user_prompt, temperature=0.7)
        if payload is None:
            return None, err
        chapter_meta = payload.get("chapter_meta") if isinstance(payload.get("chapter_meta"), dict) else {}
        chapter_text = str(payload.get("chapter_text") or "").strip()
        if not chapter_text:
            return None, "EMPTY_CHAPTER_TEXT"
        min_len = self._resolve_min_length(requirement)
        if len(chapter_text) < min_len:
            strengthen_prompt = (
                f"{user_prompt}\n\n"
                f"[硬性要求补充]\n"
                f"- chapter_text 字数不得少于 {min_len} 字。\n"
                f"- 不得用提纲替代正文。\n"
                f"- 必须延续上一章并推进到下一章目标。"
            )
            retry_payload, retry_err = self._call_llm_json(system_prompt, strengthen_prompt, temperature=0.8)
            if retry_payload is not None:
                retry_text = str(retry_payload.get("chapter_text") or "").strip()
                if retry_text and len(retry_text) >= min_len:
                    payload = retry_payload
                    chapter_text = retry_text
                elif retry_err:
                    err = retry_err
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        chapter_meta.setdefault("chapter_id", chapter_hint["chapter_id"] or "chapter_auto")
        chapter_meta.setdefault("kind", chapter_hint["kind"] or "NORMAL")
        chapter_meta.setdefault("title", chapter_hint["title"] or "Generated Chapter")
        chapter_meta.setdefault("subtitle", None)
        chapter_meta.setdefault("volume_id", None)
        chapter_meta.setdefault("arc_id", None)
        chapter_meta.setdefault("order_index", chapter_hint["order_index"] or 1)
        chapter_meta.setdefault("status", "GENERATED")
        chapter_meta.setdefault("summary", chapter_text[:120])
        chapter_meta.setdefault("created_at", now)
        chapter_meta.setdefault("updated_at", now)
        return (
            StepExecutionResult(
                artifact_payload=chapter_meta,
                chapter_text=chapter_text,
                llm_used=True,
                llm_error=None,
                llm_provider="ARK",
            ),
            None,
        )

    @staticmethod
    def _resolve_min_length(requirement: dict[str, Any]) -> int:
        target_length = requirement.get("target_length")
        if isinstance(target_length, dict):
            try:
                min_len = int(target_length.get("min") or 0)
                if min_len > 0:
                    return min_len
            except Exception:
                pass
        return 1800

    def _reviewer_with_llm(
        self,
        requirement: dict[str, Any],
        chapter_text: str,
        chapter_meta: dict[str, Any],
        character_summary: str,
        world_summary: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        system_prompt = load_prompt("reviewer_system.txt")
        user_prompt = render_prompt(
            "reviewer_user.txt",
            requirement_json=json.dumps(requirement, ensure_ascii=False, indent=2),
            chapter_text=chapter_text,
            chapter_meta_json=json.dumps(chapter_meta, ensure_ascii=False, indent=2),
            character_summary=character_summary,
            world_summary=world_summary,
        )
        return self._call_llm_json(system_prompt, user_prompt)

    def _memory_gate_with_llm(
        self,
        review: dict[str, Any],
        chapter_text: str,
        main_memory: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        system_prompt = load_prompt("memory_curator_system.txt")
        user_prompt = render_prompt(
            "memory_curator_user.txt",
            review_json=json.dumps(review, ensure_ascii=False, indent=2),
            chapter_text=chapter_text,
            main_memory=main_memory,
        )
        return self._call_llm_json(system_prompt, user_prompt)

    def _persist_memory_pipeline(
        self,
        run: Run,
        review_payload: dict[str, Any],
        gate_payload: dict[str, Any],
        chapter_text: str,
    ) -> dict[str, Any]:
        session = getattr(self.run_repo, "session", None)
        if session is None or not hasattr(session, "add") or not hasattr(session, "execute"):
            return {"enabled": False, "reason": "NO_DB_SESSION"}

        delta_payloads = self._build_memory_delta_payloads(chapter_text=chapter_text, review_payload=review_payload)
        _ = gate_payload
        risk_level = self._evaluate_memory_risk(review_payload=review_payload, chapter_text=chapter_text)
        # Policy: memory merge must always be manually reviewed.
        auto_merge = False

        delta_rows: list[MemoryDelta] = []
        merge_ids: list[str] = []

        for delta_type, payload in delta_payloads.items():
            row = self._upsert_memory_delta(
                run=run,
                delta_type=delta_type,
                payload=payload,
                gate_status="PENDING_REVIEW",
                risk_level=risk_level,
            )
            delta_rows.append(row)
            decision = MergeDecision(
                tenant_id=run.tenant_id,
                project_id=run.project_id,
                run_id=run.id,
                delta_id=row.id,
                decision_type="PENDING_REVIEW",
                payload_json={
                    "delta_type": delta_type,
                    "risk_level": risk_level,
                },
                reason="manual review required",
                created_by=None,
            )
            session.add(decision)
            session.flush()
            merge_ids.append(self._safe_entity_id(decision, prefix="merge"))

        return {
            "enabled": True,
            "auto_merge": auto_merge,
            "risk_level": risk_level,
            "delta_ids": [self._safe_entity_id(row, prefix="delta") for row in delta_rows],
            "merge_decision_ids": merge_ids,
        }

    def _upsert_memory_delta(
        self,
        run: Run,
        delta_type: str,
        payload: dict[str, Any],
        gate_status: str,
        risk_level: str,
    ) -> MemoryDelta:
        session = getattr(self.run_repo, "session", None)
        existing_stmt = (
            select(MemoryDelta)
            .where(MemoryDelta.run_id == run.id)
            .where(MemoryDelta.delta_type == delta_type)
            .where(MemoryDelta.deleted_at.is_(None))
            .order_by(MemoryDelta.created_at.desc())
            .limit(1)
        )
        existing = session.scalar(existing_stmt)
        if existing is not None:
            existing.payload_json = payload
            existing.gate_status = gate_status
            existing.risk_level = risk_level
            session.flush()
            session.refresh(existing)
            return existing

        row = MemoryDelta(
            tenant_id=run.tenant_id,
            run_id=run.id,
            project_id=run.project_id,
            delta_type=delta_type,
            payload_json=payload,
            gate_status=gate_status,
            risk_level=risk_level,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        if not getattr(row, "id", None):
            row.id = f"delta-{run.id}-{delta_type}"
        return row

    def _apply_memory_delta_to_main(self, run: Run, delta_type: str, payload: dict[str, Any]) -> None:
        session = getattr(self.run_repo, "session", None)
        latest_stmt = (
            select(Memory)
            .where(Memory.project_id == run.project_id)
            .where(Memory.memory_type == delta_type)
            .where(Memory.deleted_at.is_(None))
            .order_by(Memory.version_no.desc(), Memory.updated_at.desc())
            .limit(1)
        )
        latest = session.scalar(latest_stmt)
        latest_version = int(latest.version_no) if latest is not None else 0
        merged_summary = self._merge_memory_summary(latest.summary_json if latest is not None else None, payload)

        memory = Memory(
            tenant_id=run.tenant_id,
            project_id=run.project_id,
            memory_type=delta_type,
            summary_json=merged_summary,
            version_no=latest_version + 1,
            storage_bucket=None,
            storage_key=None,
        )
        session.add(memory)

    @staticmethod
    def _merge_memory_summary(base_summary: Any, delta_payload: dict[str, Any]) -> list[str]:
        base_lines = OrchestratorService._extract_lines(base_summary)
        delta_lines = OrchestratorService._extract_lines(delta_payload)
        seen = {line for line in base_lines if line}
        merged = [line for line in base_lines if line]
        for line in delta_lines:
            if line and line not in seen:
                merged.append(line)
                seen.add(line)
        return merged[:120]

    @staticmethod
    def _extract_lines(value: Any) -> list[str]:
        lines: list[str] = []
        if value is None:
            return lines
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, list):
                    for nested in item:
                        text = str(nested).strip()
                        if text:
                            lines.append(text)
                else:
                    text = str(item).strip()
                    if text:
                        lines.append(f"{key}: {text}")
        return lines

    def _build_memory_delta_payloads(self, chapter_text: str, review_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        chapter_lines = [line.strip() for line in chapter_text.splitlines() if line.strip()]
        sample_lines = chapter_lines[:8]
        empty_reason = "章节内容为空，未提取到前情增量"
        if not chapter_lines:
            empty_reason = "章节正文读取失败：未找到本次 run 生成的正文版本"

        repetition = [str(x).strip() for x in (review_payload.get("repetition_issues") or []) if str(x).strip()]
        suggestions = [str(x).strip() for x in (review_payload.get("revision_suggestions") or []) if str(x).strip()]

        character_delta = {
            "characters": sample_lines[:4] or ["主角行为与关系无新增变化"],
            "review_signals": suggestions[:3],
        }
        world_delta = {
            "rules": sample_lines[2:6] or ["无新增世界规则"],
            "review_signals": repetition[:3],
        }
        story_delta = {
            "milestones": sample_lines[:6] or [empty_reason],
        }
        return {
            "CHARACTERS": character_delta,
            "WORLD_RULES": world_delta,
            "STORY_SO_FAR": story_delta,
        }

    @staticmethod
    def _evaluate_memory_risk(review_payload: dict[str, Any], chapter_text: str) -> str:
        low_bound = min(
            int(review_payload.get("character_consistency_score", 0)),
            int(review_payload.get("world_consistency_score", 0)),
            int(review_payload.get("style_match_score", 0)),
        )
        issues = [str(x).strip() for x in (review_payload.get("repetition_issues") or []) if str(x).strip()]
        high_risk_keywords = ["设定反转", "时间线冲突", "同名角色", "身份冲突", "世界规则冲突"]
        has_high_keyword = any(keyword in chapter_text for keyword in high_risk_keywords)

        if low_bound < 75 or len(issues) >= 3 or has_high_keyword:
            return "HIGH"
        if low_bound < 85 or len(issues) > 0:
            return "MEDIUM"
        return "LOW"
    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_any(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_entity_id(entity: Any, prefix: str) -> str:
        value = getattr(entity, "id", None)
        if value:
            return str(value)
        return f"{prefix}-unknown"

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


















