from __future__ import annotations

from datetime import datetime, timezone

from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import Character, Memory, MemoryDelta, MergeDecision
from plotweaver_api.repositories.character_repo import CharacterRepository
from plotweaver_api.repositories.memory_delta_repo import MemoryDeltaRepository
from plotweaver_api.repositories.memory_repo import MemoryRepository
from plotweaver_api.repositories.merge_decision_repo import MergeDecisionRepository
from plotweaver_api.schemas.memory import (
    CharacterResponse,
    MemoryDeltaDecisionRequest,
    MemoryDeltaDecisionResponse,
    MemoryDeltaResponse,
    MemoryHistoryItem,
    MemorySnapshotItem,
    MemorySnapshotResponse,
    MergeDecisionResponse,
)


class MemoryService:
    def __init__(
        self,
        character_repo: CharacterRepository,
        memory_repo: MemoryRepository,
        delta_repo: MemoryDeltaRepository,
        decision_repo: MergeDecisionRepository,
    ):
        self.character_repo = character_repo
        self.memory_repo = memory_repo
        self.delta_repo = delta_repo
        self.decision_repo = decision_repo

    def list_characters(self, project_id: str, limit: int = 100, offset: int = 0) -> list[CharacterResponse]:
        return [self._to_character_response(row) for row in self.character_repo.list_by_project(project_id, limit, offset)]

    def list_memory_deltas(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[MemoryDeltaResponse]:
        if status:
            rows = self.delta_repo.list_by_project_status(project_id, status.upper(), limit, offset)
        else:
            rows = self.delta_repo.list_by_project(project_id, limit, offset)
        return [self._to_delta_response(row) for row in rows]

    def list_merge_decisions(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MergeDecisionResponse]:
        return [self._to_decision_response(row) for row in self.decision_repo.list_by_project(project_id, limit, offset)]

    def get_snapshots(self, project_id: str) -> MemorySnapshotResponse:
        rows = self.memory_repo.list_latest_by_project(project_id)
        return MemorySnapshotResponse(
            project_id=project_id,
            snapshots=[
                MemorySnapshotItem(
                    memory_type=row.memory_type,
                    version_no=row.version_no,
                    summary_json=row.summary_json,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
        )

    def list_history(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MemoryHistoryItem]:
        rows = self.memory_repo.list_history(project_id, limit=limit, offset=offset)
        return [
            MemoryHistoryItem(
                id=str(row.id),
                memory_type=row.memory_type,
                version_no=row.version_no,
                summary_json=row.summary_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def decide_delta(
        self,
        project_id: str,
        delta_id: str,
        payload: MemoryDeltaDecisionRequest,
        user_id: str | None,
    ) -> MemoryDeltaDecisionResponse:
        delta = self.delta_repo.get(delta_id)
        if delta is None or delta.deleted_at is not None or str(delta.project_id) != project_id:
            raise NotFoundError("Memory delta not found", details={"project_id": project_id, "delta_id": delta_id})

        if delta.gate_status in {"MERGED", "REJECTED"}:
            recent = self.decision_repo.list_by_delta(delta_id, limit=1, offset=0)
            return MemoryDeltaDecisionResponse(
                delta=self._to_delta_response(delta),
                merge_decision=self._to_decision_response(recent[0]) if recent else None,
            )

        decision = payload.decision.upper()
        if decision not in {"MERGE", "REJECT"}:
            raise ValidationError("Unsupported memory decision", details={"decision": payload.decision})

        merge_decision = None
        now = datetime.now(timezone.utc)

        if decision == "MERGE":
            self._apply_delta_to_memory(delta)
            delta.gate_status = "MERGED"
            delta.applied_at = now
            delta.applied_by = user_id
            merge_decision = self.decision_repo.add(
                MergeDecision(
                    tenant_id=delta.tenant_id,
                    project_id=delta.project_id,
                    run_id=delta.run_id,
                    delta_id=delta.id,
                    decision_type="MERGE",
                    payload_json=delta.payload_json,
                    reason=payload.reason or "manual merge",
                    created_by=user_id,
                )
            )
        else:
            delta.gate_status = "REJECTED"
            delta.applied_at = now
            delta.applied_by = user_id
            merge_decision = self.decision_repo.add(
                MergeDecision(
                    tenant_id=delta.tenant_id,
                    project_id=delta.project_id,
                    run_id=delta.run_id,
                    delta_id=delta.id,
                    decision_type="REJECT",
                    payload_json=delta.payload_json,
                    reason=payload.reason or "manual reject",
                    created_by=user_id,
                )
            )

        self.delta_repo.session.flush()
        self.delta_repo.session.refresh(delta)
        return MemoryDeltaDecisionResponse(
            delta=self._to_delta_response(delta),
            merge_decision=self._to_decision_response(merge_decision) if merge_decision else None,
        )

    def _apply_delta_to_memory(self, delta: MemoryDelta) -> None:
        latest = self.memory_repo.get_latest_by_type(str(delta.project_id), delta.delta_type)
        latest_version = int(latest.version_no) if latest else 0
        merged_summary = self._merge_summary(latest.summary_json if latest else None, delta.payload_json)
        memory = Memory(
            tenant_id=delta.tenant_id,
            project_id=delta.project_id,
            memory_type=delta.delta_type,
            summary_json=merged_summary,
            version_no=latest_version + 1,
        )
        self.memory_repo.add(memory)

    @staticmethod
    def _merge_summary(base: dict | list | None, delta_payload: dict) -> list[str]:
        base_lines: list[str] = []
        if isinstance(base, list):
            base_lines = [str(item).strip() for item in base if str(item).strip()]
        elif isinstance(base, dict):
            for value in base.values():
                if isinstance(value, list):
                    base_lines.extend(str(item).strip() for item in value if str(item).strip())
                elif value:
                    base_lines.append(str(value).strip())

        delta_lines: list[str] = []
        for value in delta_payload.values():
            if isinstance(value, list):
                delta_lines.extend(str(item).strip() for item in value if str(item).strip())
            elif value:
                delta_lines.append(str(value).strip())

        seen = {line for line in base_lines if line}
        merged = [line for line in base_lines if line]
        for line in delta_lines:
            if line and line not in seen:
                merged.append(line)
                seen.add(line)
        return merged[:100]

    @staticmethod
    def _to_character_response(row: Character) -> CharacterResponse:
        return CharacterResponse(
            id=str(row.id),
            project_id=str(row.project_id),
            character_id=row.character_id,
            canonical_name=row.canonical_name,
            display_name=row.display_name,
            aliases_json=row.aliases_json,
            merge_status=row.merge_status,
            card_json=row.card_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_delta_response(row: MemoryDelta) -> MemoryDeltaResponse:
        return MemoryDeltaResponse(
            id=str(row.id),
            run_id=str(row.run_id),
            project_id=str(row.project_id),
            delta_type=row.delta_type,
            payload_json=row.payload_json,
            gate_status=row.gate_status,
            risk_level=row.risk_level,
            applied_at=row.applied_at,
            applied_by=str(row.applied_by) if row.applied_by else None,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_decision_response(row: MergeDecision) -> MergeDecisionResponse:
        return MergeDecisionResponse(
            id=str(row.id),
            project_id=str(row.project_id),
            run_id=str(row.run_id) if row.run_id else None,
            delta_id=str(row.delta_id) if row.delta_id else None,
            decision_type=row.decision_type,
            payload_json=row.payload_json,
            reason=row.reason,
            created_at=row.created_at,
        )
