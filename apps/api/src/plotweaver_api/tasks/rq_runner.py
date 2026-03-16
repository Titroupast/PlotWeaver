from __future__ import annotations

from typing import Any

from .interface import TaskRunner


class RQTaskRunner(TaskRunner):
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        raise NotImplementedError("RQ task runner will be implemented in later phase")
