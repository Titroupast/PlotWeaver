from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class RepositoryBase(Generic[T]):
    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model

    def get(self, entity_id: Any) -> T | None:
        return self.session.get(self.model, entity_id)

    def list(self, limit: int = 20, offset: int = 0) -> Sequence[T]:
        stmt = select(self.model).limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity
