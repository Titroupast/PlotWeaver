from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: Any | None = None


class NotFoundError(AppError):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(code="PW-COMMON-404", message=message, status_code=404, details=details)


class ConflictError(AppError):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(code="PW-COMMON-409", message=message, status_code=409, details=details)


class ValidationError(AppError):
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(code="PW-COMMON-422", message=message, status_code=422, details=details)


def _resolve_trace_id(request: Request) -> str | None:
    return getattr(request.state, "trace_id", None) or request.headers.get("x-request-id")


def app_error_response(err: AppError, trace_id: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=err.status_code,
        content={
            "code": err.code,
            "message": err.message,
            "details": err.details,
            "trace_id": trace_id,
        },
    )


def register_exception_handlers(app):
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError):
        return app_error_response(exc, trace_id=_resolve_trace_id(request))

    @app.exception_handler(Exception)
    async def _handle_unknown(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "code": "PW-COMMON-500",
                "message": "Internal server error",
                "details": str(exc),
                "trace_id": _resolve_trace_id(request),
            },
        )
