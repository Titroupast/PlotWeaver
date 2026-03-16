from __future__ import annotations

import uuid
from typing import Any

from .interface import TaskRunner


class InProcessTaskRunner(TaskRunner):
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        return f"inproc-{task_name}-{uuid.uuid4()}"
