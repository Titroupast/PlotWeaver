from __future__ import annotations

from plotweaver_api.db.settings import settings
from plotweaver_api.storage.interface import StorageClient
from plotweaver_api.storage.local_storage import LocalStorageClient
from plotweaver_api.tasks.inprocess_runner import InProcessTaskRunner
from plotweaver_api.tasks.interface import TaskRunner


def get_task_runner() -> TaskRunner:
    return InProcessTaskRunner()


def get_storage_client() -> StorageClient:
    return LocalStorageClient(root_dir=settings.storage_local_root)
