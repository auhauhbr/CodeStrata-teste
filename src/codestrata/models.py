from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EvidenceKind(StrEnum):
    MANIFEST = "manifest"
    CONFIG = "config"
    SOURCE = "source"
    FILE = "file"
    LOCKFILE = "lockfile"


class EventKind(StrEnum):
    INTRODUCED = "introduced"
    REMOVED = "removed"
    VERSION_CHANGED = "version_changed"


@dataclass(slots=True, frozen=True)
class Evidence:
    technology: str
    kind: EvidenceKind
    path: str
    detail: str
    weight: int
    version: str | None = None


@dataclass(slots=True)
class TechnologyDetection:
    name: str
    category: str
    confidence: int
    version: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(slots=True)
class Snapshot:
    ref: str
    sha: str
    committed_at: datetime
    detections: list[TechnologyDetection] = field(default_factory=list)


@dataclass(slots=True)
class TimelineEvent:
    kind: EventKind
    technology: str
    at: datetime
    sha: str
    from_version: str | None = None
    to_version: str | None = None


@dataclass(slots=True)
class ArchaeologyReport:
    repository: str
    generated_at: datetime
    snapshots: list[Snapshot]
    events: list[TimelineEvent]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def encode(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, StrEnum):
                return value.value
            if hasattr(value, "__dataclass_fields__"):
                return {key: encode(item) for key, item in asdict(value).items()}
            if isinstance(value, list):
                return [encode(item) for item in value]
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            return value

        return encode(self)
