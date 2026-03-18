from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from plotweaver_api.dependencies.db import get_db_session
from plotweaver_api.dependencies.runtime import get_storage_client, get_task_runner
from plotweaver_api.repositories.artifact_repo import ArtifactRepository
from plotweaver_api.repositories.chapter_repo import ChapterRepository
from plotweaver_api.repositories.character_repo import CharacterRepository
from plotweaver_api.repositories.memory_delta_repo import MemoryDeltaRepository
from plotweaver_api.repositories.memory_repo import MemoryRepository
from plotweaver_api.repositories.merge_decision_repo import MergeDecisionRepository
from plotweaver_api.repositories.project_repo import ProjectRepository
from plotweaver_api.repositories.requirement_repo import RequirementRepository
from plotweaver_api.repositories.run_event_repo import RunEventRepository
from plotweaver_api.repositories.run_repo import RunRepository
from plotweaver_api.services.artifact_service import ArtifactService
from plotweaver_api.services.chapter_service import ChapterService
from plotweaver_api.services.health_service import HealthService
from plotweaver_api.services.memory_service import MemoryService
from plotweaver_api.services.orchestrator_service import OrchestratorService
from plotweaver_api.services.project_service import ProjectService
from plotweaver_api.services.requirement_service import RequirementService
from plotweaver_api.services.run_service import RunService
from plotweaver_api.storage.interface import StorageClient
from plotweaver_api.tasks.interface import TaskRunner


def get_health_service(session: Session = Depends(get_db_session)) -> HealthService:
    return HealthService(session)


def get_project_service(session: Session = Depends(get_db_session)) -> ProjectService:
    return ProjectService(ProjectRepository(session))


def get_chapter_service(
    session: Session = Depends(get_db_session),
    storage_client: StorageClient = Depends(get_storage_client),
) -> ChapterService:
    return ChapterService(ChapterRepository(session), storage=storage_client)


def get_requirement_service(session: Session = Depends(get_db_session)) -> RequirementService:
    return RequirementService(RequirementRepository(session))


def get_run_service(
    session: Session = Depends(get_db_session),
    task_runner: TaskRunner = Depends(get_task_runner),
) -> RunService:
    return RunService(RunRepository(session), task_runner)


def get_artifact_service(session: Session = Depends(get_db_session)) -> ArtifactService:
    return ArtifactService(ArtifactRepository(session))


def get_memory_service(session: Session = Depends(get_db_session)) -> MemoryService:
    return MemoryService(
        character_repo=CharacterRepository(session),
        memory_repo=MemoryRepository(session),
        delta_repo=MemoryDeltaRepository(session),
        decision_repo=MergeDecisionRepository(session),
    )


def get_orchestrator_service(
    session: Session = Depends(get_db_session),
    task_runner: TaskRunner = Depends(get_task_runner),
    storage_client: StorageClient = Depends(get_storage_client),
) -> OrchestratorService:
    return OrchestratorService(
        run_repo=RunRepository(session),
        artifact_repo=ArtifactRepository(session),
        event_repo=RunEventRepository(session),
        task_runner=task_runner,
        storage=storage_client,
    )
