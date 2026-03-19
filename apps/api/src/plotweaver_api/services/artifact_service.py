from __future__ import annotations

from plotweaver_api.core.contracts import build_payload_hash, validate_artifact_payload
from plotweaver_api.core.errors import NotFoundError
from plotweaver_api.db.models import RunArtifact
from plotweaver_api.repositories.artifact_repo import ArtifactRepository
from plotweaver_api.schemas.artifact import ArtifactCreateRequest, ArtifactResponse


class ArtifactService:
    def __init__(self, repo: ArtifactRepository):
        self.repo = repo

    def create(self, tenant_id: str, payload: ArtifactCreateRequest) -> ArtifactResponse:
        validated_payload = validate_artifact_payload(payload.artifact_type, payload.payload_json)
        payload_hash = payload.payload_hash or build_payload_hash(validated_payload)

        artifact = RunArtifact(
            tenant_id=tenant_id,
            run_id=payload.run_id,
            artifact_type=payload.artifact_type,
            version_no=payload.version_no,
            payload_json=validated_payload,
            payload_hash=payload_hash,
        )
        saved = self.repo.add(artifact)
        return self._to_response(saved)

    def list(self, run_id: str, limit: int = 100, offset: int = 0) -> list[ArtifactResponse]:
        return [
            self._to_response(item)
            for item in self.repo.list_by_run(run_id, limit=limit, offset=offset)
        ]

    def update_payload(self, artifact_id: str, run_id: str, payload_json: dict) -> ArtifactResponse:
        artifact = self.repo.get(artifact_id)
        if artifact is None or str(artifact.run_id) != run_id or artifact.deleted_at is not None:
            raise NotFoundError("Artifact not found", details={"run_id": run_id, "artifact_id": artifact_id})

        validated_payload = validate_artifact_payload(artifact.artifact_type, payload_json)
        artifact.payload_json = validated_payload
        artifact.payload_hash = build_payload_hash(validated_payload)
        self.repo.session.flush()
        self.repo.session.refresh(artifact)
        return self._to_response(artifact)

    @staticmethod
    def _to_response(artifact: RunArtifact) -> ArtifactResponse:
        return ArtifactResponse(
            id=str(artifact.id),
            run_id=str(artifact.run_id),
            artifact_type=artifact.artifact_type,
            version_no=artifact.version_no,
            payload_json=artifact.payload_json,
            payload_hash=artifact.payload_hash,
            created_at=artifact.created_at,
        )
