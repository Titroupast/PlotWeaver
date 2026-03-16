from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .settings import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def tenant_session(tenant_id: str) -> Iterator[Session]:
    session = SessionLocal()
    try:
        session.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
