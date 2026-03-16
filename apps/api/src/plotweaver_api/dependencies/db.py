from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from plotweaver_api.db.session import SessionLocal, set_tenant_context
from plotweaver_api.db.settings import settings


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    return x_tenant_id or settings.default_tenant_id


def get_db_session(tenant_id: str = Depends(get_tenant_id)) -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        set_tenant_context(session, tenant_id)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()