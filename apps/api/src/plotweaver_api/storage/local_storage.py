from __future__ import annotations

from pathlib import Path

from .interface import StorageClient


class LocalStorageClient(StorageClient):
    def __init__(self, root_dir: str = "./.local_storage"):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_text(self, key: str, content: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def get_text(self, key: str) -> str:
        path = self.root / key
        return path.read_text(encoding="utf-8")
