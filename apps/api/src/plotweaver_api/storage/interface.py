from __future__ import annotations

from abc import ABC, abstractmethod


class StorageClient(ABC):
    @abstractmethod
    def put_text(self, key: str, content: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_text(self, key: str) -> str:
        raise NotImplementedError
