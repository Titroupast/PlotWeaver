from __future__ import annotations

from fastapi import APIRouter, Depends

from plotweaver_api.dependencies.services import get_health_service
from plotweaver_api.schemas.common import HealthResponse
from plotweaver_api.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    return service.liveness()


@router.get("/ready", response_model=HealthResponse)
def ready(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    return service.readiness()
