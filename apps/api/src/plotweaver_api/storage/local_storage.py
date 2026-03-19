from __future__ import annotations

from pathlib import Path

from .interface import StorageClient


class LocalStorageClient(StorageClient):
    def __init__(self, root_dir: str = "./.local_storage"):
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_text(self, key: str, content: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def get_text(self, key: str) -> str:
        raw_path = Path(key)
        if raw_path.is_absolute():
            return raw_path.read_text(encoding="utf-8")

        primary = self.root / key
        if primary.exists():
            return primary.read_text(encoding="utf-8")

        # Backward compatibility for historical runs written from different working directories.
        this_file = Path(__file__).resolve()
        api_root = this_file.parents[3]  # apps/api
        repo_root = this_file.parents[5]
        candidates = [
            Path.cwd() / ".local_storage" / key,
            api_root / ".local_storage" / key,
            repo_root / ".local_storage" / key,
            repo_root / "apps" / "web" / ".local_storage" / key,
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")

        return primary.read_text(encoding="utf-8")
