from __future__ import annotations

from plotweaver_api.core.contracts import build_payload_hash, validate_requirement_payload
from plotweaver_api.db.models import Requirement
from plotweaver_api.repositories.requirement_repo import RequirementRepository
from plotweaver_api.schemas.requirement import RequirementCreateRequest, RequirementResponse


class RequirementService:
    def __init__(self, repo: RequirementRepository):
        self.repo = repo

    def create(
        self,
        tenant_id: str,
        project_id: str,
        payload: RequirementCreateRequest,
        user_id: str | None = None,
    ) -> RequirementResponse:
        # Backward-compatible defaults so older/web clients can omit optional contract keys.
        normalized_payload = dict(payload.payload_json)
        normalized_payload.setdefault("chapter_goal", payload.chapter_goal)
        normalized_payload.setdefault("must_include", [])
        normalized_payload.setdefault("must_not_include", [])
        normalized_payload.setdefault("tone", "")
        normalized_payload.setdefault("continuity_constraints", [])
        normalized_payload.setdefault("target_length", 0)
        normalized_payload.setdefault("optional_notes", "")

        validated_payload = validate_requirement_payload(normalized_payload)
        payload_hash = payload.payload_hash or build_payload_hash(validated_payload)

        req = Requirement(
            tenant_id=tenant_id,
            project_id=project_id,
            chapter_goal=payload.chapter_goal,
            payload_json=validated_payload,
            payload_hash=payload_hash,
            source=payload.source,
            created_by=user_id,
            updated_by=user_id,
        )
        saved = self.repo.add(req)
        return self._to_response(saved)

    def list(self, project_id: str, limit: int = 50, offset: int = 0) -> list[RequirementResponse]:
        return [
            self._to_response(item)
            for item in self.repo.list_by_project(project_id, limit=limit, offset=offset)
        ]

    @staticmethod
    def _to_response(req: Requirement) -> RequirementResponse:
        return RequirementResponse(
            id=str(req.id),
            project_id=str(req.project_id),
            chapter_goal=req.chapter_goal,
            payload_json=req.payload_json,
            payload_hash=req.payload_hash,
            source=req.source,
            created_at=req.created_at,
        )
