from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TaskRunner(ABC):
    @abstractmethod
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        raise NotImplementedError
