from __future__ import annotations

from plotweaver_api.db.models import Character, MemoryDelta, MergeDecision
from plotweaver_api.repositories.character_repo import CharacterRepository
from plotweaver_api.repositories.memory_delta_repo import MemoryDeltaRepository
from plotweaver_api.repositories.merge_decision_repo import MergeDecisionRepository
from plotweaver_api.schemas.memory import CharacterResponse, MemoryDeltaResponse, MergeDecisionResponse


class MemoryService:
    def __init__(
        self,
        character_repo: CharacterRepository,
        delta_repo: MemoryDeltaRepository,
        decision_repo: MergeDecisionRepository,
    ):
        self.character_repo = character_repo
        self.delta_repo = delta_repo
        self.decision_repo = decision_repo

    def list_characters(self, project_id: str, limit: int = 100, offset: int = 0) -> list[CharacterResponse]:
        return [self._to_character_response(row) for row in self.character_repo.list_by_project(project_id, limit, offset)]

    def list_memory_deltas(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MemoryDeltaResponse]:
        return [self._to_delta_response(row) for row in self.delta_repo.list_by_project(project_id, limit, offset)]

    def list_merge_decisions(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MergeDecisionResponse]:
        return [self._to_decision_response(row) for row in self.decision_repo.list_by_project(project_id, limit, offset)]

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
            created_at=row.created_at,
        )

    @staticmethod
    def _to_decision_response(row: MergeDecision) -> MergeDecisionResponse:
        return MergeDecisionResponse(
            id=str(row.id),
            project_id=str(row.project_id),
            run_id=str(row.run_id) if row.run_id else None,
            decision_type=row.decision_type,
            payload_json=row.payload_json,
            reason=row.reason,
            created_at=row.created_at,
        )
