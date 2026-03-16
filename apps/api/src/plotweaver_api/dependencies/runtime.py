from __future__ import annotations

from fastapi import Depends

from plotweaver_api.tasks.inprocess_runner import InProcessTaskRunner
from plotweaver_api.tasks.interface import TaskRunner


def get_task_runner() -> TaskRunner:
    return InProcessTaskRunner()
