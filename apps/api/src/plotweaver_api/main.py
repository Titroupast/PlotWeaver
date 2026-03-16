from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from plotweaver_api.api.v1 import api_router
from plotweaver_api.core.config import settings
from plotweaver_api.core.errors import register_exception_handlers
from plotweaver_api.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        debug=settings.app_debug,
        openapi_tags=[
            {"name": "health", "description": "Health and readiness"},
            {"name": "projects", "description": "Project management"},
            {"name": "chapters", "description": "Chapter metadata and versions"},
            {"name": "requirements", "description": "Continuation requirements"},
            {"name": "runs", "description": "Long-running generation tasks"},
            {"name": "artifacts", "description": "Structured artifacts for runs"},
            {"name": "memory", "description": "Memory and merge decisions"},
        ],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        trace_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-request-id"] = trace_id
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
