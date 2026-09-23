from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..git import GitRepository
from ..models import Evidence


@dataclass(slots=True)
class DetectionContext:
    repository: GitRepository
    ref: str
    files: list[str]
    _cache: dict[str, str | None] = field(default_factory=dict)

    def read(self, path: str, *, max_bytes: int = 512_000) -> str | None:
        if path not in self._cache:
            self._cache[path] = self.repository.read_file(self.ref, path, max_bytes=max_bytes)
        return self._cache[path]

    def has(self, path: str) -> bool:
        return path in self.files

    def matching(self, *suffixes: str) -> list[str]:
        lowered = tuple(suffix.lower() for suffix in suffixes)
        return [path for path in self.files if path.lower().endswith(lowered)]


class Detector(Protocol):
    name: str

    def detect(self, context: DetectionContext) -> list[Evidence]: ...
