from __future__ import annotations

from .interface import StorageClient


class S3StorageClient(StorageClient):
    def __init__(self, bucket: str):
        self.bucket = bucket

    def put_text(self, key: str, content: str) -> str:
        raise NotImplementedError("S3 storage is not implemented in Phase 1")

    def get_text(self, key: str) -> str:
        raise NotImplementedError("S3 storage is not implemented in Phase 1")
