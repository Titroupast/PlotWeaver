from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from plotweaver_api.dependencies.auth import get_user_id
from plotweaver_api.dependencies.db import get_tenant_id
from plotweaver_api.dependencies.services import get_project_service
from plotweaver_api.schemas.project import ProjectCreateRequest, ProjectImportResponse, ProjectResponse
from plotweaver_api.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _looks_like_mojibake(text: str) -> bool:
    if not text:
        return True
    suspicious_tokens = ["锛", "鈥", "绗", "闆", "鍙", "鏃", "璇", "鐨", "銆", "�"]
    hits = sum(text.count(token) for token in suspicious_tokens)
    ratio = hits / max(1, len(text))
    return hits >= 8 and ratio > 0.01


def _decode_uploaded_txt(raw: bytes) -> str:
    # Prefer Unicode codecs first, then legacy GB18030 fallback.
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be", "gb18030"):
        try:
            decoded = raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
        if not decoded:
            continue
        if _looks_like_mojibake(decoded):
            continue
        return decoded
    from plotweaver_api.core.errors import ValidationError

    raise ValidationError(
        "Unable to decode txt file or detected garbled text",
        details={"hint": "请将文件保存为 UTF-8 或 UTF-16 后重试"},
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return service.list(tenant_id=tenant_id, limit=limit, offset=offset)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return service.create(tenant_id=tenant_id, payload=payload, user_id=user_id)


@router.post("/import-txt", response_model=ProjectImportResponse, status_code=201)
async def import_project_from_txt(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    language: str = Form(default="zh-CN"),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectImportResponse:
    file_name = (file.filename or "").lower()
    if not file_name.endswith(".txt"):
        from plotweaver_api.core.errors import ValidationError

        raise ValidationError("Only .txt file is supported", details={"filename": file.filename})

    raw = await file.read()
    text = _decode_uploaded_txt(raw)

    return service.import_from_text(
        tenant_id=tenant_id,
        title=title,
        novel_text=text,
        description=description,
        language=language,
        user_id=user_id,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    project = service.get(project_id)
    if project is None:
        from plotweaver_api.core.errors import NotFoundError

        raise NotFoundError("Project not found", details={"project_id": project_id})
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    user_id: str | None = Depends(get_user_id),
    service: ProjectService = Depends(get_project_service),
) -> Response:
    service.delete(project_id=project_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
