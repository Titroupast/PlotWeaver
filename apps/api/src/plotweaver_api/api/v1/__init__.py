from fastapi import APIRouter

from .routers import artifacts, chapters, health, memory, projects, requirements, runs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(chapters.router)
api_router.include_router(requirements.router)
api_router.include_router(runs.router)
api_router.include_router(artifacts.router)
api_router.include_router(memory.router)
