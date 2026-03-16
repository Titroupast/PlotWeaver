from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_orchestrator_service, get_run_service
from plotweaver_api.schemas.run import (
    HumanReviewDecisionRequest,
    RunCreateRequest,
    RunEventResponse,
    RunExecuteRequest,
    RunResponse,
    RunStateUpdateRequest,
)
from plotweaver_api.services.orchestrator_service import OrchestratorService
from plotweaver_api.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunResponse])
def list_runs(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RunService = Depends(get_run_service),
) -> list[RunResponse]:
    return service.list(project_id=project_id, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> RunResponse:
    return service.get(run_id)


@router.post("", response_model=RunResponse, status_code=201)
def create_run(
    payload: RunCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    return service.create(tenant_id=tenant_id, payload=payload, user_id=user_id)


@router.patch("/{run_id}/state", response_model=RunResponse)
def update_run_state(
    run_id: str,
    payload: RunStateUpdateRequest,
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    return service.update_state(run_id=run_id, payload=payload)


@router.post("/{run_id}/execute", response_model=RunResponse)
def execute_run(
    run_id: str,
    payload: RunExecuteRequest | None = None,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> RunResponse:
    return service.execute(run_id=run_id, payload=payload)


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
def list_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    after_cursor: str | None = Query(default=None),
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> list[RunEventResponse]:
    return service.list_events(run_id=run_id, limit=limit, offset=offset, after_cursor=after_cursor)


@router.get("/{run_id}/stream")
async def stream_run_events(
    run_id: str,
    after_cursor: str | None = Query(default=None),
    service: OrchestratorService = Depends(get_orchestrator_service),
    run_service: RunService = Depends(get_run_service),
):
    async def event_generator():
        cursor = after_cursor
        terminal_states = {"SUCCEEDED", "FAILED", "CANCELLED"}

        while True:
            events = service.list_events(run_id=run_id, limit=200, offset=0, after_cursor=cursor)
            for event in events:
                cursor = event.cursor or cursor
                yield f"id: {event.cursor or event.id}\n"
                yield "event: run-event\n"
                yield f"data: {event.model_dump_json()}\n\n"

            run = run_service.get(run_id)
            yield "event: run-state\n"
            yield f"data: {run.model_dump_json()}\n\n"

            if run.state in terminal_states:
                yield "event: done\n"
                yield f"data: {json.dumps({'run_id': run.id, 'state': run.state})}\n\n"
                break

            yield "event: heartbeat\n"
            yield f"data: {json.dumps({'run_id': run.id})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/{run_id}/review-decision", response_model=RunResponse)
def apply_human_review_decision(
    run_id: str,
    payload: HumanReviewDecisionRequest,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> RunResponse:
    return service.apply_human_review(run_id=run_id, payload=payload)
